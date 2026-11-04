"""Freeze shared inputs for three native retrieval extension workers, without labels."""

from __future__ import annotations

import json
from pathlib import Path

from occupational_fitness_rag.evaluation.anchored_hybrid import rank_channels
from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.evaluation.passage_comparison import read_records
from occupational_fitness_rag.provenance import digest, write_json
from tools.run_anchored_hybrid import reconstruct_channels, verify_saved
from tools.run_planned_hybrid import load_inputs


def prepare(root, output):
    parent_dir = root / "outputs/experiments/planned_hybrid_v1"
    parent, pins = verify_saved(parent_dir)
    corpus, queries, patients, vectors, anchors, imported = load_inputs(root, parent["config"])
    channels = reconstruct_channels(
        parent_dir,
        parent,
        read_records(parent_dir / "results.jsonl"),
        corpus,
        queries,
        patients,
        vectors,
        anchors,
    )
    units = {u["source_id"]: u for u in corpus["units"]}
    candidates = {}
    original = {
        (r["query_id"], r["method"]): r
        for r in read_records(root / "outputs/experiments/shared_retrieval_v1/results.jsonl")
    }
    for q in queries:
        result = rank_channels(
            channels[q["query_id"]],
            units,
            {"policy": "anchor_only", "candidate_k": 30, "sensitivity_k": 30},
        )
        ids = result["source_ids"]
        if ids[:10] != original[(q["query_id"], "hybrid")]["source_ids"]:
            raise ValueError("Native extension candidate anchor differs from original RRF")
        candidates[q["query_id"]] = ids[:20]
    data = {
        "kind": "three_native_retrieval_extensions_shared_inputs",
        "imported": imported,
        "parent_identity": parent["identity"],
        "parent_artifacts_sha256": file_hash(parent_dir / "artifacts.json"),
        "corpus_sha256": digest(corpus),
        "queries_sha256": digest(queries),
        "patients_sha256": digest(patients),
        "corpus_vectors_sha256": digest(vectors),
        "query_vectors_sha256": digest(anchors),
        "candidates_sha256": digest(candidates),
        "builder_sha256": file_hash(__file__),
        "labels_loaded": False,
    }
    identity = digest(data)
    if output.exists() or not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Use a fresh native extension input directory")
    output.mkdir(parents=True)
    for name, value in (
        ("corpus.json", corpus),
        ("queries.json", queries),
        ("patients.json", patients),
    ):
        write_json(output / name, value)
    flag = {
        "experiment_identity": identity,
        "corpus": corpus,
        "queries": queries,
        "candidates": candidates,
        "config": {
            "checkpoint_receipt": str(root / ".runtime/cache/models/bge_download_receipt.json"),
            "checkpoint_revision": "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e",
            "expected_versions": {"FlagEmbedding": "1.4.2", "torch": "2.14.1+cu130"},
            "threads": 4,
            "max_length": 2048,
            "batch_size": 2,
            "device": "cuda:0",
            "use_fp16": True,
        },
    }
    neo = {
        "experiment_identity": identity,
        "corpus": corpus,
        "queries": queries,
        "corpus_vectors": vectors,
        "query_vectors": anchors,
        "config": {
            "expected_sdk_version": "1.22.0",
            "expected_server_version": "2026.10.0",
            "embedding_dimensions": 768,
        },
    }
    page = {
        "corpus": str(output / "corpus.json"),
        "queries": str(output / "queries.json"),
        "output": "outputs/experiments/native_pageindex_retrieval_v1",
        "preparation_identity": imported["preparation"]["identity"],
        "config": {
            "endpoint": "http://127.0.0.1:11434",
            "model": "qwen3.5:4b-q4_K_M",
            "expected_model_digest": "91fa08b9fedfbbda924cd71febc5f6adbf31503cf7811df817dcf93bd56b08ff",
            "expected_runtime_version": "0.40.6",
            "expected_pageindex_version": "0.4.5",
            "context_length": 8192,
            "max_branches": 3,
            "candidate_max_bytes": 20000,
            "top_k": 10,
        },
    }
    for name, job in (
        ("flag_input.json", flag),
        ("neo4j_input.json", neo),
        ("pageindex_request.json", page),
    ):
        write_json(output / name, job)
    write_json(
        output / "worker_inputs.json",
        {
            n: file_hash(output / n)
            for n in ("flag_input.json", "neo4j_input.json", "pageindex_request.json")
        },
    )
    write_json(output / "manifest.json", {**data, "identity": identity, "production_change": False})
    (output / "builder_source.py").write_bytes(Path(__file__).read_bytes())
    if verify_saved(parent_dir)[1] != pins:
        raise ValueError("Parent rankings changed during preparation")
    write_json(
        output / "artifacts.json", {p.name: file_hash(p) for p in output.iterdir() if p.is_file()}
    )
    return {
        "identity": identity,
        "cases": len(patients),
        "queries": len(queries),
        "units": len(units),
        "model_calls": 0,
    }


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    print(
        json.dumps(
            prepare(root, root / "outputs/experiments/retrieval_extensions_inputs_v1"), indent=2
        )
    )
