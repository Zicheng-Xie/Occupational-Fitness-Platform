"""Prepare shared fact-scoped queries, without building indexes or running retrieval.

The readiness gate remains closed until graph identity/mapping validation and the
next corpus/context review are complete. No historical rankings become new results.
"""

import argparse
import json
from pathlib import Path

import yaml

from occupational_fitness_rag.evaluation import applicability_comparison as comparison
from occupational_fitness_rag.evaluation.applicability_judgment import validate_patient_payload
from occupational_fitness_rag.evaluation.comparison_corpus import verify_corpus
from occupational_fitness_rag.evaluation.module_queries import build_module_query
from occupational_fitness_rag.evaluation.passage_comparison import patient_identity, source_snapshot
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json
from tools.build_source_literal_facts import load_snapshot

METHODS = ("vector", "bm25", "hybrid", "graph_local", "lightrag", "graphrag")
PATIENT_FIELDS = ("licence_context", "modules", "nurse_note", "verified_patient_facts")


def prepare_queries(inputs, snapshot, corpus):
    if set(inputs) != set(snapshot["cases"]):
        raise ValueError("Query preparation must cover the complete fact snapshot")
    patients, queries = {}, []
    for case_id, item in sorted(inputs.items()):
        payload = item["payload"]
        validate_patient_payload(payload)
        case = snapshot["cases"][case_id]
        if (
            patient_identity(payload) != case["sensitivity_patient_identity"]
            or payload["verified_patient_facts"] != case["sensitivity_verified_patient_facts"]
        ):
            raise ValueError("Query input differs from the verified source-literal snapshot")
        patient = {key: payload[key] for key in PATIENT_FIELDS}
        if patient["licence_context"] != "commercial":
            raise ValueError("Commercial replay cannot use a private patient context")
        patients[case_id] = patient
        for module in patient["modules"]:
            query, audit = build_module_query(patient, module)
            data = {
                "case_id": case_id, "module": module, "query": query, "query_audit": audit,
                "patient_identity": patient_identity(payload),
                "fact_snapshot_identity": snapshot["identity"],
                "corpus_sha256": corpus["corpus_sha256"], "licence_context": "commercial",
            }
            queries.append({**data, "query_id": digest(data)})
    keys = {(item["case_id"], item["module"]) for item in queries}
    if len(keys) != len(queries):
        raise ValueError("Duplicate case/module query")
    return patients, queries


def build(root, config_path, snapshot_path, output, corpus_path=None):
    root, output = Path(root).resolve(), Path(output).resolve()
    config_text = Path(config_path).read_text(encoding="utf-8")
    config = yaml.safe_load(config_text)
    verified = comparison.load_retrieval(config)
    original = verified["upstream_snapshot"]
    snapshot = load_snapshot(snapshot_path, root)
    corpus = verified["corpus"]
    original_corpus_sha = corpus["corpus_sha256"]
    corpus_file_sha = None
    if corpus_path is not None:
        selected_raw = Path(corpus_path).read_bytes()
        revised = json.loads(selected_raw)
        canonical = {unit["source_id"] for unit in corpus["units"] if "-EXP-" not in unit["source_id"]}
        if revised["document_sha256"] != corpus["document_sha256"] or not canonical <= {
            unit["source_id"] for unit in revised["units"]
        }:
            raise ValueError("Corpus revision must retain the guide edition and canonical sources")
        corpus, corpus_file_sha = revised, sha256_bytes(selected_raw)
    verify_corpus(root, corpus)
    if original["manifest.json"].get("derivation", {}).get("fact_snapshot_identity") != snapshot["identity"]:
        raise ValueError("Expected a fact-sensitivity freeze bound to this snapshot")
    if any(unit["licence_context"] not in {"commercial", "shared"} for unit in corpus["units"]):
        raise ValueError("Private-only evidence entered the shared corpus")
    patients, queries = prepare_queries(original["frozen_inputs.json"], snapshot, corpus)
    planned = [
        {"method": method, "case_id": query["case_id"], "module": query["module"],
         "query_id": query["query_id"], "query_sha256": query["query_audit"]["query_sha256"]}
        for method in METHODS for query in queries
    ]
    plan = {
        "methods": list(METHODS), "top_k": 5, "sensitivity_k": 10,
        "case_count": len(patients), "case_module_scopes": len(queries),
        "planned_retrieval_records": len(planned), "planned": planned,
        "executed_retrieval_calls": 0, "executed_judgment_calls": 0,
        "graph_indexes_built": 0, "ready_for_execution": False,
        "remaining_gates": [
            "Complete independent source/context review of the selected original-PDF corpus",
            "Bind graph indexes to full corpus, model, settings, worker and storage identities",
            "Reject every unmapped graph source and incomplete or duplicate query record",
            "Freeze the common judgment and no-evidence contracts before inference",
        ],
        "scope_note": (
            "New module queries are generated from the source-literal fact version. "
            "Historical rankings and embeddings are not reused as newly executed retrieval. "
            "Reference evidence IDs, reference outcomes and rule outcomes are not query inputs. "
            "The 33 engineering fixtures have been observed before and are not an unseen holdout."
        ),
    }
    identity_data = {
        "kind": "six_method_shared_query_preparation", "fact_snapshot_identity": snapshot["identity"],
        "corpus_sha256": corpus["corpus_sha256"], "patient_inputs_sha256": digest(patients),
        "historical_corpus_sha256": original_corpus_sha, "selected_corpus_file_sha256": corpus_file_sha,
        "queries_sha256": digest(queries), "plan_sha256": digest(plan),
        "upstream_fingerprints": verified["fingerprints"],
        "source_snapshot": source_snapshot(config_text),
        "builder_source": Path(__file__).read_text(encoding="utf-8"),
        "clinical_review": "pending", "production_change": False,
    }
    manifest = {**identity_data, "identity": digest(identity_data)}
    upstream = Path(config["retrieval_dir"]).resolve()
    if not output.is_relative_to(root) or (
        output == upstream or output.is_relative_to(upstream) or upstream.is_relative_to(output)
    ):
        raise ValueError("Shared query preparation must be a separate project directory")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Preserve previous preparations; select a new empty output")
    output.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "manifest.json": manifest, "patients.json": patients, "queries.json": queries,
        "plan.json": plan, "corpus.json": corpus,
    }
    for name, data in artifacts.items():
        write_json(output / name, data)
    write_json(output / "artifacts.json", {
        "identity": manifest["identity"],
        "artifacts": {name: sha256_bytes((output / name).read_bytes()) for name in artifacts},
    })
    return {
        "identity": manifest["identity"], "cases": len(patients), "module_queries": len(queries),
        "planned_retrieval_records": len(planned), "retrieval_executed": False,
        "ready_for_execution": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/experiments/applicability_fact_sensitivity_v3.yaml")
    parser.add_argument("--snapshot", default="outputs/experiments/source_literal_facts_v1")
    parser.add_argument("--output", default="outputs/experiments/six_method_query_preparation_v1")
    parser.add_argument("--corpus", help="Explicit separately versioned original-PDF corpus revision")
    args = parser.parse_args()
    print(json.dumps(build(Path(__file__).resolve().parents[1], args.config, args.snapshot, args.output, args.corpus), indent=2))
