"""Diagnostic recovery and intervention comparisons use no live model or patient data."""

import json
from copy import deepcopy

import pytest

from occupational_fitness_rag.evaluation import judgment_diagnostics as diagnostics
from occupational_fitness_rag.evaluation.evidence_judgment import (
    CriterionCheck,
    EvidenceJudgment,
    quote_locations,
    validate_protocol_answer,
)
from occupational_fitness_rag.provenance import digest

QUOTE = "An active synthetic safety condition requires a hold until review is complete."
MODEL = "synthetic-local-model"


@pytest.fixture
def payload():
    return {
        "licence_context": "commercial",
        "modules": ["vision"],
        "nurse_note": "Synthetic operator record; a safety condition is recorded.",
        "verified_patient_facts": {
            "vision.safety_condition": {
                "value": True,
                "patient_quotes": ["a safety condition is recorded"],
            }
        },
        "guideline_evidence": [
            {
                "source_id": "fixture-source-1",
                "section": "fixture-section",
                "pdf_page": 1,
                "printed_page": 1,
                "source_text": QUOTE,
            }
        ],
    }


@pytest.fixture
def config():
    return {
        "endpoint": "http://127.0.0.1:11434",
        "context_length": 8192,
        "output_tokens": 1536,
        "prompt_max_bytes": 24000,
        "max_validation_repairs": 1,
        "timeout_seconds": 5,
    }


def answer(**updates):
    return {
        "assessment_outcome": "temporarily_unfit",
        "explanation": "The supplied synthetic condition satisfies the quoted hold requirement.",
        "source_ids": ["fixture-source-1"],
        "fact_fields": ["vision.safety_condition"],
        "criterion_checks": [
            {
                "module": "vision",
                "source_id": "fixture-source-1",
                "guideline_quote": QUOTE,
                "fact_fields": ["vision.safety_condition"],
                "licence_pathway": "temporary_no_driving",
                "finding": "established_restriction",
                "conclusion": "The verified condition establishes the synthetic restriction.",
            }
        ],
        **updates,
    }


def wire_answer(**updates):
    return {
        key: value
        for key, value in answer(**updates).items()
        if key not in {"source_ids", "fact_fields"}
    }


def invalid_wire_answer():
    proposed = wire_answer()
    proposed["criterion_checks"][0]["guideline_quote"] = QUOTE.replace("requires", "forbids")
    return proposed


def raw_response(content=None, **updates):
    return {
        "done": True,
        "done_reason": "stop",
        "prompt_eval_count": 100,
        "eval_count": 50,
        "message": {"content": json.dumps(content if content is not None else wire_answer())},
        **updates,
    }


def queued_post(*responses):
    requests = []

    def post(endpoint, route, body, timeout):
        requests.append(deepcopy(body))
        assert endpoint == "http://127.0.0.1:11434"
        assert route == "/api/chat" and timeout == 5
        item = responses[len(requests) - 1]
        if isinstance(item, Exception):
            raise item
        return deepcopy(item)

    return post, requests


def scored_row(result, *, protocol="evidence_contract", **updates):
    reference = "temporarily_unfit"
    return {
        "case_id": "synthetic-case-1",
        "model": MODEL,
        "model_digest": "same-pinned-digest",
        "evidence_policy": "hybrid_fixed",
        "protocol": protocol,
        "repeat": 0,
        **result,
        "reference_outcome": reference,
        "reference_agreement": result["status"] == "completed"
        and result.get("answer", {}).get("assessment_outcome") == reference,
        **updates,
    }


def completed_row(payload, *, protocol="evidence_contract", correct=True, **updates):
    proposed = answer(
        assessment_outcome="temporarily_unfit" if correct else "insufficient_information"
    )
    return scored_row(
        {
            "status": "completed",
            "answer": proposed,
            "attempts": [{"status": "completed", "answer": proposed}],
            "input_snapshot": deepcopy(payload),
            "seconds": 1.0,
            "recovered_after_validation_failure": False,
        },
        protocol=protocol,
        **updates,
    )


