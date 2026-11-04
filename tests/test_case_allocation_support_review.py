import json
from copy import deepcopy

import pytest

from tools.prepare_case_allocation_support_review import (
    ARMS,
    FOCUS_CASES,
    REVIEW_FIELDS,
    _render,
    copy_technical_source_audit,
    require_complete_inventory,
    review_groups,
    worksheet_rows,
)


def observation(method="hybrid", model="model", repeat=0):
    return {
        "case_id": FOCUS_CASES[0],
        "method": method,
        "model": model,
        "repeat": repeat,
        "status": "completed",
        "request_identity": method + model,
        "payload_identity": method,
        "experiment_identity": "frozen",
        "answer": {
            "assessment_outcome": "insufficient_information",
            "explanation": "Unchanged claim <script>.",
            "source_ids": ["S"],
            "fact_fields": ["blackout.occurred"],
        },
    }


def payload():
    return {
        "nurse_note": "Exact original nurse note.",
        "licence_context": "commercial",
        "modules": ["blackout", "vision"],
        "verified_patient_facts": {"blackout.occurred": {"value": True}},
        "guideline_evidence": [
            {
                "source_id": "S",
                "source_text": "Exact original <source>.",
                "section": "1.2.1",
                "pdf_page": 68,
                "printed_page": 57,
            }
        ],
    }


def test_duplicate_contexts_group_without_losing_any_occurrence_keys():
    rows = [observation(), observation("seventh_case_coverage", "second-model", 2)]
    payloads = {(row["case_id"], row["method"]): payload() for row in rows}
    groups = review_groups(rows, payloads)
    assert len(groups) == 1
    assert len(groups[0]["occurrences"]) == 2
    assert groups[0]["occurrences"][1]["method"] == "seventh_case_coverage"
    assert groups[0]["occurrences"][1]["model"] == "second-model"
    assert groups[0]["occurrences"][1]["repeat"] == 2
    assert groups[0]["claim"]["accepted_answer"] == rows[0]["answer"]


@pytest.mark.parametrize("difference", ["explanation", "facts", "original", "citations", "note"])
def test_nonidentical_claims_or_contexts_never_share_a_review(difference):
    a, b = observation(), observation("ninth_case_coverage")
    first, second = payload(), payload()
    if difference == "explanation":
        b["answer"]["explanation"] += " "
    elif difference == "facts":
        second["verified_patient_facts"]["blackout.occurred"]["value"] = False
    elif difference == "original":
        second["guideline_evidence"][0]["source_text"] += " "
    elif difference == "citations":
        b["answer"]["source_ids"] = []
    else:
        second["nurse_note"] += " "
    groups = review_groups(
        [a, b], {(a["case_id"], a["method"]): first, (b["case_id"], b["method"]): second}
    )
    assert len(groups) == 2


def test_all_human_fields_stay_blank_and_engineering_labels_are_not_disclosed():
    row = observation()
    groups = review_groups([row], {(row["case_id"], row["method"]): payload()})
    group_rows, source_rows = worksheet_rows(groups)
    for item in [groups[0]["human_review"], group_rows[0], source_rows[0]]:
        assert all(item[field] == "" for field in REVIEW_FIELDS)
    assert not any("reference" in key or "expected" in key for key in groups[0])
    assert group_rows[0]["accepted_outcome"] == row["answer"]["assessment_outcome"]
    assert (
        source_rows[0]["unchanged_original_text"]
        == payload()["guideline_evidence"][0]["source_text"]
    )
    assert source_rows[0]["cited_by_model"]


def inventory():
    cases = (*FOCUS_CASES, *("C" + str(n) for n in range(31)))
    return [
        {"case_id": case, "method": method, "model": model, "repeat": repeat}
        for case in cases
        for method in ARMS
        for model in ("llama", "qwen")
        for repeat in range(3)
    ]


def test_complete_990_inventory_yields_exactly_60_focus_conditions():
    conditions = inventory()
    focus = require_complete_inventory(conditions, conditions)
    assert len(focus) == 60
    assert {row["case_id"] for row in focus} == set(FOCUS_CASES)


