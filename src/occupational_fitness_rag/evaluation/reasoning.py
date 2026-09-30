"""Audit links from a nurse note through rule predicates to verified guideline text.

This is an engineering trace test. It does not infer new clinical facts or issue a
fitness certificate; the production rule result remains authoritative.
"""

from __future__ import annotations

import csv
import json
from html import escape
from pathlib import Path
from statistics import mean
from time import perf_counter

from occupational_fitness_rag.case_intake.traceable import extract_traceable_file
from occupational_fitness_rag.provenance import digest, write_json


def _fact_link(case, field, fact):
    quotations = [
        {
            "quote": span.quote,
            "line_start": span.line_start,
            "line_end": span.line_end,
            "start": span.start,
            "end": span.end,
        }
        for span in fact.evidence
    ]
    grounded = (
        fact.status != "present"
        or bool(quotations)
        and all(
            case.source_text[item["start"] : item["end"]] == item["quote"] for item in quotations
        )
    )
    return {
        "field": field,
        "status": fact.status,
        "value": fact.value,
        "quotations": quotations,
        "grounded_in_note": grounded,
    }


def audit_case(workflow, label):
    """Return a source-checked trace; an outcome label is optional."""
    source = (workflow.root / label["input"]).resolve()
    if not source.is_relative_to((workflow.root / "data/cases").resolve()):
        raise ValueError("Reasoning fixture points outside the case directory")
    selected = None if label["module"] == "all" else [label["module"]]
    case = extract_traceable_file(source, workflow.book.field_specs, selected)
    if case.case_id != label["case_id"]:
        raise ValueError("Reasoning fixture case ID disagrees with the source")
    before = digest(case)
    start = perf_counter()
    result, evidence, _ = workflow.assess(case)
    if digest(case) != before or evidence.integrity["rule_result_fields_modified_by_rag"]:
        raise RuntimeError("Reasoning audit mutated an authoritative input")
    by_rule = {item.rule_id: item for item in evidence.evidence_items}
    traces = []
    for rule in result.rules_evaluated:
        if rule.result not in {"triggered", "unknown"}:
            continue
        item = by_rule.get(rule.rule_id)
        facts = [
            _fact_link(case, field, fact) for field, fact in sorted(rule.observed_facts.items())
        ]
        citations = (
            []
            if item is None
            else [
                {
                    "source_id": c.source_id,
                    "source_text": c.source_text,
                    "section": c.section,
                    "printed_page": c.printed_page,
                    "pdf_page": c.pdf_page,
                    "source_path": c.source_path,
                    "verified_against_source": c.verified_against_source,
                    "matches_catalogue": (
                        c.source_id in workflow.catalogue.units
                        and workflow.catalogue.units[c.source_id]["evidence_text"] == c.source_text
                    ),
                }
                for c in item.citations
            ]
        )
        checks = {
            "patient_facts_grounded": all(f["grounded_in_note"] for f in facts),
            "rule_facts_match_case": all(
                case.facts.get(field) == fact
                for field, fact in rule.observed_facts.items()
                if field in case.facts
            ),
            "predicate_truth_matches_rule": (
                rule.condition_trace.get("predicate", {}).get("truth")
                == (True if rule.result == "triggered" else None)
            ),
            "requested_guideline_sources_bound": (
                item is not None
                and item.status == "complete"
                and set(rule.source_ids) <= {c["source_id"] for c in citations}
            ),
            "guideline_text_verified": all(
                c["verified_against_source"] and c["matches_catalogue"] for c in citations
            ),
            "rule_predicate_trace_present": bool(rule.condition_trace),
        }
        traces.append(
            {
                "rule_id": rule.rule_id,
                "module": rule.module,
                "rule_result": rule.result,
                "rule_outcome": rule.assessment_outcome,
                "reason": rule.reason,
                "condition_trace": rule.condition_trace,
                "missing_fields": rule.missing_fields,
                "patient_facts": facts,
                "guideline_evidence": citations,
                "checks": checks,
                "passed": all(checks.values()),
            }
        )
    module = next((m for m in result.modules if m.module == label["module"]), None)
    actual = module.assessment_outcome if module else result.assessment_outcome
    checks = {
        "rule_evidence_links_complete": bool(traces) and all(t["passed"] for t in traces),
        "no_unresolved_evidence_requests": not evidence.unresolved_requests,
        "case_and_rule_unchanged": digest(case) == before,
    }
    if "expected_outcome" in label:
        checks["development_label_agreement"] = actual == label["expected_outcome"]
    return {
        "case_id": case.case_id,
        "module": label["module"],
        "source_file": label["input"],
        "source_sha256": case.source_sha256,
        "patient_note": case.source_text,
        "expected_development_outcome": label.get("expected_outcome"),
        "provisional_outcome": actual,
        "overall_outcome": result.assessment_outcome,
        "route": result.route,
        "missing_fields": module.missing_fields
        if module
        else sorted({f for m in result.modules for f in m.missing_fields}),
        "rule_traces": traces,
        "checks": checks,
        "passed": all(checks.values()),
        "latency_ms": round((perf_counter() - start) * 1000, 2),
    }


