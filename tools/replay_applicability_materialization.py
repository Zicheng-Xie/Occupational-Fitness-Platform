"""Replay preserved stage-one responses through parsing, provenance and request building."""

import argparse
import json
from pathlib import Path

from occupational_fitness_rag.evaluation import applicability_judgment as api
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json


def replay(directories, output):
    checks, pins = [], {}
    for directory in map(Path, directories):
        raw = (directory / "results.jsonl").read_bytes()
        if not raw.endswith(b"\n"):
            raise ValueError("Historical prefix has an incomplete tail")
        manifest = json.loads((directory / "manifest.json").read_bytes())
        pins[str(directory)] = sha256_bytes(raw)
        for row in map(json.loads, raw.decode("utf-8").splitlines()):
            stage = row.get("stages", {}).get("applicability")
            if not stage:
                continue
            payload, attempt = row["input_snapshot"], stage["attempts"][0]
            if digest(payload) != row["input_sha256"]:
                raise ValueError("Historical patient payload changed")
            body = api.build_applicability_request(manifest["config"], row["model"], payload)
            if digest(body) != attempt["request_sha256"]:
                raise ValueError("Initial applicability request changed")
            proposal = api.parse_applicability_response(attempt["raw_response"], payload)
            locations = api.review_locations(proposal, payload)
            aggregation = api.build_aggregation_request(
                manifest["config"], row["model"], payload, proposal
            )
            size = len(json.dumps(aggregation, allow_nan=False).encode("utf-8"))
            if size > manifest["config"]["request_max_bytes"]:
                raise ValueError("Aggregation request exceeds its frozen byte budget")
            saved = attempt.get("criterion_locations")
            if saved is not None and locations != saved:
                raise ValueError("A previously accepted original source location changed")
            checks.append(
                {
                    "directory": str(directory),
                    "case_id": row["case_id"],
                    "model": row["model"],
                    "policy": row["evidence_policy"],
                    "repeat": row["repeat"],
                    "historical_status": row["status"],
                    "initial_request_unchanged": True,
                    "derived_reference_counts": [
                        len(item.fact_fields) for item in proposal.passage_checks
                    ],
                    "resolved_source_count": len(locations),
                    "aggregation_request_bytes": size,
                    "previous_locations_compared": saved is not None,
                    "aggregation_executed": False,
                }
            )
    report = {
        "historical_results_sha256": pins,
        "checks": checks,
        "stage_one_responses_replayed": len(checks),
        "previously_failed_conditions_replayed": sum(
            item["historical_status"] == "failed" for item in checks
        ),
        "maximum_derived_reference_count": max(
            n for item in checks for n in item["derived_reference_counts"]
        ),
        "new_model_calls": 0,
        "original_rows_modified": False,
        "tool_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "parser_sha256": sha256_bytes(Path(api.__file__).read_bytes()),
        "interpretation": "Historical first responses are replayed through parsing, original-source resolution and aggregation request building. No final historical judgment is accepted or changed; a real two-stage model pilot remains required.",
    }
    write_json(Path(output), report)
    return {key: value for key, value in report.items() if key != "checks"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", nargs="+")
    parser.add_argument("--output", default=".runtime/union_full_path_regression.json")
    args = parser.parse_args()
    print(json.dumps(replay(args.directories, args.output), indent=2))
