"""Experimental PDF corpus; never replaces the production rule catalogue.

Narrative regions are cut at complete subsection boundaries, not token offsets.
Tabulated standards continue to use the existing column-verified anchors.
"""

from __future__ import annotations

import re
from pathlib import Path

import pymupdf

from occupational_fitness_rag.ingestion.source_catalogue import extract_region
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json

MODULES = ("hypertension", "vision", "hearing", "blackout", "diabetes")
# PDF page numbers, one based. Tables and diagrams are explicitly excluded here.
NARRATIVE_PAGES = {
    "blackout": [68, 69, 72],
    "hypertension": [],  # Exact high-blood-pressure region below.
    "diabetes": [*range(103, 111), 114],
    "hearing": [116, 117, 118, 119, 121],
    "vision": [*range(212, 220), 223],
}
SECTION = re.compile(r"^\s*(\d+(?:\.\d+)+)[.\s]")
REFERENCE = re.compile(r"(?:refer\s+(?:also\s+)?to\s+|section\s+)(\d+(?:\.\d+)+)", re.I)


def narrative_scope_issue(title: str, text: str) -> str | None:
    """Reject private-headed material and flattened decision-chart branches.

    A clipped commercial word elsewhere in a private column cannot establish
    commercial applicability. Conversely, ordinary prose explicitly addressing
    both licence classes must not be rejected just for mentioning private.
    This structural guard is not a complete semantic applicability review.
    """
    if re.match(r"^private(?:\s|$|[:\-\u2013\u2014])", title.strip(), re.I):
        return "private-headed region requires separate scope review"
    answers = re.findall(r"^\s*(?:yes|no)\s*$", text, re.I | re.M)
    if len(answers) >= 2:
        return "flattened decision-chart answers require manual branch and column review"
    return None


def verify_source_segments(doc, unit, document_sha256):
    """Resolve a same-page composite to distinct, unchanged original rectangles."""
    segments = unit["source_segments"]
    if (
        not isinstance(segments, list)
        or len(segments) < 2
        or unit.get("segment_separator") != "\n\n"
    ):
        raise ValueError("Invalid original-source composite segment contract")
    seen, texts, offset = set(), [], 0
    for segment in segments:
        sid = segment["segment_id"]
        if not isinstance(sid, str) or not sid or sid in seen:
            raise ValueError("Duplicate or invalid original-source segment ID")
        seen.add(sid)
        if (
            segment["source_document_sha256"] != document_sha256
            or segment["pdf_page"] != unit["pdf_page"]
            or segment["printed_page"] != unit["printed_page"]
        ):
            raise ValueError("Original source segment document or page differs")
        actual = extract_region(doc[segment["pdf_page"] - 1], segment["bbox"])
        if (
            not actual
            or actual != segment["source_text"]
            or sha256_bytes(actual.encode("utf-8")) != segment["text_sha256"]
            or type(segment["composed_char_start"]) is not int
            or type(segment["composed_char_end"]) is not int
            or segment["composed_char_start"] != offset
            or segment["composed_char_end"] != offset + len(actual)
        ):
            raise ValueError("Original source segment text, rectangle or composite offset differs")
        texts.append(actual)
        offset += len(actual) + 2
    original = unit["context_derivation"]
    criterion = [
        segment for segment in segments if segment["segment_id"] == "canonical_criterion_cell"
    ]
    if (
        len(criterion) != 1
        or criterion[0]["bbox"] != unit["bbox"]
        or criterion[0]["source_text"] != original["original_evidence_text"]
        or criterion[0]["text_sha256"] != original["original_text_sha256"]
        or original["original_bbox"] != unit["bbox"]
    ):
        raise ValueError("Composite differs from its original canonical criterion")
    composed = "\n\n".join(texts)
    if unit.get("source_text") != composed:
        raise ValueError("Composite source text differs from its exact original segments")
    return composed


