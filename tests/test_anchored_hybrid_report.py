"""Protect reference-scoring gates, original-source scope and context accounting."""

from copy import deepcopy

import pytest

from occupational_fitness_rag.provenance import digest, write_json
from tools.report_anchored_hybrid import evidence_costs, validate_rankings, verify_bundle


def inventory():
    queries = [
        {"query_id": "q", "case_id": "case", "module": "vision", "licence_context": "commercial"}
    ]
    units = {"source": {"module": "vision", "licence_context": "commercial", "text_sha256": "text"}}
    rows = [
        {
            "query_id": "q",
            "case_id": "case",
            "module": "vision",
            "method": "candidate",
            "experiment_identity": "run",
            "status": "completed",
            "source_ids": ["source"],
            "original_text_hashes": {"source": "text"},
        }
    ]
    return rows, queries, units


def test_inventory_gate_rejects_duplicates_missing_conditions_and_wrong_identity():
    rows, queries, units = inventory()
    validate_rankings(rows, queries, units, ["candidate"], "run")
    for changed in ([], [*rows, *rows]):
        with pytest.raises(ValueError, match="inventory"):
            validate_rankings(changed, queries, units, ["candidate"], "run")
    with pytest.raises(ValueError, match="identity"):
        validate_rankings(rows, queries, units, ["candidate"], "another")


def test_private_evidence_and_modified_original_fingerprint_are_rejected():
    rows, queries, units = inventory()
    changed = deepcopy(units)
    changed["source"]["licence_context"] = "private"
    with pytest.raises(ValueError, match="scope"):
        validate_rankings(rows, queries, changed, ["candidate"])
    changed = deepcopy(rows)
    changed[0]["original_text_hashes"]["source"] = "changed"
    with pytest.raises(ValueError, match="fingerprint"):
        validate_rankings(changed, queries, units, ["candidate"])
    changed[0].update(status="failed", source_ids=["source"])
    with pytest.raises(ValueError, match="substituted"):
        validate_rankings(changed, queries, units, ["candidate"])


def test_artifact_and_self_identity_checks_are_independent(tmp_path):
    data = {"kind": "test"}
    write_json(
        tmp_path / "manifest.json", {**data, "identity": digest(data), "production_change": False}
    )
    from occupational_fitness_rag.evaluation.graph_contract import file_hash

    write_json(
        tmp_path / "artifacts.json", {"manifest.json": file_hash(tmp_path / "manifest.json")}
    )
    assert verify_bundle(tmp_path)[0]["identity"] == digest(data)
    write_json(
        tmp_path / "manifest.json", {**data, "identity": "changed", "production_change": False}
    )
    with pytest.raises(ValueError, match="artifact"):
        verify_bundle(tmp_path)
    write_json(
        tmp_path / "artifacts.json", {"manifest.json": file_hash(tmp_path / "manifest.json")}
    )
    with pytest.raises(ValueError, match="self-identity"):
        verify_bundle(tmp_path)


def test_case_budget_replay_retains_whole_original_exclusions_and_false_facts():
    patient = {
        "licence_context": "commercial",
        "modules": ["vision"],
        "nurse_note": "No diplopia.",
        "verified_patient_facts": {
            "vision.diplopia.present": {"value": False, "patient_quotes": ["No diplopia."]}
        },
    }
    units = {
        sid: {
            "module": "vision",
            "licence_context": "commercial",
            "evidence_text": text,
            "section": "10.3",
            "pdf_page": 222,
            "printed_page": 211,
        }
        for sid, text in (("large", "x" * 9500), ("small", "A complete criterion."))
    }
    rows = [
        {
            "query_id": "q",
            "case_id": "case",
            "module": "vision",
            "method": "candidate",
            "status": "completed",
            "source_ids": ["large", "small"],
        }
    ]
    original = deepcopy(patient)
    records, metrics = evidence_costs(rows, units, {"case": patient})
    assert patient == original
    assert records[0]["allocation"]["documented_modules"] == ["vision"]
    assert records[0]["budget"]["excluded_by_byte_budget"] == ["large"]
    assert records[0]["budget"]["supplied_source_ids"] == ["small"]
    assert metrics[0]["excluded_original_units"] == 1
    assert metrics[0]["mean_top5_original_utf8_bytes"] == 9521
    assert metrics[0]["cases_with_budget_exclusions"] == 1


def test_failed_or_oversized_only_case_is_not_a_ready_judgment_allocation():
    patient = {
        "licence_context": "commercial",
        "modules": ["vision"],
        "nurse_note": "Not measured.",
        "verified_patient_facts": {},
    }
    units = {
        "large": {
            "module": "vision",
            "licence_context": "commercial",
            "evidence_text": "x" * 9500,
            "section": "10.3",
            "pdf_page": 222,
            "printed_page": 211,
        }
    }
    rows = [
        {
            "query_id": "q",
            "case_id": "case",
            "module": "vision",
            "method": "candidate",
            "status": "completed",
            "source_ids": ["large"],
        }
    ]
    records, metrics = evidence_costs(rows, units, {"case": patient})
    assert records[0]["status"] == "blocked"
    assert metrics[0]["excluded_original_units"] == 1
    assert metrics[0]["ready_case_allocations"] == 0
    rows[0].update(status="failed", source_ids=[])
    records, metrics = evidence_costs(rows, units, {"case": patient})
    assert records[0]["status"] == "blocked"
    assert metrics[0]["mean_top5_original_utf8_bytes"] is None
