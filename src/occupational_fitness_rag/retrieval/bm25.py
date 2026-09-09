from __future__ import annotations

import math
import re
from collections import Counter

from occupational_fitness_rag.indexing.base import StoredDocument

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_.-]+")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text)]


def rank_bm25(
    query: str, docs: list[StoredDocument], k: int, k1: float = 1.5, b: float = 0.75
) -> list[tuple[StoredDocument, float]]:
    """Small Okapi BM25 implementation for a filtered guideline subset."""
    if not docs:
        return []
    tokenized = [tokenize(doc.text) for doc in docs]
    n = len(tokenized)
    avgdl = sum(len(x) for x in tokenized) / max(n, 1)
    dfs: Counter[str] = Counter()
    for tokens in tokenized:
        dfs.update(set(tokens))
    query_terms = tokenize(query)
    scored: list[tuple[StoredDocument, float]] = []
    for doc, tokens in zip(docs, tokenized):
        tf = Counter(tokens)
        dl = len(tokens)
        score = 0.0
        for term in query_terms:
            df = dfs.get(term, 0)
            if df == 0:
                continue
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            freq = tf.get(term, 0)
            denom = freq + k1 * (1 - b + b * dl / max(avgdl, 1e-9))
            if denom:
                score += idf * (freq * (k1 + 1)) / denom
        if score > 0:
            scored.append((doc, score))
    return sorted(scored, key=lambda x: x[1], reverse=True)[:k]
