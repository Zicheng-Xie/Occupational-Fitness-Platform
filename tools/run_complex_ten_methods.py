"""Execute all ten preserved retrieval strategies on the complete 234-note cohort."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from contextlib import nullcontext
from pathlib import Path
from time import perf_counter

import yaml

from occupational_fitness_rag.evaluation.guarded_hybrid import rank_channels
from occupational_fitness_rag.evaluation.judgment_comparison import local_post
from occupational_fitness_rag.evaluation.planned_hybrid import execute_plan
from occupational_fitness_rag.evaluation.prefix_allocation import allocate_prefix
from occupational_fitness_rag.indexing.base import StoredDocument
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json
from tools.complex_ten_inputs import DEFAULT, METHODS, ROOT, read, rows
from tools.run_scope88_prefix_allocation import GUARDED_CONFIG
from tools.run_scope88_shared_retrieval import deduplicate_channels
from tools.run_shared_retrieval import rank_method


def pin(path):
    return sha256_bytes(Path(path).read_bytes())


def append(path, value):
    with Path(path).open("ab") as stream:
        stream.write((json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n").encode())


def freeze(output):
    inventory, queries, corpus, patients = [
        read(output / n)
        for n in ("input_inventory.json", "queries.json", "corpus.json", "patients.json")
    ]
    if len(inventory) != 234 or set(patients) != {i["case_id"] for i in inventory}:
        raise ValueError("Incomplete patient preparation")
    protected = [
        ROOT / "configs/workflow.yaml",
        ROOT / "configs/rules/austroads_commercial_v1.yaml",
        ROOT / "data/knowledge/raw/ap_g56_22.pdf",
    ]
    protected += list((ROOT / "src/occupational_fitness_rag").rglob("*.py"))
    protected += [
        ROOT / ("tools/" + n)
        for n in [
            "complex_ten_inputs.py",
            "complex_ten_contract.py",
            "run_complex_ten_methods.py",
            "complex_native_worker.py",
            "run_scope88_tree.py",
            "pageindex_extension_worker.py",
            "flag_embedding_extension_worker.py",
            "run_neo4j_strategies.py",
            "neo4j_extension_worker.py",
            "run_shared_retrieval.py",
            "run_scope88_shared_retrieval.py",
            "run_scope88_prefix_allocation.py",
        ]
    ]
    protected += [ROOT / i["input"] for i in inventory]
    protected += list((ROOT / "data/cases/gold").glob("*.json"))
    protected += [ROOT / "outputs/experiments/scope88_shared_retrieval_v2/corpus_vectors.json"]
    sources = {str(p.relative_to(ROOT).as_posix()): pin(p) for p in protected}
    config = read(ROOT / "outputs/experiments/scope88_external_graph_v1/manifest.json")["config"]
    cfg = yaml.safe_load(
        (ROOT / "configs/experiments/planned_hybrid_v1.yaml").read_text(encoding="utf-8")
    )
    plan = {
        "kind": "complete_complex_234_ten_method_retrieval",
        "sources": sources,
        "prepared_files": {
            n: pin(output / n)
            for n in ["queries.json", "patients.json", "corpus.json", "input_inventory.json"]
        },
        "fact_files": {p.name: pin(p) for p in (output / "facts").glob("*.json")},
        "methods": METHODS,
        "cases": len(inventory),
        "query_scopes": len(queries),
        "planned_conditions": len(queries) * 10,
        "corpus_identity": corpus["corpus_sha256"],
        "external_config": config,
        "planned_config": cfg,
        "guarded_config": GUARDED_CONFIG,
        "clinical_review": "pending",
        "judgment_calls": 0,
        "production_change": False,
    }
    target = output / "plan.json"
    if target.exists():
        prior = read(target)
        if {k: v for k, v in prior.items() if k not in {"identity", "runtime"}} != plan:
            raise ValueError("Frozen inputs or implementation changed")
        return prior
    from tools.run_frozen_retrieval_judgments import runtime

    plan["runtime"] = runtime(
        {
            "endpoint": config["endpoint"],
            "expected_runtime_version": config["expected_runtime_version"],
            "expected_model_digests": {
                config["graph_model"]: config["graph_model_digest"],
                config["embedding_model"]: config["embedding_model_digest"],
            },
        }
    )
    plan["identity"] = digest(plan)
    write_json(target, plan)
    return plan


def verify(output, plan):
    if plan["identity"] != digest({k: v for k, v in plan.items() if k != "identity"}):
        raise ValueError("Plan self identity differs")
    for name, expected in plan["sources"].items():
        if pin(ROOT / name) != expected:
            raise ValueError("Frozen source changed: " + name)
    for name, expected in plan["prepared_files"].items():
        if pin(output / name) != expected:
            raise ValueError("Frozen query/corpus changed")
    for name, expected in plan["fact_files"].items():
        if pin(output / "facts" / name) != expected:
            raise ValueError("Frozen intake changed")


def embed(output, texts, model):
    folder = output / "embeddings"
    folder.mkdir(exist_ok=True)
    body = {"model": model, "input": texts, "truncate": False}
    cache = folder / (digest(body) + ".json")
    if cache.exists():
        r = read(cache)
        if r["request"] != body or r["record_sha256"] != digest(
            {k: v for k, v in r.items() if k != "record_sha256"}
        ):
            raise ValueError("Embedding cache changed")
        if r["status"] != "completed":
            raise ValueError("Retained embedding failure: " + r.get("error", "unknown"))
        return r["raw_response"]["embeddings"]
    record = {"request": body, "provider_called": True}
    begin = perf_counter()
    try:
        raw = local_post("http://127.0.0.1:11434", "/api/embed", body, 120)
        if len(raw["embeddings"]) != len(texts) or any(len(v) != 768 for v in raw["embeddings"]):
            raise ValueError("Actual embedding count or dimension differs")
        record.update(status="completed", raw_response=raw)
        return raw["embeddings"]
    except Exception as exc:
        record.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        record["seconds"] = perf_counter() - begin
        record["record_sha256"] = digest(record)
        write_json(cache, record)


def local_routes(output, plan):
    from occupational_fitness_rag.rules.engine import RuleBook

    corpus, queries, patients = [
        read(output / n) for n in ("corpus.json", "queries.json", "patients.json")
    ]
    units = {u["source_id"]: u for u in corpus["units"]}
    vectors = read(ROOT / "outputs/experiments/scope88_shared_retrieval_v2/corpus_vectors.json")
    original = read(ROOT / "outputs/experiments/scope88_shared_retrieval_v2/corpus.json")
    if original != corpus:
        raise ValueError("Shared actual source vectors refer to a different corpus")
    docs = [
        StoredDocument(u["source_id"], u["evidence_text"], {"module": u["module"]})
        for u in corpus["units"]
    ]
    book = RuleBook(ROOT / "configs/rules/austroads_commercial_v1.yaml")
    result_path = output / "local_rankings.jsonl"
    done = {(r["query_id"], r["method"]) for r in rows(result_path)}
    anchors, query_vectors = {}, {}
    for i, q in enumerate(queries, 1):
        qid, note = q["query_id"], q["query"]
        vec = embed(output, [note], plan["external_config"]["embedding_model"])[0]
        query_vectors[qid] = vec
        anchors[qid] = [
            r["source_id"]
            for r in rank_method(note, q["module"], "hybrid", docs, vectors, vec, units, book, 20)
        ]
        for method in METHODS[:4] + [METHODS[6]]:
            if (qid, method) in done:
                continue
            start = perf_counter()
            r = {k: q[k] for k in ("query_id", "case_id", "module", "cohort")}
            r.update(method=method, experiment_identity=plan["identity"], source_ids=[])
            try:
                if method == METHODS[6]:
                    data = execute_plan(
                        q,
                        patients[q["case_id"]],
                        corpus,
                        vectors,
                        vec,
                        lambda texts: embed(
                            output, texts, plan["external_config"]["embedding_model"]
                        ),
                        plan["planned_config"],
                    )
                    channels = deduplicate_channels(data)
                    baseline = rank_channels(channels, units, GUARDED_CONFIG)
                    result = allocate_prefix(baseline, units, "criterion_floor")
                    r.update(**result, plan_events=data["events"], channels_sha256=digest(channels))
                else:
                    ranked = rank_method(
                        note, q["module"], method, docs, vectors, vec, units, book, 10
                    )
                    r.update(source_ids=[v["source_id"] for v in ranked], ranked_sources=ranked)
                r["status"] = "completed"
            except Exception as exc:
                r.update(status="failed", source_ids=[], error=f"{type(exc).__name__}: {exc}")
            r["seconds"] = perf_counter() - start
            r["record_sha256"] = digest(r)
            append(result_path, r)
        if i % 20 == 0 or i == len(queries):
            print(f"Local five routes {i}/{len(queries)}", flush=True)
    write_json(output / "query_vectors.json", query_vectors)
    write_json(output / "anchor_candidates.json", anchors)


def execute(output=DEFAULT, selected=None):
    output = Path(output).resolve()
    plan = freeze(output)
    verify(output, plan)
    chosen = selected or [
        "local",
        "flag_embedding_rerank",
        "neo4j_frontier_criterion_v3",
        "pageindex_rrf_predicate_navigation",
        "lightrag",
        "graphrag",
    ]
    envs = {
        "flag_embedding_rerank": "flag_gpu",
        "neo4j_frontier_criterion_v3": "retrieval_extensions",
        "pageindex_rrf_predicate_navigation": "retrieval_extensions",
        "lightrag": "lightrag",
        "graphrag": "graphrag",
    }
    for method in chosen:
        if method == "local":
            local_routes(output, plan)
        else:
            folder = output / "workers" / method
            folder.mkdir(parents=True, exist_ok=True)
            if (folder / "complete.json").exists():
                continue
            command = [
                str(ROOT / ".runtime" / envs[method] / "Scripts/python.exe"),
                "-X",
                "utf8",
                "-m",
                "tools.complex_native_worker",
                "--output",
                str(output),
                "--method",
                method,
            ]
            env = {
                **os.environ,
                "PYTHONPATH": str(ROOT / "src") + os.pathsep + str(ROOT),
                "PYTHONUTF8": "1",
                "HF_HUB_OFFLINE": "1",
                "HF_HUB_DISABLE_TELEMETRY": "1",
            }
            if method in {"lightrag", "graphrag"}:
                from tools.run_external_graph_retrieval import AuditProxy

                context = AuditProxy(plan["external_config"], folder)
                context.job = folder
            else:
                context = nullcontext()
            with context, (folder / "stdout.log").open("a", encoding="utf-8") as log:
                result = subprocess.run(
                    command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT
                )
            print(f"Worker {method}: exit {result.returncode}", flush=True)
            if result.returncode:
                raise RuntimeError(
                    f"Worker {method} failed; inspect its retained log, no substitute used"
                )
        verify(output, plan)
    print("Selected retrieval stages finished", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT)
    parser.add_argument("--stages", nargs="+")
    args = parser.parse_args()
    execute(args.output, args.stages)
