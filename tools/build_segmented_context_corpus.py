"""Build a separate experimental corpus from independently addressed PDF regions."""

import argparse
import json
import re
from copy import deepcopy
from html import escape
from pathlib import Path

import pymupdf

from occupational_fitness_rag.evaluation.comparison_corpus import verify_corpus
from occupational_fitness_rag.ingestion.source_catalogue import extract_region
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json


def compose_unit(unit, segments):
    """Preserve the original criterion rectangle; address the full text by segments."""
    if len({segment["segment_id"] for segment in segments}) != len(segments):
        raise ValueError("Duplicate source segment")
    result = deepcopy(unit)
    offset, mapped = 0, []
    for segment in segments:
        text = segment["source_text"]
        if not text or sha256_bytes(text.encode("utf-8")) != segment["text_sha256"]:
            raise ValueError("Empty or changed original source segment")
        mapped.append({**deepcopy(segment), "composed_char_start": offset,
                       "composed_char_end": offset + len(text)})
        offset += len(text) + 2
    criterion = [segment for segment in mapped if segment["segment_id"] == "canonical_criterion_cell"]
    if len(criterion) != 1 or criterion[0]["source_text"] != unit["evidence_text"] or criterion[0]["bbox"] != unit["bbox"]:
        raise ValueError("The original canonical criterion and rectangle must remain exact")
    text = "\n\n".join(segment["source_text"] for segment in mapped)
    result.update(
        evidence_text=text, source_text=text, text_sha256=sha256_bytes(text.encode("utf-8")),
        source_segments=mapped, segment_separator="\n\n",
        geometry_scope="bbox addresses the original criterion cell; source_segments address the complete composite",
        context_derivation={
            "original_text_sha256": unit["text_sha256"] ,
            "original_evidence_text": unit["evidence_text"],
            "original_bbox": deepcopy(unit["bbox"]),
            "context_kind": "original_condition_row_heading_and_commercial_column_heading",
            "private_standard_text_included": False,
            "clinical_review": "pending", "independent_human_review": "pending",
        },
    )
    # A duplicate rectangle that only covers the old cell cannot address the composite.
    if result.pop("alternate_regions", None):
        result["original_alternate_regions"] = deepcopy(unit["alternate_regions"])
    return result


