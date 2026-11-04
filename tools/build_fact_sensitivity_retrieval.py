"""Freeze a held-evidence sensitivity arm; never rerun or relabel historical retrieval."""

import argparse
import json
from copy import deepcopy
from pathlib import Path

from occupational_fitness_rag.evaluation import applicability_comparison as comparison
from occupational_fitness_rag.evaluation import passage_comparison as previous
from occupational_fitness_rag.evaluation.applicability_judgment import validate_patient_payload
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json


def replace_facts(payload, case):
    """Change only the versioned facts; original passages and patient wording stay exact."""
    if (
        previous.patient_identity(payload) != case["original_patient_identity"]
        or payload["verified_patient_facts"] != case["original_verified_patient_facts"]
    ):
        raise ValueError("Fact snapshot is not bound to this original patient input")
    updated = deepcopy(payload)
    updated["verified_patient_facts"] = deepcopy(case["sensitivity_verified_patient_facts"])
    validate_patient_payload(updated)
    if previous.patient_identity(updated) != case["sensitivity_patient_identity"]:
        raise ValueError("Sensitivity patient identity differs from its snapshot")
    if any(updated[key] != payload[key] for key in payload if key != "verified_patient_facts"):
        raise ValueError("Held-evidence sensitivity changed another input dimension")
    return updated


def build_artifacts(original, snapshot, builder_source, original_pins=None):
    """Derive a complete new freeze with an explicit historical retrieval origin."""
    manifest = original["manifest.json"]
    cases = original["frozen_inputs.json"]
    if set(cases) != set(snapshot["cases"]):
        raise ValueError("Sensitivity snapshot must cover the complete frozen case inventory")
    if snapshot["metadata"]["retrieval_identity"] != manifest["identity"]:
        raise ValueError("Fact snapshot belongs to another retrieval freeze")
    inputs, payloads = deepcopy(cases), deepcopy(original["payloads.json"])
    original_evidence = {}
    for case_id, item in inputs.items():
        case = snapshot["cases"][case_id]
        for field in ["payload", "reference_payload"]:
            item[field] = replace_facts(item[field], case)
        original_evidence[case_id] = {}
        for policy, selected in payloads[case_id].items():
            if selected["status"] != "completed":
                raise ValueError(
                    "A failed original retrieval cannot become a completed sensitivity arm"
                )
            old = selected["payload"]
            if digest(old) != selected["input_sha256"]:
                raise ValueError("Original prepared payload fingerprint is invalid")
            original_evidence[case_id][policy] = digest(old["guideline_evidence"])
            selected["original_input_sha256"] = selected["input_sha256"]
            selected["payload"] = replace_facts(old, case)
            selected["input_sha256"] = digest(selected["payload"])
            selected["selection"]["fact_condition"] = snapshot["version"]
            selected["selection"]["retrieval_origin"] = "held_original_query_and_evidence"
            if (
                digest(selected["payload"]["guideline_evidence"])
                != original_evidence[case_id][policy]
            ):
                raise ValueError("Sensitivity evidence changed")
    derivation = {
        "kind": "source_literal_fact_sensitivity_with_held_evidence",
        "original_retrieval_identity": manifest["identity"],
        "fact_snapshot_identity": snapshot["identity"],
        "fact_version": snapshot["version"],
        "retrieval_executed": False,
        "original_queries_retained": True,
        "original_evidence_sha256": original_evidence,
        "new_embedding_calls": 0,
        "new_retrieval_calls": 0,
        "clinical_review": "pending",
        "production_change": False,
        "original_files_sha256": original_pins or {},
        "scope": (
            "Only verified_patient_facts changes. Historical queries, rankings, Top-5 original "
            "passages, labels, models and budgets remain fixed. This isolates a source-literal "
            "engineering input sensitivity, not end-to-end retrieval improvement."
        ),
    }
    source = deepcopy(original["source_snapshot.json"])
    source["held_evidence_derivation"] = {
        "builder_content": builder_source,
        "builder_sha256": sha256_bytes(builder_source.encode("utf-8")),
        "fact_snapshot": snapshot,
        "derivation": derivation,
    }
    identity_data = {
        field: deepcopy(manifest[field]) for field in comparison.UPSTREAM_IDENTITY_FIELDS
    }
    identity_data["config"]["fact_condition"] = snapshot["version"]
    identity_data["config"]["preparation_kind"] = derivation["kind"]
    identity_data["config_sha256"] = digest(identity_data["config"])
    identity_data["sources_sha256"] = digest(source)
    identity_data["patient_inputs_sha256"] = digest(inputs)
    identity_data["historical_fingerprints"]["fact_snapshot_identity"] = snapshot["identity"]
    identity_data["historical_fingerprints"]["original_preparation_identity"] = manifest["identity"]
    identity = digest(identity_data)
    new_manifest = {
        **deepcopy(manifest),
        **identity_data,
        "identity": identity,
        "preparation_kind": derivation["kind"],
        "derivation": derivation,
    }
    artifacts = {
        "manifest.json": new_manifest,
        "source_snapshot.json": source,
        "frozen_inputs.json": inputs,
        "corpus.json": original["corpus.json"],
        "payloads.json": payloads,
        "derivation.json": derivation,
        "fact_snapshot.json": snapshot,
    }
    for name in ["retrieval.json", "embeddings.json"]:
        # Original records are preserved verbatim as data, with their historical
        # origin explicit. No old call/time is presented as newly executed work.
        value = deepcopy(original[name])
        value["original_identity"] = value["identity"]
        value["identity"] = identity
        value["reuse_kind"] = "historical_held_query_and_evidence"
        value["new_calls"] = 0
        artifacts[name] = value
    return artifacts


