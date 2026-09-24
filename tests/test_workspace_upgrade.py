import json
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient

from occupational_fitness_rag.api import create_app
from occupational_fitness_rag.evaluation.model_judgment import (
    ExperimentalJudgment,
    run_judgment_study,
)
from occupational_fitness_rag.evaluation.retrieval_study import score_sources
from occupational_fitness_rag.llm import OllamaClient
from occupational_fitness_rag.provenance import digest
from occupational_fitness_rag.retrieval.indicators import IndicatorRetriever, knowledge_chunks
from occupational_fitness_rag.schemas.indicator import IndicatorRequest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def workspace(tmp_path):
    app = create_app(str(ROOT / "configs/workflow.offline.yaml"), output_root=tmp_path / "runs")
    with TestClient(app) as client:
        yield app, client


def complete(app, client, response):
    assert response.status_code == 202, response.text
    job = response.json()["job_id"]
    app.state.jobs.futures[job].result(timeout=20)
    return client.get(f"/assessments/jobs/{job}").json()


def test_browser_text_submission_creates_verified_report(workspace):
    app, client = workspace
    assert client.get("/").status_code == 200
    assert client.get("/docs").status_code == 200
    assert client.get("/assets/workspace.js").status_code == 200
    result = complete(
        app,
        client,
        client.post(
            "/assessments/text",
            json={"case_id": "WEB-001", "text": "No diabetes.", "modules": ["diabetes"]},
        ),
    )
    assert result["status"] == "completed", result
    report = client.get(result["report_url"])
    assert report.status_code == 200
    assert "/guideline/ap_g56_22.pdf#page=" in report.text
    assert "/#records" in report.text
    assert "DRAFT" in report.text
    assert client.get("/assessments").json()[0]["case_id"] == "WEB-001"
    data = client.get(result["report_url"].replace("draft_report.html", "structured_case.json"))
    assert data.json()["modules_requested"] == ["diabetes"]
    assert "attachment" in data.headers["content-disposition"]


@pytest.mark.parametrize("suffix", ["txt", "md", "pdf"])
def test_file_intake_all_supported_formats(workspace, suffix):
    app, client = workspace
    content = b"No diabetes."
    if suffix == "pdf":
        with pymupdf.open() as doc:
            doc.new_page().insert_text((50, 50), "No diabetes.")
            content = doc.tobytes()
    response = client.post(
        f"/assessments/file?case_id=FILE-{suffix}&filename=../record.{suffix}&modules=diabetes",
        content=content,
    )
    result = complete(app, client, response)
    assert result["status"] == "completed", result
    run = app.state.jobs.output_root / f"FILE-{suffix}" / result["run_id"]
    assert (run / f"source_input.{suffix}").read_bytes() == content
    assert app.state.workflow.verify_run(run)["source_citations_verified"]


def test_input_rejections_and_local_browser_boundary(workspace):
    _, client = workspace
    prefix = "/assessments/file?case_id=CHECK&modules=diabetes&filename="
    assert client.post(prefix + "case.docx", content=b"x").status_code == 415
    assert client.post(prefix + "case.pdf", content=b"not a pdf").status_code == 422
    assert client.post(prefix + "case.txt", content=b"\xff").status_code == 422
    assert client.post(prefix + "case.txt", content=b"").status_code == 422
    assert client.post(prefix + "case.txt", content=b"x" * (8 * 1024 * 1024 + 1)).status_code == 413
    assert (
        client.post(
            "/assessments/text", json={"case_id": "../bad", "text": "x", "modules": ["diabetes"]}
        ).status_code
        == 422
    )
    assert client.get("/assets/secrets.env").status_code == 404
    assert client.get("/", headers={"host": "malicious.example"}).status_code == 400
    assert (
        client.post(
            prefix + "case.txt", content=b"x", headers={"origin": "https://external.example"}
        ).status_code
        == 403
    )


def test_scanned_pdf_fails_with_actionable_message(workspace):
    app, client = workspace
    with pymupdf.open() as doc:
        doc.new_page()
        content = doc.tobytes()
    result = complete(
        app,
        client,
        client.post(
            "/assessments/file?case_id=SCAN&filename=scan.pdf&modules=hearing", content=content
        ),
    )
    assert result["status"] == "failed"
    assert "OCR" in result["error"]


