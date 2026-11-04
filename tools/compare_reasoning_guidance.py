"""Paired aggregation diagnostic on source-literal facts and a shared fresh ledger."""

import argparse
import json
import os
from collections import Counter
from datetime import datetime, timezone
from html import escape
from itertools import product
from pathlib import Path

import yaml

from occupational_fitness_rag.evaluation import applicability_comparison as experiment
from occupational_fitness_rag.evaluation import applicability_judgment as judgment
from occupational_fitness_rag.evaluation import passage_comparison as previous
from occupational_fitness_rag.evaluation import passage_judgment
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json
from tools.build_source_literal_facts import load_snapshot

GUIDANCE = ("baseline", "source_bound_v1")
KEYS = ("model", "case_id", "evidence_policy", "guidance", "repeat")


def config_for(config, guidance):
    if guidance not in GUIDANCE:
        raise ValueError("Unknown guidance arm")
    return {**config, "judgment_guidance": guidance}


def load_evidence(config):
    """Verify immutable old evidence separately from the new judge environment."""
    if config.get("evidence_import") != "frozen_read_only":
        raise ValueError("An explicit frozen read-only evidence import is required")
    historical = json.loads((Path(config["retrieval_dir"]) / "manifest.json").read_bytes())
    # This checks the historical evidence's own declared runtime. It executes no
    # retrieval or inference. The NEW judge still requires config's runtime pin.
    evidence_config = {
        **config, "expected_runtime_version": historical["config"]["expected_runtime_version"],
    }
    return experiment.load_retrieval(evidence_config)


def validate_saved(rows, stages, manifest, frozen, config):
    planned = {tuple(key) for key in manifest["planned_keys"]}
    keys = [tuple(row[key] for key in KEYS) for row in rows]
    if len(keys) != len(set(keys)) or not set(keys) <= planned:
        raise ValueError("Unexpected or repeated paired diagnostic key")
    shared = {}
    for row in stages:
        key = (row["model"], row["case_id"], row["evidence_policy"])
        if key in shared or key not in {tuple(k) for k in manifest["shared_stage_keys"]}:
            raise ValueError("Unexpected or repeated shared first stage")
        payload = frozen["payloads"][row["case_id"]][row["evidence_policy"]]["payload"]
        if row["experiment_identity"] != manifest["identity"] or row["input_sha256"] != digest(payload):
            raise ValueError("Shared first-stage identity differs")
        for attempt in row["stage"]["attempts"]:
            if attempt["request_sha256"] != digest(attempt["request"]):
                raise ValueError("Shared first-stage request differs")
            if attempt["status"] == "completed":
                parsed = judgment.parse_applicability_response(attempt["raw_response"], payload)
                if parsed.model_dump(mode="json") != attempt["answer"]:
                    raise ValueError("Shared ledger differs from original raw response")
        if row["stage"]["status"] == "completed" and row["stage"]["answer"] != row["stage"]["attempts"][-1]["answer"]:
            raise ValueError("Shared ledger differs from its accepted attempt")
        shared[key] = row
    for row in rows:
        key = (row["model"], row["case_id"], row["evidence_policy"])
        stage = shared[key]["stage"]
        payload = frozen["payloads"][row["case_id"]][row["evidence_policy"]]["payload"]
        if (
            row["experiment_identity"] != manifest["identity"]
            or row["input_sha256"] != digest(payload)
            or row["shared_stage_sha256"] != digest(shared[key])
            or row["reference_outcome"] != frozen["labels"][row["case_id"]]
        ):
            raise ValueError("Saved aggregation identity, shared ledger or reference differs")
        if stage["status"] != "completed":
            if row["status"] != "failed" or row["model_calls"] != 0 or row["attempts"]:
                raise ValueError("A failed shared ledger cannot become successful aggregation")
            continue
        review = judgment.ApplicabilityReview.model_validate(stage["answer"])
        arm = config_for(config, row["guidance"])
        expected = judgment.build_aggregation_request(arm, row["model"], payload, review)
        if row["attempts"][0]["request"] != expected:
            raise ValueError("Saved aggregation request differs from frozen inputs")
        calls = 0
        for attempt in row["attempts"]:
            if attempt["request_sha256"] != digest(attempt["request"]) or attempt["request_bytes"] != len(previous.json_bytes(attempt["request"])):
                raise ValueError("Saved aggregation request fingerprint differs")
            calls += bool(attempt["provider_called"])
            if attempt["status"] == "completed":
                parsed = judgment.parse_aggregation_response(attempt["raw_response"], payload, review, config=arm)
                if parsed.model_dump(mode="json") != attempt["answer"]:
                    raise ValueError("Saved accepted response differs")
        if calls != row["model_calls"]:
            raise ValueError("Saved aggregation call count differs")
        if row["status"] == "completed" and row["answer"] != row["attempts"][-1]["answer"]:
            raise ValueError("Final proposal differs from its accepted raw response")
        agreement = row["status"] == "completed" and row["answer"]["assessment_outcome"] == row["reference_outcome"]
        if row["reference_agreement"] != agreement:
            raise ValueError("Saved agreement differs")
    return set(keys), shared


