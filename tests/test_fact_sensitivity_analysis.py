"""Reject confounded paired comparisons and retain failures as execution failures."""

from copy import deepcopy

import pytest

from occupational_fitness_rag.evaluation.passage_comparison import patient_identity
from occupational_fitness_rag.provenance import digest
from tools.compare_fact_sensitivity import compare_pair, validate_held_origin


def pair():
    payload = {
        "licence_context": "commercial",
        "modules": ["diabetes"],
        "nurse_note": "diabetes.present = false",
        "verified_patient_facts": {},
        "guideline_evidence": [{"source_id": "held-original", "source_text": "Exact original"}],
    }
    updated = deepcopy(payload)
    updated["verified_patient_facts"]["diabetes.present"] = {
        "value": False,
        "patient_quotes": [payload["nurse_note"]],
    }
    before = {
        "model": "fixture",
        "case_id": "case",
        "evidence_policy": "module_query",
        "protocol": "applicability_first",
        "repeat": 0,
        "model_digest": "frozen-judge",
        "reference_outcome": "insufficient_information",
        "status": "completed",
        "reference_agreement": False,
        "input_snapshot": payload,
        "input_sha256": "old",
        "answer": {"assessment_outcome": "temporarily_unfit"},
    }
    after = {
        **before,
        "input_snapshot": updated,
        "input_sha256": "new",
        "reference_agreement": True,
        "answer": {"assessment_outcome": "insufficient_information"},
    }
    case = {
        "original_patient_identity": patient_identity(payload),
        "sensitivity_patient_identity": patient_identity(updated),
        "original_verified_patient_facts": payload["verified_patient_facts"],
        "sensitivity_verified_patient_facts": updated["verified_patient_facts"],
        "changes": [{"field": "diabetes.present"}],
    }
    before["input_sha256"], after["input_sha256"] = digest(payload), digest(updated)
    return before, after, case


def test_valid_wrong_to_correct_is_distinct_from_recovered_execution():
    before, after, case = pair()
    assert compare_pair(before, after, case)["transition"] == "accepted_wrong_to_correct"
    before.update(status="failed", reference_agreement=False)
    before.pop("answer")
    result = compare_pair(before, after, case)
    assert result["transition"] == "failed_to_valid"
    assert result["after_agreement"] is True


def test_changed_evidence_rejected_even_when_patient_facts_are_correct():
    before, after, case = pair()
    after["input_snapshot"]["guideline_evidence"][0]["source_text"] += " New evidence"
    with pytest.raises(ValueError, match="beyond the pinned"):
        compare_pair(before, after, case)


@pytest.mark.parametrize("field", ["model_digest", "reference_outcome", "repeat"])
def test_changed_reference_model_or_repeat_cannot_be_paired(field):
    before, after, case = pair()
    after[field] = "different"
    with pytest.raises(ValueError):
        compare_pair(before, after, case)


def test_regression_is_retained_without_rewriting_the_model_outcome():
    before, after, case = pair()
    before["reference_agreement"], after["reference_agreement"] = True, False
    result = compare_pair(before, after, case)
    assert result["transition"] == "accepted_correct_to_wrong"
    assert result["after_outcome"] == after["answer"]["assessment_outcome"]


def test_invalid_input_fingerprint_is_rejected_even_when_content_is_bound():
    before, after, case = pair()
    after["input_sha256"] = "stale"
    with pytest.raises(ValueError, match="beyond the pinned"):
        compare_pair(before, after, case)


def test_retrieval_record_changes_cannot_be_called_a_held_query_comparison():
    snapshot = {"identity": "facts", "metadata": {"retrieval_identity": "original"}}
    original = {
        "manifest.json": {"identity": "original"},
        "retrieval.json": {"records": [{"query": "Original"}]},
        "embeddings.json": {"vectors": [[1]]},
        "corpus.json": {"corpus": "same"},
    }
    updated = deepcopy(original)
    updated["manifest.json"]["derivation"] = {
        "kind": "source_literal_fact_sensitivity_with_held_evidence",
        "original_retrieval_identity": "original",
        "fact_snapshot_identity": "facts",
        "retrieval_executed": False,
        "new_retrieval_calls": 0,
        "new_embedding_calls": 0,
    }
    validate_held_origin({"upstream_snapshot": original}, {"upstream_snapshot": updated}, snapshot)
    updated["retrieval.json"]["records"][0]["query"] = "Rebuilt query"
    with pytest.raises(ValueError, match="historical retrieval origin"):
        validate_held_origin(
            {"upstream_snapshot": original}, {"upstream_snapshot": updated}, snapshot
        )
