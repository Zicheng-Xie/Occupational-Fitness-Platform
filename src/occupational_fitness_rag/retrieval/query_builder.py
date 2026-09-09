from __future__ import annotations

from occupational_fitness_rag.schemas.rule_result import RuleResult


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
