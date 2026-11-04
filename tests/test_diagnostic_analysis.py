"""Diagnostic gains require matched inputs and must retain raw failures and review status."""

import csv
import json
from copy import deepcopy

import pytest

from occupational_fitness_rag.evaluation.diagnostic_analysis import (
    analyze_diagnostics,
    criterion_review_rows,
    evidence_difference,
    export_diagnostic_analysis,
    load_snapshot,
    write_review,
)
from occupational_fitness_rag.provenance import digest


def record(protocol="baseline", policy="hybrid_fixed", outcome="insufficient_information"):
    answer = {"assessment_outcome": outcome, "explanation": "An unreviewed proposed judgment."}
    payload = {
        "modules": ["blackout"],
        "licence_context": "commercial",
        "nurse_note": "A witnessed episode is under investigation.",
        "verified_patient_facts": {
            "blackout.occurred": {"value": True, "patient_quotes": ["A witnessed episode"]}
        },
        "guideline_evidence": [
            {
                "source_id": "source-1",
                "pdf_page": 68,
                "section": "1.2.1",
                "source_text": "Drivers should not drive until the mechanism is established.",
            }
        ],
    }
    if protocol == "evidence_contract":
        answer["criterion_checks"] = [
            {
                "module": "blackout",
                "source_id": "source-1",
                "guideline_quote": "Drivers should not drive until the mechanism is established.",
                "fact_fields": ["blackout.occurred"],
                "licence_pathway": "temporary_no_driving",
                "finding": "established_restriction",
                "conclusion": "A proposed restriction requires independent review.",
            }
        ]
    return {
        "case_id": "case-1",
        "model": "local",
        "model_digest": "pinned-digest",
        "evidence_policy": policy,
        "protocol": protocol,
        "repeat": 0,
        "status": "completed",
        "answer": answer,
        "attempts": [{"number": 1, "status": "completed", "answer": deepcopy(answer)}],
        "input_snapshot": payload,
        "input_sha256": digest(payload),
        "reference_outcome": "temporarily_unfit",
        "reference_agreement": False,
        "seconds": 1,
    }


def test_protocol_and_evidence_axes_keep_failures_and_identity_mismatches_separate():
    baseline = record()
    contract = record("evidence_contract", outcome="temporarily_unfit")
    selected = record("evidence_contract", "documented_modules", "does_not_meet_standard")
    selected["input_snapshot"]["guideline_evidence"][0]["source_id"] = "source-2"
    selected["input_sha256"] = digest(selected["input_snapshot"])
    analysis = analyze_diagnostics([baseline, contract, selected], {"planned_conditions": 4})
    pairs = [pair for pair in analysis["pairs"] if pair["stage"] == "final_with_repair"]
    assert [pair["transition"] for pair in pairs] == ["wrong_to_correct", "correct_to_wrong"]
    assert pairs[0]["axis"] == "protocol"
    assert pairs[0]["evidence_change"] == "identical_ordered_evidence"
    assert pairs[1]["axis"] == "evidence_policy"
    assert pairs[1]["added_source_ids"] == ["source-2"]
    assert pairs[1]["removed_source_ids"] == ["source-1"]
    assert len(analysis["missing_comparators"]) == 1
    assert analysis["execution_status"] == "completeness_not_verified"

    changed = deepcopy(selected)
    changed["model_digest"] = "different-revision"
    changed["input_snapshot"]["verified_patient_facts"] = {}
    changed["input_sha256"] = digest(changed["input_snapshot"])
    pair = analyze_diagnostics([contract, changed], {})["pairs"][0]
    assert pair["transition"] == "excluded_identity_mismatch"
    assert set(pair["exclusion_reasons"]) == {
        "patient_input_mismatch",
        "model_digest_missing_or_mismatched",
    }
    changed = deepcopy(contract)
    changed["input_sha256"] = "stale"
    pair = analyze_diagnostics([baseline, changed], {})["pairs"][0]
    assert "intervention_input_fingerprint_mismatch" in pair["exclusion_reasons"]
    with pytest.raises(ValueError, match="Duplicate"):
        analyze_diagnostics([baseline, baseline], {})


