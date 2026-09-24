"""Regression checks for all-module completeness and source review scope."""

import json
from pathlib import Path

import pytest

from occupational_fitness_rag.case_intake.indexed_review import clinical_passages
from occupational_fitness_rag.case_intake.traceable import extract_traceable_file
from occupational_fitness_rag.pipeline.workflow import OccupationalFitnessWorkflow
from occupational_fitness_rag.reporting.builder import render_reports
from occupational_fitness_rag.schemas.workflow import MODULES

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = json.loads((ROOT / "data/cases/gold/validation_complex_expectations.json").read_text())


@pytest.fixture(scope="module")
def workflow():
    return OccupationalFitnessWorkflow(ROOT / "configs/workflow.offline.yaml")


@pytest.mark.parametrize("case_id", EXPECTED)
def test_all_requested_modules_preserve_expected_outcome(workflow, case_id):
    case = extract_traceable_file(
        ROOT / f"data/cases/validation_nurse_notes/{case_id}.txt", workflow.book.field_specs
    )
    assert case.modules_requested == list(MODULES)
    result, evidence, note = workflow.assess(case)
    assert result.assessment_outcome == EXPECTED[case_id]["overall_outcome"]
    assert set(EXPECTED[case_id]["required_rules"]) <= {r.rule_id for r in result.triggered_rules}
    reports = render_reports(case, result, evidence, note, ROOT, ROOT / "outputs")
    for report in reports.values():
        assert "Established rule findings" in report
        for rule_id in EXPECTED[case_id]["required_rules"]:
            assert rule_id in report
    if case_id == "VAL-MIX-08":
        assert {g["module"] for g in evidence.retrieval["symptom_discovery"]} == {
            "hearing",
            "diabetes",
        }
        assert "does not erase the findings" in reports["draft_report.html"]


def test_hypoglycaemia_awareness_is_not_a_blackout_symptom(workflow):
    for text, expected in [
        ("Hypoglycaemia awareness has not been assessed.", False),
        ("Impaired hypoglycaemia awareness is reported.", False),
        ("The driver lost awareness and collapsed after a missed meal.", True),
        ("There was loss of awareness during a hypoglycaemic episode.", True),
    ]:
        _, _, evidence, _ = workflow.from_text(text, "SCOPE")
        modules = {g["module"] for g in evidence.retrieval["symptom_discovery"]}
        assert ("blackout" in modules) is expected


def test_source_review_excludes_only_standalone_administrative_header():
    text = "Synthetic validation nurse note. No real patient data.\n\nNo diabetes."
    assert clinical_passages(text) == ["No diabetes."]
    assert clinical_passages("No real patient data. The driver fainted.") == [
        "No real patient data. The driver fainted."
    ]


def test_context_version_preserves_historical_rule_replay(workflow):
    case = extract_traceable_file(
        ROOT / "data/cases/validation_nurse_notes/VAL-MIX-08.txt", workflow.book.field_specs
    )
    old = workflow.red_flag.evaluate(case, context_version=1)
    new = workflow.red_flag.evaluate(case)
    assert old.rules_evaluated == new.rules_evaluated
    assert old.assessment_outcome == new.assessment_outcome
    assert old.internal_metadata["narrative_context"] != new.internal_metadata["narrative_context"]
    assert "narrative_context_version" not in old.internal_metadata
    assert new.internal_metadata["narrative_context_version"] == 2


@pytest.mark.parametrize("failure", ["unrelated_passage", "missing_as_false"])
def test_review_rejects_unsupported_documented_observations(workflow, failure):
    from occupational_fitness_rag.case_intake.indexed_review import indexed_source_review
    from occupational_fitness_rag.case_intake.semantic_review import review_payload
    from occupational_fitness_rag.case_intake.traceable import extract_traceable_text

    text = "Synthetic validation nurse note. No real patient data.\nThe driver has diabetes.\nBlackout status is uncertain."
    case = extract_traceable_text(text, "INVALID-REVIEW", "note.txt", workflow.book.field_specs)
    payload = review_payload(case, workflow.book.field_specs)
    payload["field_dictionary"] = {
        "blackout.occurred": payload["field_dictionary"]["blackout.occurred"]
    }
    payload["extracted_facts"] = {}

    class Client:
        def generate(self, prompt, request, contract):
            assert all("Synthetic validation" not in p for p in request["SOURCE_PASSAGES"].values())
            schema = contract.model_json_schema()
            for definition in schema["$defs"].values():
                assert list(definition["properties"])[0] == "status"
            return contract.model_validate(
                {
                    "field_0": {
                        "status": "documented",
                        "value": False,
                        "passage_id": 0 if failure == "unrelated_passage" else 1,
                        "explanation": "No blackout."
                        if failure == "unrelated_passage"
                        else "not_documented",
                    }
                }
            )

    with pytest.raises(ValueError):
        indexed_source_review(Client(), case, payload, 10000)
