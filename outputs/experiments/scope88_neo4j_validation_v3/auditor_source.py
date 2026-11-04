"""Reconstruct new Neo4j strategy rankings from frozen actual native responses."""

from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.evaluation.neo4j_criterion_transfer import (
    VARIANTS as TRANSFER_VARIANTS,
)
from occupational_fitness_rag.evaluation.neo4j_criterion_transfer import transfer
from occupational_fitness_rag.evaluation.neo4j_strategies import VARIANTS, native_rrf, rank
from occupational_fitness_rag.provenance import digest, write_json
from tools.run_neo4j_strategies import verify_bundle


def read(path):
    return json.loads(Path(path).read_bytes())


def records(path):
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def audit(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists() or not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Use a fresh audit output directory")
    parent = root / "outputs/experiments/scope88_neo4j_strategies_v2"
    child = root / "outputs/experiments/scope88_neo4j_criterion_transfer_v3"
    shared = root / "outputs/experiments/scope88_shared_retrieval_v2"
    directories = (parent, child, shared)
    inventories = {d.name: verify_bundle(d) for d in directories}
    corpus, queries = [read(shared / n) for n in ("corpus.json", "queries.json")]
    units = {u["source_id"]: u for u in corpus["units"]}
    anchors = read(shared / "anchor_candidates.json")
    qmap = {q["query_id"]: q for q in queries}
    traces = {r["query_id"]: r for r in records(parent / "native_queries.jsonl")}
    parent_rows = records(parent / "results.jsonl")
    children = records(child / "results.jsonl")
    by_pair = {(r["query_id"], r["method"]): r for r in parent_rows}
    if len(by_pair) != 231 or len(children) != 154 or len(traces) != 77 or set(traces) != set(qmap):
        raise ValueError("Native result inventory is missing or duplicated")
    parent_matches = transfer_matches = graph_paths = 0
    for qid, trace in traces.items():
        query = qmap[qid]
        if (
            query["corpus_sha256"] != corpus["corpus_sha256"]
            or trace["frozen_query"] != query["query"]
        ):
            raise ValueError("Actual native query does not bind to the reviewed corpus/text")
        native = native_rrf(
            trace["vector_records"], trace["fulltext_records"], units, query["module"]
        )
        if native != trace["native_rrf"]:
            raise ValueError("Native engine rank fusion cannot be reconstructed")
        graph_paths += len(trace["graph_records"])
        for variant in VARIANTS:
            expected = rank(
                variant, anchors[qid], native, trace["graph_records"], units, query["module"]
            )
            row = by_pair[(qid, variant)]
            if row["status"] != "completed" or any(row[k] != expected[k] for k in expected):
                raise ValueError("Native strategy differs from actual response reconstruction")
            parent_matches += 1
    for row in children:
        qid = row["query_id"]
        if row["method"] not in TRANSFER_VARIANTS:
            raise ValueError("Unexpected transfer method")
        baseline = by_pair[(qid, VARIANTS[-1])]
        expected = transfer(row["method"], baseline, traces[qid], units)
        if row["status"] != "completed" or any(row[k] != expected[k] for k in expected):
            raise ValueError("Transfer ranking differs from the actual native source frontier")
        transfer_matches += 1
    baseline = read(parent / "native_baseline.json")
    if baseline["manifest"]["original_sources"] != 88 or len(baseline["manifest"]["indexes"]) != 10:
        raise ValueError("Native Neo4j corpus/index inventory differs")
    for row in baseline["results"]:
        if row["status"] != "completed" or row["query_id"] not in qmap:
            raise ValueError("Native baseline is failed or out of scope")
        for hit in row["ranked_sources"]:
            sid = hit["source_id"]
            if sid not in units or units[sid]["module"] != row["module"]:
                raise ValueError("Native baseline returned a quarantined or cross-module original")
            if any(p["text_sha256"] != units[sid]["text_sha256"] for p in hit["graph_paths"]):
                raise ValueError("Native baseline original source hashes differ")
    for d in directories:
        if verify_bundle(d) != inventories[d.name]:
            raise ValueError("Frozen native inputs changed during the audit")
    try:
        with socket.create_connection(("127.0.0.1", 17687), timeout=0.5):
            listener_status = "running"
    except ConnectionRefusedError:
        listener_status = "stopped"
    except OSError:
        listener_status = "unavailable"
    checks = {
        "corpus_sha256": corpus["corpus_sha256"],
        "actual_source_count": len(units),
        "unique_query_conditions": len(qmap),
        "reconstructed_native_strategy_rows": parent_matches,
        "reconstructed_typed_transfer_rows": transfer_matches,
        "actual_native_graph_path_records": graph_paths,
        "native_baseline_rows_mapped": len(baseline["results"]),
        "native_online_indexes": len(baseline["manifest"]["indexes"]),
        "all_reconstructed_rankings_match": True,
        "source_hashes_and_module_scope_valid": True,
        "new_model_calls": 0,
        "new_native_calls": 0,
        "reference_labels_used_by_audit": False,
        "experimental_native_server_loopback_listener_observed": listener_status,
        "production_change": False,
    }
    data = {
        "kind": "actual_native_query_and_source_allocation_reconstruction_audit",
        "input_artifact_sha256": {d.name: file_hash(d / "artifacts.json") for d in directories},
        "auditor_sha256": file_hash(__file__),
        "checks": checks,
    }
    output.mkdir(parents=True)
    write_json(output / "manifest.json", {**data, "identity": digest(data)})
    write_json(output / "checks.json", checks)
    (output / "auditor_source.py").write_bytes(Path(__file__).read_bytes())
    write_json(
        output / "artifacts.json", {p.name: file_hash(p) for p in output.iterdir() if p.is_file()}
    )
    return checks


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/experiments/scope88_neo4j_validation_v3")
    )
    print(json.dumps(audit(Path(__file__).resolve().parents[1], parser.parse_args().output)))
