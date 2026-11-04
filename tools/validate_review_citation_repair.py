"""Audit the actual screenshot regression without relabelling model judgments."""

from __future__ import annotations

import argparse
import json
import shutil

from tools.complex_ten_contract import ROOT, pin, read, write_json
from tools.serve_retrieval_judgments import DEFAULT

STUDY = ROOT / "outputs/experiments/review_citation_repair_20261104"
FAILED_ID = "8c984a40c3ed7c09e229757fb78b467edd4c41de48377ca2df8aaa5cfbc038d6"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish-to-main", action="store_true")
    args = parser.parse_args()
    matrix = read(STUDY / "final_matrix.json")
    records = [read(STUDY / "final_live/records" / (row["id"] + ".json")) for row in matrix]
    if any(r["status"] not in {"completed", "requires_review"} for r in records):
        raise ValueError("The screenshot regression is not complete")
    previous = DEFAULT / "records" / (FAILED_ID + ".json")
    archived = STUDY / "before" / previous.relative_to(ROOT)
    if pin(previous) != pin(archived):
        raise ValueError("The original failed observation changed")
    old = read(previous)
    comparisons = []
    for r in records:
        if r["payload"]["nurse_note"] != old["payload"]["nurse_note"]:
            raise ValueError("The original nurse note changed")
        if r["payload"]["guideline_evidence"] != old["payload"]["guideline_evidence"][:r["condition"]["top_k"]]:
            raise ValueError("The supplied whole original passages changed")
        for check in r["result"]["checks"]:
            if check["applicability"] == "established" and not check["patient_span"]:
                raise ValueError("An established check has no original patient reference")
        comparisons.append({"id": r["id"], "condition": r["condition"], "status": r["status"],
            "fitness": r["result"]["fitness"], "outcome": r["result"]["outcome"],
            "seconds": r["seconds"], "model_calls": r["model_calls"],
            "supplied_originals": len(r["payload"]["guideline_evidence"]),
            "validation_warnings": r["result"]["validation_warnings"],
            "actual_prompt_tokens": r["raw_response"]["prompt_eval_count"],
            "configured_context": r["request"]["options"]["num_ctx"],
            "clinical_review_status": "pending"})
        if args.publish_to_main:
            source = STUDY / "final_live/records" / (r["id"] + ".json")
            target = DEFAULT / "records" / source.name
            if target.exists() and pin(target) != pin(source):
                raise ValueError("Do not overwrite a different observed review")
            if not target.exists():
                shutil.copy2(source, target)
    implementation = [
        "src/occupational_fitness_rag/evaluation/retrieval_judgment.py",
        "tools/serve_retrieval_judgments.py",
        "src/occupational_fitness_rag/web/static/retrieval_judgment.js",
        "tests/test_retrieval_judgment.py", "tests/retrieval_judgment_client.test.cjs",
        "docs/retrieval_model_judgment.md", "tools/validate_review_citation_repair.py",
    ]
    for name in implementation:
        target = STUDY / "implementation" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    summary = {"old_failed_record_id": FAILED_ID, "old_failure_sha256": pin(previous),
        "old_error": old["error"], "old_failed_record_preserved": True,
        "same_original_note_and_ranked_evidence": True, "conditions": len(records),
        "reference_contract_failures": 0, "clinical_accuracy_claim": False,
        "interpretation": "Reference structure now passes for this regression. "
            "Model conclusions can still be wrong; consistency warnings remain visible.",
        "repair_path_evidence": "Bounded repair and immutable manual retry are covered by unit tests. "
            "These four natural model conditions passed reference validation on their first new call.",
        "rows": comparisons, "implementation": {name: pin(ROOT / name) for name in implementation}}
    write_json(STUDY / "validation_summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in {"rows", "implementation"}}, indent=2))


if __name__ == "__main__":
    main()
