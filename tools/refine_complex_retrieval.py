"""Freeze and evaluate five retrieval refinements on the unchanged 234 notes.

The original ten methods remain independent immutable baselines. Native Neo4j
and PageIndex candidates are replayed, not simulated or silently re-executed.
New literal sentence embeddings are real local Ollama requests with raw receipts.
"""

from __future__ import annotations

import argparse
import csv
import os
from collections import Counter
from pathlib import Path
from time import perf_counter

from occupational_fitness_rag.evaluation.planned_hybrid import execute_plan, search_channels
from occupational_fitness_rag.evaluation.retrieval_refinement import (
    POLICY,
    fuse_views,
    literal_facets,
    literal_parent_closure,
    original_footprints,
    refine_ranking,
)
from occupational_fitness_rag.indexing.base import StoredDocument
from occupational_fitness_rag.rules.engine import RuleBook
from tools.complex_ten_contract import DEFAULT as PARENT
from tools.complex_ten_contract import METHODS, ROOT, append, digest, pin, read, rows, write_json
from tools.report_complex_ten_methods import audit_rankings
from tools.run_complex_ten_methods import embed
from tools.run_shared_retrieval import rank_method

DEFAULT = ROOT / "outputs/experiments/complex_234_refinement_20261029"
TARGETS = [METHODS[i] for i in (2, 3, 6, 8, 9)]
SUFFIXES = ("protected_completion", "literal_facets")
VARIANTS = [method + "__" + suffix for method in TARGETS for suffix in SUFFIXES]
SOURCES = [
    "tools/refine_complex_retrieval.py",
    "tools/report_complex_refinement.py",
    "src/occupational_fitness_rag/evaluation/retrieval_refinement.py",
    "src/occupational_fitness_rag/case_intake/narrative_context.py",
    "src/occupational_fitness_rag/evaluation/planned_hybrid.py",
]


def freeze(output, parent):
    if (output / "protocol.json").exists():
        verify(output, parent)
        return read(output / "protocol.json")
    plan, queries, corpus, actual, pending = audit_rankings(parent)
    if pending or len(actual) != 3570 or any(r["status"] != "completed" for r in actual):
        raise ValueError("Require the complete, valid original ten-method comparison")
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "queries.json", queries)
    write_json(output / "corpus.json", corpus)
    write_json(output / "patients.json", read(parent / "patients.json"))
    # Includes actual wide native traces, not engineering reference answers.
    if (output / "baseline_rankings.jsonl").exists():
        if rows(output / "baseline_rankings.jsonl") != actual:
            raise ValueError("The retained baseline inventory differs")
    else:
        for row in actual:
            append(output / "baseline_rankings.jsonl", row)
    protocol = {
        "kind": "paired_234_note_retrieval_refinement",
        "date": "2026-10-29",
        "parent_identity": plan["identity"],
        "parent_directory": parent.name,
        "cases": 234,
        "query_scopes": 357,
        "corpus_originals": 88,
        "targets": TARGETS,
        "suffixes": list(SUFFIXES),
        "variants": VARIANTS,
        "planned_new_conditions": 357 * len(VARIANTS),
        "policy": POLICY,
        "frozen_ranking_configuration": {
            "literal_sentence_budget": 6,
            "anchor_weight": 0.65,
            "rrf_k": 60,
            "max_improvement_steps": 32,
            "protected_prefixes": [1, 3, 5, 10],
            "selection_objective": "lexicographic: typed atoms @5, all original atoms @5, typed atoms @10, all original atoms @10, discounted measured relevance",
            "parent_policy": "same-page complete literal containment of an actually retrieved original",
            "candidate_policy": "original-query channels; original method-specific graph/tree/planned candidates; bounded verbatim sentence vector/BM25 views",
        },
        "native_policy": "Frozen actual Neo4j response frontier and PageIndex navigated leaf inventory; new first-party ranking only, no new native graph/tree calls",
        "label_policy": "Open references only in the post-run scorer; no label-aware branch selection or source backfill",
        "validation_status": "development-cohort comparison; 40 correlated synthetic scenario families; no unseen or clinical-accuracy claim",
        "packet_policy": "unchanged round-robin five whole originals, 9000 serialized UTF-8 evidence bytes; no truncation or rank-six refill",
        "production_change": False,
        "retained_initial_implementation_attempt": {
            "directory": "initial_attempt",
            "protocol_sha256": pin(output / "initial_attempt/protocol.json"),
            "rankings_sha256": pin(output / "initial_attempt/rankings.jsonl"),
            "source_snapshots": {
                name: pin(output / "initial_attempt/implementation" / name) for name in SOURCES
            },
            "diagnosis": "A tuple swap assigned the replacement ID to both positions; duplicate-source validation rejected 1164 conditions. Correct the swap, retain all initial observations, and rerun all 3570 conditions without selecting favorable results.",
        }
        if (output / "initial_attempt/protocol.json").exists()
        else None,
        "new_fact_extraction_calls": 0,
        "judgment_calls": 0,
        "data_files": {
            n: pin(output / n)
            for n in ("queries.json", "corpus.json", "patients.json", "baseline_rankings.jsonl")
        },
        "parent_files": {
            n: pin(parent / n)
            for n in (
                "plan.json",
                "queries.json",
                "corpus.json",
                "patients.json",
                "comparison/summary.json",
                "comparison/references.json",
            )
        },
        "source_files": {n: pin(ROOT / n) for n in SOURCES},
        "embedding_model": plan["external_config"]["embedding_model"],
        "corpus_vectors_sha256": pin(
            ROOT / "outputs/experiments/scope88_shared_retrieval_v2/corpus_vectors.json"
        ),
        "case_hashes": {r["input"]: r["sha256"] for r in read(parent / "input_inventory.json")},
    }
    protocol["identity"] = digest(protocol)
    write_json(output / "protocol.json", protocol)
    return protocol


