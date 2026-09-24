"""Compatibility checks for the Red Flag and local review workflows."""

import json
from pathlib import Path

import pytest

from occupational_fitness_rag.case_intake.model_intake import apply_model_proposals
from occupational_fitness_rag.case_intake.traceable import extract_traceable_text
from occupational_fitness_rag.llm import OllamaClient, RouteSuggestion
from occupational_fitness_rag.pipeline.config import LLMConfig
from occupational_fitness_rag.pipeline.workflow import OccupationalFitnessWorkflow
from occupational_fitness_rag.provenance import digest
from occupational_fitness_rag.schemas.red_flag_result import RAGInput

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def workflow():
    return OccupationalFitnessWorkflow(ROOT / "configs/workflow.offline.yaml")


def test_projection_preserves_scoped_queries_without_full_decision(workflow):
    case, result, evidence, _ = workflow.from_text(
        "hearing.audiometry.available = true\nhearing.unaided_better_ear_average_db = 45\n"
        "Unrelated note: gardening.",
        "SCOPED-QUERY",
        ["hearing"],
    )
    payload = result.rag_input()
    assert payload.schema_version == "1.1.0"
    assert not {"source_text", "rules_evaluated", "assessment_outcome"} & set(payload.model_dump())
    for request in payload.rag_requests:
        rule = workflow.book.rules_by_id[request.rule_id]
        assert set(payload.indicator_context[request.request_id]) <= set(rule["required_facts"])
    queries = [item.semantic_query for item in evidence.evidence_items if item.semantic_query]
    assert any("45" in query for query in queries)
    assert all("gardening" not in query for query in queries)
    assert evidence.rule_result_sha256 == digest(result)
    old = payload.model_dump()
    old["schema_version"] = "1.0.0"
    old.pop("indicator_context")
    assert workflow.retriever.run(RAGInput.model_validate(old)).evidence_items
    corrupt = payload.model_dump()
    first = payload.rag_requests[0].request_id
    corrupt["indicator_context"][first]["diabetes.present"] = {"status": "unknown"}
    with pytest.raises(ValueError, match="exceeds"):
        workflow.retriever.run(RAGInput.model_validate(corrupt))


@pytest.mark.parametrize(
    "quote,field,value",
    [
        ("BP 172/102 mmHg.", "cardiovascular.blood_pressure.observed_systolic", 102),
        ("Hearing average is 45 dB.", "hearing.ent_or_audiologist_information_available", True),
        ("History of diabetes.", "diabetes.severe_hypoglycaemia_recent", True),
    ],
)
def test_generic_disease_or_number_match_cannot_authorize_field(workflow, quote, field, value):
    case = extract_traceable_text(quote, "GROUND-CHECK", "input.txt", workflow.book.field_specs)
    updated, audit = apply_model_proposals(
        case,
        {"proposals": [{"field": field, "value": value, "quote": quote}]},
        workflow.book.field_specs,
    )
    assert not audit["accepted_fields"]
    assert updated.facts.get(field) == case.facts.get(field)


def test_grounding_checks_the_selected_occurrence_context(workflow):
    quote = "History of diabetes."
    text = quote + "\nFamily: " + quote
    case = extract_traceable_text(text, "OCCURRENCE", "input.txt", workflow.book.field_specs)
    _, audit = apply_model_proposals(
        case,
        {
            "proposals": [
                {
                    "field": "diabetes.present",
                    "value": True,
                    "quote": quote,
                    "source_start": text.rindex(quote),
                }
            ]
        },
        workflow.book.field_specs,
    )
    assert not audit["accepted_fields"]


def test_route_model_runs_for_text_and_file_and_replays_without_model(
    workflow, tmp_path, monkeypatch
):
    workflow.config.llm.enabled = True
    workflow.config.llm.route_classification_enabled = True  # Explicit experiment only.
    workflow.config.llm.extraction_enabled = False
    workflow.config.llm.semantic_review_enabled = False
    calls = []

    def classify(self, text, result):
        calls.append(text)
        return {
            "status": "grounded",
            "route": "rag_fusion",
            "reason": "Review requested.",
            "evidence_quotes": [text],
        }

    monkeypatch.setattr(OllamaClient, "classify_route", classify)
    text = "No diabetes."
    _, result, _, _ = workflow.from_text(text, "ROUTE-TEXT", ["diabetes"])
    path = tmp_path / "ROUTE-FILE.txt"
    path.write_text(text)
    run = workflow.run_file(path, tmp_path / "runs", ["diabetes"])
    assert len(calls) == 2
    assert result.route == "rag_review"
    assert json.loads((run / "rule_result.json").read_text())["route"] == "rag_review"
    assert workflow.verify_run(run)["rules_replayed"]
    assert len(calls) == 2
    assert (run / "rag_input.json").is_file()


def test_empty_route_evidence_and_oversized_notes_are_withheld(monkeypatch):
    client = OllamaClient(LLMConfig(max_input_chars=100))
    monkeypatch.setattr(
        client,
        "generate",
        lambda *args: RouteSuggestion(
            route="rag_fusion", reason="Unsubstantiated suggestion.", evidence_quotes=[""]
        ),
    )
    assert client.classify_route("No diabetes.", {})["status"] == "withheld"
    assert client.classify_route("x" * 101, {})["status"] == "skipped_context_budget"


def test_chunk_overlap_is_bounded_by_effective_input_budget():
    client = OllamaClient(LLMConfig(max_input_chars=100, extraction_chunk_overlap=400))
    chunks = list(client._chunks("x" * 1000))
    assert len(chunks) < 25
    assert chunks[-1][0] + len(chunks[-1][1]) == 1000
    assert all(len(chunk) <= 100 for _, chunk in chunks)


def test_historical_reports_verify_integrity_without_current_rule_replay(workflow, tmp_path):
    from occupational_fitness_rag.reporting.archive import verify_saved_report

    source = tmp_path / "ARCHIVE.txt"
    source.write_text("No diabetes.")
    run = workflow.run_file(source, tmp_path / "runs", ["diabetes"])
    assert verify_saved_report(workflow, run)["rules_replayed"]
    workflow.book.sha256 = "f" * 64
    check = verify_saved_report(workflow, run)
    assert check["status"] == "historical_verified"
    assert not check["rules_replayed"]
    assert check["source_citations_verified"]
    (run / "draft_report.html").write_text("Changed")
    with pytest.raises(ValueError, match="fingerprint"):
        verify_saved_report(workflow, run)


def test_browser_discloses_historical_report_and_exposes_rag_schema(tmp_path):
    from fastapi.testclient import TestClient

    from occupational_fitness_rag.api import create_app

    app = create_app(str(ROOT / "configs/workflow.offline.yaml"), output_root=tmp_path / "runs")
    with TestClient(app) as client:
        source = tmp_path / "ARCHIVE-UI.txt"
        source.write_text("No diabetes.")
        run = app.state.workflow.run_file(source, tmp_path / "runs", ["diabetes"])
        app.state.workflow.book.sha256 = "f" * 64
        response = client.get(f"/reports/ARCHIVE-UI/{run.name}/draft_report.html")
        assert response.status_code == 200
        assert "Historical assessment:" in response.text
        assert "not been replayed against the current ruleset" in response.text
        assert client.get("/contracts/rag_input.schema.json").status_code == 200
        assert "/red-flag/evaluate" in client.get("/docs").text
