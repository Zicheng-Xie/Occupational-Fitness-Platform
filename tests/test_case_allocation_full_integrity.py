import json

import pytest

from tools.audit_case_allocation_full import (
    independently_score,
    paired_decomposition,
    read_prefix,
    validate_raw,
)


def response(source_ids=None):
    return {
        "model": "llama3:8b",
        "status": "completed",
        "raw_response": {
            "model": "llama3:8b",
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 10,
            "message": {
                "content": json.dumps(
                    {
                        "assessment_outcome": "insufficient_information",
                        "explanation": "Unknown facts remain unresolved.",
                        "source_ids": ["s"] if source_ids is None else source_ids,
                        "fact_fields": [],
                    }
                )
            },
        },
    }


def test_empty_citations_are_a_failure_not_an_accepted_abstention():
    payload = {"guideline_evidence": [{"source_id": "s"}], "verified_patient_facts": {}}
    config = {"context_length": 100, "output_tokens": 20}
    answer, reason = validate_raw(response([]), payload, config)
    assert answer is None and reason == "empty_source_citations"
    answer, reason = validate_raw(response(), payload, config)
    assert reason is None and answer["assessment_outcome"] == "insufficient_information"


def test_context_overflow_and_wrong_provider_model_are_rejected():
    row = response()
    payload = {"guideline_evidence": [{"source_id": "s"}], "verified_patient_facts": {}}
    config = {"context_length": 100, "output_tokens": 20}
    row["raw_response"]["prompt_eval_count"] = 81
    assert validate_raw(row, payload, config)[1] == "context_reservation_failed"
    row["raw_response"]["model"] = "another"
    assert validate_raw(row, payload, config)[1] == "provider_model_differs"


def test_partial_tail_is_exposed_without_repairing_live_records(tmp_path):
    path = tmp_path / "calls.jsonl"
    raw = b'{"case":"a"}\n{"case":"unfinished'
    path.write_bytes(raw)
    rows, prefix, tail = read_prefix(path)
    assert rows == [{"case": "a"}]
    assert prefix == b'{"case":"a"}\n' and tail > 0
    assert path.read_bytes() == raw


def test_corrupted_complete_record_is_not_hidden_as_partial(tmp_path):
    path = tmp_path / "calls.jsonl"
    path.write_bytes(b"{bad}\n")
    with pytest.raises(ValueError):
        read_prefix(path)


def test_case_aggregation_does_not_count_repeats_as_independent_patients():
    labels = {"c": {"reference_outcome": "temporarily_unfit"}}
    rows = [
        {
            "case_id": "c",
            "method": "hybrid",
            "model": "m",
            "repeat": i,
            "status": "completed" if i < 2 else "failed",
            "answer": {"assessment_outcome": "temporarily_unfit"},
        }
        for i in range(3)
    ]
    metrics, patients = independently_score(rows, labels)
    assert len(patients) == 1
    assert patients[0]["majority_correct"] is True
    assert metrics[0]["engineering_reference_agreement_all_recorded"] == 2 / 3
    assert metrics[0]["failed"] == 1
    assert metrics[0]["insufficient_predictions"] == 0


def test_valid_improvement_and_contract_recovery_are_separate():
    labels = {c: {"reference_outcome": "temporarily_unfit"} for c in ("a", "b")}
    rows = []
    for case, failed in (("a", False), ("b", True)):
        for arm, outcome in (
            ("hybrid", "insufficient_information"),
            ("seventh_round_robin", "temporarily_unfit"),
        ):
            rows.append(
                {
                    "case_id": case,
                    "method": arm,
                    "model": "m",
                    "repeat": 0,
                    "request_identity": case + arm,
                    "status": "failed" if failed and arm == "hybrid" else "completed",
                    "answer": {"assessment_outcome": outcome},
                }
            )
    result = next(r for r in paired_decomposition(rows, labels) if r["pair"] == "retrieval_seventh")
    assert result["valid_prediction_net_correct"] == 1
    assert result["contract_net_correct"] == 1
    assert result["all_recorded_net_correct"] == 2


def test_identical_request_contract_variation_is_not_hidden():
    labels = {"c": {"reference_outcome": "temporarily_unfit"}}
    rows = [
        {
            "case_id": "c",
            "method": arm,
            "model": "m",
            "repeat": 0,
            "request_identity": "same",
            "status": status,
            "answer": {"assessment_outcome": "temporarily_unfit"},
        }
        for arm, status in (
            ("seventh_round_robin", "completed"),
            ("seventh_case_coverage", "failed"),
        )
    ]
    result = next(
        r for r in paired_decomposition(rows, labels) if r["pair"] == "allocation_seventh"
    )
    assert result["same_request_net_correct"] == -1
    assert result["changed_request_net_correct"] == 0
    assert result["identical_request_outcome_or_contract_variations"] == 1
