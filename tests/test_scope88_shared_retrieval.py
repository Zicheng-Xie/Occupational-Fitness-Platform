"""Reviewed retrieval must reuse actual vectors without reusing old rankings."""

from copy import deepcopy

import pytest

from occupational_fitness_rag.provenance import digest, write_json
from tools.run_scope88_shared_retrieval import (
    deduplicate_channels,
    facet_embedder,
    rebind_queries,
    subset_vectors,
)


def test_corpus_rebinding_changes_only_query_metadata_and_keeps_actual_vector():
    query = {
        "query": "No current blackout",
        "corpus_sha256": "old94",
        "query_audit": {"query_sha256": "literal-pin", "field_values": {"blackout.history": False}},
    }
    query["query_id"] = digest(query)
    before = deepcopy(query)
    result, lineage, vectors = rebind_queries([query], "new88", {query["query_id"]: [0.2, 0.8]})
    assert query == before
    new = result[0]
    assert new["corpus_sha256"] == "new88" and new["query_id"] != query["query_id"]
    assert new["query"] == query["query"] and new["query_audit"] == query["query_audit"]
    assert digest({k: v for k, v in new.items() if k != "query_id"}) == new["query_id"]
    assert lineage[new["query_id"]]["parent_query_id"] == query["query_id"]
    assert lineage[new["query_id"]]["query_audit_sha256"] == digest(query["query_audit"])
    assert vectors == {new["query_id"]: [0.2, 0.8]}


def test_subset_vectors_preserves_reviewed_order_and_exact_original_identity():
    original = {
        "document_sha256": "pdf",
        "units": [
            {"source_id": "a", "evidence_text": "Original A"},
            {"source_id": "b", "evidence_text": "Original B"},
            {"source_id": "c", "evidence_text": "Original C"},
        ],
    }
    revised = {"document_sha256": "pdf", "units": [original["units"][2], original["units"][0]]}
    assert subset_vectors(original, revised, [[1, 0], [0, 1], [1, 1]]) == [[1, 1], [1, 0]]
    revised = deepcopy(revised)
    revised["units"][0]["evidence_text"] = "An edited passage must be re-embedded"
    with pytest.raises(ValueError, match="text or metadata"):
        subset_vectors(original, revised, [[1, 0], [0, 1], [1, 1]])


@pytest.mark.parametrize("problem", ["duplicate", "unknown", "not_subset", "document"])
def test_invalid_reviewed_vector_reuse_is_rejected(problem):
    original = {"document_sha256": "pdf", "units": [{"source_id": "a"}, {"source_id": "b"}]}
    revised = {"document_sha256": "pdf", "units": [{"source_id": "a"}]}
    if problem == "duplicate":
        revised["units"] *= 2
    elif problem == "unknown":
        revised["units"] = [{"source_id": "unknown"}]
    elif problem == "not_subset":
        revised["units"] = original["units"]
    else:
        revised["document_sha256"] = "different PDF"
    with pytest.raises(ValueError):
        subset_vectors(original, revised, [[1, 0], [0, 1]])


def test_literal_facet_reuse_requires_the_exact_actual_request_and_response(tmp_path):
    body = {"model": "embedder", "input": ["No current blackout"], "truncate": False}
    parent = {"identity": "old", "config": {"embedding_model": "embedder"}}
    (tmp_path / "query_records").mkdir()
    cache = {"key": digest({"identity": "old", "request": body}), "vectors": [[0.2, 0.8]]}
    write_json(tmp_path / "query_records/q.embedding.json", cache)
    calls = [
        {
            "query_id": "q",
            "status": "completed",
            "request": body,
            "request_sha256": digest(body),
            "raw_response": {"embeddings": [[0.2, 0.8]]},
        }
    ]
    embed = facet_embedder(tmp_path, parent, "q", calls)
    assert embed(["No current blackout"]) == [[0.2, 0.8]]
    with pytest.raises(ValueError, match="lacks an actual"):
        embed(["Current blackout"])
    calls[0]["raw_response"]["embeddings"] = [[0.8, 0.2]]
    with pytest.raises(ValueError, match="actual recorded"):
        embed(["No current blackout"])


def test_serialized_followup_alias_is_counted_once_and_conflicts_fail():
    followup = {"channel": "followup:f", "kind": "bm25", "query": "literal", "hits": []}
    result = {
        "events": [
            {"stage": "search", "channels": [followup]},
            {"stage": "refine", "keyword_only_followups": [followup]},
        ]
    }
    assert deduplicate_channels(result) == [followup]
    result["events"][1]["keyword_only_followups"] = [{**followup, "query": "other"}]
    with pytest.raises(ValueError, match="conflicting"):
        deduplicate_channels(result)