def test_one_validation_repair_retains_failed_raw_request_and_separate_metrics(config, payload):
    invalid = raw_response(invalid_wire_answer())
    valid = raw_response()
    post, requests = queued_post(invalid, valid)
    snapshot = deepcopy(payload)
    result = diagnostics.run_condition(config, MODEL, payload, "evidence_contract", post=post)
    assert result["status"] == "completed"
    assert result["recovered_after_validation_failure"] is True
    assert [a["status"] for a in result["attempts"]] == ["failed", "completed"]
    assert result["attempts"][0]["raw_response"] == invalid
    assert result["attempts"][1]["raw_response"] == valid
    assert [a["request_sha256"] for a in result["attempts"]] == [digest(r) for r in requests]
    assert result["attempts"][0]["request_sha256"] != result["attempts"][1]["request_sha256"]
    assert requests[1]["messages"][:2] == requests[0]["messages"]
    assert requests[1]["messages"][2]["content"] == invalid["message"]["content"]
    assert "same original patient facts" in requests[1]["messages"][3]["content"].lower()
    assert payload == snapshot == result["input_snapshot"]
    assert result["support_review"] == "pending_independent_review"
    metric = diagnostics.summarize_diagnostics([scored_row(result)], 1)["metrics"][0]
    assert metric["first_attempt_valid"] == 0
    assert metric["first_attempt_agreement"] == 0
    assert metric["final_valid"] == 1 and metric["final_agreement"] == 1
    assert metric["recoveries"] == 1 and metric["model_calls"] == 2


def test_invalid_outputs_are_bounded_to_two_recorded_calls(config, payload):
    invalid = raw_response(invalid_wire_answer())
    post, requests = queued_post(invalid, invalid)
    result = diagnostics.run_condition(config, MODEL, payload, "evidence_contract", post=post)
    assert len(requests) == len(result["attempts"]) == 2
    assert result["status"] == "failed"
    assert result["recovered_after_validation_failure"] is False
    assert all(a["raw_response"] == invalid for a in result["attempts"])
    assert all(a["status"] == "failed" for a in result["attempts"])


@pytest.mark.parametrize("failure", [TimeoutError("fixture timeout"), OSError("fixture transport")])
def test_transport_failure_is_recorded_without_retry(config, payload, failure):
    post, requests = queued_post(failure)
    result = diagnostics.run_condition(config, MODEL, payload, "evidence_contract", post=post)
    assert result["status"] == "failed"
    assert len(requests) == len(result["attempts"]) == 1
    assert "fixture" in result["error"]
    assert "raw_response" not in result["attempts"][0]
    assert result["attempts"][0]["request_sha256"] == digest(requests[0])


@pytest.mark.parametrize("completion", [{"done_reason": "length"}, {"done": False}])
def test_truncation_is_not_repaired_even_if_response_contains_valid_json(
    config, payload, completion
):
    raw = raw_response(**completion)
    post, requests = queued_post(raw)
    result = diagnostics.run_condition(config, MODEL, payload, "evidence_contract", post=post)
    assert result["status"] == "failed"
    assert len(requests) == len(result["attempts"]) == 1
    assert result["attempts"][0]["raw_response"] == raw
    assert "partial answers rejected" in result["error"]


def test_context_exhaustion_is_recorded_without_retry(config, payload):
    raw = raw_response(prompt_eval_count=config["context_length"] - config["output_tokens"])
    post, requests = queued_post(raw)
    result = diagnostics.run_condition(config, MODEL, payload, "evidence_contract", post=post)
    assert len(requests) == len(result["attempts"]) == 1
    assert result["status"] == "failed" and "context reserve" in result["error"]
    assert result["attempts"][0]["raw_response"] == raw


def test_byte_limit_rejection_preserves_condition_without_making_model_call(config, payload):
    config["prompt_max_bytes"] = 1
    post, requests = queued_post()
    result = diagnostics.run_condition(config, MODEL, payload, "evidence_contract", post=post)
    assert result["status"] == "failed" and result["attempts"] == []
    assert "byte limit" in result["error"]
    assert requests == []
    metric = diagnostics.summarize_diagnostics([scored_row(result)], 1)["metrics"][0]
    assert metric["conditions"] == 1 and metric["model_calls"] == 0
    assert metric["first_attempt_valid"] == metric["final_valid"] == 0