def verify(output, parent):
    protocol = read(output / "protocol.json")
    if protocol["identity"] != digest({k: v for k, v in protocol.items() if k != "identity"}):
        raise ValueError("Refinement protocol changed")
    for key, base in (("data_files", output), ("parent_files", parent), ("source_files", ROOT)):
        for name, expected in protocol[key].items():
            if pin(base / name) != expected:
                raise ValueError("Frozen refinement input changed: " + name)
    if protocol["corpus_vectors_sha256"] != pin(
        ROOT / "outputs/experiments/scope88_shared_retrieval_v2/corpus_vectors.json"
    ):
        raise ValueError("Original source vectors changed")
    # This validates the previous protocol's protected facts, original code,
    # rulebook and all intake artifacts without rewriting any old result.
    from tools.complex_ten_contract import verify as verify_parent

    verify_parent(parent, read(parent / "plan.json"))
    for item in read(parent / "input_inventory.json"):
        if pin(ROOT / item["input"]) != item["sha256"]:
            raise ValueError("An original nurse note changed")
    return protocol


def prepare(output, parent):
    protocol = freeze(output, parent)
    queries = read(output / "queries.json")
    existing_vectors = read(parent / "query_vectors.json")
    facets = {q["query_id"]: literal_facets(q["query"], q["module"], 6) for q in queries}
    texts = list(dict.fromkeys(text for values in facets.values() for text in values))
    vectors = {}
    for i in range(0, len(texts), 8):
        batch = texts[i : i + 8]
        result = embed(output, batch, protocol["embedding_model"])
        vectors.update(zip(batch, result, strict=True))
        if i % 80 == 0:
            print(
                f"Actual literal-sentence embeddings {min(i + 8, len(texts))}/{len(texts)}",
                flush=True,
            )
    write_json(output / "facet_queries.json", facets)
    write_json(output / "facet_vectors.json", vectors)
    write_json(
        output / "preparation.json",
        {
            "protocol_identity": protocol["identity"],
            "facets_sha256": pin(output / "facet_queries.json"),
            "vectors_sha256": pin(output / "facet_vectors.json"),
            "unique_sentences": len(texts),
            "literal_source_substrings_only": True,
            "source_query_vectors_sha256": pin(parent / "query_vectors.json"),
            "existing_vectors": len(existing_vectors),
            "labels_opened": False,
        },
    )
    return protocol


