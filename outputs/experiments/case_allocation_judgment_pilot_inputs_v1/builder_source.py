"""Freeze five paired evidence arms before reading engineering reference labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from occupational_fitness_rag.evaluation.case_evidence_allocation import allocate_case_evidence
from occupational_fitness_rag.evaluation.evidence_selection import select_documented_evidence
from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.evaluation.judgment_comparison import judgment_request
from occupational_fitness_rag.evaluation.passage_comparison import patient_identity, read_records
from occupational_fitness_rag.provenance import digest, write_json
from tools.prepare_retrieval_judgments import common_evidence
from tools.run_frozen_retrieval_judgments import prepare_inputs, verify_files

ARMS = {
    "hybrid": ("hybrid", "round_robin"),
    "seventh_round_robin": ("scope88_prefix_criterion_v6", "round_robin"),
    "seventh_case_coverage": ("scope88_prefix_criterion_v6", "case_coverage"),
    "ninth_round_robin": ("neo4j_frontier_criterion_v3", "round_robin"),
    "ninth_case_coverage": ("neo4j_frontier_criterion_v3", "case_coverage"),
}


def prepare(root, output, *, pilot=False):
    root, output = Path(root).resolve(), Path(output).resolve()
    if not output.is_relative_to(root / "outputs/experiments") or output.exists():
        raise ValueError("Use a fresh isolated preparation directory")
    config_path = root / "configs/experiments/case_allocation_judgments_v1.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    report = root / config["retrieval_report"]
    pins = verify_files(report)
    patients = json.loads((root / config["query_preparation"] / "patients.json").read_bytes())
    shared_pins = verify_files(root / config["query_preparation"])
    units = {u["source_id"]: u for u in json.loads((report / "corpus.json").read_bytes())["units"]}
    ranks = read_records(report / "rankings.jsonl")
    chosen = config["mechanism_pilot_cases"] if pilot else sorted(patients)
    if len(set(chosen)) != len(chosen) or set(chosen) - patients.keys():
        raise ValueError("Invalid frozen mechanism-pilot case inventory")
    payloads, requests, conditions = [], {}, []
    for case_id in sorted(chosen):
        patient = patients[case_id]
        for arm, (method, policy) in ARMS.items():
            rows = [r for r in ranks if r["case_id"] == case_id and r["method"] == method]
            if len(rows) != len(patient["modules"]) or {r["module"] for r in rows} != set(
                patient["modules"]
            ):
                raise ValueError("Incomplete actual retrieval module inventory")
            allocation = (
                allocate_case_evidence(
                    patient, rows, units, byte_limit=config["evidence_max_bytes"]
                )
                if policy == "case_coverage"
                else select_documented_evidence(patient, rows, 5)
            )
            payload, budget = common_evidence(
                patient, units, allocation["source_ids"], config["evidence_max_bytes"]
            )
            if not payload["guideline_evidence"] or budget["excluded_by_byte_budget"]:
                raise ValueError("An arm has empty or unexpectedly excluded evidence")
            pid = digest({"case_id": case_id, "method": arm, "payload": payload})
            payloads.append(
                {
                    "case_id": case_id,
                    "method": arm,
                    "status": "ready",
                    "payload": payload,
                    "payload_identity": pid,
                    "allocation": allocation,
                    "budget": budget,
                }
            )
            for model in config["models"]:
                body = judgment_request(config, model, payload)
                if len(json.dumps(body, ensure_ascii=False).encode()) > config["request_max_bytes"]:
                    raise ValueError("Fixed judge request exceeds its explicit limit")
                identity = digest(body)
                requests[identity] = body
                conditions.extend(
                    {
                        "case_id": case_id,
                        "method": arm,
                        "model": model,
                        "repeat": repeat,
                        "payload_identity": pid,
                        "request_identity": identity,
                    }
                    for repeat in range(config["repeats"])
                )
    output.mkdir(parents=True)
    # Persist exact allocations and bodies before opening any answer/source labels.
    for name, value in (
        ("payloads.json", payloads),
        ("requests.json", requests),
        ("conditions.json", conditions),
    ):
        write_json(output / name, value)
    references_path = root / config["reference_inputs"]
    if (
        file_hash(references_path)
        != json.loads((report / "manifest.json").read_bytes())["reference_sha256"]
    ):
        raise ValueError("Reference version differs from frozen retrieval comparison")
    references = json.loads(references_path.read_bytes())
    labels = {}
    for case in chosen:
        if patient_identity(patients[case]) != patient_identity(references[case]["payload"]):
            raise ValueError("Fixed reference facts differ")
        labels[case] = {
            "reference_outcome": references[case]["reference_outcome"],
            "cohort": "complex_validation" if case.startswith("VAL-MIX-") else "engineering",
            "clinical_review": "pending",
        }
    scoring = json.loads((report / "retrieval_metrics.json").read_bytes())
    refs = {(r["case_id"], r["module"]): r["reference_sources"] for r in scoring}
    packet_rows = []
    for record in payloads:
        for module in record["payload"]["modules"]:
            expected = set(refs[(record["case_id"], module)])
            supplied = [
                s["source_id"]
                for s in record["payload"]["guideline_evidence"]
                if s["module"] == module
            ]
            covered = set().union(
                *({sid, *units[sid].get("covers_source_ids", [])} for sid in supplied)
            )
            packet_rows.append(
                {
                    "case_id": record["case_id"],
                    "module": module,
                    "method": record["method"],
                    "reference_sources": sorted(expected),
                    "supplied_source_ids": supplied,
                    "coverage": len(expected & covered) / len(expected) if expected else None,
                }
            )
    metrics = []
    for arm in ARMS:
        rows = [r for r in packet_rows if r["method"] == arm and r["coverage"] is not None]
        metrics.append(
            {
                "method": arm,
                "labeled_scopes": len(rows),
                "packet_coverage": sum(r["coverage"] for r in rows) / len(rows) if rows else None,
            }
        )
    changes = []
    by_key = {(r["case_id"], r["method"]): r for r in payloads}
    for case in chosen:
        for route in ("seventh", "ninth"):
            a, b = [by_key[(case, route + suffix)] for suffix in ("_round_robin", "_case_coverage")]
            changes.append(
                {
                    "case_id": case,
                    "route": route,
                    "same_model_input": a["payload"] == b["payload"],
                    "old_sources": a["budget"]["supplied_source_ids"],
                    "new_sources": b["budget"]["supplied_source_ids"],
                }
            )
    sources = [
        Path(__file__),
        root / "src/occupational_fitness_rag/evaluation/case_evidence_allocation.py",
        root / "src/occupational_fitness_rag/evaluation/evidence_selection.py",
        root / "src/occupational_fitness_rag/evaluation/judgment_comparison.py",
        root / "tools/prepare_retrieval_judgments.py",
    ]
    data = {
        "kind": "scope88_case_allocation_judgment_preparation",
        "config": config,
        "phase": "mechanism_pilot" if pilot else "full_development_comparison",
        "case_ids": sorted(chosen),
        "arms": ARMS,
        "retrieval_artifacts": pins,
        "shared_artifacts": shared_pins,
        "reference_sha256": file_hash(references_path),
        "payloads_sha256": digest(payloads),
        "requests_sha256": digest(requests),
        "conditions_sha256": digest(conditions),
        "labels_sha256": digest(labels),
        "sources": {str(p.relative_to(root)): file_hash(p) for p in sources},
        "labels_opened_after_requests_saved": True,
    }
    write_json(
        output / "manifest.json", {**data, "identity": digest(data), "production_change": False}
    )
    write_json(output / "scoring_labels.json", labels)
    write_json(output / "packet_coverage.json", packet_rows)
    write_json(output / "allocation_changes.json", changes)
    summary = {
        "case_count": len(chosen),
        "ready_payloads": len(payloads),
        "planned_calls": len(conditions),
        "ready_for_final_judgment_run": True,
        "phase": data["phase"],
        "metrics": metrics,
        "changed_cases_by_route": {
            route: sum(not c["same_model_input"] for c in changes if c["route"] == route)
            for route in ("seventh", "ninth")
        },
        "judgment_calls": 0,
        "production_change": False,
    }
    write_json(output / "summary.json", summary)
    (output / "builder_source.py").write_bytes(Path(__file__).read_bytes())
    (output / "allocator_source.py").write_bytes(sources[1].read_bytes())
    write_json(
        output / "artifacts.json", {p.name: file_hash(p) for p in output.iterdir() if p.is_file()}
    )
    prepare_inputs(output)  # Validate compatibility with the unchanged actual-call runner.
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mechanism-pilot", action="store_true")
    args = parser.parse_args()
    print(json.dumps(prepare(Path.cwd(), args.output, pilot=args.mechanism_pilot), indent=2))
