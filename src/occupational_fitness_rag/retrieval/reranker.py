from __future__ import annotations

from typing import Protocol

from .fusion import FusedResult


class Reranker(Protocol):
    def rerank(self, query: str, items: list[FusedResult]) -> list[FusedResult]: ...


class NoOpReranker:
    def rerank(self, query: str, items: list[FusedResult]) -> list[FusedResult]:
        return items


class CrossEncoderReranker:
    def __init__(self, model_name: str):
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise RuntimeError("Install the rerank extra: pip install -e '.[rerank]'") from exc
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, items: list[FusedResult]) -> list[FusedResult]:
        if not items:
            return []
        scores = self.model.predict([(query, item.doc.text) for item in items])
        for item, score in zip(items, scores):
            item.rerank_score = float(score)
        return sorted(
            items,
            key=lambda x: x.rerank_score if x.rerank_score is not None else float("-inf"),
            reverse=True,
        )
