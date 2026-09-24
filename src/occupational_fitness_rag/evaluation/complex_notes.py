"""Exercise raw-note intake and separately score unconstrained indicator discovery.

Engineering development labels are deliberately never given to the workflow or
retriever. Exact rule-bound citation coverage is not a retrieval accuracy metric.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from statistics import mean

from occupational_fitness_rag.evaluation.retrieval_study import score_sources
from occupational_fitness_rag.pipeline.workflow import OccupationalFitnessWorkflow
from occupational_fitness_rag.provenance import digest, write_json
from occupational_fitness_rag.retrieval.indicators import IndicatorRetriever
from occupational_fitness_rag.schemas.indicator import IndicatorRequest


def check_fact(facts, check):
    fact = facts.get(check["field"], {"status": "unknown", "value": None})
    present = fact["status"] == "present"
    kind = check["kind"]
    if kind == "not_present":
        passed = not present
    elif kind == "not_true":
        passed = not (present and fact["value"] is True)
    elif kind == "not_value":
        passed = not (present and fact["value"] == check["value"])
    elif kind == "equals":
        passed = present and type(fact["value"]) is type(check["value"])
        passed = passed and fact["value"] == check["value"]
    else:
        raise ValueError(f"Unknown fact check: {kind}")
    return {**check, "passed": passed, "actual_status": fact["status"], "actual": fact["value"]}


def render_report(report, output):
    def cell(value):
        return escape(str(value))

    rows = []
    for row in report["workflow"]:
        link = Path(row["bundle"]).as_posix() + "/draft_report.html"
        rows.append(
            f'<tr><td><a href="{cell(link)}">{cell(row["case_id"])}</a></td>'
            f"<td>{cell(row['route'])}</td><td>{row['ranking_calls']}</td>"
            f"<td>{cell(row['semantic_review_status'])}</td>"
            f"<td>{sum(c['passed'] for c in row['fact_checks'])}/{len(row['fact_checks'])}</td>"
            f"<td>{cell(row['routing_check'])}</td></tr>"
        )
    summaries = []
    for method in ("vector", "bm25", "hybrid"):
        for k in (1, 3, 5):
            group = [r for r in report["discovery"] if r["method"] == method and r["top_k"] == k]
            if group:
                summaries.append(
                    f"<tr><td>{method}</td><td>{k}</td><td>{len(group)}</td>"
                    f"<td>{mean(r['recall_at_k'] for r in group):.1%}</td>"
                    f"<td>{mean(r['mrr'] for r in group):.3f}</td></tr>"
                )
    details = []
    for row in report["discovery"]:
        if row["top_k"] == 5:
            details.append(
                f"<details><summary>{cell(row['query_id'])} / {row['method']} / "
                f"Recall@5 {row['recall_at_k']:.0%}</summary><p>{cell(row['query'])}</p>"
                f"<pre>{cell(json.dumps(row, indent=2))}</pre></details>"
            )
    html = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Complex Notes | Occupational Fitness Platform</title>
<style>body{font:16px/1.6 system-ui;color:#193344;background:#f3f6f8;margin:0}
main{max-width:1120px;margin:auto;padding:36px 24px}h1{font-size:32px;letter-spacing:-1px}
section,details{background:white;border:1px solid #dce4e8;border-radius:8px;padding:20px;margin:16px 0}
table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;padding:12px;border-bottom:1px solid #e1e7ec}
a{color:#11617d}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}.scroll{overflow-x:auto}
summary{cursor:pointer;font-weight:600}.muted{color:#536975}</style><main>
<p class="muted">OCCUPATIONAL FITNESS PLATFORM / ENGINEERING VALIDATION</p>
<h1>Complex nurse-note stress test</h1>"""
    html += f"<p>Profile: {cell(report['profile'])}. Generated: {cell(report['created_at'])}</p>"
    html += """<p>Synthetic development cases; source labels await independent review.
Recall measures labelled guideline retrieval, not clinical accuracy. An abstention check
passing means that an unsupported fact was withheld, not that extraction succeeded.</p>
<p><a href="results.json">Full results and provenance</a></p>
<section><h2>Raw-note workflow</h2><p>Open a case to inspect its note, model audits,
rules, ranked candidates and original guideline citations. Controls should use the fast
path unless a recorded model failure requires human review.</p><div class="scroll"><table>
<tr><th>Case</th><th>Route</th><th>Ranking calls</th><th>Semantic review</th><th>Fact checks</th><th>Routing check</th></tr>"""
    html += "".join(rows) + "</table></div></section>"
    html += """<section><h2>Indicator discovery comparison</h2><p>Each query is a manually
annotated, exact paragraph from the note, searched within its module. This isolates
retrieval performance and does not measure automatic passage-selection accuracy.
Expected source IDs are supplied only to scoring. Rule-bound exact citations are excluded.</p>
<table><tr><th>Method</th><th>Top K</th><th>Queries</th><th>Mean source recall</th><th>MRR</th></tr>"""
    html += "".join(summaries) + "</table></section><h2>Inspectable ranked results</h2>"
    html += "".join(details) + "</main></html>"
    (output / "index.html").write_text(html, encoding="utf-8")


