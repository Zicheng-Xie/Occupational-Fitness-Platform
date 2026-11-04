"""Independently audit frozen retrieval outputs without calling any models.

Run with the existing GraphRAG Python environment, which supplies pyarrow for
reading the actual native index. Only a fresh output directory is written.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def records(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]


def fingerprint(value):
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_bundle(path):
    pins = read(path / "artifacts.json")
    require(bool(pins), "Empty frozen artifact inventory")
    for name, expected in pins.items():
        target = (path / name).resolve()
        require(target.is_relative_to(path.resolve()), "Unsafe artifact path")
        require(file_hash(target) == expected, "Changed frozen artifact: " + str(target))
    return {"files": len(pins), "artifact_manifest_sha256": file_hash(path / "artifacts.json")}


def footprint(ids, units):
    return {source for sid in ids for source in [sid, *units[sid].get("covers_source_ids", [])]}


def allocate(patient, rows, units):
    """Reimplement the fixed documented-module round robin and whole-source cap."""
    requested = list(dict.fromkeys(patient["modules"]))
    documented = set()
    for field, fact in patient["verified_patient_facts"].items():
        if fact.get("value") is not None and fact.get("status", "present") == "present":
            prefix = field.split(".", 1)[0]
            documented.add("hypertension" if prefix == "cardiovascular" else prefix)
    active = [module for module in requested if module in documented] or requested
    by_module = {row["module"]: row["source_ids"] for row in rows}
    selected = []
    for rank in range(max(len(by_module[module]) for module in active)):
        for module in active:
            ids = by_module[module]
            if rank < len(ids) and ids[rank] not in selected and len(selected) < 5:
                selected.append(ids[rank])
        if len(selected) == 5:
            break
    evidence, excluded = [], []
    for sid in selected:
        unit = units[sid]
        source = {
            "source_id": sid,
            "module": unit["module"],
            "source_text": unit["evidence_text"],
            "section": unit["section"],
            "pdf_page": unit["pdf_page"],
            "printed_page": unit["printed_page"],
        }
        raw = json.dumps([*evidence, source], ensure_ascii=False, separators=(",", ":")).encode()
        if len(raw) > 9000:
            excluded.append(sid)
        else:
            evidence.append(source)
    return {
        "selected_top_5": selected,
        "supplied_source_ids": [item["source_id"] for item in evidence],
        "excluded_by_byte_budget": excluded,
        "evidence_utf8_bytes": len(
            json.dumps(evidence, ensure_ascii=False, separators=(",", ":")).encode()
        ),
    }


def audit_prefix(path, units):
    rows = records(path / "results.jsonl")
    index = {(row["query_id"], row["method"]): row for row in rows}
    criteria = {sid for sid, unit in units.items() if unit.get("criterion_type")}
    count = 0
    for row in rows:
        if row["method"] == "scope88_guarded_v3":
            continue
        prior = index[(row["query_id"], "scope88_guarded_v3")]["source_ids"]
        floor = footprint(prior[:5], units)
        if row["method"] == "scope88_prefix_criterion_v6":
            floor &= criteria
        choices = []
        for positions in itertools.combinations(range(len(prior)), min(5, len(prior))):
            covered = footprint([prior[position] for position in positions], units)
            if floor <= covered:
                choices.append((-len(covered & criteria), sum(p + 1 for p in positions), positions))
        best = min(choices)
        first = [prior[position] for position in best[2]]
        expected = first + [sid for sid in prior if sid not in first]
        require(
            row["source_ids"] == expected, "Prefix differs from exhaustive label-free objective"
        )
        count += 1
    return {"exhaustively_recomputed_prefix_rows": count, "new_model_calls": 0}


def audit_page(base, units):
    path = base / "scope88_tree_coverage_v1"
    rows = records(path / "results.jsonl")
    calls = records(path / "model_calls.jsonl")
    imported = records(path / "imported_model_calls.jsonl")
    mapping = read(path / "native_index/source_mapping.json")
    parent = base / "native_pageindex_retrieval_v4"
    old = sum(
        (
            records(parent / name)
            for name in (
                "imported_v2_model_calls.jsonl",
                "imported_v3_model_calls.jsonl",
                "model_calls.jsonl",
            )
        ),
        [],
    )
    old_hashes = {fingerprint(call) for call in old}
    by_hash = {fingerprint(call): call for call in imported}
    require(set(by_hash) <= old_hashes and len(by_hash) == 130, "Unproven imported tree calls")
    by_call = {(call["query_id"], call["phase"]): call for call in calls}
    require(len(calls) == len(by_call) == 178, "Repeated or incomplete tree calls")
    imported_controls, max_bytes, exclusions = 0, 0, 0
    for row in rows:
        if row.get("historical_query_id"):
            observed = [by_hash[value] for value in row["actual_prior_calls_sha256"]]
            require(len(observed) == 2, "Imported tree control must retain two actual calls")
            rank = next(call for call in observed if call["phase"] != "branches")
            imported_controls += 1
        else:
            rank = by_call[(row["query_id"], row["method"])]
        raw = rank["raw_response"]
        raw = json.loads(raw) if isinstance(raw, str) else raw
        selected = list(dict.fromkeys(json.loads(raw["message"]["content"])["node_ids"]))
        require(
            selected == row["selected_leaf_node_ids"], "Tree IDs differ from actual model response"
        )
        leaves = mapping[row["module"]]["leaves"]
        require(
            [leaves[n]["source_id"] for n in selected] == row["source_ids"],
            "Tree original mapping differs",
        )
        originals = json.loads(rank["request"]["messages"][1]["content"])["originals"]
        size = len(json.dumps(originals, ensure_ascii=False).encode())
        max_bytes = max(size, max_bytes)
        require(size <= 20000, "Tree candidate context exceeds its fixed byte cap")
        require(
            all(
                item["original_text"] == units[item["source_id"]]["evidence_text"]
                for item in originals
            ),
            "Tree supplied original text changed",
        )
        allowed = rank["request"]["format"]["properties"]["node_ids"]["items"]["enum"]
        require(
            len(selected) == min(10, len(allowed)) and set(selected) <= set(allowed),
            "Tree output is underfilled or fabricated",
        )
        exclusions += bool(row.get("excluded_native_nodes_by_navigation_budget"))
    return {
        "ranking_records": len(rows),
        "imported_control_results": imported_controls,
        "imported_actual_calls": len(imported),
        "new_actual_calls": len(calls),
        "new_call_phases": dict(Counter(call["phase"] for call in calls)),
        "rows_with_whole_candidate_byte_exclusions": exclusions,
        "max_original_candidate_json_bytes": max_bytes,
        "max_observed_prompt_tokens": max(
            call["raw_response"].get("prompt_eval_count", 0) for call in calls
        ),
        "no_fabricated_original_refill": True,
    }


def graph_health(base, units):
    import pyarrow.parquet as parquet

    external = base / "scope88_external_graph_v1"
    folder = external / "indexes/graphrag/vision"
    files = {
        name: folder / "output" / (name + ".parquet")
        for name in ("text_units", "entities", "relationships")
    }
    tables = {name: parquet.read_table(path).to_pylist() for name, path in files.items()}
    mapping_path = folder / "source_mapping.json"
    mapping = read(mapping_path)
    linkage = []
    for row in tables["text_units"]:
        source = mapping[str(row["human_readable_id"])]
        require(source["text_unit_id"] == row["id"], "Native text-unit mapping differs")
        linkage.append(
            {
                "source_ids": source["source_ids"],
                "human_readable_id": row["human_readable_id"],
                "text_unit_id": row["id"],
                "entity_ids": row["entity_ids"] or [],
                "relationship_ids": row["relationship_ids"] or [],
                "actual_entity_table_links": sum(
                    row["id"] in entity["text_unit_ids"] for entity in tables["entities"]
                ),
                "actual_relationship_table_links": sum(
                    row["id"] in edge["text_unit_ids"] for edge in tables["relationships"]
                ),
            }
        )
    missing = [row for row in linkage if not row["entity_ids"]]
    require(len(linkage) == 27 and len(missing) == 1, "Unexpected native graph health inventory")
    source_id = "AFTD2022-EXP-a09b64ac70a92828"
    require(
        missing[0]["source_ids"] == [source_id]
        and missing[0]["actual_entity_table_links"]
        == missing[0]["actual_relationship_table_links"]
        == 0,
        "Missing graph-source linkage changed",
    )
    calls = records(external / "model_calls.jsonl")
    failed = [call for call in calls if call["status"] != "completed"]
    groups = {call["request_sha256"] for call in failed}
    require(len(failed) == 3 and len(groups) == 1, "Graph failed-call inventory changed")
    key = next(iter(groups))
    require(
        not any(call["status"] == "completed" and call["request_sha256"] == key for call in calls),
        "Exact failed graph request was recovered",
    )
    failure_proof = []
    for call in failed:
        raw = call["raw_response"]
        raw = json.loads(raw) if isinstance(raw, str) else raw
        require(raw["done_reason"] == "length", "Unexpected graph extraction failure reason")
        require(
            any(
                units[source_id]["evidence_text"] in message.get("content", "")
                for message in call["request"]["messages"]
            ),
            "Failed request does not contain exact affected original",
        )
        failure_proof.append(
            {
                "record_sha256": fingerprint(call),
                "request_sha256": key,
                "done_reason": raw["done_reason"],
                "eval_count": raw.get("eval_count"),
                "phase": call["phase"],
                "completion_rejected": call["completion_rejected"],
            }
        )
    imports = records(external / "imported_model_calls.jsonl")
    require(
        all(call["status"] == "completed" for call in imports),
        "Historical imported graph call failed",
    )
    results = records(external / "results.jsonl")
    returned = {}
    for method in ("graphrag", "lightrag"):
        rows = [row for row in results if row["method"] == method and row["module"] == "vision"]
        require(len(rows) == 12, "Vision query count changed")
        returned[method] = {
            "queries": 12,
            "affected_source_in_top10": sum(source_id in row["source_ids"][:10] for row in rows),
        }
    log_path = folder / "logs/indexing-engine.log"
    lines = log_path.read_text(encoding="utf-8").splitlines()
    quoted = [{"line": number, "text": lines[number - 1]} for number in (137, 219, 678, 679)]
    return {
        "status": "degraded_partial_entity_extraction",
        "source_id": source_id,
        "pdf_page": units[source_id]["pdf_page"],
        "source_text": units[source_id]["evidence_text"],
        "source_text_sha256": units[source_id]["text_sha256"],
        "native_table_rows": {name: len(rows) for name, rows in tables.items()},
        "all_original_unit_linkage": linkage,
        "unlinked_originals": missing,
        "failed_exact_request_sha256": key,
        "failed_attempts": failure_proof,
        "successful_identical_retry_count": 0,
        "vision_top10_exposure": returned,
        "new_actual_calls": len(calls),
        "new_call_routes": dict(Counter(call["route"] for call in calls)),
        "imported_actual_calls": len(imports),
        "log_excerpt": quoted,
        "proof_file_sha256": {
            str(path): file_hash(path)
            for path in [
                *files.values(),
                mapping_path,
                log_path,
                external / "model_calls.jsonl",
                external / "imported_model_calls.jsonl",
            ]
        },
        "interpretation": "Original text is stored, but one original has no graph entities or relations. Completed retrieval does not establish clean graph construction. This experiment cannot establish framework or clinical superiority.",
    }


def audit_report(path, actual, patients, units, references):
    pins = verify_bundle(path)
    manifest = read(path / "manifest.json")
    require(
        fingerprint(
            {k: v for k, v in manifest.items() if k not in {"identity", "production_change"}}
        )
        == manifest["identity"],
        "Report self identity differs",
    )
    rows = records(path / "rankings.jsonl")
    require(len(rows) == 1463, "Expected nineteen frozen 77-query variants")
    scores = {
        (row["query_id"], row["method"]): row for row in read(path / "retrieval_metrics.json")
    }
    packets = {(row["query_id"], row["method"]): row for row in read(path / "packet_coverage.json")}
    budgets = {
        (row["case_id"], row["method"]): row for row in read(path / "case_evidence_budgets.json")
    }
    max_bytes = exclusions = 0
    for row in rows:
        origin = actual[(row["query_id"], row["method"])]
        require(
            all(row[key] == origin[key] for key in ("source_ids", "status", "experiment_identity")),
            "Report differs from actual worker output",
        )
        require(row["status"] == "completed", "A failed route was substituted")
        require(
            all(
                sid in units and units[sid]["module"] == row["module"] for sid in row["source_ids"]
            ),
            "A source is quarantined, unknown or wrong-module",
        )
        reference = {
            item["source_id"]
            for item in references[row["case_id"]]["reference_payload"]["guideline_evidence"]
            if item["module"] == row["module"]
        }
        score = scores[(row["query_id"], row["method"])]
        require(set(score["reference_sources"]) == reference, "Reference-source labels changed")
        for k in (5, 10):
            expected = (
                len(reference & footprint(row["source_ids"][:k], units)) / len(reference)
                if reference
                else None
            )
            require(
                score["coverage_recall_" + str(k)] == expected, "Recorded source coverage differs"
            )
    for method in dict.fromkeys(row["method"] for row in rows):
        group = [row for row in rows if row["method"] == method]
        for case_id, patient in patients.items():
            case_rows = [row for row in group if row["case_id"] == case_id]
            expected = allocate(patient, case_rows, units)
            saved = budgets[(case_id, method)]["budget"]
            require(
                all(saved[key] == value for key, value in expected.items()),
                "Saved case budget differs from independent allocator",
            )
            max_bytes = max(max_bytes, expected["evidence_utf8_bytes"])
            exclusions += len(expected["excluded_by_byte_budget"])
            for row in case_rows:
                key = (row["query_id"], method)
                needed = set(scores[key]["reference_sources"])
                supplied = [
                    sid
                    for sid in expected["supplied_source_ids"]
                    if units[sid]["module"] == row["module"]
                ]
                coverage = (
                    len(needed & footprint(supplied, units)) / len(needed) if needed else None
                )
                require(
                    packets[key]["packet_original_coverage"] == coverage,
                    "Post-allocation module coverage differs",
                )
    summary = read(path / "summary.json")
    require(
        summary["actual_report_model_calls"] == summary["judgment_calls"] == 0,
        "Reporter unexpectedly claims judgments",
    )
    quality = (
        read(path / "native_index_quality.json")
        if (path / "native_index_quality.json").exists()
        else None
    )
    return {
        "path": str(path),
        "identity": manifest["identity"],
        "artifact_checks": pins,
        "ranking_records": len(rows),
        "case_budgets_verified": len(budgets),
        "module_packets_verified": len(packets),
        "max_case_evidence_bytes": max_bytes,
        "byte_exclusions": exclusions,
        "main_metrics": summary["main_metrics"],
        "prefix_gains": summary["prefix_gains_vs_v3"],
        "native_index_quality": quality,
        "judgment_calls": 0,
    }


def run(root, output, reports):
    base = root / "outputs/experiments"
    require(
        output.is_relative_to(base) and not output.exists(),
        "Use a fresh experiment audit directory",
    )
    names = [
        "scope88_shared_retrieval_v2",
        "scope88_prefix_allocation_v6",
        "scope88_flag_rerank_v2",
        "scope88_neo4j_strategies_v2",
        "scope88_neo4j_criterion_transfer_v3",
        "scope88_tree_coverage_v1",
        "scope88_external_graph_v1",
    ]
    bundles = {name: verify_bundle(base / name) for name in names}
    corpus = read(base / names[0] / "corpus.json")
    units = {unit["source_id"]: unit for unit in corpus["units"]}
    require(len(units) == 88, "Expected reviewed source inventory")
    queries = read(base / names[0] / "queries.json")
    require(
        all(
            q["corpus_sha256"] == corpus["corpus_sha256"]
            and q["query_id"] == fingerprint({k: v for k, v in q.items() if k != "query_id"})
            for q in queries
        ),
        "Reviewed query identity differs",
    )
    actual_rows = sum((records(base / name / "results.jsonl") for name in names), [])
    actual_rows += read(base / "scope88_neo4j_strategies_v2/native_baseline.json")["results"]
    actual = {(row["query_id"], row["method"]): row for row in actual_rows}
    require(
        len(actual) == len(actual_rows) == 1463, "Actual worker inventory is repeated or incomplete"
    )
    patients = read(base / names[0] / "patients.json")
    references = read(base / "source_literal_retrieval_v1/frozen_inputs.json")
    report_results = [audit_report(path, actual, patients, units, references) for path in reports]
    checks = {
        "input_bundles": bundles,
        "query_identity_checks": len(queries),
        "scope88_corpus_sha256": corpus["corpus_sha256"],
        "prefix_allocation": audit_prefix(base / names[1], units),
        "tree_actual_calls": audit_page(base, units),
        "clinical_source_review": "pending",
        "new_model_calls": 0,
        "production_change": False,
    }
    health = graph_health(base, units)
    output.mkdir(parents=True)

    def save(name, value):
        (output / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )

    save("checks.json", checks)
    save("graph_health.json", health)
    save("report_audits.json", report_results)
    shutil.copyfile(__file__, output / "auditor_source.py")
    manifest = {
        "kind": "independent_scope88_actual_output_audit",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_sha256": file_hash(__file__),
        "reports": [
            {"path": str(path), "artifacts_sha256": file_hash(path / "artifacts.json")}
            for path in reports
        ],
        "model_calls": 0,
        "production_change": False,
    }
    manifest["identity"] = fingerprint(manifest)
    save("manifest.json", manifest)
    blocks = "".join(
        "<article><h2>"
        + escape(Path(row["path"]).name)
        + "</h2><p>1,463 actual rankings, 627 independently replayed case budgets, 1,463 module packet checks. Maximum case evidence "
        + str(row["max_case_evidence_bytes"])
        + " bytes; zero byte exclusions.</p><p>Graph extraction qualification: "
        + (
            "Explicitly degraded"
            if row["native_index_quality"]
            else "Historical report predates this finding"
        )
        + "</p></article>"
        for row in report_results
    )
    html = (
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>Independent retrieval audit</title><style>body{font:15px/1.7 system-ui;max-width:1100px;margin:40px auto;color:#213547;padding:20px;background:#f5f7f9}article{padding:24px;background:white;border:1px solid #d8e1e8;margin:18px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#225d89}.warning{border-left:5px solid #b7771a}</style><p>OCCUPATIONAL FITNESS PLATFORM</p><h1>Independent reviewed-corpus retrieval audit</h1><article class="warning"><h2>Microsoft GraphRAG Vision index: degraded extraction</h2><p>One original is stored but has no graph entity or relationship links. Three identical extraction attempts ended at the output-token limit, without a successful identical retry. Final retrieval execution completed, but the graph was only partially constructed. Its measured coverage is provisional and cannot establish framework or clinical superiority.</p><p>Affected original: AFTD2022-EXP-a09b64ac70a92828 · PDF220. Present in 0/12 GraphRAG Vision Top10 results and 12/12 LightRAG Vision Top10 results.</p></article>'
        + blocks
        + '<article><h2>Scope and interpretation</h2><p>All six quarantined source IDs are absent. Remaining 88 sources are not fully clinically or textually certified. Both method7 coverage gains concern Blackout queries without verified module facts; only SYN-EXT-009 survives the fixed case allocator. These are source-coverage results, not patient fitness-judgment improvements.</p></article><p><a href="checks.json">Structured checks</a> · <a href="graph_health.json">Native graph proof, source linkage, log lines and file hashes</a> · <a href="report_audits.json">Independent report/packet results</a> · <a href="manifest.json">Audit provenance</a> · <a href="auditor_source.py">Reproducible audit source</a></p></html>'
    )
    (output / "index.html").write_text(html, encoding="utf-8")
    save(
        "artifacts.json",
        {path.name: file_hash(path) for path in output.iterdir() if path.is_file()},
    )
    return {
        "identity": manifest["identity"],
        "output": str(output),
        "graph_status": health["status"],
        "audited_reports": len(reports),
        "new_model_calls": 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/experiments/scope88_independent_audit_v1")
    )
    parser.add_argument("--report", type=Path, action="append")
    arguments = parser.parse_args()
    project = arguments.root.resolve()
    targets = arguments.report or [
        Path("outputs/experiments/scope88_optimization_comparison_v1"),
        Path("outputs/experiments/scope88_optimization_comparison_v2"),
    ]
    print(
        json.dumps(
            run(
                project,
                (project / arguments.output).resolve(),
                [(project / path).resolve() for path in targets],
            ),
            indent=2,
        )
    )
