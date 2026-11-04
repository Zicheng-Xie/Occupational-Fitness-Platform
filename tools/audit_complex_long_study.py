"""Audit the completed long-note study and isolate an authored-fact diagnostic.

The diagnostic deliberately supplies authored reference facts to unchanged rules.
It is not automatic extraction, an unseen test, or a new production result.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from fractions import Fraction
from html import escape
from pathlib import Path
from statistics import mean, median

from occupational_fitness_rag.case_intake.traceable import valid_value
from occupational_fitness_rag.evaluation.long_note_study import classification, source_metrics
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json
from occupational_fitness_rag.red_flag import RedFlagEvaluator
from occupational_fitness_rag.rules.engine import RuleBook
from occupational_fitness_rag.schemas.workflow import ClinicalCase, Fact, TextSpan
from tools.run_complex_long_study import read, records, verify_notes

ROOT = Path(__file__).resolve().parents[1]


def authored_case(item, label, book):
    text = (ROOT / item["input"]).read_text(encoding="utf-8")
    paragraphs = text.strip().split("\n\n")
    facts = {key: Fact(unit=spec.get("unit")) for key, spec in book.field_specs.items()}
    for check in label["fact_checks"]:
        if check["kind"] != "equals":
            continue
        name, value = check["field"], check["value"]
        if not valid_value(name, value, book.field_specs):
            raise ValueError("Authored reference has an invalid field type/range: " + name)
        module = "hypertension" if name.startswith("cardiovascular.") else name.split(".")[0]
        quote = paragraphs[2] if module == label["primary_module"] else paragraphs[4]
        start = text.index(quote)
        span = TextSpan(
            start=start,
            end=start + len(quote),
            quote=quote,
            line_start=text.count("\n", 0, start) + 1,
            line_end=text.count("\n", 0, start + len(quote) - 1) + 1,
        )
        facts[name] = Fact(
            value=value,
            status="present",
            unit=book.field_specs[name].get("unit"),
            evidence=[span],
            method="authored_reference_fact_diagnostic",
        )
    for kind in ("uncorrected", "corrected"):
        keys = [f"vision.{kind}.{eye}.snellen" for eye in ("right", "left")]
        if all(facts[k].status == "present" for k in keys):
            best = max((facts[k].value for k in keys), key=Fraction)
            name = f"vision.{kind}.better_eye"
            facts[name] = Fact(
                value=best,
                status="present",
                unit=book.field_specs[name].get("unit"),
                evidence=[s for k in keys for s in facts[k].evidence],
                method="mathematical_snellen_derivation",
                derived_from=keys,
            )
    return ClinicalCase(
        case_id=item["case_id"],
        modules_requested=item["modules"],
        source_document=item["case_id"] + ".txt",
        source_kind="structured",
        source_text=text,
        source_sha256=item["sha256"],
        text_sha256=sha256_bytes(text.encode()),
        facts=facts,
        extraction_method="authored_reference_facts_not_automatic_intake",
    )


def latency(rows):
    values = sorted(r["seconds"] for r in rows)
    return {
        "attempts": len(values),
        "sum_seconds": sum(values),
        "mean_seconds": mean(values) if values else None,
        "median_seconds": median(values) if values else None,
        "p95_seconds": values[max(0, (95 * len(values) + 99) // 100 - 1)] if values else None,
    }


def run(source, output, diagnostic_only=False):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("Preserve the existing independent audit")
    plan = read(source / "plan.json")
    verify_notes(plan)
    gold = read(ROOT / plan["config"]["gold"])
    if (
        sha256_bytes((ROOT / plan["config"]["gold"]).read_bytes()) != plan["gold_sha256"]
        or digest(gold) != plan["gold_value_sha256"]
    ):
        raise ValueError("Reference labels changed")
    labels = {r["case_id"]: r for r in gold["cases"]}
    book = RuleBook(ROOT / "configs/rules/austroads_commercial_v1.yaml")
    evaluator = RedFlagEvaluator(book)
    diagnostic = []
    for item in plan["inputs"]:
        case = authored_case(item, labels[item["case_id"]], book)
        result = evaluator.evaluate(case)
        diagnostic.append(
            {
                "case_id": item["case_id"],
                "status": "completed",
                "assessment_outcome": result.assessment_outcome.value,
                "fact_source": "authored_engineering_reference_not_model_extraction",
                "actual_model_calls": 0,
                "triggered_rule_ids": [r.rule_id for r in result.triggered_rules],
            }
        )
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "authored_fact_diagnostic.json", diagnostic)
    diagnostic_metrics = classification(diagnostic, labels, "workflow")
    if diagnostic_only:
        write_json(
            output / "summary.json",
            {
                "diagnostic_only": True,
                "cases": 200,
                "diagnostic_metrics": diagnostic_metrics,
                "automatic_extraction_accuracy": None,
                "clinical_accuracy": None,
                "production_change": False,
            },
        )
        return diagnostic_metrics
    summary = read(source / "summary.json")
    if not summary["complete"]:
        raise ValueError("Do not audit a partial run as completed")
    retrieval, workflow, judgments = [
        records(source / name, plan["identity"])
        for name in ("retrieval.jsonl", "workflow.jsonl", "judgments.jsonl")
    ]
    expected = {
        (r["case_id"], m, method)
        for r in plan["inputs"]
        for m in r["modules"]
        for method in ("vector", "bm25", "hybrid")
    }
    assert (
        len(retrieval) == 720
        and {(r["case_id"], r["module"], r["method"]) for r in retrieval} == expected
    )
    assert len(workflow) == 200 and len(judgments) == 200
    assert {r["case_id"] for r in workflow} == set(labels) == {r["case_id"] for r in judgments}
    for name, pin in plan["sources"].items():
        assert sha256_bytes((ROOT / name).read_bytes()) == pin, name
    for path, key in [
        ("configs/rules/austroads_commercial_v1.yaml", "rules_sha256"),
        ("data/knowledge/processed/source_catalogue.json", "catalogue_sha256"),
        ("data/knowledge/raw/ap_g56_22.pdf", "guideline_sha256"),
        (plan["config"]["corpus"], "corpus_file_sha256"),
        (plan["config"]["workflow"], "base_workflow_sha256"),
    ]:
        assert sha256_bytes((ROOT / path).read_bytes()) == plan[key], path
    checks = {
        "all_720_ranking_conditions_accounted_for": True,
        "all_200_workflow_and_200_judgment_conditions_accounted_for": True,
        "original_24_notes_unchanged": True,
        "all_200_new_note_fingerprints_unchanged": True,
        "frozen_sources_unchanged": True,
        "actual_model_responses_not_replaced_by_reference_answers": True,
    }
    for kind, rows in (("workflow", workflow), ("judgment", judgments)):
        correct = 0
        for r in rows:
            actual = (
                r.get("assessment_outcome")
                if kind == "workflow"
                else r.get("answer", {}).get("assessment_outcome")
            )
            correct += (
                r["status"] == "completed" and actual == labels[r["case_id"]]["expected_outcome"]
            )
        assert correct == summary[kind + "_metrics"]["correct"]
    units = {u["source_id"]: u for u in read(source / "corpus.json")["units"]}
    type_names = Counter()
    withheld = Counter()
    examples = []
    missing_call_audits = 0
    for r in workflow:
        if r["status"] != "completed":
            continue
        bundle = source / r["bundle"]
        assert (
            sha256_bytes((bundle / "run_manifest.json").read_bytes()) == r["bundle_manifest_sha256"]
        )
        manifest = read(bundle / "run_manifest.json")
        for name, pin in manifest["files"].items():
            assert sha256_bytes((bundle / name).read_bytes()) == pin, name
        audit = read(bundle / "llm_extraction_audit.json")
        if "calls" not in audit:
            missing_call_audits += 1
        for item in audit.get("withheld", []):
            withheld[item.get("reason", "unknown")] += 1
            if isinstance(item.get("value"), str) and item["value"] in {
                "boolean",
                "string",
                "number",
                "integer",
                "array",
                "list",
            }:
                type_names[item["value"]] += 1
                if len(examples) < 20:
                    examples.append(
                        {
                            "case_id": r["case_id"],
                            "field": item["field"],
                            "returned_value": item["value"],
                            "quote": item["quote"],
                            "rejection": item.get("reason"),
                        }
                    )
    packets = []
    empty_fact_reference_answers = []
    prose_source_flags = []
    for row in retrieval:
        assert len(row["source_ids"]) == len(set(row["source_ids"]))
        assert all(units[s]["module"] == row["module"] for s in row["source_ids"])
    for r in judgments:
        if r.get("request"):
            assert digest(r["request"]) == r["request_sha256"]
            assert json.loads(r["request"]["messages"][1]["content"]) == r["input_payload"]
            assert r["input_payload"]["nurse_note"] == (
                ROOT / next(i["input"] for i in plan["inputs"] if i["case_id"] == r["case_id"])
            ).read_text(encoding="utf-8")
            if "raw_response" in r:
                assert r["raw_response"]["model"] == plan["config"]["judge_model"]
            if r["status"] == "completed":
                import re

                answer = r["answer"]
                supplied = {s["source_id"] for s in r["input_payload"]["guideline_evidence"]}
                assert set(answer["source_ids"]) <= supplied
                assert (
                    set(answer["fact_fields"])
                    <= r["input_payload"]["verified_patient_facts"].keys()
                )
                if not answer["fact_fields"]:
                    empty_fact_reference_answers.append(r["case_id"])
                literals = set(re.findall(r"AFTD2022-[A-Za-z0-9-]+", answer["explanation"]))
                if literals - supplied:
                    prose_source_flags.append(
                        {
                            "case_id": r["case_id"],
                            "unrecognized_literal_ids": sorted(literals - supplied),
                        }
                    )
            ids = [u["source_id"] for u in r["input_payload"]["guideline_evidence"]]
            for module, expected_ids in labels[r["case_id"]]["expected_sources"].items():
                packets.append(
                    {
                        "case_id": r["case_id"],
                        "module": module,
                        **source_metrics(ids, expected_ids, units, 5),
                    }
                )
    baseline = (
        sum(r["expected_outcome"] == "insufficient_information" for r in labels.values()) / 200
    )
    result = {
        "source_experiment_identity": plan["identity"],
        "checks": checks,
        "source_summary_sha256": sha256_bytes((source / "summary.json").read_bytes()),
        "always_insufficient_baseline_agreement": baseline,
        "authored_fact_diagnostic_metrics": diagnostic_metrics,
        "authored_fact_diagnostic_note": "Reference facts deliberately supplied to unchanged rules: an intake-isolation diagnostic, not automatic extraction or an achieved system improvement.",
        "literal_type_names_rejected_as_values": dict(type_names),
        "withheld_proposal_reasons": dict(withheld),
        "extraction_failures_without_complete_generation_call_audit": missing_call_audits,
        "latency": {
            "retrieval": latency(retrieval),
            "workflow": latency(workflow),
            "judgment": latency(judgments),
        },
        "judge_packet_reference_coverage": mean(r["coverage_recall"] for r in packets)
        if packets
        else None,
        "judge_packet_complete_reference_scopes": sum(r["complete_coverage"] for r in packets),
        "judge_packet_scored_scopes": len(packets),
        "cases_with_judge_budget_exclusions": sum(
            bool(r.get("evidence_budget", {}).get("skipped_by_budget")) for r in judgments
        ),
        "actual_experimental_judge_attempts": sum(r["actual_judge_attempts"] for r in judgments),
        "workflow_recorded_generation_calls_lower_bound": sum(
            r.get("captured_extraction_generation_records", 0)
            + r.get("captured_review_generation_records", 0)
            for r in workflow
        ),
        "clinical_explanation_support": "pending_independent_review",
        "accepted_answers_without_a_verified_fact_reference": empty_fact_reference_answers,
        "literal_prose_source_review_flags": prose_source_flags,
        "literal_prose_flag_note": "ASCII literal check only; not a complete hallucination or entailment measure.",
        "clinical_accuracy": None,
        "production_change": False,
    }
    write_json(output / "summary.json", result)
    write_json(output / "type_name_value_examples.json", examples)
    write_json(output / "judge_packet_coverage.json", packets)
    rows = "".join(f"<tr><td>{escape(k)}</td><td>{v}</td></tr>" for k, v in type_names.items())
    html = f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>Long-note study audit | Occupational Fitness Platform</title><style>body{{font:15px/1.7 'Segoe UI',Arial;background:#f5f7fa;color:#21384a;max-width:1100px;padding:36px;margin:auto}}section{{background:white;border:1px solid #dce4eb;border-radius:8px;padding:24px;margin:20px 0}}td,th{{padding:12px;text-align:left;border-bottom:1px solid #dce4eb}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}a{{color:#25618a}}</style><h1>200-case audit and intake isolation</h1><section><p>All 200 live workflow cases, 200 experimental judgment conditions and 720 discovery conditions are accounted for. No clinical accuracy is established.</p><p>Always-insufficient reference baseline: {baseline:.1%}. This baseline is necessary because information-insufficient references are common in this stress cohort.</p><p>Authored reference facts supplied directly to unchanged rules: {diagnostic_metrics["correct"]}/200 = {diagnostic_metrics["engineering_reference_agreement_all_recorded"]:.1%}. This is a diagnostic, not an improved automatic system or an independently labelled validation.</p></section><section><h2>Rejected type names instead of actual values</h2><table><tr><th>Literal returned as a value</th><th>Rejected proposals</th></tr>{rows}</table><p><a href="type_name_value_examples.json">Inspect exact examples</a></p></section><section><h2>Full independent checks</h2><pre>{escape(json.dumps(result, indent=2))}</pre><p><a href="summary.json">Machine-readable audit</a> · <a href="authored_fact_diagnostic.json">Diagnostic outcomes</a> · <a href="judge_packet_coverage.json">Actual judge-packet coverage</a></p></section></html>"""
    (output / "index.html").write_text(html, encoding="utf-8")
    write_json(
        output / "artifacts.json",
        {
            p.name: sha256_bytes(p.read_bytes())
            for p in output.iterdir()
            if p.is_file() and p.name != "artifacts.json"
        },
    )
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", default="outputs/evaluation/complex_long_200_20261027")
    p.add_argument("--output", default="outputs/evaluation/complex_long_200_audit_20261027")
    p.add_argument("--diagnostic-only", action="store_true")
    a = p.parse_args()
    print(json.dumps(run(a.source, a.output, a.diagnostic_only), indent=2))
