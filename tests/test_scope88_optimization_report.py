"""Reporting must preserve scope, failure, selection and packet-allocation boundaries."""

import json
from copy import deepcopy

import pytest

from occupational_fitness_rag.provenance import digest
from tools.report_scope88_optimization import (
    BASE10,
    CANDIDATE10,
    OBSERVED10,
    canonical_rows,
    case_packet_coverage,
    case_packet_pairs,
    facts_present,
    native_index_quality,
    navigation_costs,
    packet_coverage,
    promotion,
    summarize_case_packets,
    tree_development_selection,
)


def packet_inputs():
    units = {
        "h": {"module": "hypertension"},
        "b1": {"module": "blackout"},
        "b2": {"module": "blackout"},
    }
    queries = [{"query_id": "q", "query_audit": {"field_values": {}}}]
    rows = [{"query_id": "q", "method": "method", "source_ids": ["b1", "b2"]}]
    scores = [
        {
            "query_id": "q",
            "case_id": "case",
            "module": "blackout",
            "method": "method",
            "cohort": "engineering",
            "reference_sources": ["b2"],
            "coverage_recall_5": 1.0,
        }
    ]
    budgets = [
        {
            "case_id": "case",
            "method": "method",
            "status": "ready",
            "budget": {
                "supplied_source_ids": ["h", "b1"],
                "selected_top_5": ["h", "b1"],
                "excluded_by_byte_budget": [],
            },
        }
    ]
    return rows, scores, budgets, queries, units


def test_false_and_zero_are_verified_facts_but_empty_fields_are_not():
    assert facts_present({"query_audit": {"field_values": {"event": False, "count": 0}}})
    assert not facts_present({"query_audit": {"field_values": {}}})
    with pytest.raises(ValueError, match="mapping"):
        facts_present({"query_audit": {"field_values": []}})


def test_module_top5_gain_does_not_imply_actual_case_packet_coverage():
    records, metrics = packet_coverage(*packet_inputs())
    row = records[0]
    assert row["module_top5_original_coverage"] == 1
    assert row["packet_original_coverage"] == 0
    assert row["module_top5_not_selected_by_count_or_module"] == ["b2"]
    assert row["module_originals_excluded_by_byte_budget"] == []
    assert metrics[0]["mean_packet_original_coverage"] == 0
    assert metrics[0]["module_top5_units_not_selected_by_count_or_module"] == 1


def test_selected_but_over_byte_budget_is_not_count_or_module_omission():
    args = packet_inputs()
    args[2][0]["budget"]["selected_top_5"].append("b2")
    args[2][0]["budget"]["excluded_by_byte_budget"] = ["b2"]
    records, metrics = packet_coverage(*args)
    assert records[0]["module_top5_not_selected_by_count_or_module"] == []
    assert records[0]["module_originals_excluded_by_byte_budget"] == ["b2"]
    assert metrics[0]["module_units_excluded_by_byte_budget"] == 1


def test_missing_module_evidence_is_explicit_even_with_complete_module_ranking():
    args = packet_inputs()
    args[2][0]["budget"]["supplied_source_ids"] = ["h"]
    records, metrics = packet_coverage(*args)
    assert records[0]["no_module_evidence_in_packet"]
    assert metrics[0]["labeled_scopes_without_module_evidence"] == 1


def test_case_packet_coverage_uses_reference_union_without_double_weighting():
    units = {"whole": {"covers_source_ids": ["a", "b"]}, "c": {}}
    common = {"case_id": "c1", "method": "baseline", "packet_source_ids": ["whole"]}
    records = [
        {**common, "reference_sources": ["a", "b"]},
        {**common, "reference_sources": ["b", "c"]},
    ]
    cases = case_packet_coverage(records, units)
    assert len(cases) == 1
    assert cases[0]["packet_original_coverage"] == 2 / 3
    assert cases[0]["packet_exact_reference_recall"] == 0
    candidate = {**cases[0], "method": "candidate", "packet_original_coverage": 1.0}
    paired = case_packet_pairs([*cases, candidate], "baseline", "candidate")
    assert paired["counts"] == {"improved": 1}
    assert summarize_case_packets(cases)[0]["labeled_cases"] == 1


def test_case_packet_sources_must_be_identical_across_module_views():
    records = [
        {"case_id": "c", "method": "m", "packet_source_ids": ["a"], "reference_sources": []},
        {"case_id": "c", "method": "m", "packet_source_ids": ["b"], "reference_sources": []},
    ]
    with pytest.raises(ValueError, match="inconsistent replay packets"):
        case_packet_coverage(records, {"a": {}, "b": {}})


