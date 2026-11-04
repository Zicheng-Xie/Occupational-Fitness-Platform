"""Immutable-passage provenance and protocol controls using synthetic originals."""

import json
from copy import deepcopy

import pytest

from occupational_fitness_rag.evaluation.passage_judgment import (
    PASSAGE_SYSTEM,
    build_request,
    criterion_locations,
    output_consistency_flags,
    parse_response,
    passage_catalogue,
    serialized_request_bytes,
)

CONFIG = {"context_length": 8192, "output_tokens": 2048}


@pytest.fixture
def payload():
    return {
        "licence_context": "commercial",
        "modules": ["vision", "blackout"],
        "nurse_note": "Synthetic fictional assessment note.",
        "verified_patient_facts": {
            "vision.safety_condition": {"value": True, "patient_quotes": ["Condition recorded"]}
        },
        "guideline_evidence": [
            {
                "source_id": "fixture-source",
                "module": "vision",
                "pdf_page": 2,
                "printed_page": 1,
                "section": "fixture.1",
                "source_text": "Synthetic original: é 😀\r\n•\tDo not drive until review.\n"
                "Permission remains conditional on the complete assessment.",
            }
        ],
    }


def proposal(payload, **updates):
    return {
        "assessment_outcome": "temporarily_unfit",
        "explanation": "The documented condition requires a provisional hold under the supplied source.",
        "criterion_checks": [
            {
                "module": "vision",
                "passage_id": next(iter(passage_catalogue(payload))),
                "fact_fields": ["vision.safety_condition"],
                "licence_pathway": "temporary_no_driving",
                "finding": "established_restriction",
                "conclusion": "The recorded condition requires review before driving.",
            }
        ],
        **updates,
    }


def response(proposed, **updates):
    return {"done": True, "message": {"content": json.dumps(proposed)}, **updates}


def test_passage_ids_bind_exact_original_metadata_and_survive_reordering(payload):
    original = deepcopy(payload)
    first = passage_catalogue(payload)
    payload["guideline_evidence"].append(
        {**payload["guideline_evidence"][0], "source_id": "fixture-source-2"}
    )
    assert set(first) <= set(passage_catalogue(payload))
    assert passage_catalogue(payload) == passage_catalogue(
        {**payload, "guideline_evidence": list(reversed(payload["guideline_evidence"]))}
    )
    changed = deepcopy(original)
    changed["guideline_evidence"][0]["source_text"] += " "
    assert set(first).isdisjoint(passage_catalogue(changed))
    changed = deepcopy(original)
    changed["guideline_evidence"][0]["pdf_page"] = 3
    assert set(first).isdisjoint(passage_catalogue(changed))


def test_selected_passage_is_derived_verbatim_without_changing_predicted_outcome(payload):
    proposed = proposal(payload, assessment_outcome="insufficient_information")
    raw = response(proposed)
    before = deepcopy(raw)
    answer = parse_response(raw, payload, "passage_selection")
    assert answer.assessment_outcome == "insufficient_information"
    assert raw == before
    assert answer.source_ids == ["fixture-source"]
    assert answer.fact_fields == ["vision.safety_condition"]
    location = criterion_locations(answer, payload)[0]
    span = location["spans"][0]
    text = payload["guideline_evidence"][0]["source_text"]
    assert span["original_quote"] == text
    assert text[span["char_start"] : span["char_end"]] == text
    assert span["char_end"] == len(text)
    assert span["char_end"] != len(text.encode("utf-16-le")) // 2
    assert location["offset_unit"] == "python_unicode_code_points"
    assert location["support_review"] == "pending_independent_review"
    assert output_consistency_flags(answer, payload) == [
        "reported_restriction_not_reflected_in_outcome"
    ]


def test_both_arms_receive_identical_patient_and_evidence_content(payload):
    before = deepcopy(payload)
    quote = build_request(CONFIG, "llama3:8b", payload, "quote_contract")
    selected = build_request(CONFIG, "llama3:8b", payload, "passage_selection")
    assert quote["messages"][1] == selected["messages"][1]
    wire = json.loads(selected["messages"][1]["content"])
    source = wire["guideline_evidence"][0]
    assert source["source_text"] == payload["guideline_evidence"][0]["source_text"]
    assert source["passage_id"] in passage_catalogue(payload)
    assert payload == before
    assert "guideline_quote" not in selected["format"]["$defs"]["PassageCheck"]["properties"]
    assert "copy a SHORT" not in PASSAGE_SYSTEM
    assert "both\n  unconditional AND conditional" in PASSAGE_SYSTEM
    assert serialized_request_bytes(selected) > len(json.dumps(payload).encode())


def test_stale_or_other_bundle_passage_id_is_never_repaired(payload):
    proposed = proposal(payload)
    changed = deepcopy(payload)
    changed["guideline_evidence"][0]["source_text"] += " A changed qualification."
    with pytest.raises(ValueError, match="not in this evidence bundle"):
        parse_response(response(proposed), changed, "passage_selection")


@pytest.mark.parametrize("field,value", [("module", "blackout"), ("fact_fields", ["unknown.fact"])])
def test_module_and_fact_bindings_are_checked_after_resolution(payload, field, value):
    proposed = proposal(payload)
    proposed["criterion_checks"][0][field] = value
    with pytest.raises(ValueError, match="module differs|unverified"):
        parse_response(response(proposed), payload, "passage_selection")


@pytest.mark.parametrize("finding", ["established_restriction", "conditional_permission"])
def test_established_findings_require_explicit_verified_fact_references(payload, finding):
    proposed = proposal(payload)
    proposed["criterion_checks"][0].update(finding=finding, fact_fields=[])
    with pytest.raises(ValueError, match="verified patient fact"):
        parse_response(response(proposed), payload, "passage_selection")


def test_free_prose_cannot_silently_add_citations(payload):
    proposed = proposal(payload)
    proposed["explanation"] = "A fabricated-source-id and unknown.fact occur in this explanation."
    answer = parse_response(response(proposed), payload, "passage_selection")
    assert answer.source_ids == ["fixture-source"]
    assert answer.fact_fields == ["vision.safety_condition"]


@pytest.mark.parametrize("metadata", [{"pdf_page": None}, {"module": "hearing"}, {"section": ""}])
def test_incomplete_or_out_of_scope_original_metadata_is_rejected(payload, metadata):
    payload["guideline_evidence"][0].update(metadata)
    with pytest.raises(ValueError):
        passage_catalogue(payload)


def test_incomplete_response_and_duplicate_sources_are_rejected(payload):
    with pytest.raises(ValueError, match="incomplete"):
        parse_response(
            response(proposal(payload), done_reason="length"), payload, "passage_selection"
        )
    payload["guideline_evidence"] *= 2
    with pytest.raises(ValueError, match="duplicate"):
        passage_catalogue(payload)


def test_no_consistency_flag_does_not_assert_source_entailment(payload):
    # A structurally consistent claim can still be clinically wrong. No label is consulted.
    answer = parse_response(response(proposal(payload)), payload, "passage_selection")
    assert output_consistency_flags(answer, payload) == []
    assert criterion_locations(answer, payload)[0]["support_review"] != "approved"
