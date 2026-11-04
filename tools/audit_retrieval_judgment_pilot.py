"""Audit two case-level proposals against unchanged legacy engineering references.

Labels are read after all model calls and never supplied to the review service.
This small, previously inspected development set is not a clinical accuracy test.
"""

from __future__ import annotations

import json
from collections import Counter

from occupational_fitness_rag.evaluation.retrieval_judgment import llama_token_counter
from tools.complex_ten_contract import ROOT, pin, read, write_json
from tools.serve_retrieval_judgments import DEFAULT


def main():
    summary = read(DEFAULT / "integration_summary.json")
    if not summary["all_terminal"]:
        raise ValueError("Complete the integration matrix before opening reference labels")
    labels_path = ROOT / "data/cases/gold/validation_complex_expectations.json"
    labels = read(labels_path)
    comparisons = []
    for row in summary["rows"]:
        if row["module"] != "all_requested":
            continue
        record = read(DEFAULT / "records" / (row["id"] + ".json"))
        source = ROOT / "data/cases/validation_nurse_notes" / (row["case_id"] + ".txt")
        if source.read_text(encoding="utf-8") != record["payload"]["nurse_note"]:
            raise ValueError("Case note differs from its frozen model input")
        result = row.get("result") or {}
        comparisons.append({
            "case_id": row["case_id"], "condition": row["condition"],
            "record_id": row["id"], "status": row["status"],
            "reference_outcome": labels[row["case_id"]]["overall_outcome"],
            "model_outcome": result.get("outcome"),
            "matches_legacy_engineering_reference": result.get("outcome") ==
                labels[row["case_id"]]["overall_outcome"] if result else None,
            "original_input_sha256": pin(source),
            "supplied_source_ids": [s["source_id"] for s in record["payload"]["guideline_evidence"]],
            "review_warnings": result.get("validation_warnings", []),
        })
    accepted = [r for r in comparisons if r["model_outcome"]]
    write_json(DEFAULT / "pilot_reference_audit.json", {
        "cohort": "Two previously inspected development cases; not independent validation",
        "reference_version_sha256": pin(labels_path), "clinical_review_status": "pending",
        "planned": len(comparisons), "returned_proposals": len(accepted),
        "blocked_conditions": len(comparisons) - len(accepted),
        "legacy_reference_matches": sum(r["matches_legacy_engineering_reference"] for r in accepted),
        "rows": comparisons,
        "interpretation": "Contract-valid output is not evidence of fitness correctness. "
            "Reconcile reference semantics and inspect missing/unused decisive evidence before "
            "any accuracy or production replacement claim. Do not tune against these answers.",
    })
    counter_path = ROOT / "outputs/experiments/retrieval_judgments_tokenizer/llama3.json"
    count = llama_token_counter(read(counter_path))
    budget = []
    for row in summary["rows"]:
        r = read(DEFAULT / "records" / (row["id"] + ".json"))
        body, raw = r.get("request"), r.get("raw_response")
        if not body or not raw:
            continue
        combined = "".join(m["content"] for m in body["messages"]) + json.dumps(body["format"])
        bound = (count(combined) if body["model"].startswith("llama")
                 else len(combined.encode())) + 256
        actual = raw["prompt_eval_count"]
        budget.append({"record_id": r["id"], "model": body["model"],
            "conservative_input_bound": bound, "actual_prompt_tokens": actual,
            "within_estimate": actual <= bound,
            "within_reserved_context": bound + body["options"]["num_predict"] <=
                body["options"]["num_ctx"]})
    write_json(DEFAULT / "token_budget_audit.json", budget)
    print(json.dumps({"case_level_conditions": len(comparisons), "returned": len(accepted),
                      "legacy_reference_matches": sum(r["matches_legacy_engineering_reference"]
                                                       for r in accepted),
                      "context_audits": len(budget),
                      "all_within_context": all(r["within_estimate"] and r["within_reserved_context"]
                                                for r in budget),
                      "status": dict(Counter(r["status"] for r in summary["rows"]))}, indent=2))


if __name__ == "__main__":
    main()
