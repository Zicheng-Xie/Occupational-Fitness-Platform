"""Compare frozen guarded retrieval with every preserved earlier retrieval arm."""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from html import escape
from pathlib import Path

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.provenance import digest, write_json
from tools.report_anchored_hybrid import (
    NO_MMR_METHOD,
    PARENT_METHOD,
    SIX_METHODS,
    evidence_costs,
    read_rows,
    render,
    validate_rankings,
    verify_bundle,
    write_csv,
)
from tools.report_planned_hybrid import evaluate, paired_changes, summarize


def top10_changes(scored, baseline, candidate):
    index = {(row["query_id"], row["method"]): row for row in scored}
    records = []
    for (qid, method), after in index.items():
        if method != candidate:
            continue
        before = index[(qid, baseline)]
        left, right = before["coverage_recall_10"], after["coverage_recall_10"]
        delta = None if left is None or right is None else right - left
        change = (
            "unlabeled"
            if delta is None
            else "improved"
            if delta > 1e-12
            else "regressed"
            if delta < -1e-12
            else "unchanged"
        )
        records.append(
            {
                "query_id": qid,
                "case_id": after["case_id"],
                "module": after["module"],
                "baseline": baseline,
                "candidate": candidate,
                "coverage_change": change,
                "coverage_recall_10_delta": delta,
            }
        )
    return {
        "baseline": baseline,
        "candidate": candidate,
        "counts": dict(Counter(row["coverage_change"] for row in records)),
        "rows": records,
    }


def guard_audit(rows, original, units):
    """Check the coverage floor against actual original-RRF ranks, without labels."""
    anchors = {row["query_id"]: row["source_ids"] for row in original if row["method"] == "hybrid"}

    def footprint(ids):
        return {
            sid for source in ids for sid in [source, *units[source].get("covers_source_ids", [])]
        }

    records = []
    for row in rows:
        if row["status"] != "completed":
            continue
        diagnostics = row["diagnostics"]
        baseline = anchors[row["query_id"]]
        if diagnostics["original_rrf_source_ids"] != baseline:
            raise ValueError("Guarded method's anchor ranks differ from the actual original hybrid")
        protected = footprint(baseline)
        returned = footprint(row["source_ids"])
        retained = protected <= returned
        if diagnostics["guard_enabled"] and (
            not retained or not diagnostics["protected_coverage_retained"]
        ):
            raise ValueError("A guarded ranking lost an actual original-RRF source footprint")
        records.append(
            {
                "query_id": row["query_id"],
                "case_id": row["case_id"],
                "module": row["module"],
                "method": row["method"],
                "guard_enabled": diagnostics["guard_enabled"],
                "protected_coverage_retained": retained,
                "protected_original_footprint": sorted(protected),
                "missing_original_atoms": sorted(protected - returned),
                "guard_fallback_reason": diagnostics["guard_fallback_reason"],
            }
        )
    return records


