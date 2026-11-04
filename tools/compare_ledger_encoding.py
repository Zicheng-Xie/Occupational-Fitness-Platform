"""Compare aggregation encodings with identical frozen stage-one proposals.

This diagnostic changes only duplicated patient-value materialization. It is not
a retrieval-method comparison or a replay of the complete two-stage workflow.
"""

import argparse
import json
import os
from collections import Counter
from datetime import datetime, timezone
from html import escape
from itertools import product
from pathlib import Path

from occupational_fitness_rag.evaluation import applicability_comparison as experiment
from occupational_fitness_rag.evaluation import applicability_judgment as judgment
from occupational_fitness_rag.evaluation import passage_comparison as previous
from occupational_fitness_rag.evaluation import passage_judgment
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json

MODES = ("full_values", "field_references")
KEY = ("model", "case_id", "mode", "repeat")


def inputs_from(source, case_ids, models, policy):
    source = Path(source)
    if (source / ".run.lock").exists():
        raise ValueError("The upstream writer must stop before freezing a diagnostic")
    raw = (source / "results.jsonl").read_bytes()
    rows = previous.read_records(source / "results.jsonl")
    manifest = json.loads((source / "manifest.json").read_bytes())
    audit = json.loads((source / "execution_audit.json").read_bytes())
    if audit["results_sha256"] != sha256_bytes(raw):
        raise ValueError("Upstream results differ from the completed execution audit")
    fields = (
        "config", "config_sha256", "sources_sha256", "upstream_fingerprints",
        "environment", "planned_keys",
    )
    if digest({key: manifest[key] for key in fields}) != manifest["identity"]:
        raise ValueError("Upstream manifest identity is invalid")
    if {previous.condition_key(row) for row in rows} != {
        tuple(key) for key in manifest["planned_keys"]
    } or len(rows) != len(manifest["planned_keys"]):
        raise ValueError("Upstream conditions are incomplete or repeated")
    selected = {}
    for model, case_id in product(models, case_ids):
        matches = [
            row for row in rows
            if row["model"] == model and row["case_id"] == case_id
            and row["evidence_policy"] == policy
            and row["protocol"] == "applicability_first" and row["repeat"] == 0
        ]
        if len(matches) != 1:
            raise ValueError("Exactly one prespecified repeat-zero ledger is required")
        row = matches[0]
        stage = row["stages"].get("applicability", {})
        if stage.get("status") != "completed":
            raise ValueError("The prespecified stage-one ledger is unavailable")
        payload = row["input_snapshot"]
        judgment.validate_patient_payload(payload)
        review = judgment.parse_applicability_response(
            stage["attempts"][-1]["raw_response"], payload,
        )
        if review.model_dump(mode="json") != stage["answer"]:
            raise ValueError("Cached ledger differs from reparsed original response")
        selected[model + "/" + case_id] = {
            "payload": payload, "review": review.model_dump(mode="json"),
            "upstream_condition_key": list(previous.condition_key(row)),
            "reference_outcome": row["reference_outcome"],
            "historical_aggregation_status": row.get("stages", {}).get(
                "aggregation", {},
            ).get("status"),
        }
    if (source / "results.jsonl").read_bytes() != raw:
        raise ValueError("Upstream results changed during freezing")
    return selected, {
        "directory": str(source.resolve()), "identity": manifest["identity"],
        "results_sha256": sha256_bytes(raw),
        "manifest_sha256": sha256_bytes((source / "manifest.json").read_bytes()),
        "first_stage_runtime": manifest["environment"]["runtime"],
    }, manifest["config"]


def request_pair(config, model, payload, review):
    requests = {
        mode: judgment.build_aggregation_request(
            {**config, "aggregation_ledger_mode": mode}, model, payload, review,
        ) for mode in MODES
    }
    wires = {mode: json.loads(body["messages"][1]["content"]) for mode, body in requests.items()}
    for mode in MODES:
        for key in payload:
            if wires[mode][key] != wires["full_values"][key]:
                raise ValueError("A supposedly shared patient or source input changed")
    for full, compact in zip(
        wires["full_values"]["proposed_applicability_ledger"],
        wires["field_references"]["proposed_applicability_ledger"], strict=True,
    ):
        if compact != {key: value for key, value in full.items() if key != "referenced_patient_values"}:
            raise ValueError("Ledger interpretation changed during encoding")
    return requests


