"""Native dependency-isolated routes; every returned item maps to a frozen original."""

from __future__ import annotations

import argparse
import asyncio
import importlib.metadata
import shutil
from pathlib import Path
from time import perf_counter

from tools.complex_ten_contract import (
    DEFAULT,
    METHODS,
    ROOT,
    append,
    digest,
    pin,
    read,
    rows,
    verify,
    write_json,
)


def observed(folder, query, plan, method, fn):
    path = folder / "results.jsonl"
    if any(r["query_id"] == query["query_id"] for r in rows(path)):
        return
    record = {k: query[k] for k in ("query_id", "case_id", "module", "cohort")}
    record.update(method=method, experiment_identity=plan["identity"], source_ids=[])
    begin = perf_counter()
    try:
        record.update(fn(), status="completed")
    except Exception as exc:
        record.update(status="failed", source_ids=[], error=f"{type(exc).__name__}: {exc}")
    record["seconds"] = perf_counter() - begin
    record["record_sha256"] = digest(record)
    append(path, record)


def flag(output, folder, plan):
    from tools.flag_embedding_extension_worker import run

    corpus, queries, anchors = [
        read(output / n) for n in ("corpus.json", "queries.json", "anchor_candidates.json")
    ]
    cfg = read(ROOT / "outputs/experiments/scope88_flag_rerank_v2/manifest.json")["config"]
    job = {
        "experiment_identity": plan["identity"],
        "corpus": corpus,
        "queries": queries,
        "candidates": anchors,
        "config": cfg,
    }
    write_json(folder / "input.json", job)
    run(folder / "input.json", folder / "native", resume=(folder / "native").exists())
    for r in rows(folder / "native/results.jsonl"):
        q = next(q for q in queries if q["query_id"] == r["query_id"])
        r.update(
            cohort=q["cohort"],
            native_experiment_identity=r["experiment_identity"],
            experiment_identity=plan["identity"],
            seconds=r.get("seconds", r.get("reranking_seconds", r.get("ranking_seconds", 0))),
        )
        append(folder / "results.jsonl", r)


