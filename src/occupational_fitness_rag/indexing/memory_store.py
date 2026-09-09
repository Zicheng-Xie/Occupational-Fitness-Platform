from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable

from occupational_fitness_rag.ingestion.models import GuidelineChunk

from .base import StoredDocument

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_.-]+")


def _tokens(text: str) -> list[str]:
    return [x.lower() for x in _TOKEN_RE.findall(text)]


def _cosine(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(value * b.get(key, 0) for key, value in a.items())
    na = math.sqrt(sum(value * value for value in a.values()))
    nb = math.sqrt(sum(value * value for value in b.values()))
    return dot / (na * nb) if na and nb else 0.0


class InMemoryVectorStore:
    """Lexical cosine store for offline experiments, not dense semantic embeddings."""

    def __init__(self, chunks: Iterable[GuidelineChunk] = ()):
        self.docs: list[StoredDocument] = []
        self.add(list(chunks))

    def add(self, chunks: list[GuidelineChunk]) -> None:
        incoming = {chunk.chunk_id for chunk in chunks}
        self.docs = [doc for doc in self.docs if doc.chunk_id not in incoming]
        for chunk in chunks:
            md = dict(chunk.metadata)
            md.update(
                {
                    "section": chunk.section,
                    "title": chunk.title,
                    "pages": list(chunk.pages),
                }
            )
            self.docs.append(StoredDocument(chunk.chunk_id, chunk.text, md))

    @staticmethod
    def _matches(metadata: dict, where: dict[str, str]) -> bool:
        return all(str(metadata.get(key, "")) == str(value) for key, value in where.items())

    def get_filtered(self, where: dict[str, str], limit: int | None = None) -> list[StoredDocument]:
        docs = [doc for doc in self.docs if self._matches(doc.metadata, where)]
        return docs[:limit] if limit is not None else docs

    def search(self, query: str, where: dict[str, str], k: int) -> list[StoredDocument]:
        q = Counter(_tokens(query))
        scored = []
        for doc in self.get_filtered(where):
            score = _cosine(q, Counter(_tokens(doc.text)))
            if score > 0:
                scored.append(StoredDocument(doc.chunk_id, doc.text, dict(doc.metadata), score))
        return sorted(scored, key=lambda d: d.vector_score or 0.0, reverse=True)[:k]
