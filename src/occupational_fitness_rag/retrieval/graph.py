"""Experimental rule/source graph expansion over the existing verified anchors.

This is a small graph-assisted retrieval baseline, not a full-document GraphRAG
system. It does not infer diagnoses or change the production RAG configuration.
"""

from __future__ import annotations

from collections import defaultdict

from occupational_fitness_rag.retrieval.fusion import FusedResult


def expand_graph(seeds, filtered_documents, book, catalogue, module, top_k):
    """Rank seed hits and one-hop neighbours with fixed, inspectable edge weights."""
    docs = {doc.chunk_id: doc for doc in filtered_documents}
    source_to_chunks = defaultdict(set)
    for doc in filtered_documents:
        for source_id in doc.metadata["source_ids_csv"].split(","):
            if source_id not in catalogue.units:
                raise ValueError("Graph chunk contains an unknown source ID")
            source_to_chunks[source_id].add(doc.chunk_id)
    edges = defaultdict(dict)

    def connect(left, right, weight):
        if left != right and left in source_to_chunks and right in source_to_chunks:
            edges[left][right] = max(edges[left].get(right, 0), weight)
            edges[right][left] = max(edges[right].get(left, 0), weight)

    for rule in book.rules:
        if rule["module"] != module:
            continue
        sources = rule["source_ids"]
        for left in sources:
            for right in sources:
                connect(left, right, 0.85)
    for source_id in source_to_chunks:
        unit = catalogue.units[source_id]
        for other in unit["cross_references"]:
            connect(source_id, other, 0.85)
        for other in source_to_chunks:
            if unit["section"] == catalogue.units[other]["section"]:
                connect(source_id, other, 0.45)

    scores = defaultdict(float)
    direct = {}
    for rank, hit in enumerate(seeds[:3], 1):
        if hit.doc.chunk_id not in docs:
            raise ValueError("Graph seed crossed its metadata filter")
        direct[hit.doc.chunk_id] = hit
        vote = 1.0 / (60 + rank)
        scores[hit.doc.chunk_id] += vote
        for source_id in hit.doc.metadata["source_ids_csv"].split(","):
            for neighbour, weight in edges[source_id].items():
                for chunk_id in source_to_chunks[neighbour]:
                    scores[chunk_id] += vote * weight
    ranked = sorted(scores, key=lambda chunk_id: (-scores[chunk_id], chunk_id))[:top_k]
    return [
        FusedResult(
            doc=docs[chunk_id],
            score=scores[chunk_id],
            vector_score=direct[chunk_id].vector_score if chunk_id in direct else None,
            bm25_score=direct[chunk_id].bm25_score if chunk_id in direct else None,
        )
        for chunk_id in ranked
    ]