def test_missing_or_duplicate_actual_conditions_never_enter_review_pack():
    conditions = inventory()
    with pytest.raises(ValueError, match="complete frozen 990"):
        require_complete_inventory(conditions[:-1], conditions)
    with pytest.raises(ValueError, match="Duplicate actual"):
        require_complete_inventory([*conditions, conditions[0]], conditions)


def test_three_model_repeats_are_required_not_merely_60_total_rows():
    conditions = inventory()
    changed = deepcopy(conditions)
    changed[0]["repeat"] = 4
    with pytest.raises(ValueError, match="all three repeats"):
        require_complete_inventory(changed, changed)


def test_failed_response_is_not_promoted_to_accepted_judgment():
    row = observation()
    del row["answer"]
    row.update(
        status="failed",
        error="Missing citation",
        raw_response={"message": {"content": "raw unchanged"}},
    )
    group = review_groups([row], {(row["case_id"], row["method"]): payload()})[0]
    assert group["claim"]["accepted_answer"] is None
    assert group["claim"]["unaccepted_response"] == "raw unchanged"
    assert group["claim"]["failure_reason"] == "Missing citation"
    assert group["human_review"] == dict.fromkeys(REVIEW_FIELDS, "")


def test_failed_invalid_citation_is_visible_without_inventing_an_original():
    row = observation()
    del row["answer"]
    row.update(
        status="failed",
        error="Source identifier was not supplied",
        raw_response={"message": {"content": '{"source_ids":["UNKNOWN"]}'}},
    )
    group = review_groups([row], {(row["case_id"], row["method"]): payload()})[0]
    assert group["claim"]["accepted_answer"] is None
    assert group["cited_source_ids"] == ["UNKNOWN"]
    assert group["unresolved_cited_source_ids"] == ["UNKNOWN"]
    source = worksheet_rows([group])[1][-1]
    assert source["original_available_in_supplied_packet"] is False
    assert source["unchanged_original_text"] == ""
    assert source["source_support"] == ""


def test_portable_source_audit_copies_only_technical_proof_not_patient_opinions(tmp_path):
    original, output = tmp_path / "original", tmp_path / "output"
    original.mkdir()
    output.mkdir()
    audit = {
        "source_id": "S",
        "corpus_file_sha256": "corpus",
        "document_sha256": "pdf",
        "pdf_page": 68,
        "printed_page": 57,
        "section": "1.2.1",
        "bbox": [1, 2, 3, 4],
        "licence_context": "shared",
        "original_source_text": "Exact original.",
        "pdf_region_text": "Exact original.\n",
        "normalized_exact_region_match": True,
        "adjacent_section": "Prior patient applicability opinion must not be copied",
    }
    (original / "manifest.json").write_text(json.dumps(audit), encoding="utf-8")
    (original / "source_region.png").write_bytes(b"image")
    copy_technical_source_audit(original, audit, output)
    copied = json.loads((output / "source_audit/manifest.json").read_bytes())
    assert copied["original_source_text"] == audit["original_source_text"]
    assert copied["clinical_and_support_review_status"] == "pending_independent_review"
    assert "adjacent_section" not in copied
    assert "Prior patient applicability opinion" not in json.dumps(copied)
    assert (output / "source_audit/source_region.png").read_bytes() == b"image"


def test_readonly_html_preserves_claims_originals_and_blank_human_review(tmp_path):
    row = observation()
    groups = review_groups([row], {(row["case_id"], row["method"]): payload()})
    _render(tmp_path, groups)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "Independent clinical and support review is pending" in html
    assert "No item has been reviewed" in html
    assert "evidence_guide.pdf#page=68" in html
    assert "source_audit/manifest.json" in html
    assert "&lt;script&gt;" in html
    assert "&lt;source&gt;" in html
    assert "read-only review viewer" in html
    assert 'class="blank"' in html
