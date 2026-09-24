"""Symptom-led module discovery alongside mandatory rule-bound source citations."""

from occupational_fitness_rag.retrieval.engine import RetrievalEngine
from occupational_fitness_rag.settings import RetrievalSettings


def discover_symptoms(retriever, result, rules):
    groups = {}
    for request in result.rag_requests:
        module = rules[request.rule_id]["module"]
        for span in result.narrative_context.get(request.request_id, []):
            groups.setdefault(module, {})[(span.start, span.end)] = span
    reports = []
    engine = RetrievalEngine(retriever.store, RetrievalSettings(top_k=5))
    for module, positions in sorted(groups.items()):
        spans = sorted(positions.values(), key=lambda s: s.start)
        query = " ".join(s.quote for s in spans)[:6000]
        filters = {
            "module": module,
            "licence_context": "commercial",
            "source_version": "AP-G56-22",
            "index_sha256": retriever.workflow.catalogue.index_sha256,
        }
        hits = engine.retrieve(query, filters)
        ranked, citations, seen = [], [], set()
        for rank, hit in enumerate(hits, 1):
            if any(str(hit.doc.metadata.get(k)) != v for k, v in filters.items()):
                raise ValueError("Symptom retrieval crossed its module/version boundary")
            source_ids = hit.doc.metadata["source_ids_csv"].split(",")
            ranked.append(
                {
                    "rank": rank,
                    "chunk_id": hit.doc.chunk_id,
                    "source_ids": source_ids,
                    "fusion_score": hit.score,
                    "vector_score": hit.vector_score,
                    "bm25_score": hit.bm25_score,
                }
            )
            for sid in source_ids:
                if sid not in seen:
                    citations.append(
                        retriever.workflow.catalogue.citation(
                            sid, hit.score, "retrieval_rank"
                        ).model_dump(mode="json")
                    )
                    seen.add(sid)
        reports.append(
            {
                "module": module,
                "query": query,
                "query_mode": "joined_verbatim_symptom_spans",
                "source_text_sha256": result.narrative_source_text_sha256,
                "source_passages": [s.model_dump(mode="json") for s in spans],
                "metadata_filters": filters,
                "ranked_candidates": ranked,
                "citations": citations,
                "status": "candidates_found" if ranked else "no_candidates",
                "clinical_facts_inferred": False,
            }
        )
    return reports
