"""Consolidate ten real retrieval routes and preserve every earlier ablation.

All worker inventories and source mappings are validated before reference
labels are opened. Parsing audits, retrieval recall and judgment completion
remain separate. No model or database call is made by this reporter.
"""

from __future__ import annotations

import argparse
import json
import shutil
from copy import deepcopy
from pathlib import Path

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.provenance import digest, write_json
from tools.report_anchored_hybrid import (
    NO_MMR_METHOD,
    SIX_METHODS,
    evidence_costs,
    read_rows,
    validate_rankings,
    verify_bundle,
    write_csv,
)
from tools.report_guarded_hybrid import top10_changes
from tools.report_planned_hybrid import evaluate, paired_changes, summarize

NATIVE_METHODS = ("flag_embedding_rerank", "neo4j_clause_graph", "pageindex_tree_adapter")
DEFAULT_PREFERRED = "planned_hybrid_v3_guarded_30"
LABELS = {
    "vector": "1 · Vector",
    "bm25": "2 · BM25",
    "hybrid": "3 · Hybrid RRF",
    "graph_local": "4 · Source graph-assisted",
    "lightrag": "5 · LightRAG mix",
    "graphrag": "6 · Microsoft GraphRAG Local",
    "flag_embedding_rerank": "8 · FlagEmbedding reranking",
    "neo4j_clause_graph": "9 · Neo4j hybrid clause graph",
    "pageindex_tree_adapter": "10 · PageIndex tree + local navigation",
}


def load_json(path):
    return json.loads(Path(path).read_bytes())


def verify_files(directory):
    directory = Path(directory).resolve()
    pins = load_json(directory / "artifacts.json")
    if not pins:
        raise ValueError("Empty frozen artifact inventory")
    for name, expected in pins.items():
        source = (directory / name).resolve()
        if (
            not source.is_relative_to(directory)
            or not source.is_file()
            or file_hash(source) != expected
        ):
            raise ValueError("Changed or unsafe frozen source: " + name)
    return pins


def validate_common(corpus, queries, patients):
    units = {u["source_id"]: u for u in corpus["units"]}
    if len(units) != len(corpus["units"]) or len(queries) != 77 or len(patients) != 33:
        raise ValueError("Expected the fixed 94-source, 77-query, 33-case comparison")
    if len(units) != 94 or {q["case_id"] for q in queries} != set(patients):
        raise ValueError("Shared source or patient inventory differs")
    import hashlib

    for unit in units.values():
        if hashlib.sha256(unit["evidence_text"].encode()).hexdigest() != unit["text_sha256"]:
            raise ValueError("Original source text fingerprint differs")
    return units


def validate_native(rows, queries, units, method, identity):
    validate_rankings(rows, queries, units, [method], identity)
    for row in rows:
        if row["status"] == "completed" and "ranked_sources" in row:
            if [r["source_id"] for r in row["ranked_sources"]] != row["source_ids"]:
                raise ValueError("Native source ranking differs from mapped originals")
        for source in row.get("ranked_sources", []):
            for path in source.get("graph_paths", []):
                sid, seed = path["source_id"], path["seed_source_id"]
                if (
                    sid != source["source_id"]
                    or seed not in units
                    or units[seed]["module"] != row["module"]
                ):
                    raise ValueError("Native graph path crosses source identity or module")
                if path["text_sha256"] != units[sid]["text_sha256"]:
                    raise ValueError("Native graph path original fingerprint differs")


def experiment_path(root, value):
    """Allow legitimate absolute parent paths, but never leave experiment storage."""
    path = (Path(root).resolve() / value).resolve()
    if not path.is_relative_to(Path(root).resolve() / "outputs/experiments"):
        raise ValueError("PageIndex lineage path escapes experimental storage")
    return path


