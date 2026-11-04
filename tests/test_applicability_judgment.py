"""Two-stage identifier and provenance contracts, not medical accuracy tests."""

import json
from copy import deepcopy

import pytest

from occupational_fitness_rag.evaluation.applicability_judgment import (
    AGGREGATION_SYSTEM,
    build_aggregation_request,
    build_applicability_request,
    ledger_consistency_flags,
    ledger_payload,
    parse_aggregation_response,
    parse_applicability_response,
    review_locations,
)
from occupational_fitness_rag.evaluation.passage_judgment import (
    build_request as build_passage_request,
)
from occupational_fitness_rag.evaluation.passage_judgment import (
    criterion_locations,
    passage_catalogue,
)

CONFIG = {"context_length": 8192, "output_tokens": 2048}


@pytest.fixture
def payload():
    return {
        "licence_context": "commercial",
        "modules": ["vision", "blackout"],
        "nurse_note": "Synthetic note; an unverified historical claim remains context.",
        "verified_patient_facts": {
            "vision.documented_condition": {
                "value": False,
                "patient_quotes": ["The synthetic condition is explicitly absent."],
            },
            "blackout.documented_count": {"value": 0, "patient_quotes": ["Count is zero."]},
        },
        "guideline_evidence": [
            {
                "source_id": "synthetic-original-a",
                "module": "vision",
                "pdf_page": 2,
                "printed_page": 1,
                "section": "fixture.a",
                "source_text": "Synthetic original é 😀:\r\n• Permission requires every supplied prerequisite.\n"
                "A missing prerequisite does not establish permission.",
            },
            {
                "source_id": "synthetic-original-b",
                "module": "blackout",
                "pdf_page": 3,
                "printed_page": 2,
                "section": "fixture.b",
                "source_text": "Synthetic original: a referral is an assessment step, not permission or prohibition.",
            },
        ],
    }


def raw_response(value, **metadata):
    return {"done": True, "message": {"content": json.dumps(value)}, **metadata}


def ledger_proposal(payload):
    checks = []
    for anchor in passage_catalogue(payload).values():
        field = (
            "vision.documented_condition"
            if anchor["module"] == "vision"
            else "blackout.documented_count"
        )
        checks.append(
            {
                "module": anchor["module"],
                "passage_id": anchor["passage_id"],
                "fact_fields": [field],
                "statement_type": "conditional_opportunity",
                "applicability": "uncertain",
                "licence_pathway": "conditional",
                "prerequisites": [
                    {
                        "requirement": "A documented prerequisite",
                        "status": "unknown",
                        "fact_fields": [field],
                    }
                ],
                "numeric_application": "Not applicable",
                "finding": "information_missing",
                "conclusion": "The prerequisite has not been established.",
            }
        )
    return {
        "passages": {
            f"P{index}": {
                key: value for key, value in check.items() if key not in {"module", "passage_id"}
            }
            for index, check in enumerate(checks, 1)
        }
    }


def review_for(payload):
    return parse_applicability_response(raw_response(ledger_proposal(payload)), payload)


def aggregate_proposal(review, **updates):
    original = review.passage_checks[0]
    fields = ("module", "passage_id", "fact_fields", "licence_pathway", "finding", "conclusion")
    return {
        "assessment_outcome": "insufficient_information",
        "explanation": "The synthetic prerequisites remain unresolved.",
        "criterion_checks": [{field: getattr(original, field) for field in fields}],
        **updates,
    }


@pytest.mark.parametrize("change", ["missing", "unknown"])
def test_ledger_requires_exact_slot_coverage(payload, change):
    proposed = ledger_proposal(payload)
    if change == "missing":
        proposed["passages"].pop("P2")
    else:
        proposed["passages"]["P9"] = proposed["passages"].pop("P2")
    with pytest.raises(ValueError, match="exactly once"):
        parse_applicability_response(raw_response(proposed), payload)


def test_ledger_order_and_schema_are_bound_to_the_actual_bundle(payload):
    review = review_for(payload)
    request = build_applicability_request(CONFIG, "llama3:8b", payload)
    schema = request["format"]
    assert schema["properties"]["passages"]["required"] == ["P1", "P2"]
    assert schema["properties"]["passages"]["additionalProperties"] is False
    assert "passage_id" not in schema["$defs"]["ApplicabilityEntry"]["properties"]
    assert [check.passage_id for check in review.passage_checks] == list(passage_catalogue(payload))
    assert "assessment_outcome" not in schema["properties"]
    assert schema["$defs"]["Prerequisite"]["properties"]["fact_fields"]["items"]["enum"] == list(
        payload["verified_patient_facts"]
    )


