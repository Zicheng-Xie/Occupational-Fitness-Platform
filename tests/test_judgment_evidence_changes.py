from copy import deepcopy

import pytest

from tools.report_judgment_evidence_changes import compare_evidence


def inputs():
    before = {
        "verified_patient_facts": {"present": False, "count": 0},
        "nurse_note": "Original note.",
        "guideline_evidence": [
            {"source_id": "a", "source_text": "Complete criterion."},
            {"source_id": "b", "source_text": "Complete qualification."},
        ],
    }
    after = deepcopy(before)
    after["guideline_evidence"] = [
        after["guideline_evidence"][1],
        {"source_id": "c", "source_text": "Another original criterion."},
        after["guideline_evidence"][0],
    ]
    return before, after


def test_evidence_join_preserves_added_removed_and_actual_order():
    before, after = inputs()
    result = compare_evidence(before, after)
    assert result["added_source_ids"] == ["c"]
    assert result["removed_source_ids"] == []
    assert result["common_source_rank_changes"] == [
        {"source_id": "a", "baseline_rank": 1, "candidate_rank": 3},
        {"source_id": "b", "baseline_rank": 2, "candidate_rank": 1},
    ]


@pytest.mark.parametrize("change", ["fact_type", "original_source"])
def test_changed_fact_type_or_same_id_with_changed_original_is_not_attributed_to_retrieval(change):
    before, after = inputs()
    if change == "fact_type":
        after["verified_patient_facts"]["present"] = 0
    else:
        after["guideline_evidence"][0]["source_text"] = "Changed qualification."
    with pytest.raises(ValueError):
        compare_evidence(before, after)
