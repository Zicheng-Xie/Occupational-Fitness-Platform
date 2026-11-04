"""Compare an independently saved additional arm with immutable six-method results."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter
from html import escape
from pathlib import Path

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.evaluation.planned_hybrid import METHOD
from occupational_fitness_rag.provenance import digest, write_json


def evaluate(rows, queries, units, references):
    qmap = {q["query_id"]: q for q in queries}
    scored = []
    for row in rows:
        q = qmap[row["query_id"]]
        if row["case_id"] != q["case_id"] or row["module"] != q["module"]:
            raise ValueError("Ranking scope differs from its original query")
        required = {
            s["source_id"]
            for s in references[q["case_id"]]["reference_payload"]["guideline_evidence"]
            if s["module"] == q["module"]
        }
        ids = row["source_ids"]
        if len(ids) != len(set(ids)) or any(
            sid not in units or units[sid]["module"] != q["module"] for sid in ids
        ):
            raise ValueError("Repeated, unmapped or out-of-module original source")
        if row["status"] != "completed" and ids:
            raise ValueError("A failed retrieval cannot supply substitute evidence")
        record = {key: row[key] for key in ("query_id", "case_id", "module", "method", "status")}
        record.update(
            reference_sources=sorted(required),
            cohort="complex_validation" if q["case_id"].startswith("VAL-MIX-") else "engineering",
        )
        for k in (5, 10):
            returned = set(ids[:k])
            covered = {
                sid
                for source in ids[:k]
                for sid in [source, *units[source].get("covers_source_ids", [])]
            }
            record[f"exact_recall_{k}"] = (
                len(required & returned) / len(required) if required else None
            )
            record[f"coverage_recall_{k}"] = (
                len(required & covered) / len(required) if required else None
            )
        scored.append(record)
    return scored


def summarize(scored):
    metrics = []
    for method in dict.fromkeys(r["method"] for r in scored):
        rows = [r for r in scored if r["method"] == method]
        labeled = [r for r in rows if r["reference_sources"]]
        metrics.append(
            {
                "method": method,
                "records": len(rows),
                "completed": sum(r["status"] == "completed" for r in rows),
                "labeled_scopes": len(labeled),
                **{
                    key: sum(r[key] for r in labeled) / len(labeled) if labeled else None
                    for key in (
                        "exact_recall_5",
                        "exact_recall_10",
                        "coverage_recall_5",
                        "coverage_recall_10",
                    )
                },
                "fully_covered_5": sum(r["coverage_recall_5"] == 1 for r in labeled),
            }
        )
    return metrics


def paired_changes(scored, baseline="hybrid", candidate=METHOD):
    comparisons = []
    index = {(r["query_id"], r["method"]): r for r in scored}
    for (qid, method), row in index.items():
        if method != candidate:
            continue
        before = index[(qid, baseline)]
        if not row["reference_sources"]:
            state, delta = "unlabeled", None
        else:
            delta = row["coverage_recall_5"] - before["coverage_recall_5"]
            state = "improved" if delta > 1e-12 else "regressed" if delta < -1e-12 else "unchanged"
        comparisons.append(
            {
                "query_id": qid,
                "case_id": row["case_id"],
                "module": row["module"],
                "baseline": baseline,
                "candidate": candidate,
                "coverage_change": state,
                "coverage_recall_5_delta": delta,
            }
        )
    return {
        "counts": dict(Counter(row["coverage_change"] for row in comparisons)),
        "rows": comparisons,
        "interpretation": "Changes in original-source recall, not changes in fitness judgment correctness",
    }


def build(root, six_dir, new_dir, reference_path, output):
    root, six_dir, new_dir, output = [Path(p).resolve() for p in (root, six_dir, new_dir, output)]
    if output.exists() or not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Use a new experimental report directory")
    for directory in (six_dir, new_dir):
        for name, expected in json.loads((directory / "artifacts.json").read_bytes()).items():
            if file_hash(directory / name) != expected:
                raise ValueError("Frozen experiment artifact changed: " + str(directory / name))
    six_manifest, manifest = [
        json.loads((p / "manifest.json").read_bytes()) for p in (six_dir, new_dir)
    ]
    if (
        digest({k: v for k, v in manifest.items() if k not in {"identity", "production_change"}})
        != manifest["identity"]
    ):
        raise ValueError("Additional method manifest self-identity differs")
    corpus, queries = [
        json.loads((new_dir / name).read_bytes()) for name in ("corpus.json", "queries.json")
    ]
    if any(
        json.loads((six_dir / name).read_bytes()) != value
        for name, value in (("corpus.json", corpus), ("queries.json", queries))
    ):
        raise ValueError("The additional method and six methods use different frozen inputs")
    originals = [
        json.loads(line)
        for line in (six_dir / "rankings.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    new = [
        json.loads(line)
        for line in (new_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    if (
        len(new) != len(queries)
        or len({r["query_id"] for r in new}) != len(new)
        or {r["query_id"] for r in new} != {q["query_id"] for q in queries}
        or any(
            r["method"] != METHOD or r["experiment_identity"] != manifest["identity"] for r in new
        )
    ):
        raise ValueError("New method inventory is incomplete, repeated or misidentified")
    rows = [*originals, *new]
    ablation = [
        {
            **r,
            "method": "planned_hybrid_no_diversity",
            "source_ids": r.get("without_diversity_source_ids", []),
        }
        for r in new
    ]
    # References are unavailable to the ranking implementation. Open only here,
    # after every ranking was frozen, and check the original reference pin.
    if file_hash(reference_path) != six_manifest["references_sha256"]:
        raise ValueError("Engineering reference labels changed")
    references = json.loads(Path(reference_path).read_bytes())
    units = {u["source_id"]: u for u in corpus["units"]}
    scored = evaluate([*rows, *ablation], queries, units, references)
    new_summary = json.loads((new_dir / "summary.json").read_bytes())
    summary = {
        "methods": 7,
        "ranking_records": len(rows),
        "ablation_records": len(ablation),
        "cases": len({q["case_id"] for q in queries}),
        "module_queries": len(queries),
        "metrics": summarize(scored),
        "paired_vs_hybrid": paired_changes(scored),
        "diversity_ablation": paired_changes(scored, "planned_hybrid_no_diversity", METHOD),
        "cohorts": {
            name: summarize([r for r in scored if r["cohort"] == name])
            for name in ("engineering", "complex_validation")
        },
        "new_method_execution": new_summary,
        "source_review": json.loads((new_dir / "design_sources.json").read_bytes()),
        "inherited_graph_quality": json.loads(
            (six_dir / "graph_completion_quality.json").read_bytes()
        ),
        "judgment_calls": 0,
        "production_change": False,
        "interpretation": "Engineering reference-source recall, not clinical or fitness classification accuracy. Labels are incomplete, observed development fixtures are not a sealed holdout. The ablation reuses identical channels and removes only final passage diversity. Query-term coverage is lexical, not medical support.",
    }
    identity = {
        "six_method_identity": six_manifest["identity"],
        "additional_method_identity": manifest["identity"],
        "six_artifacts_sha256": file_hash(six_dir / "artifacts.json"),
        "additional_artifacts_sha256": file_hash(new_dir / "artifacts.json"),
        "references_sha256": file_hash(reference_path),
        "reporter_sha256": file_hash(__file__),
    }
    output.mkdir(parents=True)
    write_json(
        output / "manifest.json",
        {**identity, "identity": digest(identity), "production_change": False},
    )
    write_json(output / "summary.json", summary)
    write_json(output / "retrieval_metrics.json", scored)
    write_json(output / "paired_changes.json", summary["paired_vs_hybrid"])
    for name in ("corpus.json", "queries.json", "model_calls.jsonl", "design_sources.json"):
        path = new_dir / name
        if path.exists():
            shutil.copyfile(path, output / name)
    shutil.copyfile(six_dir / "evidence_guide.pdf", output / "evidence_guide.pdf")
    (output / "rankings.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in [*rows, *ablation]),
        encoding="utf-8",
    )
    for filename, records in (
        ("summary.csv", summary["metrics"]),
        ("paired_changes.csv", summary["paired_vs_hybrid"]["rows"]),
    ):
        with (output / filename).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    render(output, rows, new, queries, units, summary)
    write_json(
        output / "artifacts.json", {p.name: file_hash(p) for p in output.iterdir() if p.is_file()}
    )
    return summary


def render(output, rows, new, queries, units, summary):
    def pct(value):
        return "Not labeled" if value is None else f"{value:.2%}"

    table = "".join(
        f"<tr><td>{r['method']}</td><td>{r['completed']}/{r['records']}</td><td>{pct(r['exact_recall_5'])}</td>"
        f"<td>{pct(r['coverage_recall_5'])}</td><td>{pct(r['coverage_recall_10'])}</td><td>{r['fully_covered_5']}/{r['labeled_scopes']}</td></tr>"
        for r in summary["metrics"]
    )
    rmap = {(r["query_id"], r["method"]): r for r in rows}
    nmap = {r["query_id"]: r for r in new}
    changes = {r["query_id"]: r for r in summary["paired_vs_hybrid"]["rows"]}
    cards = []
    for query in queries:
        qid = query["query_id"]
        panels = []
        for method in ("hybrid", METHOD):
            row = rmap[(qid, method)]
            evidence = "".join(
                f"<details><summary>{rank}. {escape(sid)} · PDF {units[sid]['pdf_page']}</summary>"
                f"<p>Section {escape(str(units[sid]['section']))} · Printed page {units[sid]['printed_page']} · "
                f'<a href="evidence_guide.pdf#page={units[sid]["pdf_page"]}">Original PDF</a></p><pre>{escape(units[sid]["evidence_text"])}</pre></details>'
                for rank, sid in enumerate(row["source_ids"][:10], 1)
            )
            panels.append(
                f"<div><h3>{method}</h3><p>{escape(row.get('error', row['status']))}</p>{evidence}</div>"
            )
        trace = nmap[qid]
        cards.append(
            f'<article data-case="{escape(query["case_id"])}" data-module="{query["module"]}" data-change="{changes[qid]["coverage_change"]}">'
            f"<h2>{escape(query['case_id'])} / {query['module']}</h2><p>Source coverage @5: {changes[qid]['coverage_change']}</p>"
            f"<details><summary>Frozen original query</summary><pre>{escape(query['query'])}</pre></details>"
            f'<div class="compare">{"".join(panels)}</div><details><summary>Plan, channels, inspection and bounded refinement</summary>'
            f"<pre>{escape(json.dumps(trace.get('events', []), ensure_ascii=False, indent=2))}</pre></details></article>"
        )
    filters = "".join(
        f'<label>{key.title()} <select id="{key}"><option value="">All</option>'
        + "".join(f"<option>{escape(v)}</option>" for v in sorted(values))
        + "</select></label>"
        for key, values in (
            ("case", {q["case_id"] for q in queries}),
            ("module", {q["module"] for q in queries}),
            ("change", {r["coverage_change"] for r in changes.values()}),
        )
    )
    cost = summary["new_method_execution"]
    html = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Planned Hybrid RRF | Occupational Fitness Platform</title><style>
body{margin:0;background:#f4f6f8;color:#223443;font:14px/1.6 Arial,sans-serif}main{max-width:1280px;margin:36px auto;padding:0 24px}
header,section,article{background:white;border:1px solid #d9e1e8;border-radius:8px;margin:20px 0;padding:24px}h1{font-size:30px}h2{font-size:20px}h3{font-size:16px}
table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:12px;border-bottom:1px solid #e2e8ee}.compare{display:grid;grid-template-columns:1fr 1fr;gap:24px}.compare>div{min-width:0}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f8fa;padding:14px;font:12px/1.6 Consolas,monospace}summary{cursor:pointer;padding:10px 0}details{border-bottom:1px solid #e2e8ee}
label{display:inline-block;margin:8px 20px 8px 0}select{padding:8px}a{color:#23618b}.muted{color:#5d7182}@media(max-width:800px){.compare{grid-template-columns:1fr}}[hidden]{display:none}</style></head><body><main>
<header><p class="muted">OCCUPATIONAL FITNESS PLATFORM · RETRIEVAL COMPARISON</p><h1>Planned Hybrid RRF</h1>
<p>An additional first-party method inspired by selected WeKnora retrieval and DeerFlow orchestration designs. It does not execute the complete external frameworks.</p>"""
    html += f"<p>{summary['cases']} cases · {summary['module_queries']} shared queries · six preserved methods plus one new method · one separately labeled diversity ablation.</p></header>"
    html += (
        "<section><h2>Original-source retrieval</h2><p>"
        + escape(summary["interpretation"])
        + "</p><table><tr><th>Method</th><th>Completed</th><th>Exact R@5</th><th>Coverage R@5</th><th>Coverage R@10</th><th>Fully covered @5</th></tr>"
        + table
        + "</table></section>"
    )
    html += (
        "<section><h2>Paired change against existing hybrid RRF</h2><p>"
        + escape(str(summary["paired_vs_hybrid"]["counts"]))
        + "</p><p>These changes describe source-reference recall. Common-model fitness judgments have not run for this arm.</p></section>"
    )
    html += f"<section><h2>Execution cost and provenance</h2><p>{cost['actual_new_embedding_calls']} actual new embedding calls; {cost['actual_new_embedding_inputs']} facet inputs; {cost['keyword_followups']} keyword follow-ups; {cost['failures']} failed conditions. The {cost['shared_embedding_calls_imported_not_recounted']} original embedding calls are reused by hash, and are not counted as new calls. No judgment or planner LLM calls were made.</p>"
    html += '<p><a href="design_sources.json">Reviewed repositories and exact source revisions</a> · <a href="manifest.json">Experiment identities</a> · <a href="model_calls.jsonl">Actual new calls</a> · <a href="rankings.jsonl">Raw rankings and stage traces</a> · <a href="summary.csv">Summary CSV</a> · <a href="paired_changes.csv">Per-query changes CSV</a></p></section>'
    html += f"<section><h2>Inherited graph quality</h2><p>The imported six-method version has {summary['inherited_graph_quality']['truncated_completion_calls']} length-limited graph completion flags. Its original records remain unchanged; the stricter graph reconstruction is reported as a separate version.</p></section>"
    html += (
        "<section><h2>Compare the same case</h2>"
        + filters
        + '<p id="count"></p></section>'
        + "".join(cards)
    )
    html += """</main><script>const keys=['case','module','change'];function filter(){let n=0;document.querySelectorAll('article').forEach(a=>{a.hidden=keys.some(k=>document.getElementById(k).value&&a.dataset[k]!==document.getElementById(k).value);if(!a.hidden)n++});document.getElementById('count').textContent=n+' shared query comparisons shown'}keys.forEach(k=>document.getElementById(k).addEventListener('change',filter));filter();</script></body></html>"""
    (output / "index.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--six", required=True)
    parser.add_argument("--additional", default="outputs/experiments/planned_hybrid_v1")
    parser.add_argument(
        "--references", default="outputs/experiments/source_literal_retrieval_v1/frozen_inputs.json"
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = build(Path.cwd(), args.six, args.additional, args.references, args.output)
    print(
        json.dumps(
            {key: result[key] for key in ("methods", "ranking_records", "cases", "metrics")},
            indent=2,
        )
    )
