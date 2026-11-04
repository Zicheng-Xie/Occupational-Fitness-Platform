"""Export audited ten-route results without copying third-party code or model indexes."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from urllib.parse import unquote

from tools.complex_ten_contract import DEFAULT, ROOT, pin, read, write_json


def export(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    summary = read(source / "comparison/summary.json")
    audit = read(source / "comparison/audit.json")
    if not read(source / "native_integrity.json")["all_passed"]:
        raise ValueError("Native index and input integrity checks must pass")
    if not summary["complete"] or not audit["complete"] or summary["recorded_conditions"] != 3570:
        raise ValueError("Deliver the complete 234-case ten-method experiment")
    if destination.exists():
        raise ValueError("Preserve an existing delivery")
    for name, expected in read(source / "comparison/artifacts.json").items():
        if pin(source / "comparison" / name) != expected:
            raise ValueError("Audited report changed")
    source_files = {}
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        name = path.relative_to(source)
        # Keep original responses, requests, source mappings and actual input
        # snapshots. The copied runtime indexes and caches are reproducible
        # dependencies, not presentation material or third-party source.
        if "indexes" in name.parts or path.name.endswith(".lock"):
            continue
        source_files[name.as_posix()] = pin(path)
    destination.mkdir(parents=True)
    for name, expected in source_files.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target)
        if pin(target) != expected:
            raise ValueError("Copied experiment differs")
    implementation = [
        "tools/complex_ten_inputs.py",
        "tools/complex_ten_contract.py",
        "tools/run_complex_ten_methods.py",
        "tools/complex_native_worker.py",
        "tools/recover_complex_ten_adapters.py",
        "tools/report_complex_ten_methods.py",
        "tools/export_complex_ten_methods.py",
        "tools/audit_complex_ten_native.py",
        "tools/rerun_complex_lightrag_serial.py",
        "tests/test_complex_ten_methods.py",
        "docs/complex_234_ten_method_study.md",
    ]
    for name in implementation:
        target = destination / "implementation" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    (destination / "index.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=comparison/index.html"><title>234 cases · Ten-method comparison</title><a href="comparison/index.html">Open the complete ten-method retrieval comparison</a></html>',
        encoding="utf-8",
    )
    (destination / "README.md").write_text(
        """# 234-case ten-method retrieval comparison

Open index.html, or comparison/index.html directly. The report is self-contained
and supports cohort, disease, case, method and result filtering. Original PDF
links use the bundled guideline. notes/ contains all 234 uploadable TXT files.

All ten strategies search the same frozen 88-original commercial/shared corpus.
There are 357 requested module scopes, 3,570 final ranking conditions, 222 cases
with source labels and 273 source-labelled scopes. The remaining inputs/scopes
are retained but are not assigned invented recall labels. Source coverage is not
clinical accuracy, full clinical relevance or an evidence-supported decision.
This experiment makes no new fitness-judgment calls.

local_rankings.jsonl retains 714 initial integration failures. adapter_repair/
records their corrected adapter execution separately, with matching inputs and
the already recorded actual embeddings. comparison/ selects those corrected
records with explicit lineage. workers/ retains real native framework results,
model requests/responses and cost logs. Copied native indexes and downloaded
model weights are excluded from this report delivery; they remain in the
project workspace. No third-party source repository is copied.

implementation/ contains this experiment's first-party scripts, tests and
English methodology. delivery_manifest.json binds all delivered file bytes.
""",
        encoding="utf-8",
    )
    missing = []
    views = [destination / "index.html", destination / "comparison/index.html"]
    checked = 0
    for path in views:
        for raw in re.findall(r"\bhref=[\'\"]([^\'\"]+)", path.read_text(encoding="utf-8")):
            if raw.startswith(("#", "http:", "https:", "javascript:", "data:")) or "${" in raw:
                continue
            candidate = (path.parent / unquote(raw.split("#")[0])).resolve()
            checked += 1
            if not candidate.is_relative_to(destination) or not candidate.exists():
                missing.append({"view": path.relative_to(destination).as_posix(), "target": raw})
    if missing:
        write_json(destination / "missing_links.json", missing)
        raise ValueError("A report evidence link does not resolve")
    files = {
        p.relative_to(destination).as_posix(): pin(p) for p in destination.rglob("*") if p.is_file()
    }
    write_json(
        destination / "delivery_manifest.json",
        {
            "experiment_identity": summary["experiment_identity"],
            "source_files_sha256": source_files,
            "delivered_files_sha256": files,
            "static_report_links_checked": checked,
            "missing_links": missing,
            "native_index_and_model_weights_copied": False,
            "clinical_accuracy": None,
        },
    )
    print(
        json.dumps(
            {
                "destination": str(destination),
                "delivered_files": len(files) + 1,
                "checked_static_links": checked,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    export(args.source, args.destination)
