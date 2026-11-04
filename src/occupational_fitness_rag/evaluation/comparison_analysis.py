"""Supplemental disease, outcome and evidence-review exports for comparison runs."""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from occupational_fitness_rag.evaluation.comparison_completion import audit_completion
from occupational_fitness_rag.evaluation.comparison_error_audit import export_error_audit
from occupational_fitness_rag.evaluation.comparison_snapshot import read_recorded_rows
from occupational_fitness_rag.evaluation.judgment_comparison import summarize
from occupational_fitness_rag.provenance import write_json


def export_analysis(output: Path, checkpoint=None):
    summary_path = output / "summary.json"
    summary = (
        checkpoint
        if checkpoint is not None
        else (json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {})
    )
    path = output / "results.jsonl"
    rows = read_recorded_rows(path)
    rows = rows[: summary.get("recorded_runs", len(rows))]
    disease_metrics = []
    for module in sorted({r["module"] for r in rows}):
        disease_metrics.extend(
            dict(metric, module=module)
            for metric in summarize([r for r in rows if r["module"] == module])["metrics"]
        )
    write_json(output / "disease_metrics.json", disease_metrics)
    labels = json.loads((output / "label_audit.json").read_text(encoding="utf-8"))
    disputed = {r["case_id"] for r in labels if not r["matches_current_rules"]}
    upstream_path = output / "upstream_audit.json"
    upstream = (
        json.loads(upstream_path.read_text(encoding="utf-8")) if upstream_path.exists() else None
    )
    clean = [r for r in rows if r["case_id"] not in disputed]
    write_json(
        output / "label_consistent_sensitivity.json",
        {
            "excluded_case_ids": sorted(disputed),
            "reason": "Existing fixture differs from current frozen rules; fixed labels are not rewritten",
            "warning": "This sensitivity subset is not a replacement reference standard. Differences can originate in upstream fact quarantine; do not presume incorrect reference labels.",
            "upstream_audit": upstream,
            "summary": summarize(clean) if clean else {},
        },
    )
    outcomes = Counter(
        (r["cohort"], r["expected_outcome"])
        for r in json.loads((output / "labels.json").read_text(encoding="utf-8"))
    )
    write_json(
        output / "reference_distribution.json",
        [
            {"cohort": cohort, "reference_outcome": outcome, "cases": count}
            for (cohort, outcome), count in sorted(outcomes.items())
        ],
    )
    retrieval_path = output / "retrieval.json"
    retrieval = (
        json.loads(retrieval_path.read_text(encoding="utf-8")) if retrieval_path.exists() else []
    )
    costs = []
    for method in sorted({r["method"] for r in retrieval}):
        calls = [r for r in retrieval if r["method"] == method]
        costs.append(
            {
                "method": method,
                "retrieval_calls": len(calls),
                "retrieval_failures": sum(r["status"] != "completed" for r in calls),
                "retrieval_seconds": sum(
                    r.get("retrieval_seconds", r.get("seconds", 0)) for r in calls
                ),
                "timing_scope": "Worker retrieval calls; index construction reported separately",
            }
        )
    index_records = []
    for path in (output / "indexes").rglob("index_complete.json"):
        index_records.append(
            {
                "index_path": str(path.relative_to(output)),
                **json.loads(path.read_text(encoding="utf-8")),
            }
        )
    write_json(
        output / "costs.json",
        {
            "retrieval": costs,
            "indexes": index_records,
            "judgment_calls": len(rows),
            "judgment_seconds": sum(r["seconds"] for r in rows),
            "graph_llm_calls": None,
            "graph_call_count_status": "Framework logs retained; exact counts not normalized",
            "framework_reported_counters": json.loads(
                (output / "framework_cost_audit.json").read_text(encoding="utf-8")
            )
            if (output / "framework_cost_audit.json").exists()
            else None,
        },
    )
    manifest_path = output / "manifest.json"
    repeats = (
        json.loads(manifest_path.read_text(encoding="utf-8"))["config"]["repeats"]
        if manifest_path.exists()
        else 3
    )
    export_error_audit(output, rows, disputed, repeats)
    native_methods = {"vector", "bm25", "hybrid", "graph_local", "lightrag", "graphrag"}
    ranking = sorted(
        [
            r
            for r in summary.get("metrics", [])
            if r["cohort"] == "engineering"
            and r["model"] == "llama3:8b"
            and r["method"] in native_methods
        ],
        key=lambda r: (-r["agreement_all_runs"], r["failures"], r["mean_seconds"]),
    )
    completed = summary.get("execution_status") == "completed"
    write_json(
        output / "recommendation.json",
        {
            "status": "pending_support_and_label_review" if completed else "experiment_running",
            "production_change": False,
            "primary_engineering_ranking": ranking if completed else [],
            "recommendation": (
                "Inspect paired errors, label sensitivity, complex-cohort replication and explanation support "
                "before retaining or replacing production retrieval. Ranking alone does not establish superiority."
                if completed
                else "No method recommendation before all planned calls are recorded."
            ),
            "label_discrepancies": sorted(disputed),
            "clinical_accuracy": None,
        },
    )
    review = {}
    for r in rows:
        for source in r["input_snapshot"]["guideline_evidence"]:
            key = r["case_id"], r["method"], source["source_id"]
            review[key] = {
                "case_id": r["case_id"],
                "method": r["method"],
                "source_id": source["source_id"],
                "pdf_page": source["pdf_page"],
                "section": source["section"],
                "source_text": source["source_text"],
                "relevant": "",
                "licence_scope_correct": "",
                "qualifications_complete": "",
                "reviewer": "",
                "review_status": "pending",
                "comments": "",
            }
    review_path = output / "retrieval_review.csv"
    if review_path.exists():
        with review_path.open(encoding="utf-8-sig", newline="") as stream:
            previous_review = list(csv.DictReader(stream))
        for item in previous_review:
            key = item["case_id"], item["method"], item["source_id"]
            if key not in review or item["source_text"] != review[key]["source_text"]:
                raise ValueError("Review worksheet evidence changed; preserve the existing review")
            for field in [
                "relevant",
                "licence_scope_correct",
                "qualifications_complete",
                "reviewer",
                "review_status",
                "comments",
            ]:
                review[key][field] = item.get(field, "")
    with review_path.open("w", encoding="utf-8-sig", newline="") as stream:
        fields = [
            "case_id",
            "method",
            "source_id",
            "pdf_page",
            "section",
            "source_text",
            "relevant",
            "licence_scope_correct",
            "qualifications_complete",
            "reviewer",
            "review_status",
            "comments",
        ]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(review.values())
    if completed:
        audit_completion(output)
    return {
        "recorded_calls": len(rows),
        "label_discrepancies": len(disputed),
        "source_review_items": len(review),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    print(export_analysis(parser.parse_args().output))
