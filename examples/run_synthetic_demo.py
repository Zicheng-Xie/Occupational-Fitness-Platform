from occupational_fitness_rag.indexing.memory_store import InMemoryVectorStore
from occupational_fitness_rag.ingestion.models import GuidelineChunk
from occupational_fitness_rag.pipeline.austroads_rag import AustroadsRAGPipeline
from occupational_fitness_rag.retrieval.engine import RetrievalEngine
from occupational_fitness_rag.schemas.rule_result import RuleResult
from occupational_fitness_rag.settings import (
    AppSettings,
    ChunkingSettings,
    IndexSettings,
    RetrievalSettings,
    RoutingSettings,
    SourceSettings,
)

settings = AppSettings(
    source=SourceSettings("Synthetic Guideline", "demo-v1", "Demo", "commercial"),
    index=IndexSettings("memory", "unused", "demo"),
    retrieval=RetrievalSettings(candidate_k=10, bm25_k=10, top_k=2, use_bm25=True),
    routing=RoutingSettings(("rag_review", "human_review"), "short_circuit"),
    chunking=ChunkingSettings(),
    annotations_file="unused",
    pilot_modules=("hypertension", "vision", "hearing", "blackout", "diabetes"),
)

metadata = {
    "source_name": "Synthetic Guideline",
    "source_version": "demo-v1",
    "category": "cardiovascular",
    "subcondition": "hypertension",
    "licence_context": "commercial",
}
chunks = [
    GuidelineChunk(
        "demo-c1",
        "commercial hypertension blood pressure assessment",
        "1.1",
        "Hypertension",
        [10],
        metadata,
    ),
    GuidelineChunk(
        "demo-c2",
        "commercial hypertension follow-up monitoring",
        "1.2",
        "Monitoring",
        [11],
        metadata,
    ),
]

pipeline = AustroadsRAGPipeline(
    RetrievalEngine(InMemoryVectorStore(chunks), settings.retrieval), settings
)
rule_result = RuleResult(
    case_id="synthetic-demo",
    category="cardiovascular",
    subcondition="hypertension",
    flags=["complex_case"],
    route="rag_review",
)
print(pipeline.run(rule_result).model_dump_json(indent=2))
