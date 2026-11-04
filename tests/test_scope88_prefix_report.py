"""Extra criterion counts are incomplete-reference audits, not precision."""

from tools.report_scope88_prefix_allocation import extra_criterion_audit


def fixture():
    units = {
        sid: {"criterion_type": "general", "covers_source_ids": []}
        for sid in ("one", "two", "three")
    }
    rows = [
        {
            "query_id": "q",
            "case_id": "c",
            "module": "m",
            "method": "scope88_guarded_v3",
            "source_ids": ["one", "two"],
        },
        {
            "query_id": "q",
            "case_id": "c",
            "module": "m",
            "method": "candidate",
            "source_ids": ["one", "three"],
        },
    ]
    scored = [{"query_id": "q", "method": r["method"], "reference_sources": ["one"]} for r in rows]
    return rows, scored, units


def test_additional_criteria_are_distinct_from_reference_recall():
    rows, scored, units = fixture()
    audit = extra_criterion_audit(rows, scored, units)
    assert audit[0]["criteria_extra_to_engineering_reference"] == ["two"]
    assert audit[1]["introduced_extra_criteria_vs_guarded_v3"] == ["three"]
    assert "not established irrelevant evidence" in audit[1]["interpretation"]


def test_unlabeled_scopes_do_not_supply_zero_precision_labels():
    rows, scored, units = fixture()
    for r in scored:
        r["reference_sources"] = []
    audit = extra_criterion_audit(rows, scored, units)
    assert all(not r["reference_scope_labeled"] for r in audit)
    assert all(r["criteria_extra_to_engineering_reference"] is None for r in audit)
