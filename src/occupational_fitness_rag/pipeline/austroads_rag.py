from __future__ import annotations

from occupational_fitness_rag.retrieval.engine import RetrievalEngine
from occupational_fitness_rag.retrieval.query_builder import build_filters, build_semantic_query
from occupational_fitness_rag.schemas.evidence_pack import (
    EvidenceItem,
    EvidencePack,
    RetrievalStatus,
)
from occupational_fitness_rag.schemas.rule_result import Route, RuleResult
from occupational_fitness_rag.settings import AppSettings


class AustroadsRAGPipeline:
    def __init__(self, engine: RetrievalEngine, settings: AppSettings):
        self.engine = engine
        self.settings = settings

    def run(self, rule_result: RuleResult) -> EvidencePack:
        filters = build_filters(rule_result)

        if rule_result.route == Route.FAST_PATH:
            return EvidencePack(
                case_id=rule_result.case_id,
                status=RetrievalStatus.SKIPPED_FAST_PATH,
                filters=filters,
                notes=["Deterministic fast path: RAG not invoked."],
            )

        if (
            rule_result.route == Route.MISSING_INFORMATION
            and self.settings.routing.missing_info_policy == "short_circuit"
        ):
            return EvidencePack(
                case_id=rule_result.case_id,
                status=RetrievalStatus.SKIPPED_MISSING_INFORMATION,
                filters=filters,
                notes=[
                    "Missing case information remains unknown; RAG must not invent patient facts."
                ],
            )

        allowed_routes = set(self.settings.routing.retrieve_on_routes)
        if rule_result.route.value not in allowed_routes and not (
            rule_result.route == Route.MISSING_INFORMATION
            and self.settings.routing.missing_info_policy == "retrieve_requirements"
        ):
            return EvidencePack(
                case_id=rule_result.case_id,
                status=RetrievalStatus.INVALID_ROUTE,
                filters=filters,
                notes=[f"Route '{rule_result.route.value}' is not configured for RAG retrieval."],
            )

        include_missing = self.settings.routing.missing_info_policy == "retrieve_requirements"
        query = build_semantic_query(rule_result, include_missing=include_missing)
        results = self.engine.retrieve(query, filters)
        if not results:
            return EvidencePack(
                case_id=rule_result.case_id,
                status=RetrievalStatus.NO_EVIDENCE,
                filters=filters,
                semantic_query=query,
                notes=["No evidence matched the strict metadata filter."],
            )

        evidence = []
        for item in results:
            md = dict(item.doc.metadata)
            pages = md.get("pages", [])
            if isinstance(pages, str):
                pages = [int(x) for x in pages.split(",") if x.strip().isdigit()]
            evidence.append(
                EvidenceItem(
                    chunk_id=item.doc.chunk_id,
                    score=float(item.rerank_score if item.rerank_score is not None else item.score),
                    vector_score=item.vector_score,
                    bm25_score=item.bm25_score,
                    rerank_score=item.rerank_score,
                    section=str(md.get("section", "unknown")),
                    pages=list(pages or []),
                    excerpt=item.doc.text.strip(),
                    source_name=str(md.get("source_name", self.settings.source.name)),
                    source_version=str(md.get("source_version", self.settings.source.version)),
                    metadata={
                        key: value
                        for key, value in md.items()
                        if key not in {"section", "pages", "source_name", "source_version"}
                    },
                )
            )
        return EvidencePack(
            case_id=rule_result.case_id,
            status=RetrievalStatus.FOUND,
            filters=filters,
            semantic_query=query,
            evidence=evidence,
        )
