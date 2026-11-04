"""A completed replay audit must reject edited answers even with consistent summaries."""

import importlib.util
import json
from pathlib import Path

import pytest


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_execution_audit_reparses_accepted_raw_output(tmp_path, monkeypatch):
    fixtures = load(Path("tests/test_applicability_comparison.py"), "comparison_fixture")
    tool = load(Path("tools/audit_applicability_execution.py"), "execution_audit_tool")
    path, config, _ = fixtures.frozen.__wrapped__(tmp_path)
    fixtures.experiment.run_comparison(path, post=fixtures.post_model([]), get=fixtures.get(config))
    directory = Path(config["output"])
    manifest = json.loads((directory / "manifest.json").read_bytes())
    monkeypatch.setattr(
        tool.previous, "pinned_environment", lambda _config: manifest["environment"]
    )
    result = tool.audit(directory)
    assert result["conditions"] == 8
    assert result["accepted_attempts_reparsed"] == 12
    rows = [json.loads(line) for line in (directory / "results.jsonl").read_text().splitlines()]
    row = rows[0]
    changed = "An edited explanation that never came from the model."
    row["answer"]["explanation"] = changed
    row["attempts"][0]["answer"]["explanation"] = changed
    row["stages"]["outcome_first"]["answer"]["explanation"] = changed
    row["stages"]["outcome_first"]["attempts"][0]["answer"]["explanation"] = changed
    (directory / "results.jsonl").write_text(
        "".join(json.dumps(item) + "\n" for item in rows), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="reparsed raw output"):
        tool.audit(directory)
