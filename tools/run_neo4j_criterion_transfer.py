"""Freeze two typed-criterion transfer hypotheses using actual native Neo4j hits."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from time import perf_counter

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.evaluation.neo4j_criterion_transfer import VARIANTS, transfer
from occupational_fitness_rag.provenance import digest, write_json
from tools.run_neo4j_strategies import verify_bundle

SOURCES = (
    "tools/run_neo4j_criterion_transfer.py",
    "src/occupational_fitness_rag/evaluation/neo4j_criterion_transfer.py",
    "src/occupational_fitness_rag/evaluation/prefix_allocation.py",
    "src/occupational_fitness_rag/evaluation/guarded_hybrid.py",
    "configs/experiments/neo4j_criterion_transfer_v3.json",
)


def read(path):
    return json.loads(Path(path).read_bytes())


def records(path):
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def run(config_path):
    root = Path(__file__).resolve().parents[1]
    config_path = Path(config_path).resolve()
    config = read(config_path)
    if (
        tuple(config["variants"]) != VARIANTS
        or config["reference_labels_available_to_ranker"] is not False
    ):
        raise ValueError("Use the two fixed global transfer hypotheses")
    parent, output = [(root / config[k]).resolve() for k in ("input_run", "output")]
    if output.exists() or not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Use a new transfer experiment directory")
    pins = verify_bundle(parent)
    manifest = read(parent / "manifest.json")
    if manifest["identity"] != config["expected_input_identity"]:
        raise ValueError("Actual native parent identity differs")
    corpus, queries = [read(parent / name) for name in ("corpus.json", "queries.json")]
    units = {u["source_id"]: u for u in corpus["units"]}
    baselines = {
        r["query_id"]: r
        for r in records(parent / "results.jsonl")
        if r["method"] == config["baseline_method"]
    }
    traces = {r["query_id"]: r for r in records(parent / "native_queries.jsonl")}
    if (
        len(units) != 88
        or len(baselines) != 77
        or set(baselines) != set(traces)
        or set(traces) != {q["query_id"] for q in queries}
    ):
        raise ValueError("Actual reviewed native source or query inventory differs")
    sources = {n: file_hash(root / n) for n in SOURCES}
    data = {
        "kind": "actual_native_neo4j_frontier_criterion_transfer",
        "config": config,
        "parent_identity": manifest["identity"],
        "parent_artifacts_sha256": file_hash(parent / "artifacts.json"),
        "corpus_sha256": corpus["corpus_sha256"],
        "sources": sources,
        "reference_labels_available_to_ranker": False,
        "new_native_calls": 0,
        "new_model_calls": 0,
    }
    identity = digest(data)
    output.mkdir(parents=True)
    write_json(output / "manifest.json", {**data, "identity": identity, "production_change": False})
    for name, value in (
        ("corpus.json", corpus),
        ("queries.json", queries),
        ("config.json", config),
    ):
        write_json(output / name, value)
    for i, source in enumerate(SOURCES):
        shutil.copyfile(root / source, output / (f"source_{i}_" + Path(source).name))
    rows = []
    for query in queries:
        for variant in VARIANTS:
            started = perf_counter()
            row = {k: query[k] for k in ("query_id", "case_id", "module")}
            row.update(
                method=variant,
                experiment_identity=identity,
                parent_ranking_sha256=digest(baselines[query["query_id"]]),
            )
            try:
                result = transfer(
                    variant, baselines[query["query_id"]], traces[query["query_id"]], units
                )
                row.update(
                    status="completed",
                    **result,
                    original_text_hashes={s: units[s]["text_sha256"] for s in result["source_ids"]},
                )
            except Exception as exc:
                row.update(status="failed", source_ids=[], error=f"{type(exc).__name__}: {exc}")
            row["ranking_seconds"] = perf_counter() - started
            rows.append(row)
    if verify_bundle(parent) != pins or sources != {n: file_hash(root / n) for n in SOURCES}:
        raise ValueError("Frozen native responses or source code changed")
    (output / "results.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False, allow_nan=False) + "\n" for r in rows),
        encoding="utf-8",
    )
    summary = {
        "identity": identity,
        "planned": len(queries) * len(VARIANTS),
        "recorded": len(rows),
        "completed": sum(r["status"] == "completed" for r in rows),
        "failed": sum(r["status"] == "failed" for r in rows),
        "new_native_calls": 0,
        "new_model_calls": 0,
        "actual_native_query_responses_reused": len(traces),
        "original_query_sources_invented": False,
        "production_change": False,
    }
    write_json(output / "summary.json", summary)
    write_json(
        output / "artifacts.json", {p.name: file_hash(p) for p in output.iterdir() if p.is_file()}
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path("configs/experiments/neo4j_criterion_transfer_v3.json")
    )
    print(json.dumps(run(parser.parse_args().config)))
