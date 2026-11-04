"""Freeze identical patient facts and common judge requests after six rankings.

This command calls no model. Reference outcomes are saved only in a separate
scoring file; reference source IDs are restricted to the explicit evidence control.
"""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from html import escape
from pathlib import Path

import yaml

from occupational_fitness_rag.evaluation.applicability_judgment import validate_patient_payload
from occupational_fitness_rag.evaluation.evidence_selection import select_documented_evidence
from occupational_fitness_rag.evaluation.graph_contract import file_hash, fingerprint
from occupational_fitness_rag.evaluation.judgment_comparison import judgment_request
from occupational_fitness_rag.evaluation.passage_comparison import patient_identity
from occupational_fitness_rag.provenance import write_json

METHODS = ("vector", "bm25", "hybrid", "graph_local", "lightrag", "graphrag")
CONTROLS = ("no_evidence", "reference_evidence")


def common_evidence(patient, units, source_ids, byte_limit):
    """Keep complete original passages from Top 5 only; never backfill by labels."""
    if len(source_ids) > 5 or len(source_ids) != len(set(source_ids)):
        raise ValueError("Provide at most five distinct source IDs")
    payload = deepcopy(patient)
    evidence, excluded = [], []
    for sid in source_ids:
        unit = units[sid]
        if unit["module"] not in patient["modules"] or unit["licence_context"] not in {"commercial", "shared"}:
            raise ValueError("Evidence is outside the common patient scope")
        source = {"source_id": sid, "module": unit["module"], "source_text": unit["evidence_text"],
                  "section": unit["section"], "pdf_page": unit["pdf_page"], "printed_page": unit["printed_page"]}
        raw = json.dumps([*evidence, source], ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
        if len(raw) > byte_limit:
            excluded.append(sid)
        else:
            evidence.append(source)
    payload["guideline_evidence"] = evidence
    validate_patient_payload(payload)
    if patient_identity(payload) != patient_identity(patient):
        raise ValueError("Evidence allocation changed fixed patient facts")
    return payload, {"selected_top_5": source_ids, "supplied_source_ids": [s["source_id"] for s in evidence],
                     "excluded_by_byte_budget": excluded,
                     "evidence_utf8_bytes": len(json.dumps(evidence, ensure_ascii=False, separators=(",", ":")).encode()),
                     "policy": "whole_original_units_from_top5_no_backfill_v1"}


def prepare(root, config_path, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    if (config["repeats"] != 3 or len(config["models"]) != len(set(config["models"]))
            or not config["models"] or any(isinstance(config[k], bool) or not isinstance(config[k], int)
                                          or config[k] <= 0 for k in
                                          ("evidence_max_bytes", "request_max_bytes", "context_length", "output_tokens"))):
        raise ValueError("The common protocol requires three repeats, unique models and positive budgets")
    if not output.is_relative_to(root / "outputs/experiments") or output.exists():
        raise ValueError("Use a new, separate judgment preparation directory")
    report = root / config["retrieval_report"]
    artifacts = json.loads((report / "artifacts.json").read_bytes())
    for name, expected in artifacts.items():
        if file_hash(report / name) != expected:
            raise ValueError("Six-method report drift: " + name)
    report_manifest = json.loads((report / "manifest.json").read_bytes())
    report_summary = json.loads((report / "summary.json").read_bytes())
    if report_manifest["identity"] != config["expected_retrieval_identity"]:
        raise ValueError("Unexpected six-method retrieval version")
    if fingerprint({k: v for k, v in report_manifest.items() if k not in {"identity", "production_change", "judgment_calls"}}) != report_manifest["identity"]:
        raise ValueError("Six-method report self-identity differs")
    queries = json.loads((report / "queries.json").read_bytes())
    rankings = [json.loads(line) for line in (report / "rankings.jsonl").read_text(encoding="utf-8").splitlines()]
    if {(r["query_id"], r["method"]) for r in rankings} != {(q["query_id"], m) for q in queries for m in METHODS} or len(rankings) != len(queries) * 6:
        raise ValueError("Incomplete six-method ranking inventory")
    corpus = json.loads((report / "corpus.json").read_bytes())
    units = {u["source_id"]: u for u in corpus["units"]}
    prep = root / config["query_preparation"]
    patients = json.loads((prep / "patients.json").read_bytes())
    if fingerprint(patients) != json.loads((prep / "manifest.json").read_bytes())["patient_inputs_sha256"]:
        raise ValueError("Shared patient preparation differs")
    if json.loads((prep / "queries.json").read_bytes()) != queries:
        raise ValueError("Patient queries and retrieval report differ")
    references_path = root / config["reference_inputs"]
    if file_hash(references_path) != report_manifest["references_sha256"]:
        raise ValueError("Reference version differs")
    references = json.loads(references_path.read_bytes())
    if set(references) != set(patients):
        raise ValueError("Reference and patient case inventories differ")
    records, labels, requests, conditions = [], {}, {}, []
    for case_id, patient in sorted(patients.items()):
        if patient_identity(patient) != patient_identity(references[case_id]["payload"]):
            raise ValueError("References and retrieval have different patient facts")
        labels[case_id] = {"reference_outcome": references[case_id]["reference_outcome"],
                           "cohort": "complex_validation" if case_id.startswith("VAL-MIX-") else "engineering",
                           "clinical_review": "pending"}
        for method in (*METHODS, *CONTROLS):
            try:
                if method == "no_evidence":
                    ids, allocation = [], {"policy": "no_guideline_evidence_control"}
                elif method == "reference_evidence":
                    ids = [s["source_id"] for s in references[case_id]["reference_payload"]["guideline_evidence"]]
                    allocation = {"policy": "human_specified_source_control_from_same_corpus"}
                else:
                    rows = [r for r in rankings if r["case_id"] == case_id and r["method"] == method]
                    allocation = select_documented_evidence(patient, rows, 5)
                    ids = allocation["source_ids"]
                payload, budget = common_evidence(patient, units, ids, config["evidence_max_bytes"])
                if method != "no_evidence" and not payload["guideline_evidence"]:
                    raise ValueError("No original evidence survived; do not substitute the no-evidence control")
                key = fingerprint({"case_id": case_id, "method": method, "payload": payload})
                record = {"case_id": case_id, "method": method, "status": "ready", "payload": payload,
                          "payload_identity": key, "allocation": allocation, "budget": budget}
                pending_requests, pending_conditions = {}, []
                for model in config["models"]:
                    body = judgment_request(config, model, payload)
                    if len(json.dumps(body, ensure_ascii=False).encode()) > config["request_max_bytes"]:
                        raise ValueError("Common judge request exceeds its explicit byte budget")
                    request_id = fingerprint(body)
                    pending_requests[request_id] = body
                    for repeat in range(config["repeats"]):
                        pending_conditions.append({"case_id": case_id, "method": method, "model": model,
                                                   "repeat": repeat, "payload_identity": key, "request_identity": request_id})
                requests.update(pending_requests)
                conditions.extend(pending_conditions)
                records.append(record)
            except Exception as exc:
                records.append({"case_id": case_id, "method": method, "status": "blocked",
                                "error": f"{type(exc).__name__}: {exc}"})
    # No reference outcomes, rule results or allocation annotations enter body.
    for body in requests.values():
        wire = json.loads(body["messages"][1]["content"])
        validate_patient_payload(wire)
    condition_keys = [(c["case_id"], c["method"], c["model"], c["repeat"]) for c in conditions]
    if len(condition_keys) != len(set(condition_keys)):
        raise ValueError("Repeated planned judgment condition")
    manifest_data = {"kind": "six_retrieval_common_judge_preparation", "config": config,
                     "retrieval_report_identity": report_manifest["identity"], "retrieval_artifacts": artifacts,
                     "patient_inputs_sha256": fingerprint(patients), "payloads_sha256": fingerprint(records),
                     "labels_sha256": fingerprint(labels), "requests_sha256": fingerprint(requests),
                     "conditions_sha256": fingerprint(conditions), "builder_sha256": file_hash(__file__),
                     "judge_source_sha256": file_hash(root / "src/occupational_fitness_rag/evaluation/judgment_comparison.py"),
                     "scope": "Common single-stage source-ID judgment contract; no applicability ledger is substituted",
                     "clinical_review": "pending"}
    manifest = {**manifest_data, "identity": fingerprint(manifest_data), "judgment_calls": 0, "production_change": False}
    output.mkdir(parents=True)
    for name, value in (("manifest.json", manifest), ("payloads.json", records), ("scoring_labels.json", labels),
                        ("requests.json", requests), ("conditions.json", conditions)):
        write_json(output / name, value)
    summary = {"cases": len(patients), "payload_conditions": len(records),
               "ready_payloads": sum(r["status"] == "ready" for r in records),
               "blocked_payloads": sum(r["status"] == "blocked" for r in records),
               "planned_judgments": len(conditions), "unique_request_bodies": len(requests), "judgment_calls": 0,
               "repeats": config["repeats"], "all_expected_conditions_ready": len(conditions) == len(patients) * 8 * len(config["models"]) * config["repeats"],
               "graph_construction_truncation_flags": report_summary["graph_completion_quality"]["truncated_completion_calls"],
               "ready_for_final_judgment_run": (len(conditions) == len(patients) * 8 * len(config["models"]) * config["repeats"]
                                                and report_summary["graph_completion_quality"]["truncated_completion_calls"] == 0),
               "larger_graph_output_sensitivity_required_before_method_recommendation": report_summary["graph_completion_quality"]["truncated_completion_calls"] > 0}
    write_json(output / "summary.json", summary)
    render_inputs(output, records, summary)
    write_json(output / "artifacts.json", {p.name: file_hash(p) for p in output.iterdir() if p.is_file()})
    return summary


def render_inputs(output, records, summary):
    cards = []
    for row in records:
        body = '<p>' + escape(row.get("error", "Prepared; inference has not run.")) + '</p>'
        if row["status"] == "ready":
            body += '<details><summary>Fixed verified patient facts</summary><pre>' + escape(json.dumps(
                row["payload"]["verified_patient_facts"], ensure_ascii=False, indent=2)) + '</pre></details>'
            budget = row["budget"]
            body += f'<p>{len(budget["supplied_source_ids"])} original passages · {budget["evidence_utf8_bytes"]} UTF-8 evidence bytes</p>'
            body += '<p>Excluded whole passages: ' + escape(str(budget["excluded_by_byte_budget"])) + '</p>'
            for source in row["payload"]["guideline_evidence"]:
                body += '<details><summary>' + escape(source["source_id"]) + ' · ' + escape(source["module"]) + '</summary>'
                body += f'<a href="../six_method_retrieval_v1/evidence_guide.pdf#page={source["pdf_page"]}">PDF {source["pdf_page"]}, section {escape(str(source["section"]))}</a>'
                body += '<pre>' + escape(source["source_text"]) + '</pre></details>'
            if not row["payload"]["guideline_evidence"]:
                body += '<p>No guideline evidence: explicit no-evidence control.</p>'
        cards.append(f'<article data-case="{escape(row["case_id"])}" data-method="{row["method"]}" data-status="{row["status"]}"><h3>{escape(row["case_id"])} / {row["method"]}</h3>' + body + '</article>')
    options = ''.join('<option>' + escape(value) + '</option>' for value in sorted({r["case_id"] for r in records}))
    methods = ''.join('<option>' + m + '</option>' for m in (*METHODS, *CONTROLS))
    html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Common judgment inputs</title><style>body{font:15px/1.65 Arial,sans-serif;background:#f4f6f9;color:#213749;margin:32px auto;max-width:1150px;padding:24px}header,section,article{background:white;border:1px solid #dce3ea;border-radius:10px;padding:24px;margin:20px 0}h1{font-size:28px}h3{font-size:17px}pre{white-space:pre-wrap;background:#f6f8fb;font:13px/1.6 Consolas,monospace;padding:16px}details{padding:10px 0;border-bottom:1px solid #e3e9ef}summary{cursor:pointer}select{padding:9px;margin:10px}a{color:#1b5984}</style><header><small>OCCUPATIONAL FITNESS PLATFORM · EXPERIMENTAL INPUTS</small><h1>Common judgment inputs</h1>'''
    html += f'<p>{summary["ready_payloads"]}/{summary["payload_conditions"]} ready case/method payloads · {summary["planned_judgments"]} planned independent calls · 0 executed calls</p>'
    html += '<p>Prepared inputs only. No new fitness judgment or clinical accuracy result is claimed. Patient facts and the system prompt stay fixed across retrieval methods. Expected outcomes are absent from the model requests.</p><a href="../six_method_retrieval_v1/index.html">Retrieval comparison</a> · <a href="payloads.json">Payload records</a> · <a href="requests.json">Exact model requests</a> · <a href="conditions.json">Repeated condition inventory</a> · <a href="manifest.json">Version manifest</a></header>'
    html += f'<section><h2>Graph quality review</h2><p>The upstream execution recorded {summary["graph_construction_truncation_flags"]} length-limited graph completions. Prepared inputs preserve the original returned evidence. Final judgment execution readiness: {str(summary["ready_for_final_judgment_run"]).lower()}. Resolve the graph construction flags and freeze the final evidence version before the definitive comparison.</p></section>'
    html += '<section><label>Case <select id="case"><option value="">All</option>' + options + '</select></label><label>Method <select id="method"><option value="">All</option>' + methods + '</select></label><p id="count"></p></section>'
    html += ''.join(cards) + '''<script>function filter(){let n=0;document.querySelectorAll('article').forEach(a=>{const ok=['case','method'].every(k=>!document.getElementById(k).value||a.dataset[k]===document.getElementById(k).value);a.hidden=!ok;if(ok)n++});document.getElementById('count').textContent=n+' prepared payloads shown'}['case','method'].forEach(k=>document.getElementById(k).addEventListener('change',filter));filter();</script></html>'''
    (output / "index.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", default="outputs/experiments/retrieval_judgment_preparation_v1")
    args = parser.parse_args()
    print(json.dumps(prepare(Path.cwd(), args.config, args.output), indent=2))
