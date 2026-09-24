import json
from pathlib import Path

import pytest

from occupational_fitness_rag.case_intake.semantic_review import (
    SemanticReviewResponse,
    SourceReviewResponse,
    apply_review,
    compare_observations,
    review_payload,
    semantic_review,
)
from occupational_fitness_rag.case_intake.traceable import extract_traceable_text
from occupational_fitness_rag.evaluation.semantic_review import run_semantic_review_study
from occupational_fitness_rag.llm import OllamaClient
from occupational_fitness_rag.pipeline.config import LLMConfig
from occupational_fitness_rag.pipeline.workflow import OccupationalFitnessWorkflow
from occupational_fitness_rag.provenance import digest
from occupational_fitness_rag.schemas.workflow import ClinicalCase, Fact, WorkflowRoute

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def workflow():
    return OccupationalFitnessWorkflow(ROOT / "configs/workflow.offline.yaml")


def make_case(workflow, text="No diabetes.", modules=None):
    return extract_traceable_text(
        text,
        "SEMANTIC-TEST",
        "note.txt",
        workflow.book.field_specs,
        modules=modules or ["diabetes"],
    )


def answer(payload, issues=()):
    if "FIELDS_TO_CHECK" in payload:
        flagged = {x["field"] for x in issues}
        return SourceReviewResponse(
            observations=[
                {
                    "field": key,
                    "value": None if key in flagged else False,
                    "status": "uncertain" if key in flagged else "documented",
                    "quote": payload["ORIGINAL_NOTE"],
                    "explanation": "Synthetic source reading for the integration test.",
                }
                for key in payload["FIELDS_TO_CHECK"]
            ]
        )
    return SemanticReviewResponse(
        checked_fields=list(payload["extracted_facts"]),
        issues=list(issues),
    )


def concern(quote="No diabetes.", field="diabetes.present", kind="negation"):
    return {
        "field": field,
        "kind": kind,
        "quote": quote,
        "explanation": "The extracted assertion needs confirmation against the original note.",
    }


def test_second_pass_precedes_rules_and_preserves_original_values(workflow, monkeypatch):
    workflow.config.llm.enabled = True
    monkeypatch.setattr(OllamaClient, "extract", lambda *a: {"proposals": []})

    def review(self, system, payload, contract):
        assert "assessment_outcome" not in payload and "evidence" not in payload
        assert "EXTRACTED_FACTS" not in payload and "value" not in payload
        return answer(payload, [concern()])

    monkeypatch.setattr(OllamaClient, "generate", review)
    original_evaluate = workflow.book.evaluate

    def evaluate(case):
        assert case.facts["diabetes.present"].status == "requires_confirmation"
        assert case.facts["diabetes.present"].value is None
        assert (
            case.extraction_metadata["semantic_review"]["original_facts"]["diabetes.present"][
                "value"
            ]
            is False
        )
        return original_evaluate(case)

    monkeypatch.setattr(workflow.book, "evaluate", evaluate)
    case, result, evidence, note = workflow.from_text("No diabetes.", "SEMANTIC-TEST", ["diabetes"])
    assert result.route == WorkflowRoute.HUMAN
    assert any("semantic review" in line.lower() for line in note.review_checklist)
    assert digest(case) == result.case_sha256
    assert evidence.integrity["rule_result_fields_modified_by_rag"] is False


def test_no_issue_does_not_claim_accuracy_or_upgrade_unknowns(workflow, monkeypatch):
    case = make_case(workflow)
    monkeypatch.setattr(OllamaClient, "generate", lambda self, s, p, c: answer(p))
    updated, audit = semantic_review(case, workflow.book.field_specs, LLMConfig(enabled=True))
    assert updated.facts == case.facts
    assert audit["status"] == "completed_no_issues"
    assert audit["accuracy_verified"] is False
    assert audit["output_facts_sha256"] == audit["input_facts_sha256"]


