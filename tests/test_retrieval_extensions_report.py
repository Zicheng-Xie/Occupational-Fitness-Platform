import hashlib
import json
import re
from copy import deepcopy

import pytest

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.provenance import write_json
from tools import report_retrieval_extensions as report


def fixture():
    text = "Exact original </script><script>invalid()</script> source."
    source = {
        "source_id": "source",
        "module": "vision",
        "licence_context": "commercial",
        "evidence_text": text,
        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "section": "10.3",
        "pdf_page": 220,
        "printed_page": 209,
    }
    queries = [
        {
            "query_id": "q",
            "case_id": "case",
            "module": "vision",
            "licence_context": "commercial",
            "query": "Vision facts.",
        }
    ]
    rows = [
        {
            "query_id": "q",
            "case_id": "case",
            "module": "vision",
            "method": "flag_embedding_rerank",
            "experiment_identity": "frozen",
            "status": "completed",
            "source_ids": ["source"],
            "ranked_sources": [{"source_id": "source", "score": 0.9}],
        }
    ]
    return queries, {"source": source}, rows


def test_native_inventory_scope_and_source_identity_are_validated_before_scoring():
    queries, units, rows = fixture()
    report.validate_native(rows, queries, units, "flag_embedding_rerank", "frozen")
    for changed in (
        [],
        [*rows, *rows],
        [{**rows[0], "case_id": "different"}],
        [{**rows[0], "source_ids": ["missing"]}],
        [{**rows[0], "source_ids": ["source", "source"]}],
    ):
        with pytest.raises(ValueError):
            report.validate_native(changed, queries, units, "flag_embedding_rerank", "frozen")


def test_failed_queries_keep_empty_evidence_without_fallback():
    queries, units, rows = fixture()
    failed = {
        **rows[0],
        "status": "failed",
        "source_ids": [],
        "ranked_sources": [],
        "error": "Native failure",
    }
    report.validate_native([failed], queries, units, "flag_embedding_rerank", "frozen")
    failed["source_ids"] = ["source"]
    with pytest.raises(ValueError, match="substituted"):
        report.validate_native([failed], queries, units, "flag_embedding_rerank", "frozen")


def test_graph_path_cannot_claim_a_different_source_or_scope():
    queries, units, rows = fixture()
    row = deepcopy(rows[0])
    row["ranked_sources"][0]["graph_paths"] = [
        {
            "source_id": "source",
            "seed_source_id": "missing",
            "text_sha256": units["source"]["text_sha256"],
        }
    ]
    with pytest.raises(ValueError, match="graph path crosses"):
        report.validate_native([row], queries, units, "flag_embedding_rerank", "frozen")


def test_frozen_bundle_rejects_file_drift_and_path_escape(tmp_path):
    write_json(tmp_path / "manifest.json", {"snapshot": "original"})
    write_json(
        tmp_path / "artifacts.json", {"manifest.json": file_hash(tmp_path / "manifest.json")}
    )
    report.verify_files(tmp_path)
    write_json(tmp_path / "manifest.json", {"snapshot": "changed"})
    with pytest.raises(ValueError, match="Changed or unsafe"):
        report.verify_files(tmp_path)
    outside = tmp_path.parent / "outside.json"
    write_json(outside, {})
    write_json(tmp_path / "artifacts.json", {"../outside.json": file_hash(outside)})
    with pytest.raises(ValueError, match="Changed or unsafe"):
        report.verify_files(tmp_path)


def test_html_embedded_original_text_roundtrips_without_script_execution(tmp_path):
    queries, units, rows = fixture()
    rows = [{**rows[0], "method": method} for method in ("hybrid", "flag_embedding_rerank")]
    scored = [
        {
            "query_id": "q",
            "case_id": "case",
            "module": "vision",
            "method": r["method"],
            "coverage_recall_5": 1,
            "coverage_recall_10": 1,
            "exact_recall_5": 1,
        }
        for r in rows
    ]
    metric = {
        "method": "hybrid",
        "completed": 1,
        "records": 1,
        "exact_recall_5": 1,
        "coverage_recall_5": 1,
        "coverage_recall_10": 1,
        "fully_covered_5": 1,
        "labeled_scopes": 1,
    }
    summary = {
        "interpretation": "Development fixtures, not clinical accuracy.",
        "main_metrics": [metric],
        "framework_boundaries": {"docling": "Separate parser audit."},
        "cohorts": {},
        "diseases": {},
        "historical_and_ablation_metrics": [],
        "native_execution": {},
        "evidence_budget_metrics": [],
        "preferred_seventh_method": "flag_embedding_rerank",
    }
    report.render(tmp_path, rows, scored, queries, units, [], summary)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    raw = re.search(
        r'<script id="report-data" type="application/json">(.*?)</script>', html, re.S
    ).group(1)
    assert json.loads(raw)["units"]["source"]["evidence_text"] == units["source"]["evidence_text"]
    assert "<script>invalid()" not in html
    assert "Ten independent retrieval routes" in html
    assert "engineering" not in json.loads(raw)["rows"][0]  # no invented labels in raw rankings


def test_missing_timing_is_unavailable_instead_of_zero_cost():
    _, _, rows = fixture()
    value = report.costs(rows, {})[0]
    assert value["recorded_query_seconds"] is None and value["timed_records"] == 0


def test_absolute_parent_experiment_paths_are_valid_but_escapes_are_rejected(tmp_path):
    legitimate = tmp_path / "outputs/experiments/pageindex_parent"
    assert report.experiment_path(tmp_path, legitimate) == legitimate.resolve()
    assert (
        report.experiment_path(tmp_path, "outputs/experiments/pageindex_parent")
        == legitimate.resolve()
    )
    with pytest.raises(ValueError, match="escapes"):
        report.experiment_path(tmp_path, tmp_path.parent / "outside")


@pytest.mark.parametrize(
    ("r5", "r10", "promoted"),
    [(0.837, 1, False), (0.94, 0.99, False), (0.9259, 1, False), (0.94, 1, True)],
)
def test_seventh_method_requires_strict_top5_gain_and_full_top10_retention(r5, r10, promoted):
    candidate = "v5-primary"
    metrics = [
        {"method": report.DEFAULT_PREFERRED, "coverage_recall_5": 0.9259, "coverage_recall_10": 1},
        {"method": candidate, "coverage_recall_5": r5, "coverage_recall_10": r10},
    ]
    selected, decision = report.select_seventh(metrics, candidate)
    assert selected == (candidate if promoted else report.DEFAULT_PREFERRED)
    assert decision["candidate_passed"] is promoted
    if not promoted:
        with pytest.raises(ValueError, match="fails"):
            report.select_seventh(metrics, candidate, preferred=candidate)


def test_recovery_requires_explicit_lineage_request_not_a_parent_output_alias(tmp_path):
    request = tmp_path / "request.json"
    write_json(request, {"parent": "outputs/experiments/parent", "output": "same"})
    with pytest.raises(ValueError, match="Unexpected PageIndex recovery"):
        report.validate_pageindex_recovery(tmp_path, tmp_path, request, [], {}, [], {})
