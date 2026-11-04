"""A shared query must retain method identity and its strict disease filter."""

from types import SimpleNamespace

import pytest

from occupational_fitness_rag.indexing.base import StoredDocument
from tools.run_shared_retrieval import rank_method


def test_dense_sparse_and_rrf_are_distinct_rankings_on_the_same_filtered_inputs():
    docs = [StoredDocument("a", "keyword", {"module": "vision"}),
            StoredDocument("b", "semantic", {"module": "vision"}),
            StoredDocument("outside", "keyword keyword", {"module": "hearing"})]
    vectors = [[0, 1], [1, 0], [1, 0]]
    units = {d.chunk_id: {"module": d.metadata["module"]} for d in docs}
    def ids(method):
        return [r["source_id"] for r in rank_method("keyword", "vision", method, docs, vectors, [1, 0], units, SimpleNamespace(rules=[]), 10)]
    assert ids("vector") == ["b", "a"]
    assert ids("bm25") == ["a"]
    assert set(ids("hybrid")) == {"a", "b"}
    assert "outside" not in ids("hybrid")


def test_failed_embedding_does_not_silently_replace_vector_retrieval_with_bm25():
    docs = [StoredDocument("a", "keyword", {"module": "vision"})]
    assert rank_method("keyword", "vision", "bm25", docs, [], None, {}, None, 5)
    with pytest.raises(ValueError, match="no lexical fallback"):
        rank_method("keyword", "vision", "vector", docs, [], None, {}, None, 5)
    with pytest.raises(ValueError, match="No substitute"):
        rank_method("keyword", "vision", "graphrag", docs, [], None, {}, None, 5)
