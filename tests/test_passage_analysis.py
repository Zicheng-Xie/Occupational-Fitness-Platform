"""Paired effects and unresolved raw-ID review records must remain auditable."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from occupational_fitness_rag.evaluation.passage_analysis import (
    analyze,
    export_analysis,
    review_rows,
)
from occupational_fitness_rag.evaluation.passage_comparison import KEY_FIELDS
from occupational_fitness_rag.evaluation.passage_judgment import passage_catalogue
from occupational_fitness_rag.provenance import digest, sha256_bytes


def payload():
    return {
        "licence_context": "commercial",
        "modules": ["vision"],
        "nurse_note": "Synthetic case, observed indicator, not a real patient.",
        "verified_patient_facts": {
            "vision.indicator": {"value": True, "patient_quotes": ["observed indicator"]}
        },
        "guideline_evidence": [
            {
                "source_id": "fixture-source",
                "source_text": "Synthetic original criterion; a hold applies until verified review.",
                "module": "vision",
                "pdf_page": 1,
                "section": "1.1",
            }
        ],
    }


def row(protocol, policy="mixed_query", correct=False):
    data = payload()
    pid = next(iter(passage_catalogue(data)))
    check = {
        "module": "vision",
        "passage_id": pid,
        "fact_fields": ["vision.indicator"],
        "finding": "established_restriction",
        "licence_pathway": "temporary_no_driving",
        "conclusion": "The observed indicator requires review.",
    }
    answer = {"assessment_outcome": "temporarily_unfit" if correct else "insufficient_information"}
    request = {
        "model": "fixture-model",
        "messages": [{"role": "user", "content": json.dumps(data)}],
    }
    return {
        "model": "fixture-model",
        "model_digest": "fixture-digest",
        "case_id": "fixture-case",
        "evidence_policy": policy,
        "protocol": protocol,
        "repeat": 0,
        "experiment_identity": "fixture-experiment",
        "input_snapshot": data,
        "input_sha256": digest(data),
        "status": "completed",
        "answer": answer,
        "reference_outcome": "temporarily_unfit",
        "attempts": [
            {
                "number": 1,
                "status": "completed",
                "answer": answer,
                "request": request,
                "request_sha256": digest(request),
                "raw_response": {
                    "message": {"content": json.dumps({**answer, "criterion_checks": [check]})}
                },
            }
        ],
    }


def manifest(rows):
    return {
        "planned_keys": [[r[k] for k in KEY_FIELDS] for r in rows],
        "planned_conditions": len(rows),
        "identity": "fixture-experiment",
        "environment": {"model_digests": {"fixture-model": "fixture-digest"}},
        "phase": "targeted_diagnostic_development_set",
    }


def test_protocol_and_query_effects_have_separate_same_input_pairs():
    rows = [
        row("quote_contract"),
        row("passage_selection", correct=True),
        row("quote_contract", "module_query", True),
        row("passage_selection", "module_query", True),
    ]
    result = analyze(rows, manifest(rows))
    assert result["execution_status"] == "completed"
    assert {p["axis"] for p in result["pairs"]} == {"protocol", "evidence_policy"}
    assert any(
        p["transition"] == "wrong_to_correct" and p["axis"] == "protocol" for p in result["pairs"]
    )
    assert any(
        p["transition"] == "wrong_to_correct" and p["axis"] == "evidence_policy"
        for p in result["pairs"]
    )
    assert all(p["identity_eligible"] for p in result["pairs"])


def test_same_count_unexpected_case_cannot_be_certified_complete():
    rows = [row("quote_contract")]
    plan = manifest(rows)
    rows[0]["case_id"] = "unexpected-case"
    with pytest.raises(ValueError, match="unexpected"):
        analyze(rows, plan)


def test_missing_expected_condition_is_partial_and_exposed():
    rows = [row("quote_contract"), row("passage_selection")]
    result = analyze(rows[:1], manifest(rows))
    assert result["execution_status"] == "partial" and len(result["missing_conditions"]) == 1


@pytest.mark.parametrize("change", ["request", "model", "payload"])
def test_changed_request_model_or_patient_payload_cannot_pass_integrity(change):
    rows = [row("passage_selection")]
    plan = manifest(rows)
    if change == "request":
        rows[0]["attempts"][0]["request"]["model"] = "modified"
    elif change == "model":
        rows[0]["model_digest"] = "modified"
    else:
        rows[0]["input_snapshot"]["nurse_note"] += " Modified."
    with pytest.raises(ValueError, match="fingerprint|digest"):
        analyze(rows, plan)


def test_raw_failed_passage_choice_is_resolved_but_never_approved():
    record = row("passage_selection")
    record["status"] = record["attempts"][0]["status"] = "failed"
    before = deepcopy(record)
    items = review_rows([record])
    assert record == before and len(items) == 1
    assert items[0]["attempt_status"] == "failed"
    assert items[0]["mechanical_provenance"] == "program_resolved_full_passage"
    assert items[0]["resolved_source_id"] == "fixture-source"
    assert items[0]["support_status"] == items[0]["clinical_review_status"] == "pending"
    assert "passage_id" in json.loads(items[0]["proposed_check_json"])
    assert "guideline_quote" not in json.loads(items[0]["proposed_check_json"])


def test_unknown_raw_passage_id_remains_unresolved_without_corpus_search():
    record = row("passage_selection")
    proposed = json.loads(record["attempts"][0]["raw_response"]["message"]["content"])
    proposed["criterion_checks"][0]["passage_id"] = "not-in-this-bundle"
    record["attempts"][0]["raw_response"]["message"]["content"] = json.dumps(proposed)
    item = review_rows([record])[0]
    assert item["mechanical_provenance"] == "unresolved"
    assert item["resolved_source_id"] is None
    assert item["original_quote_spans_json"] == "[]"


def test_malformed_passage_id_cannot_fall_back_to_injected_source_quote():
    record = row("passage_selection")
    proposed = json.loads(record["attempts"][0]["raw_response"]["message"]["content"])
    proposed["criterion_checks"][0].update(
        passage_id=["invalid-identifier-shape"],
        source_id="fixture-source",
        guideline_quote=payload()["guideline_evidence"][0]["source_text"],
    )
    record["attempts"][0]["raw_response"]["message"]["content"] = json.dumps(proposed)
    item = review_rows([record])[0]
    assert item["mechanical_provenance"] == "unresolved"
    assert item["resolved_source_id"] is None
    assert json.loads(item["proposed_check_json"])["source_id"] == "fixture-source"


def test_export_hash_and_rows_use_one_snapshot_when_inference_appends(tmp_path, monkeypatch):
    records = [row("passage_selection"), row("quote_contract")]
    plan = manifest(records)
    snapshot = {"first_party_source": {"fixture.py": "frozen first-party source"}}
    plan["sources_sha256"] = digest(snapshot)
    (tmp_path / "manifest.json").write_text(json.dumps(plan), encoding="utf-8")
    (tmp_path / "source_snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")
    frozen = {"identity": plan["identity"], "artifacts": {}}
    (tmp_path / "retrieval_freeze.json").write_text(json.dumps(frozen), encoding="utf-8")
    results = tmp_path / "results.jsonl"
    first = (json.dumps(records[0]) + "\n").encode("utf-8")
    second = (json.dumps(records[1]) + "\n").encode("utf-8")
    results.write_bytes(first)
    original_read = Path.read_bytes
    reads = 0

    def append_after_snapshot(path):
        nonlocal reads
        data = original_read(path)
        if path == results:
            reads += 1
            if reads == 1:
                with results.open("ab") as stream:
                    stream.write(second)
        return data

    monkeypatch.setattr(Path, "read_bytes", append_after_snapshot)
    exported = export_analysis(tmp_path)
    actual = json.loads((tmp_path / "paired_analysis.json").read_text(encoding="utf-8"))
    assert reads == 1
    assert exported["recorded_conditions"] == 1 and exported["execution_status"] == "partial"
    assert actual["provenance"]["results_sha256"] == sha256_bytes(first)
    assert actual["provenance"]["results_bytes"] == len(first)
    assert original_read(results) == first + second
