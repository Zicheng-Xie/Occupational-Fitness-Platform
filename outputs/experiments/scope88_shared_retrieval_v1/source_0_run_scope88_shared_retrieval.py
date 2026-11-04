"""Recompute scoped retrieval on the reviewed corpus using audited real vectors.

Historical ranks are verified for provenance, never filtered into the new
rankings. Original-query and literal-facet embeddings are reusable only when
the exact source/query text matches a previously recorded native response.
No reference labels or network transport are used by this runner.
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from time import perf_counter

import yaml

from occupational_fitness_rag.evaluation.anchored_hybrid import rank_channels
from occupational_fitness_rag.evaluation.comparison_corpus import verify_corpus
from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.evaluation.passage_comparison import read_records
from occupational_fitness_rag.evaluation.planned_hybrid import execute_plan
from occupational_fitness_rag.indexing.base import StoredDocument
from occupational_fitness_rag.provenance import digest, write_json
from occupational_fitness_rag.rules.engine import RuleBook
from tools.run_anchored_hybrid import reconstruct_channels, verify_saved
from tools.run_planned_hybrid import load_inputs
from tools.run_shared_retrieval import METHODS, rank_method

SOURCES = (
    "tools/run_scope88_shared_retrieval.py",
    "tools/run_planned_hybrid.py",
    "tools/run_anchored_hybrid.py",
    "tools/run_shared_retrieval.py",
    "src/occupational_fitness_rag/evaluation/planned_hybrid.py",
    "src/occupational_fitness_rag/evaluation/anchored_hybrid.py",
    "src/occupational_fitness_rag/evaluation/comparison_corpus.py",
    "src/occupational_fitness_rag/retrieval/bm25.py",
    "src/occupational_fitness_rag/retrieval/fusion.py",
    "src/occupational_fitness_rag/retrieval/graph_local.py",
)


def read(path):
    return json.loads(Path(path).read_bytes())


def verify_files(directory):
    directory = Path(directory).resolve()
    pins = read(directory / "artifacts.json")
    if not pins:
        raise ValueError("Empty reviewed artifact inventory")
    for name, pin in pins.items():
        path = (directory / name).resolve()
        if not path.is_relative_to(directory) or file_hash(path) != pin:
            raise ValueError("Reviewed artifact changed: " + name)
    return pins


def subset_vectors(original, revised, vectors):
    """Select actual source vectors by exact unchanged original-unit identity."""
    if len(original["units"]) != len(vectors):
        raise ValueError("Historical source/vector count differs")
    old = {u["source_id"]: (u, v) for u, v in zip(original["units"], vectors, strict=True)}
    ids = [u["source_id"] for u in revised["units"]]
    if len(ids) != len(set(ids)) or not set(ids) < old.keys():
        raise ValueError("Reviewed corpus must be a strict unique subset")
    if revised["document_sha256"] != original["document_sha256"]:
        raise ValueError("Reviewed corpus source document changed")
    if any(u != old[u["source_id"]][0] for u in revised["units"]):
        raise ValueError("Reviewed source text or metadata differs from the real embedded unit")
    return [old[sid][1] for sid in ids]


def facet_embedder(directory, parent, query_id, calls):
    """Resolve one unchanged literal facet request to its actual native answer."""

    def embed(texts):
        body = {"model": parent["config"]["embedding_model"], "input": texts, "truncate": False}
        matching = [
            c
            for c in calls
            if c["query_id"] == query_id
            and c["status"] == "completed"
            and c["request"] == body
            and c["request_sha256"] == digest(body)
        ]
        if not matching:
            raise ValueError("Reviewed literal facet lacks an actual unchanged embedding request")
        cache = read(directory / "query_records" / (query_id + ".embedding.json"))
        answer = matching[-1]["raw_response"]["embeddings"]
        if (
            cache["key"] != digest({"identity": parent["identity"], "request": body})
            or cache["vectors"] != answer
            or len(answer) != len(texts)
        ):
            raise ValueError("Facet vector differs from the actual recorded native response")
        return answer

    return embed


def deduplicate_channels(result):
    channels = next(e["channels"] for e in result["events"] if e["stage"] == "search")
    followups = next(
        e["keyword_only_followups"] for e in result["events"] if e["stage"] == "refine"
    )
    merged = {}
    for channel in [*channels, *followups]:
        name = channel["channel"]
        if name in merged and merged[name] != channel:
            raise ValueError("A literal channel has conflicting actual rankings")
        merged[name] = channel
    return list(merged.values())


def prepare(root, config_path):
    root, config_path = Path(root).resolve(), Path(config_path).resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    parent_dir, reviewed_dir = [root / config[k] for k in ("historical_planned", "reviewed_corpus")]
    parent, parent_pins = verify_saved(parent_dir)
    reviewed_pins = verify_files(reviewed_dir)
    corpus = read(reviewed_dir / "corpus.json")
    if corpus["corpus_sha256"] != config["expected_reviewed_corpus_sha256"]:
        raise ValueError("Unexpected reviewed corpus identity")
    old, queries, patients, original_vectors, anchors, imports = load_inputs(root, parent["config"])
    verify_corpus(root, corpus)
    vectors = subset_vectors(old, corpus, original_vectors)
    if len(corpus["units"]) != 88 or len(queries) != 77 or len(patients) != 33:
        raise ValueError("The shared reviewed comparison requires 88/77/33 inputs")
    reconstruct_channels(
        parent_dir,
        parent,
        read_records(parent_dir / "results.jsonl"),
        old,
        queries,
        patients,
        original_vectors,
        anchors,
    )
    calls = read_records(parent_dir / "model_calls.jsonl")
    baseline = root / parent["config"]["baseline_dir"]
    baseline_manifest = read(baseline / "manifest.json")
    book = RuleBook(root / baseline_manifest["config"]["rules"])
    if book.sha256 != baseline_manifest["rules_sha256"]:
        raise ValueError("Source-graph baseline rules changed from the historical control")
    source_pins = {name: file_hash(root / name) for name in SOURCES}
    data = {
        "kind": "reviewed_scope_shared_retrieval_recomputed_from_actual_vectors",
        "config": config,
        "config_sha256": file_hash(config_path),
        "corpus_sha256": corpus["corpus_sha256"],
        "queries_sha256": digest(queries),
        "patients_sha256": digest(patients),
        "parent_identity": parent["identity"],
        "parent_artifacts_sha256": file_hash(parent_dir / "artifacts.json"),
        "reviewed_artifacts_sha256": file_hash(reviewed_dir / "artifacts.json"),
        "historical_imports": imports,
        "actual_source_vectors_sha256": digest(vectors),
        "actual_query_vectors_sha256": digest(anchors),
        "rules_sha256": book.sha256,
        "sources": source_pins,
        "python": sys.version,
        "labels_loaded": False,
        "actual_new_model_calls": 0,
        "remaining_textual_applicability_review": "pending",
    }
    identity = digest(data)
    output = (root / config["output"]).resolve()
    if output.exists() or not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Use a new experiment directory; retain historical rankings")
    output.mkdir(parents=True)
    write_json(output / "manifest.json", {**data, "identity": identity, "production_change": False})
    (output / "config.yaml").write_bytes(config_path.read_bytes())
    for i, name in enumerate(SOURCES):
        (output / f"source_{i}_{Path(name).name}").write_bytes((root / name).read_bytes())
    for name, value in (
        ("corpus.json", corpus),
        ("queries.json", queries),
        ("patients.json", patients),
        ("corpus_vectors.json", vectors),
        ("query_vectors.json", anchors),
    ):
        write_json(output / name, value)
    docs = [
        StoredDocument(
            u["source_id"],
            u["evidence_text"],
            {"module": u["module"], "source_ids_csv": u["source_id"]},
        )
        for u in corpus["units"]
    ]
    units = {u["source_id"]: u for u in corpus["units"]}
    rows, channels, events, candidates = [], {}, {}, {}
    for query in queries:
        qid = query["query_id"]
        for method in METHODS:
            started = perf_counter()
            row = {
                **{k: query[k] for k in ("query_id", "case_id", "module")},
                "method": method,
                "experiment_identity": identity,
            }
            try:
                ranked = rank_method(
                    query["query"],
                    query["module"],
                    method,
                    docs,
                    vectors,
                    anchors[qid],
                    units,
                    book,
                    20 if method == "hybrid" else 10,
                )
                ids = [r["source_id"] for r in ranked[:10]]
                if not ids or len(ids) != len(set(ids)):
                    raise ValueError("Empty or repeated original results")
                row.update(
                    status="completed",
                    source_ids=ids,
                    ranked_sources=ranked[:10],
                    candidate_source_ids=[r["source_id"] for r in ranked],
                    original_text_hashes={s: units[s]["text_sha256"] for s in ids},
                )
                if method == "hybrid":
                    candidates[qid] = [r["source_id"] for r in ranked]
            except Exception as exc:
                row.update(status="failed", source_ids=[], error=f"{type(exc).__name__}: {exc}")
            row["ranking_seconds_excluding_embedding_import"] = perf_counter() - started
            rows.append(row)
        result = execute_plan(
            query,
            patients[query["case_id"]],
            corpus,
            vectors,
            anchors[qid],
            facet_embedder(parent_dir, parent, qid, calls),
            parent["config"],
        )
        channels[qid] = deduplicate_channels(result)
        events[qid] = result["events"]
        anchor = rank_channels(
            channels[qid], units, {"policy": "anchor_only", "candidate_k": 30, "sensitivity_k": 30}
        )
        if anchor["source_ids"][:20] != candidates[qid]:
            raise ValueError("Reviewed anchor channels and fresh baseline RRF disagree")
    if any(r["status"] != "completed" for r in rows):
        raise ValueError("A reviewed baseline failed; do not freeze an incomplete input inventory")
    for name, value in (
        ("channels.json", channels),
        ("plan_events.json", events),
        ("anchor_candidates.json", candidates),
    ):
        write_json(output / name, value)
    (output / "results.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False, allow_nan=False) + "\n" for r in rows),
        encoding="utf-8",
    )
    old_jobs = root / "outputs/experiments/retrieval_extensions_inputs_v1"
    flag, neo = [
        deepcopy(read(old_jobs / name)) for name in ("flag_input.json", "neo4j_input.json")
    ]
    flag.update(experiment_identity=identity, corpus=corpus, queries=queries, candidates=candidates)
    neo.update(
        experiment_identity=identity,
        corpus=corpus,
        queries=queries,
        corpus_vectors=vectors,
        query_vectors=anchors,
    )
    write_json(output / "flag_input.json", flag)
    write_json(output / "neo4j_input.json", neo)
    write_json(
        output / "worker_inputs.json",
        {name: file_hash(output / name) for name in ("flag_input.json", "neo4j_input.json")},
    )
    summary = {
        "identity": identity,
        "cases": 33,
        "module_queries": 77,
        "original_units": 88,
        "planned": 308,
        "recorded": len(rows),
        "completed": len(rows),
        "failed": 0,
        "actual_new_model_calls": 0,
        "reused_shared_embedding_calls": 89,
        "reused_facet_embedding_calls": len(calls),
        "all_rankings_recomputed": True,
        "historical_top10_filtered_as_new_rankings": False,
        "keyword_followups": sum(
            len(next(e["keyword_only_followups"] for e in event if e["stage"] == "refine"))
            for event in events.values()
        ),
        "labels_loaded": False,
        "production_change": False,
        "interpretation": "Reviewed subset re-ranking, not complete commercial applicability certification or clinical accuracy",
    }
    write_json(output / "summary.json", summary)
    if (
        verify_saved(parent_dir)[1] != parent_pins
        or verify_files(reviewed_dir) != reviewed_pins
        or source_pins != {name: file_hash(root / name) for name in SOURCES}
    ):
        raise ValueError("Frozen source inputs or implementations changed during re-ranking")
    write_json(
        output / "artifacts.json", {p.name: file_hash(p) for p in output.iterdir() if p.is_file()}
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/experiments/scope88_shared_retrieval_v1.yaml")
    args = parser.parse_args()
    print(json.dumps(prepare(Path.cwd(), args.config), indent=2))
