"""End-to-end checks for isolated reasoning and retrieval experiments."""

import csv
import json
from pathlib import Path

from occupational_fitness_rag.evaluation.model_judgment import (
    ExperimentalJudgment,
    run_judgment_study,
)
from occupational_fitness_rag.evaluation.rag_comparison import run_rag_comparison
from occupational_fitness_rag.evaluation.reasoning import audit_case, run_reasoning_study
from occupational_fitness_rag.pipeline.workflow import OccupationalFitnessWorkflow

ROOT = Path(__file__).resolve().parents[1]


def offline_workflow():
    return OccupationalFitnessWorkflow(ROOT / "configs/workflow.offline.yaml")


def test_reasoning_audit_links_patient_quotes_and_pdf_sources(tmp_path):
    workflow = offline_workflow()
    summary = run_reasoning_study(
        workflow,
        ROOT / "data/cases/gold/workflow_expectations.json",
        tmp_path / "reasoning",
    )
    report = json.loads((tmp_path / "reasoning/results.json").read_text(encoding="utf-8"))
    assert summary["cases"] == summary["passed"] == 23
    assert report["authoritative_results_modified"] is False
    assert {row["module"] for row in report["records"]} == {
        "all",
        "hypertension",
        "vision",
        "hearing",
        "blackout",
        "diabetes",
    }
    vision = next(row for row in report["records"] if row["case_id"] == "SYN-EXT-018")
    assert vision["provisional_outcome"] == "does_not_meet_standard"
    assert any(
        cite["source_id"] == "AFTD2022-VIS-COM-007" and cite["verified_against_source"]
        for trace in vision["rule_traces"]
        for cite in trace["guideline_evidence"]
    )
    assert all(
        fact["grounded_in_note"]
        for row in report["records"]
        for trace in row["rule_traces"]
        for fact in trace["patient_facts"]
    )
    assert "Evidence-linked reasoning audit" in (tmp_path / "reasoning/index.html").read_text(
        encoding="utf-8"
    )


def test_reasoning_audit_rejects_changed_guideline_text(monkeypatch):
    workflow = offline_workflow()
    original = workflow.assess
    fixture = json.loads(
        (ROOT / "data/cases/gold/workflow_expectations.json").read_text(encoding="utf-8")
    )
    label = next(x for x in fixture["cases"] if x["case_id"] == "SYN-EXT-018")

    def tampered_assessment(case):
        result, evidence, note = original(case)
        item = evidence.evidence_items[0]
        corrupted = item.citations[0].model_copy(update={"source_text": "Altered guideline"})
        changed_item = item.model_copy(update={"citations": [corrupted, *item.citations[1:]]})
        changed_pack = evidence.model_copy(
            update={"evidence_items": [changed_item, *evidence.evidence_items[1:]]}
        )
        return result, changed_pack, note

    monkeypatch.setattr(workflow, "assess", tampered_assessment)
    audit = audit_case(workflow, label)
    assert audit["passed"] is False
    assert any(
        trace["checks"]["guideline_text_verified"] is False for trace in audit["rule_traces"]
    )