def validate_pageindex_recovery(root, directory, request_path, rows, manifest, queries, units):
    """Reconstruct reused answers and new calls without rewriting parent failures."""
    from tools import pageindex_extension_worker as navigator
    from tools import recover_pageindex_duplicates as recovery

    request = load_json(request_path)
    if set(request) != {"parent", "parent_request", "output"}:
        raise ValueError("Unexpected PageIndex recovery request")
    parent = experiment_path(root, request["parent"])
    parent_request_path = experiment_path(root, request["parent_request"])
    if (
        experiment_path(root, request["output"]) != directory.resolve()
        or file_hash(request_path) != manifest["request_sha256"]
        or file_hash(parent_request_path) != manifest["parent_request_sha256"]
        or recovery.pinned_directory(parent) != manifest["parent_artifacts"]
    ):
        raise ValueError("PageIndex recovery parent pins or request changed")
    parent_manifest, _ = verify_bundle(parent)
    if parent_manifest["identity"] != manifest["parent_identity"]:
        raise ValueError("PageIndex recovery parent identity differs")
    parent_request = load_json(parent_request_path)
    if (
        experiment_path(root, parent_request["output"]) != parent
        or navigator.settings(parent_request["config"]) != manifest["config"]
        or manifest["config"] != parent_manifest["config"]
        or file_hash(navigator.__file__) != manifest["worker_sha256"]
        or file_hash(recovery.__file__) != manifest["recovery_source_sha256"]
    ):
        raise ValueError("PageIndex recovery changed its unchanged navigation contract")
    mappings = load_json(directory / "native_index/source_mapping.json")
    for module, mapping in mappings.items():
        if (
            navigator.map_native_tree(
                module, load_json(directory / "native_index" / (module + ".json")), units
            )
            != mapping
        ):
            raise ValueError("PageIndex native original-source map differs")
    for name in ("model_calls.jsonl", "results.jsonl"):
        imported = (
            "imported_model_calls.jsonl" if name.startswith("model") else "parent_results.jsonl"
        )
        if file_hash(directory / imported) != file_hash(parent / name):
            raise ValueError("PageIndex imported actual calls or parent results changed")
    parents = read_rows(directory / "parent_results.jsonl")
    imported_calls = read_rows(directory / "imported_model_calls.jsonl")
    calls = read_rows(directory / "model_calls.jsonl")
    config = manifest["config"]
    navigator.audit_results(
        parents, queries, mappings, units, config, imported_calls, manifest["parent_identity"]
    )
    plan = load_json(directory / "normalization_plan.json")
    if digest(plan) != manifest["normalization_plan_sha256"]:
        raise ValueError("PageIndex duplicate normalization plan changed")
    by_query = {r["query_id"]: r for r in parents}
    qmap = {q["query_id"]: q for q in queries}
    if (
        len(calls) != len(plan)
        or len(imported_calls) != manifest["imported_actual_model_calls"]
        or len(calls) != manifest["planned_new_original_ranking_calls"]
        or set(c["query_id"] for c in calls) != set(plan)
        or load_json(directory / "parent_failed_results.json")
        != [r for r in parents if r["status"] != "completed"]
    ):
        raise ValueError("PageIndex imported/new call accounting or preserved failures differs")
    for row in rows:
        qid = row["query_id"]
        original = by_query[qid]
        if qid in plan:
            observed = [c for c in imported_calls if c["query_id"] == qid]
            if len(observed) != 1 or original["status"] != "failed":
                raise ValueError("Recovery replaced a completed answer or reran an existing rank")
            body, _, allowed, _ = navigator.request_body(
                qmap[qid], mappings[row["module"]], units, config, "branches"
            )
            if recovery.normalize_branch_call(observed[0], body, allowed, config) != plan[qid]:
                raise ValueError("Recovery normalization differs from the actual failed completion")
            recovery.validate_recovered(
                row,
                qmap[qid],
                mappings[row["module"]],
                units,
                config,
                calls,
                plan[qid],
                manifest["identity"],
            )
        else:
            expected = deepcopy(original)
            expected.update(
                experiment_identity=manifest["identity"],
                parent_experiment_identity=manifest["parent_identity"],
                parent_result_sha256=digest(original),
                reused_parent_result=True,
                new_retrieval_seconds=0.0,
            )
            if row != expected:
                raise ValueError("An imported PageIndex parent answer changed")
    return parent_request, {
        "parent_identity": manifest["parent_identity"],
        "parent_directory": str(parent),
        "parent_completed": sum(r["status"] == "completed" for r in parents),
        "parent_failed": sum(r["status"] == "failed" for r in parents),
        "parent_failures_preserved": load_json(directory / "parent_failed_results.json"),
        "normalization_policy": manifest["normalization_policy"],
        "imported_actual_model_calls": len(imported_calls),
        "new_actual_model_calls": len(calls),
        "total_lineage_actual_model_calls": len(imported_calls) + len(calls),
        "new_model_call_seconds": sum(c["seconds"] for c in calls),
    }


def select_seventh(metrics, v5_primary, preferred=DEFAULT_PREFERRED):
    """Promote the prespecified v5 primary only after an actual strict gain."""
    by_method = {m["method"]: m for m in metrics}
    baseline, candidate = by_method[DEFAULT_PREFERRED], by_method[v5_primary]
    promotes = (
        candidate["coverage_recall_5"] is not None
        and candidate["coverage_recall_5"] > baseline["coverage_recall_5"] + 1e-12
        and candidate["coverage_recall_10"] is not None
        and candidate["coverage_recall_10"] >= 1 - 1e-12
    )
    selected = v5_primary if promotes else DEFAULT_PREFERRED
    if preferred not in {DEFAULT_PREFERRED, "auto", selected}:
        raise ValueError("Requested seventh method fails the Top5 gain and Top10 coverage gate")
    return selected, {
        "selected": selected,
        "baseline": DEFAULT_PREFERRED,
        "candidate": v5_primary,
        "candidate_passed": promotes,
        "rule": "Strictly improve v3 coverage R@5 and retain 100% coverage R@10",
        "selection_scope": "Observed development fixtures; not an unseen holdout estimate",
    }


def pageindex_cardinality(rows, original_calls):
    """Separate successful query execution from candidate and result counts."""
    from collections import Counter

    available, returned, underfilled, unavailable = Counter(), Counter(), 0, 0
    for row in rows:
        returned[len(row["source_ids"])] += 1
        matches = [c for c in original_calls if c["query_id"] == row["query_id"]]
        if len(matches) != 1:
            raise ValueError("Cardinality audit requires one observed final request per query")
        request = matches[0]["request"]
        count = len(json.loads(request["messages"][1]["content"])["originals"])
        available[count] += 1
        underfilled += len(row["source_ids"]) < min(10, count)
        unavailable += count < 10
    return {
        "returned_original_count_distribution": dict(returned),
        "available_original_candidate_distribution": dict(available),
        "queries_returning_fewer_than10": sum(v for k, v in returned.items() if k < 10),
        "queries_with_candidate_pool_below10": unavailable,
        "queries_underfilled_relative_to_available_count": underfilled,
        "interpretation": "Completed means the model call and source contract completed; it does not mean ten originals were available or returned.",
    }


