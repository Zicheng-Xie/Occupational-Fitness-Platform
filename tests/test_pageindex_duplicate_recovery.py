import json
from copy import deepcopy

import pytest

from tools import pageindex_extension_worker as worker
from tools import recover_pageindex_duplicates as recovery


def fixture():
    config = worker.settings(
        {
            "endpoint": "http://127.0.0.1:11434",
            "model": "local",
            "expected_model_digest": "digest",
            "expected_runtime_version": "fixed",
        }
    )
    body = {
        "options": {"num_predict": 512},
        "format": {"properties": {"branch_ids": {"maxItems": 3}}},
    }
    observed = {
        "phase": "branches",
        "provider_called": True,
        "status": "failed",
        "request": body,
        "request_sha256": worker.digest(body),
        "raw_response": {
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 100,
            "message": {"content": json.dumps({"branch_ids": ["page2", "page1", "page2"]})},
        },
    }
    return observed, body, {"page1", "page2"}, config


def test_normalization_preserves_order_records_removed_positions_and_never_edits_raw():
    observed, body, allowed, config = fixture()
    before = deepcopy(observed)
    result = recovery.normalize_branch_call(observed, body, allowed, config)
    assert result["normalized_branch_ids"] == ["page2", "page1"]
    assert result["raw_branch_ids"] == ["page2", "page1", "page2"]
    assert result["removed_duplicate_ids"] == [{"raw_index": 2, "native_node_id": "page2"}]
    assert observed == before


@pytest.mark.parametrize("ids", [["page1", "leaf", "leaf"], ["page1"] * 4, ["page1", "page2"], []])
def test_unknown_excessive_unique_or_empty_outputs_are_not_recoverable(ids):
    observed, body, allowed, config = fixture()
    observed["raw_response"]["message"]["content"] = json.dumps({"branch_ids": ids})
    with pytest.raises(ValueError):
        recovery.normalize_branch_call(observed, body, allowed, config)


@pytest.mark.parametrize(
    "change", ["incomplete", "overflow", "request", "fingerprint", "not_actual"]
)
def test_actual_completion_context_and_exact_request_are_required(change):
    observed, body, allowed, config = fixture()
    if change == "incomplete":
        observed["raw_response"]["done_reason"] = "length"
    elif change == "overflow":
        observed["raw_response"]["prompt_eval_count"] = config["context_length"]
    elif change == "request":
        observed["request"] = {"different": True}
    elif change == "fingerprint":
        observed["request_sha256"] = "wrong"
    else:
        observed["provider_called"] = False
    with pytest.raises(ValueError):
        recovery.normalize_branch_call(observed, body, allowed, config)


def test_parent_artifact_membership_and_hashes_must_remain_frozen(tmp_path):
    original = tmp_path / "result.json"
    original.write_text("{}", encoding="utf-8")
    worker.save(tmp_path / "artifacts.json", {"result.json": worker.file_hash(original)})
    recovery.pinned_directory(tmp_path)
    (tmp_path / "unfrozen.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="membership"):
        recovery.pinned_directory(tmp_path)


def test_recovered_sources_must_match_new_actual_ranking_and_original_hashes():
    _, _, _, config = fixture()
    query = {"query_id": "q", "module": "hearing", "query": "Hearing test pending"}
    units = {"s": {"evidence_text": "Full original criterion.", "text_sha256": "original-pin"}}
    mapping = {
        "branches": [{"node_id": "page1", "leaf_node_ids": ["leaf1"]}],
        "leaves": {"leaf1": {"node_id": "leaf1", "source_id": "s"}},
    }
    normalization = {"normalized_branch_ids": ["page1"]}
    body, _, _, excluded = worker.request_body(
        query, mapping, units, config, "originals", ["page1"]
    )
    call = {
        "query_id": "q",
        "phase": "originals",
        "request": body,
        "request_sha256": worker.digest(body),
        "status": "completed",
        "provider_called": True,
        "selected_native_node_ids": ["leaf1"],
        "raw_response": {
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 100,
            "message": {"content": json.dumps({"node_ids": ["leaf1"]})},
        },
    }
    row = {
        "experiment_identity": "new-run",
        "selected_branch_node_ids": ["page1"],
        "selected_leaf_node_ids": ["leaf1"],
        "branch_normalization": normalization,
        "status": "completed",
        "source_ids": ["s"],
        "original_text_hashes": {"s": "original-pin"},
        "excluded_native_nodes_by_navigation_budget": excluded,
    }
    recovery.validate_recovered(
        row, query, mapping, units, config, [call], normalization, "new-run"
    )
    row["source_ids"] = ["invented-source"]
    with pytest.raises(ValueError, match="actual native"):
        recovery.validate_recovered(
            row, query, mapping, units, config, [call], normalization, "new-run"
        )
