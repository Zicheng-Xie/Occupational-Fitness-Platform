"""The shared retrieval query must not inherit labels or historical rankings."""

from copy import deepcopy

import pytest

from occupational_fitness_rag.evaluation.passage_comparison import patient_identity
from tools.prepare_six_method_inputs import METHODS, prepare_queries


@pytest.fixture
def inputs():
    payload = {
        "licence_context": "commercial", "modules": ["hypertension", "hearing"],
        "nurse_note": "An unverified family-history statement must not enter the query.",
        "verified_patient_facts": {
            "cardiovascular.persistent_systolic": {
                "value": 0, "patient_quotes": ["Synthetic explicitly recorded zero."],
            },
            "hearing.screening_concern": {
                "value": False, "patient_quotes": ["Synthetic screening concern absent."],
            },
        },
        "guideline_evidence": [{
            "source_id": "REFERENCE_SOURCE_SENTINEL", "source_text": "Historical result.",
            "module": "hearing", "section": "fixture", "pdf_page": 1, "printed_page": 1,
        }],
    }
    data = {"fixture-case": {
        "payload": payload, "reference_outcome": "REFERENCE_OUTCOME_SENTINEL",
        "rule_outcome": "RULE_OUTCOME_SENTINEL",
    }}
    snapshot = {"identity": "fact-version", "cases": {"fixture-case": {
        "sensitivity_patient_identity": patient_identity(payload),
        "sensitivity_verified_patient_facts": deepcopy(payload["verified_patient_facts"]),
    }}}
    return data, snapshot, {"corpus_sha256": "corpus-version"}


def test_fresh_queries_use_only_frozen_module_facts_and_original_quotes(inputs):
    data, snapshot, corpus = inputs
    patients, queries = prepare_queries(data, snapshot, corpus)
    assert len(queries) == 2 and len(METHODS) == 6
    assert "guideline_evidence" not in patients["fixture-case"]
    hypertension, hearing = queries
    assert "= 0" in hypertension["query"]
    assert "= false" in hearing["query"]
    assert "Synthetic explicitly recorded zero." in hypertension["query"]
    assert "Synthetic screening concern absent." not in hypertension["query"]
    assert "family-history" not in str(queries)
    assert "REFERENCE_" not in str(queries) and "RULE_OUTCOME" not in str(queries)
    assert all(q["fact_snapshot_identity"] == "fact-version" for q in queries)


@pytest.mark.parametrize("change", ["missing_case", "changed_value", "changed_quote", "private"])
def test_changed_source_literal_inputs_or_case_inventory_are_rejected(inputs, change):
    data, snapshot, corpus = inputs
    if change == "missing_case":
        snapshot["cases"]["unexpected-case"] = snapshot["cases"]["fixture-case"]
    elif change == "private":
        data["fixture-case"]["payload"]["licence_context"] = "private"
    else:
        fact = data["fixture-case"]["payload"]["verified_patient_facts"]["hearing.screening_concern"]
        if change == "changed_value":
            fact["value"] = True
        else:
            fact["patient_quotes"] = ["Changed original quotation."]
    with pytest.raises(ValueError, match="complete fact snapshot|differs"):
        prepare_queries(data, snapshot, corpus)


def test_duplicate_case_module_scope_is_rejected(inputs):
    data, snapshot, corpus = inputs
    payload = data["fixture-case"]["payload"]
    payload["modules"].append("hearing")
    snapshot["cases"]["fixture-case"]["sensitivity_patient_identity"] = patient_identity(payload)
    with pytest.raises(ValueError, match="Duplicate"):
        prepare_queries(data, snapshot, corpus)