def test_recovery_is_a_final_gain_not_a_first_attempt_gain():
    baseline = record()
    repaired = record("evidence_contract", outcome="temporarily_unfit")
    repaired["attempts"].insert(0, {"number": 1, "status": "failed", "error": "Missing citation"})
    repaired["attempts"][1]["number"] = 2
    analysis = analyze_diagnostics([baseline, repaired], {"planned_conditions": 2})
    first, final = analysis["pairs"]
    assert first["transition"] == "failure_separate"
    assert first["intervention"]["status"] == "failed"
    assert final["transition"] == "wrong_to_correct"
    metrics = [
        metric for metric in analysis["metrics"] if metric["protocol"] == "evidence_contract"
    ]
    assert metrics[0]["stage"] == "first_attempt" and metrics[0]["correct"] == 0
    assert metrics[0]["failures"] == 1
    assert metrics[0]["recorded_model_attempts"] == 1
    assert metrics[1]["stage"] == "final_with_repair" and metrics[1]["correct"] == 1
    assert metrics[1]["recoveries"] == 1 and metrics[1]["recorded_model_attempts"] == 2


def test_quote_provenance_is_not_entailment_and_raw_rejected_checks_remain_reviewable():
    row = record("evidence_contract", outcome="meets_unconditional_standard")
    item = criterion_review_rows([row])[0]
    assert item["quote_provenance"] == "matched_original_quote"
    spans = json.loads(item["original_quote_spans_json"])
    assert (
        item["source_text"][spans[0]["char_start"] : spans[0]["char_end"]]
        == spans[0]["original_quote"]
    )
    assert item["support_status"] == item["clinical_review_status"] == "pending"
    assert item["reviewer"] == ""
    assert json.loads(item["verified_fact_fields_json"])["blackout.occurred"]["value"] is True
    assert item["final_outcome"] == "meets_unconditional_standard"
    proposed = deepcopy(row["answer"])
    proposed["criterion_checks"][0]["guideline_quote"] = "Words not present in the original source."
    row["status"] = "failed"
    row.pop("answer")
    row["attempts"] = [
        {
            "number": 1,
            "status": "failed",
            "raw_response": {"message": {"content": json.dumps(proposed)}},
        }
    ]
    item = criterion_review_rows([row])[0]
    assert item["quote_provenance"] == "absent_quote"
    assert item["final_outcome"] == "" and item["attempt_status"] == "failed"
    assert item["support_status"] == "pending"


def test_ambiguous_unprovided_and_malformed_rejected_criteria_do_not_gain_support():
    row = record("evidence_contract")
    source = row["input_snapshot"]["guideline_evidence"][0]
    source["source_text"] += " " + source["source_text"]
    assert criterion_review_rows([row])[0]["quote_provenance"] == "ambiguous_quote"
    check = row["attempts"][0]["answer"]["criterion_checks"][0]
    check["source_id"] = "absent-source"
    check["fact_fields"] = ["invented.patient.fact"]
    item = criterion_review_rows([row])[0]
    assert item["quote_provenance"] == "unprovided_source"
    assert json.loads(item["unverified_fact_fields_json"]) == ["invented.patient.fact"]
    assert item["applicability_status"] == "pending"
    check["source_id"] = ["invalid-type"]
    item = criterion_review_rows([row])[0]
    assert item["quote_provenance"] == "unprovided_source"
    assert "invalid-type" in item["proposed_criterion_json"]
    row["attempts"][0]["answer"]["criterion_checks"] = None
    assert criterion_review_rows([row]) == []


def test_evidence_order_and_changed_text_under_same_identifier_are_visible():
    old = record()["input_snapshot"]
    extra = deepcopy(old["guideline_evidence"][0])
    extra["source_id"] = "source-2"
    old["guideline_evidence"].append(extra)
    new = deepcopy(old)
    new["guideline_evidence"].reverse()
    assert evidence_difference(old, new)["evidence_change"] == "same_passages_different_order"
    new["guideline_evidence"][0]["source_text"] = "Changed original text must not appear identical."
    difference = evidence_difference(old, new)
    assert difference["evidence_change"] == "changed_evidence_bundle"
    assert difference["changed_source_ids"] == ["source-2"]
    assert difference["added_source_ids"] == difference["removed_source_ids"] == []


