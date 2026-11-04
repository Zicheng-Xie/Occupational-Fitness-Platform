"""Replay native graph baselines with new vision indexes and audited module reuse.

The four unchanged module indexes and actual prior query answers are imported
with their original identities. Vision is rebuilt through the real external
workers. No filtered historical Top10 substitutes for changed-corpus retrieval.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from collections import Counter
from copy import deepcopy
from pathlib import Path
from time import perf_counter

import yaml

from occupational_fitness_rag.evaluation.graph_contract import (
    file_hash,
    fingerprint,
    validate_records,
    verify_index,
    verify_request,
    verify_runtime,
)
from occupational_fitness_rag.provenance import write_json
from tools.run_external_graph_retrieval import METHODS, AuditProxy, runtime_environment
from tools.run_scope88_shared_retrieval import read, verify_files


def import_unchanged_modules(corpus, queries, lineage, old_corpus, old_queries, old_rows):
    """Reuse only byte-identical disease inputs; never import a changed module."""
    unchanged = []
    for module in sorted({q["module"] for q in queries}):
        before = [u for u in old_corpus["units"] if u["module"] == module]
        after = [u for u in corpus["units"] if u["module"] == module]
        if before == after:
            unchanged.append(module)
    if set(unchanged) != {"blackout", "hypertension", "diabetes", "hearing"}:
        raise ValueError("Expected exactly four unchanged module corpora")
    old_q = {q["query_id"]: q for q in old_queries}
    old_results = {(r["query_id"], r["method"]): r for r in old_rows}
    original, mapped = [], []
    for query in queries:
        if query["module"] not in unchanged:
            continue
        prior_id = lineage[query["query_id"]]["parent_query_id"]
        before = old_q[prior_id]
        if {k: v for k, v in before.items() if k not in {"corpus_sha256", "query_id"}} != {
            k: v for k, v in query.items() if k not in {"corpus_sha256", "query_id"}
        }:
            raise ValueError("Unchanged module has a different literal query or fact audit")
        for method in METHODS:
            prior = old_results[(prior_id, method)]
            if prior["status"] != "completed":
                raise ValueError("Cannot import a failed native query as successful retrieval")
            original.append(prior)
            row = deepcopy(prior)
            row.update(query)
            row.update(
                parent_experiment_identity=prior["experiment_identity"],
                parent_query_id=prior_id,
                parent_result_sha256=fingerprint(prior),
                native_execution_origin="actual unchanged module index and literal query reused",
                actual_new_model_calls=0,
            )
            mapped.append(row)
    return unchanged, original, mapped


def prepare(root, config_path):
    root, config_path = Path(root).resolve(), Path(config_path).resolve()
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    shared = root / cfg["shared"]
    shared_pins = verify_files(shared)
    corpus, queries, lineage = [
        read(shared / n) for n in ("corpus.json", "queries.json", "query_lineage.json")
    ]
    old_dir = root / cfg["historical_external"]
    old_manifest = read(old_dir / "manifest.json")
    old_summary = read(old_dir / "summary.json")
    if (
        file_hash(old_dir / "results.jsonl") != old_summary["results_sha256"]
        or file_hash(old_dir / "model_calls.jsonl") != old_summary["model_calls_sha256"]
        or fingerprint(
            {k: v for k, v in old_manifest.items() if k not in {"identity", "production_change"}}
        )
        != old_manifest["identity"]
    ):
        raise ValueError("Historical native graph results or identity changed")
    old_prep = root / old_manifest["config"]["preparation_dir"]
    old_corpus, old_queries = [read(old_prep / n) for n in ("corpus.json", "queries.json")]
    old_rows = [
        json.loads(line)
        for line in (old_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    modules, originals, imported = import_unchanged_modules(
        corpus, queries, lineage, old_corpus, old_queries, old_rows
    )
    worker = root / "src/occupational_fitness_rag/evaluation/graph_worker.py"
    contract_source = worker.with_name("graph_contract.py")
    if (
        file_hash(worker) != old_manifest["worker_sha256"]
        or file_hash(contract_source) != old_manifest["contract_sha256"]
    ):
        raise ValueError("Native baseline implementation differs from historical method")
    index_pins = {}
    for method in METHODS:
        for module in modules:
            request = read(old_dir / "requests" / f"{method}-{module}.json")
            work = old_dir / "indexes" / method / module
            state = verify_index(work, method, request["index_contracts"][module])
            index_pins[f"{method}/{module}"] = {
                "index_manifest_sha256": file_hash(work / "index_manifest.json"),
                "index_identity": state["contract_sha256"],
                "source_mapping_sha256": state["source_mapping_sha256"],
                "completion_sha256": state["completion_sha256"],
            }
    settings = deepcopy(old_manifest["config"])
    settings.update(
        preparation_dir=cfg["shared"],
        expected_preparation_identity=read(shared / "manifest.json")["identity"],
        baseline_dir=cfg["shared"],
        output=cfg["output"],
    )
    environments = {
        m: runtime_environment(root / f".runtime/{m}/Scripts/python.exe", m, root) for m in METHODS
    }
    if environments != old_manifest["environments"]:
        raise ValueError("Native baseline dependency environment changed")
    data = {
        "kind": "scope88_native_external_graph_replay_with_unchanged_module_imports",
        "config": settings,
        "shared_identity": read(shared / "manifest.json")["identity"],
        "shared_artifacts_sha256": file_hash(shared / "artifacts.json"),
        "old_identity": old_manifest["identity"],
        "old_results_sha256": old_summary["results_sha256"],
        "old_calls_sha256": old_summary["model_calls_sha256"],
        "imported_indexes": index_pins,
        "worker_sha256": file_hash(worker),
        "contract_sha256": file_hash(contract_source),
        "runner_sha256": file_hash(__file__),
        "environments": environments,
        "old_runner_sha256": file_hash(root / "tools/run_external_graph_retrieval.py"),
        "shared_config": cfg,
        "planned_new_module": "vision",
        "imported_rows": len(imported),
        "planned_new_query_results": 24,
        "reference_labels_available": False,
        "reused_rows_are_actual_prior_results_not_new_calls": True,
    }
    identity = fingerprint(data)
    protocol = (root / cfg["protocol"]).resolve()
    output = (root / cfg["output"]).resolve()
    if (
        protocol.exists()
        or output.exists()
        or not all(p.is_relative_to(root / "outputs/experiments") for p in (protocol, output))
    ):
        raise ValueError("Use fresh separate protocol and execution directories")
    protocol.mkdir(parents=True)
    (protocol / "requests").mkdir()
    write_json(
        protocol / "manifest.json", {**data, "identity": identity, "production_change": False}
    )
    for row in imported:
        row["experiment_identity"] = identity
    for name, records in (
        ("imported_original_rows.jsonl", originals),
        ("imported_rows.jsonl", imported),
    ):
        (protocol / name).write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8"
        )
    calls = [
        json.loads(line)
        for line in (old_dir / "model_calls.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    reused_calls = [c for c in calls if c["phase"]["module"] in modules]
    (protocol / "imported_model_calls.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in reused_calls), encoding="utf-8"
    )
    selected = [q for q in queries if q["module"] == "vision"]
    units = [u for u in corpus["units"] if u["module"] == "vision"]
    for method in METHODS:
        contract = {
            "method": method,
            "module": "vision",
            "corpus_sha256": corpus["corpus_sha256"],
            "documents": [
                {"source_id": u["source_id"], "text_sha256": fingerprint(u["evidence_text"])}
                for u in units
            ],
            "config": settings,
            "environment": environments[method],
            "worker_sha256": data["worker_sha256"],
            "contract_sha256": data["contract_sha256"],
        }
        request = {
            "method": method,
            "config": settings,
            "corpus": str(shared / "corpus.json"),
            "corpus_file_sha256": file_hash(shared / "corpus.json"),
            "corpus_sha256": corpus["corpus_sha256"],
            "workspace": str(output / "indexes" / method),
            "top_k": 10,
            "queries": selected,
            "experiment_identity": identity,
            "index_contracts": {"vision": contract},
            "worker_sha256": data["worker_sha256"],
            "contract_sha256": data["contract_sha256"],
        }
        request["request_identity"] = fingerprint(request)
        verify_request(request, method)
        write_json(protocol / "requests" / f"{method}-vision.json", request)
    write_json(
        protocol / "summary.json",
        {
            "identity": identity,
            "status": "prepared_not_executed",
            "imported_query_results": len(imported),
            "imported_actual_model_calls": len(reused_calls),
            "planned_new_query_results": 24,
            "planned_new_native_indexes": 2,
            "actual_new_model_calls": 0,
        },
    )
    for path in (worker, contract_source, Path(__file__)):
        (protocol / path.name).write_bytes(path.read_bytes())
    if verify_files(shared) != shared_pins:
        raise ValueError("Shared88 inputs changed during graph preparation")
    write_json(
        protocol / "artifacts.json",
        {
            p.relative_to(protocol).as_posix(): file_hash(p)
            for p in protocol.rglob("*")
            if p.is_file()
        },
    )
    return read(protocol / "summary.json")


def execute(root, protocol, resume=False):
    root, protocol = Path(root).resolve(), Path(protocol).resolve()
    pins = verify_files(protocol)
    manifest = read(protocol / "manifest.json")
    if (
        fingerprint(
            {k: v for k, v in manifest.items() if k not in {"identity", "production_change"}}
        )
        != manifest["identity"]
    ):
        raise ValueError("Graph protocol identity changed")
    if file_hash(__file__) != manifest["runner_sha256"]:
        raise ValueError("Prepared graph runner source changed")
    config = manifest["config"]
    verify_runtime(config)
    shared = root / config["preparation_dir"]
    if file_hash(shared / "artifacts.json") != manifest["shared_artifacts_sha256"]:
        raise ValueError("Reviewed shared input inventory changed")
    verify_files(shared)
    corpus, queries = [read(shared / name) for name in ("corpus.json", "queries.json")]
    output = root / config["output"]
    if output.exists():
        if not resume or read(output / "manifest.json") != manifest:
            raise ValueError("Resume requires the exact same native graph protocol")
    else:
        output.mkdir(parents=True)
        for name in ("responses", "logs", "indexes"):
            (output / name).mkdir()
        for name in ("manifest.json", "imported_rows.jsonl", "imported_model_calls.jsonl"):
            shutil.copyfile(protocol / name, output / name)
    lock = output / ".run.lock"
    with lock.open("x", encoding="ascii") as stream:
        stream.write(str(os.getpid()))
    worker = root / "src/occupational_fitness_rag/evaluation/graph_worker.py"
    try:
        with AuditProxy(config, output) as proxy:
            for method in METHODS:
                request_path = protocol / "requests" / f"{method}-vision.json"
                response_path = output / "responses" / f"{method}-vision.json"
                request = read(request_path)
                selected = request["queries"]
                prior = read(response_path) if response_path.exists() else []
                done = validate_records(
                    prior, selected, method, corpus["units"], manifest["identity"]
                )
                workspace = output / "indexes" / method
                if len(done) == len(selected):
                    if any(r["status"] == "completed" for r in prior):
                        verify_index(
                            workspace / "vision", method, request["index_contracts"]["vision"]
                        )
                    continue
                proxy.job = workspace
                started, failure = perf_counter(), None
                print(
                    f"Starting real {method}/vision: {len(request['index_contracts']['vision']['documents'])} originals",
                    flush=True,
                )
                try:
                    with (output / "logs" / f"{method}-vision.log").open(
                        "a", encoding="utf-8"
                    ) as log:
                        subprocess.run(
                            [
                                str(root / f".runtime/{method}/Scripts/python.exe"),
                                "-X",
                                "utf8",
                                str(worker),
                                "--method",
                                method,
                                "--request",
                                str(request_path),
                                "--response",
                                str(response_path),
                            ],
                            stdout=log,
                            stderr=log,
                            check=True,
                            timeout=config["worker_timeout_seconds"],
                        )
                except Exception as exc:
                    failure = f"{type(exc).__name__}: {exc}"
                records = read(response_path) if response_path.exists() else []
                done = validate_records(
                    records, selected, method, corpus["units"], manifest["identity"]
                )
                for q in selected:
                    if q["query_id"] not in done:
                        records.append(
                            {
                                **q,
                                "method": method,
                                "experiment_identity": manifest["identity"],
                                "query_sha256": q["query_audit"]["query_sha256"],
                                "status": "worker_failed",
                                "source_ids": [],
                                "error": failure
                                or "Native worker returned an incomplete inventory",
                            }
                        )
                validate_records(records, selected, method, corpus["units"], manifest["identity"])
                write_json(response_path, records)
                write_json(
                    output / "logs" / f"{method}-execution.json",
                    {"seconds": perf_counter() - started, "error": failure},
                )
                print(
                    f"Finished {method}/vision: {dict(Counter(r['status'] for r in records))}",
                    flush=True,
                )
        rows = [
            json.loads(line)
            for line in (protocol / "imported_rows.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        for method in METHODS:
            rows.extend(read(output / "responses" / f"{method}-vision.json"))
            validate_records(
                [r for r in rows if r["method"] == method],
                queries,
                method,
                corpus["units"],
                manifest["identity"],
            )
        (output / "results.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False, allow_nan=False) + "\n" for r in rows),
            encoding="utf-8",
        )
        call_path = output / "model_calls.jsonl"
        calls = (
            [json.loads(line) for line in call_path.read_text(encoding="utf-8").splitlines()]
            if call_path.exists()
            else []
        )
        summary = {
            "identity": manifest["identity"],
            "planned": 154,
            "recorded": len(rows),
            "status_counts": dict(Counter(r["status"] for r in rows)),
            "actual_new_model_calls": sum(c.get("provider_called", True) for c in calls),
            "imported_actual_model_calls": read(protocol / "summary.json")[
                "imported_actual_model_calls"
            ],
            "imported_query_results": 130,
            "new_query_results": 24,
            "new_native_index_count": len(
                list((output / "indexes").glob("*/vision/index_manifest.json"))
            ),
            "reused_native_index_count": 8,
            "failed_new_calls": sum(c["status"] != "completed" for c in calls),
            "production_change": False,
            "judgment_calls": 0,
        }
        write_json(output / "summary.json", summary)
        if verify_files(protocol) != pins:
            raise ValueError("Frozen graph replay protocol changed")
        verify_runtime(config)
        write_json(
            output / "artifacts.json",
            {
                p.relative_to(output).as_posix(): file_hash(p)
                for p in output.rglob("*")
                if p.is_file()
                and p.name != ".run.lock"
                and "indexes" not in p.relative_to(output).parts
            },
        )
        return summary
    finally:
        lock.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/experiments/scope88_external_graph_v1.yaml")
    parser.add_argument("--execute", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            execute(Path.cwd(), args.execute, args.resume)
            if args.execute
            else prepare(Path.cwd(), args.config),
            indent=2,
        )
    )