def test_four_method_comparison_uses_same_module_boundary(tmp_path):
    workflow = offline_workflow()
    summary = run_rag_comparison(
        workflow,
        ROOT / "data/cases/gold/indicator_queries.json",
        ROOT / "data/cases/gold/complex_notes.json",
        tmp_path / "comparison",
    )
    report = json.loads((tmp_path / "comparison/results.json").read_text(encoding="utf-8"))
    assert summary["queries"] == 40
    assert summary["rows"] == 40 * 4 * 4
    assert set(report["methods"]) == {"vector", "bm25", "hybrid", "graph"}
    source_modules = {
        source_id: {
            rule["module"] for rule in workflow.book.rules if source_id in rule["source_ids"]
        }
        for source_id in workflow.catalogue.units
    }
    for row in report["rows"]:
        assert row["filters"]["module"] == row["module"]
        assert all(
            row["module"] in source_modules[source_id]
            for candidate in row["ranked_candidates"]
            for source_id in candidate["source_ids"]
        )
    assert report["clinical_validation"] is False
    errors = json.loads((tmp_path / "comparison/error_analysis.json").read_text(encoding="utf-8"))
    assert set(errors["misses_by_method"]) == {"vector", "bm25", "hybrid", "graph"}
    with (tmp_path / "comparison/review_queue.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        assert len(list(csv.DictReader(stream))) == 40


def test_holdout_notes_remain_separate_from_development_queries(tmp_path):
    fixture = json.loads(
        (ROOT / "data/cases/holdout/complex_notes.json").read_text(encoding="utf-8")
    )
    assert fixture["split"] == "frozen_synthetic_holdout"
    assert fixture["independent_clinical_gold"] is False
    assert len(fixture["cases"]) == 10
    development = json.loads(
        (ROOT / "data/cases/gold/complex_notes.json").read_text(encoding="utf-8")
    )
    development_passages = {
        paragraph for case in development["cases"] for paragraph in case["paragraphs"]
    }
    for item in fixture["cases"]:
        note = (ROOT / "data/cases/holdout/notes" / f"{item['id']}.txt").read_text(
            encoding="utf-8"
        )
        assert note.startswith(f"Case ID: {item['id']}\n")
        assert all(paragraph in note for paragraph in item["paragraphs"])
        assert not set(item["paragraphs"]) & development_passages
    summary = run_rag_comparison(
        offline_workflow(),
        ROOT / "data/cases/holdout/indicator_queries.json",
        ROOT / "data/cases/holdout/complex_notes.json",
        tmp_path / "holdout",
    )
    assert summary["queries"] == 10
    report = json.loads((tmp_path / "holdout/results.json").read_text(encoding="utf-8"))
    assert report["fixture_splits"] == ["frozen_synthetic_holdout"] * 2
    assert report["source_labels_reviewed"] is False
    reasoning = run_reasoning_study(
        offline_workflow(),
        ROOT / "data/cases/holdout/reasoning_cases.json",
        tmp_path / "holdout_reasoning",
    )
    assert reasoning["cases"] == reasoning["passed"] == 10
    audit = json.loads((tmp_path / "holdout_reasoning/results.json").read_text(encoding="utf-8"))
    assert audit["development_label_agreement"] is None
    assert audit["outcome_labels_present"] is False
    assert all(row["expected_development_outcome"] is None for row in audit["records"])
    with (tmp_path / "holdout_reasoning/case_review_queue.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        review_rows = list(csv.DictReader(stream))
    assert len(review_rows) == 10
    assert all(not row["clinician_assessed_outcome"] for row in review_rows)


def test_model_reasoning_rejects_unverified_citations(monkeypatch, tmp_path):
    import occupational_fitness_rag.evaluation.model_judgment as study

    class InvalidCitationClient:
        def __init__(self, config):
            self.config = config
            self.calls = []
            self.resolved_digest = "synthetic-model"

        def generate(self, system, payload, contract):
            assert "rule_outcome" not in payload
            return ExperimentalJudgment(
                assessment_outcome="temporarily_unfit",
                explanation="A candidate explanation requiring review.",
                source_ids=["NOT-A-SUPPLIED-SOURCE"],
                fact_fields=["blackout.unverified"],
            )

    monkeypatch.setattr(study, "OllamaClient", InvalidCitationClient)
    output = tmp_path / "model.json"
    summary = run_judgment_study(
        offline_workflow(),
        ROOT / "data/cases/gold/workflow_expectations.json",
        output,
        case_ids=["SYN-EXT-003"],
    )
    row = json.loads(output.read_text(encoding="utf-8"))["rows"][0]
    assert summary["completed"] == 0
    assert row["status"] == "rejected_unsupported_citation"
    assert row["invalid_source_ids"] == ["NOT-A-SUPPLIED-SOURCE"]
    assert row["invalid_fact_fields"] == ["blackout.unverified"]
