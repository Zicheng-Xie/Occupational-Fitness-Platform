"""Completion auditing must never turn empty jobs into experiment evidence."""

import json

import pytest

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.provenance import digest, write_json
from tools import audit_completed_judgments as audit


def pin(path):
    write_json(
        path / "artifacts.json",
        {
            p.name: file_hash(p)
            for p in path.iterdir()
            if p.is_file() and p.name != "artifacts.json"
        },
    )


def completed(path):
    path.mkdir()
    payload = {"guideline_evidence": [{"source_id": "real"}], "verified_patient_facts": {}}
    body = {
        "model": "local",
        "messages": [
            {"role": "system", "content": "fixed"},
            {"role": "user", "content": json.dumps(payload)},
        ],
    }
    rid = digest(body)
    conditions = [
        {
            "case_id": "case",
            "method": "hybrid",
            "model": "local",
            "repeat": 0,
            "request_identity": rid,
        }
    ]
    requests = {rid: body}
    data = {"conditions": conditions, "requests_sha256": digest(requests)}
    plan = {**data, "identity": digest(data), "production_change": False}
    answer = {
        "assessment_outcome": "insufficient_information",
        "explanation": "Measurements remain unknown.",
        "source_ids": ["real"],
        "fact_fields": [],
    }
    row = {
        **conditions[0],
        "experiment_identity": plan["identity"],
        "status": "completed",
        "answer": answer,
        "raw_response": {
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 100,
            "message": {"content": json.dumps(answer)},
        },
    }
    labels = {"case": {"reference_outcome": "insufficient_information", "cohort": "engineering"}}
    summary = {
        "identity": plan["identity"],
        "complete": True,
        "recorded": 1,
        "planned": 1,
        "actual_judgment_calls": 1,
        "accepted": 1,
        "failed": 0,
        "metrics": audit.actor.scoring([row], labels),
    }
    for name, value in (
        ("plan.json", plan),
        ("requests.json", requests),
        ("summary.json", summary),
    ):
        write_json(path / name, value)
    (path / "results.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    pin(path)
    return labels, {"context_length": 8192, "output_tokens": 2048}, row


def test_raw_answers_are_revalidated_without_mutating_completed_artifacts(tmp_path):
    path = tmp_path / "run"
    labels, config, row = completed(path)
    before = (path / "results.jsonl").read_bytes()
    assert audit.verify_completed(path, labels, config)[1] == [row]
    assert (path / "results.jsonl").read_bytes() == before
    row["answer"]["explanation"] = "Different accepted text."
    (path / "results.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    pin(path)
    with pytest.raises(ValueError, match="retained raw"):
        audit.verify_completed(path, labels, config)


def test_zero_call_output_is_a_diagnostic_not_a_completed_comparison(tmp_path):
    write_json(tmp_path / "plan.json", {"conditions": [], "identity": "zero"})
    write_json(
        tmp_path / "summary.json", {"recorded": 0, "actual_judgment_calls": 0, "complete": True}
    )
    pin(tmp_path)
    record = audit.describe_zero_revision(tmp_path, 198)
    assert record["status"] == "invalid_zero_condition_dispatch"
    assert record["actual_judgment_calls"] == 0 and record["expected_conditions"] == 198


def test_saved_metric_rewrite_is_rejected_even_with_new_file_inventory(tmp_path):
    path = tmp_path / "run"
    labels, config, _ = completed(path)
    saved = json.loads((path / "summary.json").read_bytes())
    saved["metrics"][0]["correct"] = 0
    write_json(path / "summary.json", saved)
    pin(path)
    with pytest.raises(ValueError, match="engineering scoring"):
        audit.verify_completed(path, labels, config)
