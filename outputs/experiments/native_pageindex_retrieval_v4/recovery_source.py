"""Recover only duplicate valid branch selections in a frozen PageIndex run.

The parent run is immutable. Existing successful answers and all actual parent
calls are imported with provenance; only previously missing original-ranking
calls are made. This is a selection-contract recovery ablation, not a new RAG
method or a second native PageIndex index build.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import shutil
import sys
from copy import deepcopy
from pathlib import Path
from time import perf_counter

from tools import pageindex_extension_worker as worker

POLICY = "stable_first_occurrence_valid_branch_ids_only_v1"


def read_json(path):
    return json.loads(Path(path).read_bytes())


def pinned_directory(directory):
    """Verify every parent artifact, rejecting traversal and unpinned additions."""
    directory = directory.resolve()
    pins = read_json(directory / "artifacts.json")
    observed = {
        p.relative_to(directory).as_posix()
        for p in directory.rglob("*")
        if p.is_file() and p.name != "artifacts.json"
    }
    if observed != set(pins):
        raise ValueError("Parent artifact membership changed")
    for name, expected in pins.items():
        path = (directory / name).resolve()
        if not path.is_relative_to(directory) or worker.file_hash(path) != expected:
            raise ValueError("Parent artifact changed: " + name)
    return {**pins, "artifacts.json": worker.file_hash(directory / "artifacts.json")}


def normalize_branch_call(observed, body, allowed, config):
    """Validate raw limits and native IDs before stable duplicate removal."""
    if (
        observed.get("phase") != "branches"
        or observed.get("provider_called") is not True
        or observed.get("status") != "failed"
        or observed.get("request") != body
        or observed.get("request_sha256") != worker.digest(body)
    ):
        raise ValueError("Duplicate recovery requires the exact failed actual branch request")
    raw = observed["raw_response"]
    value = json.loads(raw["message"]["content"])
    if not isinstance(value, dict) or set(value) != {"branch_ids"}:
        raise ValueError("Only the original branch selection contract can be normalized")
    ids = value["branch_ids"]
    limit = body["format"]["properties"]["branch_ids"]["maxItems"]
    if (
        not isinstance(ids, list)
        or not ids
        or len(ids) > limit
        or any(not isinstance(nid, str) or nid not in allowed for nid in ids)
        or len(ids) == len(set(ids))
    ):
        raise ValueError(
            "Recovery accepts duplicates only; unknown or excessive IDs remain invalid"
        )
    normalized, removed = [], []
    for index, nid in enumerate(ids):
        if nid in normalized:
            removed.append({"raw_index": index, "native_node_id": nid})
        else:
            normalized.append(nid)
    # Validate completion/context using the unchanged strict parser. The actual
    # raw completion is never modified; this copy exists only for validation.
    validation_copy = deepcopy(raw)
    validation_copy["message"]["content"] = json.dumps({"branch_ids": normalized})
    worker.parse_selection(validation_copy, body, "branch_ids", allowed, config)
    return {
        "policy": POLICY,
        "raw_branch_ids": ids,
        "normalized_branch_ids": normalized,
        "removed_duplicate_ids": removed,
        "parent_call_sha256": worker.digest(observed),
        "parent_request_sha256": observed["request_sha256"],
        "parent_raw_response_sha256": worker.digest(raw),
        "parent_call_status": observed["status"],
    }


def validate_recovered(row, query, mapping, units, config, calls, normalization, identity):
    if (
        row["experiment_identity"] != identity
        or row["selected_branch_node_ids"] != normalization["normalized_branch_ids"]
        or row["branch_normalization"] != normalization
    ):
        raise ValueError("Recovered row differs from frozen branch normalization")
    body, field, allowed, excluded = worker.request_body(
        query, mapping, units, config, "originals", normalization["normalized_branch_ids"]
    )
    matches = [c for c in calls if c["query_id"] == query["query_id"]]
    if len(matches) != 1:
        raise ValueError("Recovery must execute exactly one new original-ranking attempt")
    observed = matches[0]
    if (
        observed["request"] != body
        or observed["request_sha256"] != worker.digest(body)
        or observed["phase"] != "originals"
        or observed.get("provider_called") is not True
    ):
        raise ValueError("Recovery changed the original ranking prompt or options")
    if row["status"] != "completed":
        if row["source_ids"] or observed["status"] != "failed":
            raise ValueError("Failed recovery cannot contain fallback sources")
        return
    selected = worker.parse_selection(observed["raw_response"], body, field, allowed, config)
    ids = [mapping["leaves"][nid]["source_id"] for nid in selected]
    if (
        observed["status"] != "completed"
        or observed["selected_native_node_ids"] != selected
        or row["selected_leaf_node_ids"] != selected
        or row["source_ids"] != ids
        or row["original_text_hashes"] != {sid: units[sid]["text_sha256"] for sid in ids}
        or row["excluded_native_nodes_by_navigation_budget"] != excluded
    ):
        raise ValueError("Recovered evidence does not reconstruct from actual native selections")


def run(request_path):
    request_path = Path(request_path).resolve()
    request = read_json(request_path)
    if set(request) != {"parent", "parent_request", "output"}:
        raise ValueError("Recovery accepts lineage paths only, never labels or source targets")
    root = Path(__file__).resolve().parents[1]
    parent = (root / request["parent"]).resolve()
    parent_request_path = (root / request["parent_request"]).resolve()
    output = (root / request["output"]).resolve()
    if (
        not parent.is_relative_to(root / "outputs/experiments")
        or not output.is_relative_to(root / "outputs/experiments")
        or output == parent
        or output.exists()
    ):
        raise ValueError("Recovery requires a fresh separate experimental output directory")
    parent_pins = pinned_directory(parent)
    parent_manifest = read_json(parent / "manifest.json")
    parent_identity = parent_manifest["identity"]
    manifest_data = {
        k: v for k, v in parent_manifest.items() if k not in {"identity", "production_change"}
    }
    if worker.digest(manifest_data) != parent_identity:
        raise ValueError("Parent manifest identity differs")
    parent_request = read_json(parent_request_path)
    config = worker.settings(parent_request["config"])
    if (
        config != parent_manifest["config"]
        or (root / parent_request["output"]).resolve() != parent
        or parent_request["preparation_identity"] != parent_manifest["preparation_identity"]
        or worker.file_hash(worker.__file__) != parent_manifest["worker_sha256"]
    ):
        raise ValueError("Parent configuration or unchanged prompt helper differs")
    for key in ("corpus", "queries"):
        original_path = (root / parent_request[key]).resolve()
        if worker.file_hash(original_path) != parent_manifest[key + "_sha256"]:
            raise ValueError("Frozen original input changed")
    corpus, queries = [read_json(parent / name) for name in ("corpus.json", "queries.json")]
    units = worker.validate_inputs(corpus, queries)
    mappings = read_json(parent / "native_index/source_mapping.json")
    for module, mapping in mappings.items():
        actual = worker.map_native_tree(
            module, read_json(parent / "native_index" / (module + ".json")), units
        )
        if actual != mapping:
            raise ValueError("Frozen native index mapping changed")
    if importlib.metadata.version("pageindex") != parent_manifest["native_pageindex_version"]:
        raise ValueError("Native PageIndex package version changed")
    package = Path(importlib.metadata.distribution("pageindex").locate_file("pageindex"))
    for name, pin in parent_manifest["native_sources"].items():
        if worker.file_hash(package / name) != pin:
            raise ValueError("Native PageIndex implementation changed")
    parent_rows = worker.read_records(parent / "results.jsonl")
    imported_calls = worker.read_records(parent / "model_calls.jsonl")
    worker.audit_results(
        parent_rows, queries, mappings, units, config, imported_calls, parent_identity
    )
    by_query = {r["query_id"]: r for r in parent_rows}
    if set(by_query) != {q["query_id"] for q in queries} or any(
        c.get("provider_called") is not True for c in imported_calls
    ):
        raise ValueError("Parent results or actual model-call inventory is incomplete")
    normalization_plan, ineligible = {}, {}
    for query in queries:
        qid = query["query_id"]
        if by_query[qid]["status"] == "completed":
            continue
        observed = [c for c in imported_calls if c["query_id"] == qid]
        try:
            if len(observed) != 1:
                raise ValueError(
                    "Recovery requires a single failed branch call and no ranking call"
                )
            body, _, allowed, _ = worker.request_body(
                query, mappings[query["module"]], units, config, "branches"
            )
            normalization_plan[qid] = normalize_branch_call(observed[0], body, allowed, config)
        except (ValueError, KeyError, TypeError) as exc:
            ineligible[qid] = str(exc)
    environment = worker.runtime(config)
    recovery_data = {
        "kind": "native_pageindex_duplicate_valid_branch_recovery_ablation",
        "method": worker.METHOD,
        "parent_identity": parent_identity,
        "parent_artifacts": parent_pins,
        "parent_request_sha256": worker.file_hash(parent_request_path),
        "request_sha256": worker.file_hash(request_path),
        "worker_sha256": worker.file_hash(worker.__file__),
        "corpus_sha256": parent_manifest["corpus_sha256"],
        "queries_sha256": parent_manifest["queries_sha256"],
        "preparation_identity": parent_manifest["preparation_identity"],
        "native_pageindex_version": parent_manifest["native_pageindex_version"],
        "native_sources": parent_manifest["native_sources"],
        "recovery_source_sha256": worker.file_hash(__file__),
        "recovery_tests_sha256": worker.file_hash(
            root / "tests/test_pageindex_duplicate_recovery.py"
        ),
        "config": config,
        "python": sys.version,
        "runtime": environment,
        "normalization_policy": POLICY,
        "normalization_plan_sha256": worker.digest(normalization_plan),
        "imported_actual_model_calls": len(imported_calls),
        "planned_new_original_ranking_calls": len(normalization_plan),
        "reference_labels_available": False,
        "native_chat_retrieval_used": False,
        "index_model_calls_this_run": 0,
    }
    identity = worker.digest(recovery_data)
    output.mkdir(parents=True)
    worker.save(
        output / "manifest.json",
        {**recovery_data, "identity": identity, "production_change": False},
    )
    worker.save(output / "normalization_plan.json", normalization_plan)
    worker.save(output / "ineligible_parent_failures.json", ineligible)
    worker.save(
        output / "parent_failed_results.json",
        [r for r in parent_rows if r["status"] != "completed"],
    )
    for source, name in (
        (parent / "corpus.json", "corpus.json"),
        (parent / "queries.json", "queries.json"),
        (parent / "model_calls.jsonl", "imported_model_calls.jsonl"),
        (parent / "results.jsonl", "parent_results.jsonl"),
        (parent / "manifest.json", "parent_manifest.json"),
        (request_path, "request.json"),
        (parent_request_path, "parent_request.json"),
        (Path(worker.__file__), "worker_source.py"),
        (Path(__file__), "recovery_source.py"),
        (root / "tests/test_pageindex_duplicate_recovery.py", "recovery_test_source.py"),
    ):
        shutil.copyfile(source, output / name)
    shutil.copytree(parent / "native_index", output / "native_index")
    # This immutable protocol bundle is written before the first new generation.
    worker.save(
        output / "protocol_artifacts.json",
        {
            p.relative_to(output).as_posix(): worker.file_hash(p)
            for p in output.rglob("*")
            if p.is_file()
        },
    )
    rows = []
    for query in queries:
        qid = query["query_id"]
        parent_row = by_query[qid]
        row = deepcopy(parent_row)
        row.update(
            experiment_identity=identity,
            parent_experiment_identity=parent_identity,
            parent_result_sha256=worker.digest(parent_row),
            reused_parent_result=qid not in normalization_plan,
            new_retrieval_seconds=0.0,
        )
        if qid in normalization_plan:
            normalization = normalization_plan[qid]
            branches = normalization["normalized_branch_ids"]
            row.update(
                selected_branch_node_ids=branches,
                branch_normalization=normalization,
                parent_failure_preserved=True,
                parent_retrieval_seconds=parent_row["retrieval_seconds"],
            )
            started = perf_counter()
            try:
                mapping = mappings[query["module"]]
                body, field, allowed, excluded = worker.request_body(
                    query, mapping, units, config, "originals", branches
                )
                leaves = worker.call(query, body, field, allowed, config, "originals", output)
                ids = [mapping["leaves"][nid]["source_id"] for nid in leaves]
                row.update(
                    status="completed",
                    source_ids=ids,
                    selected_leaf_node_ids=leaves,
                    original_text_hashes={sid: units[sid]["text_sha256"] for sid in ids},
                    excluded_native_nodes_by_navigation_budget=excluded,
                    native_index_module=query["module"],
                )
                row.pop("error", None)
            except Exception as exc:
                row.update(status="failed", source_ids=[], error=f"{type(exc).__name__}: {exc}")
            row["new_retrieval_seconds"] = perf_counter() - started
            row["retrieval_seconds"] += row["new_retrieval_seconds"]
            print(f"Recovery {query['case_id']}/{query['module']} {row['status']}", flush=True)
        rows.append(row)
        with (output / "results.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
    new_calls = worker.read_records(output / "model_calls.jsonl")
    if len(new_calls) != len(normalization_plan) or any(
        c["query_id"] not in normalization_plan for c in new_calls
    ):
        raise ValueError("Unexpected new model-call count or scope")
    for row, query in zip(rows, queries, strict=True):
        if row["query_id"] in normalization_plan:
            validate_recovered(
                row,
                query,
                mappings[query["module"]],
                units,
                config,
                new_calls,
                normalization_plan[row["query_id"]],
                identity,
            )
        else:
            expected = deepcopy(by_query[row["query_id"]])
            expected.update(
                experiment_identity=identity,
                parent_experiment_identity=parent_identity,
                parent_result_sha256=worker.digest(by_query[row["query_id"]]),
                reused_parent_result=True,
                new_retrieval_seconds=0.0,
            )
            if row != expected:
                raise ValueError("A reused parent result changed")
    if pinned_directory(parent) != parent_pins or worker.runtime(config) != environment:
        raise ValueError("Parent artifacts or local model environment changed")
    for name, pin in read_json(output / "protocol_artifacts.json").items():
        if worker.file_hash(output / name) != pin:
            raise ValueError("Recovery protocol artifact changed")
    if (
        worker.file_hash(__file__) != recovery_data["recovery_source_sha256"]
        or worker.file_hash(worker.__file__) != recovery_data["worker_sha256"]
        or worker.file_hash(request_path) != recovery_data["request_sha256"]
    ):
        raise ValueError("Frozen recovery implementation or request changed")
    summary = {
        "identity": identity,
        "method": worker.METHOD,
        "ablation": POLICY,
        "parent_identity": parent_identity,
        "planned": len(queries),
        "recorded": len(rows),
        "completed": sum(r["status"] == "completed" for r in rows),
        "failed": sum(r["status"] != "completed" for r in rows),
        "reused_successful_parent_answers": sum(r["status"] == "completed" for r in parent_rows),
        "parent_failures_preserved": sum(r["status"] != "completed" for r in parent_rows),
        "recovery_attempted": len(normalization_plan),
        "recovery_completed": sum(
            r["status"] == "completed" and r["query_id"] in normalization_plan for r in rows
        ),
        "imported_actual_navigation_model_calls": len(imported_calls),
        "new_actual_navigation_model_calls": len(new_calls),
        "total_lineage_actual_navigation_model_calls": len(imported_calls) + len(new_calls),
        "new_model_call_seconds": sum(c["seconds"] for c in new_calls),
        "imported_model_call_seconds": sum(c["seconds"] for c in imported_calls),
        "new_prompt_tokens": sum(
            c.get("raw_response", {}).get("prompt_eval_count", 0) for c in new_calls
        ),
        "new_completion_tokens": sum(
            c.get("raw_response", {}).get("eval_count", 0) for c in new_calls
        ),
        "native_indexed_units": len(units),
        "native_module_indexes": len(mappings),
        "index_model_calls_this_run": 0,
        "reference_labels_available": False,
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