def neo(output, folder, plan):
    from neo4j import GraphDatabase
    from neo4j_graphrag.retrievers import VectorRetriever

    from occupational_fitness_rag.evaluation.neo4j_criterion_transfer import transfer
    from occupational_fitness_rag.evaluation.neo4j_strategies import native_rrf, rank
    from tools import neo4j_extension_worker as native
    from tools.run_neo4j_strategies import GRAPH_QUERY, native_item

    corpus, queries, vectors, anchors = [
        read(output / n)
        for n in ("corpus.json", "queries.json", "query_vectors.json", "anchor_candidates.json")
    ]
    units = {u["source_id"]: u for u in corpus["units"]}
    parent = read(ROOT / "outputs/experiments/scope88_neo4j_strategies_v2/manifest.json")
    graph_id = parent["identity"]
    credentials = read(ROOT / ".runtime/neo4j/credential.json")
    database = credentials.get("database", "neo4j")
    if importlib.metadata.version("neo4j-graphrag") != "1.22.0":
        raise ValueError("Native Neo4j SDK version differs")
    with GraphDatabase.driver(
        "bolt://127.0.0.1:17687",
        auth=(credentials.get("username", "neo4j"), credentials["password"]),
    ) as driver:
        driver.verify_connectivity()
        actual = driver.execute_query(
            "MATCH (n:OFPOriginalSource {experiment_id:$identity}) RETURN n.source_id AS source_id,n.text_sha256 AS text_sha256,n.vector_sha256 AS vector_sha256",
            {"identity": graph_id},
            database_=database,
        ).records
        source_vectors = read(
            ROOT / "outputs/experiments/scope88_shared_retrieval_v2/corpus_vectors.json"
        )
        expected = {
            u["source_id"]: (u["text_sha256"], digest(v))
            for u, v in zip(corpus["units"], source_vectors, strict=True)
        }
        if {r["source_id"]: (r["text_sha256"], r["vector_sha256"]) for r in actual} != expected:
            raise ValueError("Frozen native database originals or vectors differ")
        write_json(
            folder / "native_index_receipt.json",
            {
                "namespace": graph_id,
                "source_count": len(actual),
                "index_rebuilt": False,
                "source_vector_hashes_verified": True,
                "sdk_version": importlib.metadata.version("neo4j-graphrag"),
            },
        )
        for i, q in enumerate(queries, 1):

            def retrieve():
                stem, _ = native.graph_namespace(graph_id, q["module"])
                engine = VectorRetriever(
                    driver,
                    stem + "_vector",
                    return_properties=["source_id", "text_sha256"],
                    result_formatter=native_item,
                    neo4j_database=database,
                )
                dense = [
                    r.metadata
                    for r in engine.search(query_vector=vectors[q["query_id"]], top_k=30).items
                ]
                text_rows = [
                    dict(r)
                    for r in driver.execute_query(
                        "CALL db.index.fulltext.queryNodes($index,$query) YIELD node,score WHERE node.experiment_id=$identity AND node.module=$module RETURN node.source_id AS source_id,node.text_sha256 AS text_sha256,score ORDER BY score DESC,node.source_id LIMIT 30",
                        {
                            "index": stem + "_text",
                            "query": native.lexical_query(q["query"]),
                            "identity": graph_id,
                            "module": q["module"],
                        },
                        database_=database,
                    ).records
                ]
                fused = native_rrf(dense, text_rows, units, q["module"])
                seeds = anchors[q["query_id"]]
                graph = [
                    dict(r)
                    for r in driver.execute_query(
                        GRAPH_QUERY,
                        {
                            "seeds": seeds,
                            "identity": graph_id,
                            "module": q["module"],
                            "candidate_ranks": {r["source_id"]: j + 1 for j, r in enumerate(fused)},
                        },
                        database_=database,
                    ).records
                ]
                trace = {k: q[k] for k in ("query_id", "case_id", "module")}
                trace.update(
                    status="completed",
                    vector_records=dense,
                    fulltext_records=text_rows,
                    native_rrf=fused,
                    original_query_source_ids=seeds,
                    graph_records=graph,
                )
                base = {k: q[k] for k in ("query_id", "case_id", "module")}
                base.update(
                    status="completed",
                    **rank("neo4j_anchor_graph_guard_v2", seeds, fused, graph, units, q["module"]),
                )
                result = transfer(METHODS[8], base, trace, units)
                result["actual_native_trace"] = trace
                return result

            observed(folder, q, plan, METHODS[8], retrieve)
            if i % 20 == 0:
                print(f"Neo4j {i}/{len(queries)}", flush=True)


def tree(output, folder, plan):
    from tools import pageindex_extension_worker as native
    from tools.run_scope88_tree import call, ranking_body

    corpus, queries, anchors = [
        read(output / n) for n in ("corpus.json", "queries.json", "anchor_candidates.json")
    ]
    units = {u["source_id"]: u for u in corpus["units"]}
    parent = ROOT / "outputs/experiments/scope88_tree_coverage_v1"
    cfg = read(parent / "manifest.json")["config"]
    if importlib.metadata.version("pageindex") != cfg["expected_pageindex_version"]:
        raise ValueError("Native PageIndex release differs")
    native.runtime(cfg)
    mapping = read(parent / "native_index/source_mapping.json")
    for module in mapping:
        if (
            native.map_native_tree(
                module, read(parent / "native_index" / (module + ".json")), units
            )
            != mapping[module]
        ):
            raise ValueError("Native PageIndex source mapping differs")
    write_json(
        folder / "native_index_receipt.json",
        {
            "reused_index": str(parent.relative_to(ROOT)),
            "mapping_sha256": pin(parent / "native_index/source_mapping.json"),
            "config": cfg,
            "native_chat_retrieval_used": False,
            "navigator": "first-party adapter over actual PageIndex tree",
        },
    )
    for i, q in enumerate(queries, 1):

        def retrieve():
            m = mapping[q["module"]]
            body, field, allowed, _ = native.request_body(q, m, units, cfg, "branches")
            branches, _ = call(folder, q, body, field, allowed, cfg, "branches")
            body, field, allowed, excluded, candidates, expanded = ranking_body(
                q, m, units, cfg, branches, anchors[q["query_id"]][:20], predicate=True
            )
            selected, _ = call(folder, q, body, field, allowed, cfg, METHODS[9])
            return {
                "source_ids": [m["leaves"][n]["source_id"] for n in selected],
                "selected_leaf_node_ids": selected,
                "selected_branch_node_ids": branches,
                "expanded_branch_node_ids": expanded,
                "candidate_source_ids": candidates,
                "excluded_native_nodes_by_navigation_budget": excluded,
            }

        observed(folder, q, plan, METHODS[9], retrieve)
        if i % 10 == 0:
            print(f"PageIndex {i}/{len(queries)}", flush=True)


