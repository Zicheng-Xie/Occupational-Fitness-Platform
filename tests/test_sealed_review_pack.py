"""Prospective review cases remain fingerprinted and clinically unlabelled."""

import csv
import json
from pathlib import Path

import pytest

from scripts import seal_review_pack, validate_review_labels

ROOT = Path(__file__).resolve().parents[1]


def test_review_pack_is_sealed_without_system_labels():
    manifest = seal_review_pack.verify()
    assert manifest["status"] == "sealed_awaiting_clinician_labels"
    assert manifest["independent_clinical_gold"] is False
    assert len(manifest["cases"]) == 10
    with (ROOT / "data/cases/sealed_review/case_review_template.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        cases = list(csv.DictReader(stream))
    assert len(cases) == 10
    assert all(not item["clinician_assessed_outcome"] for item in cases)
    assert all(not item["reviewed_relevant_source_ids"] for item in cases)
    with (ROOT / "data/cases/sealed_review/source_review_template.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        sources = list(csv.DictReader(stream))
    assert len(sources) == 28
    assert all(not item["reviewed_applicability"] for item in sources)
    assert json.loads(
        (ROOT / "data/cases/sealed_review/manifest.json").read_text(encoding="utf-8")
    )["cases"] == manifest["cases"]


def test_seal_detects_a_changed_note_fingerprint(monkeypatch):
    original = seal_review_pack.sha256

    def changed(path):
        if path.name == "SEALED-DM-01.txt":
            return "0" * 64
        return original(path)

    monkeypatch.setattr(seal_review_pack, "sha256", changed)
    with pytest.raises(ValueError, match="fingerprint"):
        seal_review_pack.verify()


def test_label_validator_requires_complete_human_fields(tmp_path):
    case_template = ROOT / "data/cases/sealed_review/case_review_template.csv"
    source_template = ROOT / "data/cases/sealed_review/source_review_template.csv"
    with pytest.raises(ValueError, match="reviewer name"):
        validate_review_labels.validate(case_template, source_template)

    with case_template.open(encoding="utf-8-sig", newline="") as stream:
        cases = list(csv.DictReader(stream))
    with source_template.open(encoding="utf-8-sig", newline="") as stream:
        sources = list(csv.DictReader(stream))
    rules = json.loads((ROOT / "configs/rules/austroads_commercial_v1.yaml").read_text())
    first_source = {}
    for rule in rules["rules"]:
        first_source.setdefault(rule["module"], rule["source_ids"][0])
    for row in cases:
        row.update(
            reviewed_relevant_source_ids=first_source[row["module"]],
            clinician_assessed_outcome="insufficient_information",
            verified_patient_facts="Structural test data only",
            review_rationale="Structural test data only",
            reviewer_name="Test Reviewer",
            review_date="2026-10-01",
        )
    for row in sources:
        row.update(
            reviewed_applicability="accepted",
            reviewer_name="Test Reviewer",
            review_date="2026-10-01",
        )

    def write_form(path, rows):
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    cases_path, sources_path = tmp_path / "cases.csv", tmp_path / "sources.csv"
    write_form(cases_path, cases)
    write_form(sources_path, sources)
    result = validate_review_labels.validate(cases_path, sources_path)
    assert result["label_status"] == "reviewed_reference_labels"
    assert len(result["cases"]) == 10
    cases[0]["sha256"] = "0" * 64
    write_form(cases_path, cases)
    with pytest.raises(ValueError, match="fingerprint"):
        validate_review_labels.validate(cases_path, sources_path)
    cases[0]["sha256"] = seal_review_pack.verify()["cases"][0]["sha256"]
    cases[0]["acceptable_alternative_source_ids"] = next(
        source_id for module, source_id in first_source.items() if module != cases[0]["module"]
    )
    write_form(cases_path, cases)
    with pytest.raises(ValueError, match="alternative source"):
        validate_review_labels.validate(cases_path, sources_path)
    cases[0]["acceptable_alternative_source_ids"] = ""
    write_form(cases_path, cases)
    sources[0]["pdf_page"] = "0"
    write_form(sources_path, sources)
    with pytest.raises(ValueError, match="anchor metadata"):
        validate_review_labels.validate(cases_path, sources_path)
