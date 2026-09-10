"""Main CLI for the complete workflow; legacy retrieval commands remain available."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from occupational_fitness_rag.pipeline.config import load_workflow_config
from occupational_fitness_rag.provenance import write_json


def _workflow(args):
    from occupational_fitness_rag.pipeline.workflow import OccupationalFitnessWorkflow

    return OccupationalFitnessWorkflow(args.config)


def build_knowledge(args):
    from occupational_fitness_rag.ingestion.source_catalogue import SourceCatalogue, build_catalogue
    from occupational_fitness_rag.rules.contracts import export_knowledge_contracts
    from occupational_fitness_rag.rules.engine import RuleBook

    config, root = load_workflow_config(args.config)
    data = build_catalogue(root, root / config.anchors, root / config.catalogue)
    export_knowledge_contracts(
        root, RuleBook(root / config.rules), SourceCatalogue(root, root / config.catalogue)
    )
    return {"source_units": len(data["units"]), "index_sha256": data["index_sha256"]}


def assess(args):
    workflow = _workflow(args)
    path = workflow.run_file(args.input, args.output_dir, args.modules)
    result = json.loads((path / "rule_result.json").read_text(encoding="utf-8"))
    return {
        "output": str(path.resolve()),
        "report": str((path / "draft_report.html").resolve()),
        "assessment_outcome": result["assessment_outcome"],
        "route": result["route"],
    }


def demo(args):
    workflow = _workflow(args)
    inputs = sorted((workflow.root / "data/cases/nurse_notes").glob("*.txt"))
    inputs += sorted((workflow.root / "data/cases/synthetic_expansion").glob("*.txt"))
    if not inputs:
        raise ValueError("No demo case inputs found")
    outputs = []
    for source in inputs:
        path = workflow.run_file(source, args.output_dir)
        result = json.loads((path / "rule_result.json").read_text(encoding="utf-8"))
        outputs.append(
            {
                "case_id": source.stem,
                "output": path.resolve().relative_to(workflow.root).as_posix(),
                "assessment_outcome": result["assessment_outcome"],
                "route": result["route"],
            }
        )
        print(f"Completed {len(outputs)}/{len(inputs)}: {source.stem}", file=sys.stderr)
    target = Path(args.output_dir) if args.output_dir else workflow.root / "outputs"
    write_json(target / "demo_manifest.json", outputs)
    return {"cases": len(outputs), "manifest": str((target / "demo_manifest.json").resolve())}


def export_schemas(args):
    from occupational_fitness_rag.rules.engine import RuleBook
    from occupational_fitness_rag.schemas.workflow import (
        Citation,
        ClinicalCase,
        ReviewNote,
        WorkflowEvidencePack,
    )
    from occupational_fitness_rag.schemas.red_flag_result import RAGInput, WorkflowRuleResult

    config, root = load_workflow_config(args.config)
    for name, model in {
        "knowledge_unit": Citation,
        "structured_case": ClinicalCase,
        "rule_result": WorkflowRuleResult,
        "rag_input": RAGInput,
        "evidence_pack": WorkflowEvidencePack,
        "gp_review_note": ReviewNote,
    }.items():
        write_json(root / "schemas" / (name + ".schema.json"), model.model_json_schema())
    write_json(root / "schemas/field_dictionary.json", RuleBook(root / config.rules).field_specs)
    return {"directory": str(root / "schemas"), "schemas": 6}


def verify_run(args):
    return _workflow(args).verify_run(Path(args.run_dir))


def benchmark(args):
    from occupational_fitness_rag.evaluation.workflow import evaluate_workflow

    report = evaluate_workflow(_workflow(args), Path(args.gold), Path(args.output))
    if report["passed"] != report["cases"]:
        raise ValueError(f"Workflow regression failed; inspect {args.output}")
    return report


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        prog="fitness-rag",
        description="Traceable five-module commercial-driver assessment workflow",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text, func in [
        (
            "build-knowledge",
            "Build source-verified evidence units from the supplied PDF",
            build_knowledge,
        ),
        ("assess", "Run report intake, rules, evidence and draft generation", assess),
        ("demo", "Run all original and added synthetic case fixtures", demo),
        ("export-schemas", "Export strict JSON schemas and fact dictionary", export_schemas),
        ("verify-run", "Replay rules and verify an existing artifact bundle", verify_run),
        ("benchmark", "Run curated synthetic regression evaluation", benchmark),
    ]:
        command = sub.add_parser(name, help=help_text)
        command.add_argument("--config", default="configs/workflow.yaml")
        command.set_defaults(func=func)
        if name == "assess":
            command.add_argument("--input", required=True)
            command.add_argument(
                "--modules",
                nargs="+",
                choices=["hypertension", "vision", "hearing", "blackout", "diabetes"],
            )
        if name in {"assess", "demo"}:
            command.add_argument("--output-dir")
        if name == "verify-run":
            command.add_argument("--run-dir", required=True)
        if name == "benchmark":
            command.add_argument("--gold", default="data/cases/gold/workflow_expectations.json")
            command.add_argument("--output", default="outputs/evaluation/workflow_metrics.json")
    from occupational_fitness_rag.cli import (
        cmd_evaluate_extraction,
        cmd_prepare_cases,
        cmd_retrieve,
    )

    prepare = sub.add_parser(
        "prepare-cases", help="Regenerate the original ten-case extraction baseline"
    )
    prepare.add_argument("--input-dir", default="data/cases/nurse_notes")
    prepare.add_argument("--intake-output", default="data/cases/processed/intake_results.jsonl")
    prepare.add_argument(
        "--structured-output", default="data/cases/processed/structured_cases.jsonl"
    )
    prepare.add_argument("--condition-output", default="data/cases/processed/condition_maps.jsonl")
    prepare.set_defaults(func=cmd_prepare_cases)
    evaluate = sub.add_parser(
        "evaluate-extraction", help="Evaluate the supplied extraction gold set"
    )
    evaluate.add_argument("--predictions", default="data/cases/processed/intake_results.jsonl")
    evaluate.add_argument("--gold", default="data/cases/gold/structured_cases.jsonl")
    evaluate.set_defaults(func=cmd_evaluate_extraction)
    legacy = sub.add_parser(
        "legacy-retrieve", help="v0.2 single-category Chroma retrieval contract"
    )
    legacy.add_argument("--config", default="configs/rag.yaml")
    legacy.add_argument("--rule-result", required=True)
    legacy.add_argument("--output")
    legacy.set_defaults(func=cmd_retrieve)
    args = parser.parse_args()
    try:
        result = args.func(args)
        if result is not None:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, FileNotFoundError, FileExistsError, RuntimeError) as exc:
        parser.exit(2, f"fitness-rag: {exc}\n")


if __name__ == "__main__":
    main()
