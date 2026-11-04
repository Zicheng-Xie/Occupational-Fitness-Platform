"""Join frozen baseline and external graph rankings; score only after execution."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from html import escape
from pathlib import Path

from occupational_fitness_rag.evaluation.graph_contract import (
    file_hash,
    fingerprint,
    validate_records,
    verify_index,
)
from occupational_fitness_rag.provenance import write_json

METHODS = ("vector", "bm25", "hybrid", "graph_local", "lightrag", "graphrag")


def score(rows, queries, units, references):
    scored = []
    qmap = {q["query_id"]: q for q in queries}
    for row in rows:
        q = qmap[row["query_id"]]
        required = {s["source_id"] for s in references[q["case_id"]]["reference_payload"]["guideline_evidence"]
                    if s["module"] == q["module"]}
        item = {k: row[k] for k in ("query_id", "case_id", "module", "method", "status")}
        item["cohort"] = "complex_validation" if row["case_id"].startswith("VAL-MIX-") else "engineering"
        item["reference_sources"] = sorted(required)
        item["returned_sources"] = len(row["source_ids"])
        for k in (5, 10):
            ids = row["source_ids"][:k]
            covered = {sid for source in ids for sid in [source, *units[source].get("covers_source_ids", [])]}
            item[f"exact_recall_{k}"] = len(required & set(ids)) / len(required) if required else None
            item[f"coverage_recall_{k}"] = len(required & covered) / len(required) if required else None
        scored.append(item)
    metrics = []
    for method in METHODS:
        group = [r for r in scored if r["method"] == method]
        labels = [r for r in group if r["reference_sources"]]
        metrics.append({"method": method, "recorded": len(group),
                        "completed": sum(r["status"] == "completed" for r in group), "labeled_scopes": len(labels),
                        "empty_rankings": sum(r["status"] == "completed" and r["returned_sources"] == 0 for r in group),
                        **{key: sum(r[key] for r in labels) / len(labels) if labels else None
                           for key in ("exact_recall_5", "exact_recall_10", "coverage_recall_5", "coverage_recall_10")},
                        "fully_covered_5": sum(r["coverage_recall_5"] == 1 for r in labels)})
    return scored, metrics


def observed_costs(rows, graph_dir):
    calls = [json.loads(line) for line in (graph_dir / "model_calls.jsonl").read_text(encoding="utf-8").splitlines()]
    costs = []
    for method in METHODS:
        selected = [r for r in rows if r["method"] == method]
        observed = [r for r in calls if r["phase"]["method"] == method]
        indexes = [json.loads(path.read_bytes()) for path in (graph_dir / "indexes" / method).glob("*/index_manifest.json")]
        costs.append({"method": method,
                      "ranking_or_retrieval_seconds": sum(r.get("retrieval_seconds", r.get("ranking_seconds_excluding_shared_embeddings", 0)) for r in selected),
                      "index_construction_seconds": sum(i["construction"]["seconds"] for i in indexes),
                      "external_model_calls": len(observed),
                      "graph_completion_calls": sum("chat" in r["route"] for r in observed),
                      "external_embedding_calls": sum("embed" in r["route"] for r in observed),
                      "failed_http_calls": sum(r["http_status"] != 200 for r in observed),
                      "shared_baseline_embedding_cost_excluded": method in METHODS[:4]})
    return costs


def completion_quality(calls, units):
    warnings = []
    for number, call in enumerate(calls, 1):
        if "chat" not in call["route"]:
            continue
        try:
            response = json.loads(call["raw_response"])
        except json.JSONDecodeError:
            continue
        reason = response.get("done_reason")
        if reason is None and response.get("choices"):
            reason = response["choices"][0].get("finish_reason")
        if reason not in {"length", "max_tokens"}:
            continue
        text = '\n'.join(m.get("content", "") for m in call["request"].get("messages", []) if isinstance(m.get("content"), str))
        warnings.append({"call_number": number, **call["phase"], "finish_reason": reason,
                         "output_tokens": response.get("eval_count", response.get("usage", {}).get("completion_tokens")),
                         "request_sha256": call["request_sha256"],
                         "literal_source_text_matches": [u["source_id"] for u in units if u["module"] == call["phase"]["module"] and u["evidence_text"] in text]})
    return {"truncated_completion_calls": len(warnings), "warnings": warnings,
            "interpretation": ("Native frameworks may retain partial entity/relationship extraction after a length stop. Original-source mapping is a separate check. These budgeted graph configurations require a larger-output sensitivity check before a method recommendation; no unrestricted graph-completeness claim is made." if warnings else "No length-limited native completion was recorded. Transport completion and original-source mapping do not prove semantic graph completeness; independent source and clinical review remain pending.")}


def audit_indexes(root, graph_dir, corpus):
    records = []
    for path in sorted((graph_dir / "indexes").glob("*/*/index_manifest.json")):
        work, module, method = path.parent, path.parent.name, path.parent.parent.name
        mapping = json.loads((work / "source_mapping.json").read_bytes())
        expected = {u["source_id"] for u in corpus["units"] if u["module"] == module}
        mapped = {sid for item in mapping.values() for sid in item["source_ids"]}
        if mapped != expected:
            raise ValueError("External index original-source inventory differs")
        if method == "lightrag":
            tree = ET.parse(work / module / "graph_chunk_entity_relation.graphml")
            size = {"entities": sum(node.tag.endswith("}node") for node in tree.iter()),
                    "relationships": sum(node.tag.endswith("}edge") for node in tree.iter())}
        else:
            code = ("import pandas as p,json,sys; from pathlib import Path; w=Path(sys.argv[1]);"
                    "print(json.dumps({n:len(p.read_parquet(w/(n+'.parquet'))) for n in ('entities','relationships')}))")
            size = json.loads(subprocess.check_output([str(root / ".runtime/graphrag/Scripts/python.exe"),
                                                       "-X", "utf8", "-c", code, str(work / "output")], text=True))
        records.append({"method": method, "module": module, "original_sources": len(mapped),
                        "text_unit_mappings": len(mapping), **size,
                        "index_manifest_sha256": file_hash(path),
                        "source_mapping_sha256": file_hash(work / "source_mapping.json")})
    return records


def build(root, baseline_dir, graph_dir, output, reference_path):
    root, baseline_dir, graph_dir, output = [Path(p).resolve() for p in (root, baseline_dir, graph_dir, output)]
    if not output.is_relative_to(root / "outputs/experiments") or output.exists():
        raise ValueError("Use a new, separate experiment report directory")
    ba = json.loads((baseline_dir / "execution_audit.json").read_bytes())
    ga = json.loads((graph_dir / "summary.json").read_bytes())
    bm, gm = [json.loads((p / "manifest.json").read_bytes()) for p in (baseline_dir, graph_dir)]
    if file_hash(baseline_dir / "manifest.json") != ba["manifest_sha256"] or file_hash(baseline_dir / "results.jsonl") != ba["results_sha256"]:
        raise ValueError("Baseline ranking identity drift")
    if fingerprint({k: v for k, v in gm.items() if k not in {"identity", "production_change"}}) != gm["identity"]:
        raise ValueError("External experiment self-identity differs")
    if file_hash(graph_dir / "results.jsonl") != ga["results_sha256"] or (ga["model_calls_sha256"] and file_hash(graph_dir / "model_calls.jsonl") != ga["model_calls_sha256"]):
        raise ValueError("External ranking or call log drift")
    if gm["baseline_audit"] != ba or gm["preparation"] != bm["preparation_artifacts"]:
        raise ValueError("External and baseline preparations differ")
    prep = root / gm["config"]["preparation_dir"]
    for name, pin in gm["preparation"]["artifacts"].items():
        if file_hash(prep / name) != pin:
            raise ValueError("Prepared inputs changed")
    corpus, queries = [json.loads((prep / name).read_bytes()) for name in ("corpus.json", "queries.json")]
    units = {u["source_id"]: u for u in corpus["units"]}
    rows = []
    for directory in (baseline_dir, graph_dir):
        rows.extend(json.loads(line) for line in (directory / "results.jsonl").read_text(encoding="utf-8").splitlines())
    planned = {(q["query_id"], method) for q in queries for method in METHODS}
    keys = {(r["query_id"], r["method"]) for r in rows}
    if len(keys) != len(rows) or keys != planned:
        raise ValueError("Six-method query inventory is incomplete or duplicated; reference scoring remains closed")
    for method in METHODS[4:]:
        validate_records([r for r in rows if r["method"] == method], queries, method, corpus["units"], gm["identity"])
        for module in {r["module"] for r in rows if r["method"] == method and r["status"] == "completed"}:
            req = json.loads((graph_dir / "requests" / f"{method}-{module}.json").read_bytes())
            verify_index(graph_dir / "indexes" / method / module, method, req["index_contracts"][module])
    for row in rows:
        if any(s not in units or units[s]["module"] != row["module"] for s in row["source_ids"]):
            raise ValueError("Unmapped or out-of-module report evidence")
    # Only after all six rankings are immutable and the inventory is complete.
    if file_hash(reference_path) != bm["reference_inputs_sha256"]:
        raise ValueError("Reference labels differ from the baseline reference version")
    references = json.loads(Path(reference_path).read_bytes())
    scored, metrics = score(rows, queries, units, references)
    cohorts = {}
    for cohort in ("engineering", "complex_validation"):
        selected = [r for r in rows if (r["case_id"].startswith("VAL-MIX-")) == (cohort == "complex_validation")]
        _, values = score(selected, queries, units, references)
        cohorts[cohort] = {"cases": len({r["case_id"] for r in selected}), "metrics": values}
    identity = {"baseline_audit": ba, "graph_summary": ga, "corpus_sha256": corpus["corpus_sha256"],
                "queries_sha256": fingerprint(queries), "references_sha256": file_hash(reference_path),
                "reporter_sha256": file_hash(__file__), "reference_loaded_after_six_method_rankings": True}
    manifest = {**identity, "identity": fingerprint(identity), "production_change": False, "judgment_calls": 0}
    output.mkdir(parents=True)
    write_json(output / "manifest.json", manifest)
    write_json(output / "corpus.json", corpus)
    write_json(output / "queries.json", queries)
    write_json(output / "retrieval_metrics.json", scored)
    (output / "rankings.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    with (output / "summary.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(metrics[0]))
        writer.writeheader()
        writer.writerows(metrics)
    index_audit = audit_indexes(root, graph_dir, corpus)
    write_json(output / "index_audit.json", index_audit)
    calls = [json.loads(line) for line in (graph_dir / "model_calls.jsonl").read_text(encoding="utf-8").splitlines()]
    quality = completion_quality(calls, corpus["units"])
    write_json(output / "graph_completion_quality.json", quality)
    summary = {"rankings": len(rows), "cases": len({q["case_id"] for q in queries}), "module_queries": len(queries),
               "metrics": metrics, "cohorts": cohorts, "costs": observed_costs(rows, graph_dir),
               "graph_completion_quality": quality,
               "statuses": dict(Counter(r["status"] for r in rows)),
               "shared_baseline_embedding_calls": ba["embedding_calls"], "external_actual_model_calls": ga["actual_model_calls"],
               "external_failed_model_calls": ga["failed_model_calls"], "external_indexes": ga["index_count"],
               "judgment_calls": 0, "production_change": False,
               "empty_rankings": sum(not r["source_ids"] for r in rows if r["status"] == "completed"),
               "clinical_review": "pending", "engineering_relevance_labels_exhaustive": False,
               "note": "Engineering reference-source recall, not fitness judgment or clinical accuracy. Unlabeled scopes have no fabricated zero score. A failed ranking has no substitute evidence. These 33 fixtures were previously observed and are not a sealed holdout."}
    write_json(output / "summary.json", summary)
    with (output / "costs.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary["costs"][0]))
        writer.writeheader()
        writer.writerows(summary["costs"])
    guide = root / corpus["source_path"]
    if file_hash(guide) != corpus["document_sha256"]:
        raise ValueError("Original guide changed before report export")
    shutil.copyfile(guide, output / "evidence_guide.pdf")
    shutil.copyfile(graph_dir / "model_calls.jsonl", output / "external_model_calls.jsonl")
    shutil.copyfile(baseline_dir / "embedding_calls.jsonl", output / "shared_embedding_calls.jsonl")
    render(output, rows, queries, units, scored, summary)
    write_json(output / "artifacts.json", {p.name: file_hash(p) for p in output.iterdir() if p.is_file()})
    return summary


def render(output, rows, queries, units, scored, summary):
    qmap = {q["query_id"]: q for q in queries}
    smap = {(r["query_id"], r["method"]): r for r in scored}
    def percent(n):
        return "Not labeled" if n is None else f"{n:.2%}"
    table = "".join("<tr>" + "".join("<td>" + escape(str(v)) + "</td>" for v in (
        m["method"], f"{m['completed']}/{m['recorded']}", m["empty_rankings"], percent(m["exact_recall_5"]),
        percent(m["coverage_recall_5"]), percent(m["coverage_recall_10"]),
        f"{m['fully_covered_5']}/{m['labeled_scopes']}")) + "</tr>" for m in summary["metrics"])
    cards = []
    for row in rows:
        q, label = qmap[row["query_id"]], smap[(row["query_id"], row["method"])]
        passages = []
        for rank, sid in enumerate(row["source_ids"][:10], 1):
            u = units[sid]
            passages.append(f'<details><summary>{rank}. {escape(sid)} · Section {escape(str(u["section"]))} · PDF {u["pdf_page"]}</summary>'
                            f'<p>Printed page {u["printed_page"]} · {escape(u["licence_context"])} · <a href="evidence_guide.pdf#page={u["pdf_page"]}">Open guide page</a></p>'
                            f'<pre>{escape(u["evidence_text"])}</pre></details>')
        cards.append(f'<article data-case="{escape(row["case_id"])}" data-module="{row["module"]}" data-method="{row["method"]}" data-status="{row["status"]}">'
                     f'<h3>{escape(row["case_id"])} / {escape(row["module"])} / {escape(row["method"])}</h3>'
                     f'<p>{escape(row["status"])} · Top-5 coverage recall: {percent(label["coverage_recall_5"])}</p>'
                     f'<details><summary>Frozen query and reference IDs</summary><pre>{escape(q["query"])}</pre><p>{escape(str(label["reference_sources"]))}</p></details>'
                     f'<p class="error">{escape(row.get("error", ""))}</p>' + "".join(passages) + '</article>')
    def select(key, values):
        return f'<label>{key.title()} <select id="{key}"><option value="">All</option>' + "".join(
            f'<option>{escape(value)}</option>' for value in sorted(values)) + '</select></label>'
    filters = "".join(select(key, {r[key] for r in rows}) for key in ("case_id", "module", "method", "status"))
    html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Six-method retrieval comparison</title>
<style>body{margin:0;background:#f4f6f9;color:#1d3041;font:15px/1.6 Arial,sans-serif}main{max-width:1240px;margin:40px auto;padding:0 24px}header,section,article{background:white;border:1px solid #dce3ea;border-radius:10px;padding:24px;margin:20px 0}h1{font-size:30px}h2{font-size:21px}h3{font-size:17px}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:12px;border-bottom:1px solid #e5eaf0}pre{white-space:pre-wrap;font:13px/1.6 Consolas,monospace;background:#f6f8fb;padding:16px}details{padding:10px 0;border-bottom:1px solid #e5eaf0}summary{cursor:pointer}label{display:inline-block;margin:8px 16px 8px 0}select{padding:8px}.error{color:#a13d29}a{color:#185780}.muted{color:#586c7e}</style>
<main><header><p class="muted">Occupational Fitness Platform · Experimental retrieval</p><h1>Six retrieval methods, one frozen evidence corpus</h1>'''
    html += f'<p>{summary["cases"]} cases · {summary["module_queries"]} common module queries · {summary["rankings"]} ranking records · {summary["external_indexes"]} external graph indexes</p>'
    html += '<p>Engineering reference-source recall. Fitness judgment comparison has not run on these rankings. Clinical review is pending.</p></header>'
    html += '<section><h2>Source retrieval results</h2><p>Macro averages use only the 45 source-labeled scopes. The remaining 32 scopes are not assigned invented relevance labels. Exact recall and full original-text coverage are different measures. Completed means the retrieval executed; empty results are counted separately.</p><table><thead><tr><th>Method</th><th>Completed</th><th>Empty</th><th>Exact R@5</th><th>Coverage R@5</th><th>Coverage R@10</th><th>Fully covered @5</th></tr></thead><tbody>' + table + '</tbody></table></section>'
    for cohort, group in summary["cohorts"].items():
        cohort_rows = ''.join('<tr><td>' + m["method"] + '</td><td>' + percent(m["coverage_recall_5"]) + '</td><td>'
                              + percent(m["coverage_recall_10"]) + '</td><td>' + str(m["labeled_scopes"]) + '</td></tr>' for m in group["metrics"])
        html += f'<section><h2>{escape(cohort.replace("_", " ").title())}: {group["cases"]} cases</h2><table><tr><th>Method</th><th>Coverage R@5</th><th>Coverage R@10</th><th>Labeled module scopes</th></tr>{cohort_rows}</table></section>'
    html += f'<section><h2>Observed execution cost</h2><p>Shared baseline embedding calls: {summary["shared_baseline_embedding_calls"]}. External framework calls: {summary["external_actual_model_calls"]}; HTTP failures: {summary["external_failed_model_calls"]}. No judgment calls were made. Costs include graph construction and query processing; these are observed workstation costs, not an isolated latency benchmark.</p><a href="summary.csv">Summary CSV</a> · <a href="rankings.jsonl">Raw rankings</a> · <a href="retrieval_metrics.json">Per-scope metrics</a> · <a href="external_model_calls.jsonl">External calls</a> · <a href="shared_embedding_calls.jsonl">Shared embedding calls</a> · <a href="manifest.json">Version manifest</a></section>'
    cost_rows = ''.join(f'<tr><td>{r["method"]}</td><td>{r["index_construction_seconds"]:.2f}</td><td>{r["ranking_or_retrieval_seconds"]:.2f}</td><td>{r["graph_completion_calls"]}</td><td>{r["external_embedding_calls"]}</td></tr>' for r in summary["costs"])
    html += '<section><h2>Method costs</h2><p>Seconds are observed serial workstation timings. Baseline ranking time excludes the single shared embedding stage. Graph retrieval includes framework query processing and verification. Zero baseline graph calls does not mean zero shared embedding cost.</p><table><tr><th>Method</th><th>Index seconds</th><th>Ranking/retrieval seconds</th><th>Graph model calls</th><th>External embedding calls</th></tr>' + cost_rows + '</table><a href="costs.csv">Cost records CSV</a></section>'
    html += '<section><h2>Graph source integrity</h2><p>Framework entities and relationships are used to find original passages. Their generated descriptions are never substituted for original guideline evidence. <a href="index_audit.json">Inspect module document mappings and native graph sizes</a>.</p></section>'
    html += f'<section style="background:#fff8eb;border-color:#e8d8b4"><h2>Graph construction quality flags</h2><p>{summary["graph_completion_quality"]["truncated_completion_calls"]} model completions reached their output limit. {escape(summary["graph_completion_quality"]["interpretation"])}</p><a href="graph_completion_quality.json">Completion audit and any affected calls</a></section>'
    html += '<section><h2>Inspect the same case across methods</h2>' + filters + '<p id="count"></p></section><div id="cards">' + "".join(cards) + '</div></main>'
    html += '''<script>const keys=['case_id','module','method','status'];function filter(){let n=0;document.querySelectorAll('article').forEach(a=>{const ok=keys.every(k=>!document.getElementById(k).value||a.dataset[k==='case_id'?'case':k]===document.getElementById(k).value);a.hidden=!ok;if(ok)n++});document.getElementById('count').textContent=n+' ranking records shown'}keys.forEach(k=>document.getElementById(k).addEventListener('change',filter));filter();</script></html>'''
    (output / "index.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default="outputs/experiments/shared_retrieval_v1")
    parser.add_argument("--external", default="outputs/experiments/external_graph_retrieval_v2")
    parser.add_argument("--output", default="outputs/experiments/six_method_retrieval_v1")
    parser.add_argument("--references", default="outputs/experiments/source_literal_retrieval_v1/frozen_inputs.json")
    args = parser.parse_args()
    print(json.dumps(build(Path.cwd(), args.baseline, args.external, args.output, args.references), indent=2))
