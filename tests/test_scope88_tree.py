"""Native branch coverage, actual-call import and restart contracts."""

import json
from copy import deepcopy

import pytest

from tools import run_scope88_tree as tree


def fixture():
    units = {
        f"s{i}": {"source_id": f"s{i}", "module": "vision", "evidence_text": f"Whole original {i}."}
        for i in (1, 2, 3)
    }
    leaves = {
        f"n{i}": {
            "source_id": f"s{i}",
            "node_id": f"n{i}",
            "section": "10.2",
            "pdf_page": 220,
            "title": f"Source {i}",
        }
        for i in (1, 2, 3)
    }
    mapping = {
        "leaves": leaves,
        "branches": [
            {"node_id": "b1", "title": "PDF 220", "leaf_node_ids": ["n1"]},
            {"node_id": "b2", "title": "PDF 221", "leaf_node_ids": ["n2", "n3"]},
        ],
    }
    query = {
        "query_id": "new-query",
        "case_id": "synthetic",
        "module": "vision",
        "query": "Frozen documented findings.",
    }
    config = tree.native.settings(
        {
            "model": "test-model",
            "endpoint": "http://127.0.0.1:11434",
            "expected_model_digest": "test",
            "expected_runtime_version": "test",
        }
    )
    return query, mapping, units, config


def raw(field, ids):
    return {
        "done": True,
        "done_reason": "stop",
        "prompt_eval_count": 10,
        "message": {"content": json.dumps({field: ids})},
    }


def test_rrf_seeds_broaden_actual_tree_branches_without_new_sources():
    q, mapping, units, config = fixture()
    body, field, allowed, excluded, sources, branches = tree.ranking_body(
        q, mapping, units, config, ["b1"], ["s2", "s3"]
    )
    assert sources == ["s2", "s3", "s1"]
    assert branches == ["b1", "b2"]
    assert allowed == {"n1", "n2", "n3"} and excluded == []
    assert body["format"]["properties"][field]["minItems"] == 3
    actual = json.loads(body["messages"][1]["content"])["originals"]
    assert all(v["original_text"] == units[v["source_id"]]["evidence_text"] for v in actual)


def test_unknown_seed_cannot_be_inferred_from_a_section():
    q, mapping, units, config = fixture()
    with pytest.raises(ValueError, match="actual same-module"):
        tree.ranking_body(q, mapping, units, config, ["b1"], ["quarantined-source"])


def test_byte_cap_excludes_whole_original_and_never_truncates_it():
    q, mapping, units, config = fixture()
    units["s2"]["evidence_text"] = "X" * 20001
    body, _, _, excluded, sources, _ = tree.ranking_body(
        q, mapping, units, config, ["b1"], ["s2", "s3"]
    )
    assert "n2" in excluded and "s2" not in sources
    assert "X" * 100 not in body["messages"][1]["content"]


def test_predicate_prompt_is_an_explicit_separate_ablation():
    q, mapping, units, config = fixture()
    plain = tree.ranking_body(q, mapping, units, config, ["b1"], ["s2"])[0]
    revised = tree.ranking_body(q, mapping, units, config, ["b1"], ["s2"], True)[0]
    expected = deepcopy(plain)
    expected["messages"][0]["content"] += tree.PREDICATE_INSTRUCTION
    assert revised == expected


def test_restart_reuses_one_exact_actual_call_and_rejects_changed_request(tmp_path, monkeypatch):
    q, mapping, units, config = fixture()
    body, field, allowed, *_ = tree.ranking_body(q, mapping, units, config, ["b1"])
    observed = []
    monkeypatch.setattr(
        tree.native, "local_json", lambda *args: observed.append(args) or raw(field, ["n1"])
    )
    assert tree.call(tmp_path, q, body, field, allowed, config, "test-ranking")[0] == ["n1"]
    assert tree.call(tmp_path, q, body, field, allowed, config, "test-ranking")[0] == ["n1"]
    assert len(observed) == 1
    changed = deepcopy(body)
    changed["messages"][0]["content"] += "changed"
    with pytest.raises(ValueError, match="changed requests"):
        tree.call(tmp_path, q, changed, field, allowed, config, "test-ranking")


def test_import_uses_exact_context_with_rebound_query_id_and_skips_old_underfill():
    q, mapping, units, config = fixture()
    branch_body, field, _, _ = tree.native.request_body(q, mapping, units, config, "branches")
    rank_body, rank_field, *_ = tree.ranking_body(q, mapping, units, config, ["b2"])
    base = {"query_id": "old-query", "status": "completed"}
    calls = [
        {**base, "phase": "branches", "request": branch_body, "raw_response": raw(field, ["b2"])},
        {
            **base,
            "phase": "originals",
            "request": rank_body,
            "raw_response": raw(rank_field, ["n2"]),
        },
        {
            **base,
            "phase": "originals_strict_cardinality",
            "request": rank_body,
            "raw_response": raw(rank_field, ["n3", "n2"]),
        },
    ]
    parent = {
        "old-query": {
            "status": "completed",
            "source_ids": ["s3", "s2"],
            "selected_leaf_node_ids": ["n3", "n2"],
            "selected_branch_node_ids": ["b2"],
        }
    }
    row, used = tree.imported_control(q, "old-query", mapping, units, config, parent, calls)
    assert row == parent["old-query"] and used[-1] == calls[-1]
