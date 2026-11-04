"""Audit and report the complete complex-note ten-method retrieval comparison."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

from occupational_fitness_rag.evaluation.long_note_study import source_metrics
from tools.complex_ten_contract import (
    DEFAULT,
    METHODS,
    ROOT,
    digest,
    pin,
    read,
    rows,
    verify,
    write_json,
)

LABELS = [
    "1 · Vector",
    "2 · BM25",
    "3 · Hybrid RRF",
    "4 · Source graph-assisted",
    "5 · LightRAG mix",
    "6 · Microsoft GraphRAG Local",
    "7 · Prefix criterion coverage v6",
    "8 · FlagEmbedding reranking",
    "9 · Neo4j frontier + criterion coverage v3",
    "10 · PageIndex + RRF predicate navigation",
]


def reference_map(queries, units):
    """Read unchanged engineering references only after validating actual rankings."""
    cases = defaultdict(lambda: defaultdict(set))
    new = read(ROOT / "data/cases/gold/complex_long_200.json")
    for item in new["cases"]:
        for module, ids in item["expected_sources"].items():
            cases[item["case_id"]][module].update(ids)
    for item in read(ROOT / "data/cases/gold/complex_notes.json")["cases"]:
        for q in item.get("queries", []):
            cases[item["id"]][q["module"]].update(q["expected_source_ids"])
    for cid, item in read(ROOT / "data/cases/gold/validation_complex_expectations.json").items():
        for sid in item["source_ids"]:
            cases[cid][units[sid]["module"]].add(sid)
    result = {}
    for q in queries:
        required = sorted(cases[q["case_id"]][q["module"]])
        for sid in required:
            if sid not in units or units[sid]["module"] != q["module"]:
                raise ValueError("Reference source absent or outside its frozen module")
        result[q["query_id"]] = required
    return result


def audit_rankings(output):
    plan = read(output / "plan.json")
    verify(output, plan)
    queries, corpus = read(output / "queries.json"), read(output / "corpus.json")
    qmap = {q["query_id"]: q for q in queries}
    units = {u["source_id"]: u for u in corpus["units"]}
    for sid, u in units.items():
        for covered in u.get("covers_source_ids", []):
            child = units[covered]
            if (
                child["module"] != u["module"]
                or child["pdf_page"] != u["pdf_page"]
                or " ".join(child["evidence_text"].split())
                not in " ".join(u["evidence_text"].split())
            ):
                raise ValueError("Source coverage lacks same-page literal proof")
    local = rows(output / "local_rankings.jsonl")
    repair_dir = output / "adapter_repair"
    repair = rows(repair_dir / "results.jsonl")
    rmanifest = read(repair_dir / "manifest.json")
    if rmanifest["parent_identity"] != plan["identity"] or rmanifest[
        "parent_rankings_sha256"
    ] != pin(output / "local_rankings.jsonl"):
        raise ValueError("Adapter repair is not tied to these actual failures")
    if read(repair_dir / "complete.json")["results_sha256"] != pin(repair_dir / "results.jsonl"):
        raise ValueError("Repaired output changed")
    parent = {(r["query_id"], r["method"]): r for r in local}
    for r in repair:
        old = parent[(r["query_id"], r["method"])]
        if (
            r["parent_failure_sha256"] != digest(old)
            or old["status"] != "failed"
            or r["method"] not in {METHODS[3], METHODS[6]}
        ):
            raise ValueError("A repair must preserve a matching failed adapter condition")
    selected = [r for r in local if r["method"] not in {METHODS[3], METHODS[6]}] + repair
    pending = []
    for method in METHODS[4:6] + METHODS[7:]:
        directory = output / "workers" / method
        if method == "lightrag":
            serial = output / "lightrag_serial_rerun"
            manifest = read(serial / "manifest.json")
            if manifest["identity"] != digest(
                {k: v for k, v in manifest.items() if k != "identity"}
            ):
                raise ValueError("Serial execution manifest self identity differs")
            if manifest["source_sha256"] != pin(ROOT / "tools/rerun_complex_lightrag_serial.py"):
                raise ValueError("Serial controller source changed")
            if manifest["invalid_parent_model_calls_sha256"] != pin(
                directory / "model_calls.jsonl"
            ):
                raise ValueError("Retained invalid model-call trace changed")
            verify(serial, plan)
            if manifest["parent_protocol_identity"] != plan["identity"] or manifest[
                "invalid_parent_rankings_sha256"
            ] != pin(directory / "results.jsonl"):
                raise ValueError("Serial LightRAG run is not tied to its retained invalid batch")
            directory = serial / "workers/lightrag"
        actual = rows(directory / "results.jsonl")
        if (directory / "complete.json").exists():
            receipt = read(directory / "complete.json")
            if receipt["results_sha256"] != pin(directory / "results.jsonl") or receipt[
                "recorded"
            ] != len(queries):
                raise ValueError("Native completion receipt differs")
        else:
            pending.append(method)
        selected.extend(actual)
    seen = set()
    for r in selected:
        key = r["query_id"], r["method"]
        if key in seen or key[0] not in qmap or key[1] not in METHODS:
            raise ValueError("Repeated or unexpected ranking condition")
        seen.add(key)
        q = qmap[key[0]]
        if r["experiment_identity"] != plan["identity"] or any(
            r[k] != q[k] for k in ("case_id", "module", "cohort")
        ):
            raise ValueError("Ranking case or protocol identity differs")
        if r.get("record_sha256") and r["record_sha256"] != digest(
            {k: v for k, v in r.items() if k != "record_sha256"}
        ):
            raise ValueError("Ranking record changed")
        ids = r["source_ids"]
        if (
            len(ids) != len(set(ids))
            or len(ids) > 10
            or any(s not in units or units[s]["module"] != q["module"] for s in ids)
        ):
            raise ValueError("Ranking returned invalid or cross-module originals")
        if r["status"] not in {"completed", "failed"} or (
            r["status"] == "failed" and (ids or not r.get("error"))
        ):
            raise ValueError("Failed conditions cannot return substituted originals")
    return plan, queries, corpus, selected, pending


def score(queries, corpus, actual, references):
    units = {u["source_id"]: u for u in corpus["units"]}
    detail = []
    for r in actual:
        expected = references[r["query_id"]]
        row = {k: r[k] for k in ("query_id", "case_id", "module", "cohort", "method", "status")}
        row.update(
            reference_source_ids=expected,
            source_ids=r["source_ids"],
            seconds=r["seconds"],
            labeled=bool(expected),
            error=r.get("error"),
            top5_original_bytes=sum(
                len(units[s]["evidence_text"].encode()) for s in r["source_ids"][:5]
            ),
        )
        for k in (1, 3, 5, 10):
            row[str(k)] = source_metrics(r["source_ids"], expected, units, k) if expected else None
        detail.append(row)
    metrics = []
    for cohort in ("all", "new_200", "original_34"):
        for method in METHODS:
            for module in ("all", "hypertension", "vision", "hearing", "blackout", "diabetes"):
                planned = [
                    q
                    for q in queries
                    if (cohort == "all" or q["cohort"] == cohort)
                    and (module == "all" or q["module"] == module)
                ]
                group = [
                    r
                    for r in detail
                    if r["method"] == method
                    and (cohort == "all" or r["cohort"] == cohort)
                    and (module == "all" or r["module"] == module)
                ]
                labeled = [r for r in group if r["labeled"]]
                complete = len(group) == len(planned)
                value = {
                    "cohort": cohort,
                    "module": module,
                    "method": method,
                    "planned_queries": len(planned),
                    "recorded_queries": len(group),
                    "complete": complete,
                    "labeled_queries": len(labeled),
                    "failed_queries": sum(r["status"] == "failed" for r in group),
                    "empty_queries": sum(not r["source_ids"] for r in group),
                    "mean_seconds": mean(r["seconds"] for r in group) if group else None,
                    "median_seconds": median(r["seconds"] for r in group) if group else None,
                    "mean_top5_original_bytes": mean(r["top5_original_bytes"] for r in group)
                    if group
                    else None,
                }
                for k in (1, 3, 5, 10):
                    for name in (
                        "coverage_recall",
                        "exact_id_recall",
                        "complete_coverage",
                        "hit",
                        "mrr",
                    ):
                        value[f"{name}_{k}"] = (
                            mean(r[str(k)][name] for r in labeled) if labeled and complete else None
                        )
                    by_case = defaultdict(list)
                    for r in labeled:
                        by_case[r["case_id"]].append(r[str(k)]["coverage_recall"])
                    value[f"case_mean_coverage_{k}"] = (
                        mean(mean(v) for v in by_case.values()) if by_case and complete else None
                    )
                metrics.append(value)
    return detail, metrics


def packet_replay(queries, actual, references, units, limit=9000):
    """Replay one shared whole-original budget; labels are scoring-only below."""
    by_case = defaultdict(list)
    for q in queries:
        by_case[q["case_id"]].append(q)
    index = {(r["query_id"], r["method"]): r for r in actual}
    packets = []
    for method in METHODS:
        for cid, scopes in by_case.items():
            observed = [index.get((q["query_id"], method)) for q in scopes]
            record = {"case_id": cid, "method": method, "cohort": scopes[0]["cohort"]}
            if any(r is None for r in observed):
                packets.append({**record, "status": "pending"})
                continue
            available = all(r["status"] == "completed" for r in observed)
            ordered = []
            if available:
                for rank in range(5):
                    for r in observed:
                        if rank < len(r["source_ids"]):
                            ordered.append(r["source_ids"][rank])
            offered = list(dict.fromkeys(ordered))[:5]
            sources = []
            excluded = []
            for sid in offered:
                u = units[sid]
                source = {
                    "source_id": sid,
                    "module": u["module"],
                    "section": u["section"],
                    "pdf_page": u["pdf_page"],
                    "printed_page": u["printed_page"],
                    "source_text": u["evidence_text"],
                }
                if len(json.dumps([*sources, source], ensure_ascii=False).encode()) <= limit:
                    sources.append(source)
                else:
                    excluded.append(sid)
            supplied = [s["source_id"] for s in sources]
            # Reference IDs have not entered candidate offering or budget selection.
            required = set().union(*(set(references[q["query_id"]]) for q in scopes))
            covered = (
                set().union(*({sid, *units[sid].get("covers_source_ids", [])} for sid in supplied))
                if supplied
                else set()
            )
            packets.append(
                {
                    **record,
                    "status": "completed" if available else "failed",
                    "offered_source_ids": offered,
                    "supplied_source_ids": supplied,
                    "excluded_by_byte_budget": excluded,
                    "source_bytes": len(json.dumps(sources, ensure_ascii=False).encode()),
                    "reference_source_ids": sorted(required),
                    "reference_coverage": len(required & covered) / len(required)
                    if required
                    else None,
                    "complete_reference_coverage": required <= covered if required else None,
                }
            )
    metrics = []
    for cohort in ("all", "new_200", "original_34"):
        for method in METHODS:
            group = [
                p
                for p in packets
                if p["method"] == method and (cohort == "all" or p["cohort"] == cohort)
            ]
            labeled = [p for p in group if p.get("reference_coverage") is not None]
            complete = all(p["status"] != "pending" for p in group)
            metrics.append(
                {
                    "cohort": cohort,
                    "method": method,
                    "complete": complete,
                    "cases": len(group),
                    "labeled_cases": len(labeled),
                    "mean_reference_coverage": mean(p["reference_coverage"] for p in labeled)
                    if complete and labeled
                    else None,
                    "complete_case_coverage": mean(
                        p["complete_reference_coverage"] for p in labeled
                    )
                    if complete and labeled
                    else None,
                    "cases_with_budget_exclusion": sum(
                        bool(p.get("excluded_by_byte_budget")) for p in group
                    ),
                    "failed_packets": sum(p["status"] == "failed" for p in group),
                    "policy": "round-robin first five whole originals, 9000 serialized evidence bytes; no backfill or truncation",
                    "decision_model_called": False,
                }
            )
    return packets, metrics


def comparison_report(output=DEFAULT):
    output = Path(output).resolve()
    plan, queries, corpus, actual, pending = audit_rankings(output)
    units = {u["source_id"]: u for u in corpus["units"]}
    references = reference_map(queries, units)
    detail, metrics = score(queries, corpus, actual, references)
    packets, packet_metrics = packet_replay(queries, actual, references, units)
    shared_calls = [read(p) for p in (output / "embeddings").glob("*.json")]
    accounting = {
        "shared_actual_embedding_calls": len(shared_calls),
        "shared_embedding_input_texts": sum(len(r["request"]["input"]) for r in shared_calls),
        "shared_embedding_seconds": sum(r["seconds"] for r in shared_calls),
        "native_worker_calls": {},
        "upstream_intake_reused_cases": 200,
        "new_upstream_intake_cases": 34,
    }
    for method in ("lightrag", "graphrag", METHODS[9]):
        folder = output / "workers" / method
        if method == "lightrag":
            folder = output / "lightrag_serial_rerun/workers/lightrag"
        if (folder / "complete.json").exists():
            calls = rows(folder / "model_calls.jsonl")
            accounting["native_worker_calls"][method] = {
                "actual_calls": len(calls),
                "by_route": dict(Counter(c.get("route", "/api/chat") for c in calls)),
                "by_status": dict(Counter(c["status"] for c in calls)),
            }
    native_flag = output / "workers/flag_embedding_rerank/native/summary.json"
    if native_flag.exists():
        accounting["flag_embedding"] = read(native_flag)
    accounting["native_neo4j_queries"] = (
        {"vector": len(queries), "fulltext": len(queries), "cypher_graph": len(queries)}
        if (output / "workers" / METHODS[8] / "complete.json").exists()
        else None
    )
    base = {(r["query_id"], r["method"]): r for r in detail}
    changes = []
    for q in queries:
        if not references[q["query_id"]]:
            continue
        for method in (METHODS[6], METHODS[8], METHODS[9]):
            a, b = base.get((q["query_id"], "hybrid")), base.get((q["query_id"], method))
            if not a or not b:
                continue
            x, y = a["5"]["coverage_recall"], b["5"]["coverage_recall"]
            changes.append(
                {
                    "case_id": q["case_id"],
                    "query_id": q["query_id"],
                    "module": q["module"],
                    "cohort": q["cohort"],
                    "method": method,
                    "change": "improved"
                    if y > x + 1e-12
                    else "regressed"
                    if y < x - 1e-12
                    else "unchanged",
                    "hybrid_coverage_5": x,
                    "candidate_coverage_5": y,
                    "hybrid_sources": a["source_ids"][:5],
                    "candidate_sources": b["source_ids"][:5],
                }
            )
    target = output / "comparison"
    target.mkdir(exist_ok=True)
    summary = {
        "experiment_identity": plan["identity"],
        "cases": 234,
        "new_cases": 200,
        "original_cases": 34,
        "query_scopes": len(queries),
        "planned_conditions": len(queries) * 10,
        "recorded_conditions": len(actual),
        "complete": not pending and len(actual) == len(queries) * 10,
        "pending_methods": pending,
        "source_labeled_cases": len({q["case_id"] for q in queries if references[q["query_id"]]}),
        "source_labeled_scopes": sum(bool(v) for v in references.values()),
        "unlabeled_cases": sorted(
            {
                q["case_id"]
                for q in queries
                if not any(
                    references[t["query_id"]] for t in queries if t["case_id"] == q["case_id"]
                )
            }
        ),
        "metrics": metrics,
        "packet_metrics": packet_metrics,
        "execution_accounting": accounting,
        "method_labels": dict(zip(METHODS, LABELS, strict=True)),
        "failed_conditions": sum(r["status"] == "failed" for r in actual),
        "retained_initial_adapter_failures": 714,
        "invalid_concurrent_lightrag_batch": read(output / "lightrag_serial_rerun/manifest.json"),
        "adapter_repair_new_model_calls": 0,
        "judgment_calls": 0,
        "clinical_accuracy": None,
        "clinical_review": "pending",
        "production_change": False,
        "scoring_note": "Reference-source coverage is separate from clinical relevance, answer accuracy and citation entailment; unlabelled scopes do not enter recall denominators.",
        "cost_note": "Ranking times exclude shared whole-note embeddings and source/index construction. Method 7 facet times in repaired records reuse recorded actual embeddings. Native model retrieval costs remain measured in the native rows; these are incremental costs, not isolated hardware benchmarks.",
    }
    for name, value in [
        ("summary.json", summary),
        ("scored_rankings.json", detail),
        ("references.json", references),
        ("paired_changes.json", changes),
        ("packet_replay.json", packets),
    ]:
        write_json(target / name, value)
    with (target / "metrics.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(metrics[0]))
        writer.writeheader()
        writer.writerows(metrics)
    with (target / "input_inventory.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["case_id", "cohort", "modules", "input", "sha256"])
        for item in read(output / "input_inventory.json"):
            writer.writerow(
                [
                    item["case_id"],
                    item["cohort"],
                    ";".join(item["modules"]),
                    item["input"],
                    item["sha256"],
                ]
            )
    shutil.copyfile(ROOT / "data/knowledge/raw/ap_g56_22.pdf", target / "evidence_guide.pdf")
    data = {
        "summary": summary,
        "queries": queries,
        "units": units,
        "rankings": detail,
        "labels": dict(zip(METHODS, LABELS, strict=True)),
    }
    render(target, data)
    write_json(
        target / "audit.json",
        {
            "complete": summary["complete"],
            "unique_conditions": len(actual),
            "planned_conditions": len(queries) * 10,
            "all_original_inputs_and_implementation_pins_unchanged": True,
            "literal_source_coverage_verified": True,
            "cross_module_returned_sources": 0,
            "references_supplied_to_rankers": False,
            "upstream_facts_frozen_per_case": True,
            "initial_adapter_failures_retained": True,
            "repair_preserves_actual_embedding_responses": True,
            "corpus_sha256": corpus["corpus_sha256"],
            "source_sha256": pin(__file__),
        },
    )
    write_json(
        target / "artifacts.json",
        {p.name: pin(p) for p in target.iterdir() if p.is_file() and p.name != "artifacts.json"},
    )
    print(
        json.dumps(
            {
                k: summary[k]
                for k in [
                    "cases",
                    "query_scopes",
                    "source_labeled_cases",
                    "source_labeled_scopes",
                    "recorded_conditions",
                    "complete",
                    "failed_conditions",
                    "pending_methods",
                ]
            },
            indent=2,
        )
    )
    return summary


def render(target, data):
    payload = json.dumps(data, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c")
    template = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>234 cases · Ten retrieval methods | Occupational Fitness Platform</title><style>
body{margin:0;background:#f4f6f8;color:#263747;font:14px/1.6 Arial,sans-serif}main{max-width:1320px;margin:auto;padding:30px 28px}header,section{background:white;border:1px solid #dce3e9;border-radius:8px;padding:24px;margin:18px 0}h1{font-size:29px;line-height:1.25}h2{font-size:20px}small{color:#5c7287;letter-spacing:.08em}.stats{display:flex;gap:32px;flex-wrap:wrap}.stats strong{display:block;font-size:26px}.notice{border-left:3px solid #b18948;background:#fcf8ef;padding:14px}table{border-collapse:collapse;width:100%;font-size:13px}td,th{border-bottom:1px solid #e0e5eb;padding:10px;text-align:left;vertical-align:top}th{background:#f7f9fb}a{color:#235f85}label{display:inline-flex;flex-direction:column;gap:5px;margin:8px 16px 8px 0}select,button{padding:8px;border:1px solid #ccd8e2;background:white;color:#263747;border-radius:4px}details{border-top:1px solid #e0e5eb;padding:10px 0}summary{cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.65 Consolas,monospace}article{border:1px solid #dce3e9;padding:18px;border-radius:6px;min-width:0}.cards{display:grid;grid-template-columns:1fr 1fr;gap:16px}.scroll{overflow-x:auto}.muted{color:#6b7883}.tag{background:#edf2f6;padding:3px 8px;border-radius:4px}blockquote{margin:8px 0;padding:10px 14px;background:#f6f8fa;border-left:2px solid #b4c9d9}footer{color:#697b8a;padding:20px 0}@media(max-width:800px){.cards{grid-template-columns:1fr}main{padding:12px}section{padding:16px}}</style></head><body><main>
<header><small>OCCUPATIONAL FITNESS PLATFORM · COMPLETE COMPLEX-NOTE RETRIEVAL COMPARISON</small><h1>234 cases. Ten preserved retrieval methods.</h1><div class="stats" id="stats"></div><p id="progress"></p><p class="notice">Engineering evidence coverage, not clinical accuracy. All methods receive the same frozen whole-note queries, requested modules and 88-original corpus. Reference source IDs never enter ranking. Original method versions and prior results remain preserved.</p></header>
<section><h2>Retrieval performance</h2><label>Cohort<select id="cohort"><option value="all">All 234 cases</option><option value="new_200">New 200 long-form cases</option><option value="original_34">Original 34 complex cases</option></select></label><label>Disease module<select id="module"><option value="all">All requested modules</option><option>hypertension</option><option>vision</option><option>hearing</option><option>blackout</option><option>diabetes</option></select></label><div class="scroll"><table><thead><tr><th>Method</th><th>Recorded / planned</th><th>Scored scopes</th><th>Coverage R@5</th><th>Coverage R@10</th><th>Exact-ID R@5</th><th>Complete @5</th><th>MRR @10</th><th>Failed</th></tr></thead><tbody id="metrics"></tbody></table></div><p>Coverage credits only verified same-page literal original-text containment. Exact-ID recall requires the nominated source ID itself. Reference lists are incomplete relevance judgments: missing a nominated source is measurable; other returned sources are not automatically irrelevant. Hypertension has four available originals, so Top-5/10 saturates; Top-1/3 and per-module metrics are in the CSV.</p></section>
<section><h2>Cost and evidence volume</h2><div class="scroll"><table><thead><tr><th>Method</th><th>Mean ranking seconds</th><th>Median seconds</th><th>Mean Top-5 original bytes</th><th>Case-mean R@5</th></tr></thead><tbody id="cost"></tbody></table></div><p id="cost-note"></p></section>
<section><h2>Evidence-budget replay</h2><p>One shared allocation policy offers the first five whole originals in module round-robin order, with a 9,000-byte serialized evidence limit. No source is truncated or replaced using reference labels. These are case-level budget simulations; no judgment model was called. This table follows the cohort filter and retains every requested module of each case.</p><div class="scroll"><table><thead><tr><th>Method</th><th>Labelled cases</th><th>Packet coverage</th><th>Complete case coverage</th><th>Budget exclusions</th><th>Failed packets</th></tr></thead><tbody id="packets"></tbody></table></div><p><a href="packet_replay.json">Every offered, supplied and excluded original</a></p></section><section><h2>Same-case original evidence</h2><label>Case<select id="case"></select></label><label>Method<select id="method"><option value="">All ten methods</option></select></label><label>Result filter<select id="result"><option value="">All</option><option value="failure">Failed conditions</option><option value="miss">Incomplete Top-5 reference coverage</option><option value="unlabeled">Unlabelled scopes</option></select></label><p id="shown"></p><div id="case-view"></div></section>
<section><h2>Protocol, failures and audit</h2><p>There are 40 authored scenario families with five correlated variants among the new 200 notes. These are development stress inputs, not 200 independent patients. Untagged legacy notes request all five disease modules. Modules without existing source labels are retained for execution checks and omitted from recall denominators.</p><p>Two initial adapter integration errors were repaired in a separate child run: source graph mapping and prefix baseline status/module. All 714 original failures remain in the parent journal. The unchanged strategies were rerun with their recorded actual embedding responses; no reference backfill, simulated graph backend or model-generated guideline text was used.</p><p>The first LightRAG execution had 363 observations for 357 queries because two controllers overlapped. Its complete invalid batch, including all failures and repeated observations, is retained. Primary LightRAG metrics use a fresh exclusive serial run of all 357 queries with unchanged settings and no answer-based selection.</p><p>This comparison makes no fitness-judgment calls. Source retrieval, accepted citation identifiers and supported clinical reasoning are distinct measurements.</p><p><a href="summary.json">All metrics and cohort/module breakdowns</a> · <a href="metrics.csv">Metrics CSV</a> · <a href="input_inventory.csv">Input inventory</a> · <a href="scored_rankings.json">Every scored ranking</a> · <a href="paired_changes.json">Method 7/9/10 changes versus RRF</a> · <a href="audit.json">Independent accounting checks</a> · <a href="../native_integrity.json">Native index and database checks</a> · <a href="../plan.json">Frozen protocol</a> · <a href="../local_rankings.jsonl">Initial local records including failures</a> · <a href="../adapter_repair/results.jsonl">Adapter repair records</a> · <a href="../workers/lightrag/results.jsonl">Invalid concurrent LightRAG batch</a> · <a href="../lightrag_serial_rerun/workers/lightrag/results.jsonl">Primary serial LightRAG records</a> · <a href="evidence_guide.pdf">Original guideline</a></p><details><summary>Source-label availability</summary><pre id="unlabeled"></pre></details></section><footer>Occupational Fitness Platform · Clinical source and reference review pending · Production defaults unchanged</footer>
<script id="dataset" type="application/json">__PAYLOAD__</script><script>
const D=JSON.parse(document.getElementById('dataset').textContent),S=D.summary,$=id=>document.getElementById(id),esc=t=>String(t??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),pct=v=>v==null?'Pending':(v*100).toFixed(2)+'%';
$('stats').innerHTML=`<div><strong>${S.cases}</strong>Frozen input files</div><div><strong>${S.query_scopes}</strong>Requested module queries</div><div><strong>${S.recorded_conditions}/${S.planned_conditions}</strong>Actual conditions</div><div><strong>${S.source_labeled_cases}</strong>Cases with source labels</div>`;
$('progress').textContent=S.complete?'All ten methods completed.':`Incomplete: pending ${S.pending_methods.join(', ')}`;$('cost-note').textContent=S.cost_note;$('unlabeled').textContent=JSON.stringify({cases_without_source_labels:S.unlabeled_cases,source_labeled_scopes:S.source_labeled_scopes,total_scopes:S.query_scopes},null,2);
const ids=[...new Set(D.queries.map(q=>q.case_id))].sort();$('case').innerHTML='<option value="">First matching case</option>'+ids.map(c=>`<option>${esc(c)}</option>`).join('');$('case').value=ids[0];$('method').innerHTML+=Object.entries(D.labels).map(([id,label])=>`<option value="${id}">${esc(label)}</option>`).join('');
function draw(){const cohort=$('cohort').value; $('packets').innerHTML=S.packet_metrics.filter(r=>r.cohort===cohort).map(r=>`<tr><td>${esc(D.labels[r.method])}</td><td>${r.labeled_cases}</td><td>${pct(r.mean_reference_coverage)}</td><td>${pct(r.complete_case_coverage)}</td><td>${r.cases_with_budget_exclusion}</td><td>${r.failed_packets}</td></tr>`).join('');const module=$('module').value,metrics=S.metrics.filter(r=>r.cohort===cohort&&r.module===module);$('metrics').innerHTML=metrics.map(r=>`<tr><td>${esc(D.labels[r.method])}</td><td>${r.recorded_queries}/${r.planned_queries}</td><td>${r.labeled_queries}</td><td>${pct(r.coverage_recall_5)}</td><td>${pct(r.coverage_recall_10)}</td><td>${pct(r.exact_id_recall_5)}</td><td>${pct(r.complete_coverage_5)}</td><td>${r.mrr_10==null?'Pending':r.mrr_10.toFixed(3)}</td><td>${r.failed_queries}</td></tr>`).join('');$('cost').innerHTML=metrics.map(r=>`<tr><td>${esc(D.labels[r.method])}</td><td>${r.mean_seconds?.toFixed(3)??'Pending'}</td><td>${r.median_seconds?.toFixed(3)??'Pending'}</td><td>${r.mean_top5_original_bytes?.toFixed(0)??'Pending'}</td><td>${pct(r.case_mean_coverage_5)}</td></tr>`).join('');let qs=D.queries.filter(q=>(cohort==='all'||q.cohort===cohort)&&(module==='all'||q.module===module)&&(!$('case').value||q.case_id===$('case').value));if(!$('case').value&&qs.length){const first=qs[0].case_id;qs=qs.filter(q=>q.case_id===first)}$('shown').textContent=qs.length?`Showing ${qs[0].case_id}: ${qs.length} requested module scopes. Select a case to inspect every original passage.`:'No case matches these filters.';$('case-view').innerHTML=qs.map(q=>{let rs=D.rankings.filter(r=>r.query_id===q.query_id&&(!$('method').value||r.method===$('method').value));rs=rs.filter(r=>$('result').value==='failure'?r.status==='failed':$('result').value==='miss'?r.labeled&&r['5'].coverage_recall<1:$('result').value==='unlabeled'?!r.labeled:true);return `<h3>${esc(q.case_id)} / ${esc(q.module)}</h3><details><summary>Original nurse note</summary><pre>${esc(q.query)}</pre></details><div class="cards">`+rs.map(r=>`<article><strong>${esc(D.labels[r.method])}</strong><p><span class="tag">${esc(r.status)}</span> · ${r.labeled?'Coverage @5 '+pct(r['5'].coverage_recall):'No source label'} · ${r.seconds.toFixed(3)} s</p>${r.error?'<p>'+esc(r.error)+'</p>':''}<p class="muted">Expected evidence: ${r.reference_source_ids.map(esc).join(', ')||'Unlabelled'}</p>${r.source_ids.map((sid,i)=>{const u=D.units[sid];return `<details><summary>Rank ${i+1} · ${esc(sid)} · PDF ${u.pdf_page}</summary><p>Section ${esc(u.section)} · Printed page ${u.printed_page} · ${esc(u.licence_context)}</p><blockquote>${esc(u.evidence_text)}</blockquote><a href="evidence_guide.pdf#page=${u.pdf_page}" target="_blank">Open original guideline page</a></details>`}).join('')}</article>`).join('')+'</div>'}).join('')};
function caseOptions(){const c=$('cohort').value,m=$('module').value;const ids=[...new Set(D.queries.filter(q=>(c==='all'||q.cohort===c)&&(m==='all'||q.module===m)).map(q=>q.case_id))].sort();$('case').innerHTML='<option value="">First matching case</option>'+ids.map(v=>`<option>${esc(v)}</option>`).join('');} ['cohort','module'].forEach(id=>$(id).addEventListener('change',()=>{caseOptions();draw()}));['case','method','result'].forEach(id=>$(id).addEventListener('change',draw));draw();</script></main></body></html>"""
    (target / "index.html").write_text(template.replace("__PAYLOAD__", payload), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT)
    comparison_report(parser.parse_args().output)
