from pathlib import Path

import pytest

from occupational_fitness_rag.case_intake.model_intake import apply_model_proposals
from occupational_fitness_rag.case_intake.traceable import extract_traceable_text
from occupational_fitness_rag.llm import OllamaClient
from occupational_fitness_rag.pipeline.workflow import OccupationalFitnessWorkflow

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def workflow():
    return OccupationalFitnessWorkflow(ROOT / "configs/workflow.offline.yaml")


def merge(workflow, text, field, value, quote):
    case = extract_traceable_text(text, "MODEL-TEST", "input.txt", workflow.book.field_specs)
    return case, *apply_model_proposals(
        case,
        {"model": "llama3:8b", "proposals": [{"field": field, "value": value, "quote": quote}]},
        workflow.book.field_specs,
    )


def test_supported_model_fact_enters_authoritative_case(workflow):
    text = "The patient denies a history of diabetes mellitus."
    original, updated, audit = merge(workflow, text, "diabetes.present", False, text)
    assert original.facts["diabetes.present"].status == "unknown"
    assert updated.facts["diabetes.present"].value is False
    assert updated.facts["diabetes.present"].method == "llm_grounded"
    assert updated.facts["diabetes.present"].evidence[0].quote == text
    assert audit["authoritative_facts_modified"] is True


@pytest.mark.parametrize(
    "text,field,value",
    [
        ("BP 172/102 mmHg.", "cardiovascular.blood_pressure.persistent_systolic", 172),
        ("No diabetes.", "diabetes.present", True),
        ("No family history of diabetes.", "diabetes.present", False),
        ("No diabetes information is available.", "diabetes.present", False),
        ("Hearing average is 45 dB.", "hearing.average_frequencies_khz", [0.5, 1, 2, 3]),
    ],
)
def test_quote_alone_cannot_authorize_unsupported_facts(workflow, text, field, value):
    original, updated, audit = merge(workflow, text, field, value, text)
    assert not audit["accepted_fields"]
    assert updated.facts[field] == original.facts[field]


def test_conflict_is_not_overwritten_by_model(workflow):
    text = "History of diabetes. The patient denies a history of diabetes mellitus."
    _, updated, audit = merge(
        workflow,
        text,
        "diabetes.present",
        False,
        "The patient denies a history of diabetes mellitus.",
    )
    assert updated.facts["diabetes.present"].status == "conflicting"
    assert audit["withheld"]


@pytest.mark.parametrize(
    "text",
    ["The patient denies a history of diabetes.", "Family history of diabetes."],
)
def test_model_cannot_remove_context_from_quote(workflow, text):
    original, updated, audit = merge(
        workflow, text, "diabetes.present", True, "history of diabetes."
    )
    assert not audit["accepted_fields"]
    assert updated.facts["diabetes.present"] == original.facts["diabetes.present"]


def test_model_stage_precedes_rule_evaluation(monkeypatch):
    workflow = OccupationalFitnessWorkflow(ROOT / "configs/workflow.offline.yaml")
    workflow.config.llm.enabled = True
    quote = "The patient denies a history of diabetes mellitus."
    monkeypatch.setattr(
        OllamaClient,
        "extract",
        lambda *args: {
            "model": "llama3:8b",
            "proposals": [{"field": "diabetes.present", "value": False, "quote": quote}],
        },
    )
    evaluate = workflow.book.evaluate

    def checked(case):
        assert case.facts["diabetes.present"].method == "llm_grounded"
        return evaluate(case)

    monkeypatch.setattr(workflow.book, "evaluate", checked)
    case, result, _, _ = workflow.from_text(quote, "MODEL-ORDER")
    assert result.case_id == case.case_id
    assert case.extraction_metadata["model"] == "llama3:8b"


def test_structured_knowledge_contract_is_source_bound(workflow):
    citation = workflow.catalogue.citation("AFTD2022-HTN-COM-001")
    assert citation.condition == "hypertension"
    assert citation.standard == "commercial"
    assert citation.criterion_type == "unconditional"
    assert citation.source_text == citation.evidence_text
    assert citation.bounding_box == citation.bbox
    assert citation.pdf_page == 99 and citation.printed_page == 88
    with pytest.raises(ValueError, match="aliases disagree"):
        type(citation).model_validate({**citation.model_dump(), "source_text": "invented"})
