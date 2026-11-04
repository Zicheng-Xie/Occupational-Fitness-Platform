"""Audit export checks, including concurrent partial JSONL and label sensitivity."""

import json

from occupational_fitness_rag.evaluation.comparison_analysis import export_analysis
from occupational_fitness_rag.evaluation.comparison_cost_audit import audit_costs
from occupational_fitness_rag.evaluation.comparison_snapshot import (
    read_recorded_rows,
    update_snapshot,
)


def test_framework_cost_counters_are_not_summed_across_duplicate_snapshots(tmp_path):
    folder = tmp_path / "indexes" / "graph" / "vision" / "logs"
    folder.mkdir(parents=True)
    record = 'Metrics for ollama_chat/local: {\n"attempted_request_count": 7\n}'
    log = folder / "indexing-engine.log"
    log.write_text(record, encoding="utf-8")
    audit = audit_costs(tmp_path)
    assert audit["graphrag"]["attempted_graph_model_requests"] == 7
    assert audit["lightrag"]["attempted_graph_model_requests"] is None
    log.write_text(record + "\n" + record, encoding="utf-8")
    audit = audit_costs(tmp_path)
    assert audit["graphrag"]["attempted_graph_model_requests"] is None


def test_partial_multibyte_append_is_retried_without_corrupting_complete_records(tmp_path):
    path = tmp_path / "results.jsonl"
    path.write_bytes(b'{"case_id":"complete"}\n{"note":"\xe2\x80')
    assert read_recorded_rows(path) == [{"case_id": "complete"}]


def test_snapshot_keeps_identity_and_classifies_abstention(tmp_path):
    experiment = tmp_path / "experiment"
    experiment.mkdir()
    (experiment / "corpus.json").write_text('{"units": []}', encoding="utf-8")
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(
        json.dumps(
            {
                "id": "report:stable",
                "queries": {
                    name: {"rows": []} for name in ["judgments", "metrics", "transitions", "corpus"]
                },
            }
        ),
        encoding="utf-8",
    )
    row = {
        "status": "completed",
        "reference_agreement": False,
        "answer": {"assessment_outcome": "insufficient_information", "source_ids": []},
        "input_snapshot": {
            "nurse_note": "A complex note",
            "verified_patient_facts": [],
            "guideline_evidence": [],
        },
    }
    (experiment / "results.jsonl").write_text(json.dumps(row) + '\n{"partial":', encoding="utf-8")
    (experiment / "summary.json").write_text(
        json.dumps({"execution_status": "running"}), encoding="utf-8"
    )
    assert update_snapshot(experiment, snapshot) == 1
    data = json.loads(snapshot.read_text(encoding="utf-8"))
    assert data["id"] == "report:stable"
    assert data["queries"]["judgments"]["rows"][0]["error_type"] == "excess_abstention"
    assert data["status"] == "running"
    (experiment / "results.jsonl").write_text((json.dumps(row) + "\n") * 2, encoding="utf-8")
    (experiment / "summary.json").write_text(
        json.dumps({"execution_status": "running", "recorded_runs": 1}), encoding="utf-8"
    )
    assert update_snapshot(experiment, snapshot) == 1
    assert (
        "input_snapshot"
        not in json.loads(snapshot.read_text(encoding="utf-8"))["queries"]["judgments"]["rows"][0]
    )


def test_analysis_records_disputed_labels_without_rewriting(tmp_path):
    labels = [
        {"case_id": "case-1", "cohort": "engineering", "expected_outcome": "temporarily_unfit"}
    ]
    (tmp_path / "labels.json").write_text(json.dumps(labels), encoding="utf-8")
    (tmp_path / "label_audit.json").write_text(
        json.dumps([{"case_id": "case-1", "matches_current_rules": False}]), encoding="utf-8"
    )
    result = export_analysis(tmp_path)
    assert result["label_discrepancies"] == 1
    sensitivity = json.loads(
        (tmp_path / "label_consistent_sensitivity.json").read_text(encoding="utf-8")
    )
    assert sensitivity["excluded_case_ids"] == ["case-1"]
    assert json.loads((tmp_path / "labels.json").read_text(encoding="utf-8")) == labels
    assert (
        (tmp_path / "retrieval_review.csv")
        .read_text(encoding="utf-8-sig")
        .startswith("case_id,method")
    )
