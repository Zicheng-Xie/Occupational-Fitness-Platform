"""Validate completed clinician worksheets without inventing or changing labels."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date
from pathlib import Path

if __package__:
    from .seal_review_pack import PACK, ROOT, verify
else:
    from seal_review_pack import PACK, ROOT, verify

OUTCOMES = {
    "meets_unconditional_standard",
    "may_meet_conditional_standard",
    "temporarily_unfit",
    "does_not_meet_standard",
    "insufficient_information",
}


def _rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _source_ids(text, allowed):
    items = [value.strip() for value in text.split(";") if value.strip()]
    if not items or len(items) != len(set(items)) or not set(items) <= allowed:
        raise ValueError("Reviewed source IDs must be nonempty, unique and in the catalogue")
    return items


def _reviewer(row):
    if len(row["reviewer_name"].strip()) < 2:
        raise ValueError("A reviewer name is required")
    try:
        date.fromisoformat(row["review_date"])
    except ValueError as exc:
        raise ValueError("Review date must be YYYY-MM-DD") from exc


def validate(case_form: Path, source_form: Path):
    manifest = verify()
    catalogue = json.loads(
        (ROOT / "data/knowledge/processed/source_catalogue.json").read_text(encoding="utf-8")
    )
    catalogue_by_id = {unit["source_id"]: unit for unit in catalogue["units"]}
    source_ids = set(catalogue_by_id)
    expected_cases = {case["case_id"]: case for case in manifest["cases"]}
    cases = _rows(case_form)
    sources = _rows(source_form)
    if len(cases) != len(expected_cases) or {row["case_id"] for row in cases} != set(
        expected_cases
    ):
        raise ValueError("Case review form does not match the sealed case inventory")
    if len(sources) != len(source_ids) or {row["source_id"] for row in sources} != source_ids:
        raise ValueError("Source review form does not cover the sealed catalogue")
    modules_for_source = {source_id: set() for source_id in source_ids}
    rules = json.loads((ROOT / "configs/rules/austroads_commercial_v1.yaml").read_text())
    for rule in rules["rules"]:
        for source_id in rule["source_ids"]:
            modules_for_source[source_id].add(rule["module"])
    case_labels = []
    for row in cases:
        expected = expected_cases[row["case_id"]]
        if any(row[key] != expected[key] for key in ("module", "input", "sha256")):
            raise ValueError("Case identity or source fingerprint has changed")
        _reviewer(row)
        if row["clinician_assessed_outcome"] not in OUTCOMES:
            raise ValueError("A reviewed assessment outcome is required for every case")
        if not row["verified_patient_facts"].strip() or not row["review_rationale"].strip():
            raise ValueError("Verified facts and clinical rationale are required")
        relevant = _source_ids(row["reviewed_relevant_source_ids"], source_ids)
        if any(expected["module"] not in modules_for_source[source_id] for source_id in relevant):
            raise ValueError("A reviewed source is outside the selected case module")
        alternatives = (
            _source_ids(row["acceptable_alternative_source_ids"], source_ids)
            if row["acceptable_alternative_source_ids"].strip()
            else []
        )
        if any(expected["module"] not in modules_for_source[source_id] for source_id in alternatives):
            raise ValueError("An alternative source is outside the selected case module")
        case_labels.append(
            {
                "case_id": row["case_id"],
                "module": row["module"],
                "relevant_source_ids": relevant,
                "acceptable_alternative_source_ids": alternatives,
                "clinician_assessed_outcome": row["clinician_assessed_outcome"],
                "verified_patient_facts": row["verified_patient_facts"],
                "disputed_or_missing_facts": row["disputed_or_missing_facts"],
                "review_rationale": row["review_rationale"],
                "reviewer_name": row["reviewer_name"],
                "review_date": row["review_date"],
            }
        )
    source_labels = []
    for row in sources:
        unit = catalogue_by_id[row["source_id"]]
        fixed_fields = {
            "section": unit["section"],
            "printed_page": str(unit["printed_page"]),
            "pdf_page": str(unit["pdf_page"]),
            "table_row": unit["table_row"],
            "source_excerpt_display": " ".join(unit["evidence_text"].split()),
        }
        if any(row[key] != value for key, value in fixed_fields.items()):
            raise ValueError("Guideline anchor metadata or excerpt has changed")
        _reviewer(row)
        if row["reviewed_applicability"] not in {"accepted", "needs_revision", "rejected"}:
            raise ValueError("Every guideline anchor needs an applicability review")
        if row["reviewed_cross_references"].strip():
            _source_ids(row["reviewed_cross_references"], source_ids)
        source_labels.append(
            {
                "source_id": row["source_id"],
                "reviewed_applicability": row["reviewed_applicability"],
                "reviewed_cross_references": row["reviewed_cross_references"],
                "clinician_comments": row["clinician_comments"],
                "reviewer_name": row["reviewer_name"],
                "review_date": row["review_date"],
            }
        )
    return {
        "schema_version": "1.0.0",
        "label_status": (
            "reviewed_pending_adjudication"
            if any(row["reviewed_applicability"] != "accepted" for row in source_labels)
            else "reviewed_reference_labels"
        ),
        "clinical_validation": False,
        "sealed_manifest_sha256": hashlib.sha256((PACK / "manifest.json").read_bytes()).hexdigest(),
        "case_form_sha256": hashlib.sha256(case_form.read_bytes()).hexdigest(),
        "source_form_sha256": hashlib.sha256(source_form.read_bytes()).hexdigest(),
        "cases": case_labels,
        "source_reviews": source_labels,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=PACK / "case_review_template.csv")
    parser.add_argument("--sources", type=Path, default=PACK / "source_review_template.csv")
    parser.add_argument("--output", type=Path, default=PACK / "reviewed_labels.json")
    args = parser.parse_args()
    report = validate(args.cases, args.sources)
    if args.output.exists():
        raise FileExistsError("A reviewed label file already exists; preserve it as a version")
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{report['label_status']}: {len(report['cases'])} cases validated")


if __name__ == "__main__":
    main()
