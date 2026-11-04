import json
from copy import deepcopy

import pytest

from tools.report_revision_judgments import REVISION, failure_category, pair_runs, validate_evidence


def fixture():
    payload = {
        "modules": ["diabetes"],
        "verified_patient_facts": {"insulin": False},
        "guideline_evidence": [
            {
                "source_id": "a",
                "source_text": "Original criterion.",
                "module": "diabetes",
                "section": "3.3",
                "pdf_page": 112,
                "printed_page": 101,
            }
        ],
    }
    body = {
        "model": "judge",
        "options": {"temperature": 0, "seed": 0},
        "format": {"type": "object"},
        "messages": [
            {"role": "system", "content": "Use supplied originals."},
            {"role": "user", "content": json.dumps(payload)},
        ],
    }
    baseline = [
        {
            "case_id": "case",
            "model": "judge",
            "repeat": 1,
            "method": "hybrid",
            "request_identity": "before",
            "status": "completed",
            "answer": {"assessment_outcome": "reference"},
        }
    ]
    candidate = deepcopy(baseline)
    candidate[0].update(method=REVISION, request_identity="after")
    labels = {"case": {"reference_outcome": "reference", "cohort": "engineering"}}
    return baseline, candidate, {"before": body}, {"after": deepcopy(body)}, labels


def test_paired_regression_and_insufficiency_are_engineering_disagreement():
    args = fixture()
    args[1][0]["answer"]["assessment_outcome"] = "insufficient_information"
    pairs, _ = pair_runs(*args)
    assert pairs[0]["change"] == "correct_to_wrong"
    assert pairs[0]["candidate_insufficient_against_other_engineering_reference"] is True
    assert pairs[0]["independent_support_review"] == "pending"


@pytest.mark.parametrize("drift", ["patient_type", "temperature", "schema", "system", "model"])
def test_pair_rejects_non_retrieval_changes(drift):
    args = fixture()
    body = args[3]["after"]
    if drift == "patient_type":
        payload = json.loads(body["messages"][1]["content"])
        payload["verified_patient_facts"]["insulin"] = 0
        body["messages"][1]["content"] = json.dumps(payload)
    elif drift == "temperature":
        body["options"]["temperature"] = 1
    elif drift == "schema":
        body["format"] = {"type": "string"}
    elif drift == "system":
        body["messages"][0]["content"] = "Different judge."
    else:
        body["model"] = "other"
    with pytest.raises(ValueError):
        pair_runs(*args)


@pytest.mark.parametrize("inventory", ["missing", "duplicate"])
def test_pair_requires_exact_condition_inventory(inventory):
    args = fixture()
    args[1][:] = [] if inventory == "missing" else args[1] * 2
    with pytest.raises(ValueError, match="inventory"):
        pair_runs(*args)


def test_citation_failure_remains_failure_not_a_wrong_classification():
    args = fixture()
    args[1][0].update(
        status="failed",
        error="ValueError: Evidence-grounded judgment requires a supplied source citation",
    )
    args[1][0].pop("answer")
    pairs, _ = pair_runs(*args)
    assert pairs[0]["change"] == "run_or_contract_failure"
    assert pairs[0]["candidate_failure_category"] == "citation_contract_failure"
    assert not pairs[0]["candidate_insufficient_against_other_engineering_reference"]
    assert (
        failure_category({"status": "failed", "error": "Connection failed"})
        == "other_run_or_contract_failure"
    )


def test_only_source_enumeration_may_change_with_supplied_originals():
    args = fixture()
    for name, request in (("before", args[2]), ("after", args[3])):
        body = request[name]
        body["format"] = {"properties": {"source_ids": {"items": {"enum": ["a"]}}}}
    after = args[3]["after"]
    payload = json.loads(after["messages"][1]["content"])
    payload["guideline_evidence"][0]["source_id"] = "b"
    after["messages"][1]["content"] = json.dumps(payload)
    after["format"]["properties"]["source_ids"]["items"]["enum"] = ["b"]
    pairs, _ = pair_runs(*args)
    assert pairs[0]["added_source_ids"] == ["b"]
    after["format"]["properties"]["source_ids"]["items"]["enum"] = ["foreign"]
    with pytest.raises(ValueError, match="enumeration"):
        pair_runs(*args)


@pytest.mark.parametrize("change", ["text", "page", "private", "unknown", "duplicate"])
def test_evidence_requires_exact_scoped_original(change):
    payload = json.loads(fixture()[2]["before"]["messages"][1]["content"])
    unit = {
        **payload["guideline_evidence"][0],
        "evidence_text": "Original criterion.",
        "licence_context": "commercial",
    }
    units = {"a": unit}
    validate_evidence(payload, units)
    if change == "text":
        payload["guideline_evidence"][0]["source_text"] = "Altered."
    elif change == "page":
        payload["guideline_evidence"][0]["pdf_page"] = 999
    elif change == "private":
        unit["licence_context"] = "private"
    elif change == "unknown":
        payload["guideline_evidence"][0]["source_id"] = "injected"
    else:
        payload["guideline_evidence"].append(deepcopy(payload["guideline_evidence"][0]))
    with pytest.raises(ValueError):
        validate_evidence(payload, units)
