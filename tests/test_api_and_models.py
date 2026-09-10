from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from occupational_fitness_rag.api import create_app
from occupational_fitness_rag.llm import ExtractionProposals, OllamaClient, require_local_url
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


def test_openapi_exposes_only_workflow_rule_result_v1_3():
    with TestClient(create_app(str(ROOT / "configs/workflow.offline.yaml"))) as client:
        schemas = client.get("/openapi.json").json()["components"]["schemas"]

    assert "RedFlagResult" not in schemas
    contract = schemas["WorkflowRuleResult"]
    assert contract["additionalProperties"] is False
    assert contract["properties"]["schema_version"]["const"] == "1.3.0"
    assert contract["properties"]["ruleset"]["$ref"].endswith("/RulesetIdentity")
    assert {"ruleset_id", "ruleset_version", "ruleset_sha256"}.isdisjoint(contract["properties"])


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
    assert set(payload) == {"structured_case", "rule_result", "rag_input"}
    assert payload["rule_result"]["schema_version"] == "1.3.0"
    assert payload["rule_result"]["has_red_flag"] is False
    assert payload["rule_result"]["missing_information"]
    assert payload["rag_input"]["rag_requests"] == payload["rule_result"]["rag_requests"]
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


def test_model_timeout_preserves_replayable_template_report(monkeypatch, tmp_path):
    import json

    from occupational_fitness_rag.pipeline.workflow import OccupationalFitnessWorkflow

    workflow = OccupationalFitnessWorkflow(ROOT / "configs/workflow.offline.yaml")
    workflow.config.llm.enabled = True

    def unavailable(*args):
        raise TimeoutError("synthetic timeout")

    monkeypatch.setattr(OllamaClient, "extract", unavailable)
    run = workflow.run_file(ROOT / "data/cases/nurse_notes/SYN-M2-009.txt", tmp_path)
    manifest = json.loads((run / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["llm_status"] == "unavailable_fallback_to_template"
    assert workflow.verify_run(run)["rules_replayed"] is True
    assert (
        json.loads((run / "gp_review_note.json").read_text(encoding="utf-8"))["status"] == "DRAFT"
    )
