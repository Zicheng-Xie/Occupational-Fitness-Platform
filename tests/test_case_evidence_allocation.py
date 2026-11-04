from copy import deepcopy

import pytest

from occupational_fitness_rag.evaluation.case_evidence_allocation import (
    allocate_case_evidence,
    evidence_bytes,
    source_record,
)


def unit(sid, text, module="blackout", criterion=None, contains=()):
    return {
        "source_id": sid,
        "evidence_text": text,
        "module": module,
        "criterion_type": criterion,
        "licence_context": "commercial",
        "pdf_page": 68,
        "printed_page": 57,
        "section": "1.2.1",
        "covers_source_ids": list(contains),
    }


def test_balanced_case_selects_complete_original_without_changing_facts():
    modules = ["hypertension", "vision", "hearing", "blackout", "diabetes"]
    patient = {"modules": modules, "verified_patient_facts": {}}
    units = {m: unit(m, m, m) for m in modules}
    units.update(
        a=unit("a", "abc", criterion="a"),
        b=unit("b", "xyz", criterion="b"),
        parent=unit("parent", "abc xyz", criterion="table", contains=["a", "b"]),
    )
    rows = [{"module": m, "source_ids": [m]} for m in modules]
    rows[3]["source_ids"] += ["parent", "a", "b"]
    before = deepcopy((patient, rows, units))
    result = allocate_case_evidence(patient, rows, units)
    assert "parent" in result["source_ids"] and "blackout" not in result["source_ids"]
    assert len(result["source_ids"]) == 5
    assert before == (patient, rows, units)


def test_false_fact_stays_documented_and_unknown_modules_do_not_gain_facts():
    p = {
        "modules": ["blackout", "diabetes"],
        "verified_patient_facts": {"blackout.occurred": {"value": False}},
    }
    u = {"b": unit("b", "blackout", criterion="c"), "d": unit("d", "diabetes", "diabetes")}
    r = [{"module": "blackout", "source_ids": ["b"]}, {"module": "diabetes", "source_ids": ["d"]}]
    result = allocate_case_evidence(p, r, u)
    assert result["source_ids"] == ["b"]
    assert result["unmeasured_modules"] == ["diabetes"]


def test_byte_budget_selects_smaller_subsets_and_preserves_actual_floor():
    p = {"modules": ["blackout"], "verified_patient_facts": {}}
    u = {"a": unit("a", "é" * 1000, criterion="a"), "b": unit("b", "b", criterion="b")}
    limit = evidence_bytes([source_record(u["b"])])
    result = allocate_case_evidence(
        p, [{"module": "blackout", "source_ids": ["a", "b"]}], u, byte_limit=limit
    )
    assert result["source_ids"] == ["b"]
    assert result["diagnostics"]["evidence_bytes"] <= limit


@pytest.mark.parametrize("change", ["private", "false_containment", "failed"])
def test_rejects_unusable_originals(change):
    p = {"modules": ["blackout"], "verified_patient_facts": {}}
    u = {"a": unit("a", "abc", criterion="a"), "b": unit("b", "xyz", criterion="b")}
    rows = [{"module": "blackout", "source_ids": ["a", "b"]}]
    if change == "private":
        u["a"]["licence_context"] = "private"
    elif change == "false_containment":
        u["a"]["covers_source_ids"] = ["b"]
    else:
        rows[0]["status"] = "failed"
    with pytest.raises(ValueError):
        allocate_case_evidence(p, rows, u)
