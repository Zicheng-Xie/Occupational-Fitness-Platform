from occupational_fitness_rag.indexing.memory_store import InMemoryVectorStore
from occupational_fitness_rag.retrieval.engine import RetrievalEngine


def test_hybrid_retrieval_returns_relevant_filtered_docs(settings, synthetic_chunks):
    engine = RetrievalEngine(InMemoryVectorStore(synthetic_chunks), settings.retrieval)
    results = engine.retrieve(
        "commercial hypertension blood pressure assessment",
        {
            "category": "cardiovascular",
            "subcondition": "hypertension",
            "licence_context": "commercial",
        },
    )
    assert results
    assert results[0].doc.chunk_id == "c1"
    assert all(item.doc.metadata["licence_context"] == "commercial" for item in results)