def validate_rows(rows, planned, manifest, selected, config):
    """Reject altered accepted responses, initial requests, labels or call counts."""
    done = {tuple(row[field] for field in KEY) for row in rows}
    if len(done) != len(rows) or not done <= set(planned):
        raise ValueError("Duplicate or unexpected diagnostic condition")
    for row in rows:
        item = selected[row["model"] + "/" + row["case_id"]]
        review = judgment.ApplicabilityReview.model_validate(item["review"])
        body = request_pair(config, row["model"], item["payload"], review)[row["mode"]]
        if (
            row["experiment_identity"] != manifest["identity"]
            or row["input_sha256"] != digest(item)
            or row["reference_outcome"] != item["reference_outcome"]
            or row["initial_request_sha256"] != digest(body)
            or row["initial_request_bytes"] != len(previous.json_bytes(body))
            or row["status"] not in {"completed", "failed"}
            or not row["attempts"] or row["attempts"][0]["request"] != body
        ):
            raise ValueError("Saved diagnostic identity, input or initial request differs")
        calls = 0
        for attempt in row["attempts"]:
            if (
                attempt["request_sha256"] != digest(attempt["request"])
                or attempt["request_bytes"] != len(previous.json_bytes(attempt["request"]))
            ):
                raise ValueError("Saved diagnostic request fingerprint differs")
            calls += bool(attempt["provider_called"])
            if attempt["status"] == "completed":
                answer = judgment.parse_aggregation_response(
                    attempt["raw_response"], item["payload"], review,
                )
                if answer.model_dump(mode="json") != attempt["answer"]:
                    raise ValueError("Saved accepted answer differs from the raw response")
        if row["model_calls"] != calls:
            raise ValueError("Saved diagnostic call count differs")
        agreement = row["status"] == "completed" and row["answer"][
            "assessment_outcome"
        ] == item["reference_outcome"]
        if row["reference_agreement"] != agreement:
            raise ValueError("Saved diagnostic agreement differs")
        if row["status"] == "completed" and (
            row["attempts"][-1]["status"] != "completed"
            or row["answer"] != row["attempts"][-1]["answer"]
        ):
            raise ValueError("Saved final answer differs from its accepted attempt")
    return done