def verify_corpus(root: Path, corpus: dict) -> None:
    identity = corpus["corpus_sha256"]
    if digest({k: v for k, v in corpus.items() if k != "corpus_sha256"}) != identity:
        raise ValueError("Experimental corpus fingerprint mismatch")
    pdf = root / corpus["source_path"]
    if sha256_bytes(pdf.read_bytes()) != corpus["document_sha256"]:
        raise ValueError("Experimental source document changed")
    ids = set()
    with pymupdf.open(pdf) as doc:
        for unit in corpus["units"]:
            if unit["source_id"] in ids:
                raise ValueError("Duplicate experimental source ID")
            ids.add(unit["source_id"])
            actual = (
                verify_source_segments(doc, unit, corpus["document_sha256"])
                if "source_segments" in unit
                else extract_region(doc[unit["pdf_page"] - 1], unit["bbox"])
            )
            if (
                actual != unit["evidence_text"]
                or sha256_bytes(actual.encode()) != unit["text_sha256"]
            ):
                raise ValueError("Experimental passage does not match its PDF region")
            if unit["licence_context"] not in {"commercial", "shared"}:
                raise ValueError("Private-only evidence entered experimental corpus")
            for region in unit.get("alternate_regions", []):
                alternate = extract_region(doc[region["pdf_page"] - 1], region["bbox"])
                if alternate.strip() != unit["evidence_text"].strip():
                    raise ValueError(
                        "Alternate duplicate source region does not match original text"
                    )
        if any(sid not in ids for u in corpus["units"] for sid in u["cross_references"]):
            raise ValueError("Unresolved experimental cross reference")