def test_review_refresh_preserves_human_entries_and_rejects_changed_material(tmp_path):
    path = tmp_path / "review.csv"
    items = criterion_review_rows([record("evidence_contract")])
    write_review(path, items)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        edited = list(csv.DictReader(stream))
    edited[0].update(
        reviewer="Clinician A",
        support_status="requires_revision",
        comments="Inspect the licence pathway.",
        manual_note="Retain this extra review column.",
    )
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(edited[0]))
        writer.writeheader()
        writer.writerows(edited)
    write_review(path, items)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        saved = list(csv.DictReader(stream))[0]
    assert saved["reviewer"] == "Clinician A"
    assert saved["support_status"] == "requires_revision"
    assert saved["manual_note"] == "Retain this extra review column."
    changed = record("evidence_contract")
    changed["input_snapshot"]["verified_patient_facts"]["blackout.occurred"]["value"] = False
    with pytest.raises(ValueError, match="material changed"):
        write_review(path, criterion_review_rows([changed]))


def test_export_fingerprints_one_completed_jsonl_snapshot_and_preserves_tail(tmp_path):
    rows = [record(), record("evidence_contract", outcome="temporarily_unfit")]
    path = tmp_path / "results.jsonl"
    complete = ("\n".join(json.dumps(row) for row in rows) + "\n").encode()
    path.write_bytes(complete + b'{"unfinished":')
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "planned_conditions": 4,
                "model_revision_changes": {
                    "local": {"historical": "old", "current": "pinned-digest"}
                },
            }
        ),
        encoding="utf-8",
    )
    result = export_diagnostic_analysis(tmp_path)
    analysis = json.loads((tmp_path / "diagnostic_analysis.json").read_text(encoding="utf-8"))
    assert result["recorded_conditions"] == 2
    assert result["execution_status"] == "completeness_not_verified"
    assert analysis["model_revision_changes"]["local"]["historical"] == "old"
    assert analysis["clinical_accuracy"] is None
    assert analysis["provenance"]["results_snapshot"]["completed_prefix_bytes"] == len(complete)
    assert analysis["provenance"]["results_snapshot"]["uncommitted_tail_bytes"] > 0
    assert "diagnostic_analysis.py" in analysis["provenance"]["observed_code_sha256"]
    assert path.read_bytes() == complete + b'{"unfinished":'
    path.write_bytes(b'{"broken":}\n')
    with pytest.raises(ValueError):
        load_snapshot(path)


def manifest():
    return {
        "planned_conditions": 2,
        "config": {
            "case_ids": ["case-1"],
            "models": ["local"],
            "evidence_policies": ["hybrid_fixed"],
            "protocols": ["baseline", "evidence_contract"],
            "repeats": 1,
        },
    }


def test_completion_requires_every_manifest_identity_rather_than_matching_row_count():
    baseline = record()
    contract = record("evidence_contract")
    complete = analyze_diagnostics([baseline, contract], manifest())
    assert complete["execution_status"] == "completed"
    assert complete["completeness_verified"] is True
    assert complete["expected_condition_count"] == 2
    assert complete["missing_condition_keys"] == []
    partial = analyze_diagnostics([baseline], manifest())
    assert partial["execution_status"] == "partial"
    assert partial["missing_condition_keys"] == [
        ["case-1", "local", "hybrid_fixed", "evidence_contract", 0]
    ]
    for change in ({"case_id": "unexpected-case"}, {"repeat": 999}):
        unexpected = {**contract, **change}
        with pytest.raises(ValueError, match="Unexpected diagnostic condition"):
            analyze_diagnostics([baseline, unexpected], manifest())


def test_compact_manifest_cannot_certify_completion_without_the_condition_axes():
    analysis = analyze_diagnostics([record()], {"planned_conditions": 1})
    assert analysis["execution_status"] == "completeness_not_verified"
    assert analysis["completeness_verified"] is False
    assert analysis["expected_condition_count"] is None
    assert analysis["missing_condition_keys"] is None


def test_manifest_planned_count_and_axes_cannot_silently_disagree():
    inconsistent = {**manifest(), "planned_conditions": 1}
    with pytest.raises(ValueError, match="planned count"):
        analyze_diagnostics([record()], inconsistent)
    duplicated = manifest()
    duplicated["config"]["case_ids"] = ["case-1", "case-1"]
    with pytest.raises(ValueError, match="unique non-empty"):
        analyze_diagnostics([record()], duplicated)
