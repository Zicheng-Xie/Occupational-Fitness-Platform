"""Protect the owner's workflow while collaborator contracts evolve."""

import json
from pathlib import Path

import pytest

from occupational_fitness_rag.case_intake.traceable import extract_traceable_file
from occupational_fitness_rag.llm import OllamaClient
from occupational_fitness_rag.pipeline.config import LLMConfig, load_workflow_config
from occupational_fitness_rag.pipeline.workflow import OccupationalFitnessWorkflow
from occupational_fitness_rag.schemas.workflow import WorkflowRoute

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("name", ["workflow.yaml", "workflow.offline.yaml", "workflow.chroma.yaml"])
def test_all_shipped_profiles_preserve_deterministic_routing(name):
    config, _ = load_workflow_config(ROOT / "configs" / name)
    assert not config.llm.route_classification_enabled
    assert not LLMConfig().route_classification_enabled


@pytest.mark.parametrize("input_kind", ["text", "file"])
def test_review_precedes_rules_and_rag_without_extra_model_route(input_kind, tmp_path, monkeypatch):
    import occupational_fitness_rag.pipeline.workflow as pipeline

    workflow = OccupationalFitnessWorkflow(ROOT / "configs/workflow.offline.yaml")
    workflow.config.llm.enabled = True
    workflow.config.llm.narrative_enabled = False
    events = []
    from occupational_fitness_rag.case_intake.semantic_review import SourceReviewResponse

    def extract(self, text, fields, modules):
        events.append("extraction")
        return {
            "proposals": [{"field": "diabetes.present", "value": False, "quote": "No diabetes."}]
        }

    def review(self, system, payload, contract):
        assert "EXTRACTED_FACTS" not in payload
        events.append("semantic_review")
        return SourceReviewResponse(
            observations=[
                {
                    "field": field,
                    "value": False if field == "diabetes.present" else None,
                    "status": "documented" if field == "diabetes.present" else "not_documented",
                    "quote": "No diabetes." if field == "diabetes.present" else "",
                    "explanation": "Source reading for a synthetic workflow regression.",
                }
                for field in payload["FIELDS_TO_CHECK"]
            ]
        )

    def forbidden_route(*args):
        pytest.fail("The established workflow must not call the optional route model")

    evaluate = workflow.red_flag.evaluate
    retrieve = workflow.retriever.run
    build = pipeline.build_review_note

    def evaluate_checked(case):
        assert case.facts["diabetes.present"].method == "llm_grounded"
        assert case.extraction_metadata["semantic_review"]["status"] == "completed_no_issues"
        events.append("rules")
        return evaluate(case)

    def retrieve_checked(result):
        events.append("retrieval")
        return retrieve(result)

    def build_checked(*args):
        events.append("draft")
        return build(*args)

    monkeypatch.setattr(OllamaClient, "extract", extract)
    monkeypatch.setattr(OllamaClient, "generate", review)
    monkeypatch.setattr(OllamaClient, "classify_route", forbidden_route)
    monkeypatch.setattr(workflow.red_flag, "evaluate", evaluate_checked)
    monkeypatch.setattr(workflow.retriever, "run", retrieve_checked)
    monkeypatch.setattr(pipeline, "build_review_note", build_checked)
    if input_kind == "text":
        _, result, _, note = workflow.from_text("No diabetes.", "FRAMEWORK-TEXT", ["diabetes"])
        assert "llm_route" not in result.internal_metadata
        assert note.status == "DRAFT"
    else:
        source = tmp_path / "FRAMEWORK-FILE.txt"
        source.write_text("No diabetes.", encoding="utf-8")
        run = workflow.run_file(source, tmp_path / "runs", ["diabetes"])
        assert (
            "llm_route"
            not in json.loads((run / "rule_result.json").read_text(encoding="utf-8"))[
                "internal_metadata"
            ]
        )
    # File verification replays deterministic rules once after rendering.
    assert events[:5] == ["extraction", "semantic_review", "rules", "retrieval", "draft"]
    assert events[5:] == (["rules"] if input_kind == "file" else [])


def test_original_routing_snapshot_is_preserved():
    workflow = OccupationalFitnessWorkflow(ROOT / "configs/workflow.offline.yaml")
    snapshot = json.loads(
        (ROOT / "data/cases/gold/framework_routing_expectations.json").read_text(encoding="utf-8")
    )
    assert workflow.book.sha256 == snapshot["ruleset_sha256"]
    for expected in snapshot["cases"]:
        case = extract_traceable_file(ROOT / expected["input"], workflow.book.field_specs)
        result, evidence, _ = workflow.assess(case)
        assert result.route == expected["route"], case.case_id
        assert result.assessment_outcome == expected["assessment_outcome"], case.case_id
        assert [module.model_dump(mode="json") for module in result.modules] == expected[
            "modules"
        ], case.case_id
        assert {
            request.rule_id: request.request_type for request in result.rag_requests
        } == expected["request_types"], case.case_id
        expected_calls = 0 if result.route == WorkflowRoute.FAST else len(result.rag_requests)
        assert evidence.retrieval["ranking_calls"] == expected_calls, case.case_id
        for item in evidence.evidence_items:
            assert {citation.source_id for citation in item.citations} == set(
                item.requested_source_ids
            )
