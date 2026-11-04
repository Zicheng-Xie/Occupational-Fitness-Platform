"""A serial continuation must not launch a model after an incomplete first run."""

import argparse
import importlib.util
import json
from pathlib import Path

import pytest
import yaml


def load_tool():
    spec = importlib.util.spec_from_file_location(
        "serial_followup_tool", Path("tools/run_applicability_followup.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_incomplete_original_never_starts_followup(tmp_path, monkeypatch):
    tool = load_tool()
    first = tmp_path / "original"
    first.mkdir()
    key = ["model", "case", "module_query", "passage_selection", 0]
    manifest = {"identity": "fixture", "planned_conditions": 2, "planned_keys": [key, key]}
    (first / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (first / "results.jsonl").write_text(
        json.dumps(
            {
                **dict(zip(("model", "case_id", "evidence_policy", "protocol", "repeat"), key)),
                "experiment_identity": "fixture",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    config = tmp_path / "followup.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "output": str(tmp_path / "sensitivity"),
                "case_ids": ["case"],
                "models": ["model"],
                "evidence_policies": ["module_query"],
                "protocols": ["passage_selection"],
                "repeats": 1,
            }
        ),
        encoding="utf-8",
    )

    def no_process(*args, **kwargs):
        raise AssertionError("A failed original run must never launch a subprocess")

    monkeypatch.setattr(tool.subprocess, "Popen", no_process)
    state = tmp_path / "state"
    args = argparse.Namespace(
        first_directory=str(first),
        second_config=str(config),
        state_directory=str(state),
        first_conditions=2,
        second_conditions=1,
        resume_second=False,
        wait_timeout_seconds=1,
    )
    with pytest.raises(ValueError, match="incomplete"):
        tool.execute(args)
    saved = json.loads((state / "state.json").read_bytes())
    assert saved["stage"] == "failed"
    assert not (state / ".helper.lock").exists()


def test_running_writer_snapshot_is_rejected(tmp_path):
    tool = load_tool()
    (tmp_path / ".run.lock").write_text("123")
    with pytest.raises(ValueError, match="has not stopped"):
        tool.completed_snapshot(tmp_path, 1, "unused")


def test_writer_lock_disappearance_is_a_finished_poll():
    tool = load_tool()

    class DisappearingLock:
        def read_text(self, **kwargs):
            raise FileNotFoundError("writer completed between filesystem operations")

    assert tool.read_lock(DisappearingLock()) is None
