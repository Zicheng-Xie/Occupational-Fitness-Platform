"""Regression coverage for context loss and unsafe long-note interpretation."""

import json
from pathlib import Path

import pytest

from occupational_fitness_rag.case_intake.semantic_review import (
    compare_observations,
    review_payload,
)
from occupational_fitness_rag.case_intake.traceable import extract_traceable_text
from occupational_fitness_rag.evaluation.complex_notes import check_fact
from occupational_fitness_rag.pipeline.workflow import OccupationalFitnessWorkflow
from occupational_fitness_rag.provenance import digest
from occupational_fitness_rag.schemas.red_flag_result import RAGInput

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/cases/gold/complex_notes.json").read_text())["cases"]


@pytest.fixture(scope="module")
def workflow():
    return OccupationalFitnessWorkflow(ROOT / "configs/workflow.offline.yaml")


@pytest.mark.parametrize("fixture", CASES, ids=lambda c: c["id"])
def test_complex_notes_preserve_context_and_abstain(workflow, fixture):
    text = "\n\n".join(fixture["paragraphs"]) + "\n"
    case, result, pack, _ = workflow.from_text(text, fixture["id"], fixture["modules"])
    assert (pack.retrieval["ranking_calls"] > 0) == fixture["expect_ranking"]
    for check in fixture["checks"]:
        assert check_fact(case.model_dump()["facts"], check)["passed"], check
    if fixture["expect_ranking"]:
        context = result.rag_input().narrative_context
        assert context
        for request_id, spans in context.items():
            assert sum(len(s.quote) for s in spans) <= 2000
            query = next(
                i.semantic_query for i in pack.evidence_items if i.request_id == request_id
            )
            assert any(s.quote in query for s in spans)
            assert all(text[s.start : s.end] == s.quote for s in spans)
    assert pack.rule_result_sha256 == digest(result)
    assert not pack.integrity["rule_result_fields_modified_by_rag"]


@pytest.mark.parametrize(
    "sentence",
    [
        "Persistent BP 175/105 mmHg.",
        "Audiometry completed; unaided better ear average 45 dB.",
    ],
)
def test_current_measurements_remain_usable(workflow, sentence):
    case = extract_traceable_text(sentence, "CURRENT", "note.txt", workflow.book.field_specs)
    values = [f.value for f in case.facts.values() if f.status == "present"]
    assert (175 in values and 105 in values) if sentence.startswith("Persistent") else 45 in values


def test_module_passages_exclude_unrelated_note_and_structured_addendum(workflow):
    text = (
        "Hearing is difficult on radio calls.\nUnrelated hobby: gardening.\n"
        "Diabetes is treated with insulin.\nhearing.audiometry.available = true\n"
    )
    _, result, pack, _ = workflow.from_text(text, "CONTEXT", ["hearing"])
    assert result.rag_input().schema_version == "1.2.0"
    for item in pack.evidence_items:
        assert "gardening" not in item.semantic_query
        assert "insulin" not in item.semantic_query
    old = result.rag_input().model_dump()
    old.update(schema_version="1.1.0", narrative_context={}, narrative_source_text_sha256=None)
    assert workflow.retriever.run(RAGInput.model_validate(old)).evidence_items


def test_narrative_contract_rejects_unknown_request_and_oversize(workflow):
    _, result, _, _ = workflow.from_text("Hearing is difficult.", "BOUNDS", ["hearing"])
    payload = result.rag_input().model_dump()
    payload["narrative_context"]["unknown"] = []
    with pytest.raises(ValueError, match="unknown request"):
        RAGInput.model_validate(payload)
    payload = result.rag_input().model_dump()
    span = next(iter(payload["narrative_context"].values()))[0]
    span.update(quote="a" * 2001, end=span["start"] + 2001)
    with pytest.raises(ValueError, match="budget"):
        RAGInput.model_validate(payload)


def test_review_retains_uncertain_unextracted_symptom(workflow):
    text = "Whether he lost awareness is uncertain."
    case = extract_traceable_text(
        text, "UNCERTAIN", "note.txt", workflow.book.field_specs, modules=["blackout"]
    )
    response = {
        "observations": [
            {
                "field": "blackout.occurred",
                "value": None,
                "status": "uncertain",
                "quote": text,
                "explanation": "The note explicitly describes uncertainty.",
            }
        ]
    }
    answer = compare_observations(case, response, review_payload(case, workflow.book.field_specs))
    assert len(answer.issues) == 1
    assert answer.issues[0].kind == "uncertainty"


def test_conflicting_numeric_model_value_retains_units(workflow):
    from occupational_fitness_rag.case_intake.model_intake import apply_model_proposals

    text = "BP 150/90 mmHg. Blood pressure was 160/95 mmHg."
    case = extract_traceable_text(
        text, "CONFLICT", "note.txt", workflow.book.field_specs, modules=["hypertension"]
    )
    case, _ = apply_model_proposals(
        case,
        {
            "proposals": [
                {
                    "field": "cardiovascular.blood_pressure.observed_systolic",
                    "value": 160,
                    "quote": "Blood pressure was 160/95 mmHg.",
                }
            ]
        },
        workflow.book.field_specs,
    )
    fact = case.facts["cardiovascular.blood_pressure.observed_systolic"]
    assert fact.status == "conflicting" and fact.unit == "mmHg"
    assert workflow.assess(case)[0].route != "fast_path"


def test_repeated_regex_readings_keep_units(workflow):
    case, _, _, _ = workflow.from_text(
        "BP 150/90 mmHg; BP 160/95 mmHg.", "REPEAT", ["hypertension"]
    )
    assert case.facts["cardiovascular.blood_pressure.observed_systolic"].unit == "mmHg"