def render(output, rows, planned, evidence_policy="reference_evidence"):
    metrics = []
    for model, mode in product(sorted({row["model"] for row in rows}), MODES):
        group = [row for row in rows if row["model"] == model and row["mode"] == mode]
        metrics.append({
            "model": model, "mode": mode, "conditions": len(group),
            "accepted": sum(row["status"] == "completed" for row in group),
            "correct": sum(row["reference_agreement"] for row in group),
            "calls": sum(row["model_calls"] for row in group),
            "context_failures": sum("context" in row.get("error", "").lower() for row in group),
            "request_bytes": sum(row["initial_request_bytes"] for row in group),
        })
    transitions = Counter()
    by_key = {tuple(row[field] for field in KEY): row for row in rows}
    for model, case_id, repeat in sorted({
        (row["model"], row["case_id"], row["repeat"]) for row in rows
    }):
        before = by_key.get((model, case_id, "full_values", repeat))
        after = by_key.get((model, case_id, "field_references", repeat))
        if before is None or after is None:
            continue
        if before["status"] != "completed" or after["status"] != "completed":
            transition = before["status"] + "_to_" + after["status"]
        else:
            transition = (
                ("correct" if before["reference_agreement"] else "wrong") + "_to_"
                + ("correct" if after["reference_agreement"] else "wrong")
            )
        transitions[transition] += 1
    result = {
        "recorded": len(rows), "planned": planned,
        "execution_complete": len(rows) == planned,
        "evidence_policy": evidence_policy,
        "metrics": metrics, "paired_transitions": dict(transitions),
        "failures": dict(Counter(row["error"] for row in rows if row["status"] == "failed")),
        "interpretation": (
            "Cached upstream stage-one proposals are identical in both encodings. "
            "Only aggregation is rerun on the declared current runtime. Historical "
            "stage-one costs are excluded. Evidence policy: " + evidence_policy + ". "
            "This is not a retrieval-method comparison. Engineering agreement is not clinical accuracy."
        ),
        "clinical_review": "pending", "production_change": False,
    }
    write_json(output / "summary.json", result)
    table = "".join(
        "<tr>" + "".join(f"<td>{escape(str(value))}</td>" for value in item.values()) + "</tr>"
        for item in metrics
    )
    cards = ""
    for row in rows:
        cards += (
            f'<details><summary>{escape(row["case_id"])} · {escape(row["model"])} · '
            f'{row["mode"]} · repeat {row["repeat"] + 1} · {row["status"]}</summary>'
            f'<p>Request bytes: {row["initial_request_bytes"]}; calls: {row["model_calls"]}</p>'
            "<pre>" + escape(json.dumps({
                "answer": row.get("answer"), "error": row.get("error"),
                "reference_outcome": row["reference_outcome"],
                "source_locations": row.get("criterion_locations"),
            }, ensure_ascii=False, indent=2)) + "</pre></details>"
        )
    html = (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" '
        'content="width=device-width,initial-scale=1"><title>Aggregation encoding comparison</title>'
        '<style>body{font:15px/1.6 system-ui;background:#f4f6f8;color:#243748;max-width:1200px;'
        'margin:40px auto;padding:24px}section,details{background:white;border:1px solid #dce3ea;'
        'padding:18px;margin:14px 0;border-radius:8px}table{width:100%;border-collapse:collapse}'
        'td,th{padding:10px;border-bottom:1px solid #dce3ea;text-align:left}pre{white-space:pre-wrap;'
        'overflow-wrap:anywhere}summary{cursor:pointer}</style><small>OCCUPATIONAL FITNESS PLATFORM</small>'
        f'<h1>Aggregation encoding comparison</h1><p>{len(rows)}/{planned} conditions recorded</p>'
        '<section><p>' + escape(result["interpretation"]) + '</p><table><tr>'
        + "".join(f"<th>{escape(key)}</th>" for key in (list(metrics[0]) if metrics else []))
        + '</tr>' + table + '</table><pre>' + escape(json.dumps(dict(transitions), indent=2))
        + '</pre></section>' + cards
        + '<p><a href="results.jsonl">Raw requests and responses</a> · '
        '<a href="manifest.json">Frozen manifest</a> · <a href="inputs.json">Original inputs</a> · '
        '<a href="summary.json">Metrics</a></p></html>'
    )
    (output / "index.html").write_text(html, encoding="utf-8")
    return result


