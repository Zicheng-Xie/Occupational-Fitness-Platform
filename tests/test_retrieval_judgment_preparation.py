"""The next judgment experiment must vary evidence, never patient facts or labels."""

import json

import pytest

from occupational_fitness_rag.evaluation.judgment_comparison import judgment_request
from tools.prepare_retrieval_judgments import common_evidence


def inputs():
    patient = {"licence_context": "commercial", "modules": ["hypertension"],
               "nurse_note": "Repeated BP 178/106; no medication side effects.",
               "verified_patient_facts": {"cardiovascular.blood_pressure.persistent_systolic": {
                   "value": 178, "patient_quotes": ["Repeated BP 178/106"]}}}
    units = {sid: {"module": "hypertension", "licence_context": "commercial", "evidence_text": text,
                   "section": "2.3.1", "pdf_page": 99, "printed_page": 88}
             for sid, text in (("a", "A complete original criterion."), ("b", "B complete conditional criterion."))}
    return patient, units


def test_same_patient_and_prompt_across_evidence_and_no_evidence_controls():
    patient, units = inputs()
    full, _ = common_evidence(patient, units, ["a"], 9000)
    empty, _ = common_evidence(patient, units, [], 9000)
    config = {"context_length": 8192, "output_tokens": 2048}
    first, second = [judgment_request(config, "llama3:8b", p) for p in (full, empty)]
    assert first["messages"][0] == second["messages"][0]
    bodies = [json.loads(body["messages"][1]["content"]) for body in (first, second)]
    assert bodies[0]["verified_patient_facts"] == bodies[1]["verified_patient_facts"] == patient["verified_patient_facts"]
    assert bodies[1]["guideline_evidence"] == []
    assert "reference_outcome" not in bodies[0]


def test_budget_keeps_whole_originals_and_records_exclusion():
    patient, units = inputs()
    _, one = common_evidence(patient, units, ["a"], 9000)
    full, allocation = common_evidence(patient, units, ["a", "b"], one["evidence_utf8_bytes"])
    assert allocation["supplied_source_ids"] == ["a"]
    assert allocation["excluded_by_byte_budget"] == ["b"]
    assert full["guideline_evidence"][0]["source_text"] == units["a"]["evidence_text"]


def test_private_only_source_cannot_enter_shared_judge_request():
    patient, units = inputs()
    units["a"]["licence_context"] = "private"
    with pytest.raises(ValueError, match="scope"):
        common_evidence(patient, units, ["a"], 9000)


def test_reference_outcome_cannot_leak_through_patient_input():
    patient, units = inputs()
    patient["reference_outcome"] = "temporarily_unfit"
    with pytest.raises(ValueError, match="metadata"):
        common_evidence(patient, units, ["a"], 9000)
