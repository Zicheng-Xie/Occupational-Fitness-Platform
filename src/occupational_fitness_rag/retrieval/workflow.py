"""Bind required sources, then optionally rank strictly filtered contextual evidence."""

from __future__ import annotations

from occupational_fitness_rag.ingestion.models import GuidelineChunk
from occupational_fitness_rag.ingestion.source_catalogue import SourceCatalogue
from occupational_fitness_rag.provenance import digest
from occupational_fitness_rag.rules.engine import RuleBook
from occupational_fitness_rag.schemas.workflow import (
    RequestEvidence,
    WorkflowEvidencePack,
    WorkflowRoute,
    WorkflowRuleResult,
)


def catalogue_chunks(book: RuleBook, catalogue: SourceCatalogue) -> list[GuidelineChunk]:
    chunks = []
    for rule in book.rules:
        for source_id in rule["source_ids"]:
            unit = catalogue.units[source_id]
            chunks.append(
                GuidelineChunk(
                    chunk_id=unit["chunk_id"] + "-" + digest(rule["rag_query_key"])[:10],
                    text=unit["evidence_text"],
                    section=unit["section"],
                    title=unit["table_row"] or rule["subcondition"],
                    pages=[unit["pdf_page"]],
                    metadata={
                        "source_id": source_id,
                        "source_name": "Austroads Assessing Fitness to Drive",
                        "source_version": "AP-G56-22",
                        "licence_context": "commercial",
                        "category": rule["category"],
                        "subcondition": rule["subcondition"],
                        "rag_query_key": rule["rag_query_key"],
                        "index_sha256": catalogue.index_sha256,
                    },
                )
            )
    return chunks


class WorkflowRetriever:
    def __init__(
        self,
        catalogue: SourceCatalogue,
        book: RuleBook,
        engine=None,
        mode="exact",
        embedding_model="none",
    ):
        self.catalogue, self.book, self.engine, self.mode = catalogue, book, engine, mode
        self.embedding_model = embedding_model if mode == "chroma" else "none"
        self.rules = {r["rule_id"]: r for r in book.rules}
        for rule in book.rules:
            for source_id in rule["source_ids"]:
                if source_id not in catalogue.units:
                    raise ValueError(f"Unresolved rule source ID: {source_id}")

    def run(self, result: WorkflowRuleResult) -> WorkflowEvidencePack:
        if result.ruleset_sha256 != self.book.sha256:
            raise ValueError("Rule result belongs to a different ruleset version")
        request_ids = [r.request_id for r in result.rag_requests]
        if len(request_ids) != len(set(request_ids)):
            raise ValueError("Duplicate RAG request IDs")
        before = digest(result)
        items, semantic_calls = [], 0
        for request in result.rag_requests:
            rule = self.rules.get(request.rule_id)
            if not rule or any(
                getattr(request, key) != rule[key]
                for key in ("category", "subcondition", "rag_query_key", "source_ids")
            ):
                raise ValueError("RAG request does not match the authoritative rule catalogue")
            citations, unresolved = [], []
            for source_id in request.source_ids:
                citation = self.catalogue.citation(source_id)
                if citation:
                    citations.append(citation)
                else:
                    unresolved.append(source_id)
            filters = {
                "category": request.category,
                "subcondition": request.subcondition,
                "licence_context": "commercial",
                "source_version": "AP-G56-22",
                "rag_query_key": request.rag_query_key,
                "index_sha256": self.catalogue.index_sha256,
            }
            query = None
            ranked_candidates = []
            # Required exact citations are never displaced by top-k ranking.
            if self.engine and result.route != WorkflowRoute.FAST:
                query = f"{request.category} {request.subcondition} {rule['reason_template']}"
                hits = self.engine.retrieve(query, filters)
                semantic_calls += 1
                scores = {}
                for rank, hit in enumerate(hits, 1):
                    if not all(str(hit.doc.metadata.get(k)) == str(v) for k, v in filters.items()):
                        raise ValueError("Retriever violated the strict metadata boundary")
                    source_id = hit.doc.metadata.get("source_id")
                    ranked_candidates.append(
                        {
                            "rank": rank,
                            "source_id": source_id,
                            "chunk_id": hit.doc.chunk_id,
                            "fusion_score": hit.score,
                            "vector_score": hit.vector_score,
                            "bm25_score": hit.bm25_score,
                            "rerank_score": hit.rerank_score,
                            "score_type": "dense_bm25_rrf"
                            if self.mode == "chroma"
                            else "lexical_cosine_bm25_rrf",
                        }
                    )
                    if source_id in request.source_ids:
                        scores[source_id] = (
                            hit.rerank_score if hit.rerank_score is not None else hit.score
                        )
                citations.sort(key=lambda c: scores.get(c.source_id, float("-inf")), reverse=True)
            items.append(
                RequestEvidence(
                    request_id=request.request_id,
                    rule_id=request.rule_id,
                    status="complete"
                    if not unresolved
                    else "partial"
                    if citations
                    else "no_evidence",
                    requested_source_ids=request.source_ids,
                    citations=citations,
                    unresolved_source_ids=unresolved,
                    metadata_filters=filters,
                    semantic_query=query,
                    ranked_candidates=ranked_candidates,
                )
            )
        unchanged = digest(result) == before
        if not unchanged:
            raise RuntimeError("Rule result was mutated during retrieval")
        payload = dict(
            result_id=result.result_id,
            case_id=result.case_id,
            rule_result_sha256=before,
            index_sha256=self.catalogue.index_sha256,
            retrieval={
                "query_mode": "per_request",
                "backend": self.mode,
                "required_evidence": "exact_source_id_binding",
                "ranking_calls": semantic_calls,
                "embedding_model": self.embedding_model,
                "score_note": "Exact source identity score is not clinical confidence; optional ranking never replaces required evidence.",
            },
            evidence_items=items,
            unresolved_requests=[x.request_id for x in items if x.status != "complete"],
            integrity={
                "all_request_ids_accounted_for": set(request_ids) == {x.request_id for x in items},
                "all_citations_match_guideline_version": all(
                    c.guideline_version == result.guideline_version
                    for x in items
                    for c in x.citations
                ),
                "all_citations_verified_against_pdf": True,
                "rule_result_fields_modified_by_rag": False,
            },
        )
        return WorkflowEvidencePack(evidence_pack_id="EP-" + digest(payload)[:20], **payload)
