"""The allocation runner preserves actual parents and records failed attempts."""

from copy import deepcopy

import pytest

from tools.run_scope88_prefix_allocation import VARIANTS, freeze_rows, validate_config


def fixture():
    units = [
        {
            "source_id": str(i),
            "module": "example",
            "licence_context": "commercial",
            "evidence_text": "Original " + str(i),
            "text_sha256": "pin-" + str(i),
            "covers_source_ids": [str(i)],
            "criterion_type": "general",
        }
        for i in range(8)
    ]
    query = {
        "query_id": "q",
        "case_id": "case",
        "module": "example",
        "query_audit": {"query_sha256": "literal-pin"},
    }
    channels = {
        "q": [
            {
                "channel": "anchor:" + kind,
                "kind": kind,
                "query": "same actual query",
                "hits": [{"source_id": str(i), "score": 8 - i} for i in range(8)],
            }
            for kind in ("vector", "bm25")
        ]
    }
    return {"units": units}, [query], channels


def test_runner_freezes_three_independent_complete_conditions():
    corpus, queries, channels = fixture()
    inputs = deepcopy((corpus, queries, channels))
    rows = freeze_rows(corpus, queries, channels, "identity")
    assert len(rows) == 3
    assert all(r["status"] == "completed" for r in rows)
    assert set(rows[0]["source_ids"]) == set(rows[1]["source_ids"]) == set(rows[2]["source_ids"])
    assert all(r["experiment_identity"] == "identity" for r in rows)
    assert inputs == (corpus, queries, channels)


def test_failed_actual_parent_does_not_supply_other_evidence():
    corpus, queries, channels = fixture()
    channels["q"][0]["hits"][0]["source_id"] = "not-retrieved"
    rows = freeze_rows(corpus, queries, channels, "identity")
    assert len(rows) == 3
    assert all(r["status"] == "failed" and not r["source_ids"] for r in rows)
    assert all("error" in r for r in rows)


def test_incomplete_query_channel_inventory_fails_before_ranking():
    corpus, queries, _ = fixture()
    with pytest.raises(ValueError, match="inventory"):
        freeze_rows(corpus, queries, {}, "identity")


def test_no_unregistered_weights_or_variants_are_accepted():
    config = {
        "shared_inputs": "frozen",
        "expected_shared_identity": "pin",
        "output": "fresh",
        "primary_candidate": "scope88_prefix_criterion_v6",
        "variants": VARIANTS,
    }
    validate_config(config)
    with pytest.raises(ValueError, match="Unexpected"):
        validate_config({**config, "weight": 0.5})
    with pytest.raises(ValueError, match="predefined"):
        validate_config({**config, "variants": {"unregistered": "criterion_floor"}})