@pytest.mark.parametrize("change", ["module", "field", "prerequisite_field"])
def test_module_and_all_fact_references_are_validated(payload, change):
    proposed = ledger_proposal(payload)
    check = proposed["passages"]["P1"]
    if change == "module":
        check["module"] = "blackout"
    elif change == "field":
        check["fact_fields"].append("unknown.fact")
    elif change == "prerequisite_field":
        check["prerequisites"][0]["fact_fields"] = ["unknown.fact"]
    with pytest.raises(ValueError, match="Extra inputs|unverified"):
        parse_applicability_response(raw_response(proposed), payload)


def test_slot_order_is_program_bound_and_explicit_fact_union_is_derived(payload):
    proposed = ledger_proposal(payload)
    proposed["passages"]["P1"]["prerequisites"][0]["fact_fields"] = ["blackout.documented_count"]
    proposed["passages"] = dict(reversed(list(proposed["passages"].items())))
    review = parse_applicability_response(raw_response(proposed), payload)
    assert [check.passage_id for check in review.passage_checks] == list(passage_catalogue(payload))
    assert review.passage_checks[0].fact_fields == [
        "vision.documented_condition",
        "blackout.documented_count",
    ]


@pytest.mark.parametrize("count", [10, 48])
def test_derived_union_retains_all_legal_component_references(payload, count):
    fields = [f"vision.fixture_{index}" for index in range(count)]
    payload["verified_patient_facts"].update(
        {field: {"value": False, "patient_quotes": [f"{field} is absent."]} for field in fields}
    )
    proposed = ledger_proposal(payload)
    entry = proposed["passages"]["P1"]
    entry["fact_fields"] = fields[:8]
    entry["prerequisites"] = [
        {
            "requirement": f"Documented fixture prerequisite {index}",
            "status": "unknown",
            "fact_fields": fields[index : index + 8],
        }
        for index in range(8, count, 8)
    ]
    review = parse_applicability_response(raw_response(proposed), payload)
    assert review.passage_checks[0].fact_fields == fields
    assert list(ledger_payload(review, payload)[0]["referenced_patient_values"]) == fields
    locations = review_locations(review, payload)
    assert locations[0]["check"]["fact_fields"] == fields
    assert (
        locations[0]["spans"][0]["original_quote"]
        == payload["guideline_evidence"][0]["source_text"]
    )
    aggregation = build_aggregation_request(CONFIG, "fixture-model", payload, review)
    wire = json.loads(aggregation["messages"][1]["content"])
    assert list(wire["proposed_applicability_ledger"][0]["referenced_patient_values"]) == fields
    schema = build_applicability_request(CONFIG, "fixture-model", payload)["format"]
    assert schema["$defs"]["ApplicabilityEntry"]["properties"]["fact_fields"]["maxItems"] == 8
    assert schema["$defs"]["Prerequisite"]["properties"]["fact_fields"]["maxItems"] == 8


def test_derived_union_still_rejects_an_unverified_prerequisite_reference(payload):
    proposed = ledger_proposal(payload)
    proposed["passages"]["P1"]["prerequisites"][0]["fact_fields"] = ["vision.unverified"]
    with pytest.raises(ValueError, match="unverified"):
        parse_applicability_response(raw_response(proposed), payload)


def test_direct_model_references_keep_the_eight_field_limit(payload):
    proposed = ledger_proposal(payload)
    proposed["passages"]["P1"]["fact_fields"] = ["vision.documented_condition"] * 9
    with pytest.raises(ValueError, match="at most 8"):
        parse_applicability_response(raw_response(proposed), payload)


def test_duplicate_slot_json_is_rejected_before_key_collapsing(payload):
    one = json.dumps(ledger_proposal(payload)["passages"]["P1"])
    raw = {"done": True, "message": {"content": '{"passages":{"P1":' + one + ',"P1":' + one + "}}"}}
    with pytest.raises(ValueError, match="Duplicate JSON"):
        parse_applicability_response(raw, payload)


