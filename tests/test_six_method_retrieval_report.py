"""Source coverage is distinct from exact ID recall and clinical agreement."""

from tools.report_six_method_retrieval import completion_quality, score


def test_expanded_original_counts_for_coverage_but_not_canonical_id():
    rows = [{"query_id": "q", "case_id": "case", "module": "hearing", "method": "lightrag",
             "status": "completed", "source_ids": ["expanded"]}]
    queries = [{"query_id": "q", "case_id": "case", "module": "hearing"}]
    references = {"case": {"reference_payload": {"guideline_evidence": [{"module": "hearing", "source_id": "canonical"}]}}}
    units = {"expanded": {"covers_source_ids": ["canonical"]}}
    scored, _ = score(rows, queries, units, references)
    assert scored[0]["exact_recall_5"] == 0
    assert scored[0]["coverage_recall_5"] == 1


def test_unlabeled_scope_has_no_invented_zero_or_success():
    rows = [{"query_id": "q", "case_id": "case", "module": "hearing", "method": "graphrag",
             "status": "completed", "source_ids": []}]
    queries = [{"query_id": "q", "case_id": "case", "module": "hearing"}]
    references = {"case": {"reference_payload": {"guideline_evidence": []}}}
    scored, metrics = score(rows, queries, {}, references)
    assert scored[0]["coverage_recall_5"] is None
    graph = next(m for m in metrics if m["method"] == "graphrag")
    assert graph["labeled_scopes"] == 0
    assert graph["coverage_recall_5"] is None


def test_failed_graph_result_is_retained_in_labeled_denominator():
    rows = [{"query_id": "q", "case_id": "case", "module": "vision", "method": "lightrag",
             "status": "index_failed", "source_ids": []}]
    queries = [{"query_id": "q", "case_id": "case", "module": "vision"}]
    references = {"case": {"reference_payload": {"guideline_evidence": [{"module": "vision", "source_id": "canonical"}]}}}
    _, metrics = score(rows, queries, {}, references)
    graph = next(m for m in metrics if m["method"] == "lightrag")
    assert graph["completed"] == 0
    assert graph["coverage_recall_5"] == 0


def test_http_success_with_length_stop_is_a_graph_quality_warning():
    calls = [{"route": "/api/chat", "raw_response": '{"done_reason":"length","eval_count":2048}',
              "phase": {"method": "lightrag", "module": "vision", "stage": "index"},
              "request": {"messages": [{"content": "Input: Original criterion text."}]}, "request_sha256": "pin"}]
    quality = completion_quality(calls, [{"module": "vision", "source_id": "source", "evidence_text": "Original criterion text."}])
    assert quality["truncated_completion_calls"] == 1
    assert quality["warnings"][0]["literal_source_text_matches"] == ["source"]
