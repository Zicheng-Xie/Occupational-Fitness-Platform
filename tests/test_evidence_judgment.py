"""Clause-grounding contracts with synthetic, non-clinical fixtures and no model calls."""

import json
from copy import deepcopy

import pytest
from pydantic import ValidationError

from occupational_fitness_rag.evaluation.evidence_judgment import (
    CriterionCheck,
    EvidenceJudgment,
    build_request,
    criterion_locations,
    parse_response,
    quote_locations,
    validate_protocol_answer,
)
from occupational_fitness_rag.evaluation.judgment_comparison import (
    judgment_request,
    make_payload,
)
from occupational_fitness_rag.evaluation.model_judgment import ExperimentalJudgment

CONFIG = {"context_length": 8192, "output_tokens": 1536}
QUOTE = "An active safety condition requires a temporary hold until review is complete."


@pytest.fixture
def payload():
    return {
        "licence_context": "commercial",
        "modules": ["vision"],
        "nurse_note": "Synthetic operator record: safety condition recorded; review pending.",
        "verified_patient_facts": {
            "vision.safety_condition": {
                "value": True,
                "patient_quotes": ["safety condition recorded"],
            }
        },
        "guideline_evidence": [
            {
                "source_id": "synthetic-original-1",
                "section": "fixture-1",
                "pdf_page": 1,
                "printed_page": 1,
                "source_text": QUOTE + " Pending evidence alone does not establish permission.",
            }
        ],
    }


def check(**updates):
    return CriterionCheck(
        **{
            "module": "vision",
            "source_id": "synthetic-original-1",
            "guideline_quote": QUOTE,
            "fact_fields": ["vision.safety_condition"],
            "licence_pathway": "temporary_no_driving",
            "finding": "established_restriction",
            "conclusion": "The recorded safety condition satisfies the quoted hold criterion.",
            **updates,
        }
    )


def answer(criterion=None, **updates):
    return EvidenceJudgment(
        **{
            "assessment_outcome": "temporarily_unfit",
            "explanation": "The supplied original clause and verified condition support a hold.",
            "source_ids": ["synthetic-original-1"],
            "fact_fields": ["vision.safety_condition"],
            "criterion_checks": [criterion if criterion is not None else check()],
            **updates,
        }
    )


def wire_answer(criterion=None, **updates):
    return answer(criterion, **updates).model_dump(exclude={"source_ids", "fact_fields"})


@pytest.mark.parametrize("model", ["llama3:8b", "qwen3.5:4b-q4_K_M"])
def test_baseline_request_is_exactly_the_frozen_comparison_request(payload, model):
    before = deepcopy(payload)
    assert build_request(CONFIG, model, payload, "baseline") == judgment_request(
        CONFIG, model, payload
    )
    assert payload == before


def test_clause_schema_bounds_actual_identifiers_without_forcing_outcomes(payload):
    before = deepcopy(payload)
    request = build_request(CONFIG, "llama3:8b", payload, "evidence_contract")
    schema = request["format"]
    criteria = schema["$defs"]["CriterionCheck"]["properties"]
    assert criteria["module"]["enum"] == ["vision"]
    assert criteria["source_id"]["enum"] == ["synthetic-original-1"]
    assert criteria["fact_fields"]["items"]["enum"] == ["vision.safety_condition"]
    assert criteria["fact_fields"]["maxItems"] == 1
    assert set(criteria["licence_pathway"]["enum"]) == {
        "unconditional",
        "conditional",
        "both",
        "temporary_no_driving",
        "general_information",
    }
    assert set(schema["properties"]) == {
        "assessment_outcome",
        "explanation",
        "criterion_checks",
    }
    assert schema["properties"]["criterion_checks"]["maxItems"] == 5
    assert len(schema["properties"]["assessment_outcome"]["enum"]) == 5
    assert json.loads(request["messages"][1]["content"]) == payload
    assert payload == before


