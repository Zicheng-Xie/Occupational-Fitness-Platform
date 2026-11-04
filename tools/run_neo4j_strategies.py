"""Run native Neo4j per-engine RRF and bounded literal-graph strategy ablations.

The unchanged native worker rebuilds all module indexes for the reviewed corpus.
The new strategies retain actual native vector/full-text records and actual
Cypher paths. No model, expected-source label or outcome is used in ranking.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import shutil
import sys
from pathlib import Path
from time import perf_counter

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.evaluation.neo4j_strategies import POLICY, VARIANTS, native_rrf, rank
from occupational_fitness_rag.provenance import digest, write_json
from tools import neo4j_extension_worker as native

GRAPH_QUERY = """
UNWIND $seeds AS seed
MATCH (node:OFPOriginalSource {key:$identity+':'+seed})
CALL (node) {
  MATCH (node)-[:CONTAINS_ORIGINAL]-(candidate:OFPOriginalSource)
  RETURN candidate, 'literal_source_containment' AS graph_path, 0.95 AS multiplier
  UNION
  MATCH (node)-[:EXPLICIT_SECTION_REFERENCE]->(candidate:OFPOriginalSource)
  RETURN candidate, 'literal_explicit_section_reference' AS graph_path, 0.85 AS multiplier
}
WITH DISTINCT seed,candidate,graph_path,multiplier
WHERE candidate.experiment_id=$identity AND candidate.module=$module
  AND candidate.licence_context IN ['commercial','shared']
WITH seed,candidate,graph_path,multiplier
ORDER BY coalesce($candidate_ranks[candidate.source_id],1000),multiplier DESC,candidate.source_id
WITH seed,collect({source_id:candidate.source_id,text_sha256:candidate.text_sha256,
                  graph_path:graph_path,multiplier:multiplier})[0..5] AS paths
UNWIND paths AS path
RETURN seed AS seed_source_id,path.source_id AS source_id,path.text_sha256 AS text_sha256,
       path.graph_path AS graph_path,path.multiplier AS path_multiplier
