import pytest

from occupational_fitness_rag.ingestion.models import GuidelineChunk
from occupational_fitness_rag.settings import (
    AppSettings,
    ChunkingSettings,
    IndexSettings,
    RetrievalSettings,
    RoutingSettings,
    SourceSettings,
)


@pytest.fixture
def settings():
    return AppSettings(
        source=SourceSettings("Synthetic Guideline", "test-v1", "Test", "commercial"),
        index=IndexSettings("memory", "unused", "test"),
        retrieval=RetrievalSettings(candidate_k=10, bm25_k=10, top_k=3, use_bm25=True, rrf_k=60),
        routing=RoutingSettings(("rag_review", "human_review"), "short_circuit"),
        chunking=ChunkingSettings(),
        annotations_file="unused",
        pilot_modules=("hypertension", "vision", "hearing", "blackout", "diabetes"),
    )


@pytest.fixture
def synthetic_chunks():
    base = {
        "source_name": "Synthetic Guideline",
        "source_version": "test-v1",
        "jurisdiction": "Test",
        "licence_context": "commercial",
    }
    return [
        GuidelineChunk(
            "c1",
            "commercial hypertension blood pressure assessment repeated measurements",
            "1.2",
            "Hypertension",
            [10],
            {**base, "category": "cardiovascular", "subcondition": "hypertension"},
        ),
        GuidelineChunk(
            "c2",
            "commercial hypertension specialist review and monitoring evidence",
            "1.3",
            "Review",
            [11],
            {**base, "category": "cardiovascular", "subcondition": "hypertension"},
        ),
        GuidelineChunk(
            "c3",
            "commercial visual acuity assessment standard",
            "2.1",
            "Vision",
            [20],
            {**base, "category": "vision", "subcondition": "visual_acuity"},
        ),
        GuidelineChunk(
            "c4",
            "private hypertension standard should never cross commercial filter",
            "9.9",
            "Private",
            [90],
            {
                **base,
                "category": "cardiovascular",
                "subcondition": "hypertension",
                "licence_context": "private",
            },
        ),
    ]
