from __future__ import annotations

from occupational_fitness_rag.indexing.base import VectorStore
from occupational_fitness_rag.settings import RetrievalSettings

from .bm25 import rank_bm25
from .fusion import FusedResult, reciprocal_rank_fusion
from .reranker import CrossEncoderReranker, NoOpReranker


class RetrievalEngine:
    def __init__(self, store: VectorStore, settings: RetrievalSettings):
        self.store = store
        self.settings = settings
        if settings.reranker == "cross_encoder":
            self.reranker = CrossEncoderReranker(settings.cross_encoder_model)
        else:
            self.reranker = NoOpReranker()

    def retrieve(self, query: str, filters: dict[str, str]) -> list[FusedResult]:
        # HARD boundary: metadata filtering is supplied to the vector search itself.
        vector_ranked = self.store.search(query, filters, self.settings.candidate_k)

        bm25_ranked = []
        if self.settings.use_bm25:
            filtered = self.store.get_filtered(filters, self.settings.max_filtered_documents)
            bm25_ranked = rank_bm25(query, filtered, self.settings.bm25_k)

        if self.settings.use_bm25:
            fused = reciprocal_rank_fusion(vector_ranked, bm25_ranked, self.settings.rrf_k)
        else:
            fused = [
                FusedResult(
                    doc=doc, score=float(doc.vector_score or 0.0), vector_score=doc.vector_score
                )
                for doc in vector_ranked
            ]

        reranked = self.reranker.rerank(query, fused)

        # Deduplicate by chunk ID while preserving rank.
        seen: set[str] = set()
        unique: list[FusedResult] = []
        for item in reranked:
            if item.doc.chunk_id in seen:
                continue
            seen.add(item.doc.chunk_id)
            unique.append(item)
            if len(unique) >= self.settings.top_k:
                break
        return unique
