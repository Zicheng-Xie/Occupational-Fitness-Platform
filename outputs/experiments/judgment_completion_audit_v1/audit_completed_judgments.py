"""Verify completed judge records and retain zero-condition dispatch failures.

This command performs no model calls. It validates original request identities,
raw accepted outputs, source snapshots and engineering-reference scoring before
reporting a completed comparison. A zero-call adapter output is never adopted.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
from collections import Counter
from html import escape
from pathlib import Path

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.evaluation.passage_comparison import read_records
from occupational_fitness_rag.provenance import digest, write_json
from tools import run_frozen_retrieval_judgments as actor


def function_ast(path, name):
    module = ast.parse(Path(path).read_text(encoding="utf-8"))
    return ast.dump(
        next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == name)
    )


def verify_completed(directory, labels, config):
    """Revalidate raw outputs without retrying failures or changing labels."""
    directory = Path(directory)
    actor.verify_files(directory)
    plan = json.loads((directory / "plan.json").read_bytes())
    if (
        digest({k: v for k, v in plan.items() if k not in {"identity", "production_change"}})
        != plan["identity"]
    ):
        raise ValueError("Execution plan self-identity differs")
    if not plan["conditions"]:
        raise ValueError("Zero-condition output is not a completed judgment experiment")
    summary = json.loads((directory / "summary.json").read_bytes())
    requests = json.loads((directory / "requests.json").read_bytes())
    rows = read_records(directory / "results.jsonl")
    planned = {actor.key(c): c for c in plan["conditions"]}
    if (
        digest(requests) != plan["requests_sha256"]
        or any(digest(body) != rid for rid, body in requests.items())
        or len(planned) != len(plan["conditions"])
        or len(rows) != len(planned)
        or {actor.key(r) for r in rows} != set(planned)
        or summary["complete"] is not True
        or summary["identity"] != plan["identity"]
        or summary["recorded"] != len(rows)
        or summary["planned"] != len(planned)
        or summary["actual_judgment_calls"] != len(rows)
    ):
        raise ValueError("Completed request or condition inventory differs")
    for row in rows:
        if (
            row["experiment_identity"] != plan["identity"]
            or row["request_identity"] != planned[actor.key(row)]["request_identity"]
        ):
            raise ValueError("Recorded condition differs from frozen request")
        body = requests[row["request_identity"]]
        payload = json.loads(body["messages"][1]["content"])
        if row["status"] == "completed":
            accepted = actor.accept_completion(row["raw_response"], payload, row["method"], config)
            if row["answer"] != accepted.model_dump(mode="json"):
                raise ValueError("Accepted answer differs from retained raw completion")
        elif row["status"] != "failed":
            raise ValueError("Unknown completion status")
    metrics = actor.scoring(rows, labels)
    if metrics != summary["metrics"] or summary["accepted"] != sum(
        r["status"] == "completed" for r in rows
    ):
        raise ValueError("Saved engineering scoring or completion counts differ")
    return plan, rows, requests, metrics


def describe_zero_revision(directory, expected_count):
    directory = Path(directory)
    actor.verify_files(directory)
    plan = json.loads((directory / "plan.json").read_bytes())
    summary = json.loads((directory / "summary.json").read_bytes())
    if plan["conditions"] or summary["recorded"] or summary["actual_judgment_calls"]:
        raise ValueError("Expected the retained zero-call diagnostic, not another experiment")
    return {
        "status": "invalid_zero_condition_dispatch",
        "expected_conditions": expected_count,
        "actual_planned_conditions": 0,
        "actual_judgment_calls": 0,
        "saved_complete_flag_is_not_experiment_completion": summary["complete"],
        "plan_identity": plan["identity"],
        "artifacts_sha256": file_hash(directory / "artifacts.json"),
        "cause": "Case selection depended on no_evidence payloads, which are absent from the revision-only preparation.",
        "repair": "Select cases from all ready payloads, enforce identical facts and nonempty conditions; use a fresh run directory.",
    }


def build(root, parent, preparation, zero_revision, output):
    root, parent, preparation, zero_revision, output = map(
        Path, (root, parent, preparation, zero_revision, output)
    )
    actor.verify_files(preparation)
    prep_manifest = json.loads((preparation / "manifest.json").read_bytes())
    labels = json.loads((preparation / "scoring_labels.json").read_bytes())
    if digest(labels) != prep_manifest["labels_sha256"]:
        raise ValueError("Engineering labels differ from preparation")
    plan, rows, _, metrics = verify_completed(parent, labels, prep_manifest["config"])
    snapshots = json.loads((parent / "source_files.json").read_bytes())
    for original, record in snapshots.items():
        if (
            file_hash(parent / record["file"]) != record["sha256"]
            or plan["sources"][original] != record["sha256"]
        ):
            raise ValueError("Original source snapshot differs")
    archived_actor = parent / snapshots["tools\\run_frozen_retrieval_judgments.py"]["file"]
    for name in ("accept_completion", "prepare_inputs", "scoring", "paired_judgments"):
        if function_ast(archived_actor, name) != function_ast(
            root / "tools/run_frozen_retrieval_judgments.py", name
        ):
            raise ValueError("Judge validation or scoring contract changed: " + name)
    zero = describe_zero_revision(zero_revision, 198)
    source_names = [
        "tools/audit_completed_judgments.py",
        "tools/run_frozen_retrieval_judgments.py",
        "tools/run_serial_judgment_queue.py",
    ]
    audit_data = {
        "parent_identity": plan["identity"],
        "parent_artifacts_sha256": file_hash(parent / "artifacts.json"),
        "preparation_artifacts_sha256": file_hash(preparation / "artifacts.json"),
        "zero_revision_artifacts_sha256": file_hash(zero_revision / "artifacts.json"),
        "sources": {n: file_hash(root / n) for n in source_names},
    }
    if output.exists():
        raise ValueError("Preserve earlier completion audits; use a fresh directory")
    output.mkdir(parents=True)
    summary = {
        "parent_planned": len(plan["conditions"]),
        "parent_recorded": len(rows),
        "parent_accepted": sum(r["status"] == "completed" for r in rows),
        "parent_failed": sum(r["status"] == "failed" for r in rows),
        "failure_reasons": dict(Counter(r.get("error") for r in rows if r["status"] == "failed")),
        "metrics": metrics,
        "zero_revision": zero,
        "new_model_calls": 0,
        "clinical_review": "pending",
        "production_change": False,
        "interpretation": "Engineering reference agreement across observed development cases, not clinical accuracy. Repeats are independent calls, not independent patients. Source-ID validity does not establish explanation support.",
    }
    write_json(
        output / "manifest.json",
        {**audit_data, "identity": digest(audit_data), "production_change": False},
    )
    write_json(output / "summary.json", summary)
    failures = [
        {k: v for k, v in r.items() if k != "raw_response"} for r in rows if r["status"] == "failed"
    ]
    write_json(output / "failures.json", failures)
    paired = actor.paired_judgments(rows, labels)
    write_json(output / "paired_changes.json", paired)
    fields = [k for k in metrics[0] if k != "confusion_matrix_accepted"]
    with (output / "summary.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(metrics)
    table = "".join(
        "<tr>"
        + "".join(
            "<td>"
            + escape(
                str(m[k])
                if k
                not in {
                    "engineering_reference_agreement_all_recorded",
                    "macro_f1_over_observed_classes_accepted",
                }
                else f"{m[k]:.2%}"
            )
            + "</td>"
            for k in (
                "model",
                "method",
                "recorded",
                "accepted",
                "failed",
                "engineering_reference_agreement_all_recorded",
                "macro_f1_over_observed_classes_accepted",
            )
        )
        + "</tr>"
        for m in metrics
    )
    html = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Completed judgment audit | Occupational Fitness Platform</title><style>body{font:15px/1.6 Arial,sans-serif;color:#243748;background:#f4f6f8;max-width:1200px;margin:32px auto;padding:24px}main{background:white;border:1px solid #dce3ea;border-radius:8px;padding:30px}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:9px;border-bottom:1px solid #dce3ea}p{max-width:1000px}a{color:#225b83}.notice{background:#fff6df;padding:16px}</style><main><small>OCCUPATIONAL FITNESS PLATFORM · COMPLETION AUDIT</small><h1>Completed original judgment comparison</h1>"""
    html += (
        f"<p>{len(rows)}/1782 recorded conditions, {summary['parent_accepted']} accepted outputs, {summary['parent_failed']} retained citation-contract failures. Validation and scoring were replayed without new model calls.</p><p>"
        + escape(summary["interpretation"])
        + "</p><table><tr><th>Judge</th><th>Method</th><th>Recorded</th><th>Accepted</th><th>Failed</th><th>Engineering reference agreement</th><th>Macro-F1, accepted observed classes</th></tr>"
        + table
        + "</table>"
    )
    html += '<h2>Revision dispatch diagnostic</h2><p class="notice">The first revised-arm dispatch produced zero model calls because its case selector required an optional no-evidence control. Its saved 0/0 complete flag is not accepted as experimental completion. The diagnostic and failed queue remain unchanged. A corrected, separately versioned run must execute the 198 prepared conditions.</p><p>The corrected selector accepts all ready case payloads, checks identical patient facts across evidence arms, and rejects empty condition inventories. Judge prompts, model settings, schemas and original completed outputs are unchanged.</p><p><a href="summary.json">Verified summary</a> · <a href="summary.csv">Metrics CSV</a> · <a href="failures.json">Retained failures</a> · <a href="paired_changes.json">Case-level judgment changes</a> · <a href="manifest.json">Version pins</a></p></main></html>'
    (output / "index.html").write_text(html, encoding="utf-8")
    for name in source_names:
        (output / Path(name).name).write_bytes((root / name).read_bytes())
    write_json(
        output / "artifacts.json", {p.name: file_hash(p) for p in output.iterdir() if p.is_file()}
    )
    return {
        k: summary[k]
        for k in (
            "parent_planned",
            "parent_recorded",
            "parent_accepted",
            "parent_failed",
            "new_model_calls",
        )
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--parent", type=Path, default=Path("outputs/experiments/seven_method_judgment_full_v1")
    )
    parser.add_argument(
        "--preparation",
        type=Path,
        default=Path("outputs/experiments/retrieval_judgment_preparation_v2"),
    )
    parser.add_argument(
        "--zero-revision",
        type=Path,
        default=Path("outputs/experiments/anchored_hybrid_judgment_full_v2"),
    )
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/experiments/judgment_completion_audit_v1")
    )
    args = parser.parse_args()
    print(
        json.dumps(
            build(Path.cwd(), args.parent, args.preparation, args.zero_revision, args.output),
            indent=2,
        )
    )
