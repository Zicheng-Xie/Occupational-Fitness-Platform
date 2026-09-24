"""Validate the integrated Red Flag, evidence and historical report boundaries offline."""

import argparse
import json
from pathlib import Path

from occupational_fitness_rag.api import _load_experiment_cases, _red_flag_classification
from occupational_fitness_rag.case_intake.traceable import extract_traceable_file
from occupational_fitness_rag.evaluation.workflow import evaluate_workflow
from occupational_fitness_rag.pipeline.workflow import OccupationalFitnessWorkflow
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json
from occupational_fitness_rag.reporting.archive import verify_saved_report

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history-root", type=Path)
    parser.add_argument("--upstream-baseline", type=Path)
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "outputs/evaluation/framework_preservation"
    )
    args = parser.parse_args()
    workflow = OccupationalFitnessWorkflow(ROOT / "configs/workflow.offline.yaml")
    target = args.output_dir
    target.mkdir(parents=True, exist_ok=True)
    regression = evaluate_workflow(
        workflow,
        ROOT / "data/cases/gold/workflow_expectations.json",
        target / "workflow_metrics.json",
    )
    original = json.loads(
        (ROOT / "data/cases/gold/framework_routing_expectations.json").read_text(encoding="utf-8")
    )
    framework_checks = []
    for expected in original["cases"]:
        case = extract_traceable_file(ROOT / expected["input"], workflow.book.field_specs)
        result, evidence, _ = workflow.assess(case)
        framework_checks.append(
            {
                "case_id": case.case_id,
                "passed": result.route == expected["route"]
                and result.assessment_outcome == expected["assessment_outcome"]
                and [module.model_dump(mode="json") for module in result.modules]
                == expected["modules"]
                and {request.rule_id: request.request_type for request in result.rag_requests}
                == expected["request_types"]
                and evidence.retrieval["ranking_calls"] == expected["ranking_calls"],
            }
        )
    experiments = []
    for item in _load_experiment_cases(ROOT).values():
        _, result, evidence, _ = workflow.from_text(item.text, item.case_id, [item.module])
        classification = _red_flag_classification(result)
        experiments.append(
            {
                "case_id": item.case_id,
                "classification": classification,
                "outcome": result.assessment_outcome,
                "passed": classification == item.expected_red_flag_classification
                and result.assessment_outcome == item.expected_outcome
                and not evidence.unresolved_requests,
            }
        )
    demos = []
    for entry in json.loads((ROOT / "outputs/demo/manifest.json").read_text(encoding="utf-8")):
        demos.append(workflow.verify_run(ROOT / entry["output"]))
    history = []
    if args.history_root:
        for manifest in sorted(args.history_root.glob("*/run-*/run_manifest.json")):
            history.append(
                {"run_id": manifest.parent.name, **verify_saved_report(workflow, manifest.parent)}
            )
    baseline_path = (
        args.upstream_baseline
        or ROOT / "outputs/evaluation/collaboration/upstream_offline_baseline.json"
    )
    baseline = (
        json.loads(baseline_path.read_text(encoding="utf-8")) if baseline_path.exists() else None
    )
    same_as_upstream = baseline is not None and baseline["records"] == experiments
    regression_passed = (
        regression["passed"] == regression["cases"]
        and workflow.book.sha256 == original["ruleset_sha256"]
        and all(check["passed"] for check in framework_checks)
    )
    labels_passed = all(item["passed"] for item in experiments)
    status = (
        "passed"
        if regression_passed and labels_passed
        else (
            "passed_with_known_limitations" if regression_passed and same_as_upstream else "failed"
        )
    )
    report = {
        "status": status,
        "evaluation_type": "engineering_integration_regression",
        "clinical_validation": False,
        "implementation_sha256": digest(
            {
                p.relative_to(ROOT).as_posix(): sha256_bytes(p.read_bytes())
                for p in sorted((ROOT / "src/occupational_fitness_rag").rglob("*.py"))
            }
        ),
        "ruleset_sha256": workflow.book.sha256,
        "index_sha256": workflow.catalogue.index_sha256,
        "workflow_regression": regression,
        "original_framework_comparison": {
            "snapshot": original["source_snapshot_commit"],
            "passed": sum(check["passed"] for check in framework_checks),
            "cases": framework_checks,
        },
        "red_flag_experiments": experiments,
        "upstream_offline_comparison": {
            "commit": baseline["upstream_commit"] if baseline else None,
            "all_15_classifications_and_outcomes_unchanged": same_as_upstream,
            "expected_label_matches": sum(item["passed"] for item in experiments),
            "limitation": "Offline extraction does not cover every natural-language fixture; unchanged outcomes are a compatibility check, not proof that expected labels are satisfied.",
        },
        "fixed_demo_reports": demos,
        "historical_reports": history,
        "model_calls": 0,
    }
    write_json(target / "integration_checks.json", report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "workflow_cases": regression["passed"],
                "original_framework_cases": sum(check["passed"] for check in framework_checks),
                "red_flag_cases": sum(item["passed"] for item in experiments),
                "fixed_reports_verified": len(demos),
                "historical_reports_verified": len(history),
            }
        )
    )
    if report["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
