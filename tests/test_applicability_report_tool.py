"""Paired report preserves stage visibility, identity and original records."""

import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def renderer():
    spec = importlib.util.spec_from_file_location(
        "render_applicability",
        Path(__file__).resolve().parents[1] / "tools/render_applicability_report.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def completed_fixture(directory):
    rows = []
    for repeat in range(3):
        for protocol in ("passage_selection", "applicability_first"):
            answer = {
                "assessment_outcome": "insufficient_information",
                "explanation": "<script>invalid()</script>",
                "criterion_checks": [],
            }
            rows.append(
                {
                    "model": "synthetic-model",
                    "case_id": "SYNTHETIC",
                    "evidence_policy": "module_query",
                    "protocol": protocol,
                    "repeat": repeat,
                    "experiment_identity": "synthetic-identity",
                    "status": "completed",
                    "answer": answer,
                    "input_sha256": "same-input",
                    "input_snapshot": {
                        "verified_patient_facts": {},
                        "guideline_evidence": [],
                        "nurse_note": "Synthetic note.",
                    },
                    "reference_outcome": "insufficient_information",
                    "output_consistency_flags": [],
                    "stages": {
                        "applicability": {
                            "ledger_consistency_flags": ["VISIBLE_LEDGER_FLAG"],
                            "attempts": [],
                            "answer": {"passage_checks": []},
                        }
                    }
                    if protocol == "applicability_first"
                    else {},
                }
            )
    manifest = {
        "identity": "synthetic-identity",
        "planned_keys": [
            [r[k] for k in ("model", "case_id", "evidence_policy", "protocol", "repeat")]
            for r in rows
        ],
    }
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (directory / "results.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8"
    )
    return rows, manifest


def test_paired_render_escapes_text_and_preserves_raw_inputs(renderer, tmp_path):
    completed_fixture(tmp_path)
    raw = (tmp_path / "results.jsonl").read_bytes()
    result = renderer.render_report(tmp_path)
    assert (tmp_path / "results.jsonl").read_bytes() == raw
    assert result["results_sha256"] == renderer.sha256(raw)
    html = (tmp_path / "review.html").read_text(encoding="utf-8")
    assert "<script>invalid()</script>" not in html
    assert "&lt;script&gt;invalid()&lt;/script&gt;" in html
    assert 'data-flag-stage="ledger"' in html and "VISIBLE_LEDGER_FLAG" in html
    assert html.count('data-protocol="passage_selection"') == 3
    assert html.count('data-protocol="applicability_first"') == 3
    assert html.index('data-protocol="passage_selection"') < html.index(
        'data-protocol="applicability_first"'
    )
    repeatability = json.loads((tmp_path / "repeatability.json").read_text(encoding="utf-8"))
    assert all(r["stable_outcome"] and r["accepted_calls"] == 3 for r in repeatability["groups"])


def test_partial_records_and_active_writer_are_not_rendered(renderer, tmp_path):
    completed_fixture(tmp_path)
    (tmp_path / ".run.lock").write_text("1", encoding="ascii")
    with pytest.raises(ValueError, match="run lock"):
        renderer.render_report(tmp_path)
    (tmp_path / ".run.lock").unlink()
    path = tmp_path / "results.jsonl"
    path.write_bytes(path.read_bytes()[:-1])
    with pytest.raises(ValueError, match="newline"):
        renderer.render_report(tmp_path)
    assert not (tmp_path / "review.html").exists()


def test_failed_condition_is_not_presented_as_a_valid_wrong_judgment(renderer, tmp_path):
    rows, _ = completed_fixture(tmp_path)
    failed = rows[1]
    failed.update(status="failed", stages={"applicability": {"status": "failed", "attempts": []}})
    failed.pop("answer")
    (tmp_path / "results.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    renderer.render_report(tmp_path)
    html = (tmp_path / "review.html").read_text(encoding="utf-8")
    assert "No accepted judgment; execution failure is reported separately." in html
    assert "Stage 1 ledger not accepted" in html
    stability = json.loads((tmp_path / "repeatability.json").read_text(encoding="utf-8"))
    proposed = next(
        group for group in stability["groups"] if group["protocol"] == "applicability_first"
    )
    assert proposed["failed_calls"] == 1 and proposed["stable_outcome"] is None
