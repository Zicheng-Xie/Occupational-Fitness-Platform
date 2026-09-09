"""Verify the pinned synthetic report collection without invoking model services."""

import json
from pathlib import Path

from occupational_fitness_rag.pipeline.workflow import OccupationalFitnessWorkflow

ROOT = Path(__file__).resolve().parents[1]


def main():
    base = ROOT / "outputs/demo"
    entries = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    expected = {f"SYN-M2-{n:03}" for n in range(1, 11)} | {f"SYN-EXT-{n:03}" for n in range(1, 21)}
    if len(entries) != 30 or {e["case_id"] for e in entries} != expected:
        raise ValueError("The fixed collection must contain the 30 selected synthetic cases")
    workflow = OccupationalFitnessWorkflow(ROOT / "configs/workflow.offline.yaml")
    files = 0
    for entry in entries:
        output = (ROOT / entry["output"]).resolve()
        if not output.is_relative_to(base) or output.parent.name != entry["case_id"]:
            raise ValueError("Snapshot path outside its expected case directory")
        verification = workflow.verify_run(output)
        result = json.loads((output / "rule_result.json").read_text(encoding="utf-8"))
        if verification["case_id"] != entry["case_id"] or any(
            entry[key] != result[key] for key in ("assessment_outcome", "route")
        ):
            raise ValueError("Directory metadata differs from saved assessment")
        files += verification["files"] + 1
    print(
        f"Verified {len(entries)} fixed synthetic reports and {files} bundle files; no model calls"
    )


if __name__ == "__main__":
    main()