def build(root, config_path, snapshot_path, output):
    import yaml

    from tools.build_source_literal_facts import load_snapshot

    root, output = Path(root).resolve(), Path(output).resolve()
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    original_dir = Path(config["retrieval_dir"]).resolve()
    if (
        not output.is_relative_to(root)
        or output == original_dir
        or output.is_relative_to(original_dir)
        or original_dir.is_relative_to(output)
    ):
        raise ValueError("Derived freeze must be a separate project directory")
    # Complete original-passage provenance is checked before any artifact is written.
    verified = comparison.load_retrieval(config)
    original = verified["upstream_snapshot"]
    snapshot = load_snapshot(snapshot_path, root)
    original_pins = {name: sha256_bytes((original_dir / name).read_bytes()) for name in original}
    artifacts = build_artifacts(
        original, snapshot, Path(__file__).read_text(encoding="utf-8"), original_pins
    )
    if output.exists() and any(output.iterdir()):
        raise ValueError("Derived freeze output must be empty; historical freezes are immutable")
    output.mkdir(parents=True, exist_ok=True)
    for name, value in artifacts.items():
        write_json(output / name, value)
    write_json(
        output / "retrieval_freeze.json",
        {
            "identity": artifacts["manifest.json"]["identity"],
            "artifacts": {
                name: sha256_bytes((output / name).read_bytes())
                for name in ["retrieval.json", "payloads.json", "embeddings.json"]
            },
        },
    )
    return {
        "identity": artifacts["manifest.json"]["identity"],
        "cases": len(snapshot["cases"]),
        "changed_cases": snapshot["metadata"]["changed_case_count"],
        "restored_fields": snapshot["metadata"]["restored_field_count"],
        "new_retrieval_calls": 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", default="configs/experiments/applicability_comparison_full33_original.yaml"
    )
    parser.add_argument(
        "--snapshot", default="outputs/experiments/source_literal_facts_v1/source_literal_facts.json"
    )
    parser.add_argument("--output", default="outputs/experiments/source_literal_retrieval_v1")
    args = parser.parse_args()
    print(
        json.dumps(
            build(Path(__file__).resolve().parents[1], args.config, args.snapshot, args.output)
        )
    )
