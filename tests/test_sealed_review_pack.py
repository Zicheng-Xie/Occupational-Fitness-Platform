"""Prospective review cases remain fingerprinted and clinically unlabelled."""

import csv
import json
from pathlib import Path

import pytest

from scripts import seal_review_pack

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
