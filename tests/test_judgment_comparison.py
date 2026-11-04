"""Isolation and causal-comparison contracts, not clinical accuracy tests."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from occupational_fitness_rag.evaluation.comparison_corpus import (
    build_comparison_corpus,
    verify_corpus,
)
from occupational_fitness_rag.evaluation.comparison_report import render_comparison
from occupational_fitness_rag.evaluation.judgment_comparison import (
    bounded_answer_schema,
    judgment_request,
    load_labels,
    make_payload,
    summarize,
    validate_answer,
)
from occupational_fitness_rag.evaluation.model_judgment import ExperimentalJudgment
from occupational_fitness_rag.ingestion.source_catalogue import SourceCatalogue
from occupational_fitness_rag.rules.engine import RuleBook

ROOT = Path(__file__).resolve().parents[1]


def test_identifier_constraints_do_not_leak_reference_outcomes():
    payload = {
        "verified_patient_facts": {"hearing.concern": {"value": True}},
        "guideline_evidence": [{"source_id": "original-source"}],
    }
    schema = bounded_answer_schema(payload)
    assert schema["properties"]["source_ids"]["items"]["enum"] == ["original-source"]
    assert schema["properties"]["fact_fields"]["items"]["enum"] == ["hearing.concern"]
    assert schema["properties"]["fact_fields"]["maxItems"] == 1
    assert schema["properties"]["source_ids"]["maxItems"] == 1
    assert schema["properties"]["explanation"]["maxLength"] == 2000
    assert len(schema["properties"]["assessment_outcome"]["enum"]) == 5
    empty = bounded_answer_schema({"verified_patient_facts": {}, "guideline_evidence": []})
    assert empty["properties"]["source_ids"]["maxItems"] == 0
    request = judgment_request(
        {"context_length": 8192, "output_tokens": 1536}, "qwen3.5:4b", payload
    )
    assert request["think"] is False
    assert "reference_outcome" not in json.dumps(request)


@pytest.fixture
def workflow():
    return SimpleNamespace(
        root=ROOT,
        book=RuleBook(ROOT / "configs/rules/austroads_commercial_v1.yaml"),
        catalogue=SourceCatalogue(ROOT, ROOT / "data/knowledge/processed/source_catalogue.json"),
    )


def test_expansion_keeps_originals_and_pdf_identity(workflow, tmp_path):
    corpus = build_comparison_corpus(workflow, tmp_path / "corpus.json")
    assert len(corpus["units"]) > 28
    ids = {u["source_id"] for u in corpus["units"]}
    assert len({(u["module"], u["evidence_text"].strip()) for u in corpus["units"]}) == len(
        corpus["units"]
    )
    assert any(u.get("alternate_regions") for u in corpus["units"])
    assert set(workflow.catalogue.units) <= ids
    assert {u["module"] for u in corpus["units"]} == {
        "hypertension",
        "vision",
        "hearing",
        "blackout",
        "diabetes",
    }
    assert all(u["licence_context"] != "private" for u in corpus["units"])
    tables = [
        u for u in corpus["units"] if u["table_row"] == "Commercial standards with qualifications"
    ]
    assert all("Commercial standards" in u["evidence_text"] for u in tables)
    assert not any(
        "3.3.1" == u["section"] and u["source_id"].startswith("AFTD2022-EXP")
        for u in corpus["units"]
    )
    corpus["units"][0]["evidence_text"] += " invented threshold"
    with pytest.raises(ValueError, match="fingerprint"):
        verify_corpus(ROOT, corpus)


def test_no_label_leak_and_no_source_backfill():
    case = {
        "modules_requested": ["hearing"],
        "source_text": "No measured hearing threshold.",
        "facts": {
            "hearing.threshold": {"status": "unknown", "value": None, "evidence": []},
            "hearing.concern": {
                "status": "present",
                "value": True,
                "evidence": [{"quote": "hearing"}],
            },
        },
    }
    units = {
        "heard": {
            "section": "4.3",
            "pdf_page": 120,
            "printed_page": 109,
            "evidence_text": "Original guideline.",
        }
    }
    payload, excluded = make_payload(case, units, [], {"evidence_max_bytes": 1000})
    assert payload["guideline_evidence"] == []
    assert "hearing.threshold" not in payload["verified_patient_facts"]
    assert "expected_outcome" not in json.dumps(payload)
    assert excluded == []
    answer = ExperimentalJudgment(
        assessment_outcome="insufficient_information",
        explanation="No standard supplied.",
        source_ids=[],
    )
    validate_answer(answer, payload, "no_evidence")
    with pytest.raises(ValueError, match="requires"):
        validate_answer(answer, payload, "hybrid")
    answer = answer.model_copy(update={"source_ids": ["invented"]})
    with pytest.raises(ValueError, match="not supplied"):
        validate_answer(answer, payload, "no_evidence")


def test_budget_excludes_complete_passages_instead_of_truncating():
    case = {"modules_requested": ["vision"], "source_text": "Original note.", "facts": {}}
    units = {
        "s1": {"section": "10", "pdf_page": 220, "printed_page": 209, "evidence_text": "X" * 1000}
    }
    payload, excluded = make_payload(case, units, ["s1"], {"evidence_max_bytes": 200})
    assert not payload["guideline_evidence"] and excluded == ["s1"]


def test_failures_are_not_dropped_and_pairs_are_same_patient_model_repeat():
    base = {
        "case_id": "A",
        "cohort": "engineering",
        "module": "vision",
        "model": "llama",
        "repeat": 0,
        "reference_outcome": "temporarily_unfit",
        "seconds": 1,
        "input_snapshot": {
            "guideline_evidence": [],
            "verified_patient_facts": {},
            "nurse_note": "<script>alert(1)</script>",
        },
    }
    rows = [
        dict(
            base,
            method="hybrid",
            status="completed",
            reference_agreement=False,
            answer={
                "assessment_outcome": "insufficient_information",
                "explanation": "Missing",
                "source_ids": [],
            },
        ),
        dict(
            base,
            method="vector",
            status="completed",
            reference_agreement=True,
            answer={
                "assessment_outcome": "temporarily_unfit",
                "explanation": "Evidence",
                "source_ids": [],
            },
        ),
        dict(base, method="vector", repeat=1, status="failed", error="Timeout"),
    ]
    summary = summarize(rows)
    vector = next(m for m in summary["metrics"] if m["method"] == "vector")
    assert vector["agreement_all_runs"] == 0.5 and vector["failures"] == 1
    assert summary["paired_transitions"][0]["transition"] == "wrong_to_correct"
    html = render_comparison(rows, summary)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_existing_cohorts_stay_separate(workflow):
    config = {
        "cohorts": {
            "engineering": "data/cases/gold/workflow_expectations.json",
            "complex": "data/cases/gold/validation_complex_expectations.json",
        }
    }
    labels = load_labels(ROOT, config, workflow)
    assert sum(label["cohort"] == "engineering" for label in labels) == 23
    assert sum(label["cohort"] == "complex" for label in labels) == 10
    assert all(label["clinical_review_status"] == "pending" for label in labels)
