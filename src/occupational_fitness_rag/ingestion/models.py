from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ParsedBlock:
    page: int
    text: str
    bbox: tuple[float, float, float, float]
    font_size: float
    is_heading: bool = False
    section_number: str | None = None


@dataclass
class GuidelineChunk:
    chunk_id: str
    text: str
    section: str
    title: str
    pages: list[int]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "section": self.section,
            "title": self.title,
            "pages": self.pages,
            "metadata": self.metadata,
        }
