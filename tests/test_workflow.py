import json
from pathlib import Path

import pytest

from occupational_fitness_rag.case_intake.traceable import (
    extract_traceable_file,
    extract_traceable_text,
)
from occupational_fitness_rag.evaluation.workflow import evaluate_workflow
from occupational_fitness_rag.pipeline.workflow import OccupationalFitnessWorkflow
from occupational_fitness_rag.provenance import digest
from occupational_fitness_rag.reporting.builder import build_review_note, render_reports
from occupational_fitness_rag.schemas.workflow import ClinicalCase, Fact

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def workflow():
    return OccupationalFitnessWorkflow(ROOT / "configs/workflow.offline.yaml")


def _case(workflow, fields, modules=None, text=""):
    text += "\n" + "\n".join(f"{k} = {json.dumps(v)}" for k, v in fields.items())
    return extract_traceable_text(
        text, "TEST-001", "fixture.txt", workflow.book.field_specs, modules=modules
    )


def test_all_authored_workflow_expectations(workflow, tmp_path):
    result = evaluate_workflow(
        workflow, ROOT / "data/cases/gold/workflow_expectations.json", tmp_path / "metrics.json"
    )
    assert result["passed"] == result["cases"] == 23
    assert result["clinical_validation"] is False


def test_engine_uses_ruleset_outcome_precedence(workflow):
    assert [value.value for value in workflow.book.precedence] == workflow.book.metadata[
        "outcome_precedence"
    ]


@pytest.mark.parametrize(
    "source",
    sorted((ROOT / "data/cases/nurse_notes").glob("*.txt"))
    + sorted((ROOT / "data/cases/synthetic_expansion").glob("*.txt")),
    ids=lambda p: p.stem,
)
def test_every_supplied_and_added_case_completes_five_modules(workflow, source):
    case = extract_traceable_file(source, workflow.book.field_specs)
    result, evidence, note = workflow.assess(case)
    assert len(result.modules) == 5
    assert not evidence.unresolved_requests
    assert note.status == "DRAFT"


def test_corrected_eyes_remain_traceable_parents(workflow):
    case = extract_traceable_file(
        ROOT / "data/cases/nurse_notes/SYN-M2-002.txt", workflow.book.field_specs
    )
    assert case.facts["vision.corrected.right.snellen"].value == "6/6"
    assert case.facts["vision.corrected.left.snellen"].status == "present"
    assert case.facts["vision.corrected.better_eye"].derived_from == [
        "vision.corrected.right.snellen",
        "vision.corrected.left.snellen",
    ]


@pytest.mark.parametrize(
    "systolic,diastolic,expected",
    [(170, 100, False), (170.01, 100, True), (170, 100.01, True), (169.99, 99.99, False)],
)
def test_persistent_pressure_boundaries(workflow, systolic, diastolic, expected):
    case = _case(
        workflow,
        {
            "cardiovascular.blood_pressure.persistent_systolic": systolic,
            "cardiovascular.blood_pressure.persistent_diastolic": diastolic,
        },
        ["hypertension"],
    )
    rule = workflow.book.evaluate(case).rules_evaluated[0]
    assert (rule.result == "triggered") is expected


def test_single_pressure_does_not_become_persistent(workflow):
    case = _case(workflow, {}, ["hypertension"], "BP 200/120 mmHg. No repeat BP is available.")
    result = workflow.book.evaluate(case)
    assert case.facts["cardiovascular.blood_pressure.observed_systolic"].value == 200
    assert case.facts["cardiovascular.blood_pressure.persistent_systolic"].status == "unknown"
    assert result.assessment_outcome == "insufficient_information"


@pytest.mark.parametrize(
    "note,field",
    [
        ("No blackout history information is available.", "blackout.occurred"),
        ("No history of diabetes documented.", "diabetes.present"),
        ("Blackouts not assessed.", "blackout.occurred"),
        ("Diabetes status unknown.", "diabetes.present"),
    ],
)
def test_unrecorded_history_is_not_negative(workflow, note, field):
    assert _case(workflow, {}, text=note).facts[field].status == "unknown"


def test_exact_case_spans_and_no_frequency_invention(workflow):
    case = extract_traceable_file(
        ROOT / "data/cases/nurse_notes/SYN-M2-009.txt", workflow.book.field_specs
    )
    assert case.facts["hearing.unaided_better_ear_average_db"].value == 45
    assert case.facts["hearing.average_frequencies_khz"].status == "unknown"
    for fact in case.facts.values():
        for span in fact.evidence:
            assert case.source_text[span.start : span.end] == span.quote
    rule = next(
        x
        for x in workflow.book.evaluate(case).rules_evaluated
        if x.rule_id == "HEAR-COM-UNCONDITIONAL-001"
    )
    assert rule.result == "unknown"


