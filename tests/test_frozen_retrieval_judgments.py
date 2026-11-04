"""Check independent repeats, raw failure retention and paired scoring."""

import json

import pytest

from occupational_fitness_rag.provenance import digest, write_json
from tools import run_frozen_retrieval_judgments as runner


@pytest.mark.parametrize("problem", ["length", "context", "wrong_source"])
def test_completion_gate_rejects_incomplete_over_budget_or_fabricated_evidence(problem):
    payload = {"guideline_evidence": [{"source_id": "real"}], "verified_patient_facts": {}}
    raw = {
        "done": True,
        "done_reason": "stop",
        "prompt_eval_count": 100,
        "message": {
            "content": json.dumps(
                {
                    "assessment_outcome": "insufficient_information",
                    "explanation": "Missing verified measurements.",
                    "source_ids": ["real"],
                    "fact_fields": [],
                }
            )
        },
    }
    if problem == "length":
        raw["done_reason"] = "length"
    elif problem == "context":
        raw["prompt_eval_count"] = 7000
    else:
        raw["message"]["content"] = raw["message"]["content"].replace('"real"', '"invented"')
    with pytest.raises(ValueError):
        runner.accept_completion(
            raw, payload, "hybrid", {"context_length": 8192, "output_tokens": 2048}
        )


@pytest.mark.parametrize("include_control", [True, False])
def test_identical_bodies_are_called_independently_and_failures_survive_resume(
    tmp_path, monkeypatch, include_control
):
    root = tmp_path / "project"
    module = root / "tools/run_frozen_retrieval_judgments.py"
    sources = [
        module,
        root / "tools/prepare_retrieval_judgments.py",
        *[
            root / "src/occupational_fitness_rag/evaluation" / name
            for name in ("judgment_comparison.py", "model_judgment.py", "graph_completion.py")
        ],
    ]
    for path in sources:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixed test source")
    monkeypatch.setattr(runner, "__file__", str(module))
    payload = {
        "licence_context": "commercial",
        "modules": ["hearing"],
        "nurse_note": "Possible hearing loss.",
        "verified_patient_facts": {},
        "guideline_evidence": [{"source_id": "s", "source_text": "Original criterion."}],
    }
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
            "method": method,
            "model": "local",
            "repeat": repeat,
            "payload_identity": method,
            "request_identity": rid,
        }
        for method in ("hybrid", "planned_hybrid")
        for repeat in range(3)
    ]
    payloads = [
        {"case_id": "case", "method": method, "payload": payload, "status": "ready"}
        for method in (
            ("no_evidence", "hybrid", "planned_hybrid")
            if include_control
            else ("hybrid", "planned_hybrid")
        )
    ]
    config = {
        "models": ["local"],
        "context_length": 8192,
        "output_tokens": 2048,
        "endpoint": "http://127.0.0.1:11434",
    }
    monkeypatch.setattr(
        runner,
        "prepare_inputs",
        lambda *args: (
            config,
            {"identity": "prepared"},
            {},
            None,
            payloads,
            {rid: body},
            conditions,
        ),
    )
    monkeypatch.setattr(runner, "runtime", lambda config: {})
    monkeypatch.setattr(runner, "verify_files", lambda directory: {})
    preparation = root / "prepared"
    write_json(
        preparation / "scoring_labels.json",
        {"case": {"reference_outcome": "insufficient_information", "cohort": "engineering"}},
    )
    sent = []

    def post(endpoint, route, request, timeout):
        assert request == body
        assert "reference_outcome" not in json.dumps(request)
        sent.append(request)
        return {
            "done": True,
            "done_reason": "length" if len(sent) == 1 else "stop",
            "prompt_eval_count": 100,
            "message": {
                "content": json.dumps(
                    {
                        "assessment_outcome": "insufficient_information",
                        "explanation": "Missing verified measurements.",
                        "source_ids": ["s"],
                        "fact_fields": [],
                    }
                )
            },
        }

    monkeypatch.setattr(runner, "local_post", post)
    output = root / "outputs/experiments/test"
    summary = runner.run(preparation, output)
    assert len(sent) == summary["actual_judgment_calls"] == 6  # No body-level deduplication.
    assert summary["failed"] == 1 and summary["accepted"] == 5
    rows = [json.loads(line) for line in (output / "results.jsonl").read_text().splitlines()]
    assert rows[0]["raw_response"]["done_reason"] == "length"
    assert rows[0]["status"] == "failed"
    first_bytes = (output / "results.jsonl").read_bytes()
    resumed = runner.run(preparation, output, resume=True)
    assert resumed["complete"] and len(sent) == 6
    assert (output / "results.jsonl").read_bytes() == first_bytes


def test_empty_or_inconsistent_ready_cases_fail_before_execution():
    with pytest.raises(ValueError, match="nonempty"):
        runner.select_conditions([], [])
    payloads = [
        {"case_id": "case", "method": "new", "status": "ready", "payload": {"x": False}},
        {"case_id": "case", "method": "other", "status": "ready", "payload": {"x": 0}},
    ]
    with pytest.raises(ValueError, match="disagree"):
        runner.select_conditions(payloads, [{"case_id": "case"}])
    with pytest.raises(ValueError, match="inventories"):
        runner.select_conditions(payloads[:1], [{"case_id": "different"}])


def test_paired_changes_separate_improvements_regressions_and_failures():
    labels = {
        "a": {"reference_outcome": "does_not_meet_standard"},
        "b": {"reference_outcome": "insufficient_information"},
        "c": {"reference_outcome": "insufficient_information"},
    }
    rows = []
    for case, before, after in (
        ("a", "insufficient_information", "does_not_meet_standard"),
        ("b", "insufficient_information", "meets_unconditional_standard"),
        ("c", "insufficient_information", None),
    ):
        for method, outcome in (("hybrid", before), ("planned_hybrid", after)):
            row = {
                "case_id": case,
                "method": method,
                "model": "local",
                "repeat": 0,
                "status": "completed" if outcome else "failed",
            }
            if outcome:
                row["answer"] = {"assessment_outcome": outcome}
            rows.append(row)
    changes = runner.paired_judgments(rows, labels)
    assert [r["change"] for r in changes] == [
        "wrong_to_correct",
        "correct_to_wrong",
        "run_or_contract_failure",
    ]
    metrics = runner.scoring(rows, labels)
    proposed = next(r for r in metrics if r["method"] == "planned_hybrid")
    assert proposed["engineering_reference_agreement_all_recorded"] == 1 / 3
    assert proposed["engineering_reference_agreement_accepted"] == 1 / 2
