import json
from collections import Counter

import pytest

from occupational_fitness_rag.evaluation.long_note_study import (
    classification,
    fact_checks,
    source_metrics,
    value_equal,
)
from tools.build_complex_long_cases import make_cases
from tools.export_complex_long_report import portable_html
from tools.run_complex_long_study import append, judgment_payload, records


def test_all_200_uploads_have_long_sentences_and_no_embedded_labels():
    cases = make_cases()
    assert (
        len(cases) == len({r["case_id"] for r in cases}) == len({r["text"] for r in cases}) == 200
    )
    assert len({r["family"] for r in cases}) == 40
    assert set(Counter(r["primary_module"] for r in cases).values()) == {40}
    assert sum(len(r["modules"]) > 1 for r in cases) == 40
    assert len({r["expected_outcome"] for r in cases}) == 5
    for r in cases:
        assert r["complexity"]["words"] >= 220
        assert r["complexity"]["long_sentences_35_words"] >= 3
        assert "AFTD2022" not in r["text"]
        assert "assessment_outcome" not in r["text"]
        assert "source_id" not in r["text"]


def test_numeric_checks_accept_float_encoding_without_promoting_boolean_zero():
    assert value_equal(45, 45.0)
    assert not value_equal(False, 0)
    assert not value_equal(True, 1.0)
    checked = fact_checks(
        {"hearing.db": {"status": "requires_confirmation", "value": 45.0}},
        [{"field": "hearing.db", "kind": "equals", "value": 45}],
    )
    assert not checked[0]["passed"]


def test_containment_recall_is_distinct_from_exact_id_and_never_double_counts():
    units = {"parent": {"covers_source_ids": ["a", "b"]}, "a": {"covers_source_ids": ["a"]}}
    s = source_metrics(["parent", "a"], ["a", "b"], units, 5)
    assert s["coverage_recall"] == 1
    assert s["exact_id_recall"] == 0.5
    assert s["mrr"] == 1


def test_failed_classification_is_in_accuracy_and_recall_denominators():
    labels = {
        "a": {"expected_outcome": "temporarily_unfit", "family": "same"},
        "b": {"expected_outcome": "temporarily_unfit", "family": "same"},
    }
    rows = [
        {"case_id": "a", "status": "completed", "assessment_outcome": "temporarily_unfit"},
        {"case_id": "b", "status": "failed"},
    ]
    result = classification(rows, labels, "workflow")
    assert result["engineering_reference_agreement_all_recorded"] == 0.5
    assert result["engineering_reference_agreement_accepted"] == 1
    assert result["balanced_accuracy_observed_classes"] == 0.5
    assert result["failed"] == 1


def test_judgment_uses_actual_verified_facts_and_ranked_evidence_only():
    case = {
        "case_id": "case",
        "facts": {
            "blackout.occurred": {
                "status": "present",
                "value": True,
                "evidence": [{"quote": "Witnessed event."}],
            },
            "blackout.diagnosis": {
                "status": "requires_confirmation",
                "value": "seizure",
                "evidence": [],
            },
        },
    }
    units = {
        "actual-rank": {
            "module": "blackout",
            "section": "1.2",
            "pdf_page": 68,
            "printed_page": 57,
            "evidence_text": "Whole original source with qualifications.",
        }
    }
    hybrid = {("case", "blackout"): {"status": "completed", "source_ids": ["actual-rank"]}}
    payload, budget = judgment_payload(
        case, ["blackout"], "Entire complex note.", hybrid, units, 9000
    )
    assert payload["nurse_note"] == "Entire complex note."
    assert list(payload["verified_patient_facts"]) == ["blackout.occurred"]
    assert payload["guideline_evidence"][0]["source_id"] == "actual-rank"
    assert "expected_outcome" not in payload
    assert not budget["skipped_by_budget"]
    hybrid[("case", "blackout")]["status"] = "failed"
    with pytest.raises(ValueError, match="retrieval attempt failed"):
        judgment_payload(case, ["blackout"], "Note", hybrid, units, 9000)


def test_resume_journal_rejects_modified_observation(tmp_path):
    path = tmp_path / "observations.jsonl"
    append(path, {"experiment_identity": "pin", "case_id": "a", "status": "failed"})
    assert records(path, "pin")[0]["status"] == "failed"
    value = json.loads(path.read_bytes())
    value["status"] = "completed"
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="digest"):
        records(path, "pin")


def test_portable_view_rebases_guideline_and_backlink_without_changing_other_links(tmp_path):
    root = tmp_path / "delivery"
    path = root / "runs" / "case" / "run" / "draft_report.portable.html"
    source = "<a href='../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=222'>PDF</a><a href='../../../../../index.html'>Back</a><a href='structured_case.json'>Facts</a>"
    rendered = portable_html(source, path, root)
    assert "href='../../../evidence_guide.pdf#page=222'" in rendered
    assert "href='../../../index.html'" in rendered
    assert "href='structured_case.json'" in rendered
    assert "../../../../../../data" in source  # Original view remains untouched.


def test_authored_fact_diagnostic_has_explicit_nonautomatic_provenance():
    from pathlib import Path

    from occupational_fitness_rag.rules.engine import RuleBook
    from tools.audit_complex_long_study import authored_case

    root = Path(__file__).resolve().parents[1]
    labels = json.loads((root / "data/cases/gold/complex_long_200.json").read_bytes())["cases"]
    label = next(r for r in labels if r["family"] == "confirmed_event_investigation_pending")
    manifest = json.loads(
        (root / "data/cases/complex_nurse_notes/long_200_manifest.json").read_bytes()
    )
    item = next(r for r in manifest["cases"] if r["case_id"] == label["case_id"])
    case = authored_case(item, label, RuleBook(root / "configs/rules/austroads_commercial_v1.yaml"))
    assert case.extraction_method == "authored_reference_facts_not_automatic_intake"
    assert case.facts["blackout.occurred"].value is True
    assert case.facts["blackout.occurred"].method == "authored_reference_fact_diagnostic"
