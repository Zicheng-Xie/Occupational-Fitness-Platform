"""Adaptive PageIndex cardinality ablation using unchanged frozen branch pools.

Only underfilled original-ranking calls are rerun. Full parent answers, branch
navigation, original texts, model options and earlier failed attempts remain
immutable. No source reference labels or replacement retrieval routes are used.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from tools import pageindex_extension_worker as worker
from tools import recover_pageindex_duplicates as recovery

POLICY = "exact_available_original_count_valid_id_dedup_only_v1"


def strict_request(query, mapping, units, config, branches):
    body, field, allowed, excluded = worker.request_body(
        query, mapping, units, config, "originals", branches
    )
    target = min(config["top_k"], len(allowed))
    body["format"]["properties"][field]["minItems"] = target
    body["format"]["properties"][field]["maxItems"] = target
    return body, field, allowed, excluded, target


def parse_strict(raw, body, field, allowed, config):
    """Never fill absent IDs; canonicalize valid duplicates only if complete."""
    value = json.loads(raw["message"]["content"])
    if not isinstance(value, dict) or set(value) != {field}:
        raise ValueError("Strict ranking requires the unchanged native leaf-ID contract")
    ids = value[field]
    if not isinstance(ids, list) or any(not isinstance(n, str) or n not in allowed for n in ids):
        raise ValueError("Strict ranking contains unknown native leaf IDs")
    normalized, removed = [], []
    for index, nid in enumerate(ids):
        if nid in normalized:
            removed.append({"raw_index": index, "native_node_id": nid})
        else:
            normalized.append(nid)
    target = body["format"]["properties"][field]["minItems"]
    if len(normalized) != target:
        raise ValueError("Strict ranking does not contain the required distinct native leaf count")
    validation_copy = deepcopy(raw)
    validation_copy["message"]["content"] = json.dumps({field: normalized})
    worker.parse_selection(validation_copy, body, field, allowed, config)
    return normalized, {
        "raw_native_node_ids": ids,
        "normalized_native_node_ids": normalized,
        "removed_duplicate_ids": removed,
        "raw_exceeded_schema_max_items": len(ids) > target,
        "required_distinct_count": target,
    }


def call(query, body, field, allowed, config, output):
    worker.runtime(config)
    started = perf_counter()
    record = {
        **{k: query[k] for k in ("query_id", "case_id", "module")},
        "phase": "originals_strict_cardinality",
        "utc": datetime.now(timezone.utc).isoformat(),
        "request": body,
        "request_sha256": worker.digest(body),
        "provider_called": False,
    }
    try:
        record["provider_called"] = True
        raw = worker.local_json(config, "/api/chat", body)
        record["raw_response"] = raw
        ids, normalization = parse_strict(raw, body, field, allowed, config)
        record.update(status="completed", selected_native_node_ids=ids, normalization=normalization)
        return ids, normalization
    except Exception as exc:
        record.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        record["seconds"] = perf_counter() - started
        with (output / "model_calls.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")


def validate_parent(parent, queries, mappings, units, config):
    manifest = recovery.read_json(parent / "manifest.json")
    parents = worker.read_records(parent / "parent_results.jsonl")
    imported = worker.read_records(parent / "imported_model_calls.jsonl")
    new = worker.read_records(parent / "model_calls.jsonl")
    rows = worker.read_records(parent / "results.jsonl")
    plan = recovery.read_json(parent / "normalization_plan.json")
    worker.audit_results(
        parents, queries, mappings, units, config, imported, manifest["parent_identity"]
    )
    by_query = {r["query_id"]: r for r in parents}
    for row, query in zip(rows, queries, strict=True):
        qid = query["query_id"]
        if row["query_id"] != qid or row["status"] != "completed":
            raise ValueError("Strict cardinality requires a complete successful parent inventory")
        if qid in plan:
            recovery.validate_recovered(
                row,
                query,
                mappings[query["module"]],
                units,
                config,
                new,
                plan[qid],
                manifest["identity"],
            )
            observed = [c for c in imported if c["query_id"] == qid]
            body, _, allowed, _ = worker.request_body(
                query, mappings[query["module"]], units, config, "branches"
            )
            if (
                len(observed) != 1
                or recovery.normalize_branch_call(observed[0], body, allowed, config) != plan[qid]
            ):
                raise ValueError("Parent branch normalization differs from actual original calls")
        else:
            expected = deepcopy(by_query[qid])
            expected.update(
                experiment_identity=manifest["identity"],
                parent_experiment_identity=manifest["parent_identity"],
                parent_result_sha256=worker.digest(by_query[qid]),
                reused_parent_result=True,
                new_retrieval_seconds=0.0,
            )
            if row != expected:
                raise ValueError("Parent reused result differs from its actual calls")
    return rows, imported, new


def audit_results(rows, parent_rows, queries, mappings, units, config, rerun_ids, calls, identity):
    parent_map = {r["query_id"]: r for r in parent_rows}
    if len(calls) != len(rerun_ids) or {c["query_id"] for c in calls} != set(rerun_ids):
        raise ValueError("Strict cardinality call inventory is repeated or incomplete")
    for row, query in zip(rows, queries, strict=True):
        qid = query["query_id"]
        original = parent_map[qid]
        if row["query_id"] != qid or row["experiment_identity"] != identity:
            raise ValueError("Strict cardinality result inventory differs")
        body, field, allowed, excluded, target = strict_request(
            query, mappings[query["module"]], units, config, original["selected_branch_node_ids"]
        )
        if row["selected_branch_node_ids"] != original["selected_branch_node_ids"]:
            raise ValueError("Strict cardinality changed the actual selected branches")
        if qid not in rerun_ids:
            expected = deepcopy(original)
            expected.update(
                experiment_identity=identity,
                parent_experiment_identity=original["experiment_identity"],
                parent_result_sha256=worker.digest(original),
                reused_parent_result=True,
                new_retrieval_seconds=0.0,
                available_original_candidates=len(allowed),
                required_distinct_originals=target,
            )
            if row != expected or len(row["source_ids"]) != target:
                raise ValueError("A full parent ranking changed")
            continue
        observed = next(c for c in calls if c["query_id"] == qid)
        if observed["request"] != body or observed["request_sha256"] != worker.digest(body):
            raise ValueError("Strict cardinality altered prompts, native pools or model options")
        if row["status"] == "failed":
            if row["source_ids"] or observed["status"] != "failed":
                raise ValueError("Failed strict ranking cannot supply fallback evidence")
            continue
        selected, normalization = parse_strict(
            observed["raw_response"], body, field, allowed, config
        )
        ids = [mappings[query["module"]]["leaves"][n]["source_id"] for n in selected]
        if (
            row["source_ids"] != ids
            or row["selected_leaf_node_ids"] != selected
            or row["strict_cardinality_normalization"] != normalization
            or row["original_text_hashes"] != {s: units[s]["text_sha256"] for s in ids}
            or row["excluded_native_nodes_by_navigation_budget"] != excluded
            or observed["status"] != "completed"
            or observed["selected_native_node_ids"] != selected
        ):
            raise ValueError("Strict originals differ from actual native selections")


def run(request_path):
    request_path = Path(request_path).resolve()
    request = recovery.read_json(request_path)
    if set(request) != {"parent", "development_v1", "output"}:
        raise ValueError("Strict cardinality accepts frozen lineage paths only")
    root = Path(__file__).resolve().parents[1]
    paths = {k: (root / v).resolve() for k, v in request.items()}
    if any(not p.is_relative_to(root / "outputs/experiments") for p in paths.values()):
        raise ValueError("Strict cardinality paths must remain in experiment storage")
    parent, output = paths["parent"], paths["output"]
    if output.exists():
        raise ValueError("Strict cardinality needs a new output directory")
    parent_pins = recovery.pinned_directory(parent)
    development_pins = recovery.pinned_directory(paths["development_v1"])
    manifest = recovery.read_json(parent / "manifest.json")
    if (
        worker.digest(
            {k: v for k, v in manifest.items() if k not in {"identity", "production_change"}}
        )
        != manifest["identity"]
    ):
        raise ValueError("Parent identity changed")
    if (
        worker.file_hash(worker.__file__) != manifest["worker_sha256"]
        or worker.file_hash(recovery.__file__) != manifest["recovery_source_sha256"]
    ):
        raise ValueError("Frozen native prompt or recovery helper changed")
    config = manifest["config"]
    corpus, queries = [
        recovery.read_json(parent / name) for name in ("corpus.json", "queries.json")
    ]
    units = worker.validate_inputs(corpus, queries)
    mappings = recovery.read_json(parent / "native_index/source_mapping.json")
    for module, mapping in mappings.items():
        if (
            worker.map_native_tree(
                module, recovery.read_json(parent / "native_index" / (module + ".json")), units
            )
            != mapping
        ):
            raise ValueError("Native original source map changed")
    parent_rows, imported_calls, recovery_calls = validate_parent(
        parent, queries, mappings, units, config
    )
    calls_by_query = {
        c["query_id"]: c
        for c in [*imported_calls, *recovery_calls]
        if c["phase"] == "originals" and c["status"] == "completed"
    }
    rerun, candidate_counts = [], {}
    for row, query in zip(parent_rows, queries, strict=True):
        body, _, allowed, _ = worker.request_body(
            query,
            mappings[query["module"]],
            units,
            config,
            "originals",
            row["selected_branch_node_ids"],
        )
        observed = calls_by_query[query["query_id"]]
        if observed["request"] != body or observed["request_sha256"] != worker.digest(body):
            raise ValueError("Parent candidate pool is not backed by an actual frozen request")
        candidate_counts[query["query_id"]] = len(allowed)
        if len(row["source_ids"]) < min(config["top_k"], len(allowed)):
            rerun.append(query["query_id"])
    environment = worker.runtime(config)
    data = {
        "kind": "native_pageindex_adaptive_strict_cardinality_ablation",
        "method": worker.METHOD,
        "policy": POLICY,
        "parent_identity": manifest["identity"],
        "parent_artifacts": parent_pins,
        "development_v1_artifacts": development_pins,
        "development_v1_calls_separate": len(
            worker.read_records(paths["development_v1"] / "model_calls.jsonl")
        ),
        "imported_v2_actual_calls": len(imported_calls),
        "imported_v3_actual_calls": len(recovery_calls),
        "planned_new_original_ranking_calls": len(rerun),
        "rerun_query_ids": rerun,
        "candidate_counts": candidate_counts,
        "selection_stage": "Adaptive contract ablation after observed v3 results; not a sealed holdout",
        "request_sha256": worker.file_hash(request_path),
        "worker_sha256": worker.file_hash(worker.__file__),
        "recovery_source_sha256": worker.file_hash(recovery.__file__),
        "strict_source_sha256": worker.file_hash(__file__),
        "strict_tests_sha256": worker.file_hash(
            root / "tests/test_pageindex_strict_cardinality.py"
        ),
        "corpus_sha256": manifest["corpus_sha256"],
        "queries_sha256": manifest["queries_sha256"],
        "preparation_identity": manifest["preparation_identity"],
        "config": config,
        "runtime": environment,
        "python": sys.version,
        "native_chat_retrieval_used": False,
        "reference_labels_available": False,
        "index_model_calls_this_run": 0,
    }
    identity = worker.digest(data)
    output.mkdir(parents=True)
    worker.save(
        output / "manifest.json", {**data, "identity": identity, "production_change": False}
    )
    for source, name in (
        (parent / "corpus.json", "corpus.json"),
        (parent / "queries.json", "queries.json"),
        (parent / "results.jsonl", "parent_results.jsonl"),
        (parent / "imported_model_calls.jsonl", "imported_v2_model_calls.jsonl"),
        (parent / "model_calls.jsonl", "imported_v3_model_calls.jsonl"),
        (parent / "manifest.json", "parent_manifest.json"),
        (request_path, "request.json"),
        (Path(__file__), "strict_source.py"),
        (Path(worker.__file__), "worker_source.py"),
        (Path(recovery.__file__), "recovery_source.py"),
        (root / "tests/test_pageindex_strict_cardinality.py", "strict_test_source.py"),
    ):
        shutil.copyfile(source, output / name)
    shutil.copytree(parent / "native_index", output / "native_index")
    worker.save(
        output / "protocol_artifacts.json",
        {
            p.relative_to(output).as_posix(): worker.file_hash(p)
            for p in output.rglob("*")
            if p.is_file()
        },
    )
    rows = []
    for original, query in zip(parent_rows, queries, strict=True):
        qid = query["query_id"]
        row = deepcopy(original)
        target = min(config["top_k"], candidate_counts[qid])
        row.update(
            experiment_identity=identity,
            parent_experiment_identity=manifest["identity"],
            parent_result_sha256=worker.digest(original),
            reused_parent_result=qid not in rerun,
            new_retrieval_seconds=0.0,
            available_original_candidates=candidate_counts[qid],
            required_distinct_originals=target,
        )
        if qid in rerun:
            started = perf_counter()
            try:
                body, field, allowed, excluded, _ = strict_request(
                    query,
                    mappings[query["module"]],
                    units,
                    config,
                    original["selected_branch_node_ids"],
                )
                leaves, normalization = call(query, body, field, allowed, config, output)
                ids = [mappings[query["module"]]["leaves"][n]["source_id"] for n in leaves]
                row.update(
                    status="completed",
                    source_ids=ids,
                    selected_leaf_node_ids=leaves,
                    strict_cardinality_normalization=normalization,
                    original_text_hashes={s: units[s]["text_sha256"] for s in ids},
                    excluded_native_nodes_by_navigation_budget=excluded,
                )
            except Exception as exc:
                row.update(
                    status="failed",
                    source_ids=[],
                    selected_leaf_node_ids=[],
                    original_text_hashes={},
                    error=f"{type(exc).__name__}: {exc}",
                )
            row["new_retrieval_seconds"] = perf_counter() - started
            row["retrieval_seconds"] += row["new_retrieval_seconds"]
            print(f"Strict {query['case_id']}/{query['module']} {row['status']}", flush=True)
        rows.append(row)
        with (output / "results.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
    new_calls = worker.read_records(output / "model_calls.jsonl")
    audit_results(rows, parent_rows, queries, mappings, units, config, rerun, new_calls, identity)
    if (
        recovery.pinned_directory(parent) != parent_pins
        or recovery.pinned_directory(paths["development_v1"]) != development_pins
        or worker.runtime(config) != environment
    ):
        raise ValueError("Frozen lineage or local model environment changed")
    for name, pin in recovery.read_json(output / "protocol_artifacts.json").items():
        if worker.file_hash(output / name) != pin:
            raise ValueError("Frozen strict cardinality protocol changed")
    if worker.file_hash(__file__) != data["strict_source_sha256"]:
        raise ValueError("Strict cardinality source changed")
    summary = {
        "identity": identity,
        "method": worker.METHOD,
        "planned": len(queries),
        "recorded": len(rows),
        "completed": sum(r["status"] == "completed" for r in rows),
        "failed": sum(r["status"] == "failed" for r in rows),
        "parent_identity": manifest["identity"],
        "reused_full_parent_rankings": len(rows) - len(rerun),
        "imported_v2_actual_model_calls": len(imported_calls),
        "imported_v3_actual_model_calls": len(recovery_calls),
        "new_actual_model_calls": len(new_calls),
        "total_lineage_actual_model_calls": len(imported_calls)
        + len(recovery_calls)
        + len(new_calls),
        "development_v1_calls_separate": data["development_v1_calls_separate"],
        "new_model_call_seconds": sum(c["seconds"] for c in new_calls),
        "failed_new_calls": sum(c["status"] == "failed" for c in new_calls),
        "normalized_duplicate_completions": sum(
            bool(c.get("normalization", {}).get("removed_duplicate_ids")) for c in new_calls
        ),
        "new_prompt_tokens": sum(
            c.get("raw_response", {}).get("prompt_eval_count", 0) for c in new_calls
        ),
        "new_completion_tokens": sum(
            c.get("raw_response", {}).get("eval_count", 0) for c in new_calls
        ),
        "returned_below10": sum(len(r["source_ids"]) < 10 for r in rows),
        "underfilled_available_count": sum(
            len(r["source_ids"]) < r["required_distinct_originals"] for r in rows
        ),
        "native_chat_retrieval_used": False,
        "production_change": False,
    }
    worker.save(output / "summary.json", summary)
    worker.save(
        output / "artifacts.json",
        {
            p.relative_to(output).as_posix(): worker.file_hash(p)
            for p in output.rglob("*")
            if p.is_file() and p.name != "artifacts.json"
        },
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.request), indent=2))