def run(output, parent):
    protocol = verify(output, parent)
    prepared = read(output / "preparation.json")
    for name, key in (
        ("facet_queries.json", "facets_sha256"),
        ("facet_vectors.json", "vectors_sha256"),
    ):
        if pin(output / name) != prepared[key]:
            raise ValueError("Prepared literal views changed")
    queries, corpus, patients = [
        read(output / n) for n in ("queries.json", "corpus.json", "patients.json")
    ]
    units = {u["source_id"]: u for u in corpus["units"]}
    source_vectors = read(
        ROOT / "outputs/experiments/scope88_shared_retrieval_v2/corpus_vectors.json"
    )
    query_vectors = read(parent / "query_vectors.json")
    facets, facet_vectors = read(output / "facet_queries.json"), read(output / "facet_vectors.json")
    baselines = {(r["query_id"], r["method"]): r for r in rows(output / "baseline_rankings.jsonl")}
    docs = [
        StoredDocument(
            u["source_id"],
            u["evidence_text"],
            {"module": u["module"], "source_ids_csv": u["source_id"]},
        )
        for u in corpus["units"]
    ]
    book = RuleBook(ROOT / "configs/rules/austroads_commercial_v1.yaml")
    parent_plan = read(parent / "plan.json")
    done = {(r["query_id"], r["method"]) for r in rows(output / "rankings.jsonl")}
    if len(done) != len(rows(output / "rankings.jsonl")):
        raise ValueError("Repeated refinement condition")
    for i, q in enumerate(queries, 1):
        qid, module = q["query_id"], q["module"]
        if all((qid, v) in done for v in VARIANTS):
            continue
        started = perf_counter()
        common_channels = search_channels(
            q["query"], module, corpus["units"], source_vectors, query_vectors[qid], "original"
        )
        sentence_channels = []
        for j, quote in enumerate(facets[qid]):
            for channel in search_channels(
                quote,
                module,
                corpus["units"],
                source_vectors,
                facet_vectors[quote],
                "sentence:" + str(j),
            ):
                sentence_channels.append(
                    {
                        "view": quote,
                        "engine": channel["kind"],
                        "source_ids": [h["source_id"] for h in channel["hits"]],
                    }
                )
        shared_search_seconds = perf_counter() - started
        for method in TARGETS:
            base = baselines[qid, method]
            begin = perf_counter()
            native_replayed = method in TARGETS[-2:]
            if method == METHODS[3]:
                wide = [
                    r["source_id"]
                    for r in rank_method(
                        q["query"],
                        module,
                        method,
                        docs,
                        source_vectors,
                        query_vectors[qid],
                        units,
                        book,
                        30,
                    )
                ]
            elif method == METHODS[6]:

                def recorded_embed(texts):
                    body = {"model": protocol["embedding_model"], "input": texts, "truncate": False}
                    receipt = read(parent / "embeddings" / (digest(body) + ".json"))
                    if (
                        receipt["request"] != body
                        or receipt["status"] != "completed"
                        or receipt["record_sha256"]
                        != digest({k: v for k, v in receipt.items() if k != "record_sha256"})
                    ):
                        raise ValueError("A frozen planned-facet embedding changed")
                    return receipt["raw_response"]["embeddings"]

                planned = execute_plan(
                    q,
                    patients[q["case_id"]],
                    corpus,
                    source_vectors,
                    query_vectors[qid],
                    recorded_embed,
                    parent_plan["planned_config"],
                )
                planned_channels = next(
                    e["channels"] for e in planned["events"] if e["stage"] == "search"
                )
                wide = list(
                    dict.fromkeys(h["source_id"] for c in planned_channels for h in c["hits"])
                )
            elif method == METHODS[8]:
                trace = base["actual_native_trace"]
                wide = list(
                    dict.fromkeys(
                        r["source_id"]
                        for key in ("vector_records", "fulltext_records", "graph_records")
                        for r in trace[key]
                    )
                )
            elif method == METHODS[9]:
                wide = base["candidate_source_ids"]
            else:
                wide = [h["source_id"] for c in common_channels for h in c["hits"]]
            wide = list(dict.fromkeys([*base["source_ids"], *wide]))
            setup_seconds = perf_counter() - begin
            for suffix in SUFFIXES:
                variant = method + "__" + suffix
                if (qid, variant) in done:
                    continue
                r = {k: q[k] for k in ("query_id", "case_id", "module", "cohort")}
                r.update(
                    method=variant,
                    baseline_method=method,
                    protocol_identity=protocol["identity"],
                    parent_record_sha256=digest(base),
                    source_ids=[],
                )
                start = perf_counter()
                try:
                    use_facets = suffix == "literal_facets"
                    channels = [{"view": "anchor", "engine": method, "source_ids": wide}]
                    candidates = wide.copy()
                    if use_facets:
                        available = set(wide) if native_replayed else set(units)
                        extra = [
                            {**c, "source_ids": [s for s in c["source_ids"] if s in available]}
                            for c in sentence_channels
                        ]
                        channels.extend(extra)
                        candidates.extend(s for c in extra for s in c["source_ids"])
                    footprints = original_footprints(units, module)
                    candidates = literal_parent_closure(candidates, footprints)
                    scores, proof = fuse_views(channels, 0.65, 60)
                    for sid in candidates:
                        # A literal parent inherits the strongest measured child
                        # support, with an explicit attenuation. It has no
                        # invented native graph or cross-encoder score.
                        if sid not in scores:
                            scores[sid] = 0.95 * max(
                                (scores.get(child, 0.0) for child in footprints[sid] - {sid}),
                                default=0.0,
                            )
                    result = refine_ranking(base, candidates, units, scores, max_steps=32)
                    r.update(
                        result,
                        status="completed",
                        ranking_evidence=proof,
                        native_frontier_replayed=native_replayed,
                        new_native_calls=0,
                    )
                except Exception as exc:
                    r.update(status="failed", source_ids=[], error=f"{type(exc).__name__}: {exc}")
                r.update(
                    seconds=perf_counter() - start,
                    method_setup_seconds=setup_seconds,
                    shared_search_seconds=shared_search_seconds,
                    prior_ranking_seconds=base["seconds"],
                    timing_interpretation="new post-retrieval optimization only; cached embeddings and retained native/LLM navigation excluded",
                )
                r["record_sha256"] = digest(r)
                append(output / "rankings.jsonl", r)
        if i % 10 == 0 or i == len(queries):
            print(
                f"Protected refinement {i}/{len(queries)} query scopes; {i * len(VARIANTS)} planned prefix conditions",
                flush=True,
            )
    verify(output, parent)
    actual = rows(output / "rankings.jsonl")
    keys = {(r["query_id"], r["method"]) for r in actual}
    expected = {(q["query_id"], v) for q in queries for v in VARIANTS}
    if keys != expected or len(actual) != len(expected):
        raise ValueError("Incomplete or repeated refinement grid")
    write_json(
        output / "complete.json",
        {
            "recorded": len(actual),
            "failed": sum(r["status"] != "completed" for r in actual),
            "results_sha256": pin(output / "rankings.jsonl"),
            "protocol_identity": protocol["identity"],
            "failure_reasons": dict(
                Counter(r.get("error") for r in actual if r["status"] != "completed")
            ),
        },
    )


def export_csv(path, records):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "run", "report"))
    parser.add_argument("--output", type=Path, default=DEFAULT)
    parser.add_argument("--parent", type=Path, default=PARENT)
    args = parser.parse_args()
    if args.stage == "prepare":
        prepare(args.output.resolve(), args.parent.resolve())
    elif args.stage == "run":
        args.output.mkdir(parents=True, exist_ok=True)
        lock = args.output / ".owner.lock"
        with lock.open("x", encoding="ascii") as stream:
            stream.write(str(os.getpid()))
        try:
            run(args.output.resolve(), args.parent.resolve())
        finally:
            lock.unlink()
    else:
        from tools.report_complex_refinement import report

        report(args.output.resolve(), args.parent.resolve())
