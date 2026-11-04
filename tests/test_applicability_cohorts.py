"""Cohort metrics keep failures, repeated calls and oracle controls distinct."""

import importlib.util
import json
from copy import deepcopy
from itertools import product
from pathlib import Path

import pytest


def tool():
    spec = importlib.util.spec_from_file_location(
        "applicability_cohorts",
        Path(__file__).resolve().parents[1] / "tools/analyze_applicability_cohorts.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def record(case_id, truth, result, *, repeat=0):
    row = {
        "case_id": case_id,
        "reference_outcome": truth,
        "status": "completed" if result else "failed",
        "repeat": repeat,
    }
    if result:
        row["answer"] = {"assessment_outcome": result}
    return row


def fixture():
    api = tool()
    positive, insufficient = api.CLASSES[1], api.CLASSES[4]
    labels = [
        {"case_id": "CASE-1", "cohort": "engineering", "expected_outcome": positive},
        {"case_id": "CASE-2", "cohort": "complex", "expected_outcome": insufficient},
    ]
    upstream = {
        "cases": [
            {"case_id": "CASE-1", "reference": positive, "frozen_outcome": insufficient},
            {"case_id": "CASE-2", "reference": insufficient, "frozen_outcome": insufficient},
        ]
    }
    rows = []
    for case_id, protocol, policy in product(
        ["CASE-1", "CASE-2"],
        ["passage_selection", "applicability_first"],
        ["module_query", "reference_evidence"],
    ):
        truth = positive if case_id == "CASE-1" else insufficient
        result = (
            positive
            if policy == "reference_evidence"
            else insufficient
            if case_id == "CASE-1"
            else None
        )
        row = record(case_id, truth, result)
        payload = {
            "licence_context": "commercial",
            "modules": ["hearing"],
            "nurse_note": "Synthetic case",
            "verified_patient_facts": {},
            "guideline_evidence": [{"source_id": policy}],
        }
        row.update(
            model="<img src=x onerror=alert(1)>",
            protocol=protocol,
            evidence_policy=policy,
            input_snapshot=payload,
            input_sha256=api.digest(payload),
            experiment_identity="fixture",
        )
        rows.append(row)
    return api, rows, labels, upstream


def test_failure_is_false_negative_and_absent_classes_have_explicit_denominator():
    api = tool()
    conditional, insufficient = api.CLASSES[1], api.CLASSES[4]
    result = api.classification_metrics(
        [
            record("A", conditional, conditional),
            record("A", conditional, None, repeat=1),
            record("B", insufficient, insufficient),
        ]
    )
    assert result["condition_count"] == 3 and result["distinct_case_count"] == 2
    assert result["failed_conditions"] == 1
    assert result["correct_conditions"] == 2
    assert result["reference_agreement_all_conditions"] == pytest.approx(2 / 3)
    assert result["reference_agreement_valid_only"] == 1
    assert result["always_insufficient_baseline_agreement"] == pytest.approx(1 / 3)
    assert result["macro_f1_fixed_five_classes"] == pytest.approx(1 / 3)
    assert result["macro_f1_present_reference_classes"] == pytest.approx(5 / 6)
    assert result["balanced_accuracy_present_reference_classes"] == 0.75
    assert result["confusion_matrix"][conditional]["execution_failure"] == 1
    assert result["per_class"][conditional]["recall"] == 0.5
    assert result["distinct_cases_correct_in_every_recorded_repeat"] == 1


def test_cohort_pairs_separate_accepted_improvement_and_failure_recovery():
    api, rows, labels, upstream = fixture()
    result = api.analyze(rows, labels, upstream)
    assert result["observed_case_count"] == 2
    assert result["recorded_conditions"] == 8
    assert result["cohort_membership"]["complex_validation_cases"] == ["CASE-2"]
    assert result["cohort_membership"]["without_upstream_outcome_discrepancies"] == ["CASE-2"]
    transitions = [row["transition"] for row in result["evidence_policy_pairs"]]
    assert transitions.count("accepted_wrong_to_correct") == 2
    assert transitions.count("failed_to_valid") == 2
    assert all(row["distinct_case_count"] <= 2 for row in result["metrics"])
    assert result["clinical_accuracy"] is None
    assert "overall case reference" in result["interpretation"]


def test_policy_comparison_rejects_changed_facts_and_references():
    api, rows, labels, upstream = fixture()
    invalid = deepcopy(rows)
    invalid[1]["input_snapshot"]["verified_patient_facts"] = {"hearing.average": {"value": 40}}
    invalid[1]["input_sha256"] = api.digest(invalid[1]["input_snapshot"])
    with pytest.raises(ValueError, match="different patient facts"):
        api.analyze(invalid, labels, upstream)
    invalid = deepcopy(rows)
    invalid[0]["reference_outcome"] = api.CLASSES[0]
    with pytest.raises(ValueError, match="pinned original"):
        api.analyze(invalid, labels, upstream)
    invalid = deepcopy(rows)
    invalid.pop()
    with pytest.raises(ValueError, match="both fixed policies"):
        api.analyze(invalid, labels, upstream)


def test_export_refuses_active_writer_and_preserves_raw_snapshot(tmp_path):
    api, rows, labels, upstream = fixture()
    directory = tmp_path / "experiment"
    directory.mkdir()
    (directory / ".run.lock").write_text("active", encoding="utf-8")
    with pytest.raises(ValueError, match="run lock"):
        api.export_report(directory, tmp_path / "labels.json", tmp_path / "upstream.json")
    (directory / ".run.lock").unlink()
    manifest = {
        "identity": "fixture",
        "planned_keys": [
            [row[field] for field in ["model", "case_id", "evidence_policy", "protocol", "repeat"]]
            for row in rows
        ],
    }
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    raw = ("\n".join(json.dumps(row) for row in rows) + "\n").encode("utf-8")
    (directory / "results.jsonl").write_bytes(raw)
    (tmp_path / "labels.json").write_text(json.dumps(labels), encoding="utf-8")
    (tmp_path / "upstream.json").write_text(json.dumps(upstream), encoding="utf-8")
    report = api.export_report(
        directory, tmp_path / "labels.json", tmp_path / "upstream.json", api.sha256(raw)
    )
    assert (directory / "results.jsonl").read_bytes() == raw
    assert report["provenance"]["results_sha256"] == api.sha256(raw)
    html = (directory / "cohort_report.html").read_text(encoding="utf-8")
    assert "<img src=x" not in html
    assert "&lt;img src=x" in html
    with pytest.raises(ValueError, match="expected value"):
        api.export_report(directory, tmp_path / "labels.json", tmp_path / "upstream.json", "0" * 64)
    (directory / "results.jsonl").write_bytes(raw[:-1])
    with pytest.raises(ValueError, match="newline"):
        api.export_report(directory, tmp_path / "labels.json", tmp_path / "upstream.json")