def test_frozen_false_zero_and_original_passages_are_unchanged_across_stages(payload):
    before = deepcopy(payload)
    review = review_for(payload)
    first = build_applicability_request(CONFIG, "llama3:8b", payload)
    second = build_aggregation_request(CONFIG, "llama3:8b", payload, review)
    first_wire = json.loads(first["messages"][1]["content"])
    second_wire = json.loads(second["messages"][1]["content"])
    for key in ("nurse_note", "modules", "verified_patient_facts"):
        assert first_wire[key] == second_wire[key]
    assert [
        {key: value for key, value in source.items() if key != "applicability_slot"}
        for source in first_wire["guideline_evidence"]
    ] == second_wire["guideline_evidence"]
    ledger = second_wire["proposed_applicability_ledger"]
    assert ledger[0]["referenced_patient_values"]["vision.documented_condition"]["value"] is False
    assert ledger[1]["referenced_patient_values"]["blackout.documented_count"]["value"] == 0
    ledger[0]["referenced_patient_values"]["vision.documented_condition"]["patient_quotes"].append(
        "changed"
    )
    assert payload == before
    standalone = ledger_payload(review, payload)
    standalone[0]["referenced_patient_values"]["vision.documented_condition"]["value"] = True
    assert payload == before
    assert review.passage_checks[0].prerequisites[0].status == "unknown"


def test_unknown_prerequisites_and_flags_never_change_the_model_outcome(payload):
    proposed = ledger_proposal(payload)
    proposed["passages"]["P1"]["finding"] = "conditional_permission"
    review = parse_applicability_response(raw_response(proposed), payload)
    before = review.model_dump(mode="json")
    flags = ledger_consistency_flags(review)
    assert any("unestablished_prerequisite" in flag for flag in flags)
    assert any("without_reported_applicability" in flag for flag in flags)
    answer = parse_aggregation_response(
        raw_response(
            aggregate_proposal(review, assessment_outcome="may_meet_conditional_standard")
        ),
        payload,
        review,
    )
    # This deliberately inconsistent proposal remains inspectable, not auto-corrected.
    assert answer.assessment_outcome == "may_meet_conditional_standard"
    assert review.model_dump(mode="json") == before
    assert review.passage_checks[0].prerequisites[0].status == "unknown"


def test_all_ledger_locations_preserve_original_ids_pages_and_unicode_spans(payload):
    review = review_for(payload)
    locations = review_locations(review, payload)
    assert len(locations) == len(payload["guideline_evidence"])
    for location, source in zip(locations, payload["guideline_evidence"], strict=True):
        assert location["source_id"] == source["source_id"]
        assert location["pdf_page"] == source["pdf_page"]
        assert location["section"] == source["section"]
        assert location["spans"][0]["original_quote"] == source["source_text"]
        span = location["spans"][0]
        assert source["source_text"][span["char_start"] : span["char_end"]] == source["source_text"]
        assert location["support_review"] == "pending_independent_review"
        assert location["check_origin"] == "unverified_stage_one_model_proposal"
    first = locations[0]["spans"][0]
    assert first["char_end"] != len(first["original_quote"].encode("utf-16-le")) // 2


def test_source_resolution_rejects_a_review_mutated_to_an_unknown_fact(payload):
    review = review_for(payload)
    review.passage_checks[0].fact_fields.append("vision.unknown")
    with pytest.raises(ValueError, match="unverified"):
        review_locations(review, payload)


@pytest.mark.parametrize("change", ["passage", "fact"])
def test_stage_two_rejects_unexpected_passage_or_fact_identifiers(payload, change):
    review = review_for(payload)
    proposed = aggregate_proposal(review)
    if change == "passage":
        proposed["criterion_checks"][0]["passage_id"] = "PASS-not-in-ledger"
    else:
        proposed["criterion_checks"][0]["fact_fields"] = ["unknown.fact"]
    with pytest.raises(ValueError, match="absent|not in this evidence bundle|unverified"):
        parse_aggregation_response(raw_response(proposed), payload, review)


