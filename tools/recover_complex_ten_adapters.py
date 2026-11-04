"""Repair two experiment boundary contracts without replacing their retained failures."""

from __future__ import annotations

import argparse
from pathlib import Path
from time import perf_counter

from occupational_fitness_rag.evaluation.guarded_hybrid import rank_channels
from occupational_fitness_rag.evaluation.planned_hybrid import execute_plan
from occupational_fitness_rag.evaluation.prefix_allocation import allocate_prefix
from occupational_fitness_rag.indexing.base import StoredDocument
from occupational_fitness_rag.rules.engine import RuleBook
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
from tools.run_scope88_prefix_allocation import GUARDED_CONFIG
from tools.run_scope88_shared_retrieval import deduplicate_channels
from tools.run_shared_retrieval import rank_method


def repair(parent=DEFAULT):
    parent = Path(parent).resolve()
    plan = read(parent / "plan.json")
    verify(parent, plan)
    queries, corpus, patients, query_vectors = [
        read(parent / n)
        for n in ("queries.json", "corpus.json", "patients.json", "query_vectors.json")
    ]
    units = {u["source_id"]: u for u in corpus["units"]}
    vectors = read(ROOT / "outputs/experiments/scope88_shared_retrieval_v2/corpus_vectors.json")
    before = {(r["query_id"], r["method"]): r for r in rows(parent / "local_rankings.jsonl")}
    target = parent / "adapter_repair"
    target.mkdir(exist_ok=True)
    manifest = {
        "kind": "experiment_adapter_contract_repair",
        "parent_identity": plan["identity"],
        "parent_rankings_sha256": pin(parent / "local_rankings.jsonl"),
        "source_sha256": pin(__file__),
        "changes": [
            "Map every original chunk to source_ids_csv",
            "Pass successful baseline status and module to the unchanged prefix allocator",
        ],
        "ranking_strategy_changed": False,
        "labels_available_to_ranker": False,
        "new_model_calls": 0,
        "original_failure_records_retained": True,
    }
    manifest["identity"] = digest(manifest)
    if (target / "manifest.json").exists() and read(target / "manifest.json") != manifest:
        raise ValueError("Keep the previous repair and its lineage")
    write_json(target / "manifest.json", manifest)
    docs = [
        StoredDocument(
            u["source_id"],
            u["evidence_text"],
            {"module": u["module"], "source_ids_csv": u["source_id"]},
        )
        for u in corpus["units"]
    ]
    book = RuleBook(ROOT / "configs/rules/austroads_commercial_v1.yaml")
    done = {(r["query_id"], r["method"]) for r in rows(target / "results.jsonl")}
    for i, q in enumerate(queries, 1):
        for method in (METHODS[3], METHODS[6]):
            if (q["query_id"], method) in done:
                continue
            prior = before[(q["query_id"], method)]
            expected = (
                "'source_ids_csv'"
                if method == METHODS[3]
                else "Prefix allocation requires a successful actual baseline"
            )
            if prior["status"] != "failed" or expected not in prior.get("error", ""):
                raise ValueError("Only the diagnosed adapter errors enter this repair")
            r = {k: q[k] for k in ("query_id", "case_id", "module", "cohort")}
            r.update(
                method=method,
                experiment_identity=plan["identity"],
                repair_identity=manifest["identity"],
                parent_failure_sha256=digest(prior),
                source_ids=[],
            )
            start = perf_counter()
            try:
                if method == METHODS[3]:
                    ranks = rank_method(
                        q["query"],
                        q["module"],
                        method,
                        docs,
                        vectors,
                        query_vectors[q["query_id"]],
                        units,
                        book,
                        10,
                    )
                    r.update(source_ids=[v["source_id"] for v in ranks], ranked_sources=ranks)
                else:

                    def actual_embedding(texts):
                        body = {
                            "model": plan["external_config"]["embedding_model"],
                            "input": texts,
                            "truncate": False,
                        }
                        c = read(parent / "embeddings" / (digest(body) + ".json"))
                        if (
                            c["request"] != body
                            or c["status"] != "completed"
                            or c["record_sha256"]
                            != digest({k: v for k, v in c.items() if k != "record_sha256"})
                        ):
                            raise ValueError(
                                "Facet does not match an already recorded actual embedding"
                            )
                        return c["raw_response"]["embeddings"]

                    result = execute_plan(
                        q,
                        patients[q["case_id"]],
                        corpus,
                        vectors,
                        query_vectors[q["query_id"]],
                        actual_embedding,
                        plan["planned_config"],
                    )
                    channels = deduplicate_channels(result)
                    baseline = {
                        "module": q["module"],
                        "status": "completed",
                        **rank_channels(channels, units, GUARDED_CONFIG),
                    }
                    r.update(
                        **allocate_prefix(baseline, units, "criterion_floor"),
                        plan_events=result["events"],
                    )
                r["status"] = "completed"
            except Exception as exc:
                r.update(status="failed", source_ids=[], error=f"{type(exc).__name__}: {exc}")
            r["seconds"] = perf_counter() - start
            r["record_sha256"] = digest(r)
            append(target / "results.jsonl", r)
        if i % 30 == 0:
            print(f"Adapter repair {i}/{len(queries)}", flush=True)
    verify(parent, plan)
    actual = rows(target / "results.jsonl")
    write_json(
        target / "complete.json",
        {
            "recorded": len(actual),
            "failed": sum(r["status"] != "completed" for r in actual),
            "new_model_calls": 0,
            "results_sha256": pin(target / "results.jsonl"),
            "source_sha256": pin(__file__),
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, default=DEFAULT)
    repair(parser.parse_args().parent)
