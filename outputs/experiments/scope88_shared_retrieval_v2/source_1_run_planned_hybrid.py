"""Execute an additional retrieval arm without rewriting the six baselines.

Uses the exact shared corpus/query embeddings already audited by the baseline.
Only facet embeddings are new calls. Labels are opened by a separate reporter
after all new rankings have been frozen.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from time import perf_counter

import yaml

from occupational_fitness_rag.evaluation.comparison_corpus import verify_corpus
from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.evaluation.judgment_comparison import local_post
from occupational_fitness_rag.evaluation.passage_comparison import (
    HybridRetriever,
    pinned_environment,
    read_records,
)
from occupational_fitness_rag.evaluation.planned_hybrid import METHOD, execute_plan
from occupational_fitness_rag.provenance import digest, write_json

BOUND_SOURCES = (
    "tools/run_planned_hybrid.py",
    "configs/experiments/planned_hybrid_sources.json",
    "src/occupational_fitness_rag/evaluation/planned_hybrid.py",
    "src/occupational_fitness_rag/retrieval/bm25.py",
    "src/occupational_fitness_rag/evaluation/passage_comparison.py",
    "src/occupational_fitness_rag/evaluation/judgment_comparison.py",
    "src/occupational_fitness_rag/evaluation/comparison_corpus.py",
    "src/occupational_fitness_rag/evaluation/graph_contract.py",
    "src/occupational_fitness_rag/indexing/base.py",
    "src/occupational_fitness_rag/provenance.py",
)


def load_inputs(root, config):
    prep, baseline = [root / config[key] for key in ("preparation_dir", "baseline_dir")]
    pins = json.loads((prep / "artifacts.json").read_bytes())
    if pins["identity"] != config["expected_preparation_identity"]:
        raise ValueError("Unexpected query preparation")
    for name, expected in pins["artifacts"].items():
        if file_hash(prep / name) != expected:
            raise ValueError("Prepared artifact changed: " + name)
    corpus, queries, patients = [
        json.loads((prep / name).read_bytes())
        for name in ("corpus.json", "queries.json", "patients.json")
    ]
    verify_corpus(root, corpus)
    audit = json.loads((baseline / "execution_audit.json").read_bytes())
    for name, key in (
        ("results.jsonl", "results_sha256"),
        ("manifest.json", "manifest_sha256"),
        ("embedding_calls.jsonl", "embedding_calls_sha256"),
    ):
        if file_hash(baseline / name) != audit[key]:
            raise ValueError("Completed baseline changed: " + name)
    bm = json.loads((baseline / "manifest.json").read_bytes())
    if (
        bm["identity"] != config["expected_baseline_identity"]
        or bm["preparation_artifacts"] != pins
    ):
        raise ValueError("Baseline preparation identity differs")
    for name, value in (("corpus.json", corpus), ("queries.json", queries)):
        if json.loads((baseline / name).read_bytes()) != value:
            raise ValueError("Baseline and new method do not use identical inputs")
    saved = json.loads((baseline / "embeddings.json").read_bytes())
    calls = read_records(baseline / "embedding_calls.jsonl")
    originals = [u["evidence_text"] for u in corpus["units"]]
    rebuilt, original_inputs, query_vectors = [], [], {}
    for call in calls:
        body = call["request"]
        if (
            call["request_sha256"] != digest(body)
            or call["status"] != "completed"
            or body["model"] != config["embedding_model"]
            or body.get("truncate") is not False
        ):
            raise ValueError("Imported embedding call contract differs")
        texts = body["input"]
        response_vectors = call["raw_response"]["embeddings"]
        if len(texts) != len(response_vectors):
            raise ValueError("Imported embedding response count differs")
        if len(original_inputs) < len(originals):
            original_inputs.extend(texts)
            rebuilt.extend(response_vectors)
        else:
            if len(texts) != 1:
                raise ValueError("Shared query embedding must have one input")
            if texts[0] in query_vectors and query_vectors[texts[0]] != response_vectors[0]:
                raise ValueError("Duplicate query has inconsistent historical embeddings")
            query_vectors[texts[0]] = response_vectors[0]
    if (
        original_inputs != originals
        or rebuilt != saved["vectors"]
        or saved["vectors_sha256"] != digest(rebuilt)
        or saved["identity"] != bm["identity"]
    ):
        raise ValueError("Corpus vectors do not reconstruct from audited actual responses")
    query_pins, anchors = {}, {}
    for query in queries:
        path = baseline / "query_embeddings" / (query["query_id"] + ".json")
        cache = json.loads(path.read_bytes())
        vector = query_vectors.get(query["query"])
        if (
            cache["identity"] != bm["identity"]
            or cache["status"] != "completed"
            or cache["query_sha256"] != query["query_audit"]["query_sha256"]
            or cache["vector"] != vector
            or cache["vector_sha256"] != digest(vector)
        ):
            raise ValueError("Anchor vector differs from the audited shared query")
        query_pins[query["query_id"]] = file_hash(path)
        anchors[query["query_id"]] = vector
    imported = {
        "preparation": pins,
        "baseline_audit": audit,
        "baseline_identity": bm["identity"],
        "embeddings_sha256": file_hash(baseline / "embeddings.json"),
        "anchor_files": query_pins,
    }
    return corpus, queries, patients, rebuilt, anchors, imported


def run(config_path, resume=False):
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    if (
        config["sensitivity_k"] != 10
        or config["rrf_k"] != 60
        or not 0 < config["relevance_weight"] <= 1
        or not 0 <= config["lexical_coverage_threshold"] <= 1
        or type(config["max_keyword_followups"]) is not int
        or not 0 <= config["max_keyword_followups"] <= 2
    ):
        raise ValueError("Invalid bounded retrieval policy")
    corpus, queries, patients, vectors, anchors, imported = load_inputs(root, config)
    source_pins = {name: file_hash(root / name) for name in BOUND_SOURCES}
    env = pinned_environment(config)
    identity_data = {
        "kind": "additional_retrieval_arm",
        "method": METHOD,
        "config": config,
        "imported": imported,
        "sources": source_pins,
        "environment": env,
        "python": sys.version,
        "query_ids": [q["query_id"] for q in queries],
    }
    manifest = {**identity_data, "identity": digest(identity_data), "production_change": False}
    output = (root / config["output"]).resolve()
    if not output.is_relative_to(root / "outputs/experiments") or output.is_relative_to(
        root / config["baseline_dir"]
    ):
        raise ValueError("Use a separate experimental output directory")
    output.mkdir(parents=True, exist_ok=True)
    lock = output / ".run.lock"
    with lock.open("x", encoding="ascii") as stream:
        stream.write(str(os.getpid()))
    try:
        target = output / "manifest.json"
        if target.exists():
            if not resume or json.loads(target.read_bytes()) != manifest:
                raise ValueError(
                    "Resume requires identical method, model, query and corpus versions"
                )
        elif any(path.name != ".run.lock" for path in output.iterdir()):
            raise ValueError("Preserve unowned output files")
        else:
            write_json(target, manifest)
            for name, content in (("corpus.json", corpus), ("queries.json", queries)):
                write_json(output / name, content)
            (output / "method_source.py").write_bytes((root / BOUND_SOURCES[2]).read_bytes())
            (output / "runner_source.py").write_bytes(Path(__file__).read_bytes())
            write_json(
                output / "design_sources.json", json.loads((root / BOUND_SOURCES[1]).read_bytes())
            )
        rows = read_records(output / "results.jsonl")
        qmap = {q["query_id"]: q for q in queries}
        done = set()
        for row in rows:
            if (
                row["query_id"] not in qmap
                or row["query_id"] in done
                or row["experiment_identity"] != manifest["identity"]
                or row["method"] != METHOD
                or row["case_id"] != qmap[row["query_id"]]["case_id"]
                or row["module"] != qmap[row["query_id"]]["module"]
            ):
                raise ValueError("Saved ranking has an invalid identity or scope")
            done.add(row["query_id"])
        helper = HybridRetriever(corpus, config, output, manifest["identity"])
        helper.validate_vectors(vectors, len(corpus["units"]))
        (output / "query_records").mkdir(exist_ok=True)
        for query in queries:
            if query["query_id"] in done:
                continue
            started = perf_counter()
            record = {
                "query_id": query["query_id"],
                "case_id": query["case_id"],
                "module": query["module"],
                "query_sha256": query["query_audit"]["query_sha256"],
                "method": METHOD,
                "experiment_identity": manifest["identity"],
            }
            qpath = output / "query_records" / (query["query_id"] + ".json")

            def embed(texts):
                pinned_environment(config)
                body = {"model": config["embedding_model"], "input": texts, "truncate": False}
                cache = qpath.with_suffix(".embedding.json")
                key = digest({"identity": manifest["identity"], "request": body})
                if cache.exists():
                    saved = json.loads(cache.read_bytes())
                    if saved["key"] != key:
                        raise ValueError("Facet embedding checkpoint differs")
                    helper.validate_vectors(saved["vectors"], len(texts))
                    # A cache is accepted only if the corresponding real call was recorded.
                    known = [
                        r
                        for r in read_records(output / "model_calls.jsonl")
                        if r["query_id"] == query["query_id"]
                        and r["request_sha256"] == digest(body)
                        and r["status"] == "completed"
                    ]
                    if not known or known[-1]["raw_response"]["embeddings"] != saved["vectors"]:
                        raise ValueError("Facet cache lacks its actual audited response")
                    return saved["vectors"]
                call = {
                    "query_id": query["query_id"],
                    "route": "/api/embed",
                    "request": body,
                    "request_sha256": digest(body),
                    "experiment_identity": manifest["identity"],
                }
                called = perf_counter()
                try:
                    raw = local_post(
                        config["endpoint"], "/api/embed", body, config["timeout_seconds"]
                    )
                    call["raw_response"] = raw
                    values = raw.get("embeddings", [])
                    helper.validate_vectors(values, len(texts))
                    call["status"] = "completed"
                except Exception as exc:
                    call.update(status="failed", error=f"{type(exc).__name__}: {exc}")
                    raise
                finally:
                    call["seconds"] = perf_counter() - called
                    with (output / "model_calls.jsonl").open("a", encoding="utf-8") as stream:
                        stream.write(json.dumps(call, ensure_ascii=False, allow_nan=False) + "\n")
                write_json(cache, {"key": key, "vectors": values})
                return values

            try:
                result = execute_plan(
                    query,
                    patients[query["case_id"]],
                    corpus,
                    vectors,
                    anchors[query["query_id"]],
                    embed,
                    config,
                )
                record.update(status="completed", **result)
            except Exception as exc:
                record.update(
                    status="failed",
                    source_ids=[],
                    ranked_sources=[],
                    error=f"{type(exc).__name__}: {exc}",
                )
            record["retrieval_seconds_including_facet_embeddings"] = perf_counter() - started
            write_json(qpath, record)
            with (output / "results.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
            rows.append(record)
            done.add(query["query_id"])
            print(
                f"{METHOD}: {len(rows)}/{len(queries)} {query['case_id']}/{query['module']} {record['status']}",
                flush=True,
            )
        # Reconstruct every completed ranking from retained real facet responses.
        # This also verifies checkpoint contents on resume; cached model attempts
        # are never accepted as unobserved, synthetic or additional model calls.
        for row in rows:
            if row["status"] != "completed":
                continue
            query = qmap[row["query_id"]]

            def frozen_embed(texts):
                body = {"model": config["embedding_model"], "input": texts, "truncate": False}
                cached = json.loads(
                    (
                        output / "query_records" / (query["query_id"] + ".embedding.json")
                    ).read_bytes()
                )
                real = [
                    r
                    for r in read_records(output / "model_calls.jsonl")
                    if r["query_id"] == query["query_id"]
                    and r["request_sha256"] == digest(body)
                    and r["status"] == "completed"
                ]
                if (
                    cached["key"] != digest({"identity": manifest["identity"], "request": body})
                    or not real
                    or real[-1]["raw_response"]["embeddings"] != cached["vectors"]
                ):
                    raise ValueError(
                        "Recorded facet vectors are not backed by actual matching calls"
                    )
                return cached["vectors"]

            expected = execute_plan(
                query,
                patients[query["case_id"]],
                corpus,
                vectors,
                anchors[query["query_id"]],
                frozen_embed,
                config,
            )
            if any(row.get(key) != value for key, value in expected.items()):
                raise ValueError(
                    "Saved ranking cannot reconstruct from frozen facts, sources and responses"
                )
        if load_inputs(root, config)[-1] != imported:
            raise ValueError("Imported baseline artifacts changed during execution")
        if {
            name: file_hash(root / name) for name in BOUND_SOURCES
        } != source_pins or pinned_environment(config) != env:
            raise ValueError("Method source or runtime changed during execution")
        calls = read_records(output / "model_calls.jsonl")
        summary = {
            "identity": manifest["identity"],
            "method": METHOD,
            "recorded": len(rows),
            "planned": len(queries),
            "completed": sum(r["status"] == "completed" for r in rows),
            "failures": sum(r["status"] == "failed" for r in rows),
            "actual_new_embedding_calls": len(calls),
            "actual_new_embedding_inputs": sum(len(r["request"]["input"]) for r in calls),
            "failed_model_calls": sum(r["status"] != "completed" for r in calls),
            "judgment_calls": 0,
            "keyword_followups": sum(r.get("keyword_followups", 0) for r in rows),
            "shared_embedding_calls_imported_not_recounted": imported["baseline_audit"][
                "embedding_calls"
            ],
            "original_methods_changed": False,
            "production_change": False,
            "results_sha256": file_hash(output / "results.jsonl"),
            "model_calls_sha256": file_hash(output / "model_calls.jsonl") if calls else None,
        }
        write_json(output / "summary.json", summary)
        write_json(
            output / "artifacts.json",
            {
                str(p.relative_to(output)).replace("\\", "/"): file_hash(p)
                for p in output.rglob("*")
                if p.is_file() and p.name not in {".run.lock", "artifacts.json"}
            },
        )
        return summary
    finally:
        lock.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.config, args.resume), indent=2))
