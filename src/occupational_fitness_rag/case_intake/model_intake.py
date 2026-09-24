"""Local-model intake with deterministic grounding and explicit fallback provenance."""

from __future__ import annotations

import re

import pymupdf

from occupational_fitness_rag.case_intake.traceable import extract_traceable_text, valid_value
from occupational_fitness_rag.llm import OllamaClient
from occupational_fitness_rag.schemas.workflow import ClinicalCase, Fact, TextSpan


def same_value(left, right):
    if type(left) is bool or type(right) is bool:
        return type(left) is type(right) and left == right
    return left == right


def quote_supports(field, value, quote, specs):
    """Check meaning in a quote, not merely whether its characters occur in a note."""
    parsed = extract_traceable_text(quote, "GROUNDING", "quote.txt", specs)
    candidate = parsed.facts.get(field, Fact())
    if candidate.status != "unknown":
        return candidate.status == "present" and same_value(candidate.value, value)
    # Additional bounded language patterns let the model locate phrasing the
    # baseline parser does not select, without accepting arbitrary negation.
    patterns = {
        "diabetes.present": (
            r"(?:the patient |patient )?(?:denies|has no)(?: a)?(?: history of)? diabetes(?: mellitus)?[.!]?",
            False,
        ),
        "blackout.occurred": (
            r"(?:the patient |patient )?(?:denies|has no)(?: a)?(?: history of)? (?:blackouts?|loss of consciousness)[.!]?",
            False,
        ),
        "cardiovascular.blood_pressure.observed_systolic": (
            r"(?:blood pressure|bp) (?:was |is |measured at )?(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)(?:\s*mmhg)?[.!]?",
            "sbp",
        ),
        "cardiovascular.blood_pressure.observed_diastolic": (
            r"(?:blood pressure|bp) (?:was |is |measured at )?(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)(?:\s*mmhg)?[.!]?",
            "dbp",
        ),
    }
    if field not in patterns:
        return False
    pattern, meaning = patterns[field]
    match = re.fullmatch(pattern, quote.strip(), flags=re.I)
    if not match:
        return False
    expected = float(match[1 if meaning == "sbp" else 2]) if meaning in ("sbp", "dbp") else meaning
    return same_value(value, expected)


def apply_model_proposals(case, response, specs, page_ranges=()):
    facts = dict(case.facts)
    accepted, withheld = [], list(response.get("rejected", []))
    warnings = list(case.warnings)
    for proposal in response.get("proposals", []):
        field, value, quote = proposal["field"], proposal["value"], proposal["quote"]
        start = proposal.get("source_start")
        if start is None:
            start = case.source_text.find(quote) if quote else -1
        reason = None
        if field not in specs or not valid_value(field, value, specs):
            reason = "invalid_field_type_or_range"
        elif proposal.get("subject", "patient") != "patient":
            reason = "subject_is_not_patient"
        elif proposal.get("certainty", "explicit") != "explicit":
            reason = "statement_is_not_explicit"
        elif proposal.get("temporality") == "history" and (
            "blood_pressure" in field
            or field.startswith(("vision.", "hearing."))
            or field == "diabetes.treatment_category"
        ):
            reason = "historical_measurement_or_treatment_is_not_current"
        elif not quote or quote not in case.source_text:
            reason = "quote_not_in_input"
        elif (
            type(start) is not int
            or start < 0
            or case.source_text[start : start + len(quote)] != quote
        ):
            reason = "quote_offset_does_not_match_input"
        elif field == "diabetes.treatment_category" and re.search(
            r"not available for verification|awaiting verification|cannot be verified",
            re.split(r"[.!?;](?=\s|$)|\n", case.source_text[start:], maxsplit=1)[0],
            re.I,
        ):
            reason = "current_treatment_requires_verification"
        elif not quote_supports(field, value, quote, specs):
            reason = "value_not_supported_by_quote"
        elif re.search(
            r"\b(?:no|denies|without|negative for|family|mother|father|sister|brother|if|hypothetical)\b[^.;\n]{0,80}$",
            case.source_text[max(0, start - 100) : start],
            flags=re.I,
        ):
            reason = "quote_omits_possible_negation_or_subject_context"
        if reason:
            withheld.append({**proposal, "reason": reason})
            continue
        end = start + len(quote)
        span = TextSpan(
            start=start,
            end=end,
            quote=quote,
            line_start=case.source_text.count("\n", 0, start) + 1,
            line_end=case.source_text.count("\n", 0, end - 1) + 1,
            pdf_page=next((page for a, b, page in page_ranges if a <= start < b), None),
        )
        previous = facts.get(field, Fact())
        if previous.status in {"conflicting", "requires_confirmation"} or (
            previous.status == "present" and not same_value(previous.value, value)
        ):
            facts[field] = Fact(
                status="conflicting",
                evidence=[*previous.evidence, span],
                method="model_baseline_conflict",
                unit=specs[field].get("unit"),
                derived_from=previous.derived_from,
            )
            warnings.append(f"CONFLICTING_FACT:{field}")
            withheld.append({**proposal, "reason": "conflict_with_other_input_evidence"})
            continue
        facts[field] = Fact(
            value=value,
            status="present",
            unit=specs[field].get("unit"),
            evidence=[*previous.evidence, span],
            method="llm_grounded",
            derived_from=previous.derived_from,
        )
        accepted.append(field)
    # Re-validate every source span after merging; results remain machine-replayable.
    updated = ClinicalCase.model_validate(
        {
            **case.model_dump(),
            "facts": facts,
            "warnings": sorted(set(warnings)),
            "extraction_method": "local_llm_grounded_with_deterministic_fallback",
        }
    )
    return updated, {
        **response,
        "accepted_fields": sorted({key for key in accepted if facts[key].method == "llm_grounded"}),
        "withheld": withheld,
        "grounding_policy": "exact_quote_type_range_and_field_semantics_v1",
        "status": "completed" if accepted else "completed_no_grounded_fields",
        "authoritative_facts_modified": bool(accepted),
    }


def model_intake(case, specs, config, page_ranges=()):
    if not config.enabled or not config.extraction_enabled:
        return case, {"status": "disabled", "accepted_fields": []}
    client = OllamaClient(config)
    try:
        response = client.extract(case.source_text, specs, case.modules_requested)
        return apply_model_proposals(case, response, specs, page_ranges)
    except Exception as exc:
        updated = ClinicalCase.model_validate(
            {
                **case.model_dump(),
                "extraction_method": "deterministic_fallback",
                "warnings": [*case.warnings, "LOCAL_MODEL_UNAVAILABLE:deterministic_fallback"],
            }
        )
        return updated, {
            "status": "unavailable_fallback_to_template",
            "model": config.model,
            "error_type": type(exc).__name__,
            "accepted_fields": [],
        }


def pdf_ranges(path):
    ranges, offset = [], 0
    if path.suffix.lower() == ".pdf":
        with pymupdf.open(path) as doc:
            for number, page in enumerate(doc, 1):
                text = page.get_text(sort=True)
                ranges.append((offset, offset + len(text), number))
                offset += len(text) + 1
    return ranges
