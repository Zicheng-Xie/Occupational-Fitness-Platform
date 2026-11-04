"""Validate frozen replay inputs and first-stage budgets without model inference."""

import argparse
import json
from collections import Counter
from pathlib import Path

import yaml

from occupational_fitness_rag.evaluation import applicability_comparison as experiment
from occupational_fitness_rag.evaluation import applicability_judgment, passage_judgment
from occupational_fitness_rag.evaluation import passage_comparison as previous
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json


def preflight(config_path, output_path):
    config_path, output_path = Path(config_path), Path(output_path)
    config_text = config_path.read_text(encoding="utf-8")
    config = yaml.safe_load(config_text)
    experiment.validate_config(config)
    frozen = experiment.load_retrieval(config)
    environment = previous.pinned_environment(config)
    sources = previous.source_snapshot(config_text)
    rows = []
    for case_id in config["case_ids"]:
        identities = set()
        for policy in config["evidence_policies"]:
            selected = frozen["payloads"][case_id][policy]
            if selected["status"] != "completed":
                raise ValueError("Frozen evidence failed: " + case_id + " " + policy)
            payload = selected["payload"]
            identities.add(previous.patient_identity(payload))
            for model in config["models"]:
                for protocol in config["protocols"]:
                    if protocol == "passage_selection":
                        body = passage_judgment.build_request(config, model, payload, protocol)
                    else:
                        body = applicability_judgment.build_applicability_request(
                            config, model, payload
                        )
                    size = len(previous.json_bytes(body))
                    if size > config["request_max_bytes"]:
                        raise ValueError("First-stage request exceeds its byte limit")
                    rows.append(
                        {
                            "case_id": case_id,
                            "policy": policy,
                            "model": model,
                            "protocol": protocol,
                            "patient_sha256": previous.patient_identity(payload),
                            "input_sha256": selected["input_sha256"],
                            "first_request_sha256": digest(body),
                            "first_request_bytes": size,
                            "facts": len(payload["verified_patient_facts"]),
                            "original_passages": len(payload["guideline_evidence"]),
                        }
                    )
        if len(identities) != 1:
            raise ValueError("Evidence policies change the frozen patient")
    report = {
        "status": "ready_no_model_inference_performed",
        "config": str(config_path),
        "config_sha256": sha256_bytes(config_text.encode("utf-8")),
        "tool_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "source_snapshot_sha256_at_preflight": digest(sources),
        "upstream_identity": frozen["manifest"]["identity"],
        "upstream_fingerprints": frozen["fingerprints"],
        "corpus_sha256": frozen["corpus"]["corpus_sha256"],
        "environment": environment,
        "case_count": len(config["case_ids"]),
        "planned_conditions": len(rows) * config["repeats"],
        "reference_outcomes": dict(Counter(frozen["labels"].values())),
        "largest_first_stage_request_bytes": max(row["first_request_bytes"] for row in rows),
        "limitations": [
            "Aggregation requests depend on stage-one outputs and remain checked at runtime.",
            "First-stage byte checks do not establish semantic or clinical correctness.",
            "All cases were previously seen; this is not an unseen holdout.",
            "Model metadata requests do not perform inference.",
        ],
        "conditions_before_repeats": rows,
    }
    write_json(output_path, report)
    return {key: value for key, value in report.items() if key != "conditions_before_repeats"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(preflight(args.config, args.output), indent=2))
