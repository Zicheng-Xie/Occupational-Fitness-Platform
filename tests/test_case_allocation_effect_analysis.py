from copy import deepcopy

import pytest

from occupational_fitness_rag.provenance import digest
from tools.analyze_case_allocation_effects import (
    _render,
    agreement_component,
    audit_observations,
    method_metrics,
    pair_metrics,
    patient_metrics,
    support_review_flags,
)


def observation(method, repeat=0, outcome="temporarily_unfit", status="completed", request="same"):
    return {
        "case_id": "C",
        "model": "model",
        "method": method,
        "repeat": repeat,
        "request_identity": request,
        "status": status,
        **(
            {"answer": {"assessment_outcome": outcome}}
            if status == "completed"
            else {"error": "Evidence-grounded judgment requires a supplied source citation"}
        ),
    }


def conditions(arms=("hybrid",)):
    return [
        {"case_id": "C", "model": "model", "method": arm, "repeat": repeat}
        for arm in arms
        for repeat in range(3)
    ]


def test_failure_is_in_agreement_denominator_not_accepted_abstention():
    labels = {"C": {"reference_outcome": "temporarily_unfit"}}
    rows = [
        observation("hybrid", 0),
        observation("hybrid", 1, status="failed"),
        observation("hybrid", 2, outcome="insufficient_information"),
    ]
    metric = method_metrics(rows, labels, conditions())[0]
    assert metric["agreement_all_recorded"] == 1 / 3
    assert metric["accepted_insufficient"] == 1
    assert metric["insufficient_against_other_engineering_label"] == 1
    assert metric["failures_by_category"] == {"missing_source_citation": 1}
    assert metric["confusion_including_failure_column"]["temporarily_unfit"]["__failure__"] == 1


def test_three_repeat_patient_denominator_and_failure_vote_are_explicit():
    labels = {"C": {"reference_outcome": "temporarily_unfit"}}
    rows = [
        observation("hybrid", 0),
        observation("hybrid", 1, status="failed"),
        observation("hybrid", 2, status="failed"),
    ]
    patients = patient_metrics(rows, labels, conditions())
    assert len(patients) == 1
    assert patients[0]["mean_repeat_agreement"] == 1 / 3
    assert patients[0]["majority_outcome_including_failure_votes"] == "__failure__"
    assert patients[0]["failed_repeats"] == 2


def test_incomplete_repeats_never_receive_a_patient_success_estimate():
    labels = {"C": {"reference_outcome": "temporarily_unfit"}}
    patient = patient_metrics([observation("hybrid")], labels, conditions())[0]
    assert patient["mean_repeat_agreement"] is None
    assert patient["majority_matches_reference"] is None
    assert not patient["complete_repeat_inventory"]


def test_all_unique_votes_have_no_strict_majority():
    labels = {"C": {"reference_outcome": "temporarily_unfit"}}
    rows = [
        observation("hybrid", 0),
        observation("hybrid", 1, outcome="insufficient_information"),
        observation("hybrid", 2, outcome="does_not_meet_standard"),
    ]
    assert patient_metrics(rows, labels, conditions())[0]["no_strict_majority"]


def test_contract_recovery_is_separate_from_changed_valid_classification():
    old = observation("old", status="failed")
    new = observation("new")
    assert agreement_component(old, new, "temporarily_unfit") == "invalid_to_valid_correct"
    assert agreement_component(new, old, "temporarily_unfit") == "valid_correct_to_invalid"
    assert (
        agreement_component(
            observation("old", outcome="insufficient_information"), new, "temporarily_unfit"
        )
        == "valid_wrong_to_valid_correct"
    )
    assert agreement_component(old, old, "temporarily_unfit") == "both_invalid"


def test_identical_request_contract_variation_cannot_be_evidence_change():
    from tools.analyze_case_allocation_effects import ARMS

    labels = {"C": {"reference_outcome": "temporarily_unfit"}}
    payloads = {("C", arm): {"guideline_evidence": []} for arm in ARMS}
    rows = [
        observation("seventh_round_robin"),
        observation("seventh_case_coverage", status="failed"),
    ]
    repeats, _ = pair_metrics(rows, labels, conditions(ARMS), payloads)
    pair = next(p for p in repeats if p["pair"] == "allocation_seventh" and p["repeat"] == 0)
    assert pair["identical_request_contract_variation"]
    assert not pair["evidence_changed"]
    assert pair["agreement_component"] == "valid_correct_to_invalid"


