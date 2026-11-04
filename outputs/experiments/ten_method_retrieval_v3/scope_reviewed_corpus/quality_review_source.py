"""Quarantine reviewed layout failures in a new, independently fingerprinted corpus."""

import json
from copy import deepcopy
from html import escape
from pathlib import Path

from occupational_fitness_rag.evaluation.comparison_corpus import verify_corpus
from occupational_fitness_rag.provenance import digest, write_json


def apply_quality_review(corpus, review):
    """Apply pinned engineering exclusions, never reconstruct missing figure meaning."""
    if (
        digest({key: value for key, value in corpus.items() if key != "corpus_sha256"})
        != corpus["corpus_sha256"]
    ):
        raise ValueError("Original corpus fingerprint changed")
    if (
        corpus["corpus_sha256"] != review["base_corpus_sha256"]
        or corpus["document_sha256"] != review["document_sha256"]
    ):
        raise ValueError("Quality review does not match this corpus and source document")
    units = {unit["source_id"]: unit for unit in corpus["units"]}
    if len(units) != len(corpus["units"]):
        raise ValueError("Duplicate source ID in original corpus")
    entries = review["exclusions"]
    excluded = {entry["source_id"] for entry in entries}
    if not entries or len(excluded) != len(entries) or excluded - units.keys():
        raise ValueError("Missing, duplicate or unknown reviewed source exclusion")
    protected = set(review["protected_source_ids"])
    if not protected <= units.keys() or excluded & protected:
        raise ValueError("Reviewed exclusion would remove a protected canonical source")
    for entry in entries:
        unit = units[entry["source_id"]]
        if digest(unit) != entry["unit_sha256"]:
            raise ValueError("Reviewed source text or region metadata changed")
        if entry.get("engineering_review_status") != "verified_layout_failure" or not entry.get(
            "reason"
        ):
            raise ValueError("A reviewed exclusion requires an explicit engineering finding")
    revised = deepcopy(corpus)
    revised.pop("corpus_sha256")
    revised["units"] = [unit for unit in revised["units"] if unit["source_id"] not in excluded]
    removed_edges = []
    for unit in revised["units"]:
        targets = [sid for sid in unit["cross_references"] if sid in excluded]
        if targets:
            removed_edges.extend({"from": unit["source_id"], "to": sid} for sid in targets)
            unit["cross_references"] = [
                sid for sid in unit["cross_references"] if sid not in excluded
            ]
            unit["quarantined_cross_reference_targets"] = targets
    revised["exclusions"] = [*revised["exclusions"], *deepcopy(entries)]
    revised["quality_review"] = {
        "review_sha256": digest(review),
        "base_corpus_sha256": corpus["corpus_sha256"],
        "excluded_source_ids": sorted(excluded),
        "protected_source_ids": sorted(protected),
        "removed_cross_reference_edges": removed_edges,
        "engineering_status": "Reviewed layout failures quarantined; remaining units are not fully semantically reviewed",
        "clinical_review_status": "pending",
    }
    revised["corpus_sha256"] = digest(revised)
    return revised


def build_reviewed_corpus(review_path, root=None):
    root = Path(root or Path.cwd()).resolve()
    review = json.loads(Path(review_path).read_text(encoding="utf-8"))
    original_path = (root / review["input_corpus"]).resolve()
    output = (root / review["output"]).resolve()
    if (
        not original_path.is_relative_to(root)
        or not output.is_relative_to(root)
        or output == original_path.parent
    ):
        raise ValueError("Quality revision must use an isolated output inside the project")
    corpus = json.loads(original_path.read_text(encoding="utf-8"))
    verify_corpus(root, corpus)
    revised = apply_quality_review(corpus, review)
    verify_corpus(root, revised)
    target = output / "corpus.json"
    if target.exists():
        if json.loads(target.read_text(encoding="utf-8")) != revised:
            raise ValueError("Existing quality revision changed; preserve it and use a new output")
        return {
            "input_units": len(corpus["units"]),
            "retained_units": len(revised["units"]),
            "excluded_units": len(review["exclusions"]),
            "corpus_sha256": revised["corpus_sha256"],
            "output": str(output),
        }
    output.mkdir(parents=True, exist_ok=True)
    write_json(target, revised)
    write_json(output / "quality_review.json", review)
    blocks = "".join(
        f"<article><h2>{escape(entry['source_id'])}</h2><p>PDF {units['pdf_page']} · Section {escape(units['section'])}</p><p>{escape(entry['reason'])}</p><pre>{escape(units['evidence_text'])}</pre></article>"
        for entry in review["exclusions"]
        for units in [
            next(unit for unit in corpus["units"] if unit["source_id"] == entry["source_id"])
        ]
    )
    html = (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Corpus quality review | Occupational Fitness Platform</title><style>body{font:15px/1.7 system-ui;background:#f4f6f8;color:#233647;max-width:1050px;margin:40px auto;padding:20px}article{background:white;border:1px solid #dce3e9;padding:24px;margin:20px 0}pre{white-space:pre-wrap;background:#f4f7fa;padding:16px}h2{font-size:18px}</style><p>OCCUPATIONAL FITNESS PLATFORM</p><h1>Corpus quality review</h1>'
        + f"<p>{len(corpus['units'])} original units · {len(revised['units'])} retained · {len(review['exclusions'])} quarantined · {len(review['protected_source_ids'])} canonical source IDs preserved.</p><p>Engineering layout review only. Clinical applicability and explanation support remain pending. Historical experiments retain their original corpus. This revision has not replaced production knowledge.</p>"
        + blocks
        + '<p><a href="corpus.json">Revised original-text corpus</a> · <a href="quality_review.json">Pinned review and exclusion rationale</a></p></html>'
    )
    (output / "index.html").write_text(html, encoding="utf-8")
    return {
        "input_units": len(corpus["units"]),
        "retained_units": len(revised["units"]),
        "excluded_units": len(review["exclusions"]),
        "corpus_sha256": revised["corpus_sha256"],
        "output": str(output),
    }
