"""Cross-stage review is provenance checked, blinded and never an outcome rewrite."""

import csv
import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest


def tool():
    spec = importlib.util.spec_from_file_location(
        "cross_stage_audit",
        Path(__file__).resolve().parents[1] / "tools/audit_applicability_disagreements.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def example(audit):
    text = "Original conditional criterion <script>alert(1)</script>."
    check = {
        "module": "diabetes",
        "passage_id": "P1",
        "fact_fields": ["diabetes.present"],
        "licence_pathway": "conditional",
        "finding": "conditional_permission",
        "conclusion": "A proposed permission.",
    }
    source = {
        "source_id": "S1",
        "module": "diabetes",
        "section": "3.3",
        "pdf_page": 9,
        "printed_page": 8,
        "source_text": text,
    }
    payload = {
        "licence_context": "commercial",
        "modules": ["diabetes"],
        "nurse_note": "Original note.",
        "verified_patient_facts": {
            "diabetes.present": {"value": True, "patient_quotes": ["Original note."]}
        },
        "guideline_evidence": [source],
    }
    first = {
        **check,
        "applicability": "uncertain",
        "statement_type": "conditional_opportunity",
        "prerequisites": [
            {"requirement": "Specialist review", "status": "unknown", "fact_fields": []}
        ],
        "numeric_application": "No documented interval.",
    }
    return {
        "model": "pinned-model",
        "case_id": "CASE-01",
        "evidence_policy": "module_query",
        "protocol": "applicability_first",
        "repeat": 0,
        "experiment_identity": "identity",
        "status": "completed",
        "input_snapshot": payload,
        "input_sha256": audit.digest(payload),
        "reference_outcome": "REFERENCE_NOT_FOR_BLIND_REVIEW",
        "answer": {
            "assessment_outcome": "OVERALL_OUTCOME_NOT_FOR_BLIND_REVIEW",
            "criterion_checks": [check],
        },
        "stages": {"applicability": {"answer": {"passage_checks": [first]}}},
        "criterion_locations": [
            {
                "passage_id": "P1",
                "source_id": "S1",
                "section": "3.3",
                "pdf_page": 9,
                "printed_page": 8,
                "text_sha256": audit.sha256(text.encode()),
                "spans": [{"char_start": 0, "char_end": len(text), "original_quote": text}],
                "check": deepcopy(check),
            }
        ],
    }


def freeze(tmp_path, audit, rows):
    raw = ("\n".join(json.dumps(row) for row in rows) + "\n").encode()
    (tmp_path / "results.jsonl").write_bytes(raw)
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "identity": "identity",
                "planned_keys": [[row[key] for key in audit.KEY_FIELDS] for row in rows],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "execution_audit.json").write_text(
        json.dumps({"results_sha256": audit.sha256(raw)}), encoding="utf-8"
    )


def test_flags_two_reasons_retains_source_and_blinds_outcomes_without_mutation():
    audit = tool()
    row = example(audit)
    before = deepcopy(row)
    events = audit.collect_disagreements([row])
    assert len(events) == 1 and len(events[0]["reasons"]) == 2
    assert events[0]["original_passage"]["source_id"] == "S1"
    assert (
        events[0]["patient_context"]["verified_patient_facts"]
        == row["input_snapshot"]["verified_patient_facts"]
    )
    assert "NOT_FOR_BLIND_REVIEW" not in json.dumps(events)
    assert row == before


def test_other_findings_and_met_applicable_permission_are_not_flagged():
    audit = tool()
    row = example(audit)
    row["answer"]["criterion_checks"][0]["finding"] = "established_restriction"
    assert audit.collect_disagreements([row]) == []
    row = example(audit)
    first = row["stages"]["applicability"]["answer"]["passage_checks"][0]
    first["applicability"] = "applicable"
    first["prerequisites"][0]["status"] = "met"
    assert audit.collect_disagreements([row]) == []


@pytest.mark.parametrize("mutation", ["facts", "source", "span"])
def test_changed_patient_source_or_quotation_is_rejected(mutation):
    audit = tool()
    row = example(audit)
    if mutation == "facts":
        row["input_snapshot"]["verified_patient_facts"]["diabetes.present"]["value"] = False
    elif mutation == "source":
        row["criterion_locations"][0]["pdf_page"] = 99
    else:
        row["criterion_locations"][0]["spans"][0]["original_quote"] = "Changed"
    with pytest.raises(ValueError):
        audit.collect_disagreements([row])


@pytest.mark.parametrize("mutation", ["live", "tail", "hash", "missing", "duplicate", "identity"])
def test_requires_one_complete_stopped_snapshot(tmp_path, mutation):
    audit = tool()
    row = example(audit)
    freeze(tmp_path, audit, [row])
    if mutation == "live":
        (tmp_path / ".run.lock").write_text("running", encoding="utf-8")
    elif mutation == "tail":
        path = tmp_path / "results.jsonl"
        path.write_bytes(path.read_bytes().rstrip(b"\n"))
    elif mutation == "hash":
        path = tmp_path / "results.jsonl"
        path.write_bytes(path.read_bytes() + b"\n")
    elif mutation == "missing":
        path = tmp_path / "manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["planned_keys"].append(
            ["other", "CASE-02", "module_query", "applicability_first", 0]
        )
        path.write_text(json.dumps(manifest), encoding="utf-8")
    elif mutation == "duplicate":
        freeze(tmp_path, audit, [row, deepcopy(row)])
    else:
        row["experiment_identity"] = "changed"
        freeze(tmp_path, audit, [row])
    with pytest.raises(ValueError):
        audit.build(tmp_path)
    assert not (tmp_path / "cross_stage_review").exists()


def test_regeneration_preserves_annotations_and_rejects_disappearing_event(tmp_path):
    audit = tool()
    row = example(audit)
    freeze(tmp_path, audit, [row])
    report = audit.build(tmp_path)
    output = tmp_path / "cross_stage_review"
    path = output / "review.csv"
    with path.open(encoding="utf-8-sig", newline="") as stream:
        records = list(csv.DictReader(stream))
    records[0].update(
        review_status="uncertain", reviewer="Reviewer A", notes="Check source condition."
    )
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    before = path.read_bytes()
    assert audit.build(tmp_path)["judgments_changed"] == 0
    assert path.read_bytes() == before
    html = (output / "index.html").read_text(encoding="utf-8")
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "NOT_FOR_BLIND_REVIEW" not in html
    assert report["flagged_condition_count"] == 1
    records[0]["event_id"] = "missing"
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    with pytest.raises(ValueError, match="disappeared"):
        audit.build(tmp_path)


def test_empty_flag_set_has_a_header_only_worksheet(tmp_path):
    audit = tool()
    row = example(audit)
    row["status"] = "failed"
    freeze(tmp_path, audit, [row])
    report = audit.build(tmp_path)
    assert report["flagged_claim_occurrences"] == 0
    assert (
        len(
            (tmp_path / "cross_stage_review/review.csv")
            .read_text(encoding="utf-8-sig")
            .splitlines()
        )
        == 1
    )