"""

SOURCE_FILES = (
    "tools/run_neo4j_strategies.py",
    "tools/neo4j_extension_worker.py",
    "src/occupational_fitness_rag/evaluation/neo4j_strategies.py",
    "src/occupational_fitness_rag/evaluation/guarded_hybrid.py",
    "src/occupational_fitness_rag/evaluation/anchored_hybrid.py",
    "configs/experiments/neo4j_strategies_v2.json",
)


def load(path):
    return json.loads(Path(path).read_bytes())


def verify_bundle(directory):
    directory = Path(directory).resolve()
    pins = load(directory / "artifacts.json")
    if not pins:
        raise ValueError("Shared input inventory is empty")
    for name, expected in pins.items():
        target = (directory / name).resolve()
        if not target.is_relative_to(directory) or file_hash(target) != expected:
            raise ValueError("Frozen shared input changed: " + name)
    return pins


def inputs(directory):
    directory = Path(directory).resolve()
    pins = verify_bundle(directory)
    manifest = load(directory / "manifest.json")
    corpus, queries, vectors, query_vectors, anchors = [
        load(directory / n)
        for n in (
            "corpus.json",
            "queries.json",
            "corpus_vectors.json",
            "query_vectors.json",
            "anchor_candidates.json",
        )
    ]
    if len(corpus["units"]) != 88 or len(queries) != 77:
        raise ValueError("Expected the reviewed88 corpus and all77 fixed query conditions")
    units = {u["source_id"]: u for u in corpus["units"]}
    if len(units) != 88 or set(anchors) != {q["query_id"] for q in queries}:
        raise ValueError("Shared reviewed source or anchor inventory differs")
    if not isinstance(vectors, list) or len(vectors) != 88:
        raise ValueError("Shared real corpus vectors must follow the reviewed unit order")
    for q in queries:
        if (
            q.get("corpus_sha256") != corpus["corpus_sha256"]
            or digest({k: v for k, v in q.items() if k != "query_id"}) != q["query_id"]
        ):
            raise ValueError("Query corpus identity or query metadata fingerprint differs")
        native.validate_input(
            {
                "experiment_identity": "0" * 64,
                "corpus": corpus,
                "queries": [q],
                "corpus_vectors": vectors,
                "query_vectors": {q["query_id"]: query_vectors[q["query_id"]]},
                "config": {"embedding_dimensions": 768},
            }
        )
        ids = anchors[q["query_id"]]
        if (
            not ids
            or len(ids) > 20
            or len(ids) != len(set(ids))
            or any(s not in units or units[s]["module"] != q["module"] for s in ids)
        ):
            raise ValueError("Shared original-query candidates are not actual in-scope originals")
    return manifest, pins, corpus, queries, vectors, query_vectors, anchors


def native_item(record):
    from neo4j_graphrag.types import RetrieverResultItem

    node = dict(record["node"])
    item = {
        "source_id": node["source_id"],
        "text_sha256": node["text_sha256"],
        "score": record["score"],
    }
    return RetrieverResultItem(content=item, metadata=item)


def run(input_directory, output, config_path, uri, credential_file):
    from neo4j import GraphDatabase
    from neo4j_graphrag.retrievers import VectorRetriever

    root = Path(__file__).resolve().parents[1]
    input_directory, output = Path(input_directory).resolve(), Path(output).resolve()
    config_path, credential_file = Path(config_path).resolve(), Path(credential_file).resolve()
    if output.exists() or not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Use a fresh Neo4j experiment directory; preserve earlier runs")
    shared, input_pins, corpus, queries, vectors, query_vectors, anchors = inputs(input_directory)
    config = load(config_path)
    if (
        config["policy"] != POLICY
        or tuple(config["variants"]) != VARIANTS
        or config["primary_candidate"] != VARIANTS[-1]
        or (
            config["native_engine_top_k"],
            config["original_query_seed_budget"],
            config["graph_paths_per_seed"],
            config["output_source_budget"],
            config["rrf_k"],
        )
        != (30, 20, 5, 10, 60)
        or (config["anchor_weight"], config["literal_graph_weight"], config["coverage_weight"])
        != (0.8, 0.2, 0.15)
        or config["reference_labels_available"] is not False
    ):
        raise ValueError("Neo4j strategy configuration differs from the prespecified experiment")
    sources = {n: file_hash(root / n) for n in SOURCE_FILES}
    data = {
        "kind": "reviewed88_native_neo4j_retrieval_strategy_experiment",
        "shared_input_identity": shared["identity"],
        "shared_artifacts_sha256": file_hash(input_directory / "artifacts.json"),
        "config": config,
        "sources": sources,
        "graph_query_sha256": native.text_sha(GRAPH_QUERY),
        "corpus_sha256": corpus["corpus_sha256"],
        "source_count": 88,
        "query_count": 77,
        "python": sys.version,
        "labels_available_to_ranker": False,
        "model_calls": 0,
    }
    identity = digest(data)
    output.mkdir(parents=True)
    write_json(output / "manifest.json", {**data, "identity": identity, "production_change": False})
    for n, value in (("corpus.json", corpus), ("queries.json", queries), ("config.json", config)):
        write_json(output / n, value)
    for index, name in enumerate(SOURCE_FILES):
        shutil.copyfile(root / name, output / (f"source_{index}_" + Path(name).name))
    job = {
        "experiment_identity": identity,
        "corpus": corpus,
        "queries": queries,
        "corpus_vectors": vectors,
        "query_vectors": query_vectors,
        "config": {
            "expected_sdk_version": "1.22.0",
            "expected_server_version": "2026.10.0",
            "embedding_dimensions": 768,
        },
    }
    write_json(output / "native_input.json", job)
    native_started = perf_counter()
    legacy_summary = native.run(
        output / "native_input.json", output / "native_baseline.json", uri, credential_file
    )
    legacy = load(output / "native_baseline.json")
    if legacy_summary["recorded"] != 77:
        raise ValueError("Native baseline has an incomplete actual query inventory")
    credentials = load(credential_file)
    database = credentials.get("database", "neo4j")
    password = credentials["password"]
    units = {u["source_id"]: u for u in corpus["units"]}
    rows, query_records = [], []
    with GraphDatabase.driver(uri, auth=(credentials.get("username", "neo4j"), password)) as driver:
        driver.verify_connectivity()
        for q in queries:
            begin = perf_counter()
            trace = {k: q[k] for k in ("query_id", "case_id", "module")}
            trace.update(
                frozen_query=q["query"], submitted_fulltext_query=native.lexical_query(q["query"])
            )
            try:
                stem, _ = native.graph_namespace(identity, q["module"])
                retriever = VectorRetriever(
                    driver,
                    stem + "_vector",
                    return_properties=["source_id", "text_sha256"],
                    result_formatter=native_item,
                    neo4j_database=database,
                )
                dense = retriever.search(query_vector=query_vectors[q["query_id"]], top_k=30)
                vector_rows = [item.metadata for item in dense.items]
                lexical = driver.execute_query(
                    "CALL db.index.fulltext.queryNodes($index,$query) YIELD node,score "
                    "WHERE node.experiment_id=$identity AND node.module=$module "
                    "RETURN node.source_id AS source_id,node.text_sha256 AS text_sha256,score "
                    "ORDER BY score DESC,node.source_id LIMIT 30",
                    {
                        "index": stem + "_text",
                        "query": trace["submitted_fulltext_query"],
                        "identity": identity,
                        "module": q["module"],
                    },
                    database_=database,
                ).records
                lexical_rows = [dict(r) for r in lexical]
                fused = native_rrf(vector_rows, lexical_rows, units, q["module"])
                original_ids = anchors[q["query_id"]]
                native_ranks = {r["source_id"]: i + 1 for i, r in enumerate(fused)}
                paths = [
                    dict(r)
                    for r in driver.execute_query(
                        GRAPH_QUERY,
                        {
                            "seeds": original_ids,
                            "identity": identity,
                            "module": q["module"],
                            "candidate_ranks": native_ranks,
                        },
                        database_=database,
                    ).records
                ]
                trace.update(
                    status="completed",
                    vector_records=vector_rows,
                    fulltext_records=lexical_rows,
                    native_rrf=fused,
                    original_query_source_ids=original_ids,
                    graph_records=paths,
                )
                for variant in VARIANTS:
                    started = perf_counter()
                    row = {k: q[k] for k in ("query_id", "case_id", "module")}
                    row.update(method=variant, experiment_identity=identity)
                    try:
                        result = rank(variant, original_ids, fused, paths, units, q["module"])
                        row.update(
                            status="completed",
                            **result,
                            original_text_hashes={
                                sid: units[sid]["text_sha256"] for sid in result["source_ids"]
                            },
                        )
                    except Exception as exc:
                        row.update(
                            status="failed", source_ids=[], error=f"{type(exc).__name__}: {exc}"
                        )
                    row["ranking_seconds"] = perf_counter() - started
                    rows.append(row)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}".replace(password, "[redacted]")
                trace.update(status="failed", error=error)
                rows.extend(
                    {
                        **{k: q[k] for k in ("query_id", "case_id", "module")},
                        "method": variant,
                        "experiment_identity": identity,
                        "status": "failed",
                        "source_ids": [],
                        "error": error,
                    }
                    for variant in VARIANTS
                )
            trace["native_retrieval_seconds"] = perf_counter() - begin
            query_records.append(trace)
            print(f"Neo4j strategies {q['case_id']}/{q['module']} {trace['status']}", flush=True)
    if verify_bundle(input_directory) != input_pins or sources != {
        n: file_hash(root / n) for n in SOURCE_FILES
    }:
        raise ValueError("Reviewed inputs or strategy source changed during native execution")
    for filename, records in (("results.jsonl", rows), ("native_queries.jsonl", query_records)):
        (output / filename).write_text(
            "".join(json.dumps(r, ensure_ascii=False, allow_nan=False) + "\n" for r in records),
            encoding="utf-8",
        )
    summary = {
        "identity": identity,
        "primary_candidate": config["primary_candidate"],
        "planned": 77 * len(VARIANTS),
        "recorded": len(rows),
        "completed": sum(r["status"] == "completed" for r in rows),
        "failed": sum(r["status"] == "failed" for r in rows),
        "native_baseline": legacy_summary,
        "native_query_conditions": len(query_records),
        "actual_vector_searches": sum("vector_records" in r for r in query_records),
        "actual_fulltext_searches": sum("fulltext_records" in r for r in query_records),
        "actual_graph_searches": sum("graph_records" in r for r in query_records),
        "native_index_build_seconds": legacy["manifest"]["index_build_seconds"],
        "total_seconds": perf_counter() - native_started,
        "model_calls": 0,
        "sdk_version": importlib.metadata.version("neo4j-graphrag"),
        "production_change": False,
        "corpus_review_remaining": "pending clinical and complete textual applicability review",
    }
    write_json(output / "summary.json", summary)
    write_json(
        output / "artifacts.json", {p.name: file_hash(p) for p in output.iterdir() if p.is_file()}
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inputs", type=Path, default=Path("outputs/experiments/scope88_shared_retrieval_v2")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/experiments/scope88_neo4j_strategies_v2")
    )
    parser.add_argument(
        "--config", type=Path, default=Path("configs/experiments/neo4j_strategies_v2.json")
    )
    parser.add_argument("--uri", default="bolt://127.0.0.1:17687")
    parser.add_argument(
        "--credential-file", type=Path, default=Path(".runtime/neo4j/credential.json")
    )
    args = parser.parse_args()
    print(json.dumps(run(args.inputs, args.output, args.config, args.uri, args.credential_file)))