def test_only_present_facts_enter_request_and_reference_metadata_does_not_leak():
    case = {
        "modules_requested": ["vision"],
        "source_text": "Synthetic fixture record.",
        "reference_outcome": "gold-outcome-sentinel",
        "expected_source_ids": ["gold-source-sentinel"],
        "rule_result": {"outcome": "rule-result-sentinel"},
        "facts": {
            "vision.safety_condition": {
                "status": "present",
                "value": True,
                "evidence": [{"quote": "Synthetic fixture"}],
            },
            "vision.quarantined": {
                "status": "requires_confirmation",
                "value": True,
                "evidence": [{"quote": "unverified-value-sentinel"}],
            },
        },
    }
    units = {
        "synthetic-original-1": {
            "section": "fixture-1",
            "pdf_page": 1,
            "printed_page": 1,
            "evidence_text": QUOTE,
        }
    }
    payload, excluded = make_payload(
        case, units, ["synthetic-original-1"], {"evidence_max_bytes": 5000}
    )
    request = build_request(CONFIG, "llama3:8b", payload, "evidence_contract")
    serialized = json.dumps(request)
    for forbidden in (
        "gold-outcome-sentinel",
        "gold-source-sentinel",
        "rule-result-sentinel",
        "unverified-value-sentinel",
        "vision.quarantined",
        "reference_outcome",
        "expected_source_ids",
        "rule_result",
    ):
        assert forbidden not in serialized
    assert excluded == []


def test_exact_contiguous_quote_accepts_pdf_whitespace_only(payload):
    payload["guideline_evidence"][0]["source_text"] = QUOTE.replace("requires ", "requires\n  ")
    validate_protocol_answer(answer(), payload, "evidence_contract")
    validate_protocol_answer(
        answer(check(guideline_quote=QUOTE.replace("requires ", "requires\t"))),
        payload,
        "evidence_contract",
    )


def test_original_quote_locations_preserve_wrapped_half_open_character_spans():
    original_quote = QUOTE.replace("temporary hold", "temporary\n  hold")
    prefix = "Fixture heading.\n\n"
    original = prefix + original_quote + "\nNext paragraph."
    spans = quote_locations(QUOTE, original)
    assert spans == [
        {
            "char_start": len(prefix),
            "char_end": len(prefix) + len(original_quote),
            "original_quote": original_quote,
        }
    ]
    assert original[spans[0]["char_start"] : spans[0]["char_end"]] == original_quote


def test_duplicate_original_quotes_retain_all_locations_instead_of_picking_one():
    first = QUOTE.replace("requires ", "requires\n")
    separator = "\nRepeated fixture clause:\n"
    original = first + separator + QUOTE
    spans = quote_locations(QUOTE, original)
    assert len(spans) == 2
    assert spans[0]["char_start"] == 0
    assert spans[0]["char_end"] == len(first)
    assert spans[1]["char_start"] == len(first) + len(separator)
    assert spans[1]["char_end"] == len(original)
    for span in spans:
        assert original[span["char_start"] : span["char_end"]] == span["original_quote"]


def test_changed_quote_punctuation_has_no_original_location():
    assert quote_locations(QUOTE[:-1] + "!", QUOTE) == []


def test_criterion_locations_retain_selected_source_page_and_section_identity(payload):
    original = "Source two heading.\n" + QUOTE.replace("until review", "until\nreview")
    payload["guideline_evidence"].append(
        {
            "source_id": "synthetic-original-2",
            "section": "fixture-2",
            "pdf_page": 7,
            "printed_page": 3,
            "source_text": original,
        }
    )
    proposed = answer(check(source_id="synthetic-original-2"), source_ids=["synthetic-original-2"])
    validate_protocol_answer(proposed, payload, "evidence_contract")
    locations = criterion_locations(proposed, payload)
    assert len(locations) == 1
    location = locations[0]
    assert location["source_id"] == "synthetic-original-2"
    assert location["pdf_page"] == 7
    assert location["section"] == "fixture-2"
    assert location["check"] == proposed.criterion_checks[0].model_dump(mode="json")
    assert location["support_review"] == "pending_independent_review"
    assert location["spans"] == quote_locations(QUOTE, original)
    span = location["spans"][0]
    assert original[span["char_start"] : span["char_end"]] == span["original_quote"]


