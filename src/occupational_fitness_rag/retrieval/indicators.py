"""Category-scoped discovery with explicit reference expansion and no rule decisions."""

from occupational_fitness_rag.indexing.memory_store import InMemoryVectorStore
from occupational_fitness_rag.ingestion.models import GuidelineChunk
from occupational_fitness_rag.provenance import digest, sha256_bytes
from occupational_fitness_rag.retrieval.engine import RetrievalEngine
from occupational_fitness_rag.schemas.indicator import IndicatorEvidence
from occupational_fitness_rag.settings import RetrievalSettings


def knowledge_chunks(book, catalogue, strategy="unit"):
    """Keep complete anchored clauses; group by section/page only for comparison runs."""
    groups = {}
    for rule in book.rules:
        for sid in rule["source_ids"]:
            unit = catalogue.units[sid]
            key = (
                rule["module"],
                sid
                if strategy == "unit"
                else unit["section"]
                if strategy == "section"
                else str(unit["pdf_page"]),
            )
            groups.setdefault(key, {})[sid] = unit
    chunks = []
    for (module, key), units in sorted(groups.items()):
        values = list(units.values())
        chunks.append(
            GuidelineChunk(
                chunk_id="IND-"
                + digest([module, strategy, key, sorted(units), catalogue.index_sha256])[:24],
                text="\n\n".join(x["evidence_text"] for x in values),
                section=" / ".join(sorted({x["section"] for x in values})),
                title=" / ".join(x["table_row"] or x["section"] for x in values),
                pages=sorted({x["pdf_page"] for x in values}),
                metadata={
                    "module": module,
                    "licence_context": "commercial",
                    "source_version": "AP-G56-22",
                    "index_sha256": catalogue.index_sha256,
                    "source_ids_csv": ",".join(sorted(units)),
                    "parent_chapter": values[0]["section"].split(".")[0],
                    "strategy": strategy,
                },
            )
        )
    return chunks


def make_store(workflow, chunks, backend):
    if backend == "offline":
        return InMemoryVectorStore(chunks)
    if backend != "chroma":
        raise ValueError("Unknown retrieval backend")
    from occupational_fitness_rag.indexing.local_chroma import build_local_chroma

    settings = workflow.config.retrieval.model_copy(update={"collection_name": "aftd_indicators"})
    identity = digest([workflow.catalogue.index_sha256, [c.to_record() for c in chunks]])
    store = build_local_chroma(workflow.root, settings, identity)
    store.add(chunks)
    return store


class IndicatorRetriever:
    def __init__(self, workflow, backend=None, strategy="unit"):
        self.workflow = workflow
        self.backend = backend or (
            "chroma" if workflow.config.retrieval.mode == "chroma" else "offline"
        )
        self.chunks = knowledge_chunks(workflow.book, workflow.catalogue, strategy)
        self.store = make_store(workflow, self.chunks, self.backend)

    def retrieve(self, request, method="hybrid"):
        if method not in {"vector", "bm25", "hybrid"}:
            raise ValueError("Unknown retrieval method")
        filters = {
            "module": request.module,
            "licence_context": "commercial",
            "source_version": "AP-G56-22",
            "index_sha256": self.workflow.catalogue.index_sha256,
        }
        engine = RetrievalEngine(
            self.store,
            RetrievalSettings(
                candidate_k=max(20, request.top_k),
                bm25_k=max(30, request.top_k),
                top_k=request.top_k,
                use_bm25=method != "vector",
                use_vector=method != "bm25",
            ),
        )
        # Category belongs in the filter; the query contains only the actual indicator text.
        hits = engine.retrieve(request.indicator_text, filters)
        citations, ranked, seen = [], [], set()
        for rank, hit in enumerate(hits, 1):
            if any(str(hit.doc.metadata.get(k)) != v for k, v in filters.items()):
                raise ValueError("Indicator retrieval crossed its metadata boundary")
            source_ids = hit.doc.metadata["source_ids_csv"].split(",")
            ranked.append(
                {
                    "rank": rank,
                    "chunk_id": hit.doc.chunk_id,
                    "source_ids": source_ids,
                    "score": hit.score,
                    "vector_score": hit.vector_score,
                    "bm25_score": hit.bm25_score,
                }
            )
            for sid in source_ids:
                if sid not in seen:
                    citations.append(
                        self.workflow.catalogue.citation(sid, hit.score, "retrieval_rank")
                    )
                    seen.add(sid)
        related = []
        if request.expand_references:
            for citation in citations:
                for sid in citation.cross_references:
                    if sid not in seen:
                        related.append(
                            self.workflow.catalogue.citation(sid, 1, "catalogue_reference")
                        )
                        seen.add(sid)
        return IndicatorEvidence(
            case_id=request.case_id,
            indicator_id=request.indicator_id,
            module=request.module,
            query=request.indicator_text,
            source_document=request.source_document,
            source_text_sha256=sha256_bytes(request.source_text.encode("utf-8")),
            start=request.start,
            end=request.end,
            index_sha256=self.workflow.catalogue.index_sha256,
            backend=self.backend,
            status="candidates_found" if citations else "no_candidates",
            citations=citations,
            related_citations=related,
            ranked_candidates=ranked,
            filters=filters,
        )
