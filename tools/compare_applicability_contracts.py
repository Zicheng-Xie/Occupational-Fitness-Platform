"""Compare completed contract revisions with exact upstream and control-prompt checks."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json

KEYS = ("model", "case_id", "evidence_policy", "protocol", "repeat")


def load(directory):
    directory = Path(directory)
    if (directory / ".run.lock").exists():
        raise ValueError("Comparison revisions must have stopped writers")
    raw = (directory / "results.jsonl").read_bytes()
    audit = json.loads((directory / "execution_audit.json").read_text(encoding="utf-8"))
    if not raw.endswith(b"\n") or sha256_bytes(raw) != audit["results_sha256"]:
        raise ValueError("Results differ from the completed snapshot")
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    keyed = {tuple(row[key] for key in KEYS): row for row in rows}
    if len(keyed) != len(rows) or set(keyed) != {tuple(key) for key in manifest["planned_keys"]}:
        raise ValueError("Incomplete or duplicate planned conditions")
    source = json.loads((directory / "source_snapshot.json").read_text(encoding="utf-8"))
    if digest(source) != manifest["sources_sha256"] or any(
        row["experiment_identity"] != manifest["identity"]
        or digest(row["input_snapshot"]) != row["input_sha256"]
        for row in rows
    ):
        raise ValueError("Saved source or patient-input identity differs")
    return {"rows": keyed, "manifest": manifest, "source": source, "sha256": sha256_bytes(raw)}


def compare(before_dir, after_dir):
    before, after = load(before_dir), load(after_dir)
    if before["rows"].keys() != after["rows"].keys():
        raise ValueError("Revision condition sets differ")
    for field in ["upstream_fingerprints", "environment", "corpus_sha256"]:
        if before["manifest"][field] != after["manifest"][field]:
            raise ValueError("Revision comparison changes an upstream identity: " + field)
    transitions, controls = [], []
    groups = defaultdict(list)
    for key, new in after["rows"].items():
        old = before["rows"][key]
        if any(
            old[field] != new[field]
            for field in ["input_sha256", "input_snapshot", "model_digest", "reference_outcome"]
        ):
            raise ValueError(
                "Revision pair changes a patient, original evidence, judge or reference"
            )
        if key[3] == "passage_selection":
            same = old["attempts"][0]["request_sha256"] == new["attempts"][0]["request_sha256"]
            if not same:
                raise ValueError("The contemporary control's first request changed")
            controls.append(
                {
                    "condition": list(key),
                    "first_request_identical": same,
                    "outcome_changed": old.get("answer", {}).get("assessment_outcome")
                    != new.get("answer", {}).get("assessment_outcome"),
                }
            )
        else:
            a, b = old["status"] == "completed", new["status"] == "completed"
            if a and b:
                kind = {
                    (False, True): "accepted_wrong_to_correct",
                    (True, False): "accepted_correct_to_wrong",
                    (True, True): "accepted_both_correct",
                    (False, False): "accepted_both_wrong",
                }[old["reference_agreement"], new["reference_agreement"]]
            else:
                kind = {
                    (False, True): "failed_to_valid",
                    (True, False): "valid_to_failed",
                    (False, False): "both_failed",
                }[a, b]
            transitions.append(
                {
                    "condition": list(key),
                    "transition": kind,
                    "before_outcome": old.get("answer", {}).get("assessment_outcome"),
                    "after_outcome": new.get("answer", {}).get("assessment_outcome"),
                    "reference_outcome": new["reference_outcome"],
                }
            )
        for revision, row in [("original_contract", old), ("program_bound_slots", new)]:
            groups[revision, key[0], key[2], key[3]].append(row)
    metrics = [
        {
            "revision": revision,
            "model": model,
            "evidence_policy": policy,
            "protocol": protocol,
            "conditions": len(group),
            "valid": sum(row["status"] == "completed" for row in group),
            "engineering_reference_agreements": sum(row["reference_agreement"] for row in group),
            "model_calls": sum(row["model_calls"] for row in group),
            "seconds": sum(row["seconds"] for row in group),
        }
        for (revision, model, policy, protocol), group in sorted(groups.items())
    ]
    old_sources, new_sources = (
        before["source"]["first_party_source"],
        after["source"]["first_party_source"],
    )
    source_changes = [
        name
        for name in sorted(set(old_sources) | set(new_sources))
        if old_sources.get(name, {}).get("sha256") != new_sources.get(name, {}).get("sha256")
    ]
    report = {
        "before_results_sha256": before["sha256"],
        "after_results_sha256": after["sha256"],
        "tool_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "same_upstream_inputs_and_judge_pins": True,
        "changed_package_sources": source_changes,
        "control_first_requests_identical": len(controls),
        "control_recorded_outcome_changes": sum(item["outcome_changed"] for item in controls),
        "intervention_transitions": dict(Counter(item["transition"] for item in transitions)),
        "interpretation": "A first-stage schema, reference-binding and prompt-contract intervention, not a retrieval change or isolated JSON-order test. Repeats are not independent patients; format recovery is separate from accepted wrong-to-correct change. Clinical correctness remains unestablished.",
        "metrics": metrics,
        "pairs": transitions,
        "controls": controls,
    }
    write_json(Path(after_dir) / "contract_revision_comparison.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    report = compare(**{key + "_dir": value for key, value in vars(parser.parse_args()).items()})
    print(
        json.dumps(
            {
                key: report[key]
                for key in [
                    "control_first_requests_identical",
                    "control_recorded_outcome_changes",
                    "intervention_transitions",
                ]
            }
        )
    )