@pytest.mark.parametrize(
    "quote",
    [
        "An active safety condition does not require a temporary hold until review is complete.",
        "An active safety condition requires a temporary hold until review is complete!",
        "An active safety condition requires a temporary hold. Pending evidence alone",
        "Review pending: an active safety condition requires a temporary hold.",
    ],
)
def test_invented_altered_or_noncontiguous_quote_is_rejected(payload, quote):
    with pytest.raises(ValueError, match="quote does not match"):
        validate_protocol_answer(answer(check(guideline_quote=quote)), payload, "evidence_contract")


def test_checks_must_bind_to_supplied_and_final_source_citations(payload):
    with pytest.raises(ValueError, match="unprovided module or source"):
        validate_protocol_answer(
            answer(check(source_id="invented-source")), payload, "evidence_contract"
        )
    payload["guideline_evidence"].append(
        {**payload["guideline_evidence"][0], "source_id": "synthetic-original-2"}
    )
    with pytest.raises(ValueError, match="source is absent from the final citation"):
        validate_protocol_answer(
            answer(check(source_id="synthetic-original-2")), payload, "evidence_contract"
        )


def test_checks_must_bind_to_supplied_and_final_verified_facts(payload):
    with pytest.raises(ValueError, match="not supplied"):
        validate_protocol_answer(
            answer(
                check(fact_fields=["vision.quarantined"]),
                fact_fields=["vision.quarantined"],
            ),
            payload,
            "evidence_contract",
        )
    with pytest.raises(ValueError, match="facts are absent from the final fact"):
        validate_protocol_answer(answer(fact_fields=[]), payload, "evidence_contract")


def test_check_cannot_claim_unrequested_module_or_fact_free_restriction(payload):
    with pytest.raises(ValueError, match="unprovided module or source"):
        validate_protocol_answer(answer(check(module="hearing")), payload, "evidence_contract")
    with pytest.raises(ValueError, match="restriction requires a verified patient fact"):
        validate_protocol_answer(
            answer(check(fact_fields=[]), fact_fields=[]), payload, "evidence_contract"
        )
    with pytest.raises(ValidationError):
        check(module="unsupported-module")


def test_information_missing_can_be_recorded_without_inventing_verified_facts(payload):
    payload["verified_patient_facts"] = {}
    request = build_request(CONFIG, "llama3:8b", payload, "evidence_contract")
    props = request["format"]["$defs"]["CriterionCheck"]["properties"]
    assert props["fact_fields"]["maxItems"] == 0
    proposed = answer(
        check(
            finding="information_missing",
            fact_fields=[],
            conclusion="No verified finding establishes the criterion.",
        ),
        assessment_outcome="insufficient_information",
        fact_fields=[],
    )
    validate_protocol_answer(proposed, payload, "evidence_contract")


def test_original_evidence_and_clause_checks_are_mandatory(payload):
    with pytest.raises(ValidationError):
        answer(criterion_checks=[])
    payload["guideline_evidence"] = []
    with pytest.raises(ValueError, match="requires original guideline evidence"):
        build_request(CONFIG, "llama3:8b", payload, "evidence_contract")
    with pytest.raises(ValueError, match="requires a supplied source citation"):
        validate_protocol_answer(
            answer(source_ids=[], fact_fields=[]), payload, "evidence_contract"
        )


def test_parse_rejects_incomplete_output_even_when_json_is_parseable(payload):
    raw = {"done": True, "message": {"content": json.dumps(wire_answer())}}
    assert parse_response(raw, payload, "evidence_contract") == answer()
    for completion in ({"done": False}, {"done_reason": "length"}):
        with pytest.raises(ValueError, match="partial answers rejected"):
            parse_response({**raw, **completion}, payload, "evidence_contract")