def test_tampered_report_is_not_served(workspace):
    app, client = workspace
    result = complete(
        app,
        client,
        client.post(
            "/assessments/text",
            json={"case_id": "TAMPER", "text": "No diabetes.", "modules": ["diabetes"]},
        ),
    )
    run = app.state.jobs.output_root / "TAMPER" / result["run_id"]
    (run / "draft_report.html").write_text("changed", encoding="utf-8")
    assert client.get(result["report_url"]).status_code == 409


def test_indicator_query_uses_only_selected_source_span(workspace):
    _, client = workspace
    text = "Blood pressure 180/110. Hearing impairment; no audiogram is available. No diabetes."
    start, end = text.index("Hearing"), text.index(" No diabetes")
    response = client.post(
        "/rag/indicators",
        json={
            "case_id": "IND-01",
            "indicator_id": "hearing-1",
            "module": "hearing",
            "source_document": "note.txt",
            "source_text": text,
            "start": start,
            "end": end,
            "top_k": 3,
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["query"] == text[start:end]
    assert data["assessment_outcome"] is None
    assert data["citations"] and all(c["condition"] == "hearing" for c in data["citations"])
    assert "source_id" not in data["filters"] and "rag_query_key" not in data["filters"]
    with pytest.raises(ValueError):
        IndicatorRequest(
            case_id="X",
            indicator_id="X",
            module="hearing",
            source_document="x",
            source_text="a",
            start=0,
            end=2,
        )


def test_rule_queries_do_not_include_other_modules(workspace):
    app, _ = workspace
    wf = app.state.workflow
    _, result, evidence, _ = wf.from_text(
        "Reports reduced hearing. No audiogram is available. No diabetes.", "PER-IND"
    )
    before = digest(result)
    for item in evidence.evidence_items:
        if item.rule_id.startswith("HEAR"):
            assert "No diabetes" not in (item.semantic_query or "")
            assert "hearing" in item.semantic_query
        assert {c.source_id for c in item.citations} == set(item.requested_source_ids)
    assert before == digest(result)


def test_grouping_preserves_whole_anchored_text_and_module(workspace):
    app, _ = workspace
    wf = app.state.workflow
    for strategy in ("unit", "section", "page"):
        chunks = knowledge_chunks(wf.book, wf.catalogue, strategy)
        assert len({c.chunk_id for c in chunks}) == len(chunks)
        for c in chunks:
            for sid in c.metadata["source_ids_csv"].split(","):
                assert wf.catalogue.units[sid]["evidence_text"] in c.text


def test_bm25_ablation_does_not_call_vector_search(workspace, monkeypatch):
    app, _ = workspace
    ret = IndicatorRetriever(app.state.workflow, "offline")

    def forbidden(*args):
        raise AssertionError("Vector branch called in BM25-only experiment")

    monkeypatch.setattr(ret.store, "search", forbidden)
    req = IndicatorRequest(
        case_id="X",
        indicator_id="X",
        module="diabetes",
        source_document="x",
        source_text="Insulin-treated diabetes.",
        start=0,
        end=24,
    )
    assert ret.retrieve(req, "bm25").citations
    assert score_sources([["a"], ["a", "b"]], ["b"])["mrr"] == 0.5


def test_judgment_prompt_withholds_outcomes_and_rejects_fabricated_citations(
    workspace, monkeypatch, tmp_path
):
    app, _ = workspace
    app.state.workflow.config.llm.max_input_chars = 30000

    def fake(self, system, payload, contract):
        assert "expected_outcome" not in payload and "rule_outcome" not in payload
        assert "assessment_outcome" not in payload
        return ExperimentalJudgment(
            assessment_outcome="insufficient_information",
            explanation="Experimental response.",
            source_ids=["FABRICATED"],
        )

    monkeypatch.setattr(OllamaClient, "generate", fake)
    path = tmp_path / "judgment.json"
    run_judgment_study(
        app.state.workflow, ROOT / "data/cases/gold/workflow_expectations.json", path, 1
    )
    result = json.loads(path.read_text())
    assert result["completed"] == 0
    assert result["rows"][0]["status"] == "failed"
    assert result["authoritative_results_modified"] is False


def test_indicator_example_matches_schema():
    example = IndicatorRequest.model_validate_json(
        (ROOT / "examples/indicator_request.json").read_text()
    )
    assert example.indicator_text == example.source_text
