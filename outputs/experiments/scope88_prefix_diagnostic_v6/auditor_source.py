"""Audit fact availability and literal originals behind frozen prefix gains."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from html import escape
from itertools import combinations
from pathlib import Path

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.provenance import digest, write_json
from tools.report_anchored_hybrid import read_rows, write_csv
from tools.report_planned_hybrid import summarize
from tools.run_scope88_prefix_allocation import BASELINE_METHOD, read_json, verify


def verify_report(directory):
    """The report identity hashes its full declared data including production=False."""
    pins = read_json(directory / "artifacts.json")
    for name, expected in pins.items():
        source = (directory / name).resolve()
        if not source.is_relative_to(directory) or file_hash(source) != expected:
            raise ValueError("Frozen scored report changed")
    manifest = read_json(directory / "manifest.json")
    if digest({k: v for k, v in manifest.items() if k != "identity"}) != manifest["identity"]:
        raise ValueError("Frozen scored-report identity differs")
    return manifest, pins


def fact_group(query):
    audit = query["query_audit"]
    values, names = audit["field_values"], audit["field_names"]
    if (
        not isinstance(values, dict)
        or not isinstance(names, list)
        or len(names) != len(set(names))
        or set(names) != set(values)
        or any(value is None for value in values.values())
        or audit["no_documented_facts"] is not (not values)
    ):
        raise ValueError("Query fact-availability audit differs from its verified fields")
    return "verified_module_facts_present" if values else "no_verified_module_facts"


def build(experiment, report, output, root=None):
    root = Path(root or Path.cwd()).resolve()
    experiment, report, output = [Path(p).resolve() for p in (experiment, report, output)]
    if output.exists() or not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Use a new diagnostic output directory")
    run_manifest, run_pins = verify(experiment)
    report_manifest, report_pins = verify_report(report)
    if report_manifest["experiment_identity"] != run_manifest["identity"]:
        raise ValueError("Report does not describe the actual frozen allocation")
    corpus, queries, scored = [
        read_json(report / name)
        for name in ("corpus.json", "queries.json", "retrieval_metrics.json")
    ]
    units = {u["source_id"]: u for u in corpus["units"]}
    groups = {q["query_id"]: fact_group(q) for q in queries}
    rows = read_rows(experiment / "results.jsonl")
    budget_records = read_json(report / "case_evidence_budgets.json")
    budget_map = {(r["case_id"], r["method"]): r for r in budget_records}
    baseline = {r["query_id"]: r for r in rows if r["method"] == BASELINE_METHOD}
    scores = {(r["query_id"], r["method"]): r for r in scored}
    primary = "scope88_prefix_criterion_v6"
    gains, changes = [], []
    for row in rows:
        if row["method"] != primary:
            continue
        prior = baseline[row["query_id"]]
        if row["source_ids"][:5] == prior["source_ids"][:5]:
            continue
        a, b = [
            scores[(row["query_id"], m)]["coverage_recall_5"] for m in (BASELINE_METHOD, primary)
        ]
        detail = {
            **{k: row[k] for k in ("query_id", "case_id", "module")},
            "fact_availability": groups[row["query_id"]],
            "coverage_recall_5_before": a,
            "coverage_recall_5_after": b,
            "introduced_originals": [],
            "moved_background_or_originals": [],
            "full_top10_inventory_unchanged": set(row["source_ids"]) == set(prior["source_ids"]),
        }
        required = set(scores[(row["query_id"], primary)]["reference_sources"])

        def supplied(method):
            actual = budget_map[(row["case_id"], method)]
            ids = actual.get("budget", {}).get("supplied_source_ids", [])
            covered = {x for s in ids for x in [s, *units[s].get("covers_source_ids", [])]}
            return {
                "source_ids": ids,
                "module_supplied_source_ids": [
                    s for s in ids if units[s]["module"] == row["module"]
                ],
                "module_reference_coverage": len(covered & required) / len(required)
                if required
                else None,
                "case_evidence_utf8_bytes": actual.get("budget", {}).get("evidence_utf8_bytes"),
                "allocation_policy": actual.get("allocation", {}).get("policy"),
            }

        detail["actual_case_context_before"] = supplied(BASELINE_METHOD)
        detail["actual_case_context_after"] = supplied(primary)
        for sid in [s for s in row["source_ids"][:5] if s not in prior["source_ids"][:5]]:
            source = units[sid]
            contained = source.get("covers_source_ids", [])
            normalized = re.sub(r"\s+", "", source["evidence_text"])
            for child in contained:
                if re.sub(r"\s+", "", units[child]["evidence_text"]) not in normalized:
                    raise ValueError("Criterion coverage lacks literal original containment")
            detail["introduced_originals"].append(
                {
                    "source_id": sid,
                    "prior_rank": prior["source_ids"].index(sid) + 1,
                    "pdf_page": source["pdf_page"],
                    "section": source["section"],
                    "bbox": source["bbox"],
                    "text_sha256": source["text_sha256"],
                    "covers_source_ids": contained,
                    "exact_original_text": source["evidence_text"],
                    "interpretation": "Retrieved criterion alternative; applicability is not established by the allocation score",
                }
            )
        detail["moved_background_or_originals"] = [
            {
                "source_id": sid,
                "new_rank": row["source_ids"].index(sid) + 1,
                "pdf_page": units[sid]["pdf_page"],
                "section": units[sid]["section"],
                "exact_original_text": units[sid]["evidence_text"],
                "text_sha256": units[sid]["text_sha256"],
            }
            for sid in prior["source_ids"][:5]
            if sid not in row["source_ids"][:5]
        ]
        changes.append(detail)
        if a is not None and b is not None and b > a + 1e-12:
            gains.append(detail)
    subgroup = {
        group: {
            "queries": sum(value == group for value in groups.values()),
            "metrics": summarize([r for r in scored if groups[r["query_id"]] == group]),
        }
        for group in ("verified_module_facts_present", "no_verified_module_facts")
    }
    # Label-aware diagnostic only, after real rankings were frozen. These ideal
    # subsets are never passed to an executable retrieval strategy or a judge.
    oracle = []
    for qid, prior in baseline.items():
        required = set(scores[(qid, primary)]["reference_sources"])
        if not required:
            continue
        ids = prior["source_ids"]
        choices = []
        for indexes in combinations(range(len(ids)), min(5, len(ids))):
            selected = [ids[i] for i in indexes]
            covered = {x for s in selected for x in [s, *units[s].get("covers_source_ids", [])]}
            choices.append(
                (len(covered & required) / len(required), sum(i + 1 for i in indexes), indexes)
            )
        value, _, indexes = min(choices, key=lambda x: (-x[0], x[1], x[2]))
        observed = scores[(qid, primary)]["coverage_recall_5"]
        oracle.append(
            {
                "query_id": qid,
                "case_id": prior["case_id"],
                "module": prior["module"],
                "actual_v6_coverage_recall_5": observed,
                "label_aware_oracle_top5_coverage_within_actual_v3_top10": value,
                "diagnostic_gap": value - observed,
                "oracle_source_ids_not_a_deployable_method": [ids[i] for i in indexes],
                "oracle_references_read_after_ranking_freeze": True,
                "budget": "At most five unchanged originals within actual prior Top10; no case-level multi-module or 9000-byte optimization claimed",
            }
        )
    summary = {
        "subgroups": subgroup,
        "changed_top5_lists": len(changes),
        "improved_labeled_queries": len(gains),
        "improvements_with_verified_module_facts": sum(
            r["fact_availability"] == "verified_module_facts_present" for r in gains
        ),
        "improvements_without_verified_module_facts": sum(
            r["fact_availability"] == "no_verified_module_facts" for r in gains
        ),
        "oracle_diagnostic": {
            "labeled_queries": len(oracle),
            "actual_v6_mean_coverage_recall_5": sum(
                r["actual_v6_coverage_recall_5"] for r in oracle
            )
            / len(oracle),
            "label_aware_ceiling_within_actual_top10": sum(
                r["label_aware_oracle_top5_coverage_within_actual_v3_top10"] for r in oracle
            )
            / len(oracle),
            "queries_below_diagnostic_ceiling": sum(r["diagnostic_gap"] > 1e-12 for r in oracle),
            "deployable_method": False,
        },
        "interpretation": "Both measured gains occur in queries without verified module facts. The result is broader criterion allocation for ambiguous module queries; verified-fact retrieval coverage is unchanged. It does not demonstrate improved symptom understanding or predicate entailment. Moving background out of the five-source judge budget needs a separate judgment comparison.",
        "scope": "Reviewed 88-unit engineering subset; remaining textual applicability and clinical review pending",
        "new_model_calls": 0,
        "production_change": False,
    }
    data = {
        "kind": "frozen_prefix_fact_availability_and_original_evidence_audit",
        "allocation_identity": run_manifest["identity"],
        "report_identity": report_manifest["identity"],
        "allocation_artifacts_sha256": file_hash(experiment / "artifacts.json"),
        "report_artifacts_sha256": file_hash(report / "artifacts.json"),
        "auditor_sha256": file_hash(__file__),
        "model_calls": 0,
    }
    if verify(experiment)[1] != run_pins or verify_report(report)[1] != report_pins:
        raise ValueError("Frozen inputs changed during diagnostic")
    output.mkdir(parents=True)
    for name, value in (
        ("manifest.json", {**data, "identity": digest(data)}),
        ("summary.json", summary),
        ("improved_scopes.json", gains),
        ("changed_prefix_review_queue.json", changes),
        ("label_aware_oracle_diagnostic.json", oracle),
    ):
        write_json(output / name, value)
    write_csv(
        output / "fact_availability_metrics.csv",
        [
            {"fact_availability": group, **metric}
            for group, values in subgroup.items()
            for metric in values["metrics"]
        ],
    )
    html = (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Prefix allocation diagnostic | Occupational Fitness Platform</title><style>body{font:14px/1.65 Arial,sans-serif;max-width:1200px;margin:32px auto;padding:24px;color:#243748;background:#f4f6f8}section{background:white;padding:22px;margin:16px 0;border:1px solid #dce3ea;border-radius:6px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f7f9;padding:15px}summary{cursor:pointer}a{color:#225b83}</style><small>OCCUPATIONAL FITNESS PLATFORM · ENGINEERING AUDIT</small><h1>Where the prefix-allocation gain occurs</h1><section><p>'
        + escape(summary["interpretation"])
        + "</p><p>"
        + escape(summary["scope"])
        + "</p></section><section><h2>Verified-fact and ambiguous-query subgroups</h2><pre>"
        + escape(json.dumps(subgroup, indent=2))
        + "</pre></section>"
    )
    for gain in gains:
        html += (
            "<section><h2>"
            + escape(gain["case_id"] + " · " + gain["module"])
            + "</h2><p>No verified module facts. Coverage "
            + f"{gain['coverage_recall_5_before']:.2%} → {gain['coverage_recall_5_after']:.2%}"
            + ".</p>"
        )
        for source in gain["introduced_originals"]:
            html += (
                "<details><summary>"
                + escape(source["source_id"])
                + " · Prior rank "
                + str(source["prior_rank"])
                + "</summary><p>Section "
                + escape(source["section"])
                + ' · <a href="evidence_guide.pdf#page='
                + str(source["pdf_page"])
                + '">PDF '
                + str(source["pdf_page"])
                + "</a></p><pre>"
                + escape(source["exact_original_text"])
                + "</pre></details>"
            )
        html += "</section>"
    html += '<section><p><a href="summary.json">Summary</a> · <a href="fact_availability_metrics.csv">Subgroup CSV</a> · <a href="improved_scopes.json">Exact gain evidence</a> · <a href="changed_prefix_review_queue.json">All changed prefixes and displaced background</a></p></section></html>'
    (output / "index.html").write_text(html, encoding="utf-8")
    shutil.copyfile(report / "evidence_guide.pdf", output / "evidence_guide.pdf")
    shutil.copyfile(__file__, output / "auditor_source.py")
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
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.experiment, args.report, args.output), indent=2))
