from __future__ import annotations

import json
from pathlib import Path

from occupational_fitness_rag.settings import AppSettings

from .annotations import apply_annotations, load_annotation_rules
from .models import GuidelineChunk
from .pdf_parser import parse_pdf
from .section_chunker import chunk_by_section


def ingest_pdf_to_chunks(pdf_path: str | Path, settings: AppSettings) -> list[GuidelineChunk]:
    blocks = parse_pdf(pdf_path, heading_size_ratio=settings.chunking.heading_size_ratio)
    chunks = chunk_by_section(
        blocks,
        source_name=settings.source.name,
        source_version=settings.source.version,
        jurisdiction=settings.source.jurisdiction,
        max_chars=settings.chunking.max_chars,
        overlap_chars=settings.chunking.overlap_chars,
    )
    annotations = load_annotation_rules(settings.annotations_file)
    return apply_annotations(chunks, annotations, settings.source.default_licence_context)


def write_chunks_jsonl(chunks: list[GuidelineChunk], output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk.to_record(), ensure_ascii=False) + "\n")