def build_comparison_corpus(workflow, output: Path) -> dict:
    catalogue = workflow.catalogue
    units = [dict(u, module=u["condition"]) for u in catalogue.units.values()]
    pdf = workflow.root / units[0]["source_path"]
    exclusions = []

    def add_region(doc, module, number, bbox, section, title):
        text = extract_region(doc[number - 1], bbox)
        if len(text) < 70:
            return
        layout_issue = narrative_scope_issue(title, text)
        if layout_issue:
            exclusions.append(
                {"pdf_page": number, "bbox": bbox, "section": section, "reason": layout_issue}
            )
            return
        lower = text.lower()
        if "private" in lower and "commercial" not in lower:
            exclusions.append({"pdf_page": number, "bbox": bbox, "reason": "private-only wording"})
            return
        unit = {
            "source_id": "AFTD2022-EXP-" + digest([module, number, bbox, text])[:16],
            "module": module,
            "condition": module,
            "section": section,
            "table_row": title,
            "pdf_page": number,
            "printed_page": number - 11,
            "bbox": bbox,
            "evidence_text": text,
            "source_text": text,
            "text_sha256": sha256_bytes(text.encode()),
            "document_sha256": catalogue.units[next(iter(catalogue.units))]["document_sha256"],
            "source_path": pdf.relative_to(workflow.root).as_posix(),
            "licence_context": "commercial" if "commercial" in lower else "shared",
            "clinical_review_status": "pending",
            "cross_references": [],
            "boundary_review": "complete subsection within one PDF column; page continuation retained",
        }
        footer = doc[number - 1].get_text(clip=pymupdf.Rect(0, 790, 595, 842))
        if str(unit["printed_page"]) not in footer.split():
            raise ValueError("Unconfirmed printed page")
        units.append(unit)

    with pymupdf.open(pdf) as doc:
        for module, pages in NARRATIVE_PAGES.items():
            current = (
                {"blackout": "1", "diabetes": "3", "hearing": "4", "vision": "10"}[module]
                if pages
                else "2"
            )
            for number in pages:
                page = doc[number - 1]
                # A figure occupying a page/column is not safely linearized as prose.
                for left, right in [(50, 297), (303, 546)]:
                    blocks = [
                        b
                        for b in page.get_text("blocks")
                        if b[6] == 0
                        and b[0] >= left - 1
                        and b[2] <= right + 1
                        and b[1] >= 50
                        and b[3] < 790
                    ]
                    blocks.sort(key=lambda b: b[1])
                    groups, group = [], []
                    for b in blocks:
                        if SECTION.match(b[4]) and group:
                            groups.append(group)
                            group = []
                        group.append(b)
                    if group:
                        groups.append(group)
                    for group in groups:
                        match = SECTION.match(group[0][4])
                        if match:
                            current = match[1]
                        title = group[0][4].strip().replace("\n", " ")
                        # Diabetes 3.3.1 is explicitly private; omit whole subsection.
                        if module == "diabetes" and current == "3.3.1":
                            exclusions.append(
                                {
                                    "pdf_page": number,
                                    "section": current,
                                    "reason": "private-only subsection",
                                }
                            )
                            continue
                        if any("Figure " in b[4] for b in group):
                            exclusions.append(
                                {
                                    "pdf_page": number,
                                    "section": current,
                                    "reason": "figure needs manual reading-order review",
                                }
                            )
                            continue
                        bbox = [
                            left,
                            max(50, min(b[1] for b in group) - 0.2),
                            right,
                            min(789, max(b[3] for b in group) + 0.2),
                        ]
                        add_region(doc, module, number, bbox, current, title)
        add_region(doc, "hypertension", 77, [56, 295, 296, 692], "2.2.3", "High blood pressure")
        # Complete commercial columns include qualifications absent from short anchors.
        for module, number, left, top, section in [
            ("blackout", 70, 345, 175, "1.3"),
            ("blackout", 71, 345, 175, "1.3"),
            ("hypertension", 99, 345, 177, "2.3.1"),
            ("diabetes", 112, 345, 175, "3.3"),
            ("diabetes", 113, 345, 175, "3.3"),
            ("hearing", 120, 321, 325, "4.3"),
            ("vision", 220, 345, 290, "10.3"),
            ("vision", 221, 345, 175, "10.3"),
            ("vision", 222, 345, 175, "10.3"),
        ]:
            bottom = 528 if number == 99 else 780
            header = next(
                b for b in doc[number - 1].get_text("blocks") if "Commercial standards" in b[4]
            )
            # Column positions differ between the hearing, diabetes and vision tables.
            # Detect the actual header instead of clipping with one shared x coordinate.
            left, top = header[0] - 1, header[1] - 0.2
            add_region(
                doc,
                module,
                number,
                [left, top, 539, bottom],
                section,
                "Commercial standards with qualifications",
            )

    # Resolve explicit section references only; no new diagnostic relationship is inferred.
    unique_units, seen_text = [], {}
    for unit in units:
        key = (unit["module"], unit["evidence_text"].strip())
        if key in seen_text:
            original = seen_text[key]
            # Canonical IDs precede expanded units, so all 28 remain stable.
            original.setdefault("alternate_regions", []).append(
                {
                    "source_id": unit["source_id"],
                    "pdf_page": unit["pdf_page"],
                    "printed_page": unit["printed_page"],
                    "section": unit["section"],
                    "bbox": unit["bbox"],
                }
            )
            exclusions.append(
                {
                    "source_id": unit["source_id"],
                    "reason": "identical original text",
                    "canonical_source_id": original["source_id"],
                }
            )
        else:
            seen_text[key] = unit
            unique_units.append(unit)
    units = unique_units
    for u in units:
        compact = re.sub(r"\s+", "", u["evidence_text"])
        u["covers_source_ids"] = sorted(
            sid
            for sid, original in catalogue.units.items()
            if original["pdf_page"] == u["pdf_page"]
            and re.sub(r"\s+", "", original["evidence_text"]) in compact
        )
        refs = set(REFERENCE.findall(u["evidence_text"]))
        u["explicit_section_references"] = sorted(refs)
        u["unresolved_section_references"] = sorted(
            r for r in refs if not any(v["section"] == r for v in units)
        )
        u["cross_references"] = sorted(
            set(u["cross_references"])
            | {
                v["source_id"]
                for v in units
                if v["section"] in refs and v["source_id"] != u["source_id"]
            }
        )
    corpus = {
        "schema_version": "1.0.0",
        "source_path": pdf.relative_to(workflow.root).as_posix(),
        "document_sha256": sha256_bytes(pdf.read_bytes()),
        "production_catalogue_sha256": catalogue.index_sha256,
        "scope": "Five-module experimental source candidates; textual licence applicability requires independent review",
        "scope_review_status": "Metadata filtering and structural guards are not complete textual applicability verification",
        "narrative_screening_policy": "Reject private-headed regions and flattened decision-chart answers before keyword scope inference",
        "clinical_review_status": "pending",
        "units": units,
        "exclusions": exclusions,
    }
    corpus["corpus_sha256"] = digest(corpus)
    verify_corpus(workflow.root, corpus)
    write_json(output, corpus)
    return corpus
