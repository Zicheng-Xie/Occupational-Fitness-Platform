from copy import deepcopy

import pytest

from tools.report_guarded_hybrid import guard_audit, top10_changes
from tools.run_guarded_hybrid import freeze_rankings


def fixture():
    units = [
        {
            "source_id": sid,
            "module": "vision",
            "licence_context": "commercial",
            "evidence_text": "Original visual criterion " + sid,
            "covers_source_ids": [sid],
            "text_sha256": "hash-" + sid,
        }
        for sid in "AB"
    ]
    queries = [
        {
            "query_id": "q",
            "case_id": "case",
            "module": "vision",
            "query_audit": {"query_sha256": "literal-query"},
        }
    ]
    channels = [
        {
            "channel": "anchor:" + kind,
            "kind": kind,
            "query": "literal source query",
            "hits": [{"source_id": sid, "score": 1.0} for sid in "AB"],
        }
        for kind in ("vector", "bm25")
    ]
    config = {"variants": [{"method": "new-seventh", "policy": "guarded_coverage"}]}
    return config, {"units": units}, queries, {"q": channels}


def test_real_ranking_interface_keeps_original_fingerprints_and_frozen_query():
    args = fixture()
    original = deepcopy(args)
    rows = freeze_rankings(*args, "identity")
    assert original == args
    assert len(rows) == 1 and rows[0]["status"] == "completed"
    assert rows[0]["source_ids"] == ["A", "B"]
    assert rows[0]["original_text_hashes"] == {"A": "hash-A", "B": "hash-B"}
    assert rows[0]["query_sha256"] == "literal-query"
    assert rows[0]["experiment_identity"] == "identity"
    assert rows[0]["diagnostics"]["protected_coverage_retained"]


def test_scope_failure_is_recorded_without_a_retrieval_fallback():
    config, corpus, queries, channels = fixture()
    corpus["units"][0]["module"] = "diabetes"
    rows = freeze_rankings(config, corpus, queries, channels, "identity")
    assert rows[0]["status"] == "failed" and rows[0]["source_ids"] == []
    assert "ValueError" in rows[0]["error"]


def test_report_guard_uses_actual_original_ranks_and_rejects_an_invented_floor():
    config, corpus, queries, channels = fixture()
    rows = freeze_rankings(config, corpus, queries, channels, "identity")
    units = {u["source_id"]: u for u in corpus["units"]}
    original = [{"query_id": "q", "method": "hybrid", "source_ids": ["A", "B"]}]
    assert guard_audit(rows, original, units)[0]["protected_coverage_retained"]
    changed = deepcopy(rows)
    changed[0]["diagnostics"]["original_rrf_source_ids"] = ["A"]
    with pytest.raises(ValueError, match="actual original hybrid"):
        guard_audit(changed, original, units)
    changed = deepcopy(rows)
    changed[0]["source_ids"] = ["A"]
    with pytest.raises(ValueError, match="lost an actual"):
        guard_audit(changed, original, units)


def test_top10_changes_do_not_invent_relevance_labels_for_unknown_scopes():
    rows = [
        {
            "query_id": qid,
            "case_id": qid,
            "module": "vision",
            "method": method,
            "coverage_recall_10": value,
        }
        for qid, left, right in (
            ("improvement", 0.5, 1.0),
            ("unlabeled", None, None),
            ("regression", 1.0, 0.5),
        )
        for method, value in (("hybrid", left), ("new", right))
    ]
    result = top10_changes(rows, "hybrid", "new")
    assert result["counts"] == {"improved": 1, "unlabeled": 1, "regressed": 1}
