from __future__ import annotations

import hashlib
from collections.abc import Iterable

from .models import GuidelineChunk, ParsedBlock


def _chunk_id(source_version: str, section: str, pages: list[int], ordinal: int, text: str) -> str:
    raw = f"{source_version}|{section}|{pages}|{ordinal}|{text[:120]}".encode("utf-8")
    return "austroads-" + hashlib.sha1(raw).hexdigest()[:16]


def _emit(
    text_parts: list[str],
    pages: list[int],
    section: str,
    title: str,
    source_name: str,
    source_version: str,
    jurisdiction: str,
    ordinal: int,
) -> GuidelineChunk | None:
    text = "\n".join(part.strip() for part in text_parts if part.strip()).strip()
    if not text:
        return None
    pages = sorted(set(pages))
    return GuidelineChunk(
        chunk_id=_chunk_id(source_version, section, pages, ordinal, text),
        text=text,
        section=section or "unknown",
        title=title or "",
        pages=pages,
        metadata={
            "source_name": source_name,
            "source_version": source_version,
            "jurisdiction": jurisdiction,
        },
    )


def chunk_by_section(
    blocks: Iterable[ParsedBlock],
    *,
    source_name: str,
    source_version: str,
    jurisdiction: str,
    max_chars: int = 1800,
    overlap_chars: int = 180,
) -> list[GuidelineChunk]:
    """Chunk without crossing explicit section headings when possible."""
    chunks: list[GuidelineChunk] = []
    section = "unknown"
    title = ""
    text_parts: list[str] = []
    pages: list[int] = []
    ordinal = 0

    def flush() -> None:
        nonlocal text_parts, pages, ordinal
        chunk = _emit(
            text_parts, pages, section, title, source_name, source_version, jurisdiction, ordinal
        )
        if chunk:
            chunks.append(chunk)
            ordinal += 1
        if overlap_chars > 0 and text_parts:
            joined = "\n".join(text_parts)
            tail = joined[-overlap_chars:]
            text_parts = [tail] if tail.strip() else []
            pages = [pages[-1]] if pages else []
        else:
            text_parts, pages = [], []

    for block in blocks:
        if block.is_heading:
            if text_parts:
                flush()
                text_parts, pages = [], []  # do not carry overlap across a section boundary
            title = block.text
            if block.section_number:
                section = block.section_number
            text_parts.append(block.text)
            pages.append(block.page)
            continue

        projected = sum(len(x) for x in text_parts) + len(block.text) + max(0, len(text_parts) - 1)
        if projected > max_chars and text_parts:
            flush()
        text_parts.append(block.text)
        pages.append(block.page)

    if text_parts:
        flush()
    return chunks
