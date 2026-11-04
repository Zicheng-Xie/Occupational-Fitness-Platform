import hashlib
import json
from copy import deepcopy

import pytest

from tools import pageindex_extension_worker as worker


def fixtures():
    text = (
        "Commercial standard.\n### This is original source wording.\nAdditional conditions apply."
    )
    units = {
        "source-1": {
            "source_id": "source-1",
            "module": "vision",
            "section": "10.3",
            "pdf_page": 220,
            "licence_context": "commercial",
            "table_row": "Visual acuity",
            "evidence_text": text,
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        },
        "source-2": {
            "source_id": "source-2",
            "module": "vision",
            "section": "10.3",
            "pdf_page": 220,
            "licence_context": "shared",
            "evidence_text": "The original qualification remains in full.",
            "text_sha256": hashlib.sha256(
                b"The original qualification remains in full."
            ).hexdigest(),
        },
    }
    tree = {
        "structure": [
            {
                "title": "vision",
                "node_id": "root",
                "text": "",
                "nodes": [
                    {
                        "title": "Section 10.3",
                        "node_id": "section",
                        "text": "",
                        "nodes": [
                            {
                                "title": "PDF 220",
                                "node_id": "page",
                                "text": "",
                                "nodes": [
                                    {
                                        "title": sid + " | Original",
                                        "node_id": "n" + str(i),
                                        "text": u["evidence_text"],
                                    }
                                    for i, (sid, u) in enumerate(units.items())
                                ],
                            }
                        ],
                    }
                ],
            }
        ]
    }
    config = worker.settings(
        {
            "endpoint": "http://127.0.0.1:11434",
            "model": "local",
            "expected_model_digest": "digest",
            "expected_runtime_version": "fixed",
        }
    )
    query = {
        "query_id": "q",
        "case_id": "c",
        "module": "vision",
        "licence_context": "commercial",
        "query": "diplopia present=false, recent history, uncorrected acuity unknown",
    }
    return units, tree, config, query


def test_native_mapping_preserves_originals_and_pdf_provenance():
    units, tree, _, _ = fixtures()
    mapping = worker.map_native_tree("vision", tree, units)
    assert mapping["branches"][0]["leaf_node_ids"] == ["n0", "n1"]
    assert {v["source_id"] for v in mapping["leaves"].values()} == set(units)
    markdown = worker.markdown_document("vision", units)
    assert "```text\n" + units["source-1"]["evidence_text"] + "\n```" in markdown
    assert markdown.count("#### source-") == 2


@pytest.mark.parametrize(
    "change", ["unknown_source", "changed_page", "missing_original", "missing_unit"]
)
def test_native_mapping_rejects_identity_or_original_text_drift(change):
    units, tree, _, _ = fixtures()
    page = tree["structure"][0]["nodes"][0]["nodes"][0]
    if change == "unknown_source":
        page["nodes"][0]["title"] = "unknown | Original"
    elif change == "changed_page":
        page["title"] = "PDF 221"
    elif change == "missing_original":
        page["nodes"][0]["text"] = "Model paraphrase of the original"
    else:
        page["nodes"].pop()
    with pytest.raises(ValueError):
        worker.map_native_tree("vision", tree, units)


def test_navigation_budget_excludes_whole_units_without_truncating_evidence():
    units, tree, config, query = fixtures()
    mapping = worker.map_native_tree("vision", tree, units)
    body, _, allowed, _ = worker.request_body(query, mapping, units, config, "originals", ["page"])
    sources = json.loads(body["messages"][1]["content"])["originals"]
    one_size = len(json.dumps(sources[:1], ensure_ascii=False).encode())
    config["candidate_max_bytes"] = one_size
    body, _, allowed, excluded = worker.request_body(
        query, mapping, units, config, "originals", ["page"]
    )
    assert allowed == {"n0"} and excluded == ["n1"]
    assert (
        json.loads(body["messages"][1]["content"])["originals"][0]["original_text"]
        == units["source-1"]["evidence_text"]
    )


def test_branch_schema_cannot_select_visible_native_leaf_ids():
    units, tree, config, query = fixtures()
    mapping = worker.map_native_tree("vision", tree, units)
    body, field, allowed, _ = worker.request_body(query, mapping, units, config, "branches")
    rule = body["format"]["properties"][field]
    assert rule["items"]["enum"] == ["page"]
    assert rule["uniqueItems"] is True and rule["maxItems"] == 1
    visible_tree = json.loads(body["messages"][1]["content"])["native_tree"]
    assert visible_tree[0]["leaves"][0]["node_id"] == "n0"
    assert "n0" not in rule["items"]["enum"]
    raw = {
        "done": True,
        "done_reason": "stop",
        "prompt_eval_count": 100,
        "message": {"content": '{"branch_ids":["n0"]}'},
    }
    with pytest.raises(ValueError, match="unknown, repeated or excessive"):
        worker.parse_selection(raw, body, field, allowed, config)


