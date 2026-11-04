"""Deliver complete long-note evidence with separate portable presentation views."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from pathlib import Path

from occupational_fitness_rag.provenance import sha256_bytes, write_json

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_bytes())


def portable_html(text, path, root):
    def href(match):
        prefix, quote, value = match.groups()
        raw, mark, fragment = value.partition("#")
        if raw.endswith("ap_g56_22.pdf"):
            value = Path(os.path.relpath(root / "evidence_guide.pdf", path.parent)).as_posix() + (
                mark + fragment if mark else ""
            )
        elif raw.endswith("index.html") and not (path.parent / raw).resolve().is_relative_to(root):
            value = Path(os.path.relpath(root / "index.html", path.parent)).as_posix() + (
                mark + fragment if mark else ""
            )
        return prefix + quote + value + quote

    return re.sub(r"""((?:href|src)=)(["'])(.*?)\2""", href, text)


def export(source, audit, destination):
    source, audit, destination = [Path(p).resolve() for p in (source, audit, destination)]
    summary = read(source / "summary.json")
    check = read(audit / "summary.json")
    if not summary["complete"] or not all(check["checks"].values()):
        raise ValueError("Publish only a complete, audited comparison")
    if destination.exists():
        raise ValueError("Preserve the previous delivered evidence")
    # Buffer/verify source inventories before creating the requested destination.
    for folder in (source, audit):
        pins = read(folder / "artifacts.json")
        for name, pin in pins.items():
            assert sha256_bytes((folder / name).read_bytes()) == pin, (folder, name)
    source_files = {
        p.relative_to(source).as_posix(): sha256_bytes(p.read_bytes())
        for p in source.rglob("*")
        if p.is_file() and p.name != ".run.lock"
    }
    destination.mkdir(parents=True)
    for name, pin in source_files.items():
        target = destination / ("source_artifacts.json" if name == "artifacts.json" else name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target)
        assert sha256_bytes(target.read_bytes()) == pin
    shutil.copytree(audit, destination / "audit")
    implementation = [
        "tools/build_complex_long_cases.py",
        "tools/run_complex_long_study.py",
        "tools/audit_complex_long_study.py",
        "tools/export_complex_long_report.py",
        "src/occupational_fitness_rag/evaluation/long_note_study.py",
        "configs/experiments/complex_long_200.yaml",
        "docs/complex_long_200_evaluation.md",
        "tests/test_complex_long_study.py",
        "data/cases/complex_nurse_notes/README.md",
        "data/cases/complex_nurse_notes/long_200_manifest.json",
        "data/cases/complex_nurse_notes/long_200_input_inventory.csv",
    ]
    for name in implementation:
        target = destination / "implementation" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    presentation = []
    for path in destination.glob("runs/*/*/draft_report.html"):
        target = path.with_name("draft_report.portable.html")
        target.write_text(
            portable_html(path.read_text(encoding="utf-8"), target, destination), encoding="utf-8"
        )
        presentation.append(target.relative_to(destination).as_posix())
    index = (destination / "index.html").read_text(encoding="utf-8")
    # Preserve the exact original main view as well as each ordinary bundle view.
    (destination / "index.source.html").write_bytes((destination / "index.html").read_bytes())
    index = index.replace("/draft_report.html", "/draft_report.portable.html")
    index = index.replace(
        '<select id="case">', '<select id="case"><option value="">All cases</option>', 1
    )
    index = index.replace(
        "<option>CX-LONG-001</option>", "<option selected>CX-LONG-001</option>", 1
    )
    extra_script = """<script>document.getElementById('module').addEventListener('change',()=>{document.getElementById('case').value='';filter()});document.getElementById('status').addEventListener('change',()=>{document.getElementById('case').value='';filter()});document.getElementById('case').addEventListener('change',()=>{document.getElementById('module').value='';document.getElementById('status').value='';filter()});</script>"""
    index = index.replace("</html>", extra_script + "</html>")
    banner = f"""<section><h2>Completed evaluation and independent checks</h2><p><a href="audit/index.html">Open the audit and intake-isolation analysis</a> · <a href="implementation/data/cases/complex_nurse_notes/long_200_input_inventory.csv">Input inventory and module selection</a></p><p>Always-insufficient baseline agreement: {check["always_insufficient_baseline_agreement"]:.1%}. Authored reference facts supplied directly to unchanged rules: {check["authored_fact_diagnostic_metrics"]["engineering_reference_agreement_all_recorded"]:.1%}; this diagnostic is not automatic extraction or an achieved system improvement.</p><p>Original notes are in <code>notes/</code>. Original JSON and ordinary assessment HTML are retained; linked portable HTML copies rebase guideline links for this delivery. <a href="delivery_manifest.json">Delivery provenance</a>.</p></section>"""
    index = index.replace(
        "<h1>200 complex long-form nurse notes</h1>",
        "<h1>200 complex long-form nurse notes</h1>" + banner,
        1,
    )
    (destination / "index.html").write_text(index, encoding="utf-8")
    readme = """# Complex long-note evaluation delivery

Open index.html for the complete English report and audit/index.html for
independent result checks. notes/ contains the 200 uploadable UTF-8 TXT files.
Use the listed modules in implementation/data/cases/complex_nurse_notes/
long_200_input_inventory.csv. Labels, manifests and CSV files are not inputs.

Engineering reference agreement is not clinical accuracy. The cohort comprises
40 authored families and five correlated variants per family, not 200 independent
patients. The unchanged ordinary platform and the separate experimental model
judgments are reported independently. All failures remain recorded.

Every original case bundle remains byte-identical to the source, including its
run_manifest.json and draft_report.html. Additional draft_report.portable.html
files only rebase links for this delivery. index.source.html preserves the exact
source overview. source_artifacts.json describes that source overview and its
raw evidence; delivery_manifest.json describes this portable delivery.

The authored-fact diagnostic bypasses automatic extraction deliberately and
makes no claim of an improved production system. Human review of source
applicability, reference labels and explanation support remains pending.
"""
    (destination / "README.md").write_text(readme, encoding="utf-8")
    missing = []
    pattern = re.compile(r"""(?:href|src)=["']([^"']+)["']""")
    views = [
        destination / "index.html",
        destination / "audit/index.html",
        *[destination / p for p in presentation],
    ]
    checked = 0
    for path in views:
        for value in pattern.findall(path.read_text(encoding="utf-8")):
            if value.startswith(("#", "http:", "https:", "data:", "javascript:")):
                continue
            raw = value.split("#")[0]
            checked += 1
            target = (path.parent / raw).resolve()
            if not target.is_relative_to(destination) or not target.exists():
                missing.append({"view": path.relative_to(destination).as_posix(), "target": value})
    # delivery_manifest.json is about to be written; all other links must exist.
    missing = [m for m in missing if m["target"] != "delivery_manifest.json"]
    if missing:
        write_json(destination / "missing_links.json", missing)
        raise ValueError("Portable presentation links are unresolved")
    files = {
        p.relative_to(destination).as_posix(): sha256_bytes(p.read_bytes())
        for p in destination.rglob("*")
        if p.is_file()
    }
    receipt = {
        "source_experiment_identity": summary["experiment_identity"],
        "source_files_sha256": source_files,
        "delivered_files_sha256": files,
        "portable_presentations": presentation,
        "local_links_checked": checked,
        "missing_local_links": [],
        "authoritative_case_json_modified": False,
        "original_bundle_html_modified": False,
        "clinical_accuracy": None,
        "production_change": False,
    }
    write_json(destination / "delivery_manifest.json", receipt)
    return {
        "destination": str(destination),
        "delivered_files": len(files) + 1,
        "portable_case_reports": len(presentation),
        "local_links_checked": checked,
        "source_complete": True,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", default="outputs/evaluation/complex_long_200_20261027")
    p.add_argument("--audit", default="outputs/evaluation/complex_long_200_audit_20261027")
    p.add_argument("--destination", required=True)
    a = p.parse_args()
    print(json.dumps(export(a.source, a.audit, a.destination), indent=2))
