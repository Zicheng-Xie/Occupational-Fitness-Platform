"""Compare frozen reviewed-corpus optimizations and replay actual packet budgets.

No retrieval or model is called. Reference labels enter only after available
method inventories, query identities and unchanged original texts are verified.
Pending methods are unavailable, never successful zero-recall substitutions.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from copy import deepcopy
from html import escape
from pathlib import Path

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.provenance import digest, write_json
from tools.report_anchored_hybrid import evidence_costs, read_rows, validate_rankings, write_csv
from tools.report_guarded_hybrid import top10_changes
from tools.report_planned_hybrid import evaluate, paired_changes, summarize
from tools.run_scope88_shared_retrieval import read, verify_files

DEFAULTS = {
    "shared": "scope88_shared_retrieval_v2",
    "prefix": "scope88_prefix_allocation_v6",
    "flag": "scope88_flag_rerank_v2",
    "neo": "scope88_neo4j_strategies_v2",
    "neo_transfer": "scope88_neo4j_criterion_transfer_v3",
    "tree": "scope88_tree_coverage_v1",
    "external": "scope88_external_graph_v1",
}
MAIN_BASE = ["vector", "bm25", "hybrid", "graph_local", "lightrag", "graphrag"]
PRIMARY7 = "scope88_prefix_criterion_v6"
BASE7 = "scope88_guarded_v3"
BASE9 = "neo4j_anchor_graph_guard_v2"
CANDIDATE9 = "neo4j_frontier_criterion_v3"
BASE10 = "pageindex_tree_adapter"
CANDIDATE10 = "pageindex_rrf_branch_coverage"
OBSERVED10 = "pageindex_rrf_predicate_navigation"
LABELS = {
    "vector": "1 · Vector",
    "bm25": "2 · BM25",
    "hybrid": "3 · Hybrid RRF",
    "graph_local": "4 · Source graph-assisted",
    "lightrag": "5 · LightRAG mix",
    "graphrag": "6 · Microsoft GraphRAG Local",
    PRIMARY7: "7 · Prefix criterion coverage",
    "flag_embedding_rerank": "8 · FlagEmbedding reranking",
    BASE9: "9 · Neo4j guarded graph",
    CANDIDATE9: "9 · Neo4j native frontier + criterion coverage",
    BASE10: "10 · PageIndex local tree navigator",
    CANDIDATE10: "10 · PageIndex + RRF branch coverage",
    OBSERVED10: "10 · PageIndex + RRF predicate navigation (development selection)",
}


def manifest_identity(manifest):
    value = {k: v for k, v in manifest.items() if k not in {"identity", "production_change"}}
    if digest(value) != manifest["identity"]:
        raise ValueError("Frozen method manifest self-identity differs")
    return manifest["identity"]


def canonical_rows(records):
    """Preserve framework failure names while using one report status vocabulary."""
    rows = deepcopy(records)
    for row in rows:
        if row["status"] not in {"completed", "failed"}:
            if row["status"] not in {"worker_failed", "retrieval_failed", "index_failed"}:
                raise ValueError("Unknown native failure state")
            row["native_execution_status"] = row["status"]
            row["status"] = "failed"
        if row["status"] != "completed" and (row["source_ids"] or not row.get("error")):
            raise ValueError("A failed route cannot supply fallback originals")
    return rows


def facts_present(query):
    """False and zero values remain documented facts; an empty mapping does not."""
    values = query["query_audit"]["field_values"]
    if not isinstance(values, dict):
        raise ValueError("Verified field values must be a mapping")
    return bool(values)


def packet_coverage(rows, scored, budgets, queries, units):
    """Score the unchanged five-original/9000-byte replay pack, not module Top5."""
    qmap = {q["query_id"]: q for q in queries}
    by_rank = {(r["query_id"], r["method"]): r for r in rows}
    by_budget = {(b["case_id"], b["method"]): b for b in budgets}
    result = []
    for score in scored:
        query = qmap[score["query_id"]]
        rank = by_rank[(score["query_id"], score["method"])]
        allocation = by_budget[(score["case_id"], score["method"])]
        budget = allocation.get("budget", {})
        supplied = budget.get("supplied_source_ids", [])
        selected = budget.get("selected_top_5", [])
        module_sources = [s for s in supplied if units[s]["module"] == score["module"]]
        covered = {
            s for sid in module_sources for s in [sid, *units[sid].get("covers_source_ids", [])]
        }
        required = set(score["reference_sources"])
        result.append(
            {
                **{k: score[k] for k in ("query_id", "case_id", "module", "method", "cohort")},
                "has_verified_facts": facts_present(query),
                "reference_sources": sorted(required),
                "packet_status": allocation["status"],
                "packet_source_ids": supplied,
                "module_packet_source_ids": module_sources,
                "packet_original_coverage": len(required & covered) / len(required)
                if required
                else None,
                "packet_exact_reference_recall": len(required & set(module_sources)) / len(required)
                if required
                else None,
                "module_top5_original_coverage": score["coverage_recall_5"],
                "no_module_evidence_in_packet": not module_sources,
                "module_top5_not_selected_by_count_or_module": [
                    s for s in rank["source_ids"][:5] if s not in selected
                ],
                "module_originals_excluded_by_byte_budget": [
                    s
                    for s in budget.get("excluded_by_byte_budget", [])
                    if units[s]["module"] == score["module"]
                ],
                "interpretation": "Fixed allocator replay; no judgment call or accuracy assessment",
            }
        )
    return result, summarize_packets(result)


def summarize_packets(result):
    metrics = []
    for method in dict.fromkeys(r["method"] for r in result):
        group = [r for r in result if r["method"] == method]
        labeled = [r for r in group if r["reference_sources"]]
        metrics.append(
            {
                "method": method,
                "query_scopes": len(group),
                "labeled_scopes": len(labeled),
                "mean_packet_original_coverage": sum(r["packet_original_coverage"] for r in labeled)
                / len(labeled)
                if labeled
                else None,
                "mean_packet_exact_reference_recall": sum(
                    r["packet_exact_reference_recall"] for r in labeled
                )
                / len(labeled)
                if labeled
                else None,
                "fully_covered_packet_scopes": sum(
                    r["packet_original_coverage"] == 1 for r in labeled
                ),
                "labeled_scopes_without_module_evidence": sum(
                    r["no_module_evidence_in_packet"] for r in labeled
                ),
                "module_top5_units_not_selected_by_count_or_module": sum(
                    len(r["module_top5_not_selected_by_count_or_module"]) for r in group
                ),
                "module_units_excluded_by_byte_budget": sum(
                    len(r["module_originals_excluded_by_byte_budget"]) for r in group
                ),
            }
        )
    return metrics


def packet_pairs(records, baseline, candidate):
    index = {(r["query_id"], r["method"]): r for r in records}
    changes = []
    for (qid, method), row in index.items():
        if method != candidate or (qid, baseline) not in index:
            continue
        before = index[(qid, baseline)]
        a, b = before["packet_original_coverage"], row["packet_original_coverage"]
        change = (
            "unlabeled"
            if a is None or b is None
            else "improved"
            if b > a + 1e-12
            else "regressed"
            if b < a - 1e-12
            else "unchanged"
        )
        changes.append(
            {
                "query_id": qid,
                "case_id": row["case_id"],
                "module": row["module"],
                "baseline": baseline,
                "candidate": candidate,
                "change": change,
                "before_packet_coverage": a,
                "after_packet_coverage": b,
                "has_verified_facts": row["has_verified_facts"],
                "before_packet_module_sources": before["module_packet_source_ids"],
                "after_packet_module_sources": row["module_packet_source_ids"],
            }
        )
    return {"counts": dict(Counter(r["change"] for r in changes)), "rows": changes}


def case_packet_coverage(records, units):
    """Union reference requirements within each case without weighting by modules."""
    groups = {}
    for record in records:
        groups.setdefault((record["case_id"], record["method"]), []).append(record)
    cases = []
    for (case_id, method), group in groups.items():
        required = {s for row in group for s in row["reference_sources"]}
        supplied = group[0]["packet_source_ids"]
        if any(row["packet_source_ids"] != supplied for row in group):
            raise ValueError("One case has inconsistent replay packets across modules")
        covered = {s for sid in supplied for s in [sid, *units[sid].get("covers_source_ids", [])]}
        cases.append(
            {
                "case_id": case_id,
                "method": method,
                "reference_sources": sorted(required),
                "packet_source_ids": supplied,
                "packet_original_coverage": len(required & covered) / len(required)
                if required
                else None,
                "packet_exact_reference_recall": len(required & set(supplied)) / len(required)
                if required
                else None,
            }
        )
    return cases


def promotion(metrics, baseline, candidate):
    index = {m["method"]: m for m in metrics}
    if baseline not in index or candidate not in index:
        return {
            "baseline": baseline,
            "candidate": candidate,
            "selected": baseline,
            "candidate_passed": None,
            "status": "pending",
            "selection_scope": "Observed development fixtures",
        }
    before, after = index[baseline], index[candidate]
    passed = (
        after["coverage_recall_5"] > before["coverage_recall_5"] + 1e-12
        and after["coverage_recall_10"] + 1e-12 >= before["coverage_recall_10"]
    )
    return {
        "baseline": baseline,
        "candidate": candidate,
        "selected": candidate if passed else baseline,
        "candidate_passed": passed,
        "status": "evaluated",
        "rule": "Strict Top5 coverage improvement with no Top10 regression",
        "selection_scope": "Adaptive development selection, not an unseen evaluation",
    }


def tree_development_selection(metrics):
    """Keep the prespecified primary visible when reporting the best observed arm."""
    gate = promotion(metrics, BASE10, CANDIDATE10)
    by_method = {m["method"]: m for m in metrics}
    available = [m for m in (BASE10, CANDIDATE10, OBSERVED10) if m in by_method]
    if not available:
        return gate
    selected = max(
        available,
        key=lambda m: (by_method[m]["coverage_recall_5"], by_method[m]["coverage_recall_10"]),
    )
    return {
        **gate,
        "prespecified_primary": CANDIDATE10,
        "prespecified_primary_gate": gate,
        "selected": selected,
        "selection_type": "Best observed development variant after scoring; not a prespecified winning arm",
        "selection_rule": "Highest coverage R@5, then highest coverage R@10 among the three frozen arms",
    }


def build(root, output, directories=None, allow_pending=False):
    root, output = Path(root).resolve(), Path(output).resolve()
    dirs = {k: root / "outputs/experiments" / v for k, v in (directories or DEFAULTS).items()}
    if output.exists() or not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Use a fresh optimization report directory")
    shared_pins = verify_files(dirs["shared"])
    shared = read(dirs["shared"] / "manifest.json")
    manifest_identity(shared)
    corpus, queries, patients = [
        read(dirs["shared"] / n) for n in ("corpus.json", "queries.json", "patients.json")
    ]
    units = {u["source_id"]: u for u in corpus["units"]}
    if len(units) != 88 or len(queries) != 77 or len(patients) != 33:
        raise ValueError("Require the reviewed 88-unit, 77-query, 33-case comparison")
    for query in queries:
        if (
            query["corpus_sha256"] != corpus["corpus_sha256"]
            or digest({k: v for k, v in query.items() if k != "query_id"}) != query["query_id"]
        ):
            raise ValueError("Query identity was not rebound to the reviewed corpus")
    rows, pins, execution, pending = [], {}, {}, []
    for key, directory in dirs.items():
        if not (directory / "artifacts.json").is_file():
            if allow_pending and key in {"external", "tree", "neo_transfer"}:
                pending.append(key)
                continue
            raise ValueError("Experiment is pending or lacks its immutable inventory: " + key)
        inventory = verify_files(directory)
        manifest = read(directory / "manifest.json")
        identity = manifest_identity(manifest)
        pins[key] = {
            "directory": directory.relative_to(root).as_posix(),
            "identity": identity,
            "artifacts_sha256": file_hash(directory / "artifacts.json"),
            "artifacts": inventory,
        }
        for name, expected in (("corpus.json", corpus), ("queries.json", queries)):
            if (directory / name).is_file() and read(directory / name) != expected:
                raise ValueError("Method uses different reviewed source/query inputs: " + key)
        if key == "flag":
            if manifest["input_sha256"] != file_hash(dirs["shared"] / "flag_input.json"):
                raise ValueError("Flag reranker used a different reviewed job")
        if key == "neo":
            native_input = read(directory / "native_input.json")
            if native_input["corpus"] != corpus or native_input["queries"] != queries:
                raise ValueError("Native Neo4j used different reviewed originals or queries")
            native = read(directory / "native_baseline.json")
            baseline = canonical_rows(native["results"])
            validate_rankings(baseline, queries, units, ["neo4j_clause_graph"])
            rows.extend(baseline)
        record = canonical_rows(read_rows(directory / "results.jsonl"))
        methods = list(dict.fromkeys(r["method"] for r in record))
        validate_rankings(record, queries, units, methods, identity)
        rows.extend(record)
        execution[key] = read(directory / "summary.json")
    methods = list(dict.fromkeys(r["method"] for r in rows))
    validate_rankings(rows, queries, units, methods)
    if verify_files(dirs["shared"]) != shared_pins:
        raise ValueError("Reviewed inputs changed before reference scoring")
    old_dir = root / "outputs/experiments/ten_method_retrieval_v3"
    old_pins = verify_files(old_dir)
    old_manifest = read(root / "outputs/experiments/six_method_retrieval_v2/manifest.json")
    reference_path = root / "outputs/experiments/source_literal_retrieval_v1/frozen_inputs.json"
    if file_hash(reference_path) != old_manifest["references_sha256"]:
        raise ValueError("Engineering source labels changed")
    # All available actual inventories and original mappings are now frozen.
    references = read(reference_path)
    scored = evaluate(rows, queries, units, references)
    qmap = {q["query_id"]: q for q in queries}
    for record in scored:
        record["has_verified_facts"] = facts_present(qmap[record["query_id"]])
    metrics = summarize(scored)
    gate9, gate10 = promotion(metrics, BASE9, CANDIDATE9), tree_development_selection(metrics)
    main = [*MAIN_BASE, PRIMARY7, "flag_embedding_rerank", gate9["selected"], gate10["selected"]]
    metric_map = {m["method"]: m for m in metrics}
    main_metrics = [
        metric_map.get(
            m,
            {
                "method": m,
                "records": None,
                "completed": None,
                "coverage_recall_5": None,
                "coverage_recall_10": None,
                "exact_recall_5": None,
                "exact_recall_10": None,
                "labeled_scopes": None,
                "fully_covered_5": None,
            },
        )
        for m in main
    ]
    budgets, cost_metrics = evidence_costs(rows, units, patients)
    packets, packet_metrics = packet_coverage(rows, scored, budgets, queries, units)
    case_packets = case_packet_coverage(packets, units)
    paired = {
        method: paired_changes(scored, "hybrid", method) for method in methods if method != "hybrid"
    }
    paired10 = {
        method: top10_changes(scored, "hybrid", method) for method in methods if method != "hybrid"
    }
    packet_changes = {
        baseline: packet_pairs(packets, baseline, PRIMARY7) for baseline in ("hybrid", BASE7)
    }
    prefix_changes = paired_changes(scored, BASE7, PRIMARY7)
    prefix_gains = []
    for change in prefix_changes["rows"]:
        if change["coverage_change"] == "improved":
            q = qmap[change["query_id"]]
            packet = next(
                r for r in packets if r["query_id"] == q["query_id"] and r["method"] == PRIMARY7
            )
            prefix_gains.append(
                {
                    **change,
                    "has_verified_facts": facts_present(q),
                    "verified_field_values": q["query_audit"]["field_values"],
                    "packet_original_coverage": packet["packet_original_coverage"],
                    "module_packet_source_ids": packet["module_packet_source_ids"],
                    "module_top5_not_selected_by_count_or_module": packet[
                        "module_top5_not_selected_by_count_or_module"
                    ],
                }
            )
    summary = {
        "main_methods": main,
        "main_metrics": main_metrics,
        "all_metrics": metrics,
        "method_count": 10,
        "completed_method_count": len([m for m in main if m in metric_map]),
        "all_ranking_records": len(rows),
        "module_queries": 77,
        "cases": 33,
        "original_units": 88,
        "pending_inputs": pending,
        "promotion_gates": {"method9": gate9, "method10": gate10},
        "preferred_seventh_method": PRIMARY7,
        "seventh_control": BASE7,
        "facts_present_metrics": summarize([s for s in scored if s["has_verified_facts"]]),
        "no_verified_facts_metrics": summarize([s for s in scored if not s["has_verified_facts"]]),
        "facts_present_packet_metrics": summarize_packets(
            [p for p in packets if p["has_verified_facts"]]
        ),
        "no_verified_facts_packet_metrics": summarize_packets(
            [p for p in packets if not p["has_verified_facts"]]
        ),
        "cohorts": {
            c: summarize([r for r in scored if r["cohort"] == c])
            for c in ("engineering", "complex_validation")
        },
        "diseases": {
            m: summarize([r for r in scored if r["module"] == m])
            for m in sorted({q["module"] for q in queries})
        },
        "paired_top5": paired,
        "paired_top10": paired10,
        "packet_metrics": packet_metrics,
        "prefix_gains_vs_v3": prefix_gains,
        "prefix_gain_interpretation": "Observed source coverage only; gains with empty verified fields do not establish better symptom or predicate understanding",
        "packet_changes_for_primary7": packet_changes,
        "packet_changes_vs_rrf": {
            m: packet_pairs(packets, "hybrid", m) for m in methods if m != "hybrid"
        },
        "case_packet_coverage": case_packets,
        "evidence_budget_metrics": cost_metrics,
        "execution_by_bundle": execution,
        "historical94_metrics": read(old_dir / "summary.json")["main_metrics"],
        "historical94_comparison_is_separate": True,
        "remaining_textual_applicability_review": "pending; 88 retained sources are not fully certified scope-pure",
        "interpretation": "Engineering source-reference coverage on observed development fixtures, not clinical accuracy or fitness-judgment accuracy. Module Top5 and the replayed five-original/9000-byte case packet are different endpoints.",
        "actual_report_model_calls": 0,
        "judgment_calls": 0,
        "production_change": False,
    }
    data = {
        "kind": "reviewed_scope88_optimization_comparison",
        "inputs": pins,
        "old94_artifacts_sha256": file_hash(old_dir / "artifacts.json"),
        "reference_sha256": file_hash(reference_path),
        "reporter_sha256": file_hash(__file__),
        "pending_inputs": pending,
        "reference_opened_after_available_inventories_verified": True,
    }
    output.mkdir(parents=True)
    for name, value in (
        ("manifest.json", {**data, "identity": digest(data), "production_change": False}),
        ("summary.json", summary),
        ("corpus.json", corpus),
        ("queries.json", queries),
        ("retrieval_metrics.json", scored),
        ("case_evidence_budgets.json", budgets),
        ("packet_coverage.json", packets),
        ("packet_metrics.json", packet_metrics),
        ("case_packet_coverage.json", case_packets),
        ("prefix_gains.json", prefix_gains),
        ("packet_paired_changes.json", packet_changes),
    ):
        write_json(output / name, value)
    write_csv(output / "summary.csv", main_metrics)
    write_csv(output / "all_methods.csv", metrics)
    write_csv(output / "packet_metrics.csv", packet_metrics)
    write_csv(output / "facts_present.csv", summary["facts_present_metrics"])
    write_csv(output / "no_verified_facts.csv", summary["no_verified_facts_metrics"])
    write_csv(output / "evidence_budget_metrics.csv", cost_metrics)
    (output / "rankings.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False, allow_nan=False) + "\n" for r in rows),
        encoding="utf-8",
    )
    shutil.copyfile(root / corpus["source_path"], output / "evidence_guide.pdf")
    (output / "reporter_source.py").write_bytes(Path(__file__).read_bytes())
    render(output, summary, rows, scored, queries, units, packets, budgets)
    for key, pin in pins.items():
        if file_hash(dirs[key] / "artifacts.json") != pin["artifacts_sha256"]:
            raise ValueError("An input changed during report generation")
    if verify_files(old_dir) != old_pins:
        raise ValueError("Historical comparison changed")
    write_json(
        output / "artifacts.json", {p.name: file_hash(p) for p in output.iterdir() if p.is_file()}
    )
    return summary


def render(output, summary, rows, scored, queries, units, packets, budgets):
    def pct(value):
        return "Unavailable" if value is None else f"{value:.2%}"

    def table(metrics, packet=False, packet_values=None):
        result = "<table><tr><th>Method</th><th>Completed</th><th>Coverage R@5</th><th>Coverage R@10</th><th>Exact R@5</th><th>Exact R@10</th><th>Fully covered @5</th>"
        if packet:
            result += "<th>Replay packet coverage</th>"
        result += "</tr>"
        packet_map = {
            m["method"]: m
            for m in (summary["packet_metrics"] if packet_values is None else packet_values)
        }
        for m in metrics:
            result += (
                "<tr><td>"
                + escape(LABELS.get(m["method"], m["method"]))
                + "</td><td>"
                + ("Pending" if m.get("completed") is None else f"{m['completed']}/{m['records']}")
                + "</td><td>"
                + pct(m.get("coverage_recall_5"))
                + "</td><td>"
                + pct(m.get("coverage_recall_10"))
                + "</td><td>"
                + pct(m.get("exact_recall_5"))
                + "</td><td>"
                + pct(m.get("exact_recall_10"))
                + "</td><td>"
                + (
                    "Unavailable"
                    if m.get("labeled_scopes") is None
                    else f"{m['fully_covered_5']}/{m['labeled_scopes']}"
                )
                + "</td>"
            )
            if packet:
                result += (
                    "<td>"
                    + pct(packet_map.get(m["method"], {}).get("mean_packet_original_coverage"))
                    + "</td>"
                )
            result += "</tr>"
        return result + "</table>"

    html = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Reviewed retrieval optimization | Occupational Fitness Platform</title><style>body{font:14px/1.65 Arial,sans-serif;color:#243748;background:#f4f6f8;max-width:1500px;margin:32px auto;padding:22px}main{background:white;border:1px solid #dce3ea;border-radius:8px;padding:30px}h1{font-size:30px}h2{font-size:22px}section{border-top:1px solid #dce3ea;margin-top:24px;padding-top:18px}table{border-collapse:collapse;width:100%}th,td{padding:9px;text-align:left;border-bottom:1px solid #dce3ea}.notice{background:#fff8e9;border-left:4px solid #b98124;padding:18px}.info{background:#edf3f7;padding:16px}.compare{display:grid;grid-template-columns:1fr 1fr;gap:20px}.panel{padding:18px;border:1px solid #dce3ea;border-radius:6px;min-width:0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.6 Consolas,monospace;background:#f5f8fa;padding:14px}details{padding:8px 0;border-bottom:1px solid #e1e7ec}summary{cursor:pointer}select{padding:8px;margin:6px 14px 6px 6px;max-width:360px}a{color:#225b83}.badge{color:#22604b}.muted{color:#647585}@media(max-width:900px){.compare{grid-template-columns:1fr}body{padding:8px}main{padding:16px}table{font-size:11px}}</style><main><small>OCCUPATIONAL FITNESS PLATFORM · ENGINEERING VALIDATION</small><h1>Retrieval optimization on the reviewed corpus</h1>"""
    html += (
        '<p class="notice">88 retained originals · 33 observed development cases · 77 module queries · 45 source-labeled scopes. Six known private/mixed/incomplete units are quarantined. Remaining textual applicability and clinical source review are pending. No new fitness-judgment calls are represented here.</p><p>'
        + escape(summary["interpretation"])
        + "</p>"
    )
    if summary["pending_inputs"]:
        html += (
            '<p class="notice">Pending execution bundles: '
            + escape(", ".join(summary["pending_inputs"]))
            + ". Their metrics are unavailable, not zero.</p>"
        )
    html += (
        "<section><h2>Ten-route comparison</h2><p>The final column replays the unchanged case-level five-original/9000-byte allocator. It is not the module Top5 score and is not a model judgment.</p>"
        + table(summary["main_metrics"], True)
        + "</section>"
    )
    html += (
        "<section><h2>Verified-fact subgroup and seventh-method gains</h2><p>The improved source rankings must be interpreted separately for queries with verified values and empty verified-field mappings. False and zero values count as documented. Empty-field gains do not establish semantic or clinical understanding.</p><details><summary>Queries with verified facts</summary>"
        + table(summary["facts_present_metrics"], True, summary["facts_present_packet_metrics"])
        + "</details><details><summary>Queries without verified facts</summary>"
        + table(
            summary["no_verified_facts_metrics"], True, summary["no_verified_facts_packet_metrics"]
        )
        + "</details><details><summary>Every seventh-method improvement and its replay packet</summary><pre>"
        + escape(json.dumps(summary["prefix_gains_vs_v3"], indent=2))
        + "</pre></details></section>"
    )
    html += '<section><h2>Compare one query and its original evidence</h2><label>Case<select id="case"></select></label><label>Disease<select id="module"></select></label><br><label>Left method<select id="left"></select></label><label>Right method<select id="right"></select></label><p id="status"></p><div id="comparison"></div></section>'
    html += (
        "<section><h2>Historical 94-unit results: separate corpus</h2><p>These preserved results used the earlier corpus containing the six scope findings. They are history, not additional fresh 88-unit observations.</p>"
        + table(summary["historical94_metrics"])
        + "</section>"
    )
    html += (
        "<section><h2>Subgroups, ablations and promotion decisions</h2><details><summary>All frozen 88-unit methods and ablations</summary>"
        + table(summary["all_metrics"], True)
        + "</details><details><summary>Prespecified gates and observed development selection</summary><pre>"
        + escape(json.dumps(summary["promotion_gates"], indent=2))
        + "</pre></details>"
    )
    for name, metrics in {**summary["cohorts"], **summary["diseases"]}.items():
        html += "<details><summary>" + escape(name) + "</summary>" + table(metrics) + "</details>"
    html += (
        "</section><section><h2>Execution, cost and packet omissions</h2><p>Costs are recorded per execution bundle, not multiplied by reused variants. Imported actual calls and new calls are different. Stage timings with different scopes do not establish end-to-end speedups. Count/module omissions and byte-budget exclusions are recorded separately.</p><details><summary>Native execution and shared embedding reuse</summary><pre>"
        + escape(json.dumps(summary["execution_by_bundle"], indent=2))
        + "</pre></details><details><summary>Packet coverage metrics</summary><pre>"
        + escape(json.dumps(summary["packet_metrics"], indent=2))
        + "</pre></details><details><summary>Whole-original byte budgets</summary><pre>"
        + escape(json.dumps(summary["evidence_budget_metrics"], indent=2))
        + "</pre></details></section>"
    )
    html += (
        "<section><h2>Download audit data</h2>"
        + " · ".join(
            '<a href="' + n + '">' + escape(t) + "</a>"
            for n, t in [
                ("summary.csv", "Main metrics"),
                ("all_methods.csv", "All methods"),
                ("rankings.jsonl", "Frozen rankings"),
                ("packet_coverage.json", "Per-query packet coverage"),
                ("packet_metrics.csv", "Packet metrics"),
                ("case_packet_coverage.json", "Case-level packet coverage"),
                ("packet_paired_changes.json", "Packet changes"),
                ("case_evidence_budgets.json", "Allocator replay"),
                ("prefix_gains.json", "Seventh-method gains"),
                ("manifest.json", "Source fingerprints"),
                ("evidence_guide.pdf", "Original guideline"),
            ]
        )
        + "</section>"
    )
    data = json.dumps(
        {
            "rows": rows,
            "scored": scored,
            "queries": queries,
            "units": units,
            "packets": packets,
            "budgets": budgets,
            "preferred": PRIMARY7,
        },
        ensure_ascii=False,
        allow_nan=False,
    ).replace("<", "\\u003c")
    html += (
        '<script id="report-data" type="application/json">'
        + data
        + "</script><script>"
        + r"""
const d=JSON.parse(document.getElementById('report-data').textContent),$=id=>document.getElementById(id),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),pct=v=>v==null?'Unavailable':(v*100).toFixed(2)+'%';
function opts(el,vals){const old=el.value;el.innerHTML=vals.map(v=>'<option value="'+esc(v)+'">'+esc(v)+'</option>').join('');if(vals.includes(old))el.value=old}
const methods=[...new Set(d.rows.map(r=>r.method))];opts($('case'),[...new Set(d.queries.map(q=>q.case_id))]);opts($('left'),methods);opts($('right'),methods);$('left').value='hybrid';$('right').value=d.preferred;
function panel(q,m){const r=d.rows.find(x=>x.query_id===q.query_id&&x.method===m);if(!r)return '<div class="panel"><h3>'+esc(m)+'</h3><p>Pending: no completed immutable query inventory.</p></div>';const s=d.scored.find(x=>x.query_id===q.query_id&&x.method===m),p=d.packets.find(x=>x.query_id===q.query_id&&x.method===m),b=d.budgets.find(x=>x.case_id===q.case_id&&x.method===m);return '<div class="panel"><h3>'+esc(m)+'</h3><p>Module coverage R@5 '+pct(s.coverage_recall_5)+' · R@10 '+pct(s.coverage_recall_10)+' · Exact R@5 '+pct(s.exact_recall_5)+'</p><p>Replay packet source coverage '+pct(p.packet_original_coverage)+' · Module originals supplied: '+p.module_packet_source_ids.length+'</p><p>'+esc(r.error||r.status)+'</p>'+r.source_ids.map((sid,i)=>{const u=d.units[sid],inPack=p.packet_source_ids.includes(sid);return '<details><summary>'+(i+1)+'. '+esc(sid)+' · '+(i<5?'Top5':'Top10 only')+' · '+(inPack?'In replay packet':'Not in replay packet')+'</summary><p>Section '+esc(u.section)+' · Printed '+esc(u.printed_page)+' · <a href="evidence_guide.pdf#page='+Number(u.pdf_page)+'">PDF '+Number(u.pdf_page)+'</a></p><p>Verified contained IDs: '+esc((u.covers_source_ids||[]).join(', ')||'None')+'</p><pre>'+esc(u.evidence_text)+'</pre></details>'}).join('')+'<details><summary>Count/module omissions and byte exclusions</summary><pre>'+esc(JSON.stringify(p,null,2))+'</pre></details><details><summary>Fixed case-level allocator replay</summary><pre>'+esc(JSON.stringify(b,null,2))+'</pre></details><details><summary>Actual route, scores and source paths</summary><pre>'+esc(JSON.stringify(r,null,2))+'</pre></details></div>'}
function render(rebuild){const c=$('case').value;if(rebuild)opts($('module'),d.queries.filter(q=>q.case_id===c).map(q=>q.module));const q=d.queries.find(q=>q.case_id===c&&q.module===$('module').value);$('status').textContent='Same 88-unit corpus and literal query · Verified fields: '+Object.keys(q.query_audit.field_values).length;$('comparison').innerHTML='<details><summary>Frozen query and verified field values</summary><pre>'+esc(q.query)+'\n\n'+esc(JSON.stringify(q.query_audit.field_values,null,2))+'</pre></details><div class="compare">'+panel(q,$('left').value)+panel(q,$('right').value)+'</div>'}
$('case').addEventListener('change',()=>render(true));['module','left','right'].forEach(id=>$(id).addEventListener('change',()=>render(false)));render(true);
"""
        + "</script></main></html>"
    )
    (Path(output) / "index.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/experiments/scope88_optimization_comparison_v1"),
    )
    parser.add_argument("--allow-pending", action="store_true")
    args = parser.parse_args()
    result = build(Path.cwd(), args.output, allow_pending=args.allow_pending)
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "completed_method_count",
                    "pending_inputs",
                    "main_metrics",
                    "prefix_gains_vs_v3",
                )
            },
            indent=2,
        )
    )
