"""Compare ranked retrieval on the same labelled query sets without label leakage."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from html import escape
from pathlib import Path
from statistics import mean
from time import perf_counter

from occupational_fitness_rag.evaluation.retrieval_study import score_sources
from occupational_fitness_rag.provenance import digest, write_json
from occupational_fitness_rag.retrieval.graph_local import graph_manifest
from occupational_fitness_rag.retrieval.indicators import IndicatorRetriever
from occupational_fitness_rag.schemas.indicator import IndicatorRequest

METHODS = ("vector", "bm25", "hybrid", "graph", "graph_local")
TOP_K = (1, 3, 5, 10)


def _queries(indicator_fixture, complex_fixture):
    for case in indicator_fixture["cases"]:
        yield {
            "query_id": case["id"],
            "cohort": "indicator",
            "module": case["module"],
            "scenario": case["scenario"],
            "text": case["text"],
            "start": 0,
            "end": len(case["text"]),
            "expected_source_ids": case["expected_source_ids"],
        }
    for case in complex_fixture["cases"]:
        text = "\n\n".join(case["paragraphs"])
        for number, query in enumerate(case["queries"], 1):
            paragraph = case["paragraphs"][query["paragraph"]]
            start = sum(len(p) + 2 for p in case["paragraphs"][: query["paragraph"]])
            yield {
                "query_id": f"{case['id']}-Q{number}",
                "cohort": "complex_note_paragraph",
                "module": query["module"],
                "scenario": ", ".join(case["challenges"]),
                "text": text,
                "start": start,
                "end": start + len(paragraph),
                "expected_source_ids": query["expected_source_ids"],
            }


def _candidate_list(row):
    return "".join(
        "<li>" + escape(", ".join(candidate["source_ids"])) + "</li>"
        for candidate in row["ranked_candidates"]
    )


def render_html(report):
    rows = "".join(
        f"<tr><td>{escape(x['cohort'])}</td><td>{escape(x['method'])}</td>"
        f"<td>{x['top_k']}</td><td>{x['queries']}</td>"
        f"<td>{x['source_recall']:.1%}</td><td>{x['complete_coverage']:.1%}</td>"
        f"<td>{x['mrr']:.3f}</td><td>{x['mean_returned_sources']:.1f}</td>"
        f"<td>{x['mean_latency_ms']:.1f}</td></tr>"
        for x in report["summary"]
    )
    examples = "".join(
        f"<details><summary>{escape(x['query_id'])} · {escape(x['method'])} · "
        f"Recall@5 {x['recall_at_k']:.0%}</summary>"
        f"<blockquote>{escape(x['query'])}</blockquote>"
        f"<p>Expected sources: {escape(', '.join(x['expected_source_ids']))}</p>"
        f"<ol>{_candidate_list(x)}</ol>"
        "</details>"
        for x in report["rows"]
        if x["top_k"] == 5
    )
    return """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>RAG retrieval comparison | Occupational Fitness</title>
