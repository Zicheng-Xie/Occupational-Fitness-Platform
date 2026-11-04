"""Measure request bytes on frozen ledgers without invoking a judge or tokenizer."""

import argparse
import json
import statistics
from collections import Counter
from html import escape
from pathlib import Path

from occupational_fitness_rag.evaluation import applicability_judgment as judgment
from occupational_fitness_rag.evaluation import passage_comparison as previous
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json
from tools.compare_ledger_encoding import request_pair


def audit(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output or source.is_relative_to(output) or output.is_relative_to(source):
        raise ValueError("Request audit must be isolated from its source experiment")
    if (source / ".run.lock").exists():
        raise ValueError("Stop the upstream writer before this diagnostic")
    raw = (source / "results.jsonl").read_bytes()
    execution = json.loads((source / "execution_audit.json").read_bytes())
    if execution["results_sha256"] != sha256_bytes(raw):
        raise ValueError("Results differ from the execution audit")
    manifest = json.loads((source / "manifest.json").read_bytes())
    config = manifest["config"]
    records = []
    for row in previous.read_records(source / "results.jsonl"):
        stage = row.get("stages", {}).get("applicability", {})
        if stage.get("status") != "completed":
            continue
        payload = row["input_snapshot"]
        review = judgment.parse_applicability_response(
            stage["attempts"][-1]["raw_response"], payload,
        )
        if review.model_dump(mode="json") != stage["answer"]:
            raise ValueError("Stored ledger differs from its original response")
        requests = request_pair(config, row["model"], payload, review)
        original = row.get("stages", {}).get("aggregation", {}).get("attempts", [])
        if original and requests["full_values"] != original[0]["request"]:
            raise ValueError("Full-value request no longer matches its historical bytes")
        sizes = {key: len(previous.json_bytes(body)) for key, body in requests.items()}
        records.append({
            "condition_key": list(previous.condition_key(row)),
            "request_bytes": sizes,
            "bytes_saved": sizes["full_values"] - sizes["field_references"],
            "reduction_percent": 100 * (
                1 - sizes["field_references"] / sizes["full_values"]
            ),
            "historical_context_failure": "context" in row.get("error", "").lower(),
            "requests_sha256": {key: digest(body) for key, body in requests.items()},
        })
    if (source / "results.jsonl").read_bytes() != raw:
        raise ValueError("Source results changed during diagnostic")
    if not records:
        raise ValueError("No accepted first-stage proposals to inspect")
    result = {
        "source_results_sha256": sha256_bytes(raw),
        "source_identity": manifest["identity"],
        "tool_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "current_package_snapshot_sha256": digest(previous.source_snapshot("")),
        "ledger_conditions": len(records),
        "original_facts_and_complete_passages_preserved": True,
        "model_interpretations_preserved": True,
        "historical_initial_full_value_requests_match": True,
        "historical_context_failures": sum(row["historical_context_failure"] for row in records),
        "shorter_requests": sum(row["bytes_saved"] > 0 for row in records),
        "reduction_percent_median": statistics.median(row["reduction_percent"] for row in records),
        "reduction_percent_min": min(row["reduction_percent"] for row in records),
        "reduction_percent_max": max(row["reduction_percent"] for row in records),
        "models": dict(Counter(row["condition_key"][0] for row in records)),
        "records": records, "model_calls": 0, "production_change": False,
        "interpretation": (
            "Serialized byte reduction only. No token counts or model outcomes "
            "are inferred from bytes; context safety requires a real-model comparison."
        ),
    }
    output.mkdir(parents=True, exist_ok=True)
    path = output / "audit.json"
    if path.exists() and json.loads(path.read_bytes()) != result:
        raise ValueError("An existing request audit differs; preserve it and use a new output")
    write_json(path, result)
    cards = "".join(
        "<tr><td>" + escape(" / ".join(map(str, row["condition_key"]))) + "</td><td>"
        + str(row["request_bytes"]["full_values"]) + "</td><td>"
        + str(row["request_bytes"]["field_references"]) + "</td><td>"
        + f'{row["reduction_percent"]:.1f}%' + "</td></tr>" for row in records
    )
    html = (
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>Ledger encoding request audit</title>'
        '<style>body{font:15px/1.6 system-ui;color:#243748;margin:40px}table{border-collapse:collapse}'
        'td,th{padding:10px;border-bottom:1px solid #dce3ea;text-align:left}</style>'
        '<small>OCCUPATIONAL FITNESS PLATFORM</small><h1>Ledger encoding request audit</h1><p>'
        + escape(result["interpretation"]) + '</p><p>'
        + f'{len(records)} frozen ledgers; median byte reduction: {result["reduction_percent_median"]:.1f}%.'
        + ' All original facts, patient quotations and guideline passages are unchanged.</p>'
        '<p><a href="audit.json">Data and request fingerprints</a></p><table><tr><th>Condition</th>'
        '<th>Full values (bytes)</th><th>Field references (bytes)</th><th>Reduction</th></tr>'
        + cards + '</table></html>'
    )
    (output / "index.html").write_text(html, encoding="utf-8")
    return {key: value for key, value in result.items() if key != "records"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.source, args.output), indent=2))
