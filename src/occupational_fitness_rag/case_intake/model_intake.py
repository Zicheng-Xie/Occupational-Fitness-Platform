"""Local-model intake with deterministic grounding and explicit fallback provenance."""

from __future__ import annotations

import re

import pymupdf

from occupational_fitness_rag.case_intake.traceable import extract_traceable_text, valid_value
from occupational_fitness_rag.llm import OllamaClient
from occupational_fitness_rag.schemas.workflow import ClinicalCase, Fact, TextSpan

FIELD_EVIDENCE_TERMS = {
    "cardiovascular": ("blood pressure", "bp", "hypertension", "cardiac", "heart"),
    "blackout": ("blackout", "syncope", "loss of consciousness", "fainted", "fainting"),
    "vision": ("vision", "visual", "eye", "diplopia", "monocular"),
    "hearing": ("hearing", "audiometry", "audiogram", "audiologist", "ear"),
    "diabetes": ("diabetes", "diabetic", "glucose", "insulin", "hypoglycaemia"),
}


def quote_mentions_field(field, quote):
    lowered = quote.casefold()
    root = field.split(".", 1)[0]
    if any(term in lowered for term in FIELD_EVIDENCE_TERMS.get(root, ())):
        return True
    meaningful = {
        token
        for token in re.split(r"[._]", field)
        if len(token) > 3
        and token
        not in {
            "present",
            "occurred",
            "available",
            "relevant",
            "observed",
            "confirmed",
            "assessment",
            "information",
        }
    }
    return any(token in lowered for token in meaningful)


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


def generic_quote_supports(field, value, quote, specs):
    """Apply conservative type-specific evidence checks to model-only phrasing."""
    lowered = quote.casefold()
    if re.search(r"\b(?:no|not)\s+(?:\w+\s+){0,3}(?:information|data|details|history)\b", lowered):
        return False
    if re.search(r"\b(?:family history|mother|father|sibling|if|hypothetical)\b", lowered):
        return False
    if re.search(r"\b(?:possible|possibly|suspected|query|uncertain|may have|might have)\b", lowered):
        return False
    if not quote_mentions_field(field, quote):
        return False
    kind = specs[field]["type"]
    if kind == "boolean":
        negated = bool(re.search(r"\b(?:no|not|nil|denies|without|negative for|never)\b", lowered))
        return negated if value is False else not negated
    if kind == "number":
        if "persistent" in field and not re.search(
            r"\b(?:persistent|persistently|sustained|repeated|average)\b", lowered
        ):
            return False
        numbers = [float(item) for item in re.findall(r"(?<![\w.])-?\d+(?:\.\d+)?", quote)]
        return any(float(value) == item for item in numbers)
    if kind == "snellen":
        return str(value).replace(" ", "") in quote.replace(" ", "")
    if kind == "list":
        numbers = [float(item) for item in re.findall(r"(?<![\w.])-?\d+(?:\.\d+)?", quote)]
        return all(any(float(expected) == actual for actual in numbers) for expected in value)
    tokens = [part for part in str(value).casefold().split("_") if len(part) > 2]
    return bool(tokens) and all(token in lowered for token in tokens)


def apply_model_proposals(case, response, specs, page_ranges=()):
    facts = dict(case.facts)
    accepted, withheld = [], list(response.get("rejected", []))
    warnings = list(case.warnings)
    for proposal in response.get("proposals", []):
        field, value, quote = proposal["field"], proposal["value"], proposal["quote"]
        reason = None
        if field not in specs or not valid_value(field, value, specs):
            reason = "invalid_field_type_or_range"
        elif proposal.get("subject", "patient") != "patient":
            reason = "subject_is_not_patient"
        elif proposal.get("certainty", "explicit") != "explicit":
            reason = "statement_is_not_explicit"
        elif not quote or quote not in case.source_text:
            reason = "quote_not_in_input"
        elif not (
            quote_supports(field, value, quote, specs)
            or generic_quote_supports(field, value, quote, specs)
        ):
            reason = "value_not_supported_by_quote"
        elif re.search(
            r"\b(?:no|denies|without|negative for|family|if|hypothetical)\b[^.;:\n]{0,80}$",
            case.source_text[
                max(0, case.source_text.index(quote) - 100) : case.source_text.index(quote)
            ],
            flags=re.I,
        ):
            reason = "quote_omits_possible_negation_or_subject_context"
        if reason:
            withheld.append({**proposal, "reason": reason})
            continue
        start = proposal.get("source_start")
        if (
            type(start) is not int
            or start < 0
            or case.source_text[start : start + len(quote)] != quote
        ):
            start = case.source_text.index(quote)
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
