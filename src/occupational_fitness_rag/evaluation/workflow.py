"""Engineering regression metrics, explicitly separate from clinical validation."""

import json
from pathlib import Path
from time import perf_counter

from occupational_fitness_rag.case_intake.traceable import extract_traceable_file
from occupational_fitness_rag.provenance import write_json


def evaluate_workflow(workflow, gold_path: Path, output: Path) -> dict:
    data = json.loads(gold_path.read_text(encoding="utf-8"))
    labels = data["cases"]
    if not labels or len({x["case_id"] for x in labels}) != len(labels):
        raise ValueError("Evaluation labels must be nonempty and unique")
    records = []
    for label in labels:
        start = perf_counter()
        case = extract_traceable_file(workflow.root / label["input"], workflow.book.field_specs)
        if case.case_id != label["case_id"]:
            raise ValueError("Gold label and input case IDs differ")
        result, evidence, note = workflow.assess(case)
        module = next((m for m in result.modules if m.module == label["module"]), None)
        outcome = module.assessment_outcome if module else result.assessment_outcome
        triggered = {r.rule_id for r in result.rules_evaluated if r.result == "triggered"}
        missing = (
            set(module.missing_fields)
            if module
            else {f for m in result.modules for f in m.missing_fields}
        )
        checks = {
            "outcome": outcome == label["expected_outcome"],
            "expected_triggers": set(label["triggered_rules"]) <= triggered,
            "forbidden_triggers_absent": not set(label["not_triggered_rules"]) & triggered,
            "expected_missing": set(label["missing_fields"]) <= missing,
            "evidence_complete": not evidence.unresolved_requests,
            "case_spans_valid": True,
        }
        records.append(
            {
                "case_id": case.case_id,
                "module": label["module"],
                "expected": label["expected_outcome"],
                "actual": outcome,
                "checks": checks,
                "passed": all(checks.values()),
                "latency_ms": round((perf_counter() - start) * 1000, 3),
                "required_source_ids": sorted(
                    {sid for request in result.rag_requests for sid in request.source_ids}
                ),
                "bound_source_ids": sorted(
                    {c.source_id for e in evidence.evidence_items for c in e.citations}
                ),
            }
        )
    report = {
        "schema_version": "1.2.0",
        "evaluation_type": "engineering_development_regression",
        "clinical_validation": False,
        "held_out_validation": False,
        "cases": len(records),
        "passed": sum(r["passed"] for r in records),
        "outcome_accuracy": sum(r["checks"]["outcome"] for r in records) / len(records),
        "rule_boundary_pass_rate": sum(
            r["checks"]["expected_triggers"] and r["checks"]["forbidden_triggers_absent"]
            for r in records
        )
        / len(records),
        "exact_source_coverage": sum(r["checks"]["evidence_complete"] for r in records)
        / len(records),
        "ruleset_sha256": workflow.book.sha256,
        "index_sha256": workflow.catalogue.index_sha256,
        "retrieval_backend": workflow.config.retrieval.mode,
        "records": records,
        "limitations": [
            "Synthetic development cases; not an independent clinician-labelled test set.",
            "Exact source binding coverage is not semantic retrieval Recall@K.",
            "Regex/addendum coverage is not general medical-report extraction accuracy.",
        ],
    }
    write_json(output, report)
    return {k: v for k, v in report.items() if k != "records"}