def run(args):
    selected, upstream, config = inputs_from(
        args.source, args.cases, args.models, args.evidence_policy,
    )
    output = Path(args.output).resolve()
    source = Path(args.source).resolve()
    if output == source or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("Diagnostic output must be isolated from its source")
    if args.repeats < 1:
        raise ValueError("At least one repeat is required")
    config.update(
        expected_runtime_version=args.runtime_version, models=args.models,
        expected_model_digests={key: config["expected_model_digests"][key] for key in args.models},
    )
    planned = list(product(args.models, args.cases, MODES, range(args.repeats)))
    identity_data = {
        "config": config, "upstream": upstream, "inputs_sha256": digest(selected),
        "planned_keys": planned,
        "environment": previous.pinned_environment(config),
        "source_snapshot": previous.source_snapshot(json.dumps(config, sort_keys=True)),
        "tool_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "purpose": "aggregation_encoding_diagnostic", "clinical_review": "pending",
        "evidence_policy": args.evidence_policy,
    }
    manifest = {**identity_data, "identity": digest(identity_data), "production_change": False}
    output.mkdir(parents=True, exist_ok=True)
    lock = output / ".run.lock"
    with lock.open("x", encoding="ascii") as stream:
        stream.write(str(os.getpid()))
    try:
        path = output / "manifest.json"
        if path.exists():
            if not args.resume or json.loads(path.read_bytes()) != json.loads(json.dumps(manifest)):
                raise ValueError("Resume requires an identical frozen diagnostic identity")
            if json.loads((output / "inputs.json").read_bytes()) != selected:
                raise ValueError("Frozen diagnostic inputs changed")
        else:
            if any(path.name != ".run.lock" for path in output.iterdir()):
                raise ValueError("Non-empty diagnostic output has no manifest")
            write_json(path, manifest)
            write_json(output / "inputs.json", selected)
        rows = previous.read_records(output / "results.jsonl")
        done = validate_rows(rows, planned, manifest, selected, config)
        render(output, rows, len(planned), args.evidence_policy)
        added = 0
        # Counterbalance encoding order without running concurrent model jobs.
        for model, case_id, repeat in product(args.models, args.cases, range(args.repeats)):
            item = selected[model + "/" + case_id]
            payload = item["payload"]
            review = judgment.ApplicabilityReview.model_validate(item["review"])
            requests = request_pair(config, model, payload, review)
            for mode in (MODES if repeat % 2 == 0 else tuple(reversed(MODES))):
                key = (model, case_id, mode, repeat)
                if key in done:
                    continue
                if args.max_conditions is not None and added >= args.max_conditions:
                    return render(output, rows, len(planned), args.evidence_policy)
                previous.pinned_environment(config)
                result = experiment.run_stage(
                    config, requests[mode],
                    lambda raw: judgment.parse_aggregation_response(raw, payload, review),
                    lambda answer: {
                        "criterion_locations": passage_judgment.criterion_locations(answer, payload),
                        "output_consistency_flags": passage_judgment.output_consistency_flags(answer, payload),
                    },
                )
                result.pop("proposal", None)
                row = {
                    **dict(zip(KEY, key, strict=True)), **result,
                    "experiment_identity": manifest["identity"],
                    "input_sha256": digest(item),
                    "initial_request_bytes": len(previous.json_bytes(requests[mode])),
                    "initial_request_sha256": digest(requests[mode]),
                    "model_calls": sum(bool(a["provider_called"]) for a in result["attempts"]),
                    "reference_outcome": item["reference_outcome"],
                    "reference_agreement": result["status"] == "completed" and result["answer"][
                        "assessment_outcome"
                    ] == item["reference_outcome"],
                }
                if previous.read_records(output / "results.jsonl") != rows:
                    raise ValueError("Diagnostic records changed during execution")
                with (output / "results.jsonl").open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
                rows.append(row)
                done.add(key)
                added += 1
                render(output, rows, len(planned), args.evidence_policy)
                print(f"Recorded {len(rows)}/{len(planned)} {key}: {row['status']}", flush=True)
        result = render(output, rows, len(planned), args.evidence_policy)
        validate_rows(rows, planned, manifest, selected, config)
        if previous.source_snapshot(json.dumps(config, sort_keys=True)) != manifest["source_snapshot"]:
            raise ValueError("Diagnostic source snapshot changed before completion")
        if previous.pinned_environment(config) != manifest["environment"]:
            raise ValueError("Diagnostic environment changed before completion")
        write_json(output / "execution_audit.json", {
            "utc": datetime.now(timezone.utc).isoformat(),
            "results_sha256": sha256_bytes((output / "results.jsonl").read_bytes()),
            "manifest_sha256": sha256_bytes((output / "manifest.json").read_bytes()),
            "planned_condition_keys_complete": done == set(planned),
            "conditions": len(rows), "model_calls": sum(row["model_calls"] for row in rows),
            "source_snapshot_matches_at_completion": True,
            "runtime_and_model_pins_match_at_completion": True,
            "cached_first_stage_calls": 0, "production_change": False,
        })
        return result
    finally:
        lock.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--cases", nargs="+", required=True)
    parser.add_argument("--models", nargs="+", default=["llama3:8b", "qwen3.5:4b-q4_K_M"])
    parser.add_argument("--runtime-version", required=True)
    parser.add_argument(
        "--evidence-policy", choices=["module_query", "reference_evidence"],
        default="reference_evidence",
    )
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-conditions", type=int)
    print(json.dumps(run(parser.parse_args()), indent=2))
