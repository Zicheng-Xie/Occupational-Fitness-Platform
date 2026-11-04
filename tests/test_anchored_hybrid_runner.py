import json

import pytest

from occupational_fitness_rag.provenance import digest, write_json
from tools import run_anchored_hybrid as runner


def test_imported_artifact_tampering_is_rejected(tmp_path):
    data = {"kind": "retrieval", "config": {"model": "fixed"}}
    write_json(
        tmp_path / "manifest.json", {**data, "identity": digest(data), "production_change": False}
    )
    write_json(
        tmp_path / "artifacts.json", {"manifest.json": runner.file_hash(tmp_path / "manifest.json")}
    )
    runner.verify_saved(tmp_path)
    write_json(tmp_path / "manifest.json", {**data, "identity": "changed"})
    with pytest.raises(ValueError, match="artifact changed"):
        runner.verify_saved(tmp_path)


def test_facet_cache_requires_actual_matching_call(tmp_path, monkeypatch):
    (tmp_path / "query_records").mkdir()
    body = {"model": "embed", "input": ["exact patient quote = false"], "truncate": False}
    manifest = {"identity": "parent", "config": {"embedding_model": "embed"}}
    vectors = [[0.2, 0.3]]
    write_json(
        tmp_path / "query_records/q.embedding.json",
        {
            "key": digest({"identity": "parent", "request": body}),
            "vectors": vectors,
        },
    )
    call = {
        "query_id": "q",
        "request": body,
        "request_sha256": digest(body),
        "status": "completed",
        "raw_response": {"embeddings": vectors},
    }
    (tmp_path / "model_calls.jsonl").write_text(json.dumps(call) + "\n", encoding="utf-8")

    def fake_execute(query, patient, corpus, saved_vectors, anchor, embed, config):
        assert embed(body["input"]) == vectors
        return {
            "events": [
                {"stage": "search", "channels": []},
                {"stage": "refine", "keyword_only_followups": []},
            ]
        }

    monkeypatch.setattr(runner, "execute_plan", fake_execute)
    queries = [
        {
            "query_id": "q",
            "case_id": "c",
            "module": "vision",
            "query_audit": {"query_sha256": "query"},
        }
    ]
    rows = [
        {
            "query_id": "q",
            "case_id": "c",
            "module": "vision",
            "query_sha256": "query",
            "status": "completed",
            "experiment_identity": "parent",
            "events": [
                {"stage": "search", "channels": []},
                {"stage": "refine", "keyword_only_followups": []},
            ],
        }
    ]
    args = (tmp_path, manifest, rows, {}, queries, {"c": {}}, [], {"q": []})
    assert runner.reconstruct_channels(*args) == {"q": []}
    # A retained vector and a plausible request hash alone are insufficient.
    # The actual request body must also contain the exact literal input.
    call["request"] = {**body, "input": ["different patient = true"]}
    (tmp_path / "model_calls.jsonl").write_text(json.dumps(call) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="actual recorded"):
        runner.reconstruct_channels(*args)


def test_refinement_already_serialized_in_search_is_not_counted_twice(tmp_path, monkeypatch):
    (tmp_path / "model_calls.jsonl").write_text("", encoding="utf-8")
    followup = {"channel": "followup:facet", "kind": "bm25", "query": "literal", "hits": []}
    events = [
        {"stage": "search", "channels": [followup]},
        {"stage": "refine", "keyword_only_followups": [followup]},
    ]
    monkeypatch.setattr(runner, "execute_plan", lambda *args: {"events": events})
    query = {
        "query_id": "q",
        "case_id": "c",
        "module": "vision",
        "query_audit": {"query_sha256": "q"},
    }
    row = {
        "query_id": "q",
        "case_id": "c",
        "module": "vision",
        "query_sha256": "q",
        "status": "completed",
        "experiment_identity": "parent",
        "events": events,
    }
    actual = runner.reconstruct_channels(
        tmp_path, {"config": {}, "identity": "parent"}, [row], {}, [query], {"c": {}}, [], {"q": []}
    )
    assert actual == {"q": [followup]}


def test_repeated_parent_query_is_not_an_independent_ranking(tmp_path):
    (tmp_path / "model_calls.jsonl").write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="incomplete or repeated"):
        runner.reconstruct_channels(
            tmp_path, {"config": {}}, [{"query_id": "q"}] * 2, {}, [{"query_id": "q"}], {}, [], {}
        )
