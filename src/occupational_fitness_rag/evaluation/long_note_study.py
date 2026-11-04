"""Metrics and report for authored long-note intake, discovery and judgment.

Reference labels are used only by these scoring/report functions. Clinical
evidence support is not inferred from identifier validity or reference agreement.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from html import escape
from statistics import mean

OUTCOMES = [
    "meets_unconditional_standard",
    "may_meet_conditional_standard",
    "temporarily_unfit",
    "does_not_meet_standard",
    "insufficient_information",
]


def value_equal(left, right):
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is bool and type(right) is bool and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(left, right, rel_tol=0, abs_tol=1e-9)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(value_equal(a, b) for a, b in zip(left, right))
    return type(left) is type(right) and left == right


def fact_checks(facts, checks):
    result = []
    for check in checks:
        actual = facts.get(check["field"], {"status": "unknown", "value": None})
        present = actual["status"] == "present"
        passed = (
            not present
            if check["kind"] == "not_present"
            else present and value_equal(actual["value"], check["value"])
        )
        result.append(
            {
                **check,
                "passed": passed,
                "actual_status": actual["status"],
                "actual_value": actual["value"],
            }
        )
    return result


def source_metrics(ranked_ids, expected, units, k):
    """Literal original-text containment coverage, separate from exact-ID recall."""
    expected = set(expected)
    if not expected:
        raise ValueError("A source-labeled query must have a nonempty reference set")
    candidates = ranked_ids[:k]
    covered, first = set(), None
    for rank, sid in enumerate(candidates, 1):
        matches = ({sid} | set(units[sid].get("covers_source_ids", []))) & expected
        covered.update(matches)
        if matches and first is None:
            first = rank
    return {
        "coverage_recall": len(covered) / len(expected),
        "exact_id_recall": len(expected & set(candidates)) / len(expected),
        "complete_coverage": float(expected <= covered),
        "hit": float(bool(covered)),
        "mrr": 1 / first if first else 0.0,
        "returned_count": len(candidates),
    }


def classification(rows, labels, kind):
    matrix = {
        actual: {pred: 0 for pred in [*OUTCOMES, "run_or_contract_failure"]} for actual in OUTCOMES
    }
    accepted = correct = appropriate_unknown = excess_unknown = permission_disagreements = 0
    families = {}
    for row in rows:
        reference = labels[row["case_id"]]["expected_outcome"]
        if kind == "workflow":
            outcome = row.get("assessment_outcome") if row["status"] == "completed" else None
        else:
            outcome = (
                row.get("answer", {}).get("assessment_outcome")
                if row["status"] == "completed"
                else None
            )
        pred = outcome or "run_or_contract_failure"
        matrix[reference][pred] += 1
        accepted += outcome is not None
        match = outcome == reference
        correct += match
        families.setdefault(labels[row["case_id"]]["family"], []).append(float(match))
        if outcome == "insufficient_information":
            appropriate_unknown += reference == outcome
            excess_unknown += reference != outcome
        permission_disagreements += reference in {
            "temporarily_unfit",
            "does_not_meet_standard",
        } and outcome in {"meets_unconditional_standard", "may_meet_conditional_standard"}
    f1, recalls = [], []
    for label in OUTCOMES:
        tp = matrix[label][label]
        fp = sum(matrix[a][label] for a in OUTCOMES if a != label)
        fn = sum(n for p, n in matrix[label].items() if p != label)
        f1.append(2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0)
        if tp + fn:
            recalls.append(tp / (tp + fn))
    return {
        "recorded": len(rows),
        "accepted": accepted,
        "failed": len(rows) - accepted,
        "correct": correct,
        "engineering_reference_agreement_all_recorded": correct / len(rows) if rows else None,
        "engineering_reference_agreement_accepted": correct / accepted if accepted else None,
        "macro_f1_fixed_five_classes": mean(f1),
        "balanced_accuracy_observed_classes": mean(recalls) if recalls else None,
        "family_macro_agreement": mean(mean(g) for g in families.values()) if families else None,
        "appropriate_information_insufficient": appropriate_unknown,
        "excess_information_insufficient": excess_unknown,
        "restriction_to_permission_disagreements": permission_disagreements,
        "confusion_matrix": matrix,
    }


def summarize(retrieval, workflow, judgments, labels, units, plan):
    retrieval_metrics = []
    for method in ("vector", "bm25", "hybrid"):
        for k in (1, 3, 5, 10):
            for module in ("all", "hypertension", "vision", "hearing", "blackout", "diabetes"):
                group = [
                    r
                    for r in retrieval
                    if r["method"] == method and (module == "all" or r["module"] == module)
                ]
                if not group:
                    continue
                scored = [
                    source_metrics(
                        r["source_ids"] if r["status"] == "completed" else [],
                        labels[r["case_id"]]["expected_sources"][r["module"]],
                        units,
                        k,
                    )
                    for r in group
                ]
                retrieval_metrics.append(
                    {
                        "method": method,
                        "module": module,
                        "top_k": k,
                        "recorded_queries": len(group),
                        "failed_queries": sum(r["status"] != "completed" for r in group),
                        **{key: mean(s[key] for s in scored) for key in scored[0]},
                    }
                )
    field_rows = [c for r in workflow for c in r.get("fact_checks", [])]
    known = [c for c in field_rows if c["kind"] == "equals"]
    withheld = [c for c in field_rows if c["kind"] == "not_present"]
    stages = {
        "retrieval": {
            "planned": sum(len(r["modules"]) for r in plan["inputs"]) * 3,
            "recorded": len(retrieval),
        },
        "workflow": {"planned": len(plan["inputs"]), "recorded": len(workflow)},
        "judgment": {"planned": len(plan["inputs"]), "recorded": len(judgments)},
    }
    return {
        "experiment_identity": plan["identity"],
        "stages": stages,
        "complete": all(s["planned"] == s["recorded"] for s in stages.values()),
        "case_count": len(plan["inputs"]),
        "scenario_families": 40,
        "variants_per_family": 5,
        "clinical_review": "pending",
        "clinical_accuracy": None,
        "retrieval_metrics": retrieval_metrics,
        "workflow_metrics": classification(workflow, labels, "workflow"),
        "judgment_metrics": classification(judgments, labels, "judgment"),
        "workflow_by_primary_module": {
            m: classification(
                [r for r in workflow if labels[r["case_id"]]["primary_module"] == m],
                labels,
                "workflow",
            )
            for m in ("hypertension", "vision", "hearing", "blackout", "diabetes")
        },
        "judgment_by_primary_module": {
            m: classification(
                [r for r in judgments if labels[r["case_id"]]["primary_module"] == m],
                labels,
                "judgment",
            )
            for m in ("hypertension", "vision", "hearing", "blackout", "diabetes")
        },
        "scored_fact_value_checks": {
            "passed": sum(c["passed"] for c in known),
            "total": len(known),
            "rate": mean(float(c["passed"]) for c in known) if known else None,
        },
        "specified_abstention_checks": {
            "passed": sum(c["passed"] for c in withheld),
            "total": len(withheld),
            "rate": mean(float(c["passed"]) for c in withheld) if withheld else None,
        },
        "live_workflow_retrieval": {
            "cases_with_rule_ranking": sum(r.get("ranking_calls", 0) > 0 for r in workflow),
            "cases_with_symptom_discovery": sum(
                r.get("symptom_discovery_calls", 0) > 0 for r in workflow
            ),
            "rule_ranking_calls": sum(r.get("ranking_calls", 0) for r in workflow),
            "symptom_discovery_calls": sum(r.get("symptom_discovery_calls", 0) for r in workflow),
        },
        "routes": dict(Counter(r.get("route", "run_failure") for r in workflow)),
        "extraction_statuses": dict(
            Counter(r.get("extraction_status", "run_failure") for r in workflow)
        ),
        "semantic_review_statuses": dict(
            Counter(r.get("semantic_review_status", "run_failure") for r in workflow)
        ),
        "observed_seconds": {
            "discovery": sum(r["seconds"] for r in retrieval),
            "workflow": sum(r["seconds"] for r in workflow),
            "experimental_judgment": sum(r["seconds"] for r in judgments),
        },
        "original_source_and_fact_identifier_validity_does_not_establish_entailment": True,
        "production_change": False,
    }


def render(output, summary, workflow, judgments, retrieval, labels, notes, units):
    def pct(value):
        return "Pending" if value is None else f"{value:.1%}"

    wmap = {r["case_id"]: r for r in workflow}
    jmap = {r["case_id"]: r for r in judgments}
    rmap = {(r["case_id"], r["module"], r["method"]): r for r in retrieval}
    stages = " · ".join(
        f"{name.title()} {s['recorded']}/{s['planned']}" for name, s in summary["stages"].items()
    )
    metrics = "".join(
        f"<tr><td>{name}</td><td>{m['correct']}/{m['recorded']}</td><td>{pct(m['engineering_reference_agreement_all_recorded'])}</td><td>{m['macro_f1_fixed_five_classes']:.3f}</td><td>{m['failed']}</td><td>{m['excess_information_insufficient']}</td><td>{m['restriction_to_permission_disagreements']}</td></tr>"
        for name, m in (
            ("Live intake + deterministic rules", summary["workflow_metrics"]),
            ("Llama + retrieved original evidence", summary["judgment_metrics"]),
        )
    )
    ranks = "".join(
        f"<tr><td>{r['method']}</td><td>{r['top_k']}</td><td>{r['recorded_queries']}</td><td>{r['coverage_recall']:.1%}</td><td>{r['exact_id_recall']:.1%}</td><td>{r['complete_coverage']:.1%}</td><td>{r['mrr']:.3f}</td><td>{r['failed_queries']}</td></tr>"
        for r in summary["retrieval_metrics"]
        if r["module"] == "all"
    )
    options = "".join(f"<option>{case}</option>" for case in labels)
    cards = []
    for case, label in labels.items():
        w, j = wmap.get(case, {}), jmap.get(case, {})
        expected = label["expected_outcome"]
        wout = w.get("assessment_outcome", "pending_or_failed")
        jout = j.get("answer", {}).get("assessment_outcome", "pending_or_failed")
        error = (
            "failure"
            if w.get("status") == "failed" or j.get("status") == "failed"
            else "disagreement"
            if w and wout != expected or j and jout != expected
            else "agreement"
            if w and j
            else "pending"
        )
        href = w.get("bundle")
        link = (
            f'<a href="{escape(href)}/draft_report.html">Open ordinary assessment report</a>'
            if href
            else "No completed assessment bundle"
        )
        rdetails = []
        for module in label["modules"]:
            for method in ("vector", "bm25", "hybrid"):
                r = rmap.get((case, module, method))
                if not r:
                    continue
                candidates = "".join(
                    f'<details><summary>Rank {rank} · {escape(sid)} · PDF {units[sid]["pdf_page"]}</summary><p><a href="evidence_guide.pdf#page={units[sid]["pdf_page"]}">Original page</a> · Section {escape(units[sid]["section"])}</p><pre>{escape(units[sid]["evidence_text"])}</pre></details>'
                    for rank, sid in enumerate(r["source_ids"], 1)
                )
                sm = source_metrics(r["source_ids"], label["expected_sources"][module], units, 5)
                rdetails.append(
                    f"<details><summary>{escape(module)} / {method} · coverage R@5 {sm['coverage_recall']:.0%}</summary><p>{escape(r.get('error', r['status']))}</p>"
                    + candidates
                    + "</details>"
                )
        cards.append(
            f'<article data-case="{case}" data-module="{label["primary_module"]}" data-status="{error}"><h2>{case}</h2><p>{escape(label["family"])} · variant {label["variant"]} · {label["complexity"]["words"]} words · modules: {escape(", ".join(label["modules"]))}</p><table><tr><th>Engineering reference</th><th>Live workflow</th><th>Experimental model</th></tr><tr><td>{expected}</td><td>{wout}</td><td>{jout}</td></tr></table><p>{link}</p><details><summary>Original synthetic nurse note</summary><pre>{escape(notes[case])}</pre></details><details><summary>Fact extraction and specified abstention checks</summary><pre>{escape(json.dumps(w.get("fact_checks", []), indent=2))}</pre></details><details><summary>Experimental judgment, exact supplied packet and raw-response status</summary><pre>{escape(json.dumps(j, indent=2))}</pre></details><details><summary>Original-source discovery rankings</summary>'
            + "".join(rdetails)
            + "</details></article>"
        )
    html = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>200 long-note stress cases | Occupational Fitness Platform</title><style>*{box-sizing:border-box}body{margin:0;background:#f5f7fa;color:#21374a;font:14px/1.65 'Segoe UI',Arial,sans-serif}main{max-width:1320px;margin:auto;padding:36px 28px}.brand{font-size:11px;letter-spacing:.12em;color:#62778a;text-transform:uppercase}h1{font-size:32px;letter-spacing:-.6px}h2{font-size:19px}section,article{background:white;border:1px solid #dce4ec;border-radius:9px;padding:24px;margin:20px 0}.notice{padding:14px 18px;border-left:3px solid #b5863d;background:#fcf8ef}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:10px;border-bottom:1px solid #e1e7ee}th{color:#60758a;font-size:12px}pre{font:12px/1.7 Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f7fa;padding:16px}a{color:#23658b}details{border-top:1px solid #e3e8ee;margin-top:12px}summary{cursor:pointer;padding:10px 0}label{display:inline-flex;flex-direction:column;margin:4px 14px 4px 0;font-size:12px}select{padding:9px;min-width:170px;background:white;border:1px solid #ccd7e1;border-radius:4px}[hidden]{display:none}.scroll{overflow:auto}@media(max-width:700px){main{padding:20px 12px}section,article{padding:16px}table{font-size:12px}}</style><main><p class="brand">Occupational Fitness Platform · Synthetic stress evaluation</p><h1>200 complex long-form nurse notes</h1>"""
    html += f'<p>{stages} · {"Complete" if summary["complete"] else "In progress; partial metrics"}</p><p class="notice">Engineering reference agreement, not clinical accuracy. These are 40 authored scenario families with five correlated variants, including 40 multi-module inputs. Gold labels are separate from uploads and model requests. Failed attempts remain in denominators. Production logic and prior experiments are unchanged.</p>'
    html += (
        '<section><h2>Assessment and experimental judgment</h2><p>The ordinary platform uses validated facts and deterministic rules. A separate Llama experiment reads those facts and whole original passages selected by broad Hybrid RRF. Its proposal never changes the ordinary report. Selected disease scopes are specified before execution; this does not measure automatic disease classification.</p><div class="scroll"><table><tr><th>Path</th><th>Correct / recorded</th><th>Reference agreement</th><th>Macro-F1</th><th>Failures</th><th>Excess insufficiency</th><th>Restriction → permission</th></tr>'
        + metrics
        + "</table></div></section>"
    )
    html += (
        '<section><h2>Guideline discovery</h2><p>Real Chroma/Ollama vectors, BM25 and their RRF fusion search the same frozen 88-original corpus. Each query is the entire long note, filtered by its predefined module and commercial/shared scope. No reference source IDs enter search. Coverage recall credits verified literal containment; exact-ID recall is shown separately. Mandatory rule citations are excluded from these ranking metrics. The corpus retains documented layout/applicability review limitations; source retrieval does not establish clinical relevance or explanation support.</p><div class="scroll"><table><tr><th>Method</th><th>K</th><th>Queries</th><th>Coverage recall</th><th>Exact-ID recall</th><th>Complete coverage</th><th>MRR</th><th>Failures</th></tr>'
        + ranks
        + "</table></div></section>"
    )
    html += '<section><h2>Audit data</h2><p><a href="summary.json">All metrics, confusion matrices and module breakdowns</a> · <a href="retrieval.jsonl">Every ranking</a> · <a href="workflow.jsonl">Every workflow result</a> · <a href="judgments.jsonl">Every model request and raw response</a> · <a href="plan.json">Version and configuration manifest</a> · <a href="scoring_labels.json">Frozen engineering references</a> · <a href="review_queue.csv">Human review queue</a></p><p>Expected-source lists are incomplete relevance judgments; recall is coverage of those references. Fact scores apply to explicitly annotated fields, not every possible fact. Identifier validity and literal heuristic flags do not prove explanation faithfulness. Independent clinical review remains pending.</p></section>'
    html += (
        f'<section><label>Case<select id="case">{options}</select></label><label>Primary module<select id="module"><option value="">All</option>'
        + "".join(
            f"<option>{m}</option>"
            for m in ["hypertension", "vision", "hearing", "blackout", "diabetes"]
        )
        + '</select></label><label>Result filter<select id="status"><option value="">All</option><option>agreement</option><option>disagreement</option><option>failure</option><option>pending</option></select></label><p id="shown"></p></section>'
        + "".join(cards)
    )
    html += """</main><script>const keys=['case','module','status'];function filter(){let n=0;document.querySelectorAll('article').forEach(a=>{a.hidden=keys.some(k=>document.getElementById(k).value&&a.dataset[k]!==document.getElementById(k).value);if(!a.hidden)n++});document.getElementById('shown').textContent=n+' cases shown'}keys.forEach(k=>document.getElementById(k).addEventListener('change',filter));filter();</script></html>"""
    (output / "index.html").write_text(html, encoding="utf-8")