def run_complex_notes(workflow, fixture_path, output, *, profile, only=None, discovery=True):
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    cases = [c for c in fixture["cases"] if not only or c["id"] in only]
    if not cases or len({c["id"] for c in cases}) != len(cases):
        raise ValueError("Select unique existing case IDs")
    for case in cases:
        for query in case["queries"]:
            if not set(query["expected_source_ids"]) <= workflow.catalogue.units.keys():
                raise ValueError("Unknown expected source label")
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": "1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile,
        "fixture_sha256": digest(fixture),
        "index_sha256": workflow.catalogue.index_sha256,
        "ruleset_sha256": workflow.book.sha256,
        "config": workflow.config.model_dump(mode="json"),
        "clinical_review_status": fixture["clinical_review_status"],
        "independent_clinical_gold": False,
        "workflow": [],
        "discovery": [],
    }
    retriever = IndicatorRetriever(workflow) if discovery else None
    notes = workflow.root / "data/cases/complex_nurse_notes"
    notes.mkdir(parents=True, exist_ok=True)
    for case in cases:
        text = "\n\n".join(case["paragraphs"]) + "\n"
        note_path = notes / (case["id"] + ".txt")
        note_path.write_text(text, encoding="utf-8")
        bundle = workflow.run_file(note_path, output / "runs", modules=case["modules"])

        def read(name):
            return json.loads((bundle / name).read_text(encoding="utf-8"))

        facts, rule, evidence = (
            read("structured_case.json"),
            read("rule_result.json"),
            read("evidence_pack.json"),
        )
        review, extraction = read("llm_semantic_review.json"), read("llm_extraction_audit.json")
        ranked = evidence["retrieval"]["ranking_calls"] > 0
        status = "passed" if ranked == case["expect_ranking"] else "failed"
        if not case["expect_ranking"] and review["status"] in {
            "unavailable_or_invalid",
            "skipped_context_budget",
        }:
            status = "inconclusive_model_failure"
        report["workflow"].append(
            {
                "case_id": case["id"],
                "modules": case["modules"],
                "challenges": case["challenges"],
                "bundle": bundle.relative_to(output).as_posix(),
                "route": rule["route"],
                "assessment_outcome": rule["assessment_outcome"],
                "ranking_calls": evidence["retrieval"]["ranking_calls"],
                "queries_with_fact_quotes": sum(
                    any(
                        s["quote"] in (item["semantic_query"] or "")
                        for f in facts["facts"].values()
                        for s in f["evidence"]
                    )
                    for item in evidence["evidence_items"]
                    if item["semantic_query"]
                ),
                "queries_with_narrative": sum(
                    "Unverified source narrative" in (item["semantic_query"] or "")
                    for item in evidence["evidence_items"]
                ),
                "extraction_status": extraction["status"],
                "semantic_review_status": review["status"],
                "fact_checks": [check_fact(facts["facts"], c) for c in case["checks"]],
                "routing_check": status,
            }
        )
        if retriever:
            for number, query in enumerate(case["queries"], 1):
                passage = case["paragraphs"][query["paragraph"]]
                start = sum(len(p) + 2 for p in case["paragraphs"][: query["paragraph"]])
                request = IndicatorRequest(
                    case_id=case["id"],
                    indicator_id=f"{case['id']}-Q{number}",
                    module=query["module"],
                    source_document=note_path.name,
                    source_text=text,
                    start=start,
                    end=start + len(passage),
                    top_k=5,
                    expand_references=False,
                )
                for method in ("vector", "bm25", "hybrid"):
                    result = retriever.retrieve(request, method=method)
                    for k in (1, 3, 5):
                        candidates = result.ranked_candidates[:k]
                        report["discovery"].append(
                            {
                                "case_id": case["id"],
                                "query_id": request.indicator_id,
                                "module": request.module,
                                "query": result.query,
                                "method": method,
                                "top_k": k,
                                "filters": result.filters,
                                "expected_source_ids": query["expected_source_ids"],
                                "ranked_candidates": candidates,
                                **score_sources(
                                    [r["source_ids"] for r in candidates],
                                    query["expected_source_ids"],
                                ),
                            }
                        )
        write_json(output / "results.json", report)
        render_report(report, output)
        print(json.dumps(report["workflow"][-1]), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/workflow.yaml")
    parser.add_argument("--fixture", default="data/cases/gold/complex_notes.json")
    parser.add_argument("--output", default="outputs/evaluation/complex_notes/live")
    parser.add_argument("--profile", default="live")
    parser.add_argument("--only", nargs="*")
    parser.add_argument("--no-discovery", action="store_true")
    args = parser.parse_args()
    workflow = OccupationalFitnessWorkflow(args.config)
    # Report prose generation is irrelevant to intake/retrieval evaluation.
    workflow.config.llm.narrative_enabled = False
    run_complex_notes(
        workflow,
        Path(args.fixture),
        Path(args.output),
        profile=args.profile,
        only=args.only,
        discovery=not args.no_discovery,
    )


if __name__ == "__main__":
    main()
