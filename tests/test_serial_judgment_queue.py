"""Serial continuation checks with no real subprocess or model calls."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.provenance import digest
from tools import run_serial_judgment_queue as queue


def pin(directory):
    files = {
        p.name: file_hash(p)
        for p in directory.iterdir()
        if p.name not in {"artifacts.json", ".run.lock"}
    }
    queue.write_json(directory / "artifacts.json", files)
    return files


def finish(directory, plan, failed=0):
    directory.mkdir(parents=True, exist_ok=True)
    queue.write_json(directory / "plan.json", plan)
    queue.write_json(directory / "requests.json", {})
    queue.write_json(directory / "payloads.json", [])
    rows = [
        {
            **condition,
            "experiment_identity": plan["identity"],
            "status": "failed" if index < failed else "completed",
        }
        for index, condition in enumerate(plan["conditions"])
    ]
    import json

    (directory / "results.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    queue.write_json(
        directory / "summary.json",
        {
            "identity": plan["identity"],
            "complete": True,
            "planned": len(rows),
            "recorded": len(rows),
            "accepted": len(rows) - failed,
            "failed": failed,
            "actual_judgment_calls": len(rows),
        },
    )
    pin(directory)


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    root = tmp_path / "project"
    root.mkdir()
    for name in queue.SOURCE_NAMES:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("frozen actor source", encoding="utf-8")
    pp = root / queue.PARENT_PREPARATION
    pa = root / queue.PARENT_ADDITIONAL
    prep = root / queue.DEFAULT_PREPARATION
    parent = root / queue.DEFAULT_PARENT
    for directory in (pp, pa, prep, parent):
        directory.mkdir(parents=True)
    queue.write_json(pp / "manifest.json", {"identity": "parent-preparation"})
    pp_pins = pin(pp)
    (pa / "source.txt").write_text("fixed additional input", encoding="utf-8")
    pa_pins = pin(pa)
    runtime = {"version": {"version": "fixed"}, "models": {"a": "pin-a", "b": "pin-b"}}
    parent_data = {
        "preparation_identity": "parent-preparation",
        "preparation_artifacts": pp_pins,
        "additional_artifacts": pa_pins,
        "runtime": runtime,
        "sources": {name: file_hash(root / name) for name in queue.SOURCE_NAMES},
        "conditions": [
            {
                "case_id": "case",
                "method": "hybrid",
                "model": "a",
                "repeat": 0,
                "request_identity": "fixed-request",
            }
        ],
    }
    parent_plan = {**parent_data, "identity": digest(parent_data), "production_change": False}
    queue.write_json(parent / "plan.json", parent_plan)
    config = {"models": ["a", "b"], "repeats": 3}
    manifest = {
        "identity": "child-preparation",
        "config": config,
        "parent_preparation_identity": "parent-preparation",
        "parent_preparation_artifacts_sha256": file_hash(pp / "artifacts.json"),
    }
    queue.write_json(prep / "manifest.json", manifest)
    prep_pins = pin(prep)
    conditions = [
        {
            "case_id": f"case-{case:02}",
            "method": "planned_hybrid_v2_containment",
            "model": model,
            "repeat": repeat,
            "request_identity": "fixed-request",
        }
        for case in range(33)
        for model in ("a", "b")
        for repeat in range(3)
    ]
    monkeypatch.setattr(
        queue.actor,
        "prepare_inputs",
        lambda path: (
            config,
            manifest,
            prep_pins,
            None,
            [
                {
                    "case_id": f"case-{case:02}",
                    "method": "planned_hybrid_v2_containment",
                    "status": "ready",
                    "payload": {"modules": ["hearing"], "nurse_note": str(case)},
                }
                for case in range(33)
            ],
            {},
            conditions,
        ),
    )
    monkeypatch.setattr(queue.actor, "runtime", lambda config: deepcopy(runtime))
    monkeypatch.setattr(queue.actor, "local_post", lambda *args: pytest.fail("No model calls"))
    monkeypatch.setattr(
        queue.subprocess,
        "Popen",
        lambda *args, **kwargs: pytest.fail("Unexpected real child launch"),
    )
    return SimpleNamespace(
        root=root,
        parent=parent,
        prep=prep,
        config=config,
        parent_plan=parent_plan,
        runtime=runtime,
        output=root / queue.DEFAULT_OUTPUT,
        queue=root / queue.DEFAULT_QUEUE,
    )


def test_once_waits_for_live_parent_without_starting_child(prepared, monkeypatch):
    p = prepared
    (p.parent / ".run.lock").write_text("123", encoding="ascii")
    monkeypatch.setattr(queue, "process_identity", lambda pid: {"pid": pid, "creation_time": 10})
    result = queue.run(p.root, once=True)
    assert result["state"] == "waiting_for_predecessor"
    assert not p.output.exists()
    assert not (p.queue / ".run.lock").exists()
    assert queue.read_json(p.queue / "plan.json")["expected_child_plan"]["conditions"]


def test_once_ready_status_never_dispatches_and_failed_parent_attempts_are_retained(prepared):
    p = prepared
    finish(p.parent, p.parent_plan, failed=1)
    result = queue.run(p.root, once=True)
    assert result["state"] == "ready_without_dispatch"
    assert result["parent_completion"]["failed"] == 1
    assert not p.output.exists()


def test_completed_parent_dispatches_one_child_with_exact_frozen_actor_command(
    prepared, monkeypatch
):
    p = prepared
    finish(p.parent, p.parent_plan)
    sent = []

    def launch(args, **kwargs):
        sent.append((args, kwargs))
        plan = queue.read_json(p.queue / "plan.json")["expected_child_plan"]
        finish(p.output, plan, failed=2)
        return SimpleNamespace(pid=456, poll=lambda: 0)

    monkeypatch.setattr(queue.subprocess, "Popen", launch)
    monkeypatch.setattr(queue, "process_identity", lambda pid: {"pid": pid, "creation_time": 20})
    result = queue.run(p.root)
    assert result["state"] == "complete"
    assert result["child_completion"]["recorded"] == 198
    assert result["child_completion"]["failed"] == 2
    assert len(sent) == 1
    args, kwargs = sent[0]
    assert args[1:5] == ["-X", "utf8", "-m", "tools.run_frozen_retrieval_judgments"]
    assert args[5:] == ["--preparation", str(p.prep), "--output", str(p.output)]
    assert kwargs["cwd"] == str(p.root)
    assert kwargs["stderr"] == queue.subprocess.STDOUT
    resumed = queue.run(p.root, resume=True)
    assert resumed == result and len(sent) == 1


def test_parent_must_finalize_and_release_lock_before_dispatch(prepared, monkeypatch):
    p = prepared
    marker = p.parent / ".run.lock"
    marker.write_text("123", encoding="ascii")
    monkeypatch.setattr(queue, "process_identity", lambda pid: {"pid": pid, "creation_time": 10})
    once = queue.run(p.root, once=True)
    assert once["state"] == "waiting_for_predecessor"
    finish(p.parent, p.parent_plan)
    # Completion artifacts alone do not authorize overlap while the lock is held.
    second = queue.run(p.root, resume=True, once=True)
    assert second["state"] == "waiting_for_predecessor"
    marker.unlink()
    ready = queue.run(p.root, resume=True, once=True)
    assert ready["state"] == "ready_without_dispatch"


def test_dead_predecessor_process_fails_with_retained_status_and_lock(prepared, monkeypatch):
    p = prepared
    marker = p.parent / ".run.lock"
    marker.write_text("123", encoding="ascii")
    monkeypatch.setattr(queue, "process_identity", lambda pid: None)
    with pytest.raises(ValueError, match="has exited"):
        queue.run(p.root)
    assert marker.exists()
    status = queue.read_json(p.queue / "status.json")
    assert status["state"] == "failed" and "has exited" in status["error"]
    assert not p.output.exists()


def test_changed_predecessor_process_creation_time_blocks_reused_pid(prepared, monkeypatch):
    p = prepared
    (p.parent / ".run.lock").write_text("123", encoding="ascii")
    monkeypatch.setattr(queue, "process_identity", lambda pid: {"pid": pid, "creation_time": 10})
    queue.run(p.root, once=True)
    monkeypatch.setattr(queue, "process_identity", lambda pid: {"pid": pid, "creation_time": 11})
    with pytest.raises(ValueError, match="process identity changed"):
        queue.run(p.root, resume=True)
    assert queue.read_json(p.queue / "status.json")["state"] == "failed"


def test_missing_lock_and_incomplete_predecessor_never_dispatch(prepared):
    p = prepared
    queue.write_json(p.parent / "summary.json", {"complete": False})
    with pytest.raises(ValueError, match="incomplete"):
        queue.run(p.root)
    assert queue.read_json(p.queue / "status.json")["state"] == "failed"
    assert not p.output.exists()


@pytest.mark.parametrize("changed", ["actor_source", "preparation_artifact", "parent_plan"])
def test_drift_during_waiting_stops_before_model_dispatch(prepared, monkeypatch, changed):
    p = prepared
    (p.parent / ".run.lock").write_text("123", encoding="ascii")
    monkeypatch.setattr(queue, "process_identity", lambda pid: {"pid": pid, "creation_time": 10})

    def mutate(seconds):
        assert seconds == 10
        path = {
            "actor_source": p.root / queue.SOURCE_NAMES[0],
            "preparation_artifact": p.prep / "manifest.json",
            "parent_plan": p.parent / "plan.json",
        }[changed]
        path.write_text("drift", encoding="utf-8")

    monkeypatch.setattr(queue.time, "sleep", mutate)
    with pytest.raises((ValueError, queue.json.JSONDecodeError)):
        queue.run(p.root)
    assert queue.read_json(p.queue / "status.json")["state"] == "failed"
    assert not p.output.exists()


def test_runtime_drift_before_dispatch_is_retained(prepared, monkeypatch):
    p = prepared
    finish(p.parent, p.parent_plan)
    calls = []

    def runtime(config):
        calls.append(config)
        return p.runtime if len(calls) == 1 else {"version": {"version": "changed"}}

    monkeypatch.setattr(queue.actor, "runtime", runtime)
    with pytest.raises(ValueError, match="runtime changed before"):
        queue.run(p.root)
    assert queue.read_json(p.queue / "status.json")["state"] == "failed"


def test_another_live_experiment_blocks_serial_dispatch(prepared, monkeypatch):
    p = prepared
    finish(p.parent, p.parent_plan)
    other = p.root / "outputs/experiments/another/.run.lock"
    other.parent.mkdir()
    other.write_text("789", encoding="ascii")
    monkeypatch.setattr(queue, "process_identity", lambda pid: {"pid": pid, "creation_time": 10})
    with pytest.raises(ValueError, match="Another experiment process"):
        queue.run(p.root)
    assert other.exists() and not p.output.exists()


def test_child_exit_failure_preserves_process_identity_and_log(prepared, monkeypatch):
    p = prepared
    finish(p.parent, p.parent_plan)
    monkeypatch.setattr(
        queue.subprocess, "Popen", lambda *a, **k: SimpleNamespace(pid=456, poll=lambda: 7)
    )
    monkeypatch.setattr(queue, "process_identity", lambda pid: {"pid": pid, "creation_time": 20})
    with pytest.raises(ValueError, match="exited with code 7"):
        queue.run(p.root)
    status = queue.read_json(p.queue / "status.json")
    assert status["state"] == "failed"
    assert status["child_process"] == {"pid": 456, "creation_time": 20}
    assert (p.queue / "child.log").exists()


def test_completed_run_rejects_drift_and_counter_mismatch(prepared):
    p = prepared
    finish(p.parent, p.parent_plan)
    result = queue.completed_run(p.parent)
    assert result["recorded"] == 1
    (p.parent / "results.jsonl").write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="artifact changed"):
        queue.completed_run(p.parent)
    # Even a regenerated inventory cannot make an incomplete condition set pass.
    pin(p.parent)
    with pytest.raises(ValueError, match="counters"):
        queue.completed_run(p.parent)


def test_zero_condition_output_is_never_adopted_as_completed(prepared):
    p = prepared
    data = {k: v for k, v in p.parent_plan.items() if k not in {"identity", "production_change"}}
    data["conditions"] = []
    empty = {**data, "identity": digest(data), "production_change": False}
    finish(p.output, empty)
    with pytest.raises(ValueError, match="counters"):
        queue.completed_run(p.output)


def test_artifact_inventory_cannot_escape_owned_directory(tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("text")
    directory = tmp_path / "run"
    directory.mkdir()
    queue.write_json(directory / "artifacts.json", {"../outside.txt": file_hash(outside)})
    with pytest.raises(ValueError, match="escapes"):
        queue.verify_artifacts(directory)


def test_real_process_identity_reads_own_pid_without_terminating_it():
    import os

    result = queue.process_identity(os.getpid())
    assert result["pid"] == os.getpid()
    assert result["creation_time"] is not None