def validate_pageindex_strict(root, directory, request_path, rows, manifest, queries, units):
    from tools import pageindex_extension_worker as navigator
    from tools import recover_pageindex_duplicates as recovery
    from tools import run_pageindex_strict_cardinality as strict

    request = load_json(request_path)
    if set(request) != {"parent", "development_v1", "output"}:
        raise ValueError("Unexpected strict-cardinality lineage request")
    parent = experiment_path(root, request["parent"])
    development = experiment_path(root, request["development_v1"])
    if (
        experiment_path(root, request["output"]) != directory.resolve()
        or file_hash(request_path) != manifest["request_sha256"]
        or recovery.pinned_directory(parent) != manifest["parent_artifacts"]
        or recovery.pinned_directory(development) != manifest["development_v1_artifacts"]
        or file_hash(strict.__file__) != manifest["strict_source_sha256"]
        or file_hash(navigator.__file__) != manifest["worker_sha256"]
        or file_hash(recovery.__file__) != manifest["recovery_source_sha256"]
    ):
        raise ValueError("Strict-cardinality source, parent or development artifact changed")
    parent_manifest, _ = verify_bundle(parent)
    parent_rows = read_rows(parent / "results.jsonl")
    original_request, lineage = validate_pageindex_recovery(
        root, parent, parent / "request.json", parent_rows, parent_manifest, queries, units
    )
    if parent_manifest["identity"] != manifest["parent_identity"]:
        raise ValueError("Strict-cardinality parent identity differs")
    if manifest["config"] != parent_manifest["config"]:
        raise ValueError("Strict-cardinality model options or evidence budgets changed")
    for name, pin in manifest["parent_artifacts"].items():
        if name.startswith("native_index/") and file_hash(directory / name) != pin:
            raise ValueError("Strict-cardinality native branch index changed")
    for source, target in (
        ("results.jsonl", "parent_results.jsonl"),
        ("imported_model_calls.jsonl", "imported_v2_model_calls.jsonl"),
        ("model_calls.jsonl", "imported_v3_model_calls.jsonl"),
    ):
        if file_hash(parent / source) != file_hash(directory / target):
            raise ValueError("Strict-cardinality imported actual lineage changed")
    mappings = load_json(directory / "native_index/source_mapping.json")
    calls = read_rows(directory / "model_calls.jsonl")
    strict.audit_results(
        rows,
        parent_rows,
        queries,
        mappings,
        units,
        manifest["config"],
        manifest["rerun_query_ids"],
        calls,
        manifest["identity"],
    )
    v2_calls = read_rows(directory / "imported_v2_model_calls.jsonl")
    v3_calls = read_rows(directory / "imported_v3_model_calls.jsonl")
    if (
        len(v2_calls) != manifest["imported_v2_actual_calls"]
        or len(v3_calls) != manifest["imported_v3_actual_calls"]
        or len(calls) != manifest["planned_new_original_ranking_calls"]
        or len(read_rows(development / "model_calls.jsonl"))
        != manifest["development_v1_calls_separate"]
    ):
        raise ValueError("Strict-cardinality model-call accounting differs")
    parent_final_calls = [c for c in [*v2_calls, *v3_calls] if c["phase"] == "originals"]
    rerun = set(manifest["rerun_query_ids"])
    active_final_calls = [c for c in parent_final_calls if c["query_id"] not in rerun] + calls
    return original_request, {
        **lineage,
        "strict_parent_identity": manifest["parent_identity"],
        "strict_parent_cardinality": pageindex_cardinality(parent_rows, parent_final_calls),
        "strict_current_cardinality": pageindex_cardinality(rows, active_final_calls),
        "new_strict_actual_model_calls": len(calls),
        "imported_v2_actual_model_calls": len(v2_calls),
        "imported_v3_actual_model_calls": len(v3_calls),
        "total_current_lineage_actual_model_calls": len(v2_calls) + len(v3_calls) + len(calls),
        "development_v1_calls_separate": manifest["development_v1_calls_separate"],
        "strict_new_model_call_seconds": sum(c["seconds"] for c in calls),
        "strict_failed_calls": sum(c["status"] == "failed" for c in calls),
    }


def load_native(
    root, inputs, queries, corpus, units, flag_dir, neo4j_path, page_dir, worker_inputs
):
    """Validate real worker results and bind them to the same original inputs."""
    pins, rows, execution = {}, [], {}
    for method, directory in ((NATIVE_METHODS[0], flag_dir), (NATIVE_METHODS[2], page_dir)):
        directory = Path(directory)
        bundle_pins = verify_files(directory)
        manifest, summary = [
            load_json(directory / name) for name in ("manifest.json", "summary.json")
        ]
        excluded = {"identity", "production_change"}
        if digest({k: v for k, v in manifest.items() if k not in excluded}) != manifest["identity"]:
            raise ValueError("Native worker manifest identity differs")
        record = read_rows(directory / "results.jsonl")
        validate_native(record, queries, units, method, manifest["identity"])
        if (
            summary["planned"] != 77
            or summary["recorded"] != 77
            or summary["completed"] != sum(r["status"] == "completed" for r in record)
            or summary["failed"] != sum(r["status"] == "failed" for r in record)
        ):
            raise ValueError("A native route is pending or has inconsistent completion counts")
        pins[method] = {
            "manifest_identity": manifest["identity"],
            "artifacts_sha256": file_hash(directory / "artifacts.json"),
            "artifacts": bundle_pins,
        }
        execution[method] = summary
        rows.extend(record)
        if method == NATIVE_METHODS[0]:
            job_path = Path(worker_inputs[method])
            job = load_json(job_path)
            if (
                manifest["input_sha256"] != file_hash(job_path)
                or job["corpus"] != corpus
                or job["queries"] != queries
            ):
                raise ValueError("FlagEmbedding used different frozen original inputs")
            for row in record:
                if row["status"] == "completed" and any(
                    s not in job["candidates"][row["query_id"]] for s in row["source_ids"]
                ):
                    raise ValueError(
                        "Native reranker returned a source outside its frozen candidate pool"
                    )
        else:
            # PageIndex pins the shared corpus and queries directly. The native
            # hierarchy is real; the query navigator is a first-party adapter.
            request_path = Path(worker_inputs[method])
            request = load_json(request_path)
            if manifest.get("kind") == "native_pageindex_adaptive_strict_cardinality_ablation":
                request, lineage = validate_pageindex_strict(
                    root, directory, request_path, record, manifest, queries, units
                )
                execution[method] = {**summary, "recovery_lineage": lineage}
            elif (
                manifest.get("kind") == "native_pageindex_duplicate_valid_branch_recovery_ablation"
            ):
                request, lineage = validate_pageindex_recovery(
                    root, directory, request_path, record, manifest, queries, units
                )
                execution[method] = {**summary, "recovery_lineage": lineage}
            from tools.pageindex_extension_worker import settings

            master_request = load_json(Path(inputs) / "pageindex_request.json")
            if (
                settings(request["config"]) != settings(master_request["config"])
                or request["preparation_identity"] != master_request["preparation_identity"]
                or manifest["preparation_identity"] != master_request["preparation_identity"]
            ):
                raise ValueError("PageIndex model, evidence budgets or frozen preparation changed")
            paths = {
                k: Path(request[k]) if Path(request[k]).is_absolute() else root / request[k]
                for k in ("corpus", "queries")
            }
            if (
                manifest["corpus_sha256"] != file_hash(paths["corpus"])
                or manifest["queries_sha256"] != file_hash(paths["queries"])
                or load_json(paths["corpus"]) != corpus
                or load_json(paths["queries"]) != queries
            ):
                raise ValueError("PageIndex indexed different original source/query inputs")
            if summary.get("native_chat_retrieval_used") is not False:
                raise ValueError("Unexpected PageIndex retrieval contract")
    neo4j_path = Path(neo4j_path)
    native = load_json(neo4j_path)
    manifest, record = native["manifest"], native["results"]
    job_path = Path(worker_inputs[NATIVE_METHODS[1]])
    job = load_json(job_path)
    if (
        manifest["input_sha256"] != file_hash(job_path)
        or manifest["experiment_identity"] != job["experiment_identity"]
        or job["corpus"] != corpus
        or job["queries"] != queries
    ):
        raise ValueError("Neo4j used different frozen original inputs")
    validate_native(record, queries, units, NATIVE_METHODS[1], manifest["experiment_identity"])
    pins[NATIVE_METHODS[1]] = {"results_sha256": file_hash(neo4j_path), "manifest": manifest}
    execution[NATIVE_METHODS[1]] = {
        "planned": len(queries),
        "recorded": len(record),
        "completed": sum(r["status"] == "completed" for r in record),
        "failed": sum(r["status"] == "failed" for r in record),
        "index_build_seconds": manifest["index_build_seconds"],
        "llm_calls": manifest["llm_calls"],
        "native_graph_counts": manifest.get("native_graph_counts"),
        "indexes": manifest["indexes"],
    }
    rows.extend(record)
    return rows, pins, execution


