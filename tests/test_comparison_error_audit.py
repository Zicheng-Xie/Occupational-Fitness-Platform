"""Paired judgment diagnostics must not attribute model variation to retrieval."""

from copy import deepcopy

import pytest

from occupational_fitness_rag.evaluation.comparison_error_audit import (
    audit_errors,
    render_error_audit,
)


def record(method, outcome, source="original", repeat=0):
    return {
        "case_id": "case-1",
        "cohort": "engineering",
        "model": "local",
        "method": method,
        "repeat": repeat,
        "status": "completed",
        "reference_outcome": "temporarily_unfit",
        "answer": {
            "assessment_outcome": outcome,
            "explanation": "Test explanation.",
            "source_ids": [source],
        },
        "input_snapshot": {
            "licence_context": "commercial",
            "modules": ["blackout"],
            "nurse_note": "<script>injected()</script>",
            "verified_patient_facts": {"blackout.occurred": {"value": True}},
            "guideline_evidence": [
                {
                    "source_id": source,
                    "section": "1.2.1",
                    "pdf_page": 68,
                    "source_text": "Original passage.",
                }
            ],
        },
    }


def test_changed_judgment_with_identical_evidence_is_not_a_retrieval_gain():
    rows = [record("hybrid", "insufficient_information"), record("vector", "temporarily_unfit")]
    audit = audit_errors(rows)
    assert audit["pairs"][0]["transition"] == "wrong_to_correct"
    assert audit["pairs"][0]["evidence_change"] == "identical_ordered_evidence"
    assert audit["changed_outcome_with_identical_evidence"] == 1
    assert audit["repeat_stability"][0]["stable_outcome"] is None
    html = render_error_audit(audit, rows)
    assert "<script>injected()" not in html and "&lt;script&gt;" in html


def test_both_wrong_can_change_outcomes_and_patient_mismatches_are_excluded():
    rows = [
        record("hybrid", "insufficient_information"),
        record("vector", "does_not_meet_standard", "other"),
    ]
    audit = audit_errors(rows, ["case-1"])
    pair = audit["pairs"][0]
    assert pair["transition"] == "both_wrong" and pair["outcome_changed"]
    assert pair["evidence_change"] == "changed_evidence_bundle"
    assert pair["added_source_ids"] == ["other"]
    assert pair["upstream_review_difference"]
    rows[1]["input_snapshot"]["verified_patient_facts"] = {}
    audit = audit_errors(rows)
    assert audit["patient_input_mismatches"] == 1
    assert audit["pairs"][0]["transition"] == "not_comparable"


def test_repeat_stability_requires_all_calls_and_identical_inputs():
    rows = [record("vector", "temporarily_unfit", repeat=i) for i in range(3)]
    assert audit_errors(rows)["repeat_stability"][0]["stable_outcome"] is True
    changed = deepcopy(rows)
    changed[2]["input_snapshot"]["verified_patient_facts"] = {}
    assert audit_errors(changed)["repeat_stability"][0]["stable_outcome"] is None
    rows[2]["status"] = "failed"
    assert audit_errors(rows)["repeat_stability"][0]["stable_outcome"] is None
    with pytest.raises(ValueError, match="Duplicate"):
        audit_errors([rows[0], rows[0]])
