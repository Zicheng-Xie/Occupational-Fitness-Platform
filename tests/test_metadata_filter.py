from occupational_fitness_rag.indexing.memory_store import InMemoryVectorStore


def test_metadata_filters_run_before_similarity(synthetic_chunks):
    store = InMemoryVectorStore(synthetic_chunks)
    results = store.search(
        "hypertension blood pressure",
        {
            "category": "cardiovascular",
            "subcondition": "hypertension",
            "licence_context": "commercial",
        },
        10,
    )
    ids = {item.chunk_id for item in results}
    assert ids == {"c1", "c2"}
    assert "c4" not in ids
