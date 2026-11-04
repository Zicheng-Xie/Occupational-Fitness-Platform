"""Prepare a separately versioned seventh-arm judgment run without model calls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from occupational_fitness_rag.evaluation.evidence_selection import select_documented_evidence
from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.evaluation.judgment_comparison import judgment_request
from occupational_fitness_rag.evaluation.passage_comparison import read_records
from occupational_fitness_rag.provenance import digest, write_json
from tools.prepare_retrieval_judgments import common_evidence
from tools.run_anchored_hybrid import verify_saved
from tools.run_frozen_retrieval_judgments import prepare_inputs, verify_files


def prepare(common_dir, retrieval_dir, method, output):
    """Reuse the exact existing facts, prompt, model options and evidence budget."""
    config, parent, parent_pins, _, original_payloads, _, _ = prepare_inputs(common_dir)
    retrieval, retrieval_pins = verify_saved(retrieval_dir)
    root = Path(__file__).resolve().parents[1]
    prep = root / config["query_preparation"]
    corpus = json.loads((retrieval_dir / "corpus.json").read_bytes())
    queries = json.loads((retrieval_dir / "queries.json").read_bytes())
    if (
        corpus != json.loads((prep / "corpus.json").read_bytes())
        or queries != json.loads((prep / "queries.json").read_bytes())
        or method not in {v["method"] for v in retrieval["config"]["variants"]}
    ):
        raise ValueError("New arm must use the same corpus, queries and predefined method")
    rows = [r for r in read_records(retrieval_dir / "results.jsonl") if r["method"] == method]
    qmap = {q["query_id"]: q for q in queries}
    if len(rows) != len(qmap) or {r["query_id"] for r in rows} != set(qmap):
        raise ValueError("Incomplete or repeated new-arm rankings")
    units = {u["source_id"]: u for u in corpus["units"]}
    for row in rows:
        query = qmap[row["query_id"]]
        if (
            row["status"] != "completed"
            or row["experiment_identity"] != retrieval["identity"]
            or row["case_id"] != query["case_id"]
            or row["module"] != query["module"]
            or len(row["source_ids"]) != len(set(row["source_ids"]))
            or any(
                s not in units or units[s]["module"] != query["module"] for s in row["source_ids"]
            )
        ):
            raise ValueError("New-arm identity, completion or source scope differs")
    patients = {
        r["case_id"]: r["payload"]
        for r in original_payloads
        if r["method"] == "no_evidence" and r["status"] == "ready"
    }
    records, requests, conditions = [], {}, []
    for case_id, patient in sorted(patients.items()):
        chosen = [r for r in rows if r["case_id"] == case_id]
        allocation = select_documented_evidence(patient, chosen, 5)
        payload, budget = common_evidence(
            patient, units, allocation["source_ids"], config["evidence_max_bytes"]
        )
        if not payload["guideline_evidence"]:
            raise ValueError("No original evidence survives the unchanged byte budget")
        pid = digest({"case_id": case_id, "method": method, "payload": payload})
        records.append(
            {
                "case_id": case_id,
                "method": method,
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
                raise ValueError("New evidence exceeds the fixed request byte budget")
            rid = digest(body)
            requests[rid] = body
            conditions.extend(
                {
                    "case_id": case_id,
                    "method": method,
                    "model": model,
                    "repeat": repeat,
                    "payload_identity": pid,
                    "request_identity": rid,
                }
                for repeat in range(config["repeats"])
            )
    # Scoring labels are copied separately only after all model-visible bodies
    # are fixed; neither retrieval ranking nor requests receive these values.
    labels = json.loads((common_dir / "scoring_labels.json").read_bytes())
    if set(labels) != set(patients) or digest(labels) != parent["labels_sha256"]:
        raise ValueError("Engineering reference labels changed")
    if verify_files(common_dir) != parent_pins or verify_saved(retrieval_dir)[1] != retrieval_pins:
        raise ValueError("Frozen inputs changed during judgment preparation")
    data = {
        "kind": "no_mmr_seventh_arm_judge_preparation",
        "config": config,
        "method": method,
        "parent_preparation_identity": parent["identity"],
        "parent_preparation_artifacts_sha256": file_hash(common_dir / "artifacts.json"),
        "retrieval_identity": retrieval["identity"],
        "retrieval_artifacts_sha256": file_hash(retrieval_dir / "artifacts.json"),
        "payloads_sha256": digest(records),
        "requests_sha256": digest(requests),
        "conditions_sha256": digest(conditions),
        "labels_sha256": digest(labels),
        "builder_sha256": file_hash(__file__),
        "scope": "Seventh-arm revision only; compare with the original six in a separate paired report",
        "clinical_review": "pending",
    }
    if output.exists() or not output.resolve().is_relative_to(root / "outputs/experiments"):
        raise ValueError("Use a fresh separate judgment preparation directory")
    output.mkdir(parents=True)
    summary = {
        "cases": len(patients),
        "ready_payloads": len(records),
        "blocked_payloads": 0,
        "planned_judgments": len(conditions),
        "judgment_calls": 0,
        "ready_for_final_judgment_run": True,
        "method": method,
        "cases_with_budget_exclusions": sum(
            bool(r["budget"]["excluded_by_byte_budget"]) for r in records
        ),
        "production_change": False,
    }
    for name, content in (
        (
            "manifest.json",
            {**data, "identity": digest(data), "judgment_calls": 0, "production_change": False},
        ),
        ("payloads.json", records),
        ("requests.json", requests),
        ("conditions.json", conditions),
        ("scoring_labels.json", labels),
        ("summary.json", summary),
    ):
        write_json(output / name, content)
    (output / "builder_source.py").write_bytes(Path(__file__).read_bytes())
    write_json(
        output / "artifacts.json", {p.name: file_hash(p) for p in output.iterdir() if p.is_file()}
    )
    prepare_inputs(output)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--common", type=Path, required=True)
    parser.add_argument("--retrieval", type=Path, required=True)
    parser.add_argument("--method", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.common, args.retrieval, args.method, args.output), indent=2))
