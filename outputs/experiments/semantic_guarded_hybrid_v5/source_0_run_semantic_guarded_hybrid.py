"""Freeze native semantic/no-MMR ablations, then score them in a separate step.

The ranking step never loads expected source IDs or patient outcome labels.
The report step opens engineering references only after the 154-record freeze.
Native Flag scores are reused; this command makes no model calls.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from time import perf_counter

from occupational_fitness_rag.evaluation.anchored_hybrid import rank_channels
from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.evaluation.semantic_guarded_hybrid import rank_semantic
from occupational_fitness_rag.provenance import digest, write_json
from tools import flag_embedding_extension_worker as native
from tools.report_anchored_hybrid import (
    NO_MMR_METHOD,
    SIX_METHODS,
    evidence_costs,
    read_rows,
    render,
    validate_rankings,
    verify_bundle,
    write_csv,
)
from tools.report_guarded_hybrid import top10_changes
from tools.report_planned_hybrid import evaluate, paired_changes, summarize

V3 = "planned_hybrid_v3_guarded_30"
VARIANTS = (
    {"method": "planned_hybrid_v5_semantic_025", "semantic_weight": 0.25},
    {"method": "planned_hybrid_v5_semantic_050", "semantic_weight": 0.50},
)
PRIMARY = VARIANTS[0]["method"]
SOURCES = (
    "tools/run_semantic_guarded_hybrid.py",
    "src/occupational_fitness_rag/evaluation/semantic_guarded_hybrid.py",
    "src/occupational_fitness_rag/evaluation/guarded_hybrid.py",
    "src/occupational_fitness_rag/evaluation/anchored_hybrid.py",
    "tools/flag_embedding_extension_worker.py",
)


def json_at(directory, name):
    return json.loads((Path(directory) / name).read_bytes())


def load_frozen(root, v3_dir, flag_dir, inputs_dir):
    """Verify actual native candidates, scores and original anchor rank order."""
    v3, _ = verify_bundle(v3_dir)
    flag, _ = verify_bundle(flag_dir)
    inputs, _ = verify_bundle(inputs_dir)
    corpus, queries = [json_at(v3_dir, name) for name in ("corpus.json", "queries.json")]
    job_path = inputs_dir / "flag_input.json"
    job = json_at(inputs_dir, "flag_input.json")
    units = native.validate(job)
    if (
        len(queries) != 77
        or len(units) != 94
        or job["corpus"] != corpus
        or job["queries"] != queries
        or json_at(inputs_dir, "corpus.json") != corpus
        or json_at(inputs_dir, "queries.json") != queries
        or flag["input_sha256"] != file_hash(job_path)
        or flag["parent_identity"] != inputs["identity"]
        or flag.get("labels_loaded") is not False
        or file_hash(flag_dir / "worker_source.py") != flag["source_sha256"]
    ):
        raise ValueError("Native corpus, query, worker or input identity differs")
    all_prior = read_rows(v3_dir / "results.jsonl")
    prior = [row for row in all_prior if row["method"] == V3]
    observed = read_rows(flag_dir / "results.jsonl")
    validate_rankings(prior, queries, units, [V3], v3["identity"])
    validate_rankings(observed, queries, units, [native.METHOD], flag["identity"])
    native.validate_cached_rows(observed, job, flag["identity"])
    previous = {row["query_id"]: row for row in prior}
    calls = {row["query_id"]: row for row in observed}
    channels = json_at(v3_dir, "channels.json")
    for query in queries:
        qid = query["query_id"]
        original = rank_channels(
            channels[qid], units, {"policy": "anchor_only", "candidate_k": 20, "sensitivity_k": 20}
        )["source_ids"]
        row = calls[qid]
        if row["status"] == "completed":
            trace = row["candidate_trace"]
            ids = [s["source_id"] for s in trace]
            scores = [s["native_score"] for s in trace]
            order = sorted(range(len(ids)), key=lambda i: (-scores[i], i))[:10]
            if (
                ids != job["candidates"][qid]
                or ids != original
                or row["source_ids"] != [ids[i] for i in order]
                or row["ranked_sources"]
                != [
                    {"source_id": ids[i], "score": scores[i], "original_rrf_rank": i + 1}
                    for i in order
                ]
                or row["native_scoring_attempted"] is not True
                or row["returned_source_text_modified"] is not False
            ):
                raise ValueError("Native scores or candidate ranks differ from actual original RRF")
    execution = json_at(flag_dir, "summary.json")
    if execution["recorded"] != 77 or execution["native_scoring_calls"] != 77:
        raise ValueError("The native scoring run is not the complete frozen 77-call experiment")
    pins = {
        str(d.relative_to(root)): file_hash(d / "artifacts.json")
        for d in (v3_dir, flag_dir, inputs_dir)
    }
    return v3, flag, corpus, queries, units, previous, calls, pins


def run(root, output, v3_dir, flag_dir, inputs_dir):
    root = Path(root).resolve()
    output, v3_dir, flag_dir, inputs_dir = [
        (root / Path(p)).resolve() for p in (output, v3_dir, flag_dir, inputs_dir)
    ]
    if output.exists() or not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Use a fresh independent ranking directory")
    v3, flag, corpus, queries, units, prior, calls, pins = load_frozen(
        root, v3_dir, flag_dir, inputs_dir
    )
    config = {
        "primary_candidate": PRIMARY,
        "variants": list(VARIANTS),
        "formula": "0.85*((1-w)*61/(60+prior_rank)+w*native_sigmoid)+0.15*novel_corpus_atoms/M",
        "prior_rank": "v3 Top10 rank; otherwise original query RRF Top20 rank",
        "native_missing_policy": "explicit zero, not a new native call or inferred clinical truth",
        "source_budget": 10,
        "guard": "full actual v3 Top10 original-source footprint",
        "mmr": False,
        "selection_stage": "adaptive hypothesis after v3/v4 development results; prespecified before native Flag performance scoring; not sealed holdout",
    }
    source_pins = {name: file_hash(root / name) for name in SOURCES}
    data = {
        "kind": "native_semantic_blend_with_v3_original_coverage_guard",
        "config": config,
        "parent_identity": v3["parent_identity"],
        "parent_artifacts_sha256": v3["parent_artifacts_sha256"],
        "v3_identity": v3["identity"],
        "native_identity": flag["identity"],
        "input_artifacts_sha256": pins,
        "sources": source_pins,
        "query_ids": [q["query_id"] for q in queries],
        "labels_available_to_ranker": False,
    }
    identity = digest(data)
    output.mkdir(parents=True)
    write_json(output / "manifest.json", {**data, "identity": identity, "production_change": False})
    write_json(output / "corpus.json", corpus)
    write_json(output / "queries.json", queries)
    write_json(output / "config.json", config)
    rows = []
    for query in queries:
        qid = query["query_id"]
        for variant in VARIANTS:
            start = perf_counter()
            row = {k: query[k] for k in ("query_id", "case_id", "module")}
            row.update(
                method=variant["method"],
                experiment_identity=identity,
                query_sha256=query["query_audit"]["query_sha256"],
            )
            try:
                result = rank_semantic(prior[qid], calls[qid], units, variant["semantic_weight"])
                result["diagnostics"]["original_rrf_source_ids"] = prior[qid]["diagnostics"][
                    "original_rrf_source_ids"
                ]
                row.update(
                    status="completed",
                    **result,
                    original_text_hashes={
                        sid: units[sid]["text_sha256"] for sid in result["source_ids"]
                    },
                )
            except Exception as exc:
                row.update(status="failed", source_ids=[], error=f"{type(exc).__name__}: {exc}")
            row["ranking_seconds_excluding_import_reconstruction"] = perf_counter() - start
            rows.append(row)
    if (
        any(
            file_hash(root / directory / "artifacts.json") != pin for directory, pin in pins.items()
        )
        or {n: file_hash(root / n) for n in SOURCES} != source_pins
    ):
        raise ValueError("A frozen input or source changed during semantic ranking")
    validate_rankings(rows, queries, units, [v["method"] for v in VARIANTS], identity)
    (output / "results.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    summary = {
        "identity": identity,
        "planned": 154,
        "recorded": len(rows),
        "completed": sum(r["status"] == "completed" for r in rows),
        "failed": sum(r["status"] == "failed" for r in rows),
        "guarded_rankings": sum(r["status"] == "completed" for r in rows),
        "guard_violations": sum(
            not r["diagnostics"]["protected_coverage_retained"]
            for r in rows
            if r["status"] == "completed"
        ),
        "actual_new_model_calls": 0,
        "reused_native_scoring_calls": 77,
        "native_missing_candidate_scores": sum(
            len(r["diagnostics"]["native_missing_source_ids"])
            for r in rows
            if r["status"] == "completed"
        ),
        "labels_loaded": False,
        "production_change": False,
    }
    write_json(output / "summary.json", summary)
    for i, name in enumerate(SOURCES):
        shutil.copyfile(root / name, output / (f"source_{i}_" + Path(name).name))
    write_json(
        output / "artifacts.json",
        {
            p.name: file_hash(p)
            for p in output.iterdir()
            if p.is_file() and p.name != "artifacts.json"
        },
    )
    return summary


def report(root, ranking_dir, output):
    """Open references only after complete, source-bound rankings were frozen."""
    root = Path(root).resolve()
    ranking_dir, output = [(root / Path(p)).resolve() for p in (ranking_dir, output)]
    if output.exists() or not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Use a fresh comparison report directory")
    manifest, _ = verify_bundle(ranking_dir)
    corpus, queries = [json_at(ranking_dir, n) for n in ("corpus.json", "queries.json")]
    units = {u["source_id"]: u for u in corpus["units"]}
    new = read_rows(ranking_dir / "results.jsonl")
    validate_rankings(new, queries, units, [v["method"] for v in VARIANTS], manifest["identity"])
    if (
        len(new) != 154
        or manifest["config"]["variants"] != list(VARIANTS)
        or manifest["config"]["primary_candidate"] != PRIMARY
        or manifest["labels_available_to_ranker"] is not False
    ):
        raise ValueError("The prespecified two-variant complete freeze differs")
    six_dir = root / "outputs/experiments/six_method_retrieval_v2"
    six, _ = verify_bundle(six_dir, six=True)
    rows = read_rows(six_dir / "rankings.jsonl")
    validate_rankings(rows, queries, units, SIX_METHODS)
    compare_dirs = [
        root / "outputs/experiments" / name
        for name in (
            "planned_hybrid_v1",
            "anchored_hybrid_v2",
            "guarded_hybrid_v3",
            "guarded_hybrid_v4",
            "native_flag_rerank_v1",
        )
    ]
    pins = {
        str(six_dir.relative_to(root)): file_hash(six_dir / "artifacts.json"),
        str(ranking_dir.relative_to(root)): file_hash(ranking_dir / "artifacts.json"),
    }
    for directory in compare_dirs:
        preserved, _ = verify_bundle(directory)
        pins[str(directory.relative_to(root))] = file_hash(directory / "artifacts.json")
        records = read_rows(directory / "results.jsonl")
        methods = list(dict.fromkeys(r["method"] for r in records))
        validate_rankings(records, queries, units, methods, preserved["identity"])
        rows.extend(records)
        if directory.name == "planned_hybrid_v1":
            parent = preserved
            ablated = [
                {**r, "method": NO_MMR_METHOD, "source_ids": r["without_diversity_source_ids"]}
                for r in records
            ]
            for row in ablated:
                row.pop("ranked_sources", None)
                row.pop("original_text_hashes", None)
            rows.extend(ablated)
    rows.extend(new)
    patients_path = root / parent["config"]["preparation_dir"] / "patients.json"
    if file_hash(patients_path) != parent["imported"]["preparation"]["artifacts"]["patients.json"]:
        raise ValueError("Frozen patient facts changed")
    patients = json.loads(patients_path.read_bytes())
    budgets, costs = evidence_costs(rows, units, patients)
    references_path = root / "outputs/experiments/source_literal_retrieval_v1/frozen_inputs.json"
    if file_hash(references_path) != six["references_sha256"]:
        raise ValueError("Engineering source-reference labels changed")
    # The immutable 154-record label-free ranking bundle now precedes scoring.
    scored = evaluate(rows, queries, units, json.loads(references_path.read_bytes()))
    variants = [v["method"] for v in VARIANTS]
    paired = [
        {"baseline": baseline, "candidate": method, **paired_changes(scored, baseline, method)}
        for baseline in ("hybrid", V3)
        for method in variants
    ]
    summary = {
        "primary_candidate": PRIMARY,
        "predefined_variants": [
            m
            for m in dict.fromkeys(r["method"] for r in rows)
            if m not in {*SIX_METHODS, "planned_hybrid", NO_MMR_METHOD}
        ],
        "cases": len(patients),
        "module_queries": len(queries),
        "new_ablation_records": len(new),
        "ranking_records": len(rows),
        "metrics": summarize(scored),
        "paired_changes": paired,
        "paired_top10_changes": [
            top10_changes(scored, baseline, method)
            for baseline in ("hybrid", V3)
            for method in variants
        ],
        "cohorts": {
            name: summarize([r for r in scored if r["cohort"] == name])
            for name in ("engineering", "complex_validation")
        },
        "diseases": {
            name: summarize([r for r in scored if r["module"] == name])
            for name in sorted({q["module"] for q in queries})
        },
        "cost_metrics": costs,
        "new_execution": json_at(ranking_dir, "summary.json"),
        "evidence_budget_policy": "Existing documented-module round robin; five whole originals per case, 9000 UTF-8 JSON bytes, no backfill",
        "judgment_calls": 0,
        "production_change": False,
        "interpretation": "Two prespecified native semantic blends, no MMR, protected actual v3 Top10 original-source footprint. All 154 ranks were frozen before native Flag performance labels were opened. These 33 observed development cases are not a sealed holdout. Engineering original-source recall is not clinical accuracy or a demonstrated judgment improvement. Native scores reuse 77 real query/passage scoring calls; no new model inference is performed.",
    }
    output.mkdir(parents=True)
    data = {
        "ranking_identity": manifest["identity"],
        "input_artifacts_sha256": pins,
        "references_sha256": file_hash(references_path),
        "reporter_sha256": file_hash(__file__),
        "production_change": False,
    }
    write_json(output / "manifest.json", {**data, "identity": digest(data)})
    for name, value in (
        ("summary.json", summary),
        ("retrieval_metrics.json", scored),
        ("case_evidence_budgets.json", budgets),
        ("paired_top10_changes.json", summary["paired_top10_changes"]),
    ):
        write_json(output / name, value)
    for name, records in (
        ("summary.csv", summary["metrics"]),
        ("evidence_cost_metrics.csv", costs),
        (
            "cohort_metrics.csv",
            [{"cohort": name, **r} for name, values in summary["cohorts"].items() for r in values],
        ),
        (
            "disease_metrics.csv",
            [{"module": name, **r} for name, values in summary["diseases"].items() for r in values],
        ),
        ("paired_changes.csv", [r for p in paired for r in p["rows"]]),
    ):
        write_csv(output / name, records)
    (output / "rankings.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False, allow_nan=False) + "\n" for r in rows),
        encoding="utf-8",
    )
    shutil.copyfile(six_dir / "evidence_guide.pdf", output / "evidence_guide.pdf")
    shutil.copyfile(__file__, output / "reporter_source.py")
    render(output, rows, queries, units, scored, summary, budgets)
    page = output / "index.html"
    html = page.read_text(encoding="utf-8").replace(
        "Anchored fusion without MMR", "Native semantic fusion with a source-coverage floor"
    )
    html = html.replace(
        "Coverage R@5 '+pct(s.coverage_recall_5)+' · Exact R@5",
        "Coverage R@5 '+pct(s.coverage_recall_5)+' · Coverage R@10 '+pct(s.coverage_recall_10)+' · Exact R@5",
    )
    page.write_text(html, encoding="utf-8")
    write_json(
        output / "artifacts.json",
        {
            p.name: file_hash(p)
            for p in output.iterdir()
            if p.is_file() and p.name != "artifacts.json"
        },
    )
    return {
        "primary_candidate": PRIMARY,
        "metrics": [
            r
            for r in summary["metrics"]
            if r["method"] in {PRIMARY, VARIANTS[1]["method"], V3, "hybrid", native.METHOD}
        ],
        "paired_changes": paired,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("rank", "report"))
    parser.add_argument("--rankings", default="outputs/experiments/semantic_guarded_hybrid_v5")
    parser.add_argument("--output", default="outputs/experiments/semantic_guarded_retrieval_v5")
    parser.add_argument("--v3", default="outputs/experiments/guarded_hybrid_v3")
    parser.add_argument("--flag", default="outputs/experiments/native_flag_rerank_v1")
    parser.add_argument("--inputs", default="outputs/experiments/retrieval_extensions_inputs_v1")
    args = parser.parse_args()
    result = (
        run(Path.cwd(), args.rankings, args.v3, args.flag, args.inputs)
        if args.stage == "rank"
        else report(Path.cwd(), args.rankings, args.output)
    )
    print(json.dumps(result, indent=2))
