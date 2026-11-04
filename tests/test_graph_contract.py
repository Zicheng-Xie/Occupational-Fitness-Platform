"""Index reuse and partial execution must fail visibly on identity drift."""

import json

import pytest

from occupational_fitness_rag.evaluation.graph_contract import (
    file_hash,
    fingerprint,
    storage_files,
    validate_records,
    verify_index,
    verify_request,
)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def frozen_index(tmp_path):
    work = tmp_path / "hypertension"
    write(work / work.name / "kv_store_full_docs.json", {"original": "guide text"})
    write(work / "source_mapping.json", {"chunk1": ["original"]})
    write(work / "index_complete.json", {"documents": 1})
    contract = {"corpus_sha256": "corpus", "model_digest": "weights", "worker_sha256": "code"}
    write(work / "index_manifest.json", {
        "contract": contract, "contract_sha256": fingerprint(contract),
        "storage_sha256": storage_files(work, "lightrag"),
        "source_mapping_sha256": file_hash(work / "source_mapping.json"),
        "completion_sha256": file_hash(work / "index_complete.json"),
    })
    return work, contract


@pytest.mark.parametrize("field", ["corpus_sha256", "model_digest", "worker_sha256"])
def test_other_corpus_weights_or_worker_cannot_reuse_index(tmp_path, field):
    work, contract = frozen_index(tmp_path)
    with pytest.raises(ValueError, match="identity differs"):
        verify_index(work, "lightrag", {**contract, field: "changed"})


@pytest.mark.parametrize("name", ["source_mapping.json", "index_complete.json", "hypertension/kv_store_full_docs.json"])
def test_mapping_storage_and_completion_drift_are_detected(tmp_path, name):
    work, contract = frozen_index(tmp_path)
    write(work / name, {"changed": True})
    with pytest.raises(ValueError, match="changed"):
        verify_index(work, "lightrag", contract)


def test_query_cache_can_grow_without_mutating_frozen_index(tmp_path):
    work, contract = frozen_index(tmp_path)
    write(work / work.name / "kv_store_llm_response_cache.json", {"query": "keywords"})
    verify_index(work, "lightrag", contract)


def query_and_row():
    query = {"query_id": "q1", "case_id": "c1", "module": "vision", "query_audit": {"query_sha256": "text"}}
    row = {"query_id": "q1", "case_id": "c1", "module": "vision", "query_sha256": "text",
           "method": "lightrag", "experiment_identity": "run", "status": "completed", "source_ids": ["source"]}
    return query, row, [{"source_id": "source", "module": "vision"}]


def test_partial_result_is_not_complete_and_duplicate_result_is_rejected():
    q, row, units = query_and_row()
    assert validate_records([], [q], "lightrag", units, "run") == set()
    with pytest.raises(ValueError, match="duplicate"):
        validate_records([row, row], [q], "lightrag", units, "run")


def test_failed_external_framework_cannot_return_substitute_evidence():
    q, row, units = query_and_row()
    with pytest.raises(ValueError, match="no substitute"):
        validate_records([{**row, "status": "index_failed", "error": "failed"}], [q], "lightrag", units, "run")


def test_out_of_module_original_is_rejected():
    q, row, units = query_and_row()
    with pytest.raises(ValueError, match="outside its module"):
        validate_records([row], [q], "lightrag", [{**units[0], "module": "diabetes"}], "run")


def test_request_self_identity_checked_before_touching_corpus():
    with pytest.raises(ValueError, match="request identity"):
        verify_request({"request_identity": "wrong", "method": "lightrag"}, "lightrag")