def test_wire_references_form_canonical_union_in_supplied_order_without_prose_inference(payload):
    for suffix in ("secondary", "prose_only"):
        payload["verified_patient_facts"][f"vision.{suffix}"] = {
            "value": True,
            "patient_quotes": ["Synthetic fixture finding."],
        }
    for number in (2, 3):
        payload["guideline_evidence"].append(
            {**payload["guideline_evidence"][0], "source_id": f"synthetic-original-{number}"}
        )
    second = check(
        source_id="synthetic-original-2",
        fact_fields=["vision.secondary", "vision.secondary"],
    )
    first = check()
    model_answer = wire_answer(
        criterion_checks=[second, first, second],
        assessment_outcome="insufficient_information",
        explanation="Prose mentions synthetic-original-3 and vision.prose_only without citing them.",
    )
    raw = {"done": True, "message": {"content": json.dumps(model_answer)}}
    untouched = deepcopy(raw)
    parsed = parse_response(raw, payload, "evidence_contract")
    assert parsed.source_ids == ["synthetic-original-1", "synthetic-original-2"]
    assert parsed.fact_fields == ["vision.safety_condition", "vision.secondary"]
    assert parsed.criterion_checks[0].fact_fields == ["vision.secondary", "vision.secondary"]
    assert len(parsed.criterion_checks) == 3
    assert parsed.assessment_outcome == "insufficient_information"
    assert raw == untouched


@pytest.mark.parametrize(
    "criterion",
    [check(source_id="invented-source"), check(fact_fields=["vision.quarantined"])],
)
def test_wire_unknown_check_references_remain_failures_after_union_derivation(payload, criterion):
    raw = {"done": True, "message": {"content": json.dumps(wire_answer(criterion))}}
    with pytest.raises(ValueError):
        parse_response(raw, payload, "evidence_contract")


def test_wire_information_missing_never_infers_fact_reference_from_explanation(payload):
    missing = check(
        fact_fields=[],
        finding="information_missing",
        conclusion="Prose mentions vision.safety_condition but makes no verified factual claim.",
    )
    raw = {"done": True, "message": {"content": json.dumps(wire_answer(missing))}}
    parsed = parse_response(raw, payload, "evidence_contract")
    assert parsed.source_ids == ["synthetic-original-1"]
    assert parsed.fact_fields == []


@pytest.mark.parametrize(
    "outcome", ExperimentalJudgment.model_json_schema()["properties"]["assessment_outcome"]["enum"]
)
def test_wire_reference_derivation_never_rewrites_the_model_outcome(payload, outcome):
    raw = {
        "done": True,
        "message": {"content": json.dumps(wire_answer(assessment_outcome=outcome))},
    }
    assert parse_response(raw, payload, "evidence_contract").assessment_outcome == outcome


def test_baseline_wire_still_uses_the_original_v5_contract(payload):
    baseline = answer().model_dump(exclude={"criterion_checks"})
    raw = {"done": True, "message": {"content": json.dumps(baseline)}}
    parsed = parse_response(raw, payload, "baseline")
    assert parsed.model_dump() == baseline


def test_protocol_types_and_english_conclusions_are_validated(payload):
    baseline = ExperimentalJudgment(**answer().model_dump(exclude={"criterion_checks"}))
    validate_protocol_answer(baseline, payload, "baseline")
    with pytest.raises(ValueError, match="Wrong judgment protocol"):
        validate_protocol_answer(baseline, payload, "evidence_contract")
    with pytest.raises(ValueError, match="Unknown judgment protocol"):
        build_request(CONFIG, "llama3:8b", payload, "unknown")
    with pytest.raises(ValueError, match="conclusion must be in English"):
        validate_protocol_answer(
            answer(check(conclusion="\u9700\u8981\u590d\u6838")), payload, "evidence_contract"
        )