@pytest.mark.parametrize(
    "fields,rule_id,expected",
    [
        (
            {"vision.uncorrected.right.snellen": "6/18", "vision.uncorrected.left.snellen": "6/9"},
            "VIS-COM-ACUITY-UNCONDITIONAL-001",
            False,
        ),
        (
            {"vision.uncorrected.right.snellen": "6/24", "vision.uncorrected.left.snellen": "6/9"},
            "VIS-COM-ACUITY-UNCONDITIONAL-001",
            True,
        ),
        (
            {"vision.uncorrected.right.snellen": "6/12", "vision.uncorrected.left.snellen": "6/12"},
            "VIS-COM-ACUITY-UNCONDITIONAL-001",
            True,
        ),
        (
            {
                "hearing.clinical_assessment": "possible_hearing_loss",
                "hearing.average_frequencies_khz": [0.5, 1, 2, 3],
                "hearing.unaided_better_ear_average_db": 40,
            },
            "HEAR-COM-UNCONDITIONAL-001",
            True,
        ),
        (
            {
                "hearing.clinical_assessment": "possible_hearing_loss",
                "hearing.average_frequencies_khz": [0.5, 1, 2, 4],
                "hearing.unaided_better_ear_average_db": 45,
            },
            "HEAR-COM-UNCONDITIONAL-001",
            False,
        ),
    ],
)
def test_numeric_and_unit_context(workflow, fields, rule_id, expected):
    result = workflow.book.evaluate(_case(workflow, fields))
    rule = next(x for x in result.rules_evaluated if x.rule_id == rule_id)
    assert (rule.result == "triggered") is expected


@pytest.mark.parametrize(
    "name,value",
    [
        ("diabetes.present", "false"),
        ("hearing.unaided_better_ear_average_db", True),
        ("cardiovascular.blood_pressure.persistent_systolic", 999),
        ("blackout.episodes_separated_by_24h_count", 0),
        ("vision.uncorrected.left.snellen", "6/0"),
    ],
)
def test_bad_types_ranges_abstain(workflow, name, value):
    case = _case(workflow, {name: value})
    assert case.facts[name].status == "requires_confirmation"
    assert case.facts[name].value is None


def test_conflicting_assertions_abstain(workflow):
    case = _case(workflow, {"diabetes.present": True}, text="No diabetes.")
    assert case.facts["diabetes.present"].status == "conflicting"
    assert workflow.book.evaluate(case).assessment_outcome == "insufficient_information"


def test_cross_field_conflict_never_fast_paths(workflow):
    case = _case(
        workflow,
        {"diabetes.present": False, "diabetes.treatment_category": "insulin"},
        ["diabetes"],
    )
    result = workflow.book.evaluate(case)
    assert result.route == "human_review"
    assert result.assessment_outcome == "insufficient_information"


def test_three_cardiovascular_cases_are_escalated(workflow):
    for n in (4, 5, 6):
        case = extract_traceable_file(
            ROOT / f"data/cases/nurse_notes/SYN-M2-{n:03d}.txt", workflow.book.field_specs
        )
        result = workflow.book.evaluate(case)
        assert result.route == "human_review"
        assert any(x.startswith("OUTSIDE_HYPERTENSION_SCOPE") for x in result.processing_warnings)


def test_rag_cannot_mutate_rules_and_covers_every_request(workflow):
    case = _case(workflow, {}, text="Reports reduced hearing.")
    result = workflow.red_flag.evaluate(case)
    before = digest(result)
    evidence = workflow.retriever.run(result.rag_input())
    assert before == digest(result) == evidence.rule_result_sha256
    assert len(evidence.evidence_items) == len(result.rag_requests)
    assert not evidence.unresolved_requests
    for item in evidence.evidence_items:
        assert {c.source_id for c in item.citations} == set(item.requested_source_ids)


def test_request_identity_cannot_switch_source(workflow):
    result = workflow.red_flag.evaluate(_case(workflow, {}))
    rag_input = result.rag_input()
    request = rag_input.rag_requests[0].model_copy(update={"source_ids": ["AFTD2022-HEAR-COM-002"]})
    corrupt = rag_input.model_copy(update={"rag_requests": [request, *rag_input.rag_requests[1:]]})
    with pytest.raises(ValueError, match="authoritative"):
        workflow.retriever.run(corrupt)


def test_fast_path_still_binds_sources_without_ranking(workflow):
    case = extract_traceable_file(
        ROOT / "data/cases/synthetic_expansion/SYN-EXT-001.txt", workflow.book.field_specs
    )
    result, evidence, note = workflow.assess(case)
    assert result.route == "fast_path"
    assert evidence.retrieval["ranking_calls"] == 0
    assert evidence.evidence_items
    assert note.status == "DRAFT" and note.signed_at is None


