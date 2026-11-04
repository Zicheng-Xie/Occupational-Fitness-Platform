"""Audit and render paired retrieval refinements without changing old evidence."""

from __future__ import annotations

import json
import shutil
from html import escape

from occupational_fitness_rag.evaluation.retrieval_refinement import original_footprints
from tools import report_complex_ten_methods as original_report
from tools.complex_ten_contract import METHODS, ROOT, digest, pin, read, rows, write_json

NUMBERS = {METHODS[i]: str(i + 1) for i in (2, 3, 6, 8, 9)}
NAMES = {
    METHODS[2]: "Hybrid RRF",
    METHODS[3]: "Source graph-assisted",
    METHODS[6]: "Criterion coverage v6",
    METHODS[8]: "Neo4j frontier + criterion coverage v3",
    METHODS[9]: "PageIndex + RRF predicate navigation",
}


def pct(value):
    return "—" if value is None else f"{value * 100:.2f}%"


def report(output, parent):
    from tools.refine_complex_retrieval import SUFFIXES, TARGETS, VARIANTS, export_csv, verify

    protocol = verify(output, parent)
    queries, corpus = read(output / "queries.json"), read(output / "corpus.json")
    units = {u["source_id"]: u for u in corpus["units"]}
    baseline = [r for r in rows(output / "baseline_rankings.jsonl") if r["method"] in TARGETS]
    changed = rows(output / "rankings.jsonl")
    complete = read(output / "complete.json")
    if complete["results_sha256"] != pin(output / "rankings.jsonl"):
        raise ValueError("Observed refinement records changed")
    expected = {(q["query_id"], method) for q in queries for method in VARIANTS}
    if len(changed) != len(expected) or {(r["query_id"], r["method"]) for r in changed} != expected:
        raise ValueError("Refinement observation grid incomplete or duplicated")
    bmap = {(r["query_id"], r["method"]): r for r in baseline}
    protected = []
    for r in changed:
        old = bmap[r["query_id"], r["baseline_method"]]
        if r["parent_record_sha256"] != digest(old) or r["record_sha256"] != digest(
            {k: v for k, v in r.items() if k != "record_sha256"}
        ):
            raise ValueError("Refinement observation lineage changed")
        if r["status"] != "completed":
            continue
        footprints = original_footprints(units, r["module"])
        if len(r["source_ids"]) > 10 or len(r["source_ids"]) != len(set(r["source_ids"])):
            raise ValueError("Original passage count differs")
        checks = {}
        for k in (1, 3, 5, 10):
            before = set().union(*(footprints[s] for s in old["source_ids"][:k]))
            after = set().union(*(footprints[s] for s in r["source_ids"][:k]))
            checks[str(k)] = before <= after
        if not all(checks.values()):
            raise ValueError("A refinement dropped an earlier covered original")
        protected.append({"query_id": r["query_id"], "method": r["method"], "checkpoints": checks})
    # Labels enter only here, after the complete ranking/lineage audit.
    references = original_report.reference_map(queries, units)
    actual = baseline + changed
    all_methods = [m for base in TARGETS for m in (base, *(base + "__" + s for s in SUFFIXES))]
    original_methods = original_report.METHODS
    try:
        original_report.METHODS = all_methods
        detail, metrics = original_report.score(queries, corpus, actual, references)
        packets, packet_metrics = original_report.packet_replay(queries, actual, references, units)
    finally:
        original_report.METHODS = original_methods
    smap = {(r["query_id"], r["method"]): r for r in detail}
    pm = {(r["cohort"], r["method"]): r for r in packet_metrics}
    mm = {(r["cohort"], r["module"], r["method"]): r for r in metrics}
    changes, case_changes = [], []
    for method in VARIANTS:
        base = method.split("__", 1)[0]
        paired = []
        for q in queries:
            old, new = smap[q["query_id"], base], smap[q["query_id"], method]
            if not old["labeled"]:
                continue
            delta = {
                str(k): new[str(k)]["coverage_recall"] - old[str(k)]["coverage_recall"]
                for k in (1, 3, 5, 10)
            }
            pairs = {
                "case_id": q["case_id"],
                "query_id": q["query_id"],
                "module": q["module"],
                "method": method,
                "deltas": delta,
                "before_source_ids": old["source_ids"],
                "after_source_ids": new["source_ids"],
                "expected_source_ids": references[q["query_id"]],
            }
            case_changes.append(pairs)
            paired.append(pairs)
        a, b = mm["all", "all", base], mm["all", "all", method]
        changes.append(
            {
                "method": method,
                "baseline": base,
                "scored_queries": len(paired),
                **{
                    f"recall_{k}_delta": b[f"coverage_recall_{k}"] - a[f"coverage_recall_{k}"]
                    for k in (1, 3, 5, 10)
                },
                **{
                    f"improved_{k}": sum(r["deltas"][str(k)] > 1e-12 for r in paired)
                    for k in (5, 10)
                },
                **{
                    f"regressed_{k}": sum(r["deltas"][str(k)] < -1e-12 for r in paired)
                    for k in (1, 3, 5, 10)
                },
                "packet_coverage_delta": pm["all", method]["mean_reference_coverage"]
                - pm["all", base]["mean_reference_coverage"],
                "exact_id_5_delta": b["exact_id_recall_5"] - a["exact_id_recall_5"],
                "mrr_10_delta": b["mrr_10"] - a["mrr_10"],
                "mean_original_bytes_delta": b["mean_top5_original_bytes"]
                - a["mean_top5_original_bytes"],
            }
        )
    calls = [read(p) for p in (output / "embeddings").glob("*.json")]
    summary = {
        "protocol_identity": protocol["identity"],
        "complete": True,
        "cases": 234,
        "query_scopes": 357,
        "new_conditions": len(changed),
        "original_baselines": 10,
        "target_methods": TARGETS,
        "new_variants": VARIANTS,
        "labeled_cases": len({q["case_id"] for q in queries if references[q["query_id"]]}),
        "labeled_query_scopes": sum(bool(x) for x in references.values()),
        "metrics": metrics,
        "packet_metrics": packet_metrics,
        "paired_changes": changes,
        "failed_conditions": [r for r in changed if r["status"] != "completed"],
        "new_embedding_calls": len(calls),
        "new_embedding_input_texts": sum(len(c["request"]["input"]) for c in calls),
        "new_embedding_seconds": sum(c["seconds"] for c in calls),
        "nested_coverage_checks": len(protected) * 4,
        "new_native_graph_tree_calls": 0,
        "judgment_calls": 0,
        "production_change": False,
        "evaluation_type": "same-cohort engineering retrieval development; not independent validation or fitness accuracy",
        "cost_note": "Post-retrieval refinement seconds exclude frozen native graph/tree navigation, existing source/query embeddings and intake. New sentence embedding cost is shared and reported separately. No end-to-end speedup claim.",
        "coverage_note": "Full literal parent text can cover several nominated source IDs; exact-ID recall, original byte volume and finite-budget packet coverage are separate metrics. Unlabelled sources are not automatically irrelevant.",
    }
    write_json(output / "summary.json", summary)
    write_json(output / "scored_rankings.json", detail)
    write_json(output / "packet_replay.json", packets)
    write_json(output / "paired_case_changes.json", case_changes)
    write_json(output / "references.json", references)
    write_json(
        output / "coverage_audit.json",
        {
            "checked_successful_conditions": len(protected),
            "checks": len(protected) * 4,
            "all_retained": True,
            "records": protected,
        },
    )
    export_csv(output / "metrics.csv", metrics)
    export_csv(output / "paired_changes.csv", changes)
    write_html(output, corpus, queries, detail, summary, NAMES, NUMBERS, TARGETS, mm, pm)
    if not (output / "evidence_guide.pdf").exists():
        shutil.copyfile(ROOT / "data/knowledge/raw/ap_g56_22.pdf", output / "evidence_guide.pdf")
    print(
        json.dumps(
            {
                "new_conditions": len(changed),
                "failures": len(summary["failed_conditions"]),
                "changes": changes,
            },
            indent=2,
        )
    )
    return summary


