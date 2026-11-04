"""Audit a stopped, complete applicability comparison without model inference."""

import argparse
import json
from collections import Counter
from pathlib import Path

from occupational_fitness_rag.evaluation import applicability_comparison as experiment
from occupational_fitness_rag.evaluation import applicability_judgment, passage_judgment
from occupational_fitness_rag.evaluation import passage_comparison as previous
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json


def audit(directory, tests_at_completion=None, tests_at_freeze=None):
    directory = Path(directory)
    if (directory / ".run.lock").exists():
        raise ValueError("The writer must stop before its execution audit")
    raw = (directory / "results.jsonl").read_bytes()
    if not raw or not raw.endswith(b"\n"):
        raise ValueError("Missing results or incomplete JSONL tail")
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    manifest = json.loads((directory / "manifest.json").read_bytes())
    snapshot = json.loads((directory / "source_snapshot.json").read_bytes())
    config = manifest["config"]
    experiment.validate_config(config)
    identity_fields = (
        "config",
        "config_sha256",
        "sources_sha256",
        "upstream_fingerprints",
        "environment",
        "planned_keys",
    )
    if (
        digest({key: manifest[key] for key in identity_fields}) != manifest["identity"]
        or digest(snapshot) != manifest["sources_sha256"]
        or sha256_bytes(snapshot["config_text"].encode("utf-8")) != manifest["config_sha256"]
    ):
        raise ValueError("Manifest or saved source snapshot identity differs")
    keys = [previous.condition_key(row) for row in rows]
    if len(keys) != len(set(keys)) or set(keys) != {tuple(key) for key in manifest["planned_keys"]}:
        raise ValueError("Incomplete, repeated or unexpected condition keys")
    frozen = experiment.load_retrieval(config)
    if frozen["fingerprints"] != manifest["upstream_fingerprints"]:
        raise ValueError("Upstream frozen artifacts changed")
    experiment.validate_saved_rows(rows, manifest, frozen)
    accepted_attempts = 0
    for row in rows:
        payload = row.get("input_snapshot")
        stages = row.get("stages", {})
        for name, stage in stages.items():
            for attempt in stage["attempts"]:
                if attempt["status"] != "completed":
                    continue
                if name == "applicability":
                    parsed = applicability_judgment.parse_applicability_response(
                        attempt["raw_response"], payload
                    )
                elif name == "aggregation":
                    ledger = applicability_judgment.ApplicabilityReview.model_validate(
                        stages["applicability"]["answer"]
                    )
                    parsed = applicability_judgment.parse_aggregation_response(
                        attempt["raw_response"], payload, ledger, config=config
                    )
                else:
                    parsed = passage_judgment.parse_response(
                        attempt["raw_response"], payload, "passage_selection"
                    )
                if parsed.model_dump(mode="json") != attempt["answer"]:
                    raise ValueError("Accepted answer differs from reparsed raw output")
                accepted_attempts += 1
    current = previous.source_snapshot(snapshot["config_text"])
    environment = previous.pinned_environment(config)
    source_matches = digest(current) == manifest["sources_sha256"]
    if not source_matches or environment != manifest["environment"]:
        raise ValueError("Package or local model pins changed since the frozen run")
    audit_data = {
        "planned_condition_keys_complete": True,
        "source_snapshot_matches_at_completion": source_matches,
        "runtime_and_model_pins_match_at_completion": True,
        "results_sha256": sha256_bytes(raw),
        "manifest_sha256": sha256_bytes((directory / "manifest.json").read_bytes()),
        "tool_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "accepted_attempts_reparsed": accepted_attempts,
        "conditions": len(rows),
        "unique_cases": len({row["case_id"] for row in rows}),
        "condition_status": dict(Counter(row["status"] for row in rows)),
        "model_calls": sum(row["model_calls"] for row in rows),
        "tests_at_completion": tests_at_completion,
        "tests_at_freeze": tests_at_freeze,
        "cost_environment_note": (
            "Observed workstation costs; engineering and read-only analysis work may overlap. "
            "These are not isolated latency benchmarks."
        ),
        "production_change": False,
    }
    write_json(directory / "execution_audit.json", audit_data)
    return audit_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    parser.add_argument("--tests-at-completion", type=int)
    parser.add_argument("--tests-at-freeze", type=int)
    args = parser.parse_args()
    print(json.dumps(audit(args.directory, args.tests_at_completion, args.tests_at_freeze), indent=2))