def build(root, six_dir, parent_dir, prior_dir, new_dir, reference_path, output):
    root = Path(root).resolve()
    six_dir, parent_dir, prior_dir, new_dir, reference_path, output = [
        (root / Path(p)).resolve()
        for p in (six_dir, parent_dir, prior_dir, new_dir, reference_path, output)
    ]
    if output.exists() or not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Use a fresh separate report directory")
    bundles = [
        verify_bundle(directory, six=index == 0)
        for index, directory in enumerate((six_dir, parent_dir, prior_dir, new_dir))
    ]
    (six, _), (parent, _), (prior, _), (new, _) = bundles
    corpus, queries = [
        json.loads((new_dir / name).read_bytes()) for name in ("corpus.json", "queries.json")
    ]
    if len(queries) != 77:
        raise ValueError("Keep the complete shared 77-query protocol")
    for directory in (six_dir, parent_dir, prior_dir):
        for name, content in (("corpus.json", corpus), ("queries.json", queries)):
            if json.loads((directory / name).read_bytes()) != content:
                raise ValueError("A preserved method uses different frozen corpus or queries")
    for manifest in (prior, new):
        if (
            manifest["parent_identity"] != parent["identity"]
            or manifest["parent_artifacts_sha256"] != file_hash(parent_dir / "artifacts.json")
            or manifest.get("labels_available_to_ranker") is not False
            or manifest["query_ids"] != [q["query_id"] for q in queries]
        ):
            raise ValueError("A revision is not bound to the same label-free parent")
    prior_methods = [v["method"] for v in prior["config"]["variants"]]
    variants = [v["method"] for v in new["config"]["variants"]]
    all_methods = [*SIX_METHODS, PARENT_METHOD, NO_MMR_METHOD, *prior_methods, *variants]
    primary = new["config"]["primary_candidate"]
    if len(all_methods) != len(set(all_methods)) or primary not in variants:
        raise ValueError("Every preserved method and predefined new variant needs its own identity")
    units = {u["source_id"]: u for u in corpus["units"]}
    original = read_rows(six_dir / "rankings.jsonl")
    parent_rows = read_rows(parent_dir / "results.jsonl")
    prior_rows = read_rows(prior_dir / "results.jsonl")
    new_rows = read_rows(new_dir / "results.jsonl")
    validate_rankings(original, queries, units, SIX_METHODS)
    validate_rankings(parent_rows, queries, units, [PARENT_METHOD], parent["identity"])
    validate_rankings(prior_rows, queries, units, prior_methods, prior["identity"])
    validate_rankings(new_rows, queries, units, variants, new["identity"])
    no_mmr = []
    for row in parent_rows:
        ablated = {
            **row,
            "method": NO_MMR_METHOD,
            "source_ids": row["without_diversity_source_ids"],
            "events": [{"stage": "remove_final_mmr", "parent_method": PARENT_METHOD}],
        }
        ablated.pop("ranked_sources", None)
        ablated.pop("original_text_hashes", None)
        no_mmr.append(ablated)
    validate_rankings(no_mmr, queries, units, [NO_MMR_METHOD])
    rows = [*original, *parent_rows, *no_mmr, *prior_rows, *new_rows]
    audit = guard_audit(new_rows, original, units)
    patient_dir = root / parent["config"]["preparation_dir"]
    expected_patient = parent["imported"]["preparation"]["artifacts"]["patients.json"]
    if file_hash(patient_dir / "patients.json") != expected_patient:
        raise ValueError("Original patient facts changed")
    patients = json.loads((patient_dir / "patients.json").read_bytes())
    if set(patients) != {q["case_id"] for q in queries}:
        raise ValueError("Patient inventory differs from the shared query protocol")
    budgets, costs = evidence_costs(rows, units, patients)
    # Ranking/guard inventories and source scopes are fixed before labels enter.
    if file_hash(reference_path) != six["references_sha256"]:
        raise ValueError("Engineering reference labels changed")
    references = json.loads(reference_path.read_bytes())
    scored = evaluate(rows, queries, units, references)
    baselines = ["hybrid", NO_MMR_METHOD, prior["config"]["primary_candidate"]]
    paired = [
        {
            "baseline": baseline,
            "candidate": candidate,
            **paired_changes(scored, baseline, candidate),
        }
        for baseline in baselines
        for candidate in variants
    ]
    paired10 = [
        top10_changes(scored, baseline, candidate)
        for baseline in baselines
        for candidate in variants
    ]
    summary = {
        "primary_candidate": primary,
        "predefined_variants": variants,
        "preserved_original_methods": list(SIX_METHODS),
        "preserved_parent_methods": [PARENT_METHOD, NO_MMR_METHOD, *prior_methods],
        "ranking_records": len(rows),
        "new_ablation_records": len(new_rows),
        "cases": len(patients),
        "module_queries": len(queries),
        "metrics": summarize(scored),
        "paired_changes": paired,
        "paired_top10_changes": paired10,
        "cohorts": {
            name: summarize([r for r in scored if r["cohort"] == name])
            for name in ("engineering", "complex_validation")
        },
        "diseases": {
            name: summarize([r for r in scored if r["module"] == name])
            for name in sorted({q["module"] for q in queries})
        },
        "new_execution": json.loads((new_dir / "summary.json").read_bytes()),
        "cost_metrics": costs,
        "guard_summary": {
            "rankings": len(audit),
            "guarded_rankings": sum(r["guard_enabled"] for r in audit),
            "guarded_violations": sum(
                r["guard_enabled"] and not r["protected_coverage_retained"] for r in audit
            ),
            "fallbacks": sum(r["guard_fallback_reason"] is not None for r in audit),
        },
        "evidence_budget_policy": "Existing documented-module round robin; five whole original units per case, 9000 UTF-8 JSON bytes, no backfill",
        "judgment_calls": 0,
        "production_change": False,
        "interpretation": "Engineering reference-source recall on observed development fixtures, not clinical or fitness classification accuracy. Wider pools and a corpus-only coverage floor are predefined ablations; the floor preserves actual original-RRF Top10 source coverage, not patient relevance or applicability. All earlier methods and observed regressions are retained. The complex cases have already been observed and are not a sealed holdout.",
    }
    identity = {
        "six_method_identity": six["identity"],
        "parent_identity": parent["identity"],
        "prior_revision_identity": prior["identity"],
        "new_identity": new["identity"],
        "input_artifacts_sha256": {
            str(d.relative_to(root)): file_hash(d / "artifacts.json")
            for d in (six_dir, parent_dir, prior_dir, new_dir)
        },
        "references_sha256": file_hash(reference_path),
        "reporter_sha256": file_hash(__file__),
        "renderer_sha256": file_hash(root / "tools/report_anchored_hybrid.py"),
        "scoring_source_sha256": file_hash(root / "tools/report_planned_hybrid.py"),
        "patient_inputs_sha256": expected_patient,
        "references_opened_after_complete_rank_inventory": True,
    }
    for index, directory in enumerate((six_dir, parent_dir, prior_dir, new_dir)):
        if verify_bundle(directory, six=index == 0)[1] != bundles[index][1]:
            raise ValueError("A frozen artifact inventory changed during scoring")
    output.mkdir(parents=True)
    for name, value in (
        ("manifest.json", {**identity, "identity": digest(identity), "production_change": False}),
        ("summary.json", summary),
        ("retrieval_metrics.json", scored),
        ("paired_changes.json", paired),
        ("paired_top10_changes.json", paired10),
        ("case_evidence_budgets.json", budgets),
        ("guard_audit.json", audit),
    ):
        write_json(output / name, value)
    write_csv(output / "summary.csv", summary["metrics"])
    write_csv(output / "paired_changes.csv", [r for p in paired for r in p["rows"]])
    write_csv(output / "paired_top10_changes.csv", [r for p in paired10 for r in p["rows"]])
    write_csv(output / "guard_audit.csv", audit)
    write_csv(output / "evidence_cost_metrics.csv", costs)
    write_csv(
        output / "cohort_metrics.csv",
        [{"cohort": name, **row} for name, values in summary["cohorts"].items() for row in values],
    )
    write_csv(
        output / "disease_metrics.csv",
        [{"module": name, **row} for name, values in summary["diseases"].items() for row in values],
    )
    for name in ("corpus.json", "queries.json", "config.yaml", "channels.json"):
        shutil.copyfile(new_dir / name, output / name)
    shutil.copyfile(six_dir / "evidence_guide.pdf", output / "evidence_guide.pdf")
    for name, source in (
        ("reporter_source.py", Path(__file__)),
        ("renderer_source.py", root / "tools/report_anchored_hybrid.py"),
        ("scoring_source.py", root / "tools/report_planned_hybrid.py"),
    ):
        shutil.copyfile(source, output / name)
    (output / "rankings.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False, allow_nan=False) + "\n" for r in rows),
        encoding="utf-8",
    )
    render(
        output,
        rows,
        queries,
        units,
        scored,
        {**summary, "predefined_variants": [*variants, *prior_methods]},
        budgets,
    )
    html = (output / "index.html").read_text(encoding="utf-8")
    extra = "<section><h2>Top-10 source-coverage changes</h2><p>The guard was checked against the actual original-RRF ranks before reference scoring. It retains original IDs or verified literal containment within ten returned units.</p><table><tr><th>Candidate</th><th>Baseline</th><th>Improved</th><th>Regressed</th><th>Unchanged</th><th>Unlabeled</th></tr>"
    extra += "".join(
        "<tr><td>"
        + escape(p["candidate"])
        + "</td><td>"
        + escape(p["baseline"])
        + "</td>"
        + "".join(
            "<td>" + str(p["counts"].get(key, 0)) + "</td>"
            for key in ("improved", "regressed", "unchanged", "unlabeled")
        )
        + "</tr>"
        for p in paired10
    )
    extra += '</table><p><a href="paired_top10_changes.csv">Top-10 paired changes</a> · <a href="guard_audit.json">Original-source coverage guard audit</a></p></section>'
    html = html.replace(
        "<h1>Anchored fusion without MMR</h1>", "<h1>Coverage-guarded fusion without MMR</h1>"
    )
    html = html.replace("</header>", "</header>" + extra, 1)
    html = html.replace(
        "+' · Exact R@5 '+pct(s.exact_recall_5)",
        "+' · Coverage R@10 '+pct(s.coverage_recall_10)+' · Exact R@5 '+pct(s.exact_recall_5)",
    )
    (output / "index.html").write_text(html, encoding="utf-8")
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
    parser.add_argument("--six", default="outputs/experiments/six_method_retrieval_v2")
    parser.add_argument("--parent", default="outputs/experiments/planned_hybrid_v1")
    parser.add_argument("--previous", default="outputs/experiments/anchored_hybrid_v2")
    parser.add_argument("--additional", default="outputs/experiments/guarded_hybrid_v3")
    parser.add_argument(
        "--references", default="outputs/experiments/source_literal_retrieval_v1/frozen_inputs.json"
    )
    parser.add_argument("--output", default="outputs/experiments/guarded_hybrid_retrieval_v3")
    args = parser.parse_args()
    result = build(
        Path.cwd(),
        args.six,
        args.parent,
        args.previous,
        args.additional,
        args.references,
        args.output,
    )
    print(
        json.dumps(
            {
                "primary_candidate": result["primary_candidate"],
                "ranking_records": result["ranking_records"],
                "metrics": result["metrics"],
                "guard_summary": result["guard_summary"],
            },
            indent=2,
        )
    )