def test_request_build_failure_is_a_recorded_condition_not_an_unhandled_exception(config, payload):
    payload["guideline_evidence"] = []
    post, requests = queued_post()
    result = diagnostics.run_condition(config, MODEL, payload, "evidence_contract", post=post)
    assert result["status"] == "failed" and result["attempts"] == []
    assert "original guideline evidence" in result["error"]
    assert result["input_snapshot"] == payload and requests == []
    summary = diagnostics.summarize_diagnostics([scored_row(result)], 1)
    assert summary["recorded_conditions"] == 1
    assert summary["metrics"][0]["model_calls"] == 0


def test_response_parse_failure_keeps_original_raw_and_does_not_rewrite_answer(config, payload):
    config["max_validation_repairs"] = 0
    raw = raw_response(message={"content": "not JSON"})
    post, requests = queued_post(raw)
    result = diagnostics.run_condition(config, MODEL, payload, "evidence_contract", post=post)
    assert result["status"] == "failed" and len(requests) == 1
    assert result["attempts"][0]["raw_response"] == raw
    assert "answer" not in result
    assert result["attempts"][0]["request_sha256"] == digest(requests[0])


def test_provenance_failure_cannot_commit_or_score_an_accepted_judgment(config, payload):
    payload["guideline_evidence"][0].pop("pdf_page")
    raw = raw_response()
    post, requests = queued_post(raw)
    result = diagnostics.run_condition(config, MODEL, payload, "evidence_contract", post=post)
    assert result["status"] == "failed"
    assert len(requests) == len(result["attempts"]) == 1
    assert result["recovered_after_validation_failure"] is False
    assert "pdf_page" in result["error"]
    assert "answer" not in result and "criterion_locations" not in result
    attempt = result["attempts"][0]
    assert attempt["status"] == "failed" and attempt["failure_stage"] == "provenance"
    assert attempt["raw_response"] == raw
    assert attempt["request_sha256"] == digest(requests[0])
    metric = diagnostics.summarize_diagnostics([scored_row(result)], 1)["metrics"][0]
    assert metric["first_attempt_valid"] == metric["final_valid"] == 0
    assert metric["first_attempt_agreement"] == metric["final_agreement"] == 0


@pytest.mark.parametrize(
    "malformed",
    [[], "invalid provider response", {}, {"message": None}, {"message": {"content": None}}],
)
def test_malformed_provider_response_is_retained_without_repair_setup_crashing(
    config, payload, malformed
):
    post, requests = queued_post(malformed)
    result = diagnostics.run_condition(config, MODEL, payload, "evidence_contract", post=post)
    assert result["status"] == "failed" and len(requests) == 1
    assert len(result["attempts"]) == 1
    assert result["attempts"][0]["status"] == "failed"
    assert result["attempts"][0]["failure_stage"] == "response_validation"
    assert result["attempts"][0]["raw_response"] == malformed
    assert "error" in result and "answer" not in result


def test_reference_labels_are_attached_after_inference_and_not_inserted_during_repair(
    config, payload
):
    post, requests = queued_post(raw_response(invalid_wire_answer()), raw_response())
    result = diagnostics.run_condition(config, MODEL, payload, "evidence_contract", post=post)
    row = scored_row(result, reference_outcome="gold-label-sentinel")
    assert row["reference_outcome"] == "gold-label-sentinel"
    for request in requests:
        serialized = json.dumps(request)
        assert "gold-label-sentinel" not in serialized
        assert "reference_outcome" not in serialized
        assert "expected_source_ids" not in serialized
        assert "rule_result" not in serialized
        assert json.loads(request["messages"][1]["content"]) == payload


def test_intervention_pairs_require_identical_original_evidence_and_patient_input(payload):
    baseline = completed_row(payload, protocol="baseline", correct=False)
    intervention = completed_row(payload)
    pair = diagnostics.summarize_diagnostics([baseline, intervention], 2)["paired_changes"][0]
    assert pair["identical_inputs"] is True and pair["both_valid"] is True
    assert pair["transition"] == "wrong_to_correct"
    for field in ("nurse_note", "guideline_evidence"):
        changed = deepcopy(intervention)
        if field == "nurse_note":
            changed["input_snapshot"][field] += " Additional fixture statement."
        else:
            changed["input_snapshot"][field][0]["source_text"] += " Additional qualification."
        pair = diagnostics.summarize_diagnostics([baseline, changed], 2)["paired_changes"][0]
        assert pair["identical_inputs"] is False
        assert pair["transition"] == "not_comparable"


