"""Replay frozen evidence with explicit, separately scored judgment interventions."""

import argparse
import csv
import json
from collections import Counter, defaultdict
from copy import deepcopy
from html import escape
from itertools import product
from pathlib import Path
from time import perf_counter
from urllib.request import ProxyHandler, build_opener

import yaml

from occupational_fitness_rag.evaluation.comparison_snapshot import read_recorded_rows
from occupational_fitness_rag.evaluation.evidence_judgment import (
    EvidenceJudgment,
    build_request,
    criterion_locations,
    parse_response,
    payload_size,
)
from occupational_fitness_rag.evaluation.judgment_comparison import local_post, make_payload
from occupational_fitness_rag.llm import require_local_url
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json


def run_condition(config, model, payload, protocol, post=local_post):
    """Bounded validation recovery retains every failed attempt and its cost."""
    endpoint = require_local_url(config["endpoint"])
    started = perf_counter()
    result = {
        "status": "failed",
        "attempts": [],
        "input_snapshot": deepcopy(payload),
        "recovered_after_validation_failure": False,
        "support_review": "pending_independent_review",
    }
    try:
        body = build_request(config, model, payload, protocol)
    except (ValueError, KeyError) as exc:
        result.update(error=f"{type(exc).__name__}: {exc}", seconds=perf_counter() - started)
        return result
    if payload_size(payload) > config["prompt_max_bytes"]:
        result.update(error="Input exceeds the frozen prompt byte limit", seconds=0.0)
        return result
    repairs = config.get("max_validation_repairs", 0)
    if not isinstance(repairs, int) or not 0 <= repairs <= 1:
        raise ValueError("At most one explicitly recorded validation repair is allowed")
    for attempt in range(repairs + 1):
        attempt_started = perf_counter()
        record = {"number": attempt + 1, "request_sha256": digest(body), "status": "failed"}
        raw = None
        try:
            raw = post(endpoint, "/api/chat", body, timeout=config.get("timeout_seconds", 180))
            record["raw_response"] = raw
            if (raw.get("prompt_eval_count") or 0) + config["output_tokens"] >= config[
                "context_length"
            ]:
                raise ValueError("Measured prompt tokens leave insufficient context reserve")
            answer = parse_response(raw, payload, protocol)
            record.update(status="completed", answer=answer.model_dump(mode="json"))
            result.update(status="completed", answer=record["answer"])
            if isinstance(answer, EvidenceJudgment):
                result["criterion_locations"] = criterion_locations(answer, payload)
                result["citation_aggregation"] = "validated_criterion_union"
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
            result["error"] = record["error"]
        record["seconds"] = perf_counter() - attempt_started
        result["attempts"].append(record)
        if record["status"] == "completed":
            result.pop("error", None)
            break
        # Transport failures, truncation and exhausted context are not semantic repairs.
        if (
            raw is None
            or raw.get("done_reason") == "length"
            or raw.get("done") is False
            or "context reserve" in record["error"]
        ):
            break
        if attempt < repairs:
            body = deepcopy(body)
            body["messages"].extend(
                [
                    {
                        "role": "assistant",
                        "content": raw.get("message", {}).get("content", "")[:12000],
                    },
                    {
                        "role": "user",
                        "content": (
                            "The previous output failed validation: "
                            + record["error"]
                            + ". Return a corrected response using the SAME original patient facts and evidence. "
                            "Do not invent a source, quote or patient finding. Preserve uncertainty. "
                            "The validator supplies no correct assessment outcome."
                        ),
                    },
                ]
            )
    result["seconds"] = perf_counter() - started
    result["recovered_after_validation_failure"] = (
        result["status"] == "completed" and len(result["attempts"]) > 1
    )
    result["support_review"] = "pending_independent_review"
    return result


