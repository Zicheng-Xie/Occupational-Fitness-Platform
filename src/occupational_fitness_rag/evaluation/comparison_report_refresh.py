"""Refresh an existing local Data report while the experiment records results."""

import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path

from occupational_fitness_rag.evaluation.comparison_analysis import export_analysis
from occupational_fitness_rag.evaluation.comparison_snapshot import update_snapshot


def refresh(output: Path, app: Path, node: Path, builder: Path, delivery: Path | None = None):
    checkpoint = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    export_analysis(output, checkpoint)
    update_snapshot(output, app / "src/data.json", checkpoint)
    subprocess.run(
        [str(node), str(builder), "build", "--project-dir", str(app), "--separate-data"],
        check=True,
        capture_output=True,
        text=True,
    )
    exported = app / ".data-app-offline/exports/judgment_report.html"
    subprocess.run(
        [
            str(node),
            str(builder),
            "export-offline",
            "--project-dir",
            str(app),
            "--output",
            str(exported),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    shutil.copyfile(exported, output / "interactive_report.html")
    if delivery:
        delivery.mkdir(parents=True, exist_ok=True)
        for artifact in output.iterdir():
            if artifact.is_file() and artifact.suffix in {".html", ".json", ".jsonl", ".csv"}:
                shutil.copyfile(artifact, delivery / artifact.name)
    return checkpoint


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["output", "app", "node", "builder"]:
        parser.add_argument(name, type=Path)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--delivery", type=Path)
    args = parser.parse_args()
    previous = None
    while True:
        summary_path = args.output / "summary.json"
        stamp = summary_path.stat().st_mtime_ns
        if stamp != previous:
            summary = refresh(args.output, args.app, args.node, args.builder, args.delivery)
            previous = stamp
            print(f"Report refreshed: {summary.get('recorded_runs', 0)} calls", flush=True)
            if summary.get("execution_status") == "completed":
                break
        if not args.watch:
            break
        time.sleep(30)
