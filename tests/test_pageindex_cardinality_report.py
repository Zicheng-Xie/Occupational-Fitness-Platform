import json

import pytest

from tools.report_retrieval_extensions import pageindex_cardinality


def test_completed_calls_and_available_cardinality_are_distinct():
    rows = [
        {"query_id": "a", "status": "completed", "source_ids": ["s1"]},
        {"query_id": "b", "status": "completed", "source_ids": ["s2", "s3"]},
    ]
    calls = [
        {
            "query_id": qid,
            "request": {"messages": [{}, {"content": json.dumps({"originals": [1, 2]})}]},
        }
        for qid in ("a", "b")
    ]
    result = pageindex_cardinality(rows, calls)
    assert result["queries_underfilled_relative_to_available_count"] == 1
    assert result["queries_with_candidate_pool_below10"] == 2
    assert result["queries_returning_fewer_than10"] == 2
    assert result["returned_original_count_distribution"] == {1: 1, 2: 1}


def test_cardinality_audit_rejects_missing_or_duplicate_observed_final_requests():
    row = {"query_id": "a", "source_ids": []}
    with pytest.raises(ValueError, match="one observed"):
        pageindex_cardinality([row], [])