def write_html(output, corpus, queries, detail, summary, names, numbers, targets, mm, pm):
    tables = {}
    for cohort in ("all", "new_200", "original_34"):
        content = ""
        for base in targets:
            old = mm[cohort, "all", base]
            for suffix, label in (
                ("", "Original"),
                ("__protected_completion", "Allocation only"),
                ("__literal_facets", "Allocation + literal facets"),
            ):
                method = base + suffix
                m, p = mm[cohort, "all", method], pm[cohort, method]
                content += f"<tr><td>{escape(numbers[base] + ' · ' + names[base])}<small>{label}</small></td><td>{pct(m['coverage_recall_5'])}</td><td>{pct(m['coverage_recall_10'])}</td><td>{pct(m['complete_coverage_5'])}</td><td>{pct(m['exact_id_recall_5'])}</td><td>{pct(m['mrr_10'])}</td><td>{pct(p['mean_reference_coverage'])}</td><td>{m['mean_top5_original_bytes']:.0f}</td><td>{m['mean_seconds']:.4f}</td><td>{m['failed_queries']}</td><td>{(m['coverage_recall_5'] - old['coverage_recall_5']) * 100:+.2f}</td></tr>"
        tables[cohort] = content
    payload = {
        "tables": tables,
        "corpus": corpus["units"],
        "queries": queries,
        "rankings": detail,
        "targets": targets,
        "names": names,
        "numbers": numbers,
        "changes": summary["paired_changes"],
    }
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Retrieval refinement review · Occupational Fitness Platform</title><style>
    :root{font-family:Inter,Segoe UI,Arial,sans-serif;color:#233648;background:#f5f7fa;font-size:14px}*{box-sizing:border-box}body{margin:0}header,main{max-width:1510px;margin:auto;padding:30px 38px}header{border-bottom:1px solid #dce3eb}h1{font-size:30px;letter-spacing:-.6px;margin:16px 0 10px}h2{font-size:20px}h3{font-size:16px}p{line-height:1.7}small{display:block;color:#63768b;font-size:11px;margin-top:6px}.brand{font-size:12px;font-weight:650;letter-spacing:1.4px}.status{float:right;color:#426854}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin:24px 0}.metrics div,section{background:white;border:1px solid #dde5ed;border-radius:9px;padding:23px}.metrics strong{display:block;font-size:27px;margin-bottom:7px}section{margin:22px 0}.toolbar{display:flex;gap:16px;align-items:end;flex-wrap:wrap}label{font-size:12px;color:#52677e;display:flex;flex-direction:column;gap:7px}select{padding:9px;background:white;border:1px solid #cdd8e4;border-radius:5px;max-width:340px;color:#233648}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{border-bottom:1px solid #e3e9f0;padding:13px 10px;text-align:right;white-space:nowrap}th{font-size:11px;color:#63768b;font-weight:600;text-transform:uppercase}td:first-child,th:first-child{text-align:left}tr:nth-child(3n){border-bottom:2px solid #c7d4e2;background:#f6f9fc}a{color:#245a86;text-decoration:none}a:hover{text-decoration:underline}.overflow{overflow:auto}.columns{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.card{padding:18px;border:1px solid #dce4ed;border-radius:7px}.muted{color:#61748a}.note{border-left:3px solid #8aa6bf;padding-left:16px}details{margin:10px 0;border-top:1px solid #e3e9f0;padding-top:10px}summary{cursor:pointer;font-size:12px;line-height:1.6}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.8 Segoe UI,Arial,sans-serif;background:#f7f9fc;padding:13px}#query{font-size:13px}footer{padding:30px 0;color:#61748a}button{padding:8px;background:white;border:1px solid #cdd8e4;border-radius:5px;color:#233648}@media(max-width:900px){header,main{padding:22px 15px}.columns{grid-template-columns:1fr}.metrics{grid-template-columns:1fr 1fr}}
    </style></head><body><header><span class="brand">OCCUPATIONAL FITNESS PLATFORM</span><span class="status">Experiment complete · 29 October 2026</span><h1>Protected retrieval refinement</h1><p class="muted">Five method families. The same 234 input notes, frozen patient snapshots and 88 original passages. All ten earlier methods and results remain preserved.</p></header><main>
    <div class="metrics"><div><strong>234</strong>Unchanged notes</div><div><strong>357</strong>Case / module queries</div><div><strong>3,570</strong>New paired conditions</div><div><strong>273</strong>Source-labelled query scopes</div></div>
    <section><h2>Read this comparison</h2><p>Each method has an original result, a protected-allocation ablation, and a literal-sentence-facet variant. Original passage coverage at ranks 1, 3, 5 and 10 is protected independently for every successful condition. Allocation uses source metadata and measured retrieval views; engineering reference answers are opened only after ranking.</p><p class="note">These are development-cohort retrieval results. They do not measure fitness judgment accuracy. The new 200 notes include correlated scenario variants. Native Neo4j responses and PageIndex navigation are frozen and replayed here to isolate post-retrieval changes; there are no new native graph/tree navigation calls.</p><details><summary>Metric definitions and limits</summary><p>Coverage R@K: mean fraction of each query's nominated originals covered by its first K whole passages, including verified complete literal containment. Complete@5: all nominated evidence covered. Exact ID@5: direct IDs only. MRR@10: reciprocal rank of the first passage covering any reference. Packet coverage: case-mean coverage after the unchanged five-original / 9,000-byte round-robin budget. Bytes@5: actual original UTF-8 text size; larger parents are fully charged. Sources without relevance labels are not assumed irrelevant.</p><p>Seconds show recorded original ranking time or new post-retrieval refinement time, respectively. They exclude shared intake, cached/native graph/tree navigation and shared embeddings. They are not an end-to-end latency comparison or evidence of a speedup. Exact-ID recall and ranking order can worsen despite protected original coverage.</p></details></section>
    <section id="comparison"><div class="toolbar"><h2>Paired method results</h2><label>Cohort<select id="cohort"><option value="all">All 234 notes</option><option value="new_200">New 200 notes</option><option value="original_34">Original 34 notes</option></select></label></div><div class="overflow"><table><thead><tr><th>Method / variant</th><th>Coverage R@5</th><th>Coverage R@10</th><th>Complete@5</th><th>Exact ID@5</th><th>MRR@10</th><th>Packet coverage</th><th>Bytes@5</th><th>Seconds*</th><th>Failed</th><th>R@5 Δ pp</th></tr></thead><tbody id="results"></tbody></table></div><small>*Original ranking and new post-retrieval work have different timing boundaries. Full costs and individual observations are recorded in the downloadable data.</small></section>
    <section><h2>Disease breakdown</h2><div class="overflow"><table><thead><tr><th>Method</th><th>Module</th><th>Original R@5</th><th>Facet R@5</th><th>Original R@10</th><th>Facet R@10</th></tr></thead><tbody>__DISEASE__</tbody></table></div></section>
    <section id="cases"><h2>Compare original evidence</h2><div class="toolbar"><label>Case<select id="case"></select></label><label>Method family<select id="method"></select></label><label>Requested module<select id="module"></select></label><label>Evidence limit<select id="limit"><option value="5">Top 5</option><option value="10">Top 10</option></select></label></div><details><summary>Unchanged original note</summary><pre id="query"></pre></details><div id="scope" class="muted"></div><div id="evidence" class="columns"></div></section>
    <section><h2>Reproducibility and audit</h2><p>__ACCOUNTING__</p><p>__FAILURES__</p><p>__LINKS__</p><p class="muted">No production settings, assessment rules, patient input files, old methods or previous experiment records were changed. A higher retrieval coverage does not establish that a fitness judgment is correct; that requires a separately controlled decision-model experiment.</p></section><footer>Engineering evidence review · Clinical annotation pending · Occupational Fitness Platform</footer></main><script id="data" type="application/json">__DATA__</script><script>
    const d=JSON.parse(document.getElementById('data').textContent),el=id=>document.getElementById(id),esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),units=Object.fromEntries(d.corpus.map(u=>[u.source_id,u]));
    el('results').innerHTML=d.tables.all;el('cohort').onchange=()=>el('results').innerHTML=d.tables[el('cohort').value];
    const cases=[...new Set(d.queries.map(q=>q.case_id))];el('case').innerHTML=cases.map(c=>`<option>${esc(c)}</option>`).join('');el('method').innerHTML=d.targets.map(m=>`<option value="${m}">${esc(d.numbers[m]+' · '+d.names[m])}</option>`).join('');
    function modules(){const opts=d.queries.filter(q=>q.case_id===el('case').value);el('module').innerHTML=opts.map(q=>`<option>${esc(q.module)}</option>`).join('');show()}
    function show(){let q=d.queries.find(q=>q.case_id===el('case').value&&q.module===el('module').value),m=el('method').value,k=+el('limit').value;el('query').textContent=q.query;el('evidence').innerHTML=['','__protected_completion','__literal_facets'].map((s,i)=>{let r=d.rankings.find(r=>r.query_id===q.query_id&&r.method===m+s),v=r[String(k)];return `<article class="card"><h3>${['Original','Allocation only','Allocation + literal facets'][i]}</h3><p>${r.labeled?`Reference coverage: ${(v.coverage_recall*100).toFixed(2)}% · Exact ID: ${(v.exact_id_recall*100).toFixed(2)}%`:'No nominated evidence labels; retrieval still executed.'}</p>`+r.source_ids.slice(0,k).map((sid,j)=>{let u=units[sid];return `<details><summary>Rank ${j+1} · ${esc(u.table_row||sid)}<small>${esc(sid)} · Section ${esc(u.section)} · PDF ${u.pdf_page}</small></summary><p><a href="evidence_guide.pdf#page=${u.pdf_page}" target="_blank" rel="noopener">Open original guideline page ↗</a></p><pre>${esc(u.evidence_text)}</pre><small>Complete literal children: ${esc(u.covers_source_ids.join(', ')||'None')}</small></details>`}).join('')+'</article>'}).join('');el('scope').textContent=q.module+' · '+q.cohort+' · '+q.query_id.slice(0,12)}
    el('case').onchange=modules;['method','module','limit'].forEach(id=>el(id).onchange=show);modules();
    </script></body></html>"""
    disease = ""
    for base in targets:
        for module in ("hypertension", "vision", "hearing", "blackout", "diabetes"):
            old, new = mm["all", module, base], mm["all", module, base + "__literal_facets"]
            disease += f"<tr><td>{escape(numbers[base] + ' · ' + names[base])}</td><td>{module}</td><td>{pct(old['coverage_recall_5'])}</td><td>{pct(new['coverage_recall_5'])}</td><td>{pct(old['coverage_recall_10'])}</td><td>{pct(new['coverage_recall_10'])}</td></tr>"
    links = [
        "summary.json",
        "metrics.csv",
        "paired_changes.csv",
        "paired_case_changes.json",
        "protocol.json",
        "coverage_audit.json",
        "rankings.jsonl",
        "baseline_rankings.jsonl",
        "scored_rankings.json",
        "packet_replay.json",
        "references.json",
        "corpus.json",
        "queries.json",
        "preparation.json",
    ]
    html = (
        html.replace("__DISEASE__", disease)
        .replace("__DATA__", data)
        .replace("__LINKS__", " · ".join(f'<a href="{name}">{escape(name)}</a>' for name in links))
    )
    html = html.replace(
        "__ACCOUNTING__",
        f"{summary['new_embedding_calls']} actual local embedding calls / {summary['new_embedding_input_texts']} sentence inputs; {summary['new_embedding_seconds']:.2f} shared embedding seconds. {summary['nested_coverage_checks']:,} nested full-original coverage checks passed. No new fitness judgment calls.",
    )
    html = html.replace(
        "__FAILURES__",
        f"{len(summary['failed_conditions'])} failed refinement conditions; failures remain in the raw journal and are not replaced with successes.",
    )
    (output / "index.html").write_text(html, encoding="utf-8")