def test_stage_two_can_correct_a_fallible_ledger_without_rewriting_it(payload):
    proposed_ledger = ledger_proposal(payload)
    proposed_ledger["passages"]["P1"]["finding"] = "conditional_permission"
    review = parse_applicability_response(raw_response(proposed_ledger), payload)
    before = review.model_dump(mode="json")
    final_proposal = aggregate_proposal(review)
    final_proposal["criterion_checks"][0].update(
        licence_pathway="general_information",
        finding="not_established",
        conclusion="The original prerequisite remains unknown, so the preceding permission claim is unsupported.",
    )
    answer = parse_aggregation_response(raw_response(final_proposal), payload, review)
    final_check = answer.criterion_checks[0]
    assert final_check.licence_pathway == "general_information"
    assert final_check.finding == "not_established"
    assert review.model_dump(mode="json") == before
    assert review.passage_checks[0].finding == "conditional_permission"
    assert review.passage_checks[0].licence_pathway == "conditional"
    assert final_check.source_id == payload["guideline_evidence"][0]["source_id"]
    assert final_check.guideline_quote == payload["guideline_evidence"][0]["source_text"]
    assert (
        criterion_locations(answer, payload)[0]["spans"][0]["original_quote"]
        == final_check.guideline_quote
    )


def test_omitted_prerequisites_are_flagged_without_changing_the_ledger(payload):
    proposed = ledger_proposal(payload)
    proposed["passages"]["P1"].update(finding="conditional_permission", prerequisites=[])
    review = parse_applicability_response(raw_response(proposed), payload)
    before = review.model_dump(mode="json")
    assert any(
        "without_reported_prerequisites" in flag for flag in ledger_consistency_flags(review)
    )
    assert review.model_dump(mode="json") == before


def test_multiple_final_checks_can_address_different_clauses_of_one_original_unit(payload):
    review = review_for(payload)
    proposed = aggregate_proposal(review)
    second_check = deepcopy(proposed["criterion_checks"][0])
    second_check.update(
        licence_pathway="general_information",
        finding="not_established",
        conclusion="The separate background clause establishes no permission.",
    )
    proposed["criterion_checks"].append(second_check)
    answer = parse_aggregation_response(raw_response(proposed), payload, review)
    assert len(answer.criterion_checks) == 2
    assert len({check.passage_id for check in answer.criterion_checks}) == 1
    assert answer.source_ids == [payload["guideline_evidence"][0]["source_id"]]
    assert answer.criterion_checks[0].finding != answer.criterion_checks[1].finding


@pytest.mark.parametrize("metadata", [{"done": False}, {"done_reason": "length"}])
def test_both_stages_reject_truncated_or_incomplete_responses(payload, metadata):
    with pytest.raises(ValueError, match="Incomplete"):
        parse_applicability_response(raw_response(ledger_proposal(payload), **metadata), payload)
    review = review_for(payload)
    with pytest.raises(ValueError, match="Incomplete"):
        parse_aggregation_response(
            raw_response(aggregate_proposal(review), **metadata), payload, review
        )


@pytest.mark.parametrize("stage", ["applicability", "aggregation"])
def test_reference_labels_and_rule_outcomes_are_rejected_or_excluded_from_requests(payload, stage):
    review = review_for(payload)
    payload.update(
        reference_outcome="ENGINEERING_LABEL_SENTINEL",
        rule_outcome="RULE_OUTCOME_SENTINEL",
        expected_source_ids=["REFERENCE_SOURCE_SENTINEL"],
    )
    try:
        request = (
            build_applicability_request(CONFIG, "llama3:8b", payload)
            if stage == "applicability"
            else build_aggregation_request(CONFIG, "llama3:8b", payload, review)
        )
    except ValueError:
        return
    wire = request["messages"][1]["content"]
    assert "ENGINEERING_LABEL_SENTINEL" not in wire
    assert "RULE_OUTCOME_SENTINEL" not in wire
    assert "REFERENCE_SOURCE_SENTINEL" not in wire


def test_stage_two_prompt_and_schema_agree_about_output_contract(payload):
    review = review_for(payload)
    request = build_aggregation_request(CONFIG, "llama3:8b", payload, review)
    assert set(request["format"]["properties"]) == {
        "assessment_outcome",
        "explanation",
        "criterion_checks",
    }
    control = build_passage_request(CONFIG, "llama3:8b", payload, "passage_selection")
    assert request["format"] == control["format"]
    assert request["options"] == control["options"]
    assert "decisive_passage_ids" not in AGGREGATION_SYSTEM


