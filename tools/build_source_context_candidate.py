"""Propose an inactive, segmented original-PDF context repair for DM-COM-008.

No corpus, canonical text, production rule or experimental payload is modified.
The exact row title and column header remain independently addressed source spans.
"""

import argparse
import hashlib
import json
import re
from html import escape
from pathlib import Path

SOURCE_ID = "AFTD2022-DM-COM-008"
PDF_SHA256 = "5811cfbb29c4db2cec704033ec2ee31506e78445ed8108e72d324cbef780500c"
ROW_TITLE = "Insulin-treated diabetes (except gestational diabetes)"
COMMERCIAL_HEADER = "Commercial standards"


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def layout_text(raw):
    """Keep literal hyphens; remove layout newlines and collapse whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"-[ \t]*\r?\n[ \t]*", "-", raw)).strip()


def original_block(page, expected):
    """Find one exact normalized original text block and retain its supplied bbox."""
    matches = [
        block
        for block in page.get_text("blocks")
        if len(block) >= 7 and block[6] == 0 and layout_text(block[4]) == expected
    ]
    if len(matches) != 1:
        raise ValueError("Original PDF heading must resolve to one exact text block")
    block = matches[0]
    return {
        "raw_pdf_text": block[4],
        "raw_pdf_text_sha256": sha256(block[4].encode("utf-8")),
        "layout_normalized_text": layout_text(block[4]),
        "bbox": list(block[:4]),
        "bbox_origin": "Original PDF text-block geometry; no manually estimated coordinates",
        "pdf_text_block_number": block[5],
        "normalization": "Join literal hyphen followed by a layout newline, preserving the hyphen; collapse remaining whitespace. Raw PDF text is retained separately.",
    }


def build(root, output):
    import pymupdf

    root, output = Path(root).resolve(), Path(output).resolve()
    if output != root / "outputs/experiments/source_scope_review_v1":
        raise ValueError("Keep this proposal in the established source-scope review directory")
    corpus_path = root / "outputs/experiments/corpus_quality_v1/corpus.json"
    corpus_raw = corpus_path.read_bytes()
    corpus = json.loads(corpus_raw)
    units = [unit for unit in corpus["units"] if unit["source_id"] == SOURCE_ID]
    if len(units) != 1:
        raise ValueError("Canonical criterion must resolve uniquely")
    unit = units[0]
    source_path = root / "data/knowledge/raw/ap_g56_22.pdf"
    pdf_raw = source_path.read_bytes()
    if sha256(pdf_raw) != PDF_SHA256 or unit["document_sha256"] != PDF_SHA256:
        raise ValueError("Original document revision changed")
    if sha256(unit["evidence_text"].encode("utf-8")) != unit["text_sha256"]:
        raise ValueError("Canonical criterion fingerprint differs")
    document = pymupdf.open(stream=pdf_raw, filetype="pdf")
    page = document[unit["pdf_page"] - 1]
    row = original_block(page, ROW_TITLE)
    header = original_block(page, COMMERCIAL_HEADER)
    segments = []
    for identifier, role, item, filename in [
        ("row_heading", "condition_column_row_heading", row, "dm008_row_heading.png"),
        (
            "commercial_column_heading",
            "licence_column_heading",
            header,
            "dm008_commercial_heading.png",
        ),
    ]:
        rectangle = pymupdf.Rect(item["bbox"])
        clipped = page.get_text("text", clip=rectangle)
        if (
            not page.rect.contains(rectangle)
            or layout_text(clipped) != item["layout_normalized_text"]
        ):
            raise ValueError("Original heading crop differs from its text block")
        item = {
            "segment_id": identifier,
            "original_layout_role": role,
            **item,
            "pdf_region_text": clipped,
            "pdf_region_text_sha256": sha256(clipped.encode("utf-8")),
            "pdf_page": unit["pdf_page"],
            "printed_page": unit["printed_page"],
            "image": "assets/" + filename,
        }
        segments.append(item)
    criterion_clip = page.get_text("text", clip=pymupdf.Rect(unit["bbox"]))
    if layout_text(criterion_clip) != layout_text(unit["evidence_text"]):
        raise ValueError("Canonical original criterion region differs")
    segments.append(
        {
            "segment_id": "canonical_criterion_cell",
            "original_layout_role": "commercial_column_conditional_criterion",
            "source_id": SOURCE_ID,
            "bbox": unit["bbox"],
            "bbox_origin": "Existing frozen canonical original-region coordinates; unchanged",
            "source_text": unit["evidence_text"],
            "text_sha256": unit["text_sha256"],
            "pdf_region_text": criterion_clip,
            "pdf_region_text_sha256": sha256(criterion_clip.encode("utf-8")),
            "pdf_page": unit["pdf_page"],
            "printed_page": unit["printed_page"],
            "section": unit["section"],
            "image": "assets/aftd2022-dm-com-008.png",
        }
    )
    proposal = {
        "candidate_version": "source_context_candidate_v1",
        "proposed_corpus_version": "proposed_corpus_context_v2_not_active",
        "candidate_status": "proposal_not_active",
        "target_source_id": SOURCE_ID,
        "source_document": "data/knowledge/raw/ap_g56_22.pdf",
        "source_document_sha256": PDF_SHA256,
        "existing_corpus_file_sha256": sha256(corpus_raw),
        "existing_corpus_sha256": corpus["corpus_sha256"],
        "builder_sha256": sha256(Path(__file__).read_bytes()),
        "extraction_engine": "PyMuPDF " + pymupdf.VersionBind,
        "coordinate_system": "PDF points, top-left origin; PDF page labels are one-based",
        "licence_scope": "commercial",
        "segments": segments,
        "proposed_composition": {
            "ordered_segment_ids": [segment["segment_id"] for segment in segments],
            "relation": "Condition-column row heading and commercial-column heading provide enclosing original-table context for the unchanged commercial criterion cell.",
            "original_condition_column_heading_is_not_a_private_criterion": True,
            "private_standard_text_included": False,
            "materialized_combined_retrieval_text": None,
            "explanatory_or_generated_text_added_to_source_segments": False,
        },
        "full_original_page_context": "assets/pdf_page_113.png",
        "engineering_verification": {
            "source_pdf_fingerprint_matches": True,
            "headings_resolve_to_unique_original_pdf_blocks": True,
            "crop_text_matches_original_blocks": True,
            "canonical_criterion_text_and_bbox_preserved": True,
            "ai_visual_review": "Original full page 113 and generated heading crops inspected as an AI engineering review; not independent human or clinical adjudication",
        },
        "independent_human_review": "pending",
        "clinical_review": "pending",
        "active": False,
        "production_change": False,
        "frozen_corpus_change": False,
        "experimental_payload_change": False,
        "next_gate": "Independent source/context and clinical-scope review, then a separately versioned corpus and rebuilt indexes before any new retrieval experiment. Current frozen experiments retain their existing source text.",
    }
    output.mkdir(parents=True, exist_ok=True)
    assets = output / "assets"
    assets.mkdir(exist_ok=True)
    for segment in segments[:2]:
        page.get_pixmap(
            matrix=pymupdf.Matrix(3, 3), clip=pymupdf.Rect(segment["bbox"]), alpha=False
        ).save(output / segment["image"])
    for segment in segments:
        image = output / segment["image"]
        if not image.is_file():
            raise ValueError("Create the existing source-scope review images first")
        segment["image_sha256"] = sha256(image.read_bytes())
    context_image = output / proposal["full_original_page_context"]
    if not context_image.is_file():
        raise ValueError("Full original source-page context is missing")
    proposal["full_original_page_context_sha256"] = sha256(context_image.read_bytes())
    (output / "context_candidate.json").write_text(
        json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    html = [
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Original context candidate | Occupational Fitness Platform</title><style>body{font:15px/1.65 Segoe UI,Arial;max-width:1180px;margin:32px auto;padding:0 22px;color:#253447;background:#f5f7fa}article{background:white;border:1px solid #dae3eb;border-radius:9px;padding:24px;margin:22px 0}h2{font-size:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f0f5f8;padding:16px}img{max-width:100%;height:auto;border:1px solid #dae3eb}.status{border-left:3px solid #ad7c25;background:#fff4db;padding:14px}a{color:#255e85}summary{cursor:pointer}</style><h1>Original context candidate: DM-COM-008</h1>',
        '<p class="status">Inactive proposal. Engineering source verification only. Independent human and clinical review pending. No existing corpus, rule, model result or experimental payload is changed.</p>',
        "<p>The original condition-column heading carries a gestational-diabetes exception outside the existing commercial criterion crop. This proposal preserves the heading, commercial-column label and unchanged criterion as separately addressed original source segments. No combined retrieval passage is activated.</p>",
        '<p><a href="context_candidate.json">Exact source segments and fingerprints</a> · <a href="index.html">Source scope review</a></p>',
    ]
    for segment in segments:
        text = segment.get("raw_pdf_text", segment.get("source_text"))
        html.append(
            f'<article><h2>{escape(segment["segment_id"])}</h2><p>{escape(segment["original_layout_role"])} · PDF {segment["pdf_page"]} · Printed page {segment["printed_page"]} · Region {escape(str(segment["bbox"]))}</p><a href="{segment["image"]}"><img src="{segment["image"]}" alt="Original PDF segment {escape(segment["segment_id"], quote=True)}"></a><h3>Exact extracted source text</h3><pre>{escape(text)}</pre>'
        )
        if "layout_normalized_text" in segment:
            html.append(
                "<p>Display text after declared layout normalization: <strong>"
                + escape(segment["layout_normalized_text"])
                + "</strong></p>"
            )
        html.append("</article>")
    html.append(
        '<article><h2>Full original table context</h2><a href="assets/pdf_page_113.png"><img src="assets/pdf_page_113.png" alt="Original PDF page 113, printed page 102"></a><p>'
        + escape(proposal["next_gate"])
        + "</p></article></html>"
    )
    (output / "context_candidate.html").write_text("".join(html), encoding="utf-8")
    return {
        "source_id": SOURCE_ID,
        "segments": len(segments),
        "row_heading_bbox": row["bbox"],
        "active": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="outputs/experiments/source_scope_review_v1")
    args = parser.parse_args()
    print(json.dumps(build(Path(__file__).resolve().parents[1], args.output)))
