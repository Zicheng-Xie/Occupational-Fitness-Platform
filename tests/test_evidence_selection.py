"""Evidence allocation contracts; no claim of clinical retrieval quality."""

from copy import deepcopy

import pytest

from occupational_fitness_rag.evaluation.evidence_selection import select_documented_evidence


def test_documented_modules_do_not_compete_with_unmeasured_modules():
    payload = {
        "modules": ["hypertension", "vision", "hearing", "blackout", "diabetes"],
        "verified_patient_facts": {
            "vision.acuity": {"value": "6/12"},
            "blackout.occurred": {"value": True},
        },
    }
    rankings = [
        {"module": module, "source_ids": [f"{module}-{i}" for i in range(4)]}
        for module in payload["modules"]
    ]
    before = deepcopy((payload, rankings))
    selected = select_documented_evidence(payload, rankings)
    assert selected["source_ids"] == [
        "vision-0",
        "blackout-0",
        "vision-1",
        "blackout-1",
        "vision-2",
    ]
    assert selected["documented_modules"] == ["vision", "blackout"]
    assert selected["unmeasured_modules"] == ["hypertension", "hearing", "diabetes"]
    assert selected["policy"]["fallback_to_all_requested"] is False
    assert (payload, rankings) == before


def test_false_zero_and_cardiovascular_fields_are_documented():
    payload = {
        "modules": ["hypertension", "diabetes", "blackout"],
        "verified_patient_facts": {
            "cardiovascular.blood_pressure.reading": {"value": 0},
            "diabetes.present": {"value": False},
            "blackout.occurred": {"value": None, "status": "unknown"},
        },
    }
    selected = select_documented_evidence(
        payload,
        [
            {"module": "hypertension", "source_ids": ["pressure"]},
            {"module": "diabetes", "source_ids": ["diabetes"]},
        ],
    )
    assert selected["documented_modules"] == ["hypertension", "diabetes"]
    assert selected["source_ids"] == ["pressure", "diabetes"]


def test_all_missing_falls_back_without_assuming_normality():
    payload = {"modules": ["vision", "hearing"], "verified_patient_facts": {}}
    result = select_documented_evidence(
        payload,
        [
            {"module": "vision", "source_ids": ["v1", "v2"]},
            {"module": "hearing", "source_ids": ["h1", "h2"]},
        ],
        3,
    )
    assert result["source_ids"] == ["v1", "h1", "v2"]
    assert result["documented_modules"] == []
    assert result["unmeasured_modules"] == payload["modules"]
    assert result["policy"]["fallback_to_all_requested"] is True


def test_deduplication_and_cap_preserve_each_modules_rank_order():
    payload = {
        "modules": ["vision", "hearing"],
        "verified_patient_facts": {"vision.a": {"value": True}, "hearing.b": {"value": False}},
    }
    rankings = [
        {"module": "vision", "source_ids": ["shared", "v2", "v3"]},
        {"module": "hearing", "source_ids": ["shared", "h2", "v3", "h4"]},
    ]
    assert select_documented_evidence(payload, rankings, 5)["source_ids"] == [
        "shared",
        "v2",
        "h2",
        "v3",
        "h4",
    ]
    assert select_documented_evidence(payload, rankings, 2)["source_ids"] == ["shared", "v2"]
    assert select_documented_evidence(payload, rankings, 0)["source_ids"] == []


def test_extra_labels_rules_source_metadata_and_diagnosis_values_cannot_change_allocation():
    payload = {
        "modules": ["blackout"],
        "verified_patient_facts": {"blackout.diagnosis": {"value": "x"}},
    }
    rankings = [{"module": "blackout", "source_ids": ["first", "second"]}]
    clean = select_documented_evidence(payload, rankings)
    payload.update(reference_outcome="fake", rule_outcome="fake", expected_source_ids=["second"])
    payload["verified_patient_facts"]["blackout.diagnosis"]["value"] = "completely different"
    rankings[0].update(reference_source_ids=["second"], expected_outcome="fake")
    assert select_documented_evidence(payload, rankings) == clean


@pytest.mark.parametrize("top_k", [-1, 1.5, True])
def test_invalid_caps_are_rejected(top_k):
    with pytest.raises(ValueError, match="top_k"):
        select_documented_evidence({"modules": [], "verified_patient_facts": {}}, [], top_k)


def test_failed_duplicate_or_missing_rankings_are_not_silently_substituted():
    payload = {"modules": ["blackout"], "verified_patient_facts": {"blackout.a": {"value": True}}}
    with pytest.raises(ValueError, match="Failed retrieval"):
        select_documented_evidence(
            payload, [{"module": "blackout", "source_ids": [], "status": "failed"}]
        )
    with pytest.raises(ValueError, match="exactly one"):
        select_documented_evidence(payload, [{"module": "blackout", "source_ids": []}] * 2)
    with pytest.raises(ValueError, match="missing"):
        select_documented_evidence(payload, [])
