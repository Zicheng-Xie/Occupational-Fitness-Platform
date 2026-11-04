"""Freeze criterion-prefix allocation on rebuilt 88-source search channels."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter

import yaml

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.evaluation.guarded_hybrid import rank_channels
from occupational_fitness_rag.evaluation.prefix_allocation import allocate_prefix
from occupational_fitness_rag.provenance import digest, write_json

BASELINE_METHOD = "scope88_guarded_v3"
VARIANTS = {
    "scope88_prefix_full_source_control": "full_source_floor",
    "scope88_prefix_criterion_v6": "criterion_floor",
}
GUARDED_CONFIG = {
    "policy": "guarded_coverage",
    "anchor_weight": 0.75,
    "coverage_weight": 0.15,
    "rrf_k": 60,
    "candidate_k": 30,
    "sensitivity_k": 10,
}
SOURCES = (
    "tools/run_scope88_prefix_allocation.py",
    "src/occupational_fitness_rag/evaluation/prefix_allocation.py",
    "src/occupational_fitness_rag/evaluation/guarded_hybrid.py",
    "src/occupational_fitness_rag/evaluation/anchored_hybrid.py",
    "src/occupational_fitness_rag/evaluation/planned_hybrid.py",
    "src/occupational_fitness_rag/provenance.py",
)


def read_json(path):
    return json.loads(Path(path).read_bytes())


def verify(directory):
    directory = Path(directory).resolve()
    pins = read_json(directory / "artifacts.json")
    if not pins:
        raise ValueError("Empty shared-input artifact inventory")
    for name, expected in pins.items():
        source = (directory / name).resolve()
        if not source.is_relative_to(directory) or file_hash(source) != expected:
            raise ValueError("Changed or unsafe frozen input: " + name)
    manifest = read_json(directory / "manifest.json")
    if (
        digest({k: v for k, v in manifest.items() if k not in {"identity", "production_change"}})
        != manifest["identity"]
    ):
        raise ValueError("Shared-input identity differs")
    return manifest, pins


def validate_config(config):
    if set(config) != {
        "shared_inputs",
        "expected_shared_identity",
        "output",
        "primary_candidate",
        "variants",
    }:
        raise ValueError("Unexpected prefix-allocation configuration")
    if (
        config["primary_candidate"] != "scope88_prefix_criterion_v6"
        or config["variants"] != VARIANTS
    ):
        raise ValueError("Use the two predefined prefix hypotheses")


def freeze_rows(corpus, queries, channels, identity):
    units = {u["source_id"]: u for u in corpus["units"]}
    if len(units) != len(corpus["units"]) or set(channels) != {q["query_id"] for q in queries}:
        raise ValueError("Shared corpus or query-channel inventory differs")
    rows = []
    for query in queries:
        started = perf_counter()
        baseline = {
            **{k: query[k] for k in ("query_id", "case_id", "module")},
            "method": BASELINE_METHOD,
            "experiment_identity": identity,
            "query_sha256": query["query_audit"]["query_sha256"],
        }
        try:
            ranked = rank_channels(channels[query["query_id"]], units, GUARDED_CONFIG)
            baseline.update(status="completed", **ranked)
        except Exception as exc:
            baseline.update(status="failed", source_ids=[], error=f"{type(exc).__name__}: {exc}")
        baseline["ranking_seconds"] = perf_counter() - started
        baseline["original_text_hashes"] = {
            sid: units[sid]["text_sha256"] for sid in baseline["source_ids"]
        }
        rows.append(baseline)
        for method, policy in VARIANTS.items():
            started = perf_counter()
            row = {
                k: v
                for k, v in baseline.items()
                if k
                not in {
                    "source_ids",
                    "ranked_sources",
                    "diagnostics",
                    "error",
                    "original_text_hashes",
                }
            }
            row["method"] = method
            row["parent_actual_ranking_sha256"] = digest(baseline)
            try:
                result = allocate_prefix(baseline, units, policy)
                if set(result["source_ids"]) != set(baseline["source_ids"]):
                    raise ValueError("Prefix output changed its actual original inventory")
                row.update(status="completed", **result)
            except Exception as exc:
                row.update(status="failed", source_ids=[], error=f"{type(exc).__name__}: {exc}")
            row["ranking_seconds"] = perf_counter() - started
            row["original_text_hashes"] = {
                sid: units[sid]["text_sha256"] for sid in row["source_ids"]
            }
            rows.append(row)
    return rows


def run(config_path):
    root = Path(__file__).resolve().parents[1]
    config_path = Path(config_path).resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    validate_config(config)
    shared = (root / config["shared_inputs"]).resolve()
    parent, pins = verify(shared)
    if (
        parent["identity"] != config["expected_shared_identity"]
        or parent["actual_new_model_calls"] != 0
    ):
        raise ValueError("Unexpected audited shared-input identity")
    corpus, queries, patients, channels = [
        read_json(shared / name)
        for name in ("corpus.json", "queries.json", "patients.json", "channels.json")
    ]
    if len(corpus["units"]) != 88 or len(queries) != 77 or len(patients) != 33:
        raise ValueError("Expected the reviewed 88-source, 77-query, 33-case inputs")
    if any(q["corpus_sha256"] != corpus["corpus_sha256"] for q in queries):
        raise ValueError("Queries are not rebound to the actual reviewed corpus")
    source_pins = {name: file_hash(root / name) for name in SOURCES}
    data = {
        "kind": "reviewed_scope_exact_criterion_prefix_allocation",
        "config": config,
        "guarded_v3_config": GUARDED_CONFIG,
        "shared_identity": parent["identity"],
        "shared_artifacts_sha256": file_hash(shared / "artifacts.json"),
        "corpus_sha256": corpus["corpus_sha256"],
        "queries_sha256": file_hash(shared / "queries.json"),
        "sources": source_pins,
        "python": sys.version,
        "labels_loaded": False,
        "actual_new_model_calls": 0,
        "hypothesis_scope": "Observed development allocation; corpus criterion metadata is not patient predicate entailment",
    }
    identity = digest(data)
    output = (root / config["output"]).resolve()
    if output.exists() or not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Use a fresh isolated experiment output directory")
    output.mkdir(parents=True)
    write_json(output / "manifest.json", {**data, "identity": identity, "production_change": False})
    for name, value in (
        ("corpus.json", corpus),
        ("queries.json", queries),
        ("patients.json", patients),
    ):
        write_json(output / name, value)
    (output / "config.yaml").write_bytes(config_path.read_bytes())
    for index, name in enumerate(SOURCES):
        (output / f"source_{index}_{Path(name).name}").write_bytes((root / name).read_bytes())
    rows = freeze_rows(corpus, queries, channels, identity)
    if verify(shared)[1] != pins or {n: file_hash(root / n) for n in SOURCES} != source_pins:
        raise ValueError("Frozen input or implementation changed during allocation")
    (output / "results.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    revised = [r for r in rows if r["method"] != BASELINE_METHOD and r["status"] == "completed"]
    summary = {
        "identity": identity,
        "planned": len(queries) * 3,
        "recorded": len(rows),
        "completed": sum(r["status"] == "completed" for r in rows),
        "failed": sum(r["status"] == "failed" for r in rows),
        "top10_inventory_changes": sum(
            not r["diagnostics"]["top10_source_inventory_unchanged"] for r in revised
        ),
        "criterion_floor_violations": sum(
            not r["diagnostics"]["criterion_floor_retained"] for r in revised
        ),
        "labels_loaded": False,
        "actual_new_model_calls": 0,
        "production_change": False,
    }
    write_json(output / "summary.json", summary)
    write_json(
        output / "artifacts.json",
        {
            p.name: file_hash(p)
            for p in output.iterdir()
            if p.is_file() and p.name != "artifacts.json"
        },
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    print(json.dumps(run(parser.parse_args().config), indent=2))
