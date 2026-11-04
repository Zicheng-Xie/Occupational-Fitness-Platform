"""Score frozen prefix allocations against reviewed-corpus retrieval baselines."""

from __future__ import annotations

import argparse
import json
import shutil
from html import escape
from pathlib import Path

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.provenance import digest, write_json
from tools.report_anchored_hybrid import (
    evidence_costs,
    read_rows,
    validate_rankings,
    verify_bundle,
    write_csv,
)
from tools.report_guarded_hybrid import top10_changes
from tools.report_planned_hybrid import evaluate, paired_changes, summarize
from tools.run_scope88_prefix_allocation import BASELINE_METHOD, VARIANTS, read_json, verify


def extra_criterion_audit(rows, scored, units, prior=BASELINE_METHOD):
    """Describe criteria outside incomplete engineering labels, not precision."""
    criteria = {s for s, u in units.items() if u.get("criterion_type")}
    references = {(r["query_id"], r["method"]): set(r["reference_sources"]) for r in scored}
    index = {(r["query_id"], r["method"]): r for r in rows}
    records = []
    for row in rows:
        required = references[(row["query_id"], row["method"])]
        before = index[(row["query_id"], prior)]

        def covered(record):
            return {
                x
                for s in record["source_ids"][:5]
                for x in [s, *units[s].get("covers_source_ids", [])]
            } & criteria

        after_atoms, before_atoms = covered(row), covered(before)
        records.append(
            {
                "query_id": row["query_id"],
                "case_id": row["case_id"],
                "module": row["module"],
                "method": row["method"],
                "reference_scope_labeled": bool(required),
                "top5_typed_criteria": sorted(after_atoms),
                "criteria_extra_to_engineering_reference": sorted(after_atoms - required)
                if required
                else None,
                "introduced_extra_criteria_vs_guarded_v3": sorted(
                    (after_atoms - before_atoms) - required
                )
                if required
                else None,
                "interpretation": "Additional catalogue criteria relative to incomplete engineering reference labels; not established irrelevant evidence or clinical false positives",
            }
        )
    return records


