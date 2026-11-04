"""Graph summaries or unknown IDs must not silently become original evidence."""

import pytest

from occupational_fitness_rag.evaluation.graph_worker import map_original_sources


def test_original_order_is_retained_while_duplicate_document_hits_are_deduplicated():
    rows = [{"id": 2}, {"id": 1}, {"id": 3}]
    assert map_original_sources(rows, {"1": ["a"], "2": ["b"], "3": ["b"]}, {"a", "b"}, 5) == ["b", "a"]


def test_unknown_short_id_below_the_top_k_cut_is_still_a_failure():
    with pytest.raises(ValueError, match="unknown text-unit"):
        map_original_sources([{"id": 1}, {"id": 999}], {"1": ["a"]}, {"a"}, 1)


@pytest.mark.parametrize("mapping", [{"1": []}, {"1": ["foreign-module"]}, {"1": [["a"]]}])
def test_empty_or_foreign_document_mappings_are_rejected(mapping):
    with pytest.raises(ValueError, match="unknown|unmapped|out-of-module"):
        map_original_sources([{"id": 1}], mapping, {"a"}, 5)


def test_empty_framework_context_is_an_empty_result_not_a_fabricated_fallback():
    assert map_original_sources([], {"1": ["a"]}, {"a"}, 5) == []
