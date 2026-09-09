from __future__ import annotations

from dataclasses import dataclass

from occupational_fitness_rag.indexing.base import StoredDocument


@dataclass
class FusedResult:
    doc: StoredDocument
    score: float
    vector_score: float | None = None
    bm25_score: float | None = None
    rerank_score: float | None = None


def reciprocal_rank_fusion(
    vector_ranked: list[StoredDocument],
    bm25_ranked: list[tuple[StoredDocument, float]],
    rrf_k: int = 60,
) -> list[FusedResult]:
    by_id: dict[str, FusedResult] = {}
    for rank, doc in enumerate(vector_ranked, start=1):
        item = by_id.setdefault(doc.chunk_id, FusedResult(doc=doc, score=0.0))
        item.score += 1.0 / (rrf_k + rank)
        item.vector_score = doc.vector_score
    for rank, (doc, raw_score) in enumerate(bm25_ranked, start=1):
        item = by_id.setdefault(doc.chunk_id, FusedResult(doc=doc, score=0.0))
        item.score += 1.0 / (rrf_k + rank)
        item.bm25_score = raw_score
    return sorted(by_id.values(), key=lambda x: x.score, reverse=True)
