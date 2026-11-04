from copy import deepcopy

import pytest

from tools.report_planned_hybrid import evaluate, paired_changes, summarize


def data():
    queries = [
        {"query_id": "q", "case_id": "case", "module": "vision"},
        {"query_id": "u", "case_id": "unlabeled", "module": "vision"},
    ]
    units = {
        "canonical": {"module": "vision"},
        "expanded": {"module": "vision", "covers_source_ids": ["canonical"]},
        "other": {"module": "vision"},
    }
    references = {
        "case": {
            "reference_payload": {
                "guideline_evidence": [{"source_id": "canonical", "module": "vision"}]
            }
        },
        "unlabeled": {"reference_payload": {"guideline_evidence": []}},
    }
    rows = [
        {
            "query_id": q["query_id"],
            "case_id": q["case_id"],
            "module": "vision",
            "method": method,
            "status": "completed",
            "source_ids": ["other"] if method == "hybrid" else ["expanded"],
        }
        for q in queries
        for method in ("hybrid", "planned_hybrid")
    ]
    return rows, queries, units, references


def test_exact_source_and_original_text_coverage_are_distinct():
    rows, queries, units, references = data()
    scored = evaluate(rows, queries, units, references)
    metric = next(r for r in summarize(scored) if r["method"] == "planned_hybrid")
    assert metric["exact_recall_5"] == 0
    assert metric["coverage_recall_5"] == 1
    assert metric["labeled_scopes"] == 1
    assert paired_changes(scored)["counts"] == {"improved": 1, "unlabeled": 1}


def test_failed_condition_is_preserved_in_denominator_without_substitute():
    rows, queries, units, references = data()
    failed = next(r for r in rows if r["method"] == "planned_hybrid" and r["query_id"] == "q")
    failed.update(status="failed", source_ids=[])
    scored = evaluate(rows, queries, units, references)
    metric = next(r for r in summarize(scored) if r["method"] == "planned_hybrid")
    assert metric["coverage_recall_5"] == 0
    assert metric["completed"] == 1 and metric["records"] == 2
    failed["source_ids"] = ["expanded"]
    with pytest.raises(ValueError, match="substitute"):
        evaluate(rows, queries, units, references)


def test_corrupt_source_scope_or_duplicate_is_rejected():
    rows, queries, units, references = data()
    changed = deepcopy(rows)
    changed[0]["source_ids"] = ["canonical", "canonical"]
    with pytest.raises(ValueError, match="Repeated"):
        evaluate(changed, queries, units, references)
    units["expanded"]["module"] = "diabetes"
    with pytest.raises(ValueError, match="out-of-module"):
        evaluate(rows, queries, units, references)
