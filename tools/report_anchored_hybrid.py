"""Report frozen no-MMR retrieval ablations against preserved original methods.

Reference labels are opened only after all method inventories and original
source scopes have been validated. This tool performs no retrieval or model
calls and does not choose a winning variant from the observed labels.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from html import escape
from pathlib import Path

from occupational_fitness_rag.evaluation.evidence_selection import select_documented_evidence
from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.provenance import digest, write_json
from tools.prepare_retrieval_judgments import common_evidence
from tools.report_planned_hybrid import evaluate, paired_changes, summarize

SIX_METHODS = ("vector", "bm25", "hybrid", "graph_local", "lightrag", "graphrag")
PARENT_METHOD = "planned_hybrid"
NO_MMR_METHOD = "planned_hybrid_no_diversity"


def verify_bundle(directory, *, six=False):
    """Reject changed files, unsafe artifact paths and manifest identity drift."""
    directory = Path(directory).resolve()
    pins = json.loads((directory / "artifacts.json").read_bytes())
    for name, expected in pins.items():
        target = (directory / name).resolve()
        if not target.is_relative_to(directory) or file_hash(target) != expected:
            raise ValueError("Frozen experiment artifact changed or escaped: " + name)
    if "manifest.json" not in pins:
        raise ValueError("Frozen artifact inventory lacks its manifest")
    manifest = json.loads((directory / "manifest.json").read_bytes())
    excluded = {"identity", "production_change"} | ({"judgment_calls"} if six else set())
    if digest({k: v for k, v in manifest.items() if k not in excluded}) != manifest["identity"]:
        raise ValueError("Frozen experiment manifest self-identity differs")
    return manifest, pins


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]


def validate_rankings(rows, queries, units, methods, identity=None):
    """Validate complete per-method inventories before any reference is opened."""
    qmap = {q["query_id"]: q for q in queries}
    if len(qmap) != len(queries):
        raise ValueError("Repeated frozen query identity")
    expected = {(qid, method) for qid in qmap for method in methods}
    actual = [(r["query_id"], r["method"]) for r in rows]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ValueError("Ranking inventory is incomplete, repeated or unexpected")
    for row in rows:
        query = qmap[row["query_id"]]
        if (
            row["case_id"] != query["case_id"]
            or row["module"] != query["module"]
            or query.get("licence_context", "commercial") != "commercial"
            or (identity is not None and row.get("experiment_identity") != identity)
        ):
            raise ValueError("Ranking query scope or experiment identity differs")
        ids = row["source_ids"]
        if len(ids) != len(set(ids)) or len(ids) > 10:
            raise ValueError("Repeated source or evidence exceeds the Top-10 budget")
        if row["status"] not in {"completed", "failed"}:
            raise ValueError("Unknown ranking execution status")
        if (row["status"] == "completed" and not ids) or (row["status"] == "failed" and ids):
            raise ValueError("Empty completed evidence or substituted failed evidence")
        for sid in ids:
            if (
                sid not in units
                or units[sid]["module"] != query["module"]
                or units[sid].get("licence_context") not in {"commercial", "shared"}
            ):
                raise ValueError("Unmapped or out-of-scope original source")
        if "original_text_hashes" in row and row["original_text_hashes"] != {
            sid: units[sid]["text_sha256"] for sid in ids
        }:
            raise ValueError("Retrieved original text fingerprint differs")


def write_csv(path, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        writer.writerows(rows)


def evidence_costs(rows, units, patients):
    """Replay the existing case-level Top-5/9000-byte allocation without judging."""
    records, metrics = [], []
    for method in dict.fromkeys(row["method"] for row in rows):
        selected = [row for row in rows if row["method"] == method]
        byte_counts = [
            sum(len(units[sid]["evidence_text"].encode("utf-8")) for sid in row["source_ids"][:5])
            for row in selected
            if row["status"] == "completed"
        ]
        cases = []
        for case_id, patient in patients.items():
            rankings = [row for row in selected if row["case_id"] == case_id]
            record = {"case_id": case_id, "method": method}
            try:
                allocation = select_documented_evidence(patient, rankings, 5)
                _, budget = common_evidence(patient, units, allocation["source_ids"], 9000)
                record.update(status="ready", allocation=allocation, budget=budget)
                if not budget["supplied_source_ids"]:
                    record.update(
                        status="blocked",
                        error="No original evidence survived the common byte budget",
                    )
            except ValueError as exc:
                record.update(status="blocked", error=str(exc))
            records.append(record)
            cases.append(record)
        ready = [row for row in cases if row["status"] == "ready"]
        budgeted = [row for row in cases if "budget" in row]
        metrics.append(
            {
                "method": method,
                "module_query_records": len(selected),
                "mean_top5_original_utf8_bytes": sum(byte_counts) / len(byte_counts)
                if byte_counts
                else None,
                "max_top5_original_utf8_bytes": max(byte_counts, default=None),
                "cases": len(cases),
                "ready_case_allocations": len(ready),
                "blocked_case_allocations": len(cases) - len(ready),
                "cases_with_budget_exclusions": sum(
                    bool(row["budget"]["excluded_by_byte_budget"]) for row in budgeted
                ),
                "excluded_original_units": sum(
                    len(row["budget"]["excluded_by_byte_budget"]) for row in budgeted
                ),
                "mean_supplied_evidence_json_utf8_bytes": sum(
                    row["budget"]["evidence_utf8_bytes"] for row in ready
                )
                / len(ready)
                if ready
                else None,
            }
        )
    return records, metrics


def build(root, six_dir, parent_dir, new_dir, reference_path, output):
    root, six_dir, parent_dir, new_dir, output = [
        Path(p).resolve() for p in (root, six_dir, parent_dir, new_dir, output)
    ]
    if output.exists() or not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Use a fresh experimental report directory")
    six_manifest, six_pins = verify_bundle(six_dir, six=True)
    parent_manifest, parent_pins = verify_bundle(parent_dir)
    manifest, new_pins = verify_bundle(new_dir)
    if (
        manifest["parent_identity"] != parent_manifest["identity"]
        or manifest["parent_artifacts_sha256"] != file_hash(parent_dir / "artifacts.json")
        or manifest.get("labels_available_to_ranker") is not False
    ):
        raise ValueError("New rankings are not bound to the frozen label-free parent")
    corpus, queries = [
        json.loads((new_dir / name).read_bytes()) for name in ("corpus.json", "queries.json")
    ]
    if len(queries) != 77:
        raise ValueError("The planned comparison requires all 77 shared module queries")
    for directory in (six_dir, parent_dir):
        for name, value in (("corpus.json", corpus), ("queries.json", queries)):
            if json.loads((directory / name).read_bytes()) != value:
                raise ValueError("Experiments use different frozen corpus or query inputs")
    if manifest.get("query_ids") != [q["query_id"] for q in queries]:
        raise ValueError("New manifest query inventory differs")
    units = {unit["source_id"]: unit for unit in corpus["units"]}
    if len(units) != len(corpus["units"]):
        raise ValueError("Repeated corpus source identity")
    variants = [v["method"] for v in manifest["config"]["variants"]]
    primary = manifest["config"]["primary_candidate"]
    if not variants or len(set(variants)) != len(variants) or primary not in variants:
        raise ValueError("All predefined variants and their primary candidate are required")
    if set(variants) & {*SIX_METHODS, PARENT_METHOD, NO_MMR_METHOD}:
        raise ValueError("A new ablation cannot replace an existing method identity")
    original = read_rows(six_dir / "rankings.jsonl")
    parent = read_rows(parent_dir / "results.jsonl")
    new = read_rows(new_dir / "results.jsonl")
    validate_rankings(original, queries, units, SIX_METHODS)
    validate_rankings(parent, queries, units, [PARENT_METHOD], parent_manifest["identity"])
    validate_rankings(new, queries, units, variants, manifest["identity"])
    no_mmr = [
        {**row, "method": NO_MMR_METHOD, "source_ids": row["without_diversity_source_ids"]}
        for row in parent
    ]
    # The parent's text-hash map describes its MMR selection, not this ablation.
    for row in no_mmr:
        row.pop("original_text_hashes", None)
        row.pop("ranked_sources", None)
        row["events"] = [
            {
                "stage": "remove_final_mmr",
                "parent_method": PARENT_METHOD,
                "source_ids": row["source_ids"],
                "note": "Saved final fused ranking before MMR; parent MMR scores do not describe this ablation",
            }
        ]
    validate_rankings(no_mmr, queries, units, [NO_MMR_METHOD])
    rows = [*original, *parent, *no_mmr, *new]
    patient_dir = root / parent_manifest["config"]["preparation_dir"]
    patient_path = patient_dir / "patients.json"
    expected_patient_hash = parent_manifest["imported"]["preparation"]["artifacts"]["patients.json"]
    if (
        file_hash(patient_path) != expected_patient_hash
        or json.loads((patient_dir / "queries.json").read_bytes()) != queries
    ):
        raise ValueError("Frozen patients or patient module queries changed")
    patients = json.loads(patient_path.read_bytes())
    if set(patients) != {q["case_id"] for q in queries}:
        raise ValueError("Patient and retrieval case inventories differ")
    budgets, cost_metrics = evidence_costs(rows, units, patients)
    # All rank inventories are now immutable and validated. Labels enter here.
    if file_hash(reference_path) != six_manifest["references_sha256"]:
        raise ValueError("Engineering reference labels changed")
    references = json.loads(Path(reference_path).read_bytes())
    scored = evaluate(rows, queries, units, references)
    paired = [
        {
            "baseline": baseline,
            "candidate": candidate,
            **paired_changes(scored, baseline, candidate),
        }
        for baseline in ("hybrid", NO_MMR_METHOD)
        for candidate in variants
    ]
    summary = {
        "primary_candidate": primary,
        "predefined_variants": variants,
        "preserved_original_methods": list(SIX_METHODS),
        "preserved_parent_methods": [PARENT_METHOD, NO_MMR_METHOD],
        "ranking_records": len(rows),
        "new_ablation_records": len(new),
        "cases": len({q["case_id"] for q in queries}),
        "module_queries": len(queries),
        "metrics": summarize(scored),
        "paired_changes": paired,
        "cohorts": {
            name: summarize([r for r in scored if r["cohort"] == name])
            for name in ("engineering", "complex_validation")
        },
        "diseases": {
            name: summarize([r for r in scored if r["module"] == name])
            for name in sorted({q["module"] for q in queries})
        },
        "new_execution": json.loads((new_dir / "summary.json").read_bytes()),
        "cost_metrics": cost_metrics,
        "evidence_budget_policy": "Existing documented-module round robin; five whole original units per case, 9000 UTF-8 JSON bytes, no backfill",
        "judgment_calls": 0,
        "production_change": False,
        "interpretation": "Engineering reference-source recall on observed development fixtures, not clinical accuracy or fitness classification accuracy. The complex validation cohort has already been observed and is not a sealed holdout. Coverage includes verified original-text containment; exact source-ID recall is reported separately. All predefined outcomes are retained, including regressions. The primary candidate was named in the configuration before reference scoring.",
    }
    identity = {
        "six_method_identity": six_manifest["identity"],
        "parent_identity": parent_manifest["identity"],
        "new_identity": manifest["identity"],
        "six_artifacts_sha256": file_hash(six_dir / "artifacts.json"),
        "parent_artifacts_sha256": file_hash(parent_dir / "artifacts.json"),
        "new_artifacts_sha256": file_hash(new_dir / "artifacts.json"),
        "references_sha256": file_hash(reference_path),
        "reporter_sha256": file_hash(__file__),
        "scoring_source_sha256": file_hash(Path(__file__).with_name("report_planned_hybrid.py")),
        "patient_inputs_sha256": expected_patient_hash,
        "evidence_allocation_source_sha256": file_hash(
            root / "src/occupational_fitness_rag/evaluation/evidence_selection.py"
        ),
        "evidence_budget_source_sha256": file_hash(root / "tools/prepare_retrieval_judgments.py"),
        "references_opened_after_complete_rank_inventory": True,
    }
    # Detect any input drift before writing a report that appears finalized.
    for directory, pins, six in (
        (six_dir, six_pins, True),
        (parent_dir, parent_pins, False),
        (new_dir, new_pins, False),
    ):
        if verify_bundle(directory, six=six)[1] != pins:
            raise ValueError("Input artifact inventory changed during scoring")
    output.mkdir(parents=True)
    write_json(
        output / "manifest.json",
        {**identity, "identity": digest(identity), "production_change": False},
    )
    write_json(output / "summary.json", summary)
    write_json(output / "retrieval_metrics.json", scored)
    write_json(output / "paired_changes.json", paired)
    write_json(output / "case_evidence_budgets.json", budgets)
    write_csv(output / "summary.csv", summary["metrics"])
    write_csv(
        output / "paired_changes.csv", [r for comparison in paired for r in comparison["rows"]]
    )
    write_csv(
        output / "cohort_metrics.csv",
        [
            {"cohort": name, **row}
            for name, metrics in summary["cohorts"].items()
            for row in metrics
        ],
    )
    write_csv(
        output / "disease_metrics.csv",
        [
            {"module": name, **row}
            for name, metrics in summary["diseases"].items()
            for row in metrics
        ],
    )
    write_csv(output / "evidence_cost_metrics.csv", cost_metrics)
    for name in ("corpus.json", "queries.json", "config.yaml", "channels.json"):
        if (new_dir / name).exists():
            shutil.copyfile(new_dir / name, output / name)
    shutil.copyfile(six_dir / "evidence_guide.pdf", output / "evidence_guide.pdf")
    shutil.copyfile(__file__, output / "reporter_source.py")
    shutil.copyfile(
        Path(__file__).with_name("report_planned_hybrid.py"), output / "scoring_source.py"
    )
    (output / "rankings.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False, allow_nan=False) + "\n" for r in rows),
        encoding="utf-8",
    )
    render(output, rows, queries, units, scored, summary, budgets)
    write_json(
        output / "artifacts.json",
        {
            p.name: file_hash(p)
            for p in output.iterdir()
            if p.is_file() and p.name != "artifacts.json"
        },
    )
    return summary


def render(output, rows, queries, units, scored, summary, budgets=None):
    def metric_table(metrics):
        def pct(value):
            return "Not labeled" if value is None else f"{value:.2%}"

        return (
            '<div class="table-wrap"><table><thead><tr><th>Method</th><th>Completed</th><th>Exact R@5</th><th>Exact R@10</th><th>Coverage R@5</th><th>Coverage R@10</th><th>Fully covered @5</th></tr></thead><tbody>'
            + "".join(
                f'<tr class="{"primary" if r["method"] == summary["primary_candidate"] else ""}"><td>{escape(r["method"])}</td><td>{r["completed"]}/{r["records"]}</td><td>{pct(r["exact_recall_5"])}</td><td>{pct(r["exact_recall_10"])}</td><td>{pct(r["coverage_recall_5"])}</td><td>{pct(r["coverage_recall_10"])}</td><td>{r["fully_covered_5"]}/{r["labeled_scopes"]}</td></tr>'
                for r in metrics
            )
            + "</tbody></table></div>"
        )

    groups = "".join(
        f"<details><summary>{escape(kind)}: {escape(name)}</summary>{metric_table(metrics)}</details>"
        for kind, values in (("Cohort", summary["cohorts"]), ("Disease", summary["diseases"]))
        for name, metrics in values.items()
    )
    paired = "".join(
        f"<tr><td>{escape(p['candidate'])}</td><td>{escape(p['baseline'])}</td>"
        + "".join(
            f"<td>{p['counts'].get(key, 0)}</td>"
            for key in ("improved", "regressed", "unchanged", "unlabeled")
        )
        + "</tr>"
        for p in summary["paired_changes"]
    )
    choices = [*summary["predefined_variants"], PARENT_METHOD, NO_MMR_METHOD, *SIX_METHODS]
    payload = {
        "rows": rows,
        "queries": queries,
        "units": units,
        "scored": scored,
        "budgets": budgets or [],
        "primary": summary["primary_candidate"],
    }
    data = (
        json.dumps(payload, ensure_ascii=False, allow_nan=False)
        .replace("<", "\\u003c")
        .replace("&", "\\u0026")
    )
    html = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>No-MMR retrieval development | Occupational Fitness Platform</title><style>
:root{font-family:Arial,Helvetica,sans-serif;color:#203344;background:#f2f5f7;font-size:14px;line-height:1.6}*{box-sizing:border-box}body{margin:0}main{max-width:1440px;margin:32px auto;padding:0 28px}header,section{background:#fff;border:1px solid #dce4e9;border-radius:8px;padding:26px;margin-bottom:22px}header{border-top:4px solid #245776}h1{font-size:29px;line-height:1.25;margin:12px 0}h2{font-size:19px;margin-top:0}h3{font-size:16px}p{margin:8px 0}.eyebrow,.muted{color:#607385}.eyebrow{font-size:11px;letter-spacing:1.3px}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:12px}td,th{padding:11px;text-align:left;border-bottom:1px solid #dfe6eb;white-space:nowrap}th{background:#f4f7f9;font-weight:600}.primary{background:#edf5fa}details{border-bottom:1px solid #e1e7ec;padding:8px 0}summary{cursor:pointer;padding:8px 0}label{display:inline-flex;flex-direction:column;gap:6px;margin:8px 18px 12px 0;font-weight:600}select{max-width:420px;padding:9px;border:1px solid #ccd7df;border-radius:4px;color:inherit;background:white;font:inherit}.compare{display:grid;grid-template-columns:1fr 1fr;gap:24px}.panel{min-width:0;border:1px solid #dbe4eb;border-radius:6px;padding:18px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f8fa;padding:14px;font:12px/1.7 Consolas,monospace}.kpis{display:flex;gap:32px;flex-wrap:wrap;margin-top:18px}.kpis strong{display:block;font-size:24px}a{color:#216082}.tag{display:inline-block;background:#eef3f7;border-radius:3px;padding:2px 8px}.error{color:#9c3b32}@media(max-width:900px){.compare{grid-template-columns:1fr}main{padding:0 12px}header,section{padding:18px}}[hidden]{display:none}</style></head><body><main>"""
    html += f'<header><p class="eyebrow">OCCUPATIONAL FITNESS PLATFORM · EXPERIMENTAL RETRIEVAL</p><h1>Anchored fusion without MMR</h1><p>{escape(summary["interpretation"])}</p><div class="kpis"><div><strong>{summary["cases"]}</strong>shared cases</div><div><strong>{summary["module_queries"]}</strong>module queries</div><div><strong>{summary["new_ablation_records"]}</strong>new variant rankings</div><div><strong>0</strong>new model calls</div></div></header>'
    html += f"<section><h2>Original-source retrieval comparison</h2><p>The highlighted method is the predefined primary candidate. Failed conditions remain in the denominator. Unlabeled scopes are excluded from recall, and listed separately.</p>{metric_table(summary['metrics'])}</section>"
    html += "<section><h2>Cohort and disease breakdown</h2>" + groups + "</section>"
    html += (
        '<section><h2>Paired source-coverage changes at Top 5</h2><p>Counts are module-query comparisons. Repeated development testing does not establish performance on unseen patients.</p><div class="table-wrap"><table><tr><th>Candidate</th><th>Baseline</th><th>Improved</th><th>Regressed</th><th>Unchanged</th><th>Unlabeled</th></tr>'
        + paired
        + "</table></div></section>"
    )
    html += (
        "<section><h2>Evidence size and downstream context budget</h2><p>"
        + escape(summary["evidence_budget_policy"])
        + '. Module-level coverage is measured before this separate case-level allocation. A recall increase may supply longer passages and does not establish a judgment improvement.</p><div class="table-wrap"><table><tr><th>Method</th><th>Mean Top-5 original bytes</th><th>Maximum</th><th>Ready cases</th><th>Cases with exclusions</th><th>Excluded units</th></tr>'
        + "".join(
            f"<tr><td>{escape(row['method'])}</td><td>{row['mean_top5_original_utf8_bytes']:.0f}</td><td>{row['max_top5_original_utf8_bytes']}</td><td>{row['ready_case_allocations']}/{row['cases']}</td><td>{row['cases_with_budget_exclusions']}</td><td>{row['excluded_original_units']}</td></tr>"
            if row["mean_top5_original_utf8_bytes"] is not None
            else f'<tr><td>{escape(row["method"])}</td><td colspan="5">No completed ranking</td></tr>'
            for row in summary["cost_metrics"]
        )
        + '</table></div><p><a href="evidence_cost_metrics.csv">Evidence cost CSV</a> · <a href="case_evidence_budgets.json">Actual case-level allocations and exclusions</a></p></section>'
    )
    html += (
        '<section><h2>Compare the same patient and query</h2><label>Case<select id="case"></select></label><label>Disease<select id="module"></select></label><label>Candidate<select id="method">'
        + "".join(f'<option value="{escape(m)}">{escape(m)}</option>' for m in choices)
        + '</select></label><label>Coverage change<select id="change"><option value="">All</option><option>improved</option><option>regressed</option><option>unchanged</option><option>unlabeled</option></select></label><p id="comparison-status" class="muted"></p><div id="comparison"></div></section>'
    )
    html += (
        '<section><h2>Audit trail and execution scope</h2><p>Original query, source scope and real saved embeddings are shared. The new rankings run on the CPU using retained search channels; model inference is not rerun. No production configuration or original ranking is replaced.</p><p><a href="summary.csv">Aggregate CSV</a> · <a href="cohort_metrics.csv">Cohort CSV</a> · <a href="disease_metrics.csv">Disease CSV</a> · <a href="paired_changes.csv">Paired CSV</a> · <a href="retrieval_metrics.json">Scored records</a> · <a href="rankings.jsonl">Raw rankings and traces</a> · <a href="manifest.json">Frozen identities</a> · <a href="evidence_guide.pdf">Guideline PDF</a></p><details><summary>New execution accounting</summary><pre>'
        + escape(json.dumps(summary["new_execution"], indent=2))
        + "</pre></details></section>"
    )
    html += '<script id="report-data" type="application/json">' + data + "</script>"
    html += """<script>
const d=JSON.parse(document.getElementById('report-data').textContent),$=id=>document.getElementById(id),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),pct=v=>v==null?'Not labeled':(v*100).toFixed(2)+'%';
const find=(qid,m)=>d.rows.find(r=>r.query_id===qid&&r.method===m),score=(qid,m)=>d.scored.find(r=>r.query_id===qid&&r.method===m);
function state(q,m){const a=score(q,'hybrid').coverage_recall_5,b=score(q,m).coverage_recall_5;return a==null||b==null?'unlabeled':b-a>1e-12?'improved':a-b>1e-12?'regressed':'unchanged'}
function options(el,vals){const old=el.value;el.innerHTML=vals.map(v=>'<option value="'+esc(v)+'">'+esc(v)+'</option>').join('');if(vals.includes(old))el.value=old}
options($('case'),[...new Set(d.queries.map(q=>q.case_id))]);$('method').value=d.primary;
function panel(q,m){const r=find(q.query_id,m),s=score(q.query_id,m),b=d.budgets.find(x=>x.case_id===q.case_id&&x.method===m);return '<div class="panel"><h3>'+esc(m)+'</h3><p>Coverage R@5 '+pct(s.coverage_recall_5)+' · Exact R@5 '+pct(s.exact_recall_5)+'</p><p class="'+(r.status==='failed'?'error':'muted')+'">'+esc(r.error||r.status)+'</p>'+r.source_ids.slice(0,10).map((sid,i)=>{const u=d.units[sid];return '<details><summary>'+ (i+1)+'. '+esc(sid)+' <span class="tag">'+(i<5?'Top 5':'Top 10 only')+'</span></summary><p>Section '+esc(u.section)+' · Printed page '+esc(u.printed_page)+' · <a href="evidence_guide.pdf#page='+Number(u.pdf_page)+'">PDF '+Number(u.pdf_page)+'</a></p><p>Verified contained source IDs: '+esc((u.covers_source_ids||[]).join(', ')||'None')+'</p><pre>'+esc(u.evidence_text)+'</pre></details>'}).join('')+'<details><summary>Case-level evidence allocation at 9000 bytes</summary><pre>'+esc(JSON.stringify(b||{status:'unavailable'},null,2))+'</pre></details></div>'}
function render(){const c=$('case').value,m=$('method').value;options($('module'),d.queries.filter(q=>q.case_id===c).map(q=>q.module));const q=d.queries.find(q=>q.case_id===c&&q.module===$('module').value),change=state(q.query_id,m);if($('change').value&&$('change').value!==change){$('comparison-status').textContent='Selected query has '+change+' coverage. Choose another case or clear the change filter.';$('comparison').innerHTML='';return}const a=find(q.query_id,'hybrid'),b=find(q.query_id,m),added=b.source_ids.slice(0,5).filter(x=>!a.source_ids.slice(0,5).includes(x)),removed=a.source_ids.slice(0,5).filter(x=>!b.source_ids.slice(0,5).includes(x));$('comparison-status').textContent='Coverage @5: '+change+' · Same frozen patient facts and query · Original text shown in full';$('comparison').innerHTML='<details><summary>Frozen query</summary><pre>'+esc(q.query)+'</pre></details><p>Added @5: '+esc(added.join(', ')||'None')+'</p><p>Removed @5: '+esc(removed.join(', ')||'None')+'</p><div class="compare">'+panel(q,'hybrid')+panel(q,m)+'</div><details><summary>Candidate strategy, source scores and selection trace</summary><pre>'+esc(JSON.stringify({diagnostics:b.diagnostics,ranked_sources:b.ranked_sources,events:b.events},null,2))+'</pre></details>'}
['case','module','method','change'].forEach(id=>$(id).addEventListener('change',render));render();
</script></main></body></html>"""
    (Path(output) / "index.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--six", default="outputs/experiments/six_method_retrieval_v2")
    parser.add_argument("--parent", default="outputs/experiments/planned_hybrid_v1")
    parser.add_argument("--additional", default="outputs/experiments/anchored_hybrid_v2")
    parser.add_argument(
        "--references", default="outputs/experiments/source_literal_retrieval_v1/frozen_inputs.json"
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = build(Path.cwd(), args.six, args.parent, args.additional, args.references, args.output)
    print(
        json.dumps(
            {k: result[k] for k in ("primary_candidate", "ranking_records", "metrics")}, indent=2
        )
    )