def costs(rows, execution):
    result = []
    for method in dict.fromkeys(r["method"] for r in rows):
        selected = [r for r in rows if r["method"] == method]
        timings = [
            next(
                (
                    r[k]
                    for k in (
                        "retrieval_seconds",
                        "seconds",
                        "ranking_seconds_excluding_import_reconstruction",
                        "retrieval_seconds_including_facet_embeddings",
                    )
                    if k in r
                ),
                None,
            )
            for r in selected
        ]
        measured = [v for v in timings if isinstance(v, (int, float))]
        result.append(
            {
                "method": method,
                "timed_records": len(measured),
                "recorded_query_seconds": sum(measured) if measured else None,
                "mean_recorded_query_seconds": sum(measured) / len(measured) if measured else None,
                "failed_records": sum(r["status"] == "failed" for r in selected),
                "worker_execution": execution.get(method),
            }
        )
    return result


def build(
    root,
    inputs_dir,
    flag_dir,
    neo4j_path,
    pageindex_dir,
    output,
    worker_inputs=None,
    preferred=DEFAULT_PREFERRED,
    reference_path=None,
):
    root, inputs_dir, output = map(lambda p: Path(p).resolve(), (root, inputs_dir, output))
    if output.exists() or not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Use a fresh, separate experiment report directory")
    input_pins = verify_files(inputs_dir)
    input_manifest = load_json(inputs_dir / "manifest.json")
    if (
        digest(
            {k: v for k, v in input_manifest.items() if k not in {"identity", "production_change"}}
        )
        != input_manifest["identity"]
    ):
        raise ValueError("Shared input manifest self-identity differs")
    filenames = dict(
        zip(
            NATIVE_METHODS,
            ("flag_input.json", "neo4j_input.json", "pageindex_request.json"),
            strict=True,
        )
    )
    worker_inputs = worker_inputs or {m: inputs_dir / name for m, name in filenames.items()}
    worker_pins = load_json(inputs_dir / "worker_inputs.json")
    if set(worker_inputs) != set(NATIVE_METHODS) or any(
        file_hash(worker_inputs[m]) != worker_pins[name]
        for m, name in filenames.items()
        if m != NATIVE_METHODS[2]
    ):
        raise ValueError("Native worker input differs from the master frozen request")
    corpus, queries, patients = [
        load_json(inputs_dir / name) for name in ("corpus.json", "queries.json", "patients.json")
    ]
    units = validate_common(corpus, queries, patients)
    if digest(patients) != digest(
        load_json(root / "outputs/experiments/six_method_query_preparation_v2/patients.json")
    ):
        raise ValueError("Shared patient facts differ from the original comparison")
    six_dir = root / "outputs/experiments/six_method_retrieval_v2"
    six_manifest, _ = verify_bundle(six_dir, six=True)
    if (
        load_json(six_dir / "corpus.json") != corpus
        or load_json(six_dir / "queries.json") != queries
    ):
        raise ValueError("Original six methods used different frozen source/query inputs")
    originals = read_rows(six_dir / "rankings.jsonl")
    validate_rankings(originals, queries, units, SIX_METHODS)
    rows, versions = list(originals), {"six_method_identity": six_manifest["identity"]}
    parent_dir = root / "outputs/experiments/planned_hybrid_v1"
    parent, _ = verify_bundle(parent_dir)
    parent_rows = read_rows(parent_dir / "results.jsonl")
    validate_rankings(parent_rows, queries, units, ["planned_hybrid"], parent["identity"])
    rows.extend(parent_rows)
    rows.extend(
        {
            **r,
            "method": NO_MMR_METHOD,
            "source_ids": r["without_diversity_source_ids"],
            "ranked_sources": [],
        }
        for r in parent_rows
    )
    versions["planned_hybrid_v1"] = parent["identity"]
    for directory in (
        "anchored_hybrid_v2",
        "guarded_hybrid_v3",
        "guarded_hybrid_v4",
        "semantic_guarded_hybrid_v5",
    ):
        folder = root / "outputs/experiments" / directory
        manifest, _ = verify_bundle(folder)
        if (
            load_json(folder / "corpus.json") != corpus
            or load_json(folder / "queries.json") != queries
        ):
            raise ValueError("Historical ablation used different source/query inputs")
        records = read_rows(folder / "results.jsonl")
        methods = [v["method"] for v in manifest["config"]["variants"]]
        validate_rankings(records, queries, units, methods, manifest["identity"])
        rows.extend(records)
        versions[directory] = manifest["identity"]
        if manifest["parent_identity"] != parent["identity"] or manifest[
            "parent_artifacts_sha256"
        ] != file_hash(parent_dir / "artifacts.json"):
            raise ValueError("A historical ablation changed its frozen parent")
        if directory == "semantic_guarded_hybrid_v5":
            v5_primary = manifest["config"]["primary_candidate"]
            v5_manifest = manifest
            for path, pin in manifest["input_artifacts_sha256"].items():
                if file_hash(experiment_path(root, path) / "artifacts.json") != pin:
                    raise ValueError("Semantic v5 input artifacts changed")
    native_rows, native_pins, execution = load_native(
        root, inputs_dir, queries, corpus, units, flag_dir, neo4j_path, pageindex_dir, worker_inputs
    )
    rows.extend(native_rows)
    page_manifest = load_json(Path(pageindex_dir) / "manifest.json")
    page_prior_alias = None
    if page_manifest["kind"] == "native_pageindex_adaptive_strict_cardinality_ablation":
        page_prior_alias = "pageindex_tree_adapter_v3_pre_cardinality"
        prior_records = read_rows(Path(pageindex_dir) / "parent_results.jsonl")
        validate_native(
            prior_records, queries, units, NATIVE_METHODS[2], page_manifest["parent_identity"]
        )
        rows.extend({**r, "method": page_prior_alias} for r in prior_records)
    if v5_manifest["native_identity"] != native_pins[NATIVE_METHODS[0]]["manifest_identity"]:
        raise ValueError("Semantic v5 imported a different native reranker run")
    methods = list(dict.fromkeys(r["method"] for r in rows))
    validate_rankings(rows, queries, units, methods)
    if preferred not in {*methods, "auto"}:
        raise ValueError("The requested seventh method is unavailable")
    if verify_files(inputs_dir) != input_pins:
        raise ValueError("Common inputs changed before reference scoring")
    if (
        file_hash(Path(flag_dir) / "artifacts.json")
        != native_pins[NATIVE_METHODS[0]]["artifacts_sha256"]
        or file_hash(Path(pageindex_dir) / "artifacts.json")
        != native_pins[NATIVE_METHODS[2]]["artifacts_sha256"]
        or file_hash(neo4j_path) != native_pins[NATIVE_METHODS[1]]["results_sha256"]
    ):
        raise ValueError("Native worker results changed before reference scoring")
    docling_dir = root / "outputs/experiments/docling_structure_audit_v1"
    docling_manifest, _ = verify_bundle(docling_dir)
    docling_summary = load_json(docling_dir / "summary.json")
    if (
        docling_manifest["corpus_sha256"] != file_hash(inputs_dir / "corpus.json")
        or docling_summary["original_corpus_changed"] is not False
    ):
        raise ValueError("The separate parsing audit changed the comparison corpus")
    # This is the first reference read, after every real worker inventory and
    # original source mapping has been validated and frozen above.
    reference_path = Path(
        reference_path
        or root / "outputs/experiments/source_literal_retrieval_v1/frozen_inputs.json"
    )
    if file_hash(reference_path) != six_manifest["references_sha256"]:
        raise ValueError("Engineering source reference version differs")
    references = load_json(reference_path)
    scored = evaluate(rows, queries, units, references)
    metrics = summarize(scored)
    preferred, promotion = select_seventh(metrics, v5_primary, preferred)
    main = [*SIX_METHODS, preferred, *NATIVE_METHODS]
    if len(main) != len(set(main)) or len(main) != 10:
        raise ValueError("The ten-method main inventory is invalid")
    budget_rows, budget_metrics = evidence_costs(rows, units, patients)
    all_costs = costs(rows, execution)
    summary = {
        "main_methods": main,
        "preferred_seventh_method": preferred,
        "seventh_method_promotion_gate": promotion,
        "method_count": 10,
        "main_ranking_records": len(queries) * 10,
        "all_ranking_records": len(rows),
        "module_queries": len(queries),
        "cases": len(patients),
        "main_metrics": [m for name in main for m in metrics if m["method"] == name],
        "historical_and_ablation_metrics": [m for m in metrics if m["method"] not in main],
        "cohorts": {
            c: summarize([r for r in scored if r["cohort"] == c])
            for c in ("engineering", "complex_validation")
        },
        "diseases": {
            module: summarize([r for r in scored if r["module"] == module])
            for module in sorted({q["module"] for q in queries})
        },
        "paired_top5": {m: paired_changes(scored, "hybrid", m) for m in main if m != "hybrid"},
        "paired_top10": {m: top10_changes(scored, "hybrid", m) for m in main if m != "hybrid"},
        "evidence_budget_metrics": budget_metrics,
        "execution_costs": all_costs,
        "native_execution": execution,
        "docling_structure_audit": docling_summary,
        "pageindex_recovery_lineage": execution[NATIVE_METHODS[2]].get("recovery_lineage"),
        "pageindex_cardinality_comparison": (
            {
                "before": page_prior_alias,
                "after": NATIVE_METHODS[2],
                "metrics": [
                    m for m in metrics if m["method"] in {page_prior_alias, NATIVE_METHODS[2]}
                ],
                "paired_top5": paired_changes(scored, page_prior_alias, NATIVE_METHODS[2]),
                "paired_top10": top10_changes(scored, page_prior_alias, NATIVE_METHODS[2]),
                "interpretation": "Adaptive output-contract ablation on the same selected native branches and candidate originals; no unseen evaluation claim.",
            }
            if page_prior_alias
            else None
        ),
        "report_model_calls": 0,
        "judge_calls": 0,
        "production_change": False,
        "interpretation": "Engineering reference-source coverage on observed development fixtures, not clinical or fitness-judgment accuracy. Previously observed complex validation cases are not a sealed holdout. Failed attempted queries retain empty results; unexecuted methods cannot be shown as successful or assigned invented zero recall.",
        "framework_boundaries": {
            "docling": "Separate parsing audit; native reranking uses the unchanged frozen 94-source corpus. No parser-caused recall gain is claimed.",
            "neo4j": "Native HybridCypherRetriever plus first-party literal clause/condition/exception graph navigation; engineering anchors await clinical review.",
            "pageindex": "Native PageIndex hierarchical indexing plus a first-party bounded local-model navigator, not PageIndex native chat retrieval.",
        },
    }
    data = {
        "kind": "ten_route_frozen_retrieval_report",
        "input_artifacts_sha256": file_hash(inputs_dir / "artifacts.json"),
        "source_versions": versions,
        "native_versions": native_pins,
        "docling_audit_artifacts_sha256": file_hash(docling_dir / "artifacts.json"),
        "references_sha256": file_hash(reference_path),
        "reporter_sha256": file_hash(__file__),
        "references_opened_after_complete_worker_inventories": True,
        "preferred_seventh_method": preferred,
    }
    output.mkdir(parents=True)
    for name, value in (
        ("manifest.json", {**data, "identity": digest(data), "production_change": False}),
        ("summary.json", summary),
        ("corpus.json", corpus),
        ("queries.json", queries),
        ("retrieval_metrics.json", scored),
        ("case_evidence_budgets.json", budget_rows),
        ("paired_top5.json", summary["paired_top5"]),
        ("paired_top10.json", summary["paired_top10"]),
        ("pageindex_recovery_lineage.json", summary["pageindex_recovery_lineage"]),
        ("docling_structure_audit.json", docling_summary),
        ("pageindex_cardinality_comparison.json", summary["pageindex_cardinality_comparison"]),
    ):
        write_json(output / name, value)
    write_csv(output / "summary.csv", summary["main_metrics"])
    write_csv(output / "historical_ablations.csv", summary["historical_and_ablation_metrics"])
    write_csv(output / "evidence_budget_metrics.csv", budget_metrics)
    write_csv(
        output / "query_costs.csv",
        [{k: v for k, v in r.items() if k != "worker_execution"} for r in all_costs],
    )
    (output / "rankings.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False, allow_nan=False) + "\n" for r in rows),
        encoding="utf-8",
    )
    shutil.copyfile(six_dir / "evidence_guide.pdf", output / "evidence_guide.pdf")
    (output / "reporter_source.py").write_bytes(Path(__file__).read_bytes())
    render(output, rows, scored, queries, units, budget_rows, summary)
    write_json(
        output / "artifacts.json", {p.name: file_hash(p) for p in output.iterdir() if p.is_file()}
    )
    return summary