def test_reference_ledger_preserves_original_facts_passages_and_all_claims(payload):
    before = deepcopy(payload)
    review = review_for(payload)
    original_review = review.model_dump(mode="json")
    full = build_aggregation_request(CONFIG, "fixture-model", payload, review)
    compact = build_aggregation_request(
        {**CONFIG, "aggregation_ledger_mode": "field_references"},
        "fixture-model", payload, review,
    )
    full_wire = json.loads(full["messages"][1]["content"])
    wire = json.loads(compact["messages"][1]["content"])
    for key in ("verified_patient_facts", "guideline_evidence", "nurse_note", "modules"):
        assert wire[key] == full_wire[key]
    assert wire["verified_patient_facts"]["vision.documented_condition"]["value"] is False
    assert wire["verified_patient_facts"]["blackout.documented_count"]["value"] == 0
    for short, original in zip(
        wire["proposed_applicability_ledger"],
        full_wire["proposed_applicability_ledger"], strict=True,
    ):
        assert short == {
            key: value for key, value in original.items()
            if key != "referenced_patient_values"
        }
        assert all(field in wire["verified_patient_facts"] for field in short["fact_fields"])
    assert wire["ledger_sha256"] == full_wire["ledger_sha256"]
    assert compact["format"] == full["format"]
    assert compact["options"] == full["options"]
    assert payload == before
    assert review.model_dump(mode="json") == original_review


def test_reference_ledger_removes_repeated_long_quotes_without_truncation(payload):
    payload["verified_patient_facts"]["vision.documented_condition"]["patient_quotes"] = [
        "Synthetic long source quotation. " * 150
    ]
    review = review_for(payload)
    full = build_aggregation_request(CONFIG, "fixture-model", payload, review)
    compact = build_aggregation_request(
        {**CONFIG, "aggregation_ledger_mode": "field_references"},
        "fixture-model", payload, review,
    )
    assert len(json.dumps(compact).encode()) < len(json.dumps(full).encode()) - 4000
    wire = json.loads(compact["messages"][1]["content"])
    assert wire["verified_patient_facts"] == payload["verified_patient_facts"]
    assert ledger_payload(review, payload)[0]["referenced_patient_values"]


def test_unknown_ledger_mode_fails_before_inference(payload):
    with pytest.raises(ValueError, match="materialization mode"):
        build_aggregation_request(
            {**CONFIG, "aggregation_ledger_mode": "unexpected"},
            "fixture-model", payload, review_for(payload),
        )


def test_source_bound_checks_bind_identity_without_changing_the_model_outcome(payload):
    review = review_for(payload)
    config = {**CONFIG, "aggregation_ledger_mode": "field_references", "judgment_guidance": "source_bound_v1"}
    request = build_aggregation_request(config, "fixture-model", payload, review)
    schema = request["format"]["$defs"]["PassageCheck"]["properties"]
    assert schema["passage_slot"]["enum"] == ["P1", "P2"]
    assert "module" not in schema and "passage_id" not in schema
    wire = json.loads(request["messages"][1]["content"])
    assert wire["verified_patient_facts"] == payload["verified_patient_facts"]
    assert wire["source_numeric_relations"] == []
    proposed = aggregate_proposal(review, assessment_outcome="may_meet_conditional_standard")
    check = proposed["criterion_checks"][0]
    check.pop("module")
    check.pop("passage_id")
    check["passage_slot"] = "P1"
    raw = raw_response(proposed)
    before = deepcopy(raw)
    answer = parse_aggregation_response(raw, payload, review, config=config)
    assert answer.assessment_outcome == "may_meet_conditional_standard"
    assert answer.criterion_checks[0].module == "vision"
    assert answer.criterion_checks[0].source_id == payload["guideline_evidence"][0]["source_id"]
    assert answer.criterion_checks[0].guideline_quote == payload["guideline_evidence"][0]["source_text"]
    assert raw == before
    with pytest.raises(ValueError):
        parse_aggregation_response(raw, payload, review)


@pytest.mark.parametrize("change", ["unknown_slot", "module_override", "unverified_fact"])
def test_source_bound_checks_reject_unauthorized_source_and_fact_changes(payload, change):
    review = review_for(payload)
    proposed = aggregate_proposal(review)
    check = proposed["criterion_checks"][0]
    check.pop("module")
    check.pop("passage_id")
    check["passage_slot"] = "P1"
    if change == "unknown_slot":
        check["passage_slot"] = "P99"
    elif change == "module_override":
        check["module"] = "blackout"
    else:
        check["fact_fields"] = ["unknown.fact"]
    with pytest.raises(ValueError, match="slot|program-bound|unverified"):
        parse_aggregation_response(raw_response(proposed), payload, review, config={"judgment_guidance": "source_bound_v1"})
