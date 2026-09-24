from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from occupational_fitness_rag.api import create_app
from occupational_fitness_rag.llm import (
    ExtractionProposals,
    OllamaClient,
    RouteSuggestion,
    require_local_url,
)
from occupational_fitness_rag.pipeline.config import LLMConfig

ROOT = Path(__file__).resolve().parents[1]


def test_api_text_to_evidence_round_trip():
    with TestClient(create_app(str(ROOT / "configs/workflow.offline.yaml"))) as client:
        assert client.get("/health").status_code == 200
        response = client.post(
            "/assess",
            json={
                "case_id": "API-001",
                "text": "Reports reduced hearing. No audiometry or audiogram is available.",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["rule_result"]["assessment_outcome"] == "insufficient_information"
        assert payload["gp_review_note"]["status"] == "DRAFT"
        assert client.post("/rag/retrieve", json=payload["rag_input"]).status_code == 200
        assert (
            client.post("/assess", json={"case_id": "../../bad", "text": "note"}).status_code == 422
        )
        assert (
            client.post(
                "/assess", json={"case_id": "API-002", "text": "note", "path": "secret"}
            ).status_code
            == 422
        )


def test_browser_ui_accepts_txt_and_presents_quotes():
    with TestClient(create_app(str(ROOT / "configs/workflow.offline.yaml"))) as client:
        response = client.get("/simple")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'type="file"' in response.text
    assert 'accept=".txt,text/plain"' in response.text
    assert "Case source quotes" in response.text
    assert "Guideline source quotes" in response.text
    assert "fetch('/assess'" in response.text


def test_openapi_exposes_only_workflow_rule_result_v1_3():
    with TestClient(create_app(str(ROOT / "configs/workflow.offline.yaml"))) as client:
        schemas = client.get("/openapi.json").json()["components"]["schemas"]

    assert "RedFlagResult" not in schemas
    contract = schemas["WorkflowRuleResult"]
    assert contract["additionalProperties"] is False
    assert contract["properties"]["schema_version"]["const"] == "1.3.0"
    assert contract["properties"]["ruleset"]["$ref"].endswith("/RulesetIdentity")
    assert {"ruleset_id", "ruleset_version", "ruleset_sha256"}.isdisjoint(contract["properties"])


def test_openapi_exposes_experiment_cases_and_three_way_summary():
    with TestClient(create_app(str(ROOT / "configs/workflow.offline.yaml"))) as client:
        cases = client.get("/experiment/cases")
        one_case = client.get("/experiment/cases/BLK-REDFLAG-EDNOTE")
        missing = client.get("/experiment/cases/NOT-A-CASE")
        openapi = client.get("/openapi.json").json()

    assert cases.status_code == 200
    assert len(cases.json()) == 15
    assert {item["module"] for item in cases.json()} == {
        "hypertension",
        "vision",
        "hearing",
        "blackout",
        "diabetes",
    }
    assert one_case.status_code == 200
    assert "A blackout definitely occurred" in one_case.json()["text"]
    assert one_case.json()["expected_red_flag_classification"] == "RED_FLAG"
    assert missing.status_code == 404
    assert "/experiment/cases/{case_id}/evaluate" in openapi["paths"]
    summary = openapi["components"]["schemas"]["ExperimentAssessmentResponse"]
    assert {
        "red_flag_classification",
        "triggered_rule_ids",
        "missing_fields",
        "extracted_facts",
        "processing_steps",
        "rag_execution",
        "guideline_references",
        "final_output",
    } <= set(summary["properties"])
    reference = openapi["components"]["schemas"]["GuidelineReference"]
    assert {"source_text", "printed_page", "pdf_page", "verified_against_source"} <= set(
        reference["properties"]
    )


def test_blackout_experiment_case_matches_expected_red_flag_offline():
    with TestClient(create_app(str(ROOT / "configs/workflow.offline.yaml"))) as client:
        response = client.post("/experiment/cases/BLK-REDFLAG-EDNOTE/evaluate")
        text_response = client.post("/experiment/cases/BLK-REDFLAG-EDNOTE/evaluate.txt")

    assert response.status_code == 200
    payload = response.json()
    assert payload["red_flag_classification"] == "RED_FLAG"
    assert payload["has_red_flag"] is True
    assert payload["assessment_outcome"] == "temporarily_unfit"
    assert payload["red_flag_rule_ids"] == ["BLK-COM-UNDIAGNOSED-001"]
    assert "blackout.occurred" not in payload["missing_fields"]
    assert "blackout.mechanism_status" not in payload["missing_fields"]
    assert payload["matches_expected_classification"] is True
    assert payload["matches_expected_outcome"] is True
    assert payload["guideline_references"]
    assert all(item["verified_against_source"] for item in payload["guideline_references"])
    assert [step["step"] for step in payload["processing_steps"]] == list(range(1, 9))
    assert payload["rag_execution"]["invoked"] is True
    assert payload["rag_execution"]["evidence_item_count"] > 0
    assert payload["rag_execution"]["unresolved_request_count"] == 0
    assert payload["rag_execution"]["rule_result_fields_modified_by_rag"] is False
    facts = {item["field"]: item for item in payload["extracted_facts"]}
    assert facts["blackout.occurred"]["value"] is True
    assert facts["blackout.mechanism_status"]["value"] == "under_investigation"
    assert payload["final_output"]["mode"] == "RAG_INPUT"
    assert (
        "Classification: Red flag: an explicit driving-safety risk is present"
        in payload["final_output"]["text"]
    )
    assert "Fitness outcome: Temporarily unfit to drive" in payload["final_output"]["text"]
    assert "[4. Primary RAG tasks]" in payload["final_output"]["text"]
    assert "[5. Supplementary RAG tasks]" in payload["final_output"]["text"]
    assert "CLASSIFICATION=RED_FLAG" in payload["final_output"]["text"]
    assert text_response.status_code == 200
    assert text_response.headers["content-type"].startswith("text/plain")
    assert text_response.headers["content-disposition"].startswith("inline;")
    assert text_response.headers["x-result-mode"] == "RAG_INPUT"
    assert "BLK-COM-UNDIAGNOSED-001" in text_response.text


def test_existing_synthetic_case_can_run_through_experiment_endpoint():
    with TestClient(create_app(str(ROOT / "configs/workflow.offline.yaml"))) as client:
        response = client.post("/experiment/cases/SYN-EXT-008/evaluate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["case_id"] == "SYN-EXT-008"
    assert payload["module"] == "all"
    assert payload["rag_execution"]["invoked"] is True
    assert payload["rag_execution"]["evidence_item_count"] > 0
    assert payload["expected_red_flag_classification"] is None
    assert payload["matches_expected_classification"] is None


def test_experiment_missing_information_reports_rag_work(tmp_path):
    with TestClient(create_app(str(ROOT / "configs/workflow.offline.yaml"))) as client:
        response = client.post("/experiment/cases/HEAR-INCOMPLETE-CHECKLIST/evaluate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["assessment_outcome"] == "insufficient_information"
    assert payload["rag_execution"]["ranking_calls"] > 0
    assert payload["final_output"]["mode"] == "RAG_INPUT"


def test_api_missing_information_does_not_create_red_flag():
    with TestClient(create_app(str(ROOT / "configs/workflow.offline.yaml"))) as client:
        response = client.post(
            "/assess",
            json={
                "case_id": "API-MISSING-001",
                "text": "Reports reduced hearing. No audiometry or audiogram is available.",
                "modules_requested": ["hearing"],
            },
        )

    assert response.status_code == 200
    result = response.json()["rule_result"]
    assert result["schema_version"] == "1.3.0"
    assert result["assessment_outcome"] == "insufficient_information"
    assert result["missing_information"]
    assert result["has_red_flag"] is False
    assert result["red_flags"] == []
    assert result["assessment_context"]["modules_requested"] == ["hearing"]
    assert [module["module"] for module in result["modules"]] == ["hearing"]
    assert all(rule["module"] == "hearing" for rule in result["rules_evaluated"])
    assert all(request["category"] == "hearing" for request in result["rag_requests"])


def test_api_rejects_duplicate_or_unknown_modules():
    with TestClient(create_app(str(ROOT / "configs/workflow.offline.yaml"))) as client:
        duplicate = client.post(
            "/assess",
            json={
                "case_id": "API-MODULES-001",
                "text": "Reports reduced hearing.",
                "modules_requested": ["hearing", "hearing"],
            },
        )
        unknown = client.post(
            "/assess",
            json={
                "case_id": "API-MODULES-002",
                "text": "Reports reduced hearing.",
                "modules_requested": ["respiratory"],
            },
        )

    assert duplicate.status_code == 422
    assert unknown.status_code == 422


def test_red_flag_endpoint_stops_before_rag():
    with TestClient(create_app(str(ROOT / "configs/workflow.offline.yaml"))) as client:

        def retrieval_must_not_run(*args, **kwargs):
            raise AssertionError("Red Flag boundary invoked retrieval")

        client.app.state.workflow.retriever.run = retrieval_must_not_run
        response = client.post(
            "/red-flag/evaluate",
            json={
                "case_id": "API-RED-FLAG-BOUNDARY-001",
                "text": "Reports reduced hearing. No audiometry or audiogram is available.",
                "modules_requested": ["hearing"],
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "structured_case",
        "routing_category",
        "rule_result",
        "relevant_sections",
        "rag_input",
    }
    assert payload["routing_category"] == "needs_more_information"
    assert payload["rule_result"]["schema_version"] == "1.3.0"
    assert payload["rule_result"]["has_red_flag"] is False
    assert payload["rule_result"]["missing_information"]
    assert payload["relevant_sections"]
    assert set(payload["relevant_sections"][0]) == {
        "source_id",
        "section",
        "printed_page",
        "pdf_page",
    }
    assert payload["rag_input"]["rag_requests"]
    assert payload["rag_input"]["route"] == "missing_information"
    assert "evidence_pack" not in payload
    assert "gp_review_note" not in payload


@pytest.mark.parametrize(
    "url",
    [
        "https://external.example",
        "http://127.0.0.1.evil.example",
        "file:///tmp/model",
        "http://name:password@localhost",
    ],
)
def test_model_endpoint_must_be_local(url):
    with pytest.raises(ValueError):
        require_local_url(url)


def test_llm_fabricated_quote_is_rejected(monkeypatch):
    client = OllamaClient(LLMConfig())
    monkeypatch.setattr(
        client,
        "generate",
        lambda *args: ExtractionProposals.model_validate(
            {
                "proposals": [
                    {"field": "diabetes.present", "value": True, "quote": "not in note"},
                    {"field": "diabetes.present", "value": False, "quote": "No diabetes."},
                ]
            }
        ),
    )
    result = client.extract("No diabetes.", {"diabetes.present": {"type": "boolean"}})
    assert len(result["rejected"]) == 1
    assert result["proposals"][0]["status"] == "requires_confirmation"
    assert result["authoritative_facts_modified"] is False


def test_llm_route_with_fabricated_quote_is_withheld(monkeypatch):
    client = OllamaClient(LLMConfig())
    monkeypatch.setattr(
        client,
        "generate",
        lambda *args: RouteSuggestion.model_validate(
            {
                "route": "rag_fusion",
                "reason": "The case requires synthesis.",
                "evidence_quotes": ["This wording is not in the note."],
            }
        ),
    )

    result = client.classify_route(
        "Reports reduced hearing.",
        {"route": "fast_path", "assessment_outcome": "meets_unconditional_standard"},
    )

    assert result["status"] == "withheld"


def test_model_timeout_preserves_replayable_template_report(monkeypatch, tmp_path):
    import json

    from occupational_fitness_rag.pipeline.workflow import OccupationalFitnessWorkflow

    workflow = OccupationalFitnessWorkflow(ROOT / "configs/workflow.offline.yaml")
    workflow.config.llm.enabled = True

    def unavailable(*args):
        raise TimeoutError("synthetic timeout")

    monkeypatch.setattr(OllamaClient, "extract", unavailable)
    monkeypatch.setattr(OllamaClient, "generate", unavailable)
    run = workflow.run_file(ROOT / "data/cases/nurse_notes/SYN-M2-009.txt", tmp_path)
    manifest = json.loads((run / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["llm_status"] == "unavailable_fallback_to_template"
    assert workflow.verify_run(run)["rules_replayed"] is True
    assert (
        json.loads((run / "gp_review_note.json").read_text(encoding="utf-8"))["status"] == "DRAFT"
    )