def build(root, base_path, candidate_path, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    base_path, candidate_path = Path(base_path).resolve(), Path(candidate_path).resolve()
    if not output.is_relative_to(root) or output == base_path.parent or output.is_relative_to(base_path.parent):
        raise ValueError("A context revision must use a separate project output directory")
    original_raw = base_path.read_bytes()
    original = json.loads(original_raw)
    verify_corpus(root, original)
    candidate_raw = candidate_path.read_bytes()
    candidate = json.loads(candidate_raw)
    expected_roles = {
        "row_heading": "condition_column_row_heading",
        "commercial_column_heading": "licence_column_heading",
        "canonical_criterion_cell": "commercial_column_conditional_criterion",
    }
    if (
        candidate["target_source_id"] != "AFTD2022-DM-COM-008"
        or candidate["licence_scope"] != "commercial"
        or [segment["segment_id"] for segment in candidate["segments"]] != list(expected_roles)
        or any(segment["original_layout_role"] != expected_roles[segment["segment_id"]] for segment in candidate["segments"])
        or candidate["segments"][0]["layout_normalized_text"] != "Insulin-treated diabetes (except gestational diabetes)"
        or candidate["segments"][1]["layout_normalized_text"] != "Commercial standards"
    ):
        raise ValueError("Expected the reviewed insulin-treated row and commercial column context")
    if candidate["existing_corpus_file_sha256"] != sha256_bytes(original_raw) or candidate["existing_corpus_sha256"] != original["corpus_sha256"]:
        raise ValueError("The proposed context belongs to another corpus")
    pdf = root / original["source_path"]
    if sha256_bytes(pdf.read_bytes()) != candidate["source_document_sha256"]:
        raise ValueError("Source PDF fingerprint differs")
    target_id = candidate["target_source_id"]
    target = next(unit for unit in original["units"] if unit["source_id"] == target_id)
    segments = []
    with pymupdf.open(pdf) as document:
        for segment in candidate["segments"]:
            actual = extract_region(document[segment["pdf_page"] - 1], segment["bbox"])
            expected = segment.get("source_text", segment.get("pdf_region_text", "")).strip()
            if actual != expected:
                raise ValueError("Proposed source segment differs from its actual PDF rectangle")
            segments.append({
                "segment_id": segment["segment_id"], "role": segment["original_layout_role"],
                "source_text": actual, "text_sha256": sha256_bytes(actual.encode("utf-8")),
                "pdf_page": segment["pdf_page"], "printed_page": segment["printed_page"],
                "bbox": segment["bbox"], "source_document_sha256": original["document_sha256"],
            })
    revised = compose_unit(target, segments)
    corpus = deepcopy(original)
    corpus["units"] = [revised if unit["source_id"] == target_id else unit for unit in corpus["units"]]
    canonical = {unit["source_id"]: unit for unit in corpus["units"] if "-EXP-" not in unit["source_id"]}
    changes = []
    for unit in corpus["units"]:
        compact = re.sub(r"\s+", "", unit["evidence_text"])
        previous = list(unit.get("covers_source_ids", []))
        unit["covers_source_ids"] = sorted(sid for sid, source in canonical.items()
            if source["pdf_page"] == unit["pdf_page"] and re.sub(r"\s+", "", source["evidence_text"]) in compact)
        if previous != unit["covers_source_ids"]:
            changes.append({"source_id": unit["source_id"], "before": previous, "after": unit["covers_source_ids"]})
    corpus.update(
        schema_version="1.1.0",
        context_review={
            "base_corpus_sha256": original["corpus_sha256"],
            "base_corpus_file_sha256": sha256_bytes(original_raw),
            "candidate_sha256": sha256_bytes(candidate_raw), "changed_source_ids": [target_id],
            "original_pdf_regions_verified": True, "clinical_review": "pending",
            "independent_human_review": "pending", "production_change": False,
            "coverage_changes": changes,
        },
    )
    corpus.pop("corpus_sha256")
    corpus["corpus_sha256"] = digest(corpus)
    verify_corpus(root, corpus)
    if base_path.read_bytes() != original_raw or candidate_path.read_bytes() != candidate_raw:
        raise ValueError("Frozen inputs changed during context preparation")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Preserve prior corpus revisions and use an empty output")
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "corpus.json", corpus)
    write_json(output / "manifest.json", {
        "kind": "targeted_original_table_context_revision", "corpus_sha256": corpus["corpus_sha256"],
        "corpus_file_sha256": sha256_bytes((output / "corpus.json").read_bytes()),
        "builder_source": Path(__file__).read_text(encoding="utf-8"),
        "context_review": corpus["context_review"], "unit_count": len(corpus["units"]),
        "canonical_source_count": len(canonical), "retrieval_calls": 0, "graph_indexes_built": 0,
        "active_in_production": False, "source_id": target_id,
    })
    rows = "".join('<tr><td>' + escape(segment["segment_id"]) + '</td><td>'
        + str(segment["pdf_page"]) + '</td><td>' + escape(str(segment["bbox"]))
        + '</td><td><pre>' + escape(segment["source_text"]) + '</pre></td></tr>'
        for segment in revised["source_segments"])
    html = ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Original table context revision</title>'
        '<style>body{font:15px/1.6 system-ui;color:#243748;max-width:1200px;margin:40px auto;padding:24px}'
        'table{width:100%;border-collapse:collapse}td,th{padding:12px;border-bottom:1px solid #dce3ea;text-align:left}'
        'pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><small>OCCUPATIONAL FITNESS PLATFORM</small>'
        '<h1>Original table context revision</h1><p>The insulin-treated diabetes row heading, including '
        'its gestational-diabetes exception, and the commercial column heading are retained as separate original PDF regions. '
        'The previous commercial criterion cell is unchanged. No private-standard criterion is included.</p>'
        '<p>This targeted engineering revision preserves 94 units and 28 canonical source IDs. Independent human and clinical '
        'review remain pending. No production catalogue or index is replaced, and no new retrieval is claimed.</p>'
        '<table><tr><th>Segment</th><th>PDF page</th><th>Original rectangle</th><th>Exact source text</th></tr>'
        + rows + '</table><p><a href="corpus.json">Revised corpus</a> · <a href="manifest.json">Version and coverage changes</a></p></html>')
    (output / "index.html").write_text(html, encoding="utf-8")
    return {"units": len(corpus["units"]), "canonical_sources": len(canonical),
            "corpus_sha256": corpus["corpus_sha256"], "source_segments": len(segments),
            "coverage_changes": len(changes), "production_change": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="outputs/experiments/corpus_quality_v1/corpus.json")
    parser.add_argument("--candidate", default="outputs/experiments/source_scope_review_v1/context_candidate.json")
    parser.add_argument("--output", default="outputs/experiments/corpus_context_v2")
    args = parser.parse_args()
    print(json.dumps(build(Path(__file__).resolve().parents[1], args.base, args.candidate, args.output), indent=2))
