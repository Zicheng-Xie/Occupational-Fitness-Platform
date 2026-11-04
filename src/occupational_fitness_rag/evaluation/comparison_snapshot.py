"""Export recorded experimental evidence into an existing Data report snapshot."""

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path


def read_recorded_rows(path: Path):
    """Read only newline-terminated records while another process appends UTF-8."""
    rows = []
    if path.exists():
        for line in path.read_bytes().splitlines(keepends=True):
            if not line.endswith(b"\n"):
                continue
            rows.append(json.loads(line.decode("utf-8")))
    return rows


def update_snapshot(experiment: Path, snapshot_path: Path, checkpoint=None):
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8-sig"))
    corpus = json.loads((experiment / "corpus.json").read_text(encoding="utf-8"))
    snapshot["queries"]["corpus"]["rows"] = [
        {
            "source_id": u["source_id"],
            "module": u["module"],
            "section": u["section"],
            "pdf_page": u["pdf_page"],
            "text": u["evidence_text"],
        }
        for u in corpus["units"]
    ]
    definitions = {
        "corpus": (
            "corpus.json",
            "PDF-region-verified original passages; clinician review pending",
        ),
        "judgments": (
            "results.jsonl",
            "Recorded local model calls, actual supplied evidence and failures",
        ),
        "metrics": (
            "summary.json",
            "Recorded-call agreement and Macro-F1; failures remain in denominators",
        ),
        "transitions": (
            "summary.json",
            "Same-case, same-model and same-repeat changes relative to hybrid",
        ),
    }
    for query, (filename, definition) in definitions.items():
        snapshot["queries"][query]["source"] = {
            "title": filename,
            "provider": "Local experiment files",
            "description": definition,
            "links": [],
            "evidenceFlow": [
                {"title": "Recorded artifact", "detail": str((experiment / filename).resolve())},
                {
                    "title": "Frozen corpus fingerprint",
                    "detail": corpus.get("corpus_sha256", "Unavailable"),
                },
            ],
        }
    upstream_path = experiment / "upstream_audit.json"
    if upstream_path.exists():
        upstream = json.loads(upstream_path.read_text(encoding="utf-8"))
        snapshot["queries"]["upstream"] = {
            "rows": upstream["cases"],
            "payloadColumns": ["changed_fields"],
            "source": {
                "title": "Upstream fact review audit",
                "provider": "Local experiment files",
                "description": "Deterministic and frozen-rule outcomes; frozen inputs were not changed",
                "links": [],
                "evidenceFlow": [
                    {"title": "Recorded artifact", "detail": str(upstream_path.resolve())}
                ],
            },
        }
    summary_path = experiment / "summary.json"
    summary = (
        checkpoint
        if checkpoint is not None
        else (json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {})
    )
    rows = []
    path = experiment / "results.jsonl"
    if path.exists():
        recorded = read_recorded_rows(path)
        for row in recorded[: summary.get("recorded_runs", len(recorded))]:
            answer = row.get("answer", {})
            prediction = answer.get("assessment_outcome")
            error_type = (
                "failed"
                if row["status"] != "completed"
                else "none"
                if row.get("reference_agreement")
                else "excess_abstention"
                if prediction == "insufficient_information"
                else "reference_mismatch"
            )
            rows.append(
                dict(
                    {
                        key: value
                        for key, value in row.items()
                        if key not in {"raw_response", "input_snapshot"}
                    },
                    prediction=prediction,
                    error_type=error_type,
                    explanation=answer.get("explanation", ""),
                    cited_sources=", ".join(answer.get("source_ids", [])),
                    nurse_note=row["input_snapshot"]["nurse_note"],
                    facts_json=json.dumps(
                        row["input_snapshot"]["verified_patient_facts"], indent=2
                    ),
                    evidence_json=json.dumps(row["input_snapshot"]["guideline_evidence"], indent=2),
                )
            )
    snapshot["queries"]["judgments"]["rows"] = rows
    snapshot["queries"]["judgments"]["payloadColumns"] = ["facts_json", "evidence_json"]
    snapshot["queries"]["metrics"]["rows"] = summary.get("metrics", [])
    snapshot["queries"]["transitions"]["rows"] = summary.get("paired_transitions", [])
    completion_path = experiment / "completion_audit.json"
    if completion_path.exists():
        completion = json.loads(completion_path.read_text(encoding="utf-8"))
        for query, field, description in [
            (
                "classification_balance",
                "metrics",
                "Independent recalculation of agreement, reference-class recall and abstention baseline",
            ),
            (
                "paired_intervals",
                "paired_differences",
                "Case-clustered agreement differences relative to hybrid; failures remain misses",
            ),
        ]:
            snapshot["queries"][query] = {
                "rows": completion[field],
                "source": {
                    "title": "Completed comparison audit",
                    "provider": "Local experiment files",
                    "description": description,
                    "links": [],
                    "evidenceFlow": [
                        {"title": "Recorded artifact", "detail": str(completion_path.resolve())}
                    ],
                },
            }
    audit_path = experiment / "error_audit.json"
    if audit_path.exists():
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        for query, field, description in [
            (
                "error_pairs",
                "pairs",
                "Paired outcomes, exact evidence bundle differences and upstream review flags",
            ),
            (
                "repeat_stability",
                "repeat_stability",
                "Outcome stability requires all planned calls and identical inputs",
            ),
        ]:
            snapshot["queries"][query] = {
                "rows": audit[field],
                "source": {
                    "title": "Judgment error audit",
                    "provider": "Local experiment files",
                    "description": description,
                    "links": [],
                    "evidenceFlow": [
                        {"title": "Recorded artifact", "detail": str(audit_path.resolve())}
                    ],
                },
            }
    cost_path = experiment / "costs.json"
    if cost_path.exists():
        costs = json.loads(cost_path.read_text(encoding="utf-8"))
        cost_rows = []
        for retrieval in costs["retrieval"]:
            method = retrieval["method"]
            indexes = [r for r in costs["indexes"] if method in Path(r["index_path"]).parts]
            counters = (costs.get("framework_reported_counters") or {}).get(method, {})
            conditions = [r for r in rows if r["method"] == method]
            cost_rows.append(
                {
                    **retrieval,
                    "index_seconds": sum(r["seconds"] for r in indexes) if indexes else None,
                    "construction_scope": "Original cached incremental construction"
                    if any(r.get("llm_cache_reused") for r in indexes)
                    else "Original construction"
                    if indexes
                    else "Shared embedding cost not allocated",
                    "graph_model_requests": counters.get("attempted_graph_model_requests"),
                    "recorded_judgments": len(conditions),
                    "network_attempts": sum("request_sha256" in r for r in conditions),
                    "judgment_failures": sum(r["status"] != "completed" for r in conditions),
                    "judgment_seconds": sum(r["seconds"] for r in conditions),
                }
            )
        snapshot["queries"]["costs"] = {
            "rows": cost_rows,
            "source": {
                "title": "Retrieval and model cost audit",
                "provider": "Local experiment files",
                "description": "Recorded timing and framework-reported counters; unavailable counts remain null",
                "links": [],
                "evidenceFlow": [
                    {"title": "Recorded artifact", "detail": str(cost_path.resolve())}
                ],
            },
        }
    snapshot["status"] = summary.get("execution_status", "running")
    snapshot["plannedRuns"] = summary.get("planned_runs")
    labels_path = experiment / "labels.json"
    if labels_path.exists():
        labels = json.loads(labels_path.read_text(encoding="utf-8"))
        snapshot["cohortCounts"] = dict(Counter(label["cohort"] for label in labels))
    snapshot["buildStatus"] = "complete"
    snapshot["generatedAt"] = datetime.now(UTC).isoformat()
    temp = snapshot_path.with_suffix(".tmp")
    temp.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(snapshot_path)
    return len(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", type=Path)
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args()
    print(update_snapshot(args.experiment, args.snapshot))