def test_changed_model_digest_is_not_scored_as_a_same_model_intervention(payload):
    baseline = completed_row(payload, protocol="baseline", correct=False)
    intervention = completed_row(payload, model_digest="different-current-digest")
    pair = diagnostics.summarize_diagnostics([baseline, intervention], 2)["paired_changes"][0]
    assert pair["transition"] == "not_comparable"


def test_duplicate_condition_keys_are_rejected_instead_of_silently_overwritten(payload):
    row = completed_row(payload)
    with pytest.raises(ValueError, match="[Dd]uplicate"):
        diagnostics.summarize_diagnostics([row, deepcopy(row)], 2)


def test_failed_first_attempt_remains_in_denominators_after_recovery(config, payload):
    post, _ = queued_post(raw_response(invalid_wire_answer()), raw_response())
    recovery = diagnostics.run_condition(config, MODEL, payload, "evidence_contract", post=post)
    failure = {
        "status": "failed",
        "attempts": [{"status": "failed", "error": "fixture invalid output"}],
        "error": "fixture invalid output",
        "input_snapshot": deepcopy(payload),
        "seconds": 1.0,
        "recovered_after_validation_failure": False,
    }
    rows = [scored_row(recovery), scored_row(failure, case_id="synthetic-case-2")]
    summary = diagnostics.summarize_diagnostics(rows, 2)
    metric = summary["metrics"][0]
    assert metric["conditions"] == 2
    assert metric["first_attempt_valid"] == 0 and metric["first_attempt_agreement"] == 0
    assert metric["final_valid"] == 1 and metric["final_agreement"] == 0.5
    assert metric["recoveries"] == 1 and metric["model_calls"] == 3
    assert summary["failure_reasons"] == {"fixture invalid output": 1}
    assert summary["clinical_accuracy"] is None


def test_duplicate_wire_references_are_canonicalized_without_erasing_original_response(
    config, payload
):
    proposed = wire_answer()
    proposed["criterion_checks"][0]["fact_fields"] *= 2
    proposed["criterion_checks"] *= 2
    raw = raw_response(proposed)
    post, requests = queued_post(raw)
    result = diagnostics.run_condition(config, MODEL, payload, "evidence_contract", post=post)
    assert result["status"] == "completed" and len(requests) == 1
    assert result["answer"]["source_ids"] == ["fixture-source-1"]
    assert result["answer"]["fact_fields"] == ["vision.safety_condition"]
    assert len(result["answer"]["criterion_checks"]) == 2
    assert result["attempts"][0]["raw_response"] == raw
    assert json.loads(result["attempts"][0]["raw_response"]["message"]["content"]) == proposed


def test_whitespace_only_clause_never_counts_as_original_grounding(payload):
    assert quote_locations("   \n\t ", QUOTE) == []
    proposed = answer()
    proposed["criterion_checks"][0] = CriterionCheck(
        **{**proposed["criterion_checks"][0], "guideline_quote": " " * 12}
    ).model_dump()
    with pytest.raises(ValueError):
        validate_protocol_answer(
            EvidenceJudgment.model_validate(proposed), payload, "evidence_contract"
        )


def test_resume_rejects_incomplete_jsonl_tail_before_network_or_any_write(tmp_path, monkeypatch):
    baseline = tmp_path / "baseline"
    output = tmp_path / "diagnostic"
    output.mkdir()
    manifest = output / "manifest.json"
    manifest.write_bytes(b'{"preserve":"existing manifest"}')
    results = output / "results.jsonl"
    original = b'{"previous":"complete"}\n{"interrupted":'
    results.write_bytes(original)
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "baseline_dir": str(baseline),
                "output": str(output),
                "endpoint": "http://127.0.0.1:11434",
                "protocols": ["baseline", "evidence_contract"],
                "evidence_policies": ["hybrid_fixed"],
                "repeats": 1,
            }
        ),
        encoding="utf-8",
    )
    before = {p.name: p.read_bytes() for p in output.iterdir()}

    def no_network(*args, **kwargs):
        raise AssertionError("Incomplete records must be rejected before opening the network")

    monkeypatch.setattr(diagnostics, "build_opener", no_network)
    with pytest.raises(ValueError, match="incomplete trailing record"):
        diagnostics.run_diagnostics(config_path, resume=True)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before
    assert results.read_bytes() == original
