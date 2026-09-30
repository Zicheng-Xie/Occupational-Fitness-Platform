"""Create and verify a prospective, unscored clinician review pack.

The command never runs retrieval, rules, or a model on the sealed notes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "data/cases/sealed_review"
MODULES = {"HTN": "hypertension", "VIS": "vision", "HEAR": "hearing", "BLK": "blackout", "DM": "diabetes"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory():
    notes = sorted((PACK / "notes").glob("SEALED-*.txt"))
    if len(notes) != 10:
        raise ValueError("The prospective review pack requires exactly ten note files")
    cases = []
    for path in notes:
        parts = path.stem.split("-")
        if len(parts) != 3 or parts[1] not in MODULES:
            raise ValueError(f"Unexpected sealed case name: {path.name}")
        case_id = path.stem
        if not path.read_text(encoding="utf-8").startswith(f"Case ID: {case_id}\n"):
            raise ValueError(f"Case header disagrees with its file name: {path.name}")
        cases.append(
            {
                "case_id": case_id,
                "module": MODULES[parts[1]],
                "input": path.relative_to(ROOT).as_posix(),
                "sha256": sha256(path),
            }
        )
    if set(Counter(case["module"] for case in cases).values()) != {2}:
        raise ValueError("The pack needs two notes for each pilot module")
    return cases


def create():
    targets = [
        PACK / "manifest.json",
        PACK / "case_review_template.csv",
        PACK / "source_review_template.csv",
    ]
    if any(path.exists() for path in targets):
        raise FileExistsError("Review pack already exists; use --verify instead of overwriting it")
    cases = inventory()
    catalogue_path = ROOT / "data/knowledge/processed/source_catalogue.json"
    rules_path = ROOT / "configs/rules/austroads_commercial_v1.yaml"
    catalogue = json.loads(catalogue_path.read_text(encoding="utf-8"))
    manifest = {
        "schema_version": "1.0.0",
        "split": "prospective_clinician_review_v1",
        "status": "sealed_awaiting_clinician_labels",
        "independent_clinical_gold": False,
        "retrieval_or_model_results_used_for_selection": False,
        "guideline_version": "AP-G56-22",
        "catalogue_sha256": sha256(catalogue_path),
        "rules_sha256": sha256(rules_path),
        "cases": cases,
    }
    targets[0].write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    with targets[1].open("w", encoding="utf-8-sig", newline="") as stream:
        columns = [
            "case_id", "module", "input", "sha256", "reviewed_relevant_source_ids",
            "acceptable_alternative_source_ids", "clinician_assessed_outcome",
            "verified_patient_facts", "disputed_or_missing_facts", "review_rationale",
            "reviewer_name", "review_date",
        ]
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(cases)
    with targets[2].open("w", encoding="utf-8-sig", newline="") as stream:
        columns = [
            "source_id", "section", "printed_page", "pdf_page", "table_row",
            "source_excerpt_display", "reviewed_applicability", "reviewed_cross_references",
            "clinician_comments", "reviewer_name", "review_date",
        ]
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(
            {
                "source_id": unit["source_id"],
                "section": unit["section"],
                "printed_page": unit["printed_page"],
                "pdf_page": unit["pdf_page"],
                "table_row": unit["table_row"],
                "source_excerpt_display": " ".join(unit["evidence_text"].split()),
            }
            for unit in catalogue["units"]
        )
    return manifest


def verify():
    manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
    if manifest["cases"] != inventory():
        raise ValueError("The sealed note inventory or a file fingerprint has changed")
    if manifest["catalogue_sha256"] != sha256(
        ROOT / "data/knowledge/processed/source_catalogue.json"
    ):
        raise ValueError("The sealed guideline catalogue fingerprint has changed")
    if manifest["rules_sha256"] != sha256(ROOT / "configs/rules/austroads_commercial_v1.yaml"):
        raise ValueError("The sealed rulebook fingerprint has changed")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    result = verify() if args.verify else create()
    print(f"{result['split']}: {len(result['cases'])} sealed notes; {result['status']}")


if __name__ == "__main__":
    main()
