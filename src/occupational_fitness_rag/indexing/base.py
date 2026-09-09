from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from occupational_fitness_rag.ingestion.models import GuidelineChunk


@dataclass
class StoredDocument:
    chunk_id: str
    text: str
    metadata: dict[str, Any]
    vector_score: float | None = None


class VectorStore(Protocol):
    def add(self, chunks: list[GuidelineChunk]) -> None: ...
    def search(self, query: str, where: dict[str, str], k: int) -> list[StoredDocument]: ...
    def get_filtered(
        self, where: dict[str, str], limit: int | None = None
    ) -> list[StoredDocument]: ...