def render_html(report):
    rows = []
    for record in report["records"]:
        traces = []
        for trace in record["rule_traces"]:
            facts = "".join(
                f"<li><strong>{escape(f['field'])}</strong>: {escape(str(f['value']))} "
                f"({escape(f['status'])})"
                + "".join(
                    f"<blockquote>Line {q['line_start']}: {escape(q['quote'])}</blockquote>"
                    for q in f["quotations"]
                )
                + "</li>"
                for f in trace["patient_facts"]
            )
            sources = "".join(
                f"<li><strong>{escape(c['source_id'])}</strong> · section "
                f"{escape(c['section'])} · PDF {c['pdf_page']} · printed {c['printed_page']}"
                f"<blockquote>{escape(c['source_text'])}</blockquote></li>"
                for c in trace["guideline_evidence"]
            )
            traces.append(
                f"<details><summary>{escape(trace['rule_id'])} · "
                f"{escape(trace['rule_result'])} · {escape(str(trace['rule_outcome']))}</summary>"
                f"<p>{escape(trace['reason'])}</p><h4>Patient facts</h4><ul>{facts}</ul>"
                f"<h4>Original guideline evidence</h4><ul>{sources}</ul>"
                f"<p>Source checks: {'passed' if trace['passed'] else 'failed'}</p></details>"
            )
        rows.append(
            f"<article><details><summary><strong>{escape(record['case_id'])}</strong> "
            f"· {escape(record['module'])} · {escape(str(record['provisional_outcome']))} "
            f"· {'PASS' if record['passed'] else 'REVIEW'}</summary>"
            f"<p><strong>Route:</strong> {escape(str(record['route']))} · "
            f"<strong>Missing fields:</strong> {escape(', '.join(record['missing_fields']) or 'none')}</p>"
            f"<h3>Original nurse note</h3><blockquote>{escape(record['patient_note'])}</blockquote>"
            + "".join(traces)
            + "</details></article>"
        )
    return """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Evidence-linked reasoning audit | Occupational Fitness</title>
<style>body{font:15px/1.55 system-ui;color:#213548;background:#f3f5f7;margin:0}
main{max-width:1100px;margin:0 auto;padding:34px 24px}h1{font-size:30px;letter-spacing:-.03em}
p{max-width:85ch}article{background:#fff;border:1px solid #d7e0e7;border-radius:8px;
margin:12px 0;padding:16px 20px}summary{cursor:pointer}details details{border-top:1px solid #e2e8ed;
padding:12px 0}blockquote{white-space:pre-wrap;background:#f6f9fb;border-left:3px solid #9bb6c9;
padding:10px 14px;margin:10px 0;overflow-wrap:anywhere}ul{padding-left:22px}
a{color:#255675}.kicker{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#587083}
</style><main><p class="kicker">Occupational Fitness / Engineering evaluation</p>
<h1>Evidence-linked reasoning audit</h1>""" + (
        f"<p>{report['passed']}/{report['cases']} cases passed the applicable engineering "
        "checks. The outcome is a provisional rule result for clinician review, not a "
        "fitness certificate or independent clinical accuracy measurement.</p>"
        '<p><a href="results.json">Download the complete JSON audit</a> · '
        '<a href="case_review_queue.csv">Open clinician review worksheet</a></p>'
        + "".join(rows)
        + "</main></html>"
    )