def test_final_schema_enum_uses_only_originals_actually_supplied_after_budget():
    units, tree, config, query = fixtures()
    mapping = worker.map_native_tree("vision", tree, units)
    body, field, allowed, _ = worker.request_body(
        query, mapping, units, config, "originals", ["page"]
    )
    sources = json.loads(body["messages"][1]["content"])["originals"]
    config["candidate_max_bytes"] = len(json.dumps(sources[:1], ensure_ascii=False).encode())
    body, field, allowed, excluded = worker.request_body(
        query, mapping, units, config, "originals", ["page"]
    )
    assert body["format"]["properties"][field]["items"]["enum"] == ["n0"]
    assert allowed == {"n0"} and excluded == ["n1"]


@pytest.mark.parametrize("ids", [["not-supplied"], ["n0", "n0"], [{"id": "n0"}], [], "n0"])
def test_invalid_model_node_selections_fail_without_source_fallback(ids):
    units, tree, config, query = fixtures()
    mapping = worker.map_native_tree("vision", tree, units)
    body, field, allowed, _ = worker.request_body(
        query, mapping, units, config, "originals", ["page"]
    )
    raw = {
        "done": True,
        "done_reason": "stop",
        "prompt_eval_count": 100,
        "message": {"content": json.dumps({"node_ids": ids})},
    }
    with pytest.raises(ValueError):
        worker.parse_selection(raw, body, field, allowed, config)


def test_context_overflow_and_incomplete_completions_are_rejected():
    units, tree, config, query = fixtures()
    mapping = worker.map_native_tree("vision", tree, units)
    body, field, allowed, _ = worker.request_body(query, mapping, units, config, "branches")
    raw = {
        "done": True,
        "done_reason": "stop",
        "prompt_eval_count": 8000,
        "message": {"content": '{"branch_ids":["page"]}'},
    }
    with pytest.raises(ValueError, match="context"):
        worker.parse_selection(raw, body, field, allowed, config)
    raw.update(prompt_eval_count=100, done_reason="length")
    with pytest.raises(ValueError, match="incomplete"):
        worker.parse_selection(raw, body, field, allowed, config)


def test_foreign_licence_and_cloud_transport_are_rejected():
    units, _, config, query = fixtures()
    changed = deepcopy(config)
    changed["endpoint"] = "https://example.com"
    with pytest.raises(ValueError, match="local IPv4"):
        worker.settings(changed)
    units["source-1"]["licence_context"] = "private"
    with pytest.raises(ValueError, match="commercial/shared"):
        worker.validate_inputs({"units": list(units.values())}, [query])


def test_saved_selection_requires_matching_actual_observed_calls():
    units, tree, config, query = fixtures()
    mappings = {"vision": worker.map_native_tree("vision", tree, units)}
    calls = []
    for phase, selected in [("branches", ["page"]), ("originals", ["n1", "n0"])]:
        body, field, _, excluded = worker.request_body(
            query,
            mappings["vision"],
            units,
            config,
            phase,
            ["page"] if phase == "originals" else None,
        )
        calls.append(
            {
                "query_id": "q",
                "phase": phase,
                "status": "completed",
                "provider_called": True,
                "request": body,
                "request_sha256": worker.digest(body),
                "selected_native_node_ids": selected,
                "raw_response": {
                    "done": True,
                    "done_reason": "stop",
                    "prompt_eval_count": 100,
                    "message": {"content": json.dumps({field: selected})},
                },
            }
        )
    row = {
        "query_id": "q",
        "case_id": "c",
        "module": "vision",
        "method": worker.METHOD,
        "experiment_identity": "run",
        "status": "completed",
        "source_ids": ["source-2", "source-1"],
        "selected_branch_node_ids": ["page"],
        "selected_leaf_node_ids": ["n1", "n0"],
        "excluded_native_nodes_by_navigation_budget": excluded,
        "original_text_hashes": {sid: u["text_sha256"] for sid, u in units.items()},
    }
    worker.audit_results([row], [query], mappings, units, config, calls, "run")
    calls[1]["request"]["messages"][1]["content"] = '{"reference_answer":"source-2"}'
    with pytest.raises(ValueError, match="Observed navigation request"):
        worker.audit_results([row], [query], mappings, units, config, calls, "run")
