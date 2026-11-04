"""Export review snapshots while the exclusive model worker remains running."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

from tools.complex_ten_contract import pin, read, write_json
from tools.serve_retrieval_judgments import (
    DEFAULT,
    REPORTS,
    compatible_records,
    dataset,
    export,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    manifest = read(DEFAULT / "manifest.json")
    from tools.complex_ten_contract import digest

    identity = digest(manifest["implementation"])
    records = [read(p) for p in sorted((DEFAULT / "records").glob("*.json"))]
    service = SimpleNamespace(reports=REPORTS, records=lambda: records,
                              implementation_identity=identity,
                              datasets={name: dataset(path) for name, path in REPORTS.items()})
    export(service, args.destination)
    current = compatible_records(records)
    (args.destination / "judgments.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in current), encoding="utf-8")
    columns = ["case_id", "module", "method", "top_k", "model", "evidence_mode",
               "status", "fitness", "outcome", "seconds", "supplied_originals", "warnings", "error", "id"]
    with (args.destination / "judgments.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for r in current:
            result = r.get("result", {})
            writer.writerow({"case_id": r["case_id"], "module": r["module"],
                **{key: r["condition"][key] for key in ("method", "top_k", "model", "evidence_mode")},
                "status": r["status"], "fitness": result.get("fitness"),
                "outcome": result.get("outcome"), "seconds": r.get("seconds"),
                "supplied_originals": len(r["payload"]["guideline_evidence"]),
                "warnings": "; ".join(result.get("validation_warnings", [])),
                "error": r.get("error"), "id": r["id"]})
    for name in REPORTS:
        path = args.destination / name / "index.html"
        html = path.read_text(encoding="utf-8")
        html = html.replace('href="/refinement/index.html', 'href="../refinement/index.html')
        html = html.replace('href="/ten-methods/index.html', 'href="../ten-methods/index.html')
        path.write_text(html, encoding="utf-8")
    (args.destination / "index.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta http-equiv="refresh" content="0;url=refinement/index.html#local-model-review">'
        '<title>Occupational Fitness Platform</title><p>'
        '<a href="refinement/index.html#local-model-review">Retrieval and local-model assessment</a>'
        '</p></html>', encoding="utf-8")
    write_json(args.destination / "snapshot_summary.json", {
        "records": len(current), "status": dict(Counter(r["status"] for r in current)),
        "historical_records_preserved": len(records) - len(current),
        "clinical_review_status": "pending", "accuracy_claim": False,
        "live_url": "http://127.0.0.1:8781/refinement/index.html#local-model-review",
    })
    for name in ("integration_matrix.json", "integration_summary.json",
                 "token_budget_audit.json", "pilot_reference_audit.json",
                 "display_fix_validation.json"):
        if (DEFAULT / name).exists():
            shutil.copy2(DEFAULT / name, args.destination / name)
    for name in (
        *manifest["implementation"], "tools/validate_retrieval_review.py",
        "tools/audit_retrieval_judgment_pilot.py", "tools/export_retrieval_judgments.py",
        "examples/retrieval_judgment_client.py", "scripts/start_retrieval_review.ps1",
        "tests/test_retrieval_judgment.py", "docs/retrieval_model_judgment.md",
        "tests/retrieval_judgment_client.test.cjs",
        "tools/validate_review_citation_repair.py",
    ):
        source = Path(__file__).resolve().parents[1] / name
        target = args.destination / "implementation" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    study = Path(__file__).resolve().parents[1] / "outputs/experiments/review_citation_repair_20261104"
    if study.exists():
        shutil.copytree(study, args.destination / "citation_repair_validation", dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("owner.lock"))
    (args.destination / "README.md").write_text(
        "# Retrieval and local-model assessment\n\n"
        "Open index.html for the preserved refinement interface with saved model reviews.\n"
        "Open ten-methods/index.html for the ten-method evidence comparison.\n\n"
        "For new calls run scripts/start_retrieval_review.ps1 in the project and open "
        "http://127.0.0.1:8781/refinement/index.html#local-model-review.\n"
        "The local service automatically reviews the selected case, evidence and model.\n\n"
        "Saved proposals are engineering experiments. Completed means contract validation, "
        "not clinical accuracy. Requires-review warnings and failures remain visible.\n"
        "A file URL displays saved records but cannot execute a model.\n\n"
        "See integration_summary.json for the planned matrix and final status counts. "
        "See pilot_reference_audit.json for every case-level disagreement with legacy "
        "engineering labels. Contract-valid results can still be wrong; these checks "
        "do not establish clinical accuracy or justify a production replacement.\n",
        encoding="utf-8")
    # This final manifest covers the fully rewritten offline snapshot.
    write_json(args.destination / "delivery_manifest.json", {
        "source_manifest": manifest,
        "files": {p.relative_to(args.destination).as_posix(): pin(p)
                  for p in args.destination.rglob("*") if p.is_file()
                  and p.name not in {"delivery_manifest.json", "manifest.json"}},
    })
    print(json.dumps({"destination": str(args.destination), "records": len(current),
                      "status": dict(Counter(r["status"] for r in current))}, indent=2))


if __name__ == "__main__":
    main()