async def external(output, folder, plan, method):
    import re
    import sys

    from occupational_fitness_rag.evaluation.graph_worker import light_engine, microsoft_engine

    if not sys.version.startswith("3.12."):
        raise ValueError("Use the pinned native Python 3.12 environment")
    for line in (
        (ROOT / f"configs/experiments/{method}.lock.txt").read_text(encoding="utf-8").splitlines()
    ):
        if "==" in line and not line.startswith("#"):
            name, expected = line.split("==", 1)
            if importlib.metadata.version(re.sub(r"[-_.]+", "-", name)) != expected:
                raise ValueError("Native dependency differs: " + name)
    queries, corpus = [read(output / n) for n in ("queries.json", "corpus.json")]
    cfg = dict(plan["external_config"])
    proxy_cfg = {**cfg, "endpoint": cfg["audit_endpoint"]}
    for module in sorted({q["module"] for q in queries}):
        parent = (
            ROOT
            / "outputs/experiments"
            / ("scope88_external_graph_v1" if module == "vision" else "external_graph_retrieval_v3")
            / "indexes"
            / method
            / module
        )
        if not (parent / "index_complete.json").exists():
            raise ValueError("Require an actual completed native graph index")
        work = folder / "indexes" / module
        if not work.exists():
            shutil.copytree(parent, work)
        units = [u for u in corpus["units"] if u["module"] == module]
        write_json(folder / "phase.json", {"module": module, "stage": "load_frozen_index"})
        engine = await (light_engine if method == "lightrag" else microsoft_engine)(
            work, units, proxy_cfg
        )
        try:
            for i, q in enumerate([q for q in queries if q["module"] == module], 1):
                if any(r["query_id"] == q["query_id"] for r in rows(folder / "results.jsonl")):
                    continue
                write_json(
                    folder / "phase.json",
                    {"module": module, "query_id": q["query_id"], "stage": "retrieve"},
                )
                r = {k: q[k] for k in ("query_id", "case_id", "module", "cohort")}
                r.update(experiment_identity=plan["identity"], method=method, source_ids=[])
                begin = perf_counter()
                try:
                    ids, raw = await engine(q["query"], 10)
                    r.update(status="completed", source_ids=ids, native_response=raw)
                except Exception as exc:
                    r.update(status="failed", source_ids=[], error=f"{type(exc).__name__}: {exc}")
                r["seconds"] = perf_counter() - begin
                r["record_sha256"] = digest(r)
                append(folder / "results.jsonl", r)
                if i % 10 == 0:
                    print(f"{method} {module} {i}", flush=True)
        finally:
            if hasattr(engine, "close"):
                await engine.close()


def run(output, method):
    output = Path(output).resolve()
    plan = read(output / "plan.json")
    verify(output, plan)
    folder = output / "workers" / method
    folder.mkdir(parents=True, exist_ok=True)
    if method == METHODS[7]:
        flag(output, folder, plan)
    elif method == METHODS[8]:
        neo(output, folder, plan)
    elif method == METHODS[9]:
        tree(output, folder, plan)
    else:
        asyncio.run(external(output, folder, plan, method))
    expected = {q["query_id"] for q in read(output / "queries.json")}
    actual = rows(folder / "results.jsonl")
    if len(actual) != len(expected) or {r["query_id"] for r in actual} != expected:
        raise ValueError("Actual native query inventory is incomplete or repeated")
    verify(output, plan)
    write_json(
        folder / "complete.json",
        {
            "method": method,
            "recorded": len(actual),
            "failed": sum(r["status"] != "completed" for r in actual),
            "results_sha256": pin(folder / "results.jsonl"),
            "experiment_identity": plan["identity"],
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT)
    parser.add_argument("--method", choices=METHODS[4:6] + METHODS[7:], required=True)
    args = parser.parse_args()
    run(args.output, args.method)
