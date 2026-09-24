"""Ablate retrieval and grouping without supplying expected source IDs to retrieval."""

import json
from collections import defaultdict
from statistics import mean
from time import perf_counter

from occupational_fitness_rag.provenance import digest, write_json
from occupational_fitness_rag.retrieval.indicators import IndicatorRetriever
from occupational_fitness_rag.schemas.indicator import IndicatorRequest


def score_sources(ranked_groups, expected):
    expected = set(expected)
    retrieved = {sid for group in ranked_groups for sid in group}
    hits = expected & retrieved
    first = next((i for i, group in enumerate(ranked_groups, 1) if expected & set(group)), None)
    return {
        "recall_at_k": len(hits) / len(expected) if expected else None,
        "mrr": 1 / first if first else 0.0,
        "label_precision": len(hits) / len(retrieved) if retrieved else 0.0,
        "returned_source_count": len(retrieved),
        "complete_source_coverage": float(expected <= retrieved),
    }


def run_retrieval_study(workflow, gold_path, output, backend="offline"):
    fixture = json.loads(gold_path.read_text(encoding="utf-8"))
    rows = []
    ids = [c["id"] for c in fixture["cases"]]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("The retrieval fixture must contain unique case IDs")
    for case in fixture["cases"]:
        if not set(case["expected_source_ids"]) <= workflow.catalogue.units.keys():
            raise ValueError("Unknown expected source in retrieval fixture")
    for strategy in ("unit", "section", "page"):
        retriever = IndicatorRetriever(workflow, backend=backend, strategy=strategy)
        for method in ("vector", "bm25", "hybrid"):
            for case in fixture["cases"]:
                request = IndicatorRequest(
                    case_id=case["id"],
                    indicator_id=case["id"],
                    module=case["module"],
                    source_document="synthetic_indicator.txt",
                    source_text=case["text"],
                    start=0,
                    end=len(case["text"]),
                    top_k=10,
                    expand_references=False,
                )
                start = perf_counter()
                result = retriever.retrieve(request, method)
                elapsed = perf_counter() - start
                for k in (1, 3, 5, 10):
                    candidates = result.ranked_candidates[:k]
                    groups = [x["source_ids"] for x in candidates]
                    scores = score_sources(groups, case["expected_source_ids"])
                    actual = {sid for group in groups for sid in group}
                    expected_units = [
                        workflow.catalogue.units[sid] for sid in case["expected_source_ids"]
                    ]
                    actual_units = [workflow.catalogue.units[sid] for sid in actual]
                    rows.append(
                        {
                            "case_id": case["id"],
                            "module": case["module"],
                            "scenario": case["scenario"],
                            "strategy": strategy,
                            "method": method,
                            "top_k": k,
                            "query": result.query,
                            "filters": result.filters,
                            "expected_source_ids": case["expected_source_ids"],
                            "ranked_candidates": candidates,
                            **scores,
                            "section_hit": float(
                                bool(
                                    {u["section"] for u in expected_units}
                                    & {u["section"] for u in actual_units}
                                )
                            ),
                            "page_hit": float(
                                bool(
                                    {u["pdf_page"] for u in expected_units}
                                    & {u["pdf_page"] for u in actual_units}
                                )
                            ),
                            "returned_characters": sum(
                                len(u["evidence_text"]) for u in actual_units
                            ),
                            "ranking_seconds_top10": round(elapsed, 4),
                        }
                    )
    grouped = defaultdict(list)
    for row in rows:
        for module in ("all", row["module"]):
            grouped[(row["strategy"], row["method"], row["top_k"], module)].append(row)
    metrics = (
        "recall_at_k",
        "mrr",
        "label_precision",
        "complete_source_coverage",
        "section_hit",
        "page_hit",
        "returned_source_count",
        "returned_characters",
    )
    summary = [
        {
            "strategy": s,
            "method": m,
            "top_k": k,
            "module": module,
            "cases": len(group),
            **{key: round(mean(r[key] for r in group), 4) for key in metrics},
        }
        for (s, m, k, module), group in sorted(grouped.items())
    ]
    report = {
        "schema_version": "1.0.0",
        "backend": backend,
        "vector_method": "nomic-embed-text via Chroma"
        if backend == "chroma"
        else "lexical cosine surrogate",
        "clinical_review_status": fixture["clinical_review_status"],
        "independent_clinical_gold": False,
        "fixture_sha256": digest(fixture),
        "index_sha256": workflow.catalogue.index_sha256,
        "cases": len(ids),
        "observations": len(rows),
        "summary": summary,
        "rows": rows,
        "limitations": [
            "Source-based development labels require independent human review.",
            "Expected source IDs are used only for scoring, never for retrieval.",
            "Page and section strategies group existing anchors; they do not represent full-PDF chunking.",
            "Label precision treats unlabelled sources as non-hits; it is not adjudicated irrelevance.",
            "Cross-reference expansion is excluded from ranked retrieval metrics.",
            "Top K counts chunks. Broader grouped chunks may return more sources and characters.",
        ],
    }
    write_json(output, report)
    return {"report": str(output), "backend": backend, "cases": len(ids), "observations": len(rows)}
