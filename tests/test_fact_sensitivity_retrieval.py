"""Keep the evidence axis fixed when changing a source-literal input version."""

from copy import deepcopy

import pytest

from occupational_fitness_rag.evaluation.passage_comparison import patient_identity
from occupational_fitness_rag.provenance import digest
from tools.build_fact_sensitivity_retrieval import build_artifacts, replace_facts


def fixture():
    payload = {
        "licence_context": "commercial",
        "modules": ["diabetes"],
        "nurse_note": "diabetes.present = false",
        "verified_patient_facts": {},
        "guideline_evidence": [
            {
                "source_id": "original-source",
                "module": "diabetes",
                "pdf_page": 4,
                "printed_page": 2,
                "section": "3.1",
                "source_text": "Complete original wording.",
            }
        ],
    }
    facts = {"diabetes.present": {"value": False, "patient_quotes": [payload["nurse_note"]]}}
    updated = {**payload, "verified_patient_facts": facts}
    case = {
        "original_patient_identity": patient_identity(payload),
        "sensitivity_patient_identity": patient_identity(updated),
        "original_verified_patient_facts": {},
        "sensitivity_verified_patient_facts": facts,
    }
    return payload, case


def test_false_value_is_preserved_without_changing_original_evidence_or_wording():
    payload, case = fixture()
    before = deepcopy(payload)
    updated = replace_facts(payload, case)
    assert payload == before
    assert updated["verified_patient_facts"]["diabetes.present"]["value"] is False
    assert updated["guideline_evidence"] == before["guideline_evidence"]
    assert updated["nurse_note"] == before["nurse_note"]


def test_changed_patient_binding_rejected():
    payload, case = fixture()
    payload["nurse_note"] += " A different patient observation."
    with pytest.raises(ValueError, match="not bound"):
        replace_facts(payload, case)


def test_reference_metadata_cannot_be_inserted_as_fact_metadata():
    payload, case = fixture()
    case["sensitivity_verified_patient_facts"]["diabetes.present"]["expected_outcome"] = "sentinel"
    case["sensitivity_patient_identity"] = patient_identity(
        {**payload, "verified_patient_facts": case["sensitivity_verified_patient_facts"]}
    )
    with pytest.raises(ValueError, match="Unexpected verified-fact metadata"):
        replace_facts(payload, case)


def test_derivation_pins_facts_without_claiming_fresh_retrieval_and_is_self_consistent():
    payload, case = fixture()
    original = {
        "manifest.json": {
            "identity": "original-freeze",
            "config": {"top_k": 5},
            "config_sha256": "old-config",
            "sources_sha256": "old-code",
            "historical_fingerprints": {},
            "environment": {},
            "patient_inputs_sha256": "old-facts",
            "corpus_sha256": "same-corpus",
            "planned_keys": [],
        },
        "frozen_inputs.json": {
            "case": {
                "payload": payload,
                "reference_payload": payload,
                "reference_outcome": "not-consulted-sentinel",
            }
        },
        "payloads.json": {
            "case": {
                policy: {
                    "status": "completed",
                    "payload": deepcopy(payload),
                    "input_sha256": digest(payload),
                    "selection": {"policy": policy},
                }
                for policy in ["module_query", "reference_evidence"]
            }
        },
        "source_snapshot.json": {"first_party_source": {}},
        "corpus.json": {"corpus_sha256": "same-corpus"},
        "retrieval.json": {"identity": "original-freeze", "records": [{"query": "OLD"}]},
        "embeddings.json": {"identity": "original-freeze", "vectors": [[1, 2]]},
    }
    snapshot = {
        "version": "source_literal_facts_v1",
        "identity": "fact-version",
        "metadata": {"retrieval_identity": "original-freeze"},
        "cases": {"case": case},
    }
    before = deepcopy(original)
    output = build_artifacts(original, snapshot, "builder code", {"original": "raw-pin"})
    assert original == before
    assert output["retrieval.json"]["records"] == original["retrieval.json"]["records"]
    assert output["retrieval.json"]["new_calls"] == 0
    assert output["frozen_inputs.json"]["case"]["reference_outcome"] == "not-consulted-sentinel"
    manifest = output["manifest.json"]
    assert manifest["sources_sha256"] == digest(output["source_snapshot.json"])
    assert manifest["patient_inputs_sha256"] == digest(output["frozen_inputs.json"])
    assert output["derivation.json"] == manifest["derivation"]
    assert output["derivation.json"]["original_files_sha256"] == {"original": "raw-pin"}
    selected = output["payloads.json"]["case"]["module_query"]
    assert selected["payload"]["guideline_evidence"] == payload["guideline_evidence"]
    assert selected["input_sha256"] != selected["original_input_sha256"]
