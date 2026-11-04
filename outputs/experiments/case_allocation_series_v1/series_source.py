"""Execute the frozen full comparison in serial resumable actual-call batches.

The mechanism pilot is a separate completed experiment. Every one of the990
full conditions makes its own actual call; pilot observations are not imported.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.provenance import digest, write_json
from tools import run_frozen_retrieval_judgments as actor
from tools.report_case_allocation_judgments import build

PREPARATION = "outputs/experiments/case_allocation_judgment_preparation_v1"
PILOT = "outputs/experiments/case_allocation_judgment_pilot_v1"
OUTPUT = "outputs/experiments/case_allocation_judgment_full_v1"
SERIES = "outputs/experiments/case_allocation_series_v1"
REPORT = "outputs/experiments/case_allocation_judgment_comparison_v1"


def validate_pilot(root):
    path = root / PILOT
    actor.verify_files(path)
    summary = json.loads((path / "summary.json").read_bytes())
    plan = json.loads((path / "plan.json").read_bytes())
    rows = actor.read_records(path / "results.jsonl")
    if (
        not summary["complete"]
        or summary["planned"] != 150
        or len(rows) != 150
        or {actor.key(r) for r in rows} != {actor.key(c) for c in plan["conditions"]}
    ):
        raise ValueError(
            "Finish and retain the five-case mechanism pilot before the full comparison"
        )
    return file_hash(path / "artifacts.json")


def run(root, batch_size=60, resume=False):
    root = Path(root).resolve()
    if type(batch_size) is not int or batch_size <= 0:
        raise ValueError("Batch size must be positive")
    config, manifest, pins, _, _, _, conditions = actor.prepare_inputs(root / PREPARATION)
    if len(conditions) != 990 or len({c["case_id"] for c in conditions}) != 33:
        raise ValueError("The full protocol requires exactly990 conditions across33 cases")
    pilot_pin = validate_pilot(root)
    sources = [
        Path(__file__),
        Path(actor.__file__),
        root / "tools/report_case_allocation_judgments.py",
    ]
    data = {
        "preparation_identity": manifest["identity"],
        "preparation_artifacts": pins,
        "pilot_artifacts_sha256": pilot_pin,
        "batch_size": batch_size,
        "sources": {str(p.relative_to(root)): file_hash(p) for p in sources},
        "planned_actual_full_calls": 990,
        "pilot_calls_imported": 0,
        "models_serial": config["models"],
        "production_change": False,
    }
    plan = {**data, "identity": digest(data)}
    directory = root / SERIES
    directory.mkdir(exist_ok=True, parents=True)
    lock = directory / ".run.lock"
    with lock.open("x", encoding="ascii") as stream:
        stream.write(str(os.getpid()))
    try:
        plan_path = directory / "plan.json"
        if plan_path.exists():
            if not resume or json.loads(plan_path.read_bytes()) != plan:
                raise ValueError("Resume requires the identical serial plan")
        elif any(p.name != ".run.lock" for p in directory.iterdir()):
            raise ValueError("Preserve unowned series files")
        else:
            write_json(plan_path, plan)
        if (directory / "artifacts.json").exists():
            actor.verify_files(directory)
            actor.verify_files(root / OUTPUT)
            actor.verify_files(root / REPORT)
            return json.loads((root / REPORT / "summary.json").read_bytes())
        while True:
            foreign = [
                p
                for p in (root / "outputs/experiments").glob("*/.run.lock")
                if p.parent not in {directory, root / OUTPUT}
            ]
            if foreign:
                raise ValueError("Another experiment owns an inference lock: " + str(foreign))
            if actor.verify_files(root / PREPARATION) != pins or any(
                file_hash(p) != data["sources"][str(p.relative_to(root))] for p in sources
            ):
                raise ValueError("Frozen serial source or preparation changed")
            write_json(
                directory / "status.json",
                {
                    "stage": "running",
                    "identity": plan["identity"],
                    "updated_utc": datetime.now(timezone.utc).isoformat(),
                    "planned": 990,
                    "recorded_at_batch_start": len(
                        actor.read_records(root / OUTPUT / "results.jsonl")
                    ),
                    "production_change": False,
                },
            )
            result = actor.run(
                root / PREPARATION,
                root / OUTPUT,
                resume=(root / OUTPUT / "plan.json").exists(),
                max_new_calls=batch_size,
            )
            write_json(
                directory / "status.json",
                {
                    "stage": "judgment_complete" if result["complete"] else "checkpoint",
                    "identity": plan["identity"],
                    "planned": result["planned"],
                    "recorded": result["recorded"],
                    "failed": result["failed"],
                    "updated_utc": datetime.now(timezone.utc).isoformat(),
                    "production_change": False,
                },
            )
            print(
                json.dumps({k: result[k] for k in ("planned", "recorded", "failed", "complete")}),
                flush=True,
            )
            if result["complete"]:
                if (root / REPORT).exists():
                    actor.verify_files(root / REPORT)
                    report_manifest = json.loads((root / REPORT / "manifest.json").read_bytes())
                    actual_plan = json.loads((root / OUTPUT / "plan.json").read_bytes())
                    if report_manifest["run_identity"] != actual_plan["identity"]:
                        raise ValueError("Existing final report belongs to another actual run")
                    report = json.loads((root / REPORT / "summary.json").read_bytes())
                else:
                    report = build(root, root / PREPARATION, root / OUTPUT, root / REPORT)
                write_json(
                    directory / "status.json",
                    {
                        "stage": "complete",
                        "planned": 990,
                        "recorded": 990,
                        "failed": report["failure_count"],
                        "report": REPORT,
                        "production_change": False,
                    },
                )
                write_json(
                    directory / "artifacts.json",
                    {
                        p.name: file_hash(p)
                        for p in directory.iterdir()
                        if p.is_file() and p.name not in {"artifacts.json", ".run.lock"}
                    },
                )
                return report
    except Exception as exc:
        write_json(
            directory / "failure.json",
            {
                "error": f"{type(exc).__name__}: {exc}",
                "updated_utc": datetime.now(timezone.utc).isoformat(),
            },
        )
        raise
    finally:
        lock.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    run(Path.cwd(), resume=args.resume)