def build(shared, experiment, output, root=None):
    root = Path(root or Path.cwd()).resolve()
    shared, experiment, output = [Path(p).resolve() for p in (shared, experiment, output)]
    if output.exists() or not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Use a fresh isolated report directory")
    parent, parent_pins = verify(shared)
    manifest, pins = verify(experiment)
    if manifest["shared_identity"] != parent["identity"] or manifest[
        "shared_artifacts_sha256"
    ] != file_hash(shared / "artifacts.json"):
        raise ValueError("Allocation input lineage differs")
    if manifest["labels_loaded"] is not False or manifest["actual_new_model_calls"] != 0:
        raise ValueError("Unexpected ranking execution scope")
    corpus, queries, patients = [
        read_json(shared / name) for name in ("corpus.json", "queries.json", "patients.json")
    ]
    if any(
        read_json(experiment / name) != value
        for name, value in (
            ("corpus.json", corpus),
            ("queries.json", queries),
            ("patients.json", patients),
        )
    ):
        raise ValueError("Experiment and shared input contents differ")
    units = {u["source_id"]: u for u in corpus["units"]}
    if len(units) != 88 or len(queries) != 77 or len(patients) != 33:
        raise ValueError("Expected actual reviewed-source inventory")
    baseline_rows = read_rows(shared / "results.jsonl")
    baseline_methods = list(dict.fromkeys(r["method"] for r in baseline_rows))
    validate_rankings(baseline_rows, queries, units, baseline_methods, parent["identity"])
    new_rows = read_rows(experiment / "results.jsonl")
    validate_rankings(new_rows, queries, units, [BASELINE_METHOD, *VARIANTS], manifest["identity"])
    if any(r["status"] != "completed" for r in new_rows):
        raise ValueError("Unresolved allocation failures require an explicit failed-run report")
    primary = "scope88_prefix_criterion_v6"
    before = {r["query_id"]: r for r in new_rows if r["method"] == BASELINE_METHOD}
    for row in new_rows:
        if row["method"] == BASELINE_METHOD:
            continue
        actual_parent = before[row["query_id"]]
        if row["parent_actual_ranking_sha256"] != digest(actual_parent) or set(
            row["source_ids"]
        ) != set(actual_parent["source_ids"]):
            raise ValueError("Prefix reordering changed its actual guarded baseline")
    # Every real ranking is frozen and validated before reference labels open.
    six_manifest, _ = verify_bundle(root / "outputs/experiments/six_method_retrieval_v2", six=True)
    reference_path = root / "outputs/experiments/source_literal_retrieval_v1/frozen_inputs.json"
    if file_hash(reference_path) != six_manifest["references_sha256"]:
        raise ValueError("Engineering source-reference version differs")
    rows = [*baseline_rows, *new_rows]
    scored = evaluate(rows, queries, units, read_json(reference_path))
    metrics = summarize(scored)
    budgets, budget_metrics = evidence_costs(rows, units, patients)
    extra = extra_criterion_audit(rows, scored, units)
    summary = {
        "primary_candidate": primary,
        "baseline_method": BASELINE_METHOD,
        "cases": len(patients),
        "module_queries": len(queries),
        "original_units": 88,
        "ranking_records": len(rows),
        "new_ablation_records": len(new_rows),
        "metrics": metrics,
        "cohorts": {
            c: summarize([r for r in scored if r["cohort"] == c])
            for c in ("engineering", "complex_validation")
        },
        "diseases": {
            m: summarize([r for r in scored if r["module"] == m])
            for m in sorted({q["module"] for q in queries})
        },
        "paired_top5": [
            paired_changes(scored, base, method)
            for base in ("hybrid", BASELINE_METHOD)
            for method in VARIANTS
        ],
        "paired_top10": [
            top10_changes(scored, base, method)
            for base in ("hybrid", BASELINE_METHOD)
            for method in VARIANTS
        ],
        "evidence_budget_metrics": budget_metrics,
        "extra_criterion_audit": [
            {
                "method": method,
                "labeled_queries": len(
                    selected := [
                        r for r in extra if r["method"] == method and r["reference_scope_labeled"]
                    ]
                ),
                "mean_extra_criteria_vs_reference": sum(
                    len(r["criteria_extra_to_engineering_reference"]) for r in selected
                )
                / len(selected)
                if selected
                else None,
                "mean_introduced_extra_criteria_vs_v3": sum(
                    len(r["introduced_extra_criteria_vs_guarded_v3"]) for r in selected
                )
                / len(selected)
                if selected
                else None,
            }
            for method in dict.fromkeys(r["method"] for r in rows)
        ],
        "execution": read_json(experiment / "summary.json"),
        "scope": "Known six source-scope failures quarantined; remaining textual applicability and clinical review pending",
        "interpretation": "Engineering reference-original coverage on observed development fixtures. Corpus criterion metadata shares the catalogue underlying reference labels; broader criterion coverage alone is not patient-specific relevance, predicate entailment or clinical accuracy.",
        "actual_new_model_calls": 0,
        "judgment_calls": 0,
        "production_change": False,
    }
    if verify(shared)[1] != parent_pins or verify(experiment)[1] != pins:
        raise ValueError("Frozen inputs changed during scoring")
    output.mkdir(parents=True)
    data = {
        "kind": "reviewed_scope_prefix_allocation_comparison",
        "shared_identity": parent["identity"],
        "experiment_identity": manifest["identity"],
        "shared_artifacts_sha256": file_hash(shared / "artifacts.json"),
        "experiment_artifacts_sha256": file_hash(experiment / "artifacts.json"),
        "references_sha256": file_hash(reference_path),
        "reporter_sha256": file_hash(__file__),
        "labels_opened_after_rankings_frozen": True,
        "production_change": False,
    }
    for name, value in (
        ("manifest.json", {**data, "identity": digest(data)}),
        ("summary.json", summary),
        ("corpus.json", corpus),
        ("queries.json", queries),
        ("retrieval_metrics.json", scored),
        ("case_evidence_budgets.json", budgets),
        ("extra_criterion_audit.json", extra),
    ):
        write_json(output / name, value)
    for name, value in (
        ("summary.csv", metrics),
        ("evidence_budget_metrics.csv", budget_metrics),
        ("extra_criterion_metrics.csv", summary["extra_criterion_audit"]),
        ("paired_changes.csv", [r for pair in summary["paired_top5"] for r in pair["rows"]]),
    ):
        write_csv(output / name, value)
    (output / "rankings.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False, allow_nan=False) + "\n" for r in rows),
        encoding="utf-8",
    )
    shutil.copyfile(root / corpus["source_path"], output / "evidence_guide.pdf")
    shutil.copyfile(__file__, output / "reporter_source.py")
    render(output, rows, scored, queries, units, budgets, summary)
    write_json(
        output / "artifacts.json",
        {
            p.name: file_hash(p)
            for p in output.iterdir()
            if p.is_file() and p.name != "artifacts.json"
        },
    )
    return summary


