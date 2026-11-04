"""Run native FlagEmbedding reranking over frozen original RRF candidates.

Docling parsing is audited separately so that a parser change cannot silently
change the shared retrieval corpus. This worker never loads patient labels.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
from time import perf_counter

METHOD = "flag_embedding_rerank"


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def save(path, value):
    Path(path).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def validate(job):
    if set(job) != {"experiment_identity", "corpus", "queries", "candidates", "config"}:
        raise ValueError("Unexpected input fields; reference answers are not accepted")
    units = {u["source_id"]: u for u in job["corpus"]["units"]}
    if len(units) != len(job["corpus"]["units"]):
        raise ValueError("Duplicate original evidence")

    def reject_labels(value):
        if isinstance(value, dict):
            if {
                "reference_source_ids",
                "reference_outcome",
                "reference_payload",
                "expected_sources",
                "expected_source_ids",
            } & set(value):
                raise ValueError("Reference labels are not valid query inputs")
            for child in value.values():
                reject_labels(child)
        elif isinstance(value, list):
            for child in value:
                reject_labels(child)

    qids = set()
    for query in job["queries"]:
        reject_labels(query)
        qid = query["query_id"]
        if qid in qids or query["licence_context"] != "commercial":
            raise ValueError("Repeated query or incompatible licence scope")
        qids.add(qid)
        ids = job["candidates"][qid]
        if not ids or len(ids) > 20 or len(ids) != len(set(ids)):
            raise ValueError("Provide at most twenty distinct original RRF candidates")
        for sid in ids:
            unit = units[sid]
            if unit["module"] != query["module"] or unit["licence_context"] not in {
                "commercial",
                "shared",
            }:
                raise ValueError("Candidate outside frozen commercial module")
            if hashlib.sha256(unit["evidence_text"].encode()).hexdigest() != unit["text_sha256"]:
                raise ValueError("Original text fingerprint differs")
    if set(job["candidates"]) != qids or not qids:
        raise ValueError("Candidate query inventory differs")
    return units


def validate_cached_rows(rows, job, identity):
    planned = {q["query_id"]: q for q in job["queries"]}
    if len({r["query_id"] for r in rows}) != len(rows):
        raise ValueError("Repeated saved native ranking")
    for row in rows:
        query = planned.get(row["query_id"])
        ids = row.get("source_ids", [])
        if (
            query is None
            or row["experiment_identity"] != identity
            or row["method"] != METHOD
            or row["case_id"] != query["case_id"]
            or row["module"] != query["module"]
            or row["status"] not in {"completed", "failed"}
        ):
            raise ValueError("Saved native ranking identity or scope differs")
        if row["status"] == "completed":
            if (
                not ids
                or len(ids) > 10
                or len(ids) != len(set(ids))
                or not set(ids) <= set(job["candidates"][row["query_id"]])
            ):
                raise ValueError("Saved completed ranking has invalid original candidates")
            scores = row["ranked_sources"]
            if [r["source_id"] for r in scores] != ids or any(
                not 0 <= r["score"] <= 1 for r in scores
            ):
                raise ValueError("Saved native scores differ from returned originals")
        elif ids:
            raise ValueError("Failed ranking cannot return substitute evidence")


def run(input_path, output, resume=False):
    job = json.loads(input_path.read_bytes())
    units = validate(job)
    config = job["config"]
    receipt_path = Path(config["checkpoint_receipt"])
    receipt = json.loads(receipt_path.read_bytes())
    if receipt["revision"] != config["checkpoint_revision"] or not receipt["completed"]:
        raise ValueError("Checkpoint revision differs")
    model_dir = Path(receipt["local_dir"])
    for name, expected in receipt["files"].items():
        if sha(model_dir / name) != expected:
            raise ValueError("Downloaded checkpoint changed: " + name)
    versions = {name: importlib.metadata.version(name) for name in config["expected_versions"]}
    if versions != config["expected_versions"]:
        raise ValueError("Native package version differs")
    data = {
        "kind": "native_flag_embedding_rerank",
        "input_sha256": sha(input_path),
        "parent_identity": job["experiment_identity"],
        "config": config,
        "checkpoint_receipt_sha256": sha(receipt_path),
        "versions": versions,
        "source_sha256": sha(__file__),
        "labels_loaded": False,
    }
    manifest = {**data, "identity": digest(data), "production_change": False}
    if output.exists():
        if not resume or json.loads((output / "manifest.json").read_bytes()) != manifest:
            raise ValueError("Resume requires identical frozen native inputs")
    else:
        output.mkdir(parents=True)
        save(output / "manifest.json", manifest)
        (output / "worker_source.py").write_bytes(Path(__file__).read_bytes())
    results_path = output / "results.jsonl"
    rows = (
        [json.loads(line) for line in results_path.read_text(encoding="utf-8").splitlines()]
        if results_path.exists()
        else []
    )
    validate_cached_rows(rows, job, manifest["identity"])
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    import torch
    from FlagEmbedding import FlagReranker

    torch.set_num_threads(config["threads"])
    start = perf_counter()
    model = FlagReranker(
        str(model_dir),
        devices=[config.get("device", "cpu")],
        use_fp16=config.get("use_fp16", False),
        trust_remote_code=False,
        max_length=config["max_length"],
        batch_size=config["batch_size"],
    )
    load_seconds = perf_counter() - start
    done = {r["query_id"] for r in rows}
    for query in job["queries"]:
        if query["query_id"] in done:
            continue
        ids = job["candidates"][query["query_id"]]
        pairs = [(query["query"], units[sid]["evidence_text"]) for sid in ids]
        row = {k: query[k] for k in ("query_id", "case_id", "module")}
        row.update(method=METHOD, experiment_identity=manifest["identity"])
        row["native_scoring_attempted"] = False
        start = perf_counter()
        try:
            token_lengths = [
                len(
                    model.tokenizer(q, text, add_special_tokens=True, truncation=False)["input_ids"]
                )
                for q, text in pairs
            ]
            row["native_scoring_attempted"] = True
            raw = model.compute_score(
                pairs,
                normalize=True,
                max_length=config["max_length"],
                batch_size=config["batch_size"],
            )
            scores = [float(raw)] if isinstance(raw, (float, int)) else [float(v) for v in raw]
            if len(scores) != len(ids) or any(not 0 <= score <= 1 for score in scores):
                raise ValueError("Native reranker returned invalid scores")
            ranking = sorted(range(len(ids)), key=lambda index: (-scores[index], index))
            row.update(
                status="completed",
                source_ids=[ids[i] for i in ranking[:10]],
                ranked_sources=[
                    {"source_id": ids[i], "score": scores[i], "original_rrf_rank": i + 1}
                    for i in ranking[:10]
                ],
                candidate_trace=[
                    {
                        "source_id": sid,
                        "native_score": scores[i],
                        "pair_tokens": token_lengths[i],
                        "scorer_input_truncated": token_lengths[i] > config["max_length"],
                    }
                    for i, sid in enumerate(ids)
                ],
                scorer_input_max_tokens=config["max_length"],
                returned_source_text_modified=False,
            )
        except Exception as exc:
            row.update(status="failed", source_ids=[], error=f"{type(exc).__name__}: {exc}")
        row["seconds"] = perf_counter() - start
        with results_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        rows.append(row)
        print(f"FlagEmbedding {len(rows)}/{len(job['queries'])} {row['status']}", flush=True)
    if sha(input_path) != data["input_sha256"] or sha(__file__) != data["source_sha256"]:
        raise ValueError("Native worker inputs changed during execution")
    summary = {
        "identity": manifest["identity"],
        "planned": len(job["queries"]),
        "recorded": len(rows),
        "completed": sum(r["status"] == "completed" for r in rows),
        "failed": sum(r["status"] != "completed" for r in rows),
        "native_scoring_calls": sum(r["native_scoring_attempted"] for r in rows),
        "model_load_seconds": load_seconds,
        "ollama_calls": 0,
        "scorer_truncated_pairs": sum(
            c["scorer_input_truncated"] for r in rows for c in r.get("candidate_trace", [])
        ),
        "production_change": False,
        "docling_changes_applied_to_corpus": False,
    }
    save(output / "summary.json", summary)
    save(
        output / "artifacts.json",
        {p.name: sha(p) for p in output.iterdir() if p.is_file() and p.name != "artifacts.json"},
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.input, args.output, args.resume), indent=2))