def _write_case_review_queue(path, records):
    columns = [
        "case_id",
        "module",
        "source_file",
        "nurse_note",
        "provisional_rule_outcome",
        "triggered_rule_ids",
        "missing_fields",
        "guideline_source_ids",
        "clinician_assessed_outcome",
        "clinician_verified_facts",
        "clinician_rejected_facts",
        "additional_information_required",
        "reviewer_name",
        "review_date",
        "review_notes",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for record in records:
            traces = record["rule_traces"]
            values = {
                "case_id": record["case_id"],
                "module": record["module"],
                "source_file": record["source_file"],
                "nurse_note": record["patient_note"],
                "provisional_rule_outcome": record["provisional_outcome"],
                "triggered_rule_ids": "; ".join(
                    trace["rule_id"] for trace in traces if trace["rule_result"] == "triggered"
                ),
                "missing_fields": "; ".join(record["missing_fields"]),
                "guideline_source_ids": "; ".join(
                    sorted(
                        {
                            citation["source_id"]
                            for trace in traces
                            for citation in trace["guideline_evidence"]
                        }
                    )
                ),
            }
            writer.writerow(
                {
                    key: "'" + str(value)
                    if str(value).lstrip().startswith(("=", "+", "-", "@"))
                    else value
                    for key in columns
                    if (value := values.get(key, "")) is not None
                }
            )


def run_reasoning_study(workflow, fixture_path: Path, output: Path, limit=None):
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    labels = fixture["cases"][:limit]
    if not labels or len({x["case_id"] for x in labels}) != len(labels):
        raise ValueError("Reasoning fixture must contain distinct cases")
    records = [audit_case(workflow, label) for label in labels]
    labelled = [
        r["checks"]["development_label_agreement"]
        for r in records
        if "development_label_agreement" in r["checks"]
    ]
    report = {
        "schema_version": "1.0.0",
        "evaluation_type": "source_linked_engineering_reasoning_audit",
        "clinical_validation": False,
        "independent_clinical_gold": False,
        "fixture_split": fixture.get("split"),
        "outcome_labels_present": bool(labelled),
        "fixture_sha256": digest(fixture),
        "ruleset_sha256": workflow.book.sha256,
        "index_sha256": workflow.catalogue.index_sha256,
        "retrieval_backend": workflow.config.retrieval.mode,
        "cases": len(records),
        "passed": sum(r["passed"] for r in records),
        "development_label_agreement": mean(labelled) if labelled else None,
        "source_link_pass_rate": mean(r["checks"]["rule_evidence_links_complete"] for r in records),
        "authoritative_results_modified": False,
        "limitations": [
            "Synthetic development labels are not independent clinician assessments.",
            "Trace checks verify source identity and fact quotations, not semantic entailment.",
            "The rule result is provisional and requires clinician review.",
            "This deterministic audit does not measure local-model reasoning quality.",
        ],
        "records": records,
    }
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "results.json", report)
    _write_case_review_queue(output / "case_review_queue.csv", records)
    (output / "index.html").write_text(render_html(report), encoding="utf-8")
    return {"report": str(output / "index.html"), "cases": len(records), "passed": report["passed"]}
