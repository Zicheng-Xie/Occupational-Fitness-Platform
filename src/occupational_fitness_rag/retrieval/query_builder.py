from __future__ import annotations

from occupational_fitness_rag.schemas.rule_result import RuleResult


def build_indicator_query(result, request, rule) -> str:
    """Use rule facts plus bounded, explicitly unverified module symptom passages."""
    # RAGInput 1.1 carries only the fields observed for this request's rule.
    # The older result form remains usable by offline evaluation helpers.
    evaluation = next(
        (x for x in getattr(result, "rules_evaluated", []) if x.rule_id == request.rule_id), None
    )
    facts = getattr(result, "indicator_context", {}).get(request.request_id, {})
    if evaluation is not None:
        facts = evaluation.observed_facts
    parts = [f"{request.category} {request.subcondition} commercial driving"]
    quotes = set()
    if facts:
        for name in rule["required_facts"]:
            fact = facts.get(name)
            if not fact:
                continue
            if fact.status == "present":
                parts.append(f"{name}: {fact.value} {fact.unit or ''}".strip())
            elif fact.status in {"requires_confirmation", "conflicting"}:
                parts.append(f"{name}: unconfirmed; source wording follows")
            else:
                continue
            for span in fact.evidence:
                if span.quote not in quotes:
                    parts.append(span.quote)
                    quotes.add(span.quote)
    if len(parts) == 1:
        parts.append("Required information: " + ", ".join(rule["required_facts"]))
    passages = getattr(result, "narrative_context", {}).get(request.request_id, [])
    narrative = [span.quote for span in passages if span.quote not in quotes]
    if narrative:
        # Reserve space so clinical phrasing is not displaced by long field lists.
        parts = [
            " | ".join(parts)[:3500],
            "Unverified source narrative (not confirmed facts): " + " ".join(narrative),
        ]
    if request.ambiguity_reasons:
        parts.append("Review context: " + ", ".join(request.ambiguity_reasons))
    return " | ".join(parts)[:6000]


def build_filters(result: RuleResult) -> dict[str, str]:
    return {
        "category": result.category,
        "subcondition": result.subcondition,
        "licence_context": result.licence_context,
    }


def build_semantic_query(result: RuleResult, include_missing: bool = False) -> str:
    parts = [
        result.category,
        result.subcondition,
        f"{result.licence_context} licence medical fitness standard",
    ]
    if result.flags:
        parts.append("flags: " + "; ".join(result.flags))
    if result.rules:
        rule_terms = [trace.rule_id for trace in result.rules if trace.rule_id]
        if rule_terms:
            parts.append("rules: " + "; ".join(rule_terms))
    if include_missing and result.missing:
        parts.append("required information: " + "; ".join(result.missing))
    return " | ".join(parts)
