"""Final audit must preserve failures, cohort imbalance and build checkpoints."""

import csv
import json
from copy import deepcopy

from occupational_fitness_rag.evaluation.comparison_analysis import export_analysis
from occupational_fitness_rag.evaluation.comparison_completion import (
    audit_completion,
    cohort_metrics,
    paired_intervals,
)
from occupational_fitness_rag.evaluation.comparison_report_refresh import refresh
from occupational_fitness_rag.provenance import digest


def call(case, reference, prediction, method="hybrid", repeat=0, status="completed"):
    return {
        "case_id": case,
        "cohort": "engineering",
        "model": "local",
        "method": method,
        "repeat": repeat,
        "status": status,
        "reference_outcome": reference,
        "answer": {"assessment_outcome": prediction},
        "input_snapshot": {
            "licence_context": "commercial",
            "modules": ["blackout"],
            "nurse_note": "Synthetic note",
            "verified_patient_facts": {},
        },
    }


def test_majority_abstention_is_distinct_from_balanced_classification():
    rows = [call(str(i), "insufficient_information", "insufficient_information") for i in range(3)]
    rows += [call("positive", "temporarily_unfit", "insufficient_information")]
    metrics, classes = cohort_metrics(rows)
    assert metrics[0]["agreement"] == 0.75
    assert metrics[0]["insufficient_only_baseline"] == 0.75
    assert metrics[0]["balanced_accuracy"] == 0.5
    assert metrics[0]["non_abstention_reference_correct"] == 0
    positive = next(r for r in classes if r["reference_outcome"] == "temporarily_unfit")
    assert positive["recall"] == 0


def test_failures_remain_misses_and_paired_intervals_resample_cases():
    rows = []
    for i in range(3):
        rows.extend(
            [
                call("a", "temporarily_unfit", "insufficient_information", repeat=i),
                call("a", "temporarily_unfit", "temporarily_unfit", "vector", i),
                call("b", "temporarily_unfit", "temporarily_unfit", repeat=i),
                call("b", "temporarily_unfit", "temporarily_unfit", "vector", i, "failed"),
            ]
        )
    metrics, _ = cohort_metrics(rows)
    vector = next(m for m in metrics if m["method"] == "vector")
    assert vector["failures"] == 3 and vector["agreement"] == 0.5
    paired = paired_intervals(rows)[0]
    assert paired["cases"] == 2 and paired["paired_calls"] == 6
    assert paired["wrong_to_correct"] == 3 and paired["loss_with_a_failed_call"] == 3
    assert paired["agreement_delta_vs_hybrid"] == 0
    assert paired["case_cluster_95ci"] == [-1, 1]
    changed = deepcopy(rows)
    changed[1]["input_snapshot"]["nurse_note"] = "Different patient input"
    assert paired_intervals(changed)[0]["excluded_input_mismatches"] == 1


def test_refresher_returns_the_built_checkpoint_when_summary_advances(tmp_path, monkeypatch):
    from occupational_fitness_rag.evaluation import comparison_report_refresh as module

    output, app = tmp_path / "output", tmp_path / "app"
    output.mkdir()
    exported = app / ".data-app-offline/exports/judgment_report.html"
    exported.parent.mkdir(parents=True)
    exported.write_text("<html>Checkpoint 12</html>", encoding="utf-8")
    checkpoint = {"recorded_runs": 12, "execution_status": "running"}
    summary = output / "summary.json"
    summary.write_text(json.dumps(checkpoint), encoding="utf-8")
    observed = []
    monkeypatch.setattr(module, "export_analysis", lambda p, c: observed.append(c))
    monkeypatch.setattr(module, "update_snapshot", lambda p, s, c: observed.append(c))

    def run(*args, **kwargs):
        summary.write_text(
            json.dumps({"recorded_runs": 24, "execution_status": "completed"}), encoding="utf-8"
        )

    monkeypatch.setattr(module.subprocess, "run", run)
    built = refresh(output, app, tmp_path / "node", tmp_path / "builder")
    assert built == checkpoint and observed == [checkpoint, checkpoint]
    assert json.loads(summary.read_text(encoding="utf-8"))["execution_status"] == "completed"
    assert (output / "interactive_report.html").read_text(
        encoding="utf-8"
    ) == "<html>Checkpoint 12</html>"


def test_completion_detects_tampered_original_passages_and_missing_conditions(tmp_path):
    row = call("a", "temporarily_unfit", "temporarily_unfit", "vector")
    source = dict(
        source_id="source-1",
        source_text="Original paragraph.",
        section="1.2",
        pdf_page=68,
        printed_page=57,
    )
    row["input_snapshot"]["guideline_evidence"] = [source]
    row["answer"].update(source_ids=["source-1"], fact_fields=[])
    row["prompt_sha256"] = digest(row["input_snapshot"])
    row["reference_agreement"] = True
    artifacts = {
        "manifest.json": {
            "planned_runs": 1,
            "config": {
                "models": ["local"],
                "methods": ["vector"],
                "repeats": 1,
                "evidence_max_bytes": 9000,
                "top_k": 5,
            },
        },
        "corpus.json": {"units": [{**source, "evidence_text": "Original paragraph."}]},
        "labels.json": [{"case_id": "a", "expected_outcome": "temporarily_unfit"}],
        "summary.json": {
            "metrics": [
                {
                    "cohort": "engineering",
                    "model": "local",
                    "method": "vector",
                    "agreement_all_runs": 1,
                    "macro_f1": 1,
                    "failures": 0,
                    "runs": 1,
                }
            ]
        },
    }
    for name, data in artifacts.items():
        (tmp_path / name).write_text(json.dumps(data), encoding="utf-8")
    records = tmp_path / "results.jsonl"
    records.write_text(json.dumps(row) + "\n", encoding="utf-8")
    assert audit_completion(tmp_path)["status"] == "passed"
    row["input_snapshot"]["guideline_evidence"][0]["source_text"] = "Changed paragraph."
    records.write_text(json.dumps(row) + "\n", encoding="utf-8")
    audit = audit_completion(tmp_path)
    assert audit["status"] == "needs_revision"
    assert audit["checks"]["original_source_mapping_mismatch"] == 1
    records.write_text("", encoding="utf-8")
    assert not audit_completion(tmp_path)["matrix_complete"]


def test_refresh_preserves_independent_source_review(tmp_path):
    row = call("a", "temporarily_unfit", "temporarily_unfit", "vector")
    row.update(module="blackout", seconds=0.1, reference_agreement=True)
    row["input_snapshot"]["guideline_evidence"] = [
        dict(source_id="source-1", source_text="Original paragraph.", section="1.2", pdf_page=68)
    ]
    (tmp_path / "results.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    (tmp_path / "labels.json").write_text(
        json.dumps([dict(case_id="a", cohort="engineering", expected_outcome="temporarily_unfit")]),
        encoding="utf-8",
    )
    (tmp_path / "label_audit.json").write_text("[]", encoding="utf-8")
    export_analysis(tmp_path)
    path = tmp_path / "retrieval_review.csv"
    with path.open(encoding="utf-8-sig", newline="") as stream:
        worksheet = list(csv.DictReader(stream))
    worksheet[0].update(
        reviewer="Independent reviewer",
        relevant="yes",
        review_status="reviewed",
        comments="Applicability checked.",
    )
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(worksheet[0]))
        writer.writeheader()
        writer.writerows(worksheet)
    export_analysis(tmp_path)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        refreshed = list(csv.DictReader(stream))
    assert refreshed == worksheet
