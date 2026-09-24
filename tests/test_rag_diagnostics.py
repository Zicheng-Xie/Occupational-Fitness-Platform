"""Protect clinical abstention while exercising meaningful symptom discovery."""

import json
from pathlib import Path

import pytest

from occupational_fitness_rag.case_intake.indexed_review import indexed_source_review
from occupational_fitness_rag.case_intake.semantic_review import review_payload
from occupational_fitness_rag.case_intake.traceable import (
    extract_traceable_file,
    extract_traceable_text,
)
from occupational_fitness_rag.pipeline.workflow import OccupationalFitnessWorkflow
from occupational_fitness_rag.provenance import digest

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = json.loads((ROOT / "data/cases/gold/validation_complex_expectations.json").read_text())


@pytest.fixture(scope="module")
def workflow():
    return OccupationalFitnessWorkflow(ROOT / "configs/workflow.offline.yaml")


@pytest.mark.parametrize("case_id", EXPECTED)
def test_complex_validation_rules_and_context(workflow, case_id):
    case = extract_traceable_file(
        ROOT / f"data/cases/validation_nurse_notes/{case_id}.txt", workflow.book.field_specs
    )
    result, evidence, _ = workflow.assess(case)
    triggered = {r.rule_id for r in result.triggered_rules}
    assert set(EXPECTED[case_id].get("required_rules", [])) <= triggered
    assert not (set(EXPECTED[case_id].get("forbidden_rules", [])) & triggered)
    assert evidence.retrieval["ranking_calls"] > 0
    assert evidence.retrieval["symptom_discovery"]
    assert evidence.rule_result_sha256 == digest(result)
    for group in evidence.retrieval["symptom_discovery"]:
        assert group["ranked_candidates"]
        assert "rag_query_key" not in group["metadata_filters"]
        assert group["source_text_sha256"] == case.text_sha256
        assert all(
            case.source_text[s["start"] : s["end"]] == s["quote"] for s in group["source_passages"]
        )


@pytest.mark.parametrize(
    "text",
    [
        "His mother has confirmed diabetes.",
        "The physician suspects possible confirmed diabetes, but no diagnosis is established.",
        "An old record says confirmed diabetes but cannot confirm whose record this is.",
    ],
)
def test_prose_does_not_diagnose_from_other_subject_or_uncertainty(workflow, text):
    case = extract_traceable_text(text, "CONTEXT", "note.txt", workflow.book.field_specs)
    assert case.facts["diabetes.present"].status != "present"


def test_zero_triggers_still_returns_ranked_symptom_evidence(workflow):
    case, result, evidence, _ = workflow.from_text(
        "The driver has fluctuating blur and an uncertain visual field measurement.",
        "SYMPTOMS",
        ["vision"],
    )
    assert not result.triggered_rules
    group = evidence.retrieval["symptom_discovery"][0]
    assert group["module"] == "vision"
    assert group["citations"] and group["ranked_candidates"]
    assert group["clinical_facts_inferred"] is False


def test_fast_path_keeps_discovery_disabled(workflow):
    _, result, evidence, _ = workflow.from_text("No diabetes.", "FAST", ["diabetes"])
    assert result.route == "fast_path"
    assert evidence.retrieval["symptom_discovery"] == []


def test_indexed_review_reconstructs_source_without_exposing_old_values(workflow):
    text = "No diabetes.\n" + "The driver brings no additional clinical records. " * 12
    case = extract_traceable_text(
        text, "REVIEW", "note.txt", workflow.book.field_specs, modules=["diabetes"]
    )

    class Client:
        def generate(self, prompt, request, contract):
            assert "extracted_facts" not in request
            assert len(request["FIELD_MAP"]) <= 6
            fields = {}
            for key, entry in request["FIELD_MAP"].items():
                is_diabetes = entry["field"] == "diabetes.present"
                fields[key] = {
                    "status": "documented" if is_diabetes else "not_documented",
                    "value": False if is_diabetes else None,
                    "passage_id": 0 if is_diabetes else None,
                    "explanation": "Source explicitly states absence.",
                }
            return contract.model_validate(fields)

    observations, batches = indexed_source_review(
        Client(), case, review_payload(case, workflow.book.field_specs), 10000
    )
    assert batches
    assert observations.observations[0].quote == "No diabetes."


def test_indexed_review_rejects_invalid_passage(workflow):
    case = extract_traceable_text(
        "No diabetes.", "BAD", "note.txt", workflow.book.field_specs, modules=["diabetes"]
    )

    class Client:
        def generate(self, prompt, request, contract):
            return contract.model_validate(
                {
                    k: {
                        "status": "documented",
                        "value": False if v["definition"]["type"] == "boolean" else "none",
                        "passage_id": 999,
                        "explanation": "Unsupported source id.",
                    }
                    for k, v in request["FIELD_MAP"].items()
                }
            )

    with pytest.raises(ValueError):
        indexed_source_review(
            Client(), case, review_payload(case, workflow.book.field_specs), 10000
        )


def test_rejected_proposals_do_not_expand_mandatory_source_review(workflow):
    text = "The driver describes fluctuating blur, with no measured acuity available."
    case = extract_traceable_text(text, "REJECTED", "note.txt", workflow.book.field_specs)
    case.extraction_metadata["proposals"] = [
        {"field": "vision.uncorrected.left.snellen", "value": "6/6", "quote": text}
    ]

    class Client:
        def generate(self, prompt, request, contract):
            assert all(
                spec["field"] != "vision.uncorrected.left.snellen"
                for spec in request["FIELD_MAP"].values()
            )
            return contract.model_validate(
                {
                    key: {
                        "explanation": "This field is not documented.",
                        "value": None,
                        "status": "not_documented",
                        "passage_id": None,
                    }
                    for key in request["FIELD_MAP"]
                }
            )

    indexed_source_review(Client(), case, review_payload(case, workflow.book.field_specs), 10000)


def test_review_checks_derived_measurements_through_their_inputs(workflow):
    text = "Uncorrected acuity measures 6/12 in the right eye and 6/18 in the left eye."
    case = extract_traceable_text(text, "DERIVED", "note.txt", workflow.book.field_specs)
    payload = review_payload(case, workflow.book.field_specs)
    assert "vision.uncorrected.better_eye" not in payload["extracted_facts"]
    assert "vision.uncorrected.right.snellen" in payload["extracted_facts"]
    assert "vision.uncorrected.left.snellen" in payload["extracted_facts"]


def test_unverified_treatment_is_not_promoted_by_a_truncated_quote(workflow):
    from occupational_fitness_rag.case_intake.model_intake import apply_model_proposals

    text = (
        "The driver reports diabetes managed with tablets, but an older specialist letter "
        "describes diet alone and the current medication box is not available for verification."
    )
    case = extract_traceable_text(text, "UNVERIFIED", "note.txt", workflow.book.field_specs)
    assert case.facts["diabetes.treatment_category"].status == "unknown"
    updated, audit = apply_model_proposals(
        case,
        {
            "proposals": [
                {
                    "field": "diabetes.treatment_category",
                    "value": "glucose_lowering_agent_non_insulin",
                    "quote": "diabetes managed with tablets",
                }
            ]
        },
        workflow.book.field_specs,
    )
    assert updated.facts["diabetes.treatment_category"].status == "unknown"
    assert audit["withheld"][0]["reason"] == "current_treatment_requires_verification"
