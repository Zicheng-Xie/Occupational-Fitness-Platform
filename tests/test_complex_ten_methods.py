"""Critical cohort and isolation checks for the complete complex-note comparison."""

import json

import pytest

from occupational_fitness_rag.provenance import digest as canonical_digest
from tools.complex_ten_contract import METHODS, digest, pin, verify, write_json
from tools.complex_ten_inputs import METHODS as INPUT_METHODS


def test_isolated_native_digest_and_method_inventory_match_main_environment():
    value = {"query": "No confirmed blackout; current BP 169/99.", "facts": [False, 0, 135.0]}
    assert digest(value) == canonical_digest(value)
    assert METHODS == INPUT_METHODS
    assert len(set(METHODS)) == 10


def test_changed_frozen_patient_snapshot_cannot_resume(tmp_path):
    (tmp_path / "facts").mkdir()
    write_json(tmp_path / "facts/case.json", {"value": False})
    plan = {
        "sources": {},
        "prepared_files": {},
        "fact_files": {"case.json": pin(tmp_path / "facts/case.json")},
    }
    plan["identity"] = digest(plan)
    verify(tmp_path, plan)
    (tmp_path / "facts/case.json").write_text(json.dumps({"value": True}), encoding="utf-8")
    with pytest.raises(ValueError, match="intake changed"):
        verify(tmp_path, plan)


def test_retrieval_failure_is_zero_recall_but_unlabelled_scope_is_not_scored():
    from tools.report_complex_ten_methods import score

    unit = {"source_id": "a", "evidence_text": "Original standard.", "covers_source_ids": []}
    queries = [
        {"query_id": str(i), "case_id": str(i), "cohort": "new_200", "module": "hearing"}
        for i in range(3)
    ]
    actual = [
        {
            **q,
            "method": "vector",
            "status": "failed" if i == 2 else "completed",
            "source_ids": [] if i == 2 else ["a"],
            "seconds": 1.0,
        }
        for i, q in enumerate(queries)
    ]
    _, metrics = score(queries, {"units": [unit]}, actual, {"0": ["a"], "1": [], "2": ["a"]})
    result = next(
        r for r in metrics if (r["cohort"], r["module"], r["method"]) == ("all", "all", "vector")
    )
    assert result["recorded_queries"] == 3
    assert result["labeled_queries"] == 2
    assert result["failed_queries"] == 1
    assert result["coverage_recall_5"] == 0.5


def test_budget_replay_never_truncates_or_backfills_a_labelled_original():
    from tools.report_complex_ten_methods import packet_replay

    query = {"query_id": "q", "case_id": "case", "module": "hearing", "cohort": "new_200"}
    units = {
        "long": {
            "module": "hearing",
            "section": "4.3",
            "pdf_page": 120,
            "printed_page": 109,
            "evidence_text": "x" * 1000,
        },
        "short": {
            "module": "hearing",
            "section": "4.3",
            "pdf_page": 120,
            "printed_page": 109,
            "evidence_text": "Original short text.",
        },
    }
    actual = [{**query, "method": "vector", "status": "completed", "source_ids": ["long", "short"]}]
    packets, _ = packet_replay([query], actual, {"q": ["long"]}, units, limit=240)
    packet = next(p for p in packets if p["method"] == "vector")
    assert packet["offered_source_ids"] == ["long", "short"]
    assert packet["excluded_by_byte_budget"] == ["long"]
    assert packet["supplied_source_ids"] == ["short"]
    assert packet["reference_coverage"] == 0
