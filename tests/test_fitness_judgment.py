import json
from copy import deepcopy
from hashlib import sha256

import pytest

from occupational_fitness_rag.evaluation.fitness_judgment import (
    build_request,
    parse_completion,
)
from occupational_fitness_rag.evaluation.judgment_comparison import judgment_request
from tools.compare_fitness_judgments import summarize, verify_checkpoint


@pytest.fixture
def payload():
    return {
        "licence_context": "commercial",
        "modules": ["blackout"],
        "nurse_note": "Synthetic note.",
        "verified_patient_facts": {
            "blackout.occurred": {"value": True, "patient_quotes": ["Witnessed loss of awareness."]}
        },
        "guideline_evidence": [
            {
                "source_id": "SOURCE-A",
                "module": "blackout",
                "source_text": "Original temporary restriction with all qualifications.",
                "section": "1.2",
                "pdf_page": 68,
            }
        ],
    }


CFG = {"context_length": 8192, "output_tokens": 2048}


def raw(value, **extra):
    return {
        "message": {"content": json.dumps(value)},
        "done": True,
        "done_reason": "stop",
        "prompt_eval_count": 200,
        **extra,
    }


def proposal(**extra):
    return {
        "criterion_checks": [
            {
                "source_slot": 1,
                "fact_fields": ["blackout.occurred"],
                "applicability": "established",
                "effect": "temporary_exclusion",
                "evidence_note": "Verified event supports the applicable restriction.",
            }
        ],
        "assessment_outcome": "insufficient_information",
        "explanation": "An internally inconsistent model proposal.",
        **extra,
    }


def test_identical_original_and_patient_evidence_across_protocols(payload):
    original = judgment_request(CFG, "llama3:8b", payload)
    assert build_request(CFG, "llama3:8b", payload, "original") == original
    for protocol in ("outcome_semantics_v1", "criterion_ledger_v1"):
        changed = build_request(CFG, "llama3:8b", payload, protocol)
        assert changed["messages"][1] == original["messages"][1]
        assert changed["options"] == original["options"]
        assert "SOURCE-A" not in changed["messages"][0]["content"]
    assert build_request(CFG, "qwen3.5:4b-q4_K_M", payload, "criterion_ledger_v1")["think"] is False


def test_binding_does_not_correct_an_inconsistent_classification(payload):
    parsed = parse_completion(raw(proposal()), payload, "criterion_ledger_v1", CFG)
    assert parsed["answer"]["source_ids"] == ["SOURCE-A"]
    assert parsed["answer"]["assessment_outcome"] == "insufficient_information"
    assert parsed["consistency_flags"] == [
        "established_temporary_restriction_not_reflected_in_outcome"
    ]
    assert parsed["clinical_explanation_support"] == "pending_independent_review"


@pytest.mark.parametrize(
    "change", ["foreign_source", "foreign_fact", "empty_verified_support", "incomplete", "context"]
)
def test_rejects_unverifiable_records_and_incomplete_completions(payload, change):
    value = proposal()
    extra = {}
    if change == "foreign_source":
        value["criterion_checks"][0]["source_slot"] = 2
    elif change == "foreign_fact":
        value["criterion_checks"][0]["fact_fields"] = ["family_history"]
    elif change == "empty_verified_support":
        value["criterion_checks"][0]["fact_fields"] = []
    elif change == "incomplete":
        extra["done_reason"] = "length"
    else:
        extra["prompt_eval_count"] = 7000
    with pytest.raises(ValueError):
        parse_completion(raw(value, **extra), payload, "criterion_ledger_v1", CFG)


def test_unknown_patient_facts_remain_unknown(payload):
    payload["verified_patient_facts"] = {}
    body = build_request(CFG, "llama3:8b", payload, "criterion_ledger_v1")
    assert body["format"]["$defs"]["CriterionRecord"]["properties"]["fact_fields"]["maxItems"] == 0
    value = proposal()
    value["criterion_checks"][0].update(fact_fields=[], applicability="unresolved")
    parsed = parse_completion(raw(value), payload, "criterion_ledger_v1", CFG)
    assert parsed["answer"]["fact_fields"] == []


def test_contract_recovery_is_not_counted_as_valid_classification_gain():
    labels = {"case": {"reference_outcome": "temporarily_unfit"}}
    base = {
        "case_id": "case",
        "method": "seventh_case_coverage",
        "model": "judge",
        "repeat": 0,
        "protocol": "original",
        "status": "failed",
        "seconds": 1,
    }
    candidate = {
        **base,
        "protocol": "criterion_ledger_v1",
        "status": "completed",
        "answer": {"assessment_outcome": "temporarily_unfit"},
    }
    plan = {
        "identity": "test",
        "conditions": [base, candidate],
        "config": {"case_ids": ["case"], "scope": "test", "repeats": 3},
    }
    summary, changes, cases = summarize([base, candidate], labels, plan)
    assert summary["paired_changes"] == {"contract_or_run_status_change": 1}
    assert changes[0]["change"] != "valid_wrong_to_correct"
    assert not cases[1]["majority_correct"]


def test_resume_accepts_new_append_but_rejects_changed_prefix(tmp_path):
    first = b'{"attempt":1}\n'
    (tmp_path / "results.jsonl").write_bytes(first)
    (tmp_path / "checkpoint_state.json").write_text(json.dumps({"results_bytes": len(first)}))
    pins = {
        "results.jsonl": sha256(first).hexdigest(),
        "checkpoint_state.json": sha256(
            (tmp_path / "checkpoint_state.json").read_bytes()
        ).hexdigest(),
    }
    (tmp_path / "artifacts.json").write_text(json.dumps(pins))
    (tmp_path / "results.jsonl").write_bytes(first + b'{"attempt":2}\n')
    verify_checkpoint(tmp_path)
    changed = deepcopy(first).replace(b"1", b"9")
    (tmp_path / "results.jsonl").write_bytes(changed)
    with pytest.raises(ValueError, match="checkpointed attempts"):
        verify_checkpoint(tmp_path)
