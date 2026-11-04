"""Native worker contracts with isolated mocks; no checkpoint or model download."""

from __future__ import annotations

import hashlib
import json
import sys
from copy import deepcopy
from types import ModuleType

import pytest

from tools import flag_embedding_extension_worker as worker


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.fixture
def native_job(tmp_path, monkeypatch):
    """Provide source-bound inputs and mock only the external native package."""
    checkpoint = tmp_path / "checkpoint"
    checkpoint.mkdir()
    weights = checkpoint / "weights.bin"
    weights.write_bytes(b"mock checkpoint bytes for contract tests only")
    receipt = tmp_path / "checkpoint_receipt.json"
    worker.save(
        receipt,
        {
            "revision": "fixed-checkpoint-revision",
            "completed": True,
            "local_dir": str(checkpoint),
            "files": {"weights.bin": worker.sha(weights)},
        },
    )
    units = [
        {
            "source_id": sid,
            "module": "vision",
            "licence_context": "commercial",
            "evidence_text": "Complete original commercial visual criterion " + sid,
            "text_sha256": text_hash("Complete original commercial visual criterion " + sid),
        }
        for sid in ("A", "B")
    ]
    job = {
        "experiment_identity": "frozen-input-identity",
        "corpus": {"units": units},
        "queries": [
            {
                "query_id": "q",
                "case_id": "case",
                "module": "vision",
                "licence_context": "commercial",
                "query": "Source-literal commercial visual query",
            }
        ],
        "candidates": {"q": ["A", "B"]},
        "config": {
            "checkpoint_receipt": str(receipt),
            "checkpoint_revision": "fixed-checkpoint-revision",
            "expected_versions": {"FlagEmbedding": "test-flag", "torch": "test-torch"},
            "threads": 1,
            "max_length": 16,
            "batch_size": 2,
        },
    }
    input_path = tmp_path / "input.json"
    worker.save(input_path, job)
    state = {
        "constructors": [],
        "calls": [],
        "threads": [],
        "scores": [0.25, 0.9],
        "score_error": None,
        "tokenizer_error": False,
        "token_count": 12,
    }

    class FakeReranker:
        def __init__(self, path, **kwargs):
            state["constructors"].append({"path": path, **kwargs})

        def tokenizer(self, query, original, **kwargs):
            assert kwargs == {"add_special_tokens": True, "truncation": False}
            if state["tokenizer_error"]:
                raise ValueError("mock tokenizer failed before inference")
            return {"input_ids": list(range(state["token_count"]))}

        def compute_score(self, pairs, **kwargs):
            state["calls"].append({"pairs": deepcopy(pairs), **kwargs})
            if state["score_error"] is not None:
                raise state["score_error"]
            return state["scores"]

    torch = ModuleType("torch")
    torch.set_num_threads = state["threads"].append
    flag = ModuleType("FlagEmbedding")
    flag.FlagReranker = FakeReranker
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "FlagEmbedding", flag)
    monkeypatch.setattr(
        worker.importlib.metadata, "version", job["config"]["expected_versions"].__getitem__
    )
    # Worker offline flags must not leak into the surrounding pytest process.
    for key in ("HF_HUB_OFFLINE", "HF_HUB_DISABLE_TELEMETRY"):
        monkeypatch.setenv(key, "test-environment-before-worker")
    return job, input_path, tmp_path / "output", state


def results(output):
    return [
        json.loads(line)
        for line in (output / "results.jsonl").read_text(encoding="utf-8").splitlines()
    ]


