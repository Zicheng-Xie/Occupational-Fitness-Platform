"""Measure the second-pass reviewer with explicitly seeded extraction errors.

This isolates reviewer behavior; it does not measure end-to-end clinical accuracy.
"""

import json
from time import perf_counter

from occupational_fitness_rag.case_intake.semantic_review import semantic_review
from occupational_fitness_rag.case_intake.traceable import extract_traceable_text, valid_value
from occupational_fitness_rag.provenance import digest, write_json
from occupational_fitness_rag.schemas.workflow import ClinicalCase, Fact, TextSpan


def seeded_case(label, specs):
    case = extract_traceable_text(
        label["text"], label["id"], "synthetic-review-fixture.txt", specs, modules=[label["module"]]
    )
    facts = dict(case.facts)
    for item in label["overrides"]:
        key = item["field"]
        if key not in specs:
            raise ValueError("Fixture uses an unknown field")
        if item.get("status") == "unknown":
            facts[key] = Fact(unit=specs[key].get("unit"))
            continue
        if not valid_value(key, item["value"], specs):
            raise ValueError("Fixture uses an invalid field type")
        start = case.source_text.index(item["quote"])
        end = start + len(item["quote"])
        facts[key] = Fact(
            value=item["value"],
            status="present",
            unit=specs[key].get("unit"),
            evidence=[
                TextSpan(
                    start=start,
                    end=end,
                    quote=item["quote"],
                    line_start=case.source_text.count("\n", 0, start) + 1,
                    line_end=case.source_text.count("\n", 0, end - 1) + 1,
                )
            ],
            method="synthetic_review_test_seed",
        )
    return ClinicalCase.model_validate({**case.model_dump(), "facts": facts})


def run_semantic_review_study(workflow, gold_path, output):
    fixture = json.loads(gold_path.read_text(encoding="utf-8"))
    # Explicit CLI opt-in, independent of the assessment's offline LLM setting.
    config = workflow.config.llm.model_copy(
        update={"enabled": True, "semantic_review_enabled": True}
    )
    rows = []
    for label in fixture["cases"]:
        case = seeded_case(label, workflow.book.field_specs)
        before = digest(case)
        started = perf_counter()
        reviewed, audit = semantic_review(case, workflow.book.field_specs, config)
        expected = set(label["expected_issue_fields"])
        actual = {issue["field"] for issue in audit["issues"]}
        completed = audit["status"] in {"completed_no_issues", "requires_confirmation"}
        rows.append(
            {
                "case_id": label["id"],
                "module": label["module"],
                "expected_issue_fields": sorted(expected),
                "flagged_fields": sorted(actual),
                "expected_fields_detected": sorted(expected & actual),
                "expected_fields_missed": sorted(expected - actual),
                "additional_flagged_fields": sorted(actual - expected),
                "exact_field_match": completed and expected == actual,
                "completed": completed,
                "seconds": round(perf_counter() - started, 3),
                "input_case_sha256": before,
                "reviewed_case_sha256": digest(reviewed),
                "audit": audit,
            }
        )
        if digest(case) != before:
            raise RuntimeError("Semantic review mutated its input")
    finished = [r for r in rows if r["completed"]]
    detected = sum(len(r["expected_fields_detected"]) for r in finished)
    expected_count = sum(len(r["expected_issue_fields"]) for r in finished)
    flagged = sum(len(r["flagged_fields"]) for r in finished)
    all_expected = sum(len(r["expected_issue_fields"]) for r in rows)
    controls = [r for r in rows if not r["expected_issue_fields"]]
    result = {
        "schema_version": "1.0.0",
        "cases": len(rows),
        "completed": len(finished),
        "fixture_sha256": digest(fixture),
        "model": config.model,
        "label_origin": fixture["label_origin"],
        "clinical_validation": False,
        "exact_field_matches": sum(r["exact_field_match"] for r in rows),
        "review_completion_rate": len(finished) / len(rows) if rows else None,
        "seeded_issue_recall_all": detected / all_expected if all_expected else None,
        "clean_controls": len(controls),
        "clean_controls_completed": sum(r["completed"] for r in controls),
        "clean_controls_with_flags": sum(bool(r["flagged_fields"]) for r in controls),
        "seeded_issue_recall_completed": detected / expected_count if expected_count else None,
        "label_precision_completed": detected / flagged if flagged else None,
        "limitations": [
            "Small synthetic development set with deliberately seeded extraction errors.",
            "Measures extraction review, not clinical outcomes or end-to-end extraction accuracy.",
            "Expected fields are not sent to the model; additional flags require human adjudication.",
            "Using the same model for extraction and review can preserve correlated errors.",
            "Failed or skipped reviews are counted separately, never as successful checks.",
        ],
        "rows": rows,
    }
    write_json(output, result)
    return {
        "report": str(output),
        **{
            k: result[k]
            for k in (
                "cases",
                "completed",
                "exact_field_matches",
                "seeded_issue_recall_completed",
                "label_precision_completed",
            )
        },
    }