def test_source_citations_are_commercial_table_regions(workflow):
    citation = workflow.catalogue.citation("AFTD2022-HTN-COM-001")
    assert citation.pdf_page == 99 and citation.printed_page == 88
    assert "> 170" in citation.evidence_text
    assert "> 200" not in citation.evidence_text
    hearing = workflow.catalogue.citation("AFTD2022-HEAR-COM-002")
    assert "≥ 40" in hearing.evidence_text and hearing.pdf_page == 120


def test_model_fields_reject_forged_source_span(workflow):
    case = _case(workflow, {"diabetes.present": False})
    data = case.model_dump(mode="json")
    data["facts"]["diabetes.present"]["evidence"][0]["quote"] = "invented"
    with pytest.raises(ValueError, match="citation"):
        ClinicalCase.model_validate(data)
    with pytest.raises(ValueError):
        Fact(value=True, status="present")


def test_report_rejects_cross_case_evidence(workflow):
    case = _case(workflow, {})
    result, evidence, _ = workflow.assess(case)
    with pytest.raises(ValueError, match="Case ID"):
        build_review_note(case, result, evidence.model_copy(update={"case_id": "WRONG"}))


def test_html_escapes_input(workflow, tmp_path):
    case = _case(workflow, {}, text="<script>alert('x')</script>")
    result, evidence, note = workflow.assess(case)
    html = render_reports(case, result, evidence, note, ROOT, tmp_path)["draft_report.html"]
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_run_replay_and_tamper_detection(workflow, tmp_path):
    source = ROOT / "data/cases/nurse_notes/SYN-M2-009.txt"
    output = workflow.run_file(source, tmp_path)
    assert workflow.verify_run(output)["status"] == "verified"
    assert workflow.run_file(source, tmp_path) == output
    with (output / "rule_result.json").open("a", encoding="utf-8") as stream:
        stream.write(" ")
    with pytest.raises(ValueError, match="fingerprint"):
        workflow.verify_run(output)


def test_source_index_fingerprint_mismatch(workflow, tmp_path):
    from occupational_fitness_rag.ingestion.source_catalogue import SourceCatalogue

    data = json.loads((ROOT / workflow.config.catalogue).read_text(encoding="utf-8"))
    data["units"][0]["evidence_text"] = "fabricated evidence"
    target = tmp_path / "corrupt.json"
    target.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="fingerprint"):
        SourceCatalogue(ROOT, target)


def test_empty_or_partial_predictions_are_penalized():
    from occupational_fitness_rag.case_intake.evaluation import exact_field_accuracy

    gold = [
        {"case_id": "a", "structured_facts": {"bp": 120}},
        {"case_id": "b", "structured_facts": {"bp": 130}},
    ]
    assert exact_field_accuracy([], gold)["field_accuracy"] == 0
    metrics = exact_field_accuracy(gold[:1], gold)
    assert metrics["field_accuracy"] == 0.5 and metrics["case_coverage"] == 0.5


def test_unrelated_query_has_no_lexical_evidence():
    from occupational_fitness_rag.indexing.memory_store import InMemoryVectorStore
    from occupational_fitness_rag.ingestion.models import GuidelineChunk

    store = InMemoryVectorStore([GuidelineChunk("id", "blood pressure", "2", "BP", [1], {})])
    assert store.search("zzzzunrelated", {}, 3) == []
    store.add([GuidelineChunk("id", "blood pressure", "2", "BP", [1], {})])
    assert len(store.docs) == 1


def test_pdf_input_keeps_page_and_original_bytes(workflow, tmp_path):
    import pymupdf

    from occupational_fitness_rag.provenance import sha256_bytes

    path = tmp_path / "SYN-PDF-001.pdf"
    with pymupdf.open() as document:
        document.new_page().insert_text((72, 72), "Synthetic case. No diabetes.")
        document.new_page().insert_text((72, 72), "No history of blackouts.")
        document.save(path)
    case = extract_traceable_file(path, workflow.book.field_specs)
    assert case.source_kind == "pdf"
    assert case.source_sha256 == sha256_bytes(path.read_bytes())
    assert case.facts["diabetes.present"].evidence[0].pdf_page == 1
    assert case.facts["blackout.occurred"].evidence[0].pdf_page == 2


def test_blank_pdf_page_is_not_silently_ignored(workflow, tmp_path):
    import pymupdf

    path = tmp_path / "SYN-SCAN-001.pdf"
    with pymupdf.open() as document:
        document.new_page().insert_text((72, 72), "Synthetic case. No diabetes.")
        document.new_page()
        document.save(path)
    with pytest.raises(ValueError, match="page 2.*OCR"):
        extract_traceable_file(path, workflow.book.field_specs)
