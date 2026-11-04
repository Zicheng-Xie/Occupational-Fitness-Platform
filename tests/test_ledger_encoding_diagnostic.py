"""Protect the paired experiment from altered requests, labels and saved answers."""

from copy import deepcopy

import pytest

from occupational_fitness_rag.evaluation import applicability_judgment as judgment
from occupational_fitness_rag.evaluation import passage_comparison as previous
from occupational_fitness_rag.evaluation.passage_judgment import passage_catalogue
from occupational_fitness_rag.provenance import digest
from tools.compare_ledger_encoding import request_pair, validate_rows


@pytest.fixture
def saved():
    config = {"context_length": 8192, "output_tokens": 2048}
    payload = {
        "licence_context": "commercial", "modules": ["vision"],
        "nurse_note": "Synthetic fixture with an explicit negative finding.",
        "verified_patient_facts": {
            "vision.diplopia": {"value": False, "patient_quotes": ["No diplopia."]},
        },
        "guideline_evidence": [{
            "source_id": "fixture-original", "module": "vision", "section": "fixture",
            "pdf_page": 1, "printed_page": 1,
            "source_text": "Synthetic original: a missing prerequisite does not establish permission.",
        }],
    }
    anchor = next(iter(passage_catalogue(payload).values()))
    review = judgment.ApplicabilityReview.model_validate({"passage_checks": [{
        "module": "vision", "passage_id": anchor["passage_id"],
        "fact_fields": ["vision.diplopia"], "statement_type": "background",
        "applicability": "uncertain", "licence_pathway": "general_information",
        "prerequisites": [], "numeric_application": "Not applicable",
        "finding": "information_missing", "conclusion": "Further information is required.",
    }]})
    item = {
        "payload": payload, "review": review.model_dump(mode="json"),
        "reference_outcome": "insufficient_information",
    }
    selected = {"fixture-model/fixture-case": item}
    body = request_pair(config, "fixture-model", payload, review)["field_references"]
    row = {
        "model": "fixture-model", "case_id": "fixture-case",
        "mode": "field_references", "repeat": 0, "status": "failed",
        "experiment_identity": "fixture-identity", "input_sha256": digest(item),
        "reference_outcome": "insufficient_information", "reference_agreement": False,
        "initial_request_sha256": digest(body),
        "initial_request_bytes": len(previous.json_bytes(body)), "model_calls": 1,
        "attempts": [{
            "status": "failed", "provider_called": True, "request": body,
            "request_sha256": digest(body), "request_bytes": len(previous.json_bytes(body)),
            "error": "Synthetic provider failure retained for review.",
        }],
    }
    planned = [("fixture-model", "fixture-case", "field_references", 0)]
    manifest = {"identity": "fixture-identity"}
    return config, selected, row, planned, manifest


def test_valid_failed_condition_remains_recorded_without_becoming_agreement(saved):
    config, selected, row, planned, manifest = saved
    assert validate_rows([row], planned, manifest, selected, config) == set(planned)
    assert row["status"] == "failed" and not row["reference_agreement"]


@pytest.mark.parametrize("field,value", [
    ("reference_outcome", "meets_unconditional_standard"),
    ("reference_agreement", True),
    ("model_calls", 0),
    ("initial_request_sha256", "changed"),
])
def test_changed_saved_identity_cost_or_agreement_is_rejected(saved, field, value):
    config, selected, row, planned, manifest = saved
    row[field] = value
    with pytest.raises(ValueError, match="differs"):
        validate_rows([row], planned, manifest, selected, config)


def test_rehashed_prompt_tampering_is_rejected_against_the_frozen_request(saved):
    config, selected, row, planned, manifest = saved
    attempt = row["attempts"][0]
    attempt["request"] = deepcopy(attempt["request"])
    attempt["request"]["messages"][1]["content"] = "A tampered source or leaked reference answer"
    attempt["request_sha256"] = digest(attempt["request"])
    attempt["request_bytes"] = len(previous.json_bytes(attempt["request"]))
    with pytest.raises(ValueError, match="initial request"):
        validate_rows([row], planned, manifest, selected, config)


def test_duplicate_condition_is_rejected(saved):
    config, selected, row, planned, manifest = saved
    with pytest.raises(ValueError, match="Duplicate"):
        validate_rows([row, deepcopy(row)], planned, manifest, selected, config)
