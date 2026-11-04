import json

import pytest

from tools import run_case_allocation_series as series


def test_rejects_incomplete_pilot_before_any_full_calls(tmp_path, monkeypatch):
    directory = tmp_path / series.PILOT
    directory.mkdir(parents=True)
    (directory / "summary.json").write_text(
        json.dumps({"complete": False, "planned": 150}), encoding="utf-8"
    )
    (directory / "plan.json").write_text(json.dumps({"conditions": []}), encoding="utf-8")
    monkeypatch.setattr(series.actor, "verify_files", lambda p: {})
    with pytest.raises(ValueError, match="Finish and retain"):
        series.validate_pilot(tmp_path)


def test_rejects_fake_complete_pilot_inventory(tmp_path, monkeypatch):
    directory = tmp_path / series.PILOT
    directory.mkdir(parents=True)
    (directory / "summary.json").write_text(
        json.dumps({"complete": True, "planned": 150}), encoding="utf-8"
    )
    (directory / "plan.json").write_text(json.dumps({"conditions": []}), encoding="utf-8")
    monkeypatch.setattr(series.actor, "verify_files", lambda p: {})
    with pytest.raises(ValueError, match="Finish and retain"):
        series.validate_pilot(tmp_path)


def test_optional_batch_budget_cannot_skip_the_actual_protocol(tmp_path):
    with pytest.raises(ValueError, match="positive"):
        series.run(tmp_path, batch_size=0)


def test_exited_lock_is_preserved_with_verified_process_evidence(tmp_path, monkeypatch):
    path = tmp_path / "outputs/experiments/old/.run.lock"
    path.parent.mkdir(parents=True)
    path.write_text("123", encoding="ascii")
    monkeypatch.setattr(series, "process_identity", lambda pid: None)
    live, exited = series.inspect_foreign_locks(tmp_path, set())
    assert live == [] and exited[0]["lock_removed"] is False
    assert path.read_text() == "123"


def test_live_foreign_lock_is_not_ignored(tmp_path, monkeypatch):
    path = tmp_path / "outputs/experiments/other/.run.lock"
    path.parent.mkdir(parents=True)
    path.write_text("123", encoding="ascii")
    monkeypatch.setattr(series, "process_identity", lambda pid: {"pid": pid, "creation_time": 1})
    live, exited = series.inspect_foreign_locks(tmp_path, set())
    assert live == [str(path)] and exited == []
