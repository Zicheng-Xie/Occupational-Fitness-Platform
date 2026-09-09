from __future__ import annotations

import re
from pathlib import Path
from statistics import median

import pymupdf as fitz

from .models import ParsedBlock

_SECTION_RE = re.compile(r"^\s*(\d+(?:\.\d+){0,4})\s+(.+?)\s*$")


def _line_text(line: dict) -> tuple[str, float]:
    spans = line.get("spans", [])
    text = "".join(str(span.get("text", "")) for span in spans).strip()
    sizes = [float(span.get("size", 0.0)) for span in spans if span.get("text", "").strip()]
    return text, (max(sizes) if sizes else 0.0)


def parse_pdf(path: str | Path, heading_size_ratio: float = 1.15) -> list[ParsedBlock]:
    """Extract line-level text with 1-indexed page provenance.

    This intentionally keeps provenance simple and auditable. More advanced OCR/table
    parsing can replace this adapter without changing the downstream chunk schema.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    doc = fitz.open(path)
    raw: list[tuple[int, str, tuple[float, float, float, float], float]] = []
    font_sizes: list[float] = []

    for page_index, page in enumerate(doc):
        page_dict = page.get_text("dict")
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                text, size = _line_text(line)
                if not text:
                    continue
                bbox = tuple(float(x) for x in line.get("bbox", (0, 0, 0, 0)))
                raw.append((page_index + 1, text, bbox, size))
                if size > 0:
                    font_sizes.append(size)

    body_size = median(font_sizes) if font_sizes else 10.0
    out: list[ParsedBlock] = []
    for page, text, bbox, size in raw:
        section_match = _SECTION_RE.match(text)
        looks_short = len(text) <= 180
        large_font = size >= body_size * heading_size_ratio
        is_heading = bool(section_match) or (looks_short and large_font)
        section_number = section_match.group(1) if section_match else None
        out.append(
            ParsedBlock(
                page=page,
                text=text,
                bbox=bbox,
                font_size=size,
                is_heading=is_heading,
                section_number=section_number,
            )
        )
    return out