@pytest.mark.parametrize(
    ("top5", "top10", "selected"),
    [(0.9, 1.0, "base"), (0.91, 0.99, "base"), (0.91, 1.0, "new")],
)
def test_promotion_requires_strict_top5_gain_without_top10_regression(top5, top10, selected):
    metrics = [
        {"method": "base", "coverage_recall_5": 0.9, "coverage_recall_10": 1.0},
        {"method": "new", "coverage_recall_5": top5, "coverage_recall_10": top10},
    ]
    assert promotion(metrics, "base", "new")["selected"] == selected


def test_best_observed_tree_arm_does_not_erase_prespecified_primary():
    metrics = [
        {"method": BASE10, "coverage_recall_5": 0.6, "coverage_recall_10": 0.6},
        {"method": CANDIDATE10, "coverage_recall_5": 0.87, "coverage_recall_10": 0.92},
        {"method": OBSERVED10, "coverage_recall_5": 0.87, "coverage_recall_10": 0.98},
    ]
    selection = tree_development_selection(metrics)
    assert selection["selected"] == OBSERVED10
    assert selection["prespecified_primary"] == CANDIDATE10
    assert selection["prespecified_primary_gate"]["selected"] == CANDIDATE10
    assert "after scoring" in selection["selection_type"]


def test_missing_method_is_pending_rather_than_successful_zero_metric():
    result = promotion([], "baseline", "candidate")
    assert result["status"] == "pending"
    assert result["candidate_passed"] is None


def test_native_failure_is_preserved_and_cannot_supply_fallback_originals():
    original = [{"status": "index_failed", "source_ids": [], "error": "Index unavailable"}]
    before = deepcopy(original)
    rows = canonical_rows(original)
    assert original == before
    assert rows[0]["status"] == "failed"
    assert rows[0]["native_execution_status"] == "index_failed"
    with pytest.raises(ValueError, match="fallback"):
        canonical_rows([{**original[0], "source_ids": ["substituted"]}])


def test_navigation_candidate_exclusions_are_separate_from_case_packet_budget():
    rows = [
        {
            "method": CANDIDATE10,
            "excluded_native_nodes_by_navigation_budget": ["node1", "node2"],
        }
    ]
    calls = [
        {
            "phase": CANDIDATE10,
            "request": {
                "messages": [{}, {"content": '{"originals": [{"original_text": "Text"}]}'}]
            },
        }
    ]
    result = navigation_costs(rows, calls)[0]
    assert result["rows_with_candidate_byte_exclusions"] == 1
    assert result["excluded_original_leaf_occurrences"] == 2
    assert result["actual_new_original_ranking_requests"] == 1
    assert result["candidate_budget_bytes"] == 20000
    assert result["different_from_case_packet_budget_bytes"] == 9000


def index_call(status="failed"):
    request = {
        "messages": [
            {
                "role": "user",
                "content": "Examples: unrelated source\n-Real Data-\nText: Commercial acuity original\n######################\nOutput:",
            }
        ]
    }
    return {
        "phase": {"stage": "index", "method": "graphrag", "module": "vision"},
        "request": request,
        "request_sha256": digest(request),
        "status": status,
        "raw_response": json.dumps({"done_reason": "length" if status == "failed" else "stop"}),
        "completion_rejected": "Partial extraction rejected" if status == "failed" else "",
    }


def test_exhausted_index_extraction_retries_degrade_quality_without_rewriting_records():
    calls = [index_call() for _ in range(3)]
    before = deepcopy(calls)
    units = {
        "visual-original": {
            "module": "vision",
            "evidence_text": "Commercial acuity original",
            "pdf_page": 220,
            "text_sha256": "original-text-hash",
        }
    }
    quality = native_index_quality(calls, units)
    assert calls == before
    assert quality["overall_status"] == "degraded"
    assert quality["failed_attempts_in_unrecovered_requests"] == 3
    issue = quality["issues"][0]
    assert issue["successful_identical_requests"] == 0
    assert issue["done_reasons"] == ["length"] * 3
    assert issue["matched_original_sources"][0]["source_id"] == "visual-original"
    assert issue["matched_original_sources"][0]["pdf_page"] == 220
    assert quality["retrieval_statuses_and_rankings_changed"] is False


def test_successful_identical_index_request_is_recovered_not_degraded():
    quality = native_index_quality([index_call(), index_call("completed")], {})
    assert quality["overall_status"] == "no_unrecovered_failure_observed"
    assert quality["recovered_exact_index_requests"] == 1
    assert quality["issues"] == []


def test_changed_index_request_fingerprint_is_rejected():
    call = index_call()
    call["request"]["messages"][0]["content"] = "Changed actual request"
    with pytest.raises(ValueError, match="fingerprint"):
        native_index_quality([call], {})
