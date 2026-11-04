"""Freeze no-MMR wider-pool and original-coverage guard ablations.

All search channels reconstruct from historical real embedding responses.
Reference labels are not loaded here; production and historical runs are kept.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter

import yaml

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.evaluation.guarded_hybrid import rank_channels
from occupational_fitness_rag.evaluation.passage_comparison import read_records
from occupational_fitness_rag.provenance import digest, write_json
from tools.run_anchored_hybrid import reconstruct_channels, verify_saved
from tools.run_planned_hybrid import load_inputs

SOURCES = (
    "tools/run_guarded_hybrid.py",
    "src/occupational_fitness_rag/evaluation/guarded_hybrid.py",
    "src/occupational_fitness_rag/evaluation/anchored_hybrid.py",
    "tools/run_anchored_hybrid.py",
    "tools/run_planned_hybrid.py",
    "src/occupational_fitness_rag/evaluation/planned_hybrid.py",
    "src/occupational_fitness_rag/retrieval/bm25.py",
    "src/occupational_fitness_rag/provenance.py",
)


def freeze_rankings(config, corpus, queries, channels, identity):
    """Return all independent predefined rankings, preserving failed attempts."""
    units = {u["source_id"]: u for u in corpus["units"]}
    rows = []
    for query in queries:
        for variant in config["variants"]:
            started = perf_counter()
            row = {
                "query_id": query["query_id"],
                "case_id": query["case_id"],
                "module": query["module"],
                "method": variant["method"],
                "query_sha256": query["query_audit"]["query_sha256"],
                "experiment_identity": identity,
            }
            try:
                result = rank_channels(
                    channels[query["query_id"]],
                    units,
                    {k: v for k, v in variant.items() if k != "method"},
                )
                ids = result["source_ids"]
                if (
                    not ids
                    or len(ids) > 10
                    or len(ids) != len(set(ids))
                    or any(units[s]["module"] != query["module"] for s in ids)
                ):
                    raise ValueError("Empty, repeated, oversized or cross-module original evidence")
                row.update(
                    status="completed",
                    source_ids=ids,
                    ranked_sources=result["ranked_sources"],
                    diagnostics=result["diagnostics"],
                    original_text_hashes={s: units[s]["text_sha256"] for s in ids},
                )
            except Exception as exc:
                row.update(status="failed", source_ids=[], error=f"{type(exc).__name__}: {exc}")
            row["ranking_seconds_excluding_import_reconstruction"] = perf_counter() - started
            rows.append(row)
    return rows


def run(config_path):
    root = Path(__file__).resolve().parents[1]
    config_path = Path(config_path)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    parent_dir = (root / config["imported_dir"]).resolve()
    parent, pins = verify_saved(parent_dir)
    if parent["identity"] != config["expected_imported_identity"]:
        raise ValueError("Unexpected immutable search-channel parent")
    corpus, queries, patients, vectors, anchors, imports = load_inputs(root, parent["config"])
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
    names = [v["method"] for v in config["variants"]]
    if not names or len(names) != len(set(names)) or config["primary_candidate"] not in names:
        raise ValueError("All predefined unique variants and the primary candidate are required")
    source_pins = {name: file_hash(root / name) for name in SOURCES}
    data = {
        "kind": "no_mmr_wide_pool_original_coverage_guard_ablation",
        "config": config,
        "parent_identity": parent["identity"],
        "parent_artifacts_sha256": file_hash(parent_dir / "artifacts.json"),
        "original_inputs": imports,
        "sources": source_pins,
        "python": sys.version,
        "query_ids": [q["query_id"] for q in queries],
        "labels_available_to_ranker": False,
    }
    identity = digest(data)
    output = (root / config["output"]).resolve()
    if not output.is_relative_to(root / "outputs/experiments") or output.exists():
        raise ValueError("Use a fresh experiment directory; preserve prior versions")
    output.mkdir(parents=True)
    write_json(output / "manifest.json", {**data, "identity": identity, "production_change": False})
    write_json(output / "corpus.json", corpus)
    write_json(output / "queries.json", queries)
    (output / "config.yaml").write_bytes(config_path.read_bytes())
    for index, name in enumerate(SOURCES):
        (output / (f"source_{index}_" + Path(name).name)).write_bytes((root / name).read_bytes())
    rows = freeze_rankings(config, corpus, queries, channels, identity)
    if (
        verify_saved(parent_dir)[1] != pins
        or load_inputs(root, parent["config"])[-1] != imports
        or {n: file_hash(root / n) for n in SOURCES} != source_pins
    ):
        raise ValueError("Frozen parent, original inputs or ranking implementation changed")
    (output / "results.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    write_json(output / "channels.json", channels)
    guarded = [r for r in rows if r.get("diagnostics", {}).get("guard_enabled")]
    summary = {
        "identity": identity,
        "planned": len(queries) * len(names),
        "recorded": len(rows),
        "completed": sum(r["status"] == "completed" for r in rows),
        "failed": sum(r["status"] != "completed" for r in rows),
        "actual_new_model_calls": 0,
        "reused_shared_embedding_calls": imports["baseline_audit"]["embedding_calls"],
        "reused_facet_embedding_calls": len(read_records(parent_dir / "model_calls.jsonl")),
        "guarded_rankings": len(guarded),
        "guard_violations": sum(
            not r["diagnostics"]["protected_coverage_retained"] for r in guarded
        ),
        "guard_fallbacks": sum(
            r["diagnostics"]["guard_fallback_reason"] is not None for r in guarded
        ),
        "labels_loaded": False,
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