@pytest.mark.parametrize(
    "mutation",
    [
        "bad_quote",
        "bad_field",
        "wrong_module",
        "missing_checked",
        "duplicate_checked",
        "extra_value",
    ],
)
def test_invalid_response_cannot_change_facts(workflow, monkeypatch, mutation):
    case = make_case(workflow)
    response = {
        "observations": [
            {
                "field": "diabetes.present",
                "value": True,
                "status": "documented",
                "quote": "No diabetes.",
                "explanation": "Synthetic mismatch for validation testing.",
            }
        ]
    }
    if mutation == "bad_quote":
        response["observations"][0]["quote"] = "Invented patient history."
    elif mutation == "bad_field":
        response["observations"][0]["field"] = "invented.field"
    elif mutation == "wrong_module":
        response["observations"].append(
            {**response["observations"][0], "field": "blackout.occurred"}
        )
    elif mutation == "missing_checked":
        response["observations"] = []
    elif mutation == "duplicate_checked":
        response["observations"] *= 2
    else:
        response["observations"][0]["replacement_value"] = True
    monkeypatch.setattr(OllamaClient, "generate", lambda *a: response)
    updated, audit = semantic_review(case, workflow.book.field_specs, LLMConfig(enabled=True))
    assert audit["status"] == "unavailable_or_invalid"
    assert audit["manual_review_required"]
    assert updated.facts == case.facts
    assert workflow.book.evaluate(updated).route == WorkflowRoute.HUMAN


def test_independent_source_reading_distinguishes_absence_from_missing(workflow):
    case = make_case(workflow)
    payload = review_payload(case, workflow.book.field_specs)
    reading = {
        "field": "diabetes.present",
        "value": False,
        "status": "documented",
        "quote": "No diabetes.",
        "explanation": "The patient explicitly has no diabetes.",
    }
    assert not compare_observations(case, {"observations": [reading]}, payload).issues
    # An independently absent observation must not be promoted to a replacement value.
    missing = {**reading, "value": None, "status": "not_documented", "quote": ""}
    result = compare_observations(case, {"observations": [missing]}, payload)
    assert result.issues[0].kind == "unsupported"
    assert result.issues[0].quote == case.facts["diabetes.present"].evidence[0].quote


def test_quarantine_propagates_to_derived_facts_and_keeps_page(workflow):
    case = make_case(workflow, "Vision 6/6.", ["vision"])
    # Construct a source-bound extraction with a derived better-eye value.
    from occupational_fitness_rag.schemas.workflow import TextSpan

    span = TextSpan(start=0, end=11, quote="Vision 6/6.", line_start=1, line_end=1, pdf_page=2)
    facts = dict(case.facts)
    parent = "vision.uncorrected.right.snellen"
    derived = "vision.uncorrected.better_eye"
    facts[parent] = Fact(value="6/6", status="present", evidence=[span])
    facts[derived] = Fact(value="6/6", status="present", evidence=[span], derived_from=[parent])
    case = ClinicalCase.model_validate({**case.model_dump(), "facts": facts})
    payload = review_payload(case, workflow.book.field_specs)
    updated, audit = apply_review(
        case, answer(payload, [concern("Vision 6/6.", parent, "subject")]), payload, [(0, 11, 2)]
    )
    assert set(audit["quarantined_fields"]) == {parent, derived}
    assert updated.facts[derived].value is None
    assert audit["issues"][0]["evidence"][0]["pdf_page"] == 2


def test_omission_never_inserts_a_model_guessed_value(workflow):
    case = make_case(workflow)
    facts = {**case.facts, "diabetes.present": Fact()}
    case = ClinicalCase.model_validate({**case.model_dump(), "facts": facts})
    payload = review_payload(case, workflow.book.field_specs)
    updated, audit = apply_review(case, answer(payload, [concern(kind="omission")]), payload)
    assert updated.facts["diabetes.present"].status == "requires_confirmation"
    assert updated.facts["diabetes.present"].value is None
    assert audit["manual_review_required"]


