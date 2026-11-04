"""Freeze label-free no-MMR fusion ablations using retained real search channels.

No model transport or reference-label loader is available to this runner. Each
imported channel is reconstructed from the original audited embedding responses
before any new ranking is produced. Production and the six baseline arms remain
unchanged.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter

import yaml

from occupational_fitness_rag.evaluation.anchored_hybrid import rank_channels
from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.evaluation.passage_comparison import read_records
from occupational_fitness_rag.evaluation.planned_hybrid import execute_plan
from occupational_fitness_rag.provenance import digest, write_json
from tools.run_planned_hybrid import load_inputs

SOURCES = (
    "tools/run_anchored_hybrid.py",
    "src/occupational_fitness_rag/evaluation/anchored_hybrid.py",
    "tools/run_planned_hybrid.py",
    "src/occupational_fitness_rag/evaluation/planned_hybrid.py",
    "src/occupational_fitness_rag/retrieval/bm25.py",
    "src/occupational_fitness_rag/provenance.py",
)


def verify_saved(directory):
    """Verify an immutable experiment, rejecting a changed manifest or trace."""
    pins = json.loads((directory / "artifacts.json").read_bytes())
    for name, expected in pins.items():
        target = (directory / name).resolve()
        if not target.is_relative_to(directory.resolve()) or file_hash(target) != expected:
            raise ValueError("Imported artifact changed: " + name)
    manifest = json.loads((directory / "manifest.json").read_bytes())
    data = {k: v for k, v in manifest.items() if k not in {"identity", "production_change"}}
    if digest(data) != manifest["identity"]:
        raise ValueError("Imported experiment self-identity differs")
    return manifest, pins


def reconstruct_channels(directory, manifest, rows, corpus, queries, patients, vectors, anchors):
    """Reject cached rankings or vectors that cannot be tied to actual calls."""
    config = manifest["config"]
    calls = read_records(directory / "model_calls.jsonl")
    by_query = {r["query_id"]: r for r in rows}
    if len(by_query) != len(rows) or set(by_query) != {q["query_id"] for q in queries}:
        raise ValueError("Imported query inventory is incomplete or repeated")
    rebuilt = {}
    for query in queries:
        qid = query["query_id"]
        row = by_query[qid]
        if (
            row["experiment_identity"] != manifest["identity"]
            or row["status"] != "completed"
            or row["case_id"] != query["case_id"]
            or row["module"] != query["module"]
            or row["query_sha256"] != query["query_audit"]["query_sha256"]
        ):
            raise ValueError("Imported query identity, status or scope differs")

        def embed(texts):
            body = {"model": config["embedding_model"], "input": texts, "truncate": False}
            cache = json.loads(
                (directory / "query_records" / (qid + ".embedding.json")).read_bytes()
            )
            observed = [
                c
                for c in calls
                if c["query_id"] == qid
                and c["status"] == "completed"
                and c["request_sha256"] == digest(body)
                and c["request"] == body
            ]
            if (
                cache["key"] != digest({"identity": manifest["identity"], "request": body})
                or not observed
                or observed[-1]["raw_response"]["embeddings"] != cache["vectors"]
            ):
                raise ValueError("Facet cache differs from its actual recorded request/response")
            return cache["vectors"]

        result = execute_plan(
            query, patients[query["case_id"]], corpus, vectors, anchors[qid], embed, config
        )
        if any(row.get(k) != v for k, v in result.items()):
            raise ValueError("Imported channel ranking cannot reconstruct: " + qid)
        events = result["events"]
        channels = next(e["channels"] for e in events if e["stage"] == "search")
        followups = next(e["keyword_only_followups"] for e in events if e["stage"] == "refine")
        # The v1 in-memory search event shares the list later extended by
        # refinement. Its serialized channels therefore already contain these
        # follow-ups. Import each identical observed channel once, never twice.
        merged = {c["channel"]: c for c in channels}
        if len(merged) != len(channels):
            raise ValueError("Parent search event repeats a channel identity")
        for channel in followups:
            name = channel["channel"]
            if name in merged and merged[name] != channel:
                raise ValueError("Refinement channel conflicts with its search event")
            merged[name] = channel
        rebuilt[qid] = list(merged.values())
    return rebuilt


def run(config_path):
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    imported_dir = (root / config["imported_dir"]).resolve()
    manifest, pins = verify_saved(imported_dir)
    if manifest["identity"] != config["expected_imported_identity"]:
        raise ValueError("Unexpected no-MMR parent experiment")
    corpus, queries, patients, vectors, anchors, original_imports = load_inputs(
        root, manifest["config"]
    )
    old_rows = read_records(imported_dir / "results.jsonl")
    channels = reconstruct_channels(
        imported_dir, manifest, old_rows, corpus, queries, patients, vectors, anchors
    )
    variants = config["variants"]
    names = [v["method"] for v in variants]
    if len(names) != len(set(names)) or not names or config["primary_candidate"] not in names:
        raise ValueError("Repeated or missing predefined retrieval variants")
    source_pins = {name: file_hash(root / name) for name in SOURCES}
    data = {
        "kind": "no_mmr_anchored_fusion_ablation",
        "config": config,
        "parent_identity": manifest["identity"],
        "parent_artifacts_sha256": file_hash(imported_dir / "artifacts.json"),
        "original_inputs": original_imports,
        "sources": source_pins,
        "python": sys.version,
        "query_ids": [q["query_id"] for q in queries],
        "labels_available_to_ranker": False,
    }
    identity = digest(data)
    output = (root / config["output"]).resolve()
    if not output.is_relative_to(root / "outputs/experiments") or output.exists():
        raise ValueError("Use a fresh experimental directory; preserve earlier rankings")
    output.mkdir(parents=True)
    write_json(output / "manifest.json", {**data, "identity": identity, "production_change": False})
    write_json(output / "corpus.json", corpus)
    write_json(output / "queries.json", queries)
    (output / "config.yaml").write_bytes(Path(config_path).read_bytes())
    for index, name in enumerate(SOURCES):
        (output / (f"source_{index}_" + Path(name).name)).write_bytes((root / name).read_bytes())
    units = {u["source_id"]: u for u in corpus["units"]}
    rows = []
    for query in queries:
        for variant in variants:
            start = perf_counter()
            row = {
                "query_id": query["query_id"],
                "case_id": query["case_id"],
                "module": query["module"],
                "method": variant["method"],
                "query_sha256": query["query_audit"]["query_sha256"],
                "experiment_identity": identity,
            }
            try:
                policy = {k: v for k, v in variant.items() if k != "method"}
                result = rank_channels(channels[query["query_id"]], units, policy)
                ranked, diagnostics = result["ranked_sources"], result["diagnostics"]
                ids = [r["source_id"] for r in ranked[:10]]
                if not ids or any(units[s]["module"] != query["module"] for s in ids):
                    raise ValueError("Empty or cross-module original evidence")
                row.update(
                    status="completed",
                    source_ids=ids,
                    ranked_sources=ranked[:10],
                    diagnostics=diagnostics,
                    original_text_hashes={s: units[s]["text_sha256"] for s in ids},
                )
            except Exception as exc:
                row.update(status="failed", source_ids=[], error=f"{type(exc).__name__}: {exc}")
            row["ranking_seconds_excluding_import_reconstruction"] = perf_counter() - start
            rows.append(row)
    if (
        verify_saved(imported_dir)[1] != pins
        or load_inputs(root, manifest["config"])[-1] != original_imports
    ):
        raise ValueError("Imported inputs changed during experiment")
    if source_pins != {name: file_hash(root / name) for name in SOURCES}:
        raise ValueError("Ranking implementation changed during experiment")
    (output / "results.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False, allow_nan=False) + "\n" for r in rows),
        encoding="utf-8",
    )
    write_json(output / "channels.json", channels)
    summary = {
        "identity": identity,
        "planned": len(queries) * len(variants),
        "recorded": len(rows),
        "completed": sum(r["status"] == "completed" for r in rows),
        "failed": sum(r["status"] != "completed" for r in rows),
        "actual_new_model_calls": 0,
        "reused_shared_embedding_calls": original_imports["baseline_audit"]["embedding_calls"],
        "reused_facet_embedding_calls": len(read_records(imported_dir / "model_calls.jsonl")),
        "production_change": False,
        "labels_loaded": False,
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