def update_result_cache(output, rows):
    """Keep file pins consistent so tests exercise semantic cache validation."""
    (output / "results.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    pins_path = output / "artifacts.json"
    if pins_path.exists():
        pins = json.loads(pins_path.read_bytes())
        pins["results.jsonl"] = worker.sha(output / "results.jsonl")
        worker.save(pins_path, pins)


def test_native_adapter_uses_original_pairs_and_a_pinned_offline_cpu_checkpoint(native_job):
    job, source, output, state = native_job
    original = deepcopy(job)
    summary = worker.run(source, output)
    assert summary["completed"] == 1 and summary["failed"] == 0
    assert summary["native_scoring_calls"] == 1 and len(state["calls"]) == 1
    assert state["calls"][0]["pairs"] == [
        (job["queries"][0]["query"], unit["evidence_text"]) for unit in job["corpus"]["units"]
    ]
    assert state["constructors"][0] == {
        "path": str(source.parent / "checkpoint"),
        "devices": ["cpu"],
        "use_fp16": False,
        "trust_remote_code": False,
        "max_length": 16,
        "batch_size": 2,
    }
    assert state["calls"][0]["normalize"] is True
    assert results(output)[0]["source_ids"] == ["B", "A"]
    assert json.loads(source.read_bytes()) == original
    assert summary["ollama_calls"] == 0 and summary["docling_changes_applied_to_corpus"] is False


def test_equal_scores_keep_original_rrf_ties_and_flag_scoring_input_truncation(native_job):
    _, source, output, state = native_job
    state["scores"] = [0.5, 0.5]
    state["token_count"] = 40
    summary = worker.run(source, output)
    row = results(output)[0]
    assert row["source_ids"] == ["A", "B"]
    assert all(c["scorer_input_truncated"] for c in row["candidate_trace"])
    assert row["returned_source_text_modified"] is False
    assert summary["scorer_truncated_pairs"] == 2


@pytest.mark.parametrize("scores", [[], [0.5], [float("nan"), 0.5], [1.1, 0.5]])
def test_invalid_native_scores_are_failed_attempts_without_original_rrf_fallback(
    native_job, scores
):
    _, source, output, state = native_job
    state["scores"] = scores
    summary = worker.run(source, output)
    row = results(output)[0]
    assert row["status"] == "failed" and row["source_ids"] == []
    assert "error" in row and summary["failed"] == 1 and summary["completed"] == 0
    assert len(state["calls"]) == 1 and summary["native_scoring_calls"] == 1


def test_native_exception_is_retained_and_counted_as_an_actual_attempt(native_job):
    _, source, output, state = native_job
    state["score_error"] = RuntimeError("mock native inference failure")
    summary = worker.run(source, output)
    row = results(output)[0]
    assert row["source_ids"] == [] and "native inference failure" in row["error"]
    assert summary["native_scoring_calls"] == 1 and summary["failed"] == 1


def test_tokenizer_failure_is_not_counted_as_a_native_scoring_call(native_job):
    _, source, output, state = native_job
    state["tokenizer_error"] = True
    summary = worker.run(source, output)
    assert results(output)[0]["status"] == "failed"
    assert state["calls"] == [] and summary["native_scoring_calls"] == 0


@pytest.mark.parametrize(
    "change",
    [
        lambda j: j["corpus"]["units"][0].update(evidence_text="Changed original source"),
        lambda j: j["corpus"]["units"][0].update(module="diabetes"),
        lambda j: j["corpus"]["units"][0].update(licence_context="private"),
        lambda j: j["queries"].append(deepcopy(j["queries"][0])),
        lambda j: j["candidates"].update(other_query=["A"]),
        lambda j: j["candidates"].update(q=["A", "A"]),
        lambda j: j.update(reference_outcome="unfit"),
        lambda j: j["queries"][0].update(expected_source_ids=["A"]),
    ],
)
def test_stale_sources_scope_duplicates_and_injected_answers_fail_before_native_load(
    native_job, change
):
    job, source, output, state = native_job
    change(job)
    worker.save(source, job)
    with pytest.raises(ValueError):
        worker.run(source, output)
    assert state["constructors"] == [] and state["calls"] == []


@pytest.mark.parametrize("mismatch", ["revision", "weights", "version"])
def test_checkpoint_or_package_drift_is_rejected_before_native_load(
    native_job, monkeypatch, mismatch
):
    job, source, output, state = native_job
    if mismatch == "revision":
        job["config"]["checkpoint_revision"] = "wrong-revision"
        worker.save(source, job)
    elif mismatch == "weights":
        (source.parent / "checkpoint/weights.bin").write_bytes(b"changed checkpoint")
    else:
        monkeypatch.setattr(
            worker.importlib.metadata, "version", lambda _: "different-native-version"
        )
    with pytest.raises(ValueError):
        worker.run(source, output)
    assert state["constructors"] == [] and state["calls"] == []


@pytest.mark.parametrize(
    "corrupt",
    [
        lambda r: r[0].update(source_ids=[]),
        lambda r: r[0].update(source_ids=["A", "A"]),
        lambda r: r[0].update(source_ids=["not-an-original-candidate"]),
        lambda r: r.append(deepcopy(r[0])),
    ],
)
def test_semantically_invalid_completed_cache_is_not_accepted_on_resume(native_job, corrupt):
    _, source, output, state = native_job
    worker.run(source, output)
    rows = results(output)
    corrupt(rows)
    update_result_cache(output, rows)
    before = len(state["calls"])
    with pytest.raises(ValueError):
        worker.run(source, output, resume=True)
    assert len(state["calls"]) == before


def test_complete_resume_does_not_rescore_existing_conditions(native_job):
    _, source, output, state = native_job
    worker.run(source, output)
    summary = worker.run(source, output, resume=True)
    assert summary["recorded"] == 1 and summary["native_scoring_calls"] == 1
    assert len(state["calls"]) == 1