def render(output, rows, scored, queries, units, budgets, summary):
    def pct(v):
        return "Unlabeled" if v is None else f"{v:.2%}"

    table = (
        "<table><tr><th>Method</th><th>Completed</th><th>Exact R@5</th><th>Coverage R@5</th><th>Coverage R@10</th><th>Fully covered @5</th></tr>"
        + "".join(
            f"<tr><td>{escape(m['method'])}</td><td>{m['completed']}/{m['records']}</td><td>{pct(m['exact_recall_5'])}</td><td>{pct(m['coverage_recall_5'])}</td><td>{pct(m['coverage_recall_10'])}</td><td>{m['fully_covered_5']}/{m['labeled_scopes']}</td></tr>"
            for m in summary["metrics"]
        )
        + "</table>"
    )
    methods = list(dict.fromkeys(r["method"] for r in rows))
    options = "".join(f'<option value="{escape(m)}">{escape(m)}</option>' for m in methods)
    data = json.dumps(
        {"rows": rows, "scored": scored, "queries": queries, "units": units, "budgets": budgets},
        ensure_ascii=False,
        allow_nan=False,
    ).replace("<", "\\u003c")
    html = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Reviewed-source prefix allocation | Occupational Fitness Platform</title><style>body{font:14px/1.65 Arial,sans-serif;color:#243748;background:#f4f6f8;max-width:1450px;margin:30px auto;padding:22px}main{background:white;border:1px solid #dce3ea;border-radius:8px;padding:30px}h1{font-size:29px}h2{font-size:21px}section{border-top:1px solid #dce3ea;margin-top:24px;padding-top:20px}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:9px;border-bottom:1px solid #dce3ea}select{padding:8px;max-width:330px}label{display:inline-block;margin:8px 16px 8px 0}.compare{display:grid;grid-template-columns:1fr 1fr;gap:20px}.panel{padding:18px;border:1px solid #dce3ea;min-width:0}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f8fa;padding:14px;font:12px/1.65 Consolas,monospace}summary{cursor:pointer;padding:8px 0}.notice{padding:18px;background:#eef3f7}a{color:#225b83}@media(max-width:850px){.compare{grid-template-columns:1fr}body{padding:10px}main{padding:18px}}</style><main><small>OCCUPATIONAL FITNESS PLATFORM · RETRIEVAL DEVELOPMENT</small><h1>Exact prefix allocation on reviewed sources</h1>"""
    html += (
        '<p class="notice">'
        + escape(summary["interpretation"])
        + "</p><p>88 original units · 77 fixed queries · 33 observed cases · 0 new model calls. The exact Top10 source inventory is retained; only which five originals enter the prefix can change.</p><p>"
        + escape(summary["scope"])
        + "</p><section><h2>Frozen method comparison</h2>"
        + table
        + "</section>"
    )
    html += "<section><h2>What the criterion hypothesis does</h2><p>The strict control preserves every prior Top5 original-source atom. The criterion hypothesis preserves prior Top5 typed criteria, then chooses five actual originals covering the largest number of corpus-defined criteria from the existing ten-source list. Ties prefer earlier prior ranks. This is exact evidence allocation, with no case-specific source promotion or label lookup. Background evidence can move out of the first five; additional criteria need applicability review.</p></section>"
    html += (
        '<section><h2>Same query, original evidence and budget</h2><label>Case <select id="case"></select></label><label>Disease <select id="module"></select></label><label>Baseline <select id="baseline">'
        + options
        + '</select></label><label>Candidate <select id="method">'
        + options
        + '</select></label><p id="status"></p><div id="comparison"></div></section>'
    )
    for title, value in (
        ("Cohort metrics", summary["cohorts"]),
        ("Disease metrics", summary["diseases"]),
        ("Paired Top5 changes", summary["paired_top5"]),
        ("Paired Top10 changes", summary["paired_top10"]),
        ("Whole-original evidence budgets", summary["evidence_budget_metrics"]),
        ("Additional criteria relative to incomplete labels", summary["extra_criterion_audit"]),
    ):
        html += (
            "<section><details><summary>"
            + escape(title)
            + "</summary><pre>"
            + escape(json.dumps(value, indent=2))
            + "</pre></details></section>"
        )
    html += (
        "<section><h2>Audit data</h2><p>"
        + " · ".join(
            f'<a href="{name}">{label}</a>'
            for name, label in (
                ("summary.csv", "Metrics CSV"),
                ("retrieval_metrics.json", "Scored records"),
                ("rankings.jsonl", "Raw source allocations"),
                ("extra_criterion_audit.json", "Extra-criterion review queue"),
                ("case_evidence_budgets.json", "9000-byte allocations"),
                ("manifest.json", "Version pins"),
                ("evidence_guide.pdf", "Original guideline"),
            )
        )
        + "</p></section>"
    )
    html += '<script id="report-data" type="application/json">' + data + "</script>"
    html += """<script>
const d=JSON.parse(document.getElementById('report-data').textContent),$=id=>document.getElementById(id),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),pct=v=>v==null?'Unlabeled':(v*100).toFixed(2)+'%';
const find=(q,m)=>d.rows.find(r=>r.query_id===q&&r.method===m),score=(q,m)=>d.scored.find(r=>r.query_id===q&&r.method===m);
function opts(e,values){const old=e.value;e.innerHTML=values.map(v=>'<option value="'+esc(v)+'">'+esc(v)+'</option>').join('');if(values.includes(old))e.value=old}
opts($('case'),[...new Set(d.queries.map(q=>q.case_id))]);$('baseline').value='scope88_guarded_v3';$('method').value='scope88_prefix_criterion_v6';
function panel(q,m){const r=find(q.query_id,m),s=score(q.query_id,m),b=d.budgets.find(x=>x.case_id===q.case_id&&x.method===m);return '<div class="panel"><h3>'+esc(m)+'</h3><p>Coverage R@5 '+pct(s.coverage_recall_5)+' · R@10 '+pct(s.coverage_recall_10)+' · Exact R@5 '+pct(s.exact_recall_5)+'</p>'+r.source_ids.map((sid,i)=>{const u=d.units[sid];return '<details><summary>'+(i+1)+'. '+esc(sid)+' · '+(i<5?'Top5':'Top10 only')+'</summary><p>Section '+esc(u.section)+' · Printed '+esc(u.printed_page)+' · <a href="evidence_guide.pdf#page='+Number(u.pdf_page)+'">PDF '+Number(u.pdf_page)+'</a></p><pre>'+esc(u.evidence_text)+'</pre></details>'}).join('')+'<details><summary>Actual case budget</summary><pre>'+esc(JSON.stringify(b,null,2))+'</pre></details><details><summary>Allocation trace</summary><pre>'+esc(JSON.stringify(r.diagnostics,null,2))+'</pre></details></div>'}
function render(){const c=$('case').value;opts($('module'),d.queries.filter(q=>q.case_id===c).map(q=>q.module));const q=d.queries.find(q=>q.case_id===c&&q.module===$('module').value),a=score(q.query_id,$('baseline').value),b=score(q.query_id,$('method').value);$('status').textContent='Coverage R@5 '+pct(a.coverage_recall_5)+' → '+pct(b.coverage_recall_5)+' · Same actual 88-source corpus';$('comparison').innerHTML='<details><summary>Frozen query</summary><pre>'+esc(q.query)+'</pre></details><div class="compare">'+panel(q,$('baseline').value)+panel(q,$('method').value)+'</div>'}
['case','module','baseline','method'].forEach(id=>$(id).addEventListener('change',render));render();
</script></main></html>"""
    (Path(output) / "index.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shared", required=True)
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = build(args.shared, args.experiment, args.output)
    print(
        json.dumps(
            {k: result[k] for k in ("primary_candidate", "ranking_records", "metrics")}, indent=2
        )
    )