def test_timeout_context_budget_and_disabled_are_explicit(workflow, monkeypatch):
    case = make_case(workflow)

    def unavailable(*a):
        raise TimeoutError("private source must not appear in public error")

    monkeypatch.setattr(OllamaClient, "generate", unavailable)
    _, audit = semantic_review(case, workflow.book.field_specs, LLMConfig(enabled=True))
    assert audit["error_type"] == "TimeoutError"
    assert "private source" not in json.dumps(audit)
    _, budget = semantic_review(
        case, workflow.book.field_specs, LLMConfig(enabled=True, max_input_chars=100)
    )
    assert budget["status"] == "skipped_context_budget"
    assert budget["manual_review_required"]
    unchanged, disabled = semantic_review(case, workflow.book.field_specs, LLMConfig())
    assert disabled["status"] == "disabled"
    assert unchanged.facts == case.facts
    assert not disabled["manual_review_required"]


def test_one_invalid_response_can_be_retried_without_accepting_partial_facts(workflow, monkeypatch):
    case = make_case(workflow)
    calls = []

    def respond(self, system, payload, contract):
        calls.append(system)
        if len(calls) == 1:
            return SourceReviewResponse(observations=[])
        return answer(payload)

    monkeypatch.setattr(OllamaClient, "generate", respond)
    updated, audit = semantic_review(case, workflow.book.field_specs, LLMConfig(enabled=True))
    assert updated.facts == case.facts
    assert audit["status"] == "completed_no_issues"
    assert [x["status"] for x in audit["attempts"]] == ["invalid", "valid"]
    assert len(calls) == 2 and "previous response failed" in calls[1]


def test_review_study_hides_seeded_values_and_labels(workflow, monkeypatch, tmp_path):
    fixture = json.loads(
        (ROOT / "data/cases/gold/semantic_review_cases.json").read_text(encoding="utf-8")
    )
    fixture["cases"] = [fixture["cases"][0], fixture["cases"][6]]
    gold = tmp_path / "gold.json"
    gold.write_text(json.dumps(fixture))

    def respond(self, system, payload, contract):
        assert "expected_issue_fields" not in payload
        assert "EXTRACTED_FACTS" not in payload and "overrides" not in payload
        assert "diabetes.present" in payload["FIELDS_TO_CHECK"]
        return answer(payload)

    monkeypatch.setattr(OllamaClient, "generate", respond)
    output = tmp_path / "review.json"
    run_semantic_review_study(workflow, gold, output)
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["completed"] == 2
    assert result["exact_field_matches"] == 2
    assert result["clean_controls_with_flags"] == 0
    assert result["clinical_validation"] is False


def test_saved_review_is_visible_replayable_and_required(workflow, monkeypatch, tmp_path):
    workflow.config.llm.enabled = True
    monkeypatch.setattr(OllamaClient, "extract", lambda *a: {"proposals": [], "model": "llama3:8b"})
    monkeypatch.setattr(OllamaClient, "generate", lambda self, s, p, c: answer(p, [concern()]))
    source = tmp_path / "SEMANTIC-TEST.txt"
    source.write_text("No diabetes.", encoding="utf-8")
    stages = []
    run = workflow.run_file(source, tmp_path / "runs", ["diabetes"], progress=stages.append)
    assert stages.index("extraction") < stages.index("semantic_review") < stages.index("rules")
    assert workflow.verify_run(run)["rules_replayed"]
    for filename in ("draft_report.html", "draft_report.md"):
        report = (run / filename).read_text(encoding="utf-8")
        assert "Extraction semantic review" in report
        assert "llm_semantic_review.json" in report
        assert "does not establish clinical accuracy" in report
    html = (run / "draft_report.html").read_text(encoding="utf-8")
    assert "href='#case-line-1'" in html
    audit = json.loads((run / "llm_semantic_review.json").read_text(encoding="utf-8"))
    assert audit["quarantined_fields"] == ["diabetes.present"]
    evidence = json.loads((run / "evidence_pack.json").read_text(encoding="utf-8"))
    queries = [item["semantic_query"] for item in evidence["evidence_items"]]
    assert any("unconfirmed; source wording follows" in q for q in queries)
    (run / "llm_semantic_review.json").write_text("{}")
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        workflow.verify_run(run)