def summarize_diagnostics(rows, planned):
    keys = {
        (r["case_id"], r["model"], r["evidence_policy"], r["protocol"], r["repeat"]) for r in rows
    }
    if len(keys) != len(rows):
        raise ValueError("Duplicate diagnostic condition")
    groups = defaultdict(list)
    for row in rows:
        groups[row["model"], row["evidence_policy"], row["protocol"]].append(row)
    metrics = []
    for (model, policy, protocol), group in sorted(groups.items()):
        first = [r["attempts"][0] if r["attempts"] else {} for r in group]
        metrics.append(
            dict(
                model=model,
                evidence_policy=policy,
                protocol=protocol,
                conditions=len(group),
                first_attempt_valid=sum(r.get("status") == "completed" for r in first),
                first_attempt_agreement=sum(
                    a.get("status") == "completed"
                    and a["answer"]["assessment_outcome"] == r["reference_outcome"]
                    for a, r in zip(first, group, strict=True)
                )
                / len(group),
                final_valid=sum(r["status"] == "completed" for r in group),
                final_agreement=sum(r["reference_agreement"] for r in group) / len(group),
                recoveries=sum(r["recovered_after_validation_failure"] for r in group),
                model_calls=sum(len(r["attempts"]) for r in group),
                seconds=sum(r["seconds"] for r in group),
            )
        )
    indexed = {
        (r["case_id"], r["model"], r["evidence_policy"], r["protocol"], r["repeat"]): r
        for r in rows
    }
    pairs = []
    for row in rows:
        if row["protocol"] != "evidence_contract":
            continue
        baseline = indexed.get(
            (row["case_id"], row["model"], row["evidence_policy"], "baseline", row["repeat"])
        )
        if baseline:
            same = digest(baseline["input_snapshot"]) == digest(row["input_snapshot"])
            same = (
                same
                and bool(row.get("model_digest"))
                and row.get("model_digest") == baseline.get("model_digest")
            )
            both = row["status"] == baseline["status"] == "completed"
            pairs.append(
                dict(
                    case_id=row["case_id"],
                    model=row["model"],
                    evidence_policy=row["evidence_policy"],
                    repeat=row["repeat"],
                    identical_inputs=same,
                    baseline=baseline.get("answer", {}).get("assessment_outcome"),
                    intervention=row.get("answer", {}).get("assessment_outcome"),
                    reference=row["reference_outcome"],
                    both_valid=both,
                    transition=(
                        "wrong_to_correct"
                        if row["reference_agreement"] and not baseline["reference_agreement"]
                        else "correct_to_wrong"
                        if baseline["reference_agreement"] and not row["reference_agreement"]
                        else "unchanged_correctness"
                    )
                    if both and same
                    else "not_comparable",
                )
            )
    return dict(
        planned_conditions=planned,
        recorded_conditions=len(rows),
        execution_status="completed" if len(rows) == planned else "running",
        metrics=metrics,
        paired_changes=pairs,
        failure_reasons=dict(Counter(r.get("error") for r in rows if r["status"] != "completed")),
        clinical_accuracy=None,
        phase="targeted_diagnostic_development_set",
        warning="Known-error cases are a development set, not an independent validation set. Quote presence does not prove entailment.",
    )


