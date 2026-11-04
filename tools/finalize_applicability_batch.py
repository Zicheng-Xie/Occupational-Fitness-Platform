"""Write a compact completion note after a one-time replay pipeline finishes."""

import argparse
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from occupational_fitness_rag.provenance import sha256_bytes, write_json
from tools.compare_fact_sensitivity import completed


def summarize(directory, expected_sha256=None):
    run = completed(directory)
    if expected_sha256 is not None and run["raw_sha256"] != expected_sha256:
        raise ValueError("Completed batch state does not pin these result bytes")
    rows = run["rows"]
    summary = json.loads((Path(directory) / "summary.json").read_bytes())
    return {
        "directory": str(directory),
        "identity": run["manifest"]["identity"],
        "raw_results_sha256": run["raw_sha256"],
        "conditions": len(rows),
        "distinct_cases": len({row["case_id"] for row in rows}),
        "status_counts": dict(Counter(row["status"] for row in rows)),
        "failure_reasons": dict(Counter(row["error"] for row in rows if row["status"] == "failed")),
        "cost": summary["cost"],
        "metrics": [
            item for item in summary["metrics"] if item["stage"] == "final_with_structural_repairs"
        ],
        "paired_transition_counts": summary["paired_transition_counts"],
    }


def finish(state_path, original_dir, sensitivity_dir, pilot_dir, output_path):
    state = json.loads(Path(state_path).read_bytes())
    if state["stage"] != "completed":
        raise ValueError("All serial model runs and report stages must finish first")
    original = summarize(original_dir, state["first_results_sha256"])
    sensitivity = summarize(sensitivity_dir, state["second_results_sha256"])
    pilot = summarize(pilot_dir)
    pilot_gate = json.loads((Path(pilot_dir) / "pilot_gate.json").read_bytes())
    if pilot_gate["raw_results_sha256"] != pilot["raw_results_sha256"]:
        raise ValueError("Pilot gate pins different original results")
    fact_analysis = json.loads(
        (Path(sensitivity_dir) / "fact_sensitivity_analysis.json").read_bytes()
    )
    interruptions = []
    for directory in [
        Path("outputs/experiments/applicability_comparison_full33_original"),
        Path("outputs/experiments/applicability_comparison_full33_original_v2"),
    ]:
        audit = json.loads((directory / "interruption_audit.json").read_bytes())
        if sha256_bytes((directory / "results.jsonl").read_bytes()) != audit["results_sha256"]:
            raise ValueError("Preserved interrupted prefix changed")
        interruptions.append({"directory": str(directory), **audit})
    report = {
        "status": "completed",
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "original_facts": original,
        "source_literal_sensitivity": sensitivity,
        "main_batch_conditions": original["conditions"] + sensitivity["conditions"],
        "pilot": pilot,
        "pilot_gate": pilot_gate,
        "fact_sensitivity_transitions": fact_analysis["transition_counts"],
        "preserved_interrupted_prefixes": interruptions,
        "known_recorded_calls_this_round": (
            original["cost"]["model_calls"]
            + sensitivity["cost"]["model_calls"]
            + pilot["cost"]["model_calls"]
            + sum(item["known_recorded_model_calls"] for item in interruptions)
        ),
        "unrecorded_interruption_costs": "unknown; not included in known recorded totals",
        "clinical_accuracy": None,
        "production_change": False,
        "remaining_requirements": [
            "Independent review of source support, patient applicability and licence scope.",
            "Clinical review of engineering labels and independently sealed cases.",
            "Repair source table context in a separately versioned corpus.",
            "Rebuild graph indexes and compare all six retrieval methods on identical inputs.",
        ],
        "interpretation": (
            "Engineering reference agreement is not clinical accuracy. The pilot contains "
            "accepted classification regressions despite valid provenance. The fact-only "
            "sensitivity holds historical queries and original evidence fixed; it does not "
            "evaluate new retrieval or authorize a production change. Repeats are not new patients."
        ),
    }
    write_json(Path(output_path), report)
    return {"status": report["status"], "main_batch_conditions": report["main_batch_conditions"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--helper-state", required=True)
    parser.add_argument("--original", required=True)
    parser.add_argument("--sensitivity", required=True)
    parser.add_argument("--pilot", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--wait", action="store_true")
    args = parser.parse_args()
    while args.wait:
        state = json.loads(Path(args.helper_state).read_bytes())
        if state["stage"] == "failed":
            raise ValueError("Serial pipeline failed; a completed note was not generated")
        if state["stage"] == "completed":
            break
        time.sleep(30)
    print(
        json.dumps(
            finish(args.helper_state, args.original, args.sensitivity, args.pilot, args.output)
        )
    )
