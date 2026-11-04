import json
from copy import deepcopy

import pytest

from tools import pageindex_extension_worker as worker
from tools import run_pageindex_strict_cardinality as strict


def fixture(ids):
    config = worker.settings(
        {
            "endpoint": "http://127.0.0.1:11434",
            "model": "local",
            "expected_model_digest": "d",
            "expected_runtime_version": "v",
        }
    )
    body = {
        "options": {"num_predict": 1024},
        "format": {"properties": {"node_ids": {"minItems": 2, "maxItems": 2}}},
    }
    raw = {
        "done": True,
        "done_reason": "stop",
        "prompt_eval_count": 100,
        "message": {"content": json.dumps({"node_ids": ids})},
    }
    return raw, body, {"a", "b", "c"}, config


def test_exact_cardinality_uses_actual_valid_ids_without_changing_raw_response():
    raw, body, allowed, config = fixture(["b", "a"])
    original = deepcopy(raw)
    ids, audit = strict.parse_strict(raw, body, "node_ids", allowed, config)
    assert ids == ["b", "a"] and audit["removed_duplicate_ids"] == []
    assert raw == original


def test_duplicate_normalization_is_explicit_and_only_accepts_full_distinct_count():
    raw, body, allowed, config = fixture(["b", "b", "a"])
    ids, audit = strict.parse_strict(raw, body, "node_ids", allowed, config)
    assert ids == ["b", "a"]
    assert audit["removed_duplicate_ids"] == [{"raw_index": 1, "native_node_id": "b"}]
    assert audit["raw_exceeded_schema_max_items"] is True


@pytest.mark.parametrize("ids", [["a"], ["a", "a"], ["a", "b", "c"], ["a", "unknown"], []])
def test_missing_unknown_or_excess_distinct_ids_fail_instead_of_filling(ids):
    raw, body, allowed, config = fixture(ids)
    with pytest.raises(ValueError):
        strict.parse_strict(raw, body, "node_ids", allowed, config)


@pytest.mark.parametrize("change", ["incomplete", "overflow"])
def test_completion_and_context_limits_remain_strict(change):
    raw, body, allowed, config = fixture(["a", "b"])
    if change == "incomplete":
        raw["done_reason"] = "length"
    else:
        raw["prompt_eval_count"] = 8192
    with pytest.raises(ValueError):
        strict.parse_strict(raw, body, "node_ids", allowed, config)


def test_only_schema_cardinality_changes_in_original_ranking_request():
    _, _, _, config = fixture([])
    query = {"module": "vision", "query": "Blurred sight"}
    units = {"s": {"evidence_text": "Full original."}}
    mapping = {
        "branches": [{"node_id": "page", "leaf_node_ids": ["leaf"]}],
        "leaves": {"leaf": {"node_id": "leaf", "source_id": "s"}},
    }
    original, _, _, _ = worker.request_body(query, mapping, units, config, "originals", ["page"])
    changed, _, _, _, target = strict.strict_request(query, mapping, units, config, ["page"])
    assert target == 1
    expected = deepcopy(original)
    expected["format"]["properties"]["node_ids"].update(minItems=1, maxItems=1)
    assert changed == expected
