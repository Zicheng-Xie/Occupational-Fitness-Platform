"""Publish a new report copy with a source-scope qualification and repair inputs.

Measured rankings and metrics remain byte-for-byte traceable to the parent.
The reviewed corpus is saved separately and has not been reranked by this tool.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from html import escape
from pathlib import Path

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.provenance import digest, write_json
from tools.report_retrieval_extensions import experiment_path, load_json, verify_files


def portable_audit_view(scope_audit, parent, html):
    """Rebase the display copy while keeping the original audit HTML pinned."""

    def replace(match):
        href = match.group(1)
        if "://" in href or href.startswith("#"):
            return match.group(0)
        path, separator, fragment = href.partition("#")
        target = (scope_audit / path).resolve()
        if target.is_relative_to(scope_audit):
            return match.group(0)
        if target == parent / "index.html":
            rebased = "../index.html"
        elif target.is_file() and file_hash(target) == file_hash(parent / "evidence_guide.pdf"):
            rebased = "../evidence_guide.pdf"
        else:
            raise ValueError("Audit viewer contains an unsupported external relative link: " + href)
        return 'href="' + rebased + (separator + fragment if separator else "") + '"'

    return re.sub(r'href="([^"]+)"', replace, html)


def build(root, parent, scope_audit, reviewed, output):
    root = Path(root).resolve()
    parent, scope_audit, reviewed, output = [
        experiment_path(root, p) for p in (parent, scope_audit, reviewed, output)
    ]
    if output.exists():
        raise ValueError("Scope qualification requires a fresh output directory")
    parent_pins = verify_files(parent)
    audit_pins = verify_files(scope_audit)
    reviewed_pins = verify_files(reviewed)
    parent_manifest, summary, corpus = [
        load_json(parent / name) for name in ("manifest.json", "summary.json", "corpus.json")
    ]
    if (
        digest(
            {k: v for k, v in parent_manifest.items() if k not in {"identity", "production_change"}}
        )
        != parent_manifest["identity"]
    ):
        raise ValueError("Parent report identity differs from its frozen contents")
    reviewed_corpus = load_json(reviewed / "corpus.json")
    before = {u["source_id"]: u for u in corpus["units"]}
    after = {u["source_id"]: u for u in reviewed_corpus["units"]}
    if not after or not set(after) < set(before):
        raise ValueError("Reviewed corpus must be a strict subset of the measured original sources")
    for sid, source in after.items():
        if (
            source["evidence_text"] != before[sid]["evidence_text"]
            or source["text_sha256"] != before[sid]["text_sha256"]
        ):
            raise ValueError("Source-scope qualification cannot silently rewrite original texts")
    excluded = sorted(set(before) - set(after))
    audit_findings = (
        load_json(scope_audit / "findings.json")
        if (scope_audit / "findings.json").is_file()
        else None
    )
    if audit_findings is not None:
        quarantined = set()
        for finding in audit_findings["findings"]:
            sid = finding["source_id"]
            if sid not in before or finding["text_sha256"] != before[sid]["text_sha256"]:
                raise ValueError("Scope audit does not match the measured original sources")
            if finding.get("recommendation", "").startswith("quarantine"):
                quarantined.add(sid)
        if quarantined != set(excluded):
            raise ValueError("Reviewed exclusions differ from the frozen scope recommendations")
    qualification = {
        "status": "measured_corpus_scope_qualification_required",
        "measured_original_units": len(before),
        "reviewed_original_units": len(after),
        "excluded_source_ids": excluded,
        "scope_finding": "The measured corpus contains private-standard, mixed-scope or incomplete flowchart units despite commercial/shared metadata. Metadata filtering did not verify commercial-only textual content.",
        "metric_interpretation": "All recorded scores remain fixed-corpus engineering reference-source coverage. They are neither corrected-corpus scores nor clinical accuracy.",
        "reviewed_corpus_rerun_complete": False,
        "review_status": "Engineering scope quarantine; clinical source review remains pending",
        "remaining_units_certified": False,
        "next_step": "Freeze the reviewed corpus, rebuild every method on those same sources, and rerun all methods and judgment comparisons before making a corrected-scope performance claim.",
        "no_model_calls": True,
        "production_change": False,
    }
    if audit_findings is not None:
        audit_summary = {
            k: audit_findings[k]
            for k in (
                "status",
                "corpus_units",
                "quarantine_recommended_count",
                "clinical_review_status",
                "scope_boundary",
            )
            if k in audit_findings
        }
    elif (scope_audit / "summary.json").is_file():
        audit_summary = load_json(scope_audit / "summary.json")
    else:
        audit_summary = {"audit_artifacts": sorted(audit_pins)}
    html = (parent / "index.html").read_text(encoding="utf-8")
    marker = "<h1>Ten independent retrieval routes</h1>"
    if html.count(marker) != 1:
        raise ValueError("Parent report has an unexpected qualification insertion point")
    notice = (
        '<aside role="note" style="border:2px solid #b98124;background:#fff8e9;padding:20px;margin:20px 0;border-radius:6px">'
        "<h2>Source-scope qualification</h2><p><strong>The following comparison used the frozen "
        + str(len(before))
        + "-unit corpus. Commercial/shared metadata did not establish commercial-only textual purity.</strong> A later source audit found private-standard, mixed-scope or incomplete flowchart units. The measured rankings and scores below are preserved; they have not been recomputed on the reviewed corpus.</p><p>The separate reviewed corpus contains "
        + str(len(after))
        + " retained original units after "
        + str(len(excluded))
        + " engineering scope exclusions. The remaining units have not been certified as scope-pure, and clinical source review remains pending. Every method must be rebuilt and rerun on this shared scope-reviewed corpus. These fixed-corpus source-coverage scores do not establish clinical fitness-judgment accuracy.</p>"
        + '<p><a href="scope_qualification.json">Qualification and excluded source IDs</a> · <a href="scope_audit/'
        + ("qualified_index.html" if (scope_audit / "index.html").is_file() else "artifacts.json")
        + '">Frozen source-scope audit</a> · <a href="scope_reviewed_corpus/corpus.json">Separate reviewed corpus (not reranked)</a></p>'
        + "<details><summary>Audit summary and next steps</summary><pre>"
        + escape(
            json.dumps({"qualification": qualification, "scope_audit": audit_summary}, indent=2)
        )
        + "</pre></details></aside>"
    )
    output.mkdir(parents=True)
    for file in parent.iterdir():
        if not file.is_file() or file.name in {
            "index.html",
            "manifest.json",
            "artifacts.json",
            "summary.json",
        }:
            continue
        name = "parent_reporter_source.py" if file.name == "reporter_source.py" else file.name
        shutil.copyfile(file, output / name)
    (output / "index.html").write_text(html.replace(marker, marker + notice), encoding="utf-8")
    write_json(output / "summary.json", {**summary, "source_scope_qualification": qualification})
    write_json(output / "scope_qualification.json", qualification)
    for source, name in (
        (parent / "manifest.json", "parent_report_manifest.json"),
        (parent / "artifacts.json", "parent_report_artifacts.json"),
    ):
        shutil.copyfile(source, output / name)
    shutil.copytree(scope_audit, output / "scope_audit")
    shutil.copytree(reviewed, output / "scope_reviewed_corpus")
    if (scope_audit / "index.html").is_file():
        original_audit_html = (scope_audit / "index.html").read_text(encoding="utf-8")
        (output / "scope_audit/qualified_index.html").write_text(
            portable_audit_view(scope_audit, parent, original_audit_html), encoding="utf-8"
        )
    (output / "qualifier_source.py").write_bytes(Path(__file__).read_bytes())
    data = {
        "kind": "source_scope_qualified_frozen_retrieval_report",
        "parent_report_identity": parent_manifest["identity"],
        "parent_report_artifacts": parent_pins,
        "scope_audit_artifacts": audit_pins,
        "reviewed_corpus_artifacts": reviewed_pins,
        "qualification": qualification,
        "qualifier_sha256": file_hash(__file__),
        "model_calls": 0,
        "original_audit_html_unchanged": True,
        "portable_audit_view": (
            "scope_audit/qualified_index.html" if (scope_audit / "index.html").is_file() else None
        ),
    }
    write_json(
        output / "manifest.json", {**data, "identity": digest(data), "production_change": False}
    )
    if (
        verify_files(parent) != parent_pins
        or verify_files(scope_audit) != audit_pins
        or verify_files(reviewed) != reviewed_pins
    ):
        raise ValueError("A frozen qualification input changed")
    if load_json(output / "summary.json")["main_metrics"] != summary["main_metrics"]:
        raise ValueError("Qualification changed the measured retrieval metrics")
    if file_hash(output / "rankings.jsonl") != file_hash(parent / "rankings.jsonl"):
        raise ValueError("Qualification changed the measured rankings")
    write_json(
        output / "artifacts.json",
        {
            p.relative_to(output).as_posix(): file_hash(p)
            for p in output.rglob("*")
            if p.is_file() and p != output / "artifacts.json"
        },
    )
    return {"identity": digest(data), **qualification}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--scope-audit", type=Path, required=True)
    parser.add_argument("--reviewed", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            build(Path.cwd(), args.parent, args.scope_audit, args.reviewed, args.output), indent=2
        )
    )