def test_literal_restriction_flags_preserve_independent_review_status():
    payload = {
        "modules": ["blackout", "diabetes"],
        "verified_patient_facts": {
            "blackout.occurred": {"value": True},
            "blackout.mechanism_status": {"value": "under_investigation"},
        },
        "guideline_evidence": [
            {
                "source_id": "S",
                "pdf_page": 68,
                "section": "1.2.1",
                "source_text": "People should be advised not to drive until the mechanism is ascertained and the corresponding standard met.",
            }
        ],
    }
    row = observation("hybrid", outcome="insufficient_information")
    row["answer"].update(explanation="Some modules have missing facts.", source_ids=[])
    review = support_review_flags(row, payload)
    assert review["entailment_score"] is None
    assert review["requested_modules_without_verified_values"] == ["diabetes"]
    assert (
        "unmeasured_modules_may_mask_supplied_restrictive_clause" in review["literal_review_cues"]
    )
    assert review["literal_restriction_anchors"][0]["pdf_page"] == 68
    assert review["status"] == "pending_independent_clinical_and_entailment_review"


def test_uncertain_or_negated_blackout_is_not_promoted_by_literal_source():
    payload = {
        "modules": ["blackout"],
        "verified_patient_facts": {"blackout.occurred": {"value": False}},
        "guideline_evidence": [],
    }
    row = observation("hybrid", outcome="insufficient_information")
    row["answer"].update(explanation="No event established.", source_ids=[])
    assert support_review_flags(row, payload)["literal_review_cues"] == []


def audit_fixture():
    payload = {}
    body = {"model": "model", "messages": [{"content": "fixed"}, {"content": "{}"}]}
    request = digest(body)
    cond = {**conditions()[0], "request_identity": request, "payload_identity": "p"}
    data = {
        "preparation_identity": "prep",
        "requests_sha256": digest({request: body}),
        "conditions": [cond],
    }
    plan = {**data, "identity": digest(data), "production_change": False}
    row = {
        **cond,
        "experiment_identity": plan["identity"],
        "status": "failed",
        "error": "transport",
    }
    return payload, body, request, cond, plan, row


def test_actual_request_and_condition_audit_rejects_duplicate_rows():
    payload, body, request, cond, plan, row = audit_fixture()
    with pytest.raises(ValueError, match="Duplicated"):
        audit_observations(
            {},
            {"identity": "prep"},
            [{"case_id": "C", "method": "hybrid", "status": "ready", "payload": payload}],
            {request: body},
            [cond],
            plan,
            [row, deepcopy(row)],
        )


def test_actual_wire_payload_cannot_differ_from_fixed_patient():
    payload, body, request, cond, plan, row = audit_fixture()
    payload["unplanned_field"] = "different patient"
    with pytest.raises(ValueError, match="payload differs"):
        audit_observations(
            {},
            {"identity": "prep"},
            [{"case_id": "C", "method": "hybrid", "status": "ready", "payload": payload}],
            {request: body},
            [cond],
            plan,
            [row],
        )


def test_request_inventory_hash_tampering_is_rejected_before_scoring():
    payload, body, request, cond, plan, row = audit_fixture()
    body["model"] = "another-model"
    with pytest.raises(ValueError, match="request inventory"):
        audit_observations(
            {},
            {"identity": "prep"},
            [{"case_id": "C", "method": "hybrid", "status": "ready", "payload": payload}],
            {request: body},
            [cond],
            plan,
            [row],
        )


def test_focus_html_preserves_pending_status_and_escapes_source_text(tmp_path):
    summary = {
        "methods": [
            {
                "model": "model",
                "method": "hybrid",
                "recorded_calls": 0,
                "planned_calls": 3,
                "agreement_all_recorded": None,
                "failed": 0,
            }
        ],
        "phase": "partial_observation_snapshot",
        "recorded_actual_calls": 0,
        "planned_actual_calls": 990,
        "patient_count": 33,
        "interpretation": "Partial, not clinical accuracy.",
        "paired_effects": [],
    }
    focus = [
        {
            "case_id": "VAL-MIX-02",
            "engineering_reference": {"reference_outcome": "temporarily_unfit"},
            "fixed_patient": {"nurse_note": "</pre><script>unsafe()</script>"},
            "blackout_packet_coverage": [],
            "actual_evidence_by_arm": {
                "hybrid": [
                    {
                        "source_id": "S",
                        "section": "1.2.1",
                        "pdf_page": 68,
                        "source_text": "<original>",
                    }
                ]
            },
            "actual_observations": [],
        }
    ]
    _render(tmp_path, summary, focus)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "partial_observation_snapshot" in html and "Pending" in html
    assert "<script>unsafe()" not in html and "&lt;original&gt;" in html
    assert "evidence_guide.pdf#page=68" in html
