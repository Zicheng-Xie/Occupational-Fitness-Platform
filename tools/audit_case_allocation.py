"""Audit fixed facts, actual Top5 membership, scope, byte budgets and criterion floors."""

from __future__ import annotations

import json
from pathlib import Path

from occupational_fitness_rag.evaluation.case_evidence_allocation import (
    evidence_bytes,
    source_record,
)
from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.evaluation.passage_comparison import patient_identity, read_records
from occupational_fitness_rag.provenance import digest, write_json
from tools.prepare_case_allocation_judgments import ARMS
from tools.run_frozen_retrieval_judgments import prepare_inputs, verify_files


def audit(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists() or not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Use a fresh audit directory")
    prep = root / "outputs/experiments/case_allocation_judgment_preparation_v1"
    config, manifest, pins, _, payloads, requests, conditions = prepare_inputs(prep)
    shared = root / config["query_preparation"]
    patients = json.loads((shared / "patients.json").read_bytes())
    report = root / config["retrieval_report"]
    report_pins = verify_files(report)
    units = {u["source_id"]: u for u in json.loads((report / "corpus.json").read_bytes())["units"]}
    ranks = read_records(report / "rankings.jsonl")
    by_key = {(r["case_id"], r["method"]): r for r in payloads}
    verified = []
    for r in payloads:
        payload, case, arm = r["payload"], r["case_id"], r["method"]
        if patient_identity(payload) != patient_identity(patients[case]):
            raise ValueError("An evidence arm changed frozen patient facts or source wording")
        ids = [u["source_id"] for u in payload["guideline_evidence"]]
        if len(ids) != len(set(ids)) or len(ids) > 5:
            raise ValueError("Invalid original count or duplicates")
        actual = {
            sid
            for row in ranks
            if row["case_id"] == case and row["method"] == ARMS[arm][0]
            for sid in row["source_ids"][:5]
        }
        if set(ids) - actual:
            raise ValueError("Evidence not present in the actual per-module Top5")
        if any(s != source_record(units[s["source_id"]]) for s in payload["guideline_evidence"]):
            raise ValueError("Original text or provenance metadata changed")
        size = evidence_bytes(payload["guideline_evidence"])
        if size > config["evidence_max_bytes"] or size != r["budget"]["evidence_utf8_bytes"]:
            raise ValueError("Evidence byte count differs")
        if arm.endswith("case_coverage"):
            old = by_key[(case, arm.replace("case_coverage", "round_robin"))]

            def criteria(record):
                covered = {
                    sid
                    for u in record["payload"]["guideline_evidence"]
                    for sid in [u["source_id"], *units[u["source_id"]].get("covers_source_ids", [])]
                }
                return {sid for sid in covered if units[sid].get("criterion_type")}

            if not criteria(old) <= criteria(r):
                raise ValueError("New allocation lost the old packet's typed criterion floor")
        verified.append({"case_id": case, "arm": arm, "source_ids": ids, "evidence_bytes": size})
    for body in requests.values():
        wire = json.loads(body["messages"][1]["content"])
        if set(wire) != {
            "licence_context",
            "modules",
            "nurse_note",
            "verified_patient_facts",
            "guideline_evidence",
        }:
            raise ValueError("Judge body contains extra scoring or allocation metadata")
    data = {
        "kind": "case_evidence_allocation_invariant_audit",
        "preparation_identity": manifest["identity"],
        "preparation_artifacts": pins,
        "retrieval_artifacts": report_pins,
        "auditor_sha256": file_hash(__file__),
        "payloads_verified": len(verified),
        "planned_judgment_conditions": len(conditions),
        "max_evidence_bytes": max(x["evidence_bytes"] for x in verified),
        "verified_facts_unchanged": True,
        "whole_originals_unchanged": True,
        "actual_top5_membership": True,
        "new_policy_criterion_floor_verified": sum(
            r["method"].endswith("case_coverage") for r in payloads
        ),
        "model_calls": 0,
        "clinical_entailment_audited": False,
        "production_change": False,
    }
    output.mkdir(parents=True)
    write_json(output / "checks.json", data)
    write_json(output / "packets.json", verified)
    write_json(output / "manifest.json", {**data, "identity": digest(data)})
    (output / "auditor_source.py").write_bytes(Path(__file__).read_bytes())
    write_json(
        output / "artifacts.json", {p.name: file_hash(p) for p in output.iterdir() if p.is_file()}
    )
    return data


if __name__ == "__main__":
    result = audit(Path.cwd(), Path("outputs/experiments/case_allocation_audit_v1"))
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "payloads_verified",
                    "new_policy_criterion_floor_verified",
                    "max_evidence_bytes",
                )
            },
            indent=2,
        )
    )
