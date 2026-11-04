"""Diagnose upstream fact quarantine without changing frozen comparison inputs."""

import argparse
import json
from pathlib import Path

from occupational_fitness_rag.case_intake.traceable import extract_traceable_file
from occupational_fitness_rag.ingestion.source_catalogue import SourceCatalogue
from occupational_fitness_rag.pipeline.config import load_workflow_config
from occupational_fitness_rag.provenance import write_json
from occupational_fitness_rag.red_flag import RedFlagEvaluator
from occupational_fitness_rag.rules.engine import RuleBook


def audit_upstream(output: Path):
    root = Path(__file__).resolve().parents[3]
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    config, _ = load_workflow_config(str(root / manifest["config"]["workflow_config"]))
    book = RuleBook(root / config.rules)
    catalogue = SourceCatalogue(root, root / config.catalogue)
    corpus = json.loads((output / "corpus.json").read_text(encoding="utf-8"))
    if (
        catalogue.index_sha256 != corpus["production_catalogue_sha256"]
        or catalogue.ruleset_sha256 != book.sha256
    ):
        raise ValueError(
            "Upstream audit rules or source catalogue differ from the experiment version"
        )
    evaluator = RedFlagEvaluator(book)
    labels = json.loads((output / "labels.json").read_text(encoding="utf-8"))
    rows = []
    for label in labels:
        frozen = json.loads(
            (output / "frozen_cases" / f"{label['case_id']}.json").read_text(encoding="utf-8")
        )
        original = extract_traceable_file(
            root / label["input"],
            book.field_specs,
            None if label["module"] == "all" else [label["module"]],
        )
        result = evaluator.evaluate(original)
        changed = []
        for field, fact in original.facts.items():
            frozen_fact = frozen["case"]["facts"].get(field, {})
            if fact.status == "present" and (
                frozen_fact.get("status") != "present" or frozen_fact.get("value") != fact.value
            ):
                changed.append(
                    {"field": field, "before": fact.model_dump(mode="json"), "frozen": frozen_fact}
                )
        rows.append(
            {
                "case_id": label["case_id"],
                "cohort": label["cohort"],
                "reference": label["expected_outcome"],
                "deterministic_outcome": str(result.assessment_outcome),
                "frozen_outcome": frozen["rule_outcome"],
                "changed_fields": changed,
                "facts_quarantined": frozen["semantic_review"].get("facts_quarantined", False),
                "case_sha256": frozen["case_sha256"],
            }
        )
    report = {
        "rules_sha256": book.sha256,
        "frozen_inputs_modified": False,
        "interpretation": "A difference after model review is not evidence of retrieval failure or an incorrect reference label",
        "cases": rows,
        "deterministic_reference_agreement": sum(
            r["reference"] == r["deterministic_outcome"] for r in rows
        ),
        "frozen_reference_agreement": sum(r["reference"] == r["frozen_outcome"] for r in rows),
        "case_count": len(rows),
    }
    write_json(output / "upstream_audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    report = audit_upstream(parser.parse_args().output)
    print({k: v for k, v in report.items() if k != "cases"})