def write_report(output, rows, planned):
    summary = summarize_diagnostics(rows, planned)
    write_json(output / "summary.json", summary)
    with (output / "summary.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        if summary["metrics"]:
            writer = csv.DictWriter(stream, fieldnames=list(summary["metrics"][0]))
            writer.writeheader()
            writer.writerows(summary["metrics"])
    metric_rows = "".join(
        f"<tr><td>{escape(m['model'])}</td><td>{escape(m['evidence_policy'])}</td><td>{m['protocol']}</td>"
        f"<td>{m['first_attempt_valid']}/{m['conditions']}</td><td>{m['first_attempt_agreement']:.1%}</td>"
        f"<td>{m['final_valid']}/{m['conditions']}</td><td>{m['final_agreement']:.1%}</td>"
        f"<td>{m['recoveries']}</td><td>{m['model_calls']}</td></tr>"
        for m in summary["metrics"]
    )
    cases = sorted({r["case_id"] for r in rows})
    models = sorted({r["model"] for r in rows})
    selectors = "".join(
        f'<label>{label}<select data-field="{key}">'
        + "".join(f'<option value="{escape(v)}">{escape(v)}</option>' for v in values)
        + "</select></label>"
        for key, label, values in [("case", "Case", cases), ("model", "Model", models)]
    )
    cards = []
    for row in rows:
        answer = row.get("answer", {})
        sources = "".join(
            f"<details><summary>{escape(s['source_id'])} · PDF {s['pdf_page']} · §{escape(s['section'])}</summary>"
            f"<blockquote>{escape(s['source_text'])}</blockquote></details>"
            for s in row["input_snapshot"]["guideline_evidence"]
        )
        cards.append(
            f'<article data-case="{escape(row["case_id"])}" data-model="{escape(row["model"])}">'
            f"<h3>{row['evidence_policy']} / {row['protocol']}</h3>"
            f"<p>{escape(row['case_id'])} · {escape(row['model'])} · {row['status']}</p>"
            f"<p>Reference: {row['reference_outcome']}<br>Proposal: {answer.get('assessment_outcome', 'Unavailable')}</p>"
            f"<p>{escape(answer.get('explanation', row.get('error', '')))}</p>"
            f"<details><summary>Criterion checks and exact original spans</summary><pre>{escape(json.dumps(row.get('criterion_locations', []), indent=2))}</pre></details>"
            f"<details><summary>Patient note and frozen facts</summary><pre>{escape(json.dumps({k: v for k, v in row['input_snapshot'].items() if k != 'guideline_evidence'}, indent=2))}</pre></details>"
            + sources
            + f"<details><summary>All attempts, including failures</summary><pre>{escape(json.dumps(row['attempts'], indent=2))}</pre></details></article>"
        )
    html = (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Evidence contract diagnostics | Occupational Fitness Platform</title><style>"
        "body{font:14px/1.65 system-ui;background:#f4f6f8;color:#233647;margin:0}header{background:#233647;color:white;padding:26px 4vw}"
        "main{max-width:1400px;margin:auto;padding:26px}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;background:white}"
        "td,th{padding:12px;border-bottom:1px solid #dce3e9;text-align:left}.cards{display:grid;grid-template-columns:1fr 1fr;gap:20px}"
        "article{border:1px solid #dce3e9;background:white;padding:22px;border-radius:8px}article[hidden]{display:none}"
        "pre,blockquote{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f7fa;padding:14px}summary{cursor:pointer;padding:8px 0}"
        "label{display:inline-block;margin:20px 20px 20px 0}select{display:block;padding:8px}.notice{background:#fff7e9;padding:18px}"
        "@media(max-width:800px){.cards{grid-template-columns:1fr}main{padding:12px}}</style>"
        "<header>OCCUPATIONAL FITNESS PLATFORM<h1>Evidence contract diagnostics</h1></header><main>"
        f"<p>{summary['recorded_conditions']}/{planned} conditions recorded · {summary['execution_status']}</p>"
        '<p class="notice">Known-error development pilot. Patient inputs and original source passages are frozen. '
        "The intervention changes category instructions and the output schema together. First attempts and repaired answers are scored separately. "
        "Exact quotation establishes provenance, not clinical support. Production decisions remain unchanged.</p>"
        '<div class="scroll"><table><thead><tr><th>Model</th><th>Evidence policy</th><th>Protocol</th><th>First valid</th>'
        "<th>First agreement</th><th>Final valid</th><th>Final agreement</th><th>Recoveries</th><th>Model calls</th></tr></thead><tbody>"
        + metric_rows
        + "</tbody></table></div>"
        + selectors
        + '<div class="cards">'
        + "".join(cards)
        + "</div>"
        '<p><a href="summary.json">Summary and paired changes</a> · <a href="summary.csv">Metrics CSV</a> · '
        '<a href="results.jsonl">Original calls and attempts</a> · <a href="manifest.json">Frozen experiment manifest</a></p>'
        '<script>function f(){const s=[...document.querySelectorAll("select")];document.querySelectorAll("article").forEach(a=>a.hidden=s.some(x=>a.dataset[x.dataset.field]!==x.value))}document.querySelectorAll("select").forEach(s=>s.addEventListener("change",f));f();</script></main></html>'
    )
    (output / "index.html").write_text(html, encoding="utf-8")
    return summary


def run_diagnostics(config_path, resume=False, max_calls=None):
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    if (
        not set(config["protocols"]) <= {"baseline", "evidence_contract"}
        or not set(config["evidence_policies"])
        <= {"hybrid_fixed", "documented_modules", "reference_evidence"}
        or config["repeats"] < 1
        or max_calls is not None
        and max_calls < 0
    ):
        raise ValueError("Invalid diagnostic configuration")
    baseline = Path(config["baseline_dir"]).resolve()
    output = Path(config["output"]).resolve()
    endpoint = require_local_url(config["endpoint"])
    if output == baseline:
        raise ValueError("Diagnostic output must be separate from the completed baseline")
    rows_path = output / "results.jsonl"
    if rows_path.exists() and not resume:
        raise ValueError("Diagnostic records already exist; use --resume or a separate output")
    old = read_recorded_rows(baseline / "results.jsonl")
    units = {
        u["source_id"]: u
        for u in json.loads((baseline / "corpus.json").read_text(encoding="utf-8"))["units"]
    }
    rankings = json.loads((baseline / "retrieval.json").read_text(encoding="utf-8"))
    with build_opener(ProxyHandler({})).open(endpoint + "/api/tags", timeout=10) as response:
        inventory = {m["name"]: m["digest"] for m in json.load(response)["models"]}
    original_inventory = json.loads((baseline / "model_inventory.json").read_text(encoding="utf-8"))
    for model in config["models"]:
        if inventory.get(model) != config["expected_model_digests"].get(model):
            raise ValueError("Judge model digest differs from the diagnostic pin")
        if (
            inventory.get(model) != original_inventory.get(model)
            and config.get("baseline_match_policy") != "permit_revision_with_contemporary_control"
        ):
            raise ValueError("Judge revision requires a contemporaneous pinned baseline")
    with build_opener(ProxyHandler({})).open(endpoint + "/api/version", timeout=10) as response:
        runtime = json.load(response)
    inputs = {}
    for case_id, policy in product(config["case_ids"], config["evidence_policies"]):
        method = "reference_evidence" if policy == "reference_evidence" else "hybrid"
        matches = [r for r in old if r["case_id"] == case_id and r["method"] == method]
        if not matches or len({digest(r["input_snapshot"]) for r in matches}) != 1:
            raise ValueError("Missing or inconsistent frozen condition")
        record = matches[0]
        payload = deepcopy(record["input_snapshot"])
        selection = {
            "policy": "frozen_v5",
            "source_ids": [s["source_id"] for s in payload["guideline_evidence"]],
        }
        if policy == "documented_modules":
            from occupational_fitness_rag.evaluation.evidence_selection import (
                select_documented_evidence,
            )

            selection = select_documented_evidence(
                payload,
                [r for r in rankings if r["case_id"] == case_id and r["method"] == "hybrid"],
                config["top_k"],
            )
            fake_case = {
                "facts": {
                    key: {
                        "status": "present",
                        "value": fact["value"],
                        "evidence": [{"quote": q} for q in fact["patient_quotes"]],
                    }
                    for key, fact in payload["verified_patient_facts"].items()
                },
                "modules_requested": payload["modules"],
                "source_text": payload["nurse_note"],
            }
            payload, excluded = make_payload(fake_case, units, selection["source_ids"], config)
            selection["excluded_by_byte_budget"] = excluded
        elif policy not in {"hybrid_fixed", "reference_evidence"}:
            raise ValueError("Unknown diagnostic evidence policy")
        inputs[case_id, policy] = {
            "payload": payload,
            "reference": record["reference_outcome"],
            "selection": selection,
        }
    condition_keys = list(
        product(
            config["models"],
            config["case_ids"],
            config["evidence_policies"],
            config["protocols"],
            range(config["repeats"]),
        )
    )
    manifest = dict(
        config=config,
        planned_conditions=len(condition_keys),
        model_digests={m: inventory[m] for m in config["models"]},
        runtime=runtime,
        historical_model_digests=original_inventory,
        model_revision_changes={
            model: {"historical": original_inventory.get(model), "current": inventory[model]}
            for model in config["models"]
            if original_inventory.get(model) != inventory[model]
        },
        baseline_fingerprints={
            name: sha256_bytes((baseline / name).read_bytes())
            for name in ["results.jsonl", "corpus.json", "manifest.json", "labels.json"]
        },
        code_sha256=digest(
            {
                p.name: p.read_text(encoding="utf-8")
                for p in Path(__file__).parent.glob("*.py")
                if p.name
                in {"evidence_judgment.py", "evidence_selection.py", "judgment_diagnostics.py"}
            }
        ),
        input_sha256=digest(
            {f"{case}:{policy}": item["payload"] for (case, policy), item in inputs.items()}
        ),
        phase="targeted_diagnostic_development_set",
        production_change=False,
        clinical_review="pending",
    )
    manifest_path = output / "manifest.json"
    if manifest_path.exists() and json.loads(manifest_path.read_text(encoding="utf-8")) != manifest:
        raise ValueError("Diagnostic identity changed; use a separate output directory")
    output.mkdir(parents=True, exist_ok=True)
    write_json(manifest_path, manifest)
    rows = read_recorded_rows(rows_path)

    def key(row):
        return row["model"], row["case_id"], row["evidence_policy"], row["protocol"], row["repeat"]

    done = {key(row) for row in rows}
    if len(done) != len(rows) or not done <= set(condition_keys):
        raise ValueError("Duplicate or unexpected diagnostic conditions")
    added = 0
    for model, case_id, policy, protocol, repeat in condition_keys:
        if (model, case_id, policy, protocol, repeat) in done:
            continue
        if max_calls is not None and added >= max_calls:
            break
        item = inputs[case_id, policy]
        with build_opener(ProxyHandler({})).open(endpoint + "/api/tags", timeout=10) as response:
            current = {m["name"]: m["digest"] for m in json.load(response)["models"]}
        if current.get(model) != inventory[model]:
            raise ValueError(
                "Pinned judge changed during the diagnostic; stop before further inference"
            )
        row = dict(
            case_id=case_id,
            model=model,
            model_digest=inventory[model],
            evidence_policy=policy,
            protocol=protocol,
            repeat=repeat,
            selection=item["selection"],
            input_sha256=digest(item["payload"]),
        )
        row.update(run_condition(config, model, item["payload"], protocol))
        # Gold is attached after inference and never sent to the local model.
        row["reference_outcome"] = item["reference"]
        row["reference_agreement"] = (
            row["status"] == "completed"
            and row["answer"]["assessment_outcome"] == item["reference"]
        )
        rows.append(row)
        with rows_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        added += 1
        write_report(output, rows, len(condition_keys))
        print(
            f"Recorded {len(rows)}/{len(condition_keys)}: {case_id} {model} {policy} {protocol} {row['status']}",
            flush=True,
        )
    return write_report(output, rows, len(condition_keys))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/experiments/judgment_diagnostics.yaml")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-calls", type=int)
    args = parser.parse_args()
    print(json.dumps(run_diagnostics(args.config, args.resume, args.max_calls), indent=2))