<style>body{font:15px/1.5 system-ui;color:#203344;background:#f3f5f7;margin:0}
main{max-width:1200px;margin:auto;padding:32px 24px}h1{font-size:30px;letter-spacing:-.03em}
section,details{background:#fff;border:1px solid #dce3e8;border-radius:8px;margin:14px 0;padding:18px}
table{width:100%;border-collapse:collapse;font-size:13px}td,th{padding:10px;border-bottom:1px solid #e3e8eb;text-align:left}
.scroll{overflow-x:auto}summary{cursor:pointer}blockquote{white-space:pre-wrap;border-left:3px solid #9bb6c9;
padding:10px 14px;background:#f7f9fb}.kicker{font-size:12px;letter-spacing:.12em;text-transform:uppercase;
color:#587083}a{color:#225978}</style><main>
<p class="kicker">Occupational Fitness / Retrieval evaluation</p>
<h1>RAG method comparison</h1>""" + (
        f"<p>{report['queries']} synthetic queries across the selected pilot modules. "
        "All methods use the same verified guideline anchors and category filters. "
        "Source labels are used only after retrieval for scoring.</p>"
        f"<p>Backend: {escape(report['backend'])}. {escape(report['vector_method'])}. "
        "Graph expands top-three hybrid seeds across rule and source links. Graph-local "
        "also activates source and rule nodes from query terms. Neither experiment "
        "builds an LLM-extracted knowledge graph or community reports.</p>"
        "<p>These are source-retrieval scores, not fitness-decision accuracy. "
        "Clinical and independent label review is pending. "
        '<a href="results.json">Inspect full JSON results</a> · '
        '<a href="error_analysis.json">Inspect retrieval misses</a> · '
        '<a href="fusion_sensitivity.json">Inspect RRF sensitivity</a> · '
        '<a href="graph_manifest.json">Inspect the source graph</a> · '
        '<a href="review_queue.csv">Open source-label review worksheet</a></p>'
        '<section><h2>Comparable retrieval scores</h2><div class="scroll"><table>'
        "<tr><th>Cohort</th><th>Method</th><th>Top K</th><th>Queries</th>"
        "<th>Recall</th><th>Full coverage</th><th>MRR</th><th>Sources returned</th>"
        "<th>Latency, ms</th></tr>" + rows + "</table></div></section>"
        "<h2>Ranked examples at Top 5</h2>" + examples + "</main></html>"
    )


def _error_analysis(rows):
    misses = []
    top_10 = {
        (row["query_id"], row["method"]): row
        for row in rows
        if row["top_k"] == 10
    }
    for row in rows:
        if row["top_k"] != 5 or row["complete_source_coverage"]:
            continue
        returned = {
            source_id
            for candidate in row["ranked_candidates"]
            for source_id in candidate["source_ids"]
        }
        missing = sorted(set(row["expected_source_ids"]) - returned)
        full_ranks = {
            source_id: candidate["rank"]
            for candidate in top_10[(row["query_id"], row["method"])]["ranked_candidates"]
            for source_id in candidate["source_ids"]
        }
        misses.append(
            {
                "query_id": row["query_id"],
                "module": row["module"],
                "method": row["method"],
                "query": row["query"],
                "provisional_expected_source_ids": row["expected_source_ids"],
                "missing_source_ids": missing,
                "missing_source_ranks_at_10": {
                    source_id: full_ranks.get(source_id) for source_id in missing
                },
                "failure_stage": (
                    "ranking_cutoff"
                    if all(source_id in full_ranks for source_id in missing)
                    else "candidate_retrieval"
                ),
                "returned_source_ids": sorted(returned),
                "ranked_candidates": row["ranked_candidates"],
                "label_review_status": "pending_human_review",
            }
        )
    return {
        "schema_version": "1.0.0",
        "evaluation_type": "top_5_provisional_source_label_errors",
        "clinical_validation": False,
        "misses_by_method": {
            method: sum(item["method"] == method for item in misses) for method in METHODS
        },
        "misses": misses,
    }


def _safe_csv_cell(value):
    """Keep untrusted nurse-note text inert when a review worksheet opens in Excel."""
    cell = str(value)
    return "'" + cell if cell.lstrip().startswith(("=", "+", "-", "@")) else cell


def _write_review_queue(path, rows, catalogue):
    columns = [
        "query_id",
        "module",
        "scenario",
        "nurse_note_query",
        "provisional_expected_source_ids",
        "provisional_source_quotes",
        "hybrid_top_5_source_ids",
        "missing_provisional_sources",
        "reviewed_relevant_source_ids",
        "acceptable_alternative_source_ids",
        "reviewed_fact_or_condition_interpretation",
        "reviewer_name",
        "review_date",
        "review_notes",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            if row["method"] != "hybrid" or row["top_k"] != 5:
                continue
            found = {
                source_id
                for candidate in row["ranked_candidates"]
                for source_id in candidate["source_ids"]
            }
            record = {
                "query_id": row["query_id"],
                "module": row["module"],
                "scenario": row["scenario"],
                "nurse_note_query": row["query"],
                "provisional_expected_source_ids": "; ".join(row["expected_source_ids"]),
                "provisional_source_quotes": "\n\n".join(
                    f"{source_id}: {catalogue.units[source_id]['evidence_text']}"
                    for source_id in row["expected_source_ids"]
                ),
                "hybrid_top_5_source_ids": "; ".join(
                    source_id
                    for candidate in row["ranked_candidates"]
                    for source_id in candidate["source_ids"]
                ),
                "missing_provisional_sources": "; ".join(
                    sorted(set(row["expected_source_ids"]) - found)
                ),
            }
            writer.writerow({key: _safe_csv_cell(record.get(key, "")) for key in columns})


def _fusion_sensitivity(rows):
    """Replay vector/BM25 ranks with fixed RRF weights; labels score only afterward."""
    ranked = {
        (row["query_id"], row["method"]): row
        for row in rows
        if row["top_k"] == 10
    }
    query_ids = sorted({row["query_id"] for row in rows})

    def replay(query_id, rrf_k, vector_weight):
        scores, candidates = {}, {}
        for method, weight in (("vector", vector_weight), ("bm25", 1.0)):
            for candidate in ranked[(query_id, method)]["ranked_candidates"]:
                chunk_id = candidate["chunk_id"]
                candidates.setdefault(chunk_id, candidate)
                scores[chunk_id] = scores.get(chunk_id, 0.0) + weight / (
                    rrf_k + candidate["rank"]
                )
        # Stable tie order follows the vector ranking, then newly seen BM25 hits.
        return [
            candidates[chunk_id]
            for chunk_id in sorted(scores, key=lambda key: -scores[key])
        ]

    for query_id in query_ids:
        actual = ranked[(query_id, "hybrid")]["ranked_candidates"]
        if [c["chunk_id"] for c in replay(query_id, 60, 1.0)] != [
            c["chunk_id"] for c in actual
        ]:
            raise ValueError("RRF replay differs from the recorded hybrid ranking")
    summary = []
    for rrf_k in (10, 30, 60, 120):
        for vector_weight in (0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0):
            metrics = []
            for query_id in query_ids:
                expected = ranked[(query_id, "vector")]["expected_source_ids"]
                top_five = replay(query_id, rrf_k, vector_weight)[:5]
                metrics.append(
                    score_sources([item["source_ids"] for item in top_five], expected)
                )
            summary.append(
                {
                    "rrf_k": rrf_k,
                    "vector_weight": vector_weight,
                    "bm25_weight": 1.0,
                    "queries": len(query_ids),
                    "source_recall_at_5": round(mean(m["recall_at_k"] for m in metrics), 4),
                    "complete_coverage_at_5": round(
                        mean(m["complete_source_coverage"] for m in metrics), 4
                    ),
                    "mrr_at_5": round(mean(m["mrr"] for m in metrics), 4),
                }
            )
    return {
        "schema_version": "1.0.0",
        "evaluation_type": "post_retrieval_rrf_sensitivity",
        "clinical_validation": False,
        "source_labels_reviewed": False,
        "production_rrf_k": 60,
        "production_vector_weight": 1.0,
        "summary": summary,
        "limitations": [
            "This replays the same top-ten vector and BM25 candidates; it does not change recall beyond that pool.",
            "The development labels are provisional and were used to inspect these weights.",
            "The existing holdout has already informed an earlier indexing decision and is not a pristine test set.",
        ],
    }


def run_rag_comparison(
    workflow,
    indicator_path: Path,
    complex_path: Path,
    output: Path,
    backend: str = "offline",
):
    indicators = json.loads(indicator_path.read_text(encoding="utf-8"))
    complex_notes = json.loads(complex_path.read_text(encoding="utf-8"))
    queries = list(_queries(indicators, complex_notes))
    if len({q["query_id"] for q in queries}) != len(queries):
        raise ValueError("Comparison queries must have unique IDs")
    for query in queries:
        if not set(query["expected_source_ids"]) <= workflow.catalogue.units.keys():
            raise ValueError("Unknown expected source label")
    retriever = IndicatorRetriever(workflow, backend=backend, strategy="unit")
    rows = []
    for query in queries:
        request = IndicatorRequest(
            case_id=query["query_id"],
            indicator_id=query["query_id"],
            module=query["module"],
            source_document=query["cohort"] + ".txt",
            source_text=query["text"],
            start=query["start"],
            end=query["end"],
            top_k=10,
            expand_references=False,
        )
        for method in METHODS:
            started = perf_counter()
            result = retriever.retrieve(request, method=method)
            elapsed = round((perf_counter() - started) * 1000, 3)
            for k in TOP_K:
                candidates = result.ranked_candidates[:k]
                scores = score_sources(
                    [candidate["source_ids"] for candidate in candidates],
                    query["expected_source_ids"],
                )
                rows.append(
                    {
                        "query_id": query["query_id"],
                        "cohort": query["cohort"],
                        "module": query["module"],
                        "scenario": query["scenario"],
                        "method": method,
                        "top_k": k,
                        "query": result.query,
                        "filters": result.filters,
                        "expected_source_ids": query["expected_source_ids"],
                        "ranked_candidates": candidates,
                        "latency_ms_top10": elapsed,
                        **scores,
                    }
                )
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["cohort"], row["method"], row["top_k"])].append(row)
        grouped[("all", row["method"], row["top_k"])].append(row)
    summary = [
        {
            "cohort": cohort,
            "method": method,
            "top_k": k,
            "queries": len(group),
            "source_recall": round(mean(r["recall_at_k"] for r in group), 4),
            "complete_coverage": round(mean(r["complete_source_coverage"] for r in group), 4),
            "mrr": round(mean(r["mrr"] for r in group), 4),
            "mean_returned_sources": round(mean(r["returned_source_count"] for r in group), 2),
            "mean_latency_ms": round(mean(r["latency_ms_top10"] for r in group), 2),
        }
        for (cohort, method, k), group in sorted(grouped.items())
    ]
    report = {
        "schema_version": "1.0.0",
        "evaluation_type": "development_source_retrieval_comparison",
        "backend": backend,
        "vector_method": (
            "nomic-embed-text via local Chroma"
            if backend == "chroma"
            else "lexical cosine surrogate; no dense embeddings"
        ),
        "queries": len(queries),
        "clinical_validation": False,
        "independent_clinical_gold": False,
        "fixture_splits": [indicators.get("split"), complex_notes.get("split")],
        "source_labels_reviewed": False,
        "indicator_fixture_sha256": digest(indicators),
        "complex_fixture_sha256": digest(complex_notes),
        "index_sha256": workflow.catalogue.index_sha256,
        "ruleset_sha256": workflow.book.sha256,
        "methods": list(METHODS),
        "graph_definition": "graph: top-three hybrid seeds and one-hop links; graph_local: query-aware rule/source/section graph, no generated entities or communities",
        "summary": summary,
        "rows": rows,
        "limitations": [
            "The same small reviewed-anchor corpus is used for every method; this is not full-PDF GraphRAG.",
            "Source labels are engineering expectations and need independent review.",
            "Offline vector results use lexical cosine rather than dense embeddings.",
            "Graph expansion starts from hybrid seeds, so results are not an independent retrieval model.",
            "Graph-local ranking uses catalogue titles and rule names as experimental metadata; it is not Microsoft GraphRAG.",
            "Expected sources are used only after retrieval for scoring.",
            "Recall measures source discovery, not clinical reasoning or licensing accuracy.",
        ],
    }
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "results.json", report)
    write_json(output / "error_analysis.json", _error_analysis(rows))
    write_json(output / "fusion_sensitivity.json", _fusion_sensitivity(rows))
    write_json(output / "graph_manifest.json", graph_manifest(workflow.book, workflow.catalogue))
    _write_review_queue(output / "review_queue.csv", rows, workflow.catalogue)
    (output / "index.html").write_text(render_html(report), encoding="utf-8")
    return {"report": str(output / "index.html"), "queries": len(queries), "rows": len(rows)}