def report(output, rows, stages, manifest):
    metrics = []
    for model, guidance in product(manifest["config"]["models"], GUIDANCE):
        group = [r for r in rows if r["model"] == model and r["guidance"] == guidance]
        metrics.append({
            "model": model, "guidance": guidance, "conditions": len(group),
            "accepted": sum(r["status"] == "completed" for r in group),
            "correct": sum(r["reference_agreement"] for r in group),
            "aggregation_calls": sum(r["model_calls"] for r in group),
            "flagged": sum(bool(r.get("output_consistency_flags")) for r in group),
        })
    paired, transitions = [], Counter()
    by_key = {tuple(r[k] for k in KEYS): r for r in rows}
    for model, case_id, policy, repeat in sorted({
        (r["model"], r["case_id"], r["evidence_policy"], r["repeat"]) for r in rows
    }):
        arms = [by_key.get((model, case_id, policy, g, repeat)) for g in GUIDANCE]
        if any(r is None for r in arms):
            continue
        before, after = arms
        if any(r["status"] != "completed" for r in arms):
            transition = before["status"] + "_to_" + after["status"]
        else:
            transition = ("correct" if before["reference_agreement"] else "wrong") + "_to_" + ("correct" if after["reference_agreement"] else "wrong")
        transitions[transition] += 1
        paired.append({"model": model, "case_id": case_id, "policy": policy, "repeat": repeat,
                       "transition": transition, "baseline": before, "source_bound": after})
    total = len(manifest["planned_keys"])
    summary = {
        "recorded": len(rows), "planned": total, "execution_complete": len(rows) == total,
        "distinct_cases": len(manifest["config"]["case_ids"]), "metrics": metrics,
        "paired_transitions": dict(transitions), "shared_first_stages": len(stages),
        "shared_stage_model_calls": sum(bool(a["provider_called"]) for r in stages for a in r["stage"]["attempts"]),
        "aggregation_model_calls": sum(r["model_calls"] for r in rows),
        "failures": dict(Counter(r["error"] for r in rows if r["status"] == "failed")),
        "scope": "Known-error development diagnostic. Fresh source-literal first-stage proposals are shared across aggregation arms. Held original evidence is not newly executed retrieval. Engineering reference agreement is not clinical accuracy.",
        "production_change": False, "clinical_review": "pending",
    }
    write_json(output / "summary.json", summary)
    write_json(output / "paired_analysis.json", paired)
    heads = list(metrics[0]) if metrics else []
    table = "".join("<tr>" + "".join(f"<td>{escape(str(m[h]))}</td>" for h in heads) + "</tr>" for m in metrics)
    cards = ""
    for pair in paired:
        arms = ""
        for name in ("baseline", "source_bound"):
            row = pair[name]
            arms += '<section><h3>' + name + '</h3><pre>' + escape(json.dumps({
                "status": row["status"], "answer": row.get("answer"),
                "error": row.get("error"), "locations": row.get("criterion_locations"),
            }, ensure_ascii=False, indent=2)) + '</pre></section>'
        cards += (f'<details data-case="{escape(pair["case_id"])}" data-model="{escape(pair["model"])}"><summary>'
                  + escape(f'{pair["case_id"]} / {pair["model"]} / {pair["policy"]} / repeat {pair["repeat"]+1} / {pair["transition"]}')
                  + '</summary><div class="pair">' + arms + '</div></details>')
    selectors = "".join(
        '<label>' + label + '<select data-field="' + field + '"><option value="">All</option>'
        + ''.join(f'<option value="{escape(v)}">{escape(v)}</option>' for v in values)
        + '</select></label>' for label, field, values in [
            ("Case", "case", manifest["config"]["case_ids"]),
            ("Model", "model", manifest["config"]["models"]),
        ]
    )
    html = (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Source-bound reasoning comparison</title><style>body{font:14px/1.6 system-ui;background:#f5f7f9;color:#243748;'
        'max-width:1400px;margin:36px auto;padding:24px}table{width:100%;border-collapse:collapse}td,th{padding:12px;text-align:left;'
        'border-bottom:1px solid #dce3ea}details,section{background:white;border:1px solid #dce3ea;padding:16px;margin:12px 0;'
        'border-radius:8px}summary{cursor:pointer}.pair{display:grid;grid-template-columns:1fr 1fr;gap:12px}'
        'pre{white-space:pre-wrap;overflow-wrap:anywhere}label{display:inline-block;margin:12px}select{margin-left:8px;padding:8px}'
        '@media(max-width:850px){.pair{grid-template-columns:1fr}}[hidden]{display:none}</style><small>OCCUPATIONAL FITNESS PLATFORM</small>'
        f'<h1>Source-bound reasoning comparison</h1><p>{len(rows)}/{total} conditions recorded</p><p>'
        + escape(summary["scope"]) + '</p><p>Changed bundle: exact source-addressed decimal relations, explicit licensing-category guidance, '
        'and program-bound final source slots. Numeric support does not decide applicability or clinical eligibility.</p><table><tr>'
        + ''.join(f'<th>{escape(h)}</th>' for h in heads) + '</tr>' + table + '</table><pre>'
        + escape(json.dumps(dict(transitions), indent=2)) + '</pre>' + selectors + cards
        + '<p><a href="inputs.json">Shared original patient inputs and passages</a> · <a href="results.jsonl">Raw aggregation records</a> · '
        '<a href="first_stages.jsonl">Fresh shared first stages</a> · <a href="manifest.json">Version manifest</a> · '
        '<a href="paired_analysis.json">Paired results</a></p><script>document.querySelectorAll("select").forEach(s=>s.onchange=()=>'
        '{const fields=[...document.querySelectorAll("select")];document.querySelectorAll("details[data-case]").forEach(d=>'
        'd.hidden=fields.some(x=>x.value&&d.dataset[x.dataset.field]!==x.value))});</script></html>'
    )
    (output / "index.html").write_text(html, encoding="utf-8")
    return summary


def append(path, row):
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")


def run(config_path, resume=False, prepare_only=False):
    config_text = Path(config_path).read_text(encoding="utf-8")
    config = yaml.safe_load(config_text)
    experiment.validate_config(config)
    for field in ("models", "case_ids", "evidence_policies"):
        if len(config[field]) != len(set(config[field])):
            raise ValueError("Diagnostic dimensions must be unique")
    if config["repeats"] < 1 or config["aggregation_ledger_mode"] != "field_references":
        raise ValueError("This diagnostic requires shared field-reference encoding and positive repeats")
    frozen = load_evidence(config)
    root = Path(__file__).resolve().parents[1]
    snapshot = load_snapshot(config["fact_snapshot"], root)
    if snapshot["identity"] != config["fact_snapshot_identity"]:
        raise ValueError("Unexpected source-literal fact snapshot")
    inputs = {}
    for cid in config["case_ids"]:
        inputs[cid] = {}
        for policy in config["evidence_policies"]:
            selected = frozen["payloads"][cid][policy]
            if selected["status"] != "completed":
                raise ValueError("A frozen retrieval failure cannot become fresh evidence")
            payload = selected["payload"]
            if previous.patient_identity(payload) != snapshot["cases"][cid]["sensitivity_patient_identity"]:
                raise ValueError("Patient input differs from source-literal version")
            inputs[cid][policy] = payload
    planned = list(product(config["models"], config["case_ids"], config["evidence_policies"], GUIDANCE, range(config["repeats"])))
    shared_keys = list(product(config["models"], config["case_ids"], config["evidence_policies"]))
    identity_data = {
        "config": config, "upstream_fingerprints": frozen["fingerprints"],
        "source_snapshot": previous.source_snapshot(config_text),
        "tool_source": Path(__file__).read_text(encoding="utf-8"),
        "environment": previous.pinned_environment(config),
        "historical_retrieval_runtime": frozen["manifest"]["config"]["expected_runtime_version"],
        "planned_keys": planned, "shared_stage_keys": shared_keys, "inputs_sha256": digest(inputs),
    }
    manifest = {**identity_data, "identity": digest(identity_data), "production_change": False}
    output = Path(config["output"]).resolve()
    upstream = Path(config["retrieval_dir"]).resolve()
    if output == upstream or output.is_relative_to(upstream) or upstream.is_relative_to(output):
        raise ValueError("Diagnostic must be separate from frozen retrieval")
    output.mkdir(parents=True, exist_ok=True)
    lock = output / ".run.lock"
    with lock.open("x", encoding="ascii") as stream:
        stream.write(str(os.getpid()))
    try:
        path = output / "manifest.json"
        if path.exists():
            if not resume or json.loads(path.read_bytes()) != json.loads(json.dumps(manifest)):
                raise ValueError("Resume requires an identical complete experiment identity")
            if json.loads((output / "inputs.json").read_bytes()) != inputs:
                raise ValueError("Frozen diagnostic inputs changed")
        else:
            if any(p.name != ".run.lock" for p in output.iterdir()):
                raise ValueError("Non-empty diagnostic output lacks a manifest")
            write_json(path, manifest)
            write_json(output / "inputs.json", inputs)
        rows = previous.read_records(output / "results.jsonl")
        stages = previous.read_records(output / "first_stages.jsonl")
        done, shared = validate_saved(rows, stages, manifest, frozen, config)
        if prepare_only:
            return report(output, rows, stages, manifest)
        for model, cid, policy in shared_keys:
            payload = inputs[cid][policy]
            key = (model, cid, policy)
            if key not in shared:
                previous.pinned_environment(config)
                stage = experiment.run_stage(
                    config, judgment.build_applicability_request(config, model, payload),
                    lambda raw: judgment.parse_applicability_response(raw, payload),
                    lambda review: {"criterion_locations": judgment.review_locations(review, payload),
                                    "ledger_consistency_flags": judgment.ledger_consistency_flags(review)},
                )
                stage.pop("proposal", None)
                item = {"model": model, "case_id": cid, "evidence_policy": policy, "stage": stage,
                        "experiment_identity": manifest["identity"], "input_sha256": digest(payload)}
                append(output / "first_stages.jsonl", item)
                stages.append(item)
                shared[key] = item
                print(f"Shared first stage {model} {cid} {policy}: {stage['status']}", flush=True)
            stage = shared[key]["stage"]
            for repeat in range(config["repeats"]):
                for guidance in GUIDANCE if repeat % 2 == 0 else tuple(reversed(GUIDANCE)):
                    condition = (model, cid, policy, guidance, repeat)
                    if condition in done:
                        continue
                    if stage["status"] != "completed":
                        result = {"status": "failed", "attempts": [], "error": "Shared first-stage failure: " + stage["error"]}
                    else:
                        review = judgment.ApplicabilityReview.model_validate(stage["answer"])
                        arm = config_for(config, guidance)
                        previous.pinned_environment(config)
                        result = experiment.run_stage(
                            arm, judgment.build_aggregation_request(arm, model, payload, review),
                            lambda raw: judgment.parse_aggregation_response(raw, payload, review, config=arm),
                            lambda answer: {"criterion_locations": passage_judgment.criterion_locations(answer, payload),
                                            "output_consistency_flags": passage_judgment.output_consistency_flags(answer, payload)},
                        )
                        result.pop("proposal", None)
                    row = {
                        **dict(zip(KEYS, condition, strict=True)), **result,
                        "experiment_identity": manifest["identity"], "input_sha256": digest(payload),
                        "shared_stage_sha256": digest(shared[key]),
                        "model_calls": sum(bool(a["provider_called"]) for a in result["attempts"]),
                        "reference_outcome": frozen["labels"][cid],
                        "reference_agreement": result["status"] == "completed" and result["answer"]["assessment_outcome"] == frozen["labels"][cid],
                    }
                    if previous.read_records(output / "results.jsonl") != rows:
                        raise ValueError("Result records changed during exclusive execution")
                    append(output / "results.jsonl", row)
                    rows.append(row)
                    done.add(condition)
                    report(output, rows, stages, manifest)
                    print(f"Recorded {len(rows)}/{len(planned)} {condition}: {row['status']}", flush=True)
        validate_saved(rows, stages, manifest, frozen, config)
        if done != set(planned) or set(shared) != set(shared_keys):
            raise ValueError("Diagnostic is missing planned conditions or shared ledgers")
        if previous.source_snapshot(config_text) != manifest["source_snapshot"] or previous.pinned_environment(config) != manifest["environment"]:
            raise ValueError("Package or runtime changed before completion")
        summary = report(output, rows, stages, manifest)
        write_json(output / "execution_audit.json", {
            "utc": datetime.now(timezone.utc).isoformat(), "conditions": len(rows),
            "planned_condition_keys_complete": True, "source_and_runtime_match": True,
            "results_sha256": sha256_bytes((output / "results.jsonl").read_bytes()),
            "first_stages_sha256": sha256_bytes((output / "first_stages.jsonl").read_bytes()),
            "manifest_sha256": sha256_bytes((output / "manifest.json").read_bytes()),
            "total_model_calls": summary["shared_stage_model_calls"] + summary["aggregation_model_calls"],
            "production_change": False,
        })
        return summary
    finally:
        lock.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.config, args.resume, args.prepare_only), indent=2))
