"""Verify generated demo bundles and publish a local report index and current examples."""

import json
from collections import Counter
from pathlib import Path
from shutil import copyfile

from occupational_fitness_rag.pipeline.workflow import OccupationalFitnessWorkflow
from occupational_fitness_rag.provenance import write_json
from occupational_fitness_rag.reporting.builder import LABELS
from occupational_fitness_rag.reporting.presentation import render_library

ROOT = Path(__file__).resolve().parents[1]


def main():
    workflow = OccupationalFitnessWorkflow(ROOT / "configs/workflow.offline.yaml")
    manifest_path = ROOT / "outputs/demo/manifest.json"
    if not manifest_path.exists():
        manifest_path = ROOT / "outputs/demo_manifest.json"
    runs = json.loads(manifest_path.read_text(encoding="utf-8"))
    if len(runs) != 30 or len({r["case_id"] for r in runs}) != 30:
        raise ValueError("Expected ten supplied and twenty added cases")
    records, entries, links = [], [], []
    for run in runs:
        path = (ROOT / run["output"]).resolve()
        check = workflow.verify_run(path)
        relative = path.relative_to(ROOT / "outputs").as_posix()
        label = LABELS[run["assessment_outcome"]]
        source = (
            "Supplied synthetic input"
            if run["case_id"].startswith("SYN-M2")
            else "Extension synthetic input"
        )
        result = json.loads((path / "rule_result.json").read_text(encoding="utf-8"))
        entries.append(
            {
                **run,
                "relative": relative,
                "missing_count": len(
                    {field for module in result["modules"] for field in module["missing_fields"]}
                ),
            }
        )
        links.append(f"| [{run['case_id']}]({relative}/draft_report.html) | {source} | {label} |")
        records.append({**check, "run_directory": path.relative_to(ROOT).as_posix()})
        if run["case_id"] == "SYN-M2-009":
            target = ROOT / "examples/contracts/syn_m2_009"
            target.mkdir(parents=True, exist_ok=True)
            for filename in (
                "structured_case.json",
                "rule_result.json",
                "evidence_pack.json",
                "gp_review_note.json",
            ):
                copyfile(path / filename, target / filename)
            write_json(
                target / "example_manifest.json",
                {
                    "generated_from": path.relative_to(ROOT).as_posix(),
                    "case_id": run["case_id"],
                    "schema_version": "1.2.0",
                    "note": "Exact copies of verified generated JSON artifacts. Original nurse note lacks audiometry frequencies; no hearing threshold breach is inferred from dB alone.",
                },
            )
    write_json(
        ROOT / "outputs/evaluation/run_verification.json",
        {
            "runs": len(records),
            "verified": len(records),
            "clinical_validation": False,
            "outcomes": dict(Counter(r["assessment_outcome"] for r in runs)),
            "records": records,
        },
    )
    page = render_library(entries)
    (ROOT / "outputs/index.html").write_text(page, encoding="utf-8")
    (ROOT / "outputs/README.md").write_text(
        "# Verified assessment reports\n\nOpen [assessment records](index.html). All reports are assessment drafts pending clinical sign-off.\n\n| Assessment report | Input source | Provisional outcome |\n|---|---|---|\n"
        + "\n".join(links)
        + "\n",
        encoding="utf-8",
    )
    print(f"Verified {len(records)} runs; generated outputs/index.html and SYN-M2-009 contracts")


if __name__ == "__main__":
    main()
