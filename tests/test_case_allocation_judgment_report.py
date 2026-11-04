import pytest

from tools.report_case_allocation_judgments import paired_effects


def row(arm, outcome, request="a", status="completed"):
    return {
        "case_id": "case",
        "model": "model",
        "repeat": 0,
        "method": arm,
        "request_identity": request,
        "status": status,
        "answer": {"assessment_outcome": outcome},
    }


def test_separates_allocation_effect_from_identical_request_variation():
    labels = {"case": {"reference_outcome": "temporarily_unfit"}}
    rows = [
        row("seventh_round_robin", "insufficient_information"),
        row("seventh_case_coverage", "temporarily_unfit"),
    ]
    p = next(p for p in paired_effects(rows, labels) if p["pair"] == "allocation_seventh")
    assert p["change"] == "wrong_to_correct"
    assert p["identical_input_variation"]  # Same request cannot establish allocation causality.


def test_failure_is_not_an_abstention_and_missing_pair_is_not_a_failure():
    labels = {"case": {"reference_outcome": "insufficient_information"}}
    rows = [
        row("seventh_round_robin", "insufficient_information"),
        row("seventh_case_coverage", None, request="b", status="failed"),
    ]
    pairs = {p["pair"]: p for p in paired_effects(rows, labels)}
    assert pairs["allocation_seventh"]["change"] == "run_or_contract_failure"
    assert pairs["allocation_ninth"]["change"] == "pending_pair"


def test_duplicate_actual_conditions_are_rejected():
    with pytest.raises(ValueError):
        paired_effects([row("hybrid", "x")] * 2, {})