def render(output, rows, scored, queries, units, budgets, summary):
    from html import escape

    def pct(value):
        return "Not labeled" if value is None else f"{value:.2%}"

    def table(metrics):
        return (
            "<table><tr><th>Method</th><th>Completed</th><th>Exact R@5</th><th>Coverage R@5</th><th>Coverage R@10</th><th>Fully covered @5</th></tr>"
            + "".join(
                "<tr><td>"
                + escape(
                    LABELS.get(
                        m["method"],
                        "7 · Guarded hybrid RRF"
                        if m["method"] == summary["preferred_seventh_method"]
                        else m["method"],
                    )
                )
                + "</td><td>"
                + str(m["completed"])
                + "/"
                + str(m["records"])
                + "</td><td>"
                + pct(m["exact_recall_5"])
                + "</td><td>"
                + pct(m["coverage_recall_5"])
                + "</td><td>"
                + pct(m["coverage_recall_10"])
                + "</td><td>"
                + str(m["fully_covered_5"])
                + "/"
                + str(m["labeled_scopes"])
                + "</td></tr>"
                for m in metrics
            )
            + "</table>"
        )

    html = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ten retrieval routes | Occupational Fitness Platform</title><style>body{font:14px/1.65 Arial,sans-serif;color:#243748;background:#f4f6f8;max-width:1460px;margin:32px auto;padding:24px}main{background:white;border:1px solid #dce3ea;border-radius:8px;padding:30px}h1{font-size:30px}h2{font-size:22px}section{border-top:1px solid #dce3ea;margin-top:26px;padding-top:18px}table{border-collapse:collapse;width:100%}th,td{padding:9px;text-align:left;border-bottom:1px solid #dce3ea}label{display:inline-block;margin:8px 16px 8px 0}select{padding:8px;margin-left:8px;max-width:340px}.compare{display:grid;grid-template-columns:1fr 1fr;gap:20px}.panel{padding:20px;border:1px solid #dce3ea;border-radius:6px;min-width:0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.65 Consolas,monospace;background:#f5f8fa;padding:14px}details{padding:9px 0;border-bottom:1px solid #e1e7ec}summary{cursor:pointer}.muted{color:#607386}.notice{background:#eef3f7;padding:16px}a{color:#225b83}.error{color:#9a451d}@media(max-width:850px){.compare{grid-template-columns:1fr}body{padding:10px}main{padding:18px}}</style><main><small>OCCUPATIONAL FITNESS PLATFORM · RETRIEVAL VALIDATION</small><h1>Ten independent retrieval routes</h1>"""
    html += (
        "<p>"
        + escape(summary["interpretation"])
        + "</p><p>33 shared cases · 77 frozen module queries · 94 unchanged original-source units · No judgment calls made by this report.</p><section><h2>Main comparison</h2><p>Coverage includes verified original-text containment. Exact source-ID recall is separate. All main methods have a full attempted query inventory; failures remain in their denominators.</p>"
        + table(summary["main_metrics"])
        + "</section>"
    )
    html += (
        "<section><h2>Framework boundaries</h2>"
        + "".join(
            "<p><strong>" + escape(k.title()) + ":</strong> " + escape(v) + "</p>"
            for k, v in summary["framework_boundaries"].items()
        )
        + "</section>"
    )
    html += (
        "<section><h2>Seventh-method development decision</h2><pre>"
        + escape(json.dumps(summary.get("seventh_method_promotion_gate", {}), indent=2))
        + "</pre><p>The semantic variants remain separate observed-development ablations. Their scores do not justify promotion unless both preset gates pass.</p></section>"
    )
    if summary.get("pageindex_cardinality_comparison"):
        lineage = summary["pageindex_recovery_lineage"]
        html += (
            "<section><h2>PageIndex candidate and output cardinality</h2><p>A completed query can still have fewer than ten original results. The strict-cardinality ablation holds the actual branch pools fixed and adds "
            + str(lineage["new_strict_actual_model_calls"])
            + " final-ranking calls. Earlier imported calls and separate development calls retain their own accounting. No unavailable originals are fabricated to fill ten slots.</p><details><summary>Actual pools, return counts, failures and model costs</summary><pre>"
            + escape(json.dumps(lineage, indent=2))
            + "</pre></details><details><summary>Same-query v3 versus strict v4 metrics and regressions</summary><pre>"
            + escape(json.dumps(summary["pageindex_cardinality_comparison"], indent=2))
            + "</pre></details></section>"
        )
    html += (
        "<section><h2>Cohorts and disease groups</h2>"
        + "".join(
            "<details><summary>"
            + escape(kind + ": " + name)
            + "</summary>"
            + table([m for m in records if m["method"] in summary["main_methods"]])
            + "</details>"
            for kind, groups in [("Cohort", summary["cohorts"]), ("Disease", summary["diseases"])]
            for name, records in groups.items()
        )
        + "</section>"
    )
    html += (
        '<section><h2>Compare the same query and original evidence</h2><label>Case<select id="case"></select></label><label>Disease<select id="module"></select></label><label>Method<select id="method">'
        + "".join(
            '<option value="'
            + escape(m, quote=True)
            + '">'
            + escape(LABELS.get(m, m))
            + "</option>"
            for m in dict.fromkeys(r["method"] for r in rows)
        )
        + '</select></label><p id="status" class="muted"></p><div id="comparison"></div></section>'
    )
    html += (
        "<section><h2>Paired changes against Hybrid RRF</h2><p>Counts describe the same queries and source coverage, not clinical judgment changes. Open the paired JSON files for the exact case and disease.</p><table><tr><th>Method</th><th>Top5 improved</th><th>Top5 regressed</th><th>Top5 unchanged</th><th>Top10 improved</th><th>Top10 regressed</th></tr>"
        + "".join(
            "<tr><td>"
            + escape(LABELS.get(method, method))
            + "</td>"
            + "".join(
                "<td>"
                + str(summary.get(key, {}).get(method, {}).get("counts", {}).get(state, 0))
                + "</td>"
                for key, state in (
                    ("paired_top5", "improved"),
                    ("paired_top5", "regressed"),
                    ("paired_top5", "unchanged"),
                    ("paired_top10", "improved"),
                    ("paired_top10", "regressed"),
                )
            )
            + "</tr>"
            for method in summary.get("main_methods", [])
            if method != "hybrid"
        )
        + "</table></section>"
    )
    html += (
        "<section><h2>Historical runs and predefined ablations</h2><details><summary>Preserved separately from the ten main routes</summary>"
        + table(summary["historical_and_ablation_metrics"])
        + "</details></section><section><h2>Execution, cost and failures</h2><p>Cached CPU ranking, native cross-encoder scoring, native graph traversal and model-based tree navigation have different costs. Missing timing values are unavailable, not zero. Context allocation is replayed with the unchanged five-original/9000-byte policy.</p><details><summary>Native execution summaries</summary><pre>"
        + escape(json.dumps(summary["native_execution"], indent=2))
        + "</pre></details><details><summary>Evidence budget metrics</summary><pre>"
        + escape(json.dumps(summary["evidence_budget_metrics"], indent=2))
        + "</pre></details><details><summary>Retained failed query attempts</summary><pre>"
        + escape(
            json.dumps(
                [
                    {
                        k: v
                        for k, v in r.items()
                        if k in {"query_id", "case_id", "method", "error", "status"}
                    }
                    for r in rows
                    if r["status"] == "failed"
                ],
                indent=2,
            )
        )
        + "</pre></details><details><summary>PageIndex strict parent failures and explicit recovery lineage</summary><p>The parent attempts retain their original failed status. The recovery imports 146 actual calls and adds only eight original-ranking calls; these are not 154 new calls.</p><pre>"
        + escape(json.dumps(summary.get("pageindex_recovery_lineage"), indent=2))
        + "</pre></details><details><summary>Separate native Docling structure audit</summary><pre>"
        + escape(json.dumps(summary.get("docling_structure_audit"), indent=2))
        + "</pre></details><details><summary>Recorded retrieval costs for every route and ablation</summary><pre>"
        + escape(json.dumps(summary.get("execution_costs", []), indent=2))
        + "</pre></details></section>"
    )
    html += (
        "<section><h2>Audit files</h2><p>"
        + " · ".join(
            '<a href="' + name + '">' + label + "</a>"
            for name, label in [
                ("summary.csv", "Main metrics CSV"),
                ("historical_ablations.csv", "Historical ablations CSV"),
                ("query_costs.csv", "Recorded query costs"),
                ("retrieval_metrics.json", "All scored records"),
                ("rankings.jsonl", "Raw rankings and source traces"),
                ("case_evidence_budgets.json", "Actual case-level evidence allocation"),
                ("paired_top5.json", "Paired Top5 changes"),
                ("paired_top10.json", "Paired Top10 changes"),
                (
                    "pageindex_recovery_lineage.json",
                    "PageIndex preserved failures and recovery calls",
                ),
                ("docling_structure_audit.json", "Separate Docling structure audit"),
                (
                    "pageindex_cardinality_comparison.json",
                    "PageIndex v3 versus strict v4 comparison",
                ),
                ("manifest.json", "Frozen version pins"),
                ("evidence_guide.pdf", "Guideline PDF"),
            ]
        )
        + "</p></section>"
    )
    data = json.dumps(
        {
            "rows": rows,
            "scored": scored,
            "queries": queries,
            "units": units,
            "budgets": budgets,
            "preferred": summary["preferred_seventh_method"],
        },
        ensure_ascii=False,
        allow_nan=False,
    ).replace("<", "\\u003c")
    html += '<script id="report-data" type="application/json">' + data + "</script>"
    html += """<script>
const d=JSON.parse(document.getElementById('report-data').textContent),$=id=>document.getElementById(id),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),pct=v=>v==null?'Not labeled':(v*100).toFixed(2)+'%';
const find=(qid,m)=>d.rows.find(r=>r.query_id===qid&&r.method===m),score=(qid,m)=>d.scored.find(r=>r.query_id===qid&&r.method===m);
function options(el,vals){const old=el.value;el.innerHTML=vals.map(v=>'<option value="'+esc(v)+'">'+esc(v)+'</option>').join('');if(vals.includes(old))el.value=old}
options($('case'),[...new Set(d.queries.map(q=>q.case_id))]);$('method').value=d.preferred;
function panel(q,m){const r=find(q.query_id,m),s=score(q.query_id,m),b=d.budgets.find(x=>x.case_id===q.case_id&&x.method===m);return '<div class="panel"><h3>'+esc(m)+'</h3><p>Coverage R@5 '+pct(s.coverage_recall_5)+' · R@10 '+pct(s.coverage_recall_10)+' · Exact R@5 '+pct(s.exact_recall_5)+'</p><p class="'+(r.status==='failed'?'error':'muted')+'">'+esc(r.error||r.status)+'</p>'+r.source_ids.slice(0,10).map((sid,i)=>{const u=d.units[sid];return '<details><summary>'+(i+1)+'. '+esc(sid)+' · '+(i<5?'Top5':'Top10 only')+'</summary><p>Section '+esc(u.section)+' · Printed page '+esc(u.printed_page)+' · <a href="evidence_guide.pdf#page='+Number(u.pdf_page)+'">PDF '+Number(u.pdf_page)+'</a></p><p>Verified contained IDs: '+esc((u.covers_source_ids||[]).join(', ')||'None')+'</p><pre>'+esc(u.evidence_text)+'</pre></details>'}).join('')+'<details><summary>Actual case-level evidence budget</summary><pre>'+esc(JSON.stringify(b,null,2))+'</pre></details><details><summary>Method execution and source-path trace</summary><pre>'+esc(JSON.stringify(r,null,2))+'</pre></details></div>'}
function render(){const c=$('case').value,m=$('method').value;options($('module'),d.queries.filter(q=>q.case_id===c).map(q=>q.module));const q=d.queries.find(q=>q.case_id===c&&q.module===$('module').value),a=score(q.query_id,'hybrid'),b=score(q.query_id,m);$('status').textContent='Same frozen patient/query · Coverage R@5: '+pct(a.coverage_recall_5)+' → '+pct(b.coverage_recall_5)+' · R@10: '+pct(a.coverage_recall_10)+' → '+pct(b.coverage_recall_10);$('comparison').innerHTML='<details><summary>Frozen query</summary><pre>'+esc(q.query)+'</pre></details><div class="compare">'+panel(q,'hybrid')+panel(q,m)+'</div>'}
['case','module','method'].forEach(id=>$(id).addEventListener('change',render));render();
</script></main></html>"""
    (Path(output) / "index.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inputs", type=Path, default=Path("outputs/experiments/retrieval_extensions_inputs_v1")
    )
    parser.add_argument(
        "--flag", type=Path, default=Path("outputs/experiments/native_flag_rerank_v1")
    )
    parser.add_argument(
        "--neo4j",
        type=Path,
        default=Path("outputs/experiments/native_neo4j_retrieval_v1/results.json"),
    )
    parser.add_argument(
        "--pageindex", type=Path, default=Path("outputs/experiments/native_pageindex_retrieval_v4")
    )
    parser.add_argument("--flag-input", type=Path)
    parser.add_argument("--neo4j-input", type=Path)
    parser.add_argument("--pageindex-request", type=Path)
    parser.add_argument("--preferred", default=DEFAULT_PREFERRED)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    worker_paths = (
        args.flag_input or args.inputs / "flag_input.json",
        args.neo4j_input or args.inputs / "neo4j_input.json",
        args.pageindex_request
        or Path(
            "outputs/experiments/retrieval_extension_protocols_v4/pageindex_strict_request.json"
        ),
    )
    result = build(
        Path.cwd(),
        args.inputs,
        args.flag,
        args.neo4j,
        args.pageindex,
        args.output,
        dict(zip(NATIVE_METHODS, worker_paths, strict=True)),
        args.preferred,
    )
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "method_count",
                    "main_ranking_records",
                    "all_ranking_records",
                    "main_metrics",
                )
            },
            indent=2,
        )
    )
