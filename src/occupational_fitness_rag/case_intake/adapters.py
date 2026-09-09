from __future__ import annotations

from occupational_fitness_rag.schemas.structured_case import StructuredCase

from .models import CaseIntakeResult


def to_structured_case(result: CaseIntakeResult) -> StructuredCase:
    """Convert intake output to the workflow's `structured_case.json` contract."""
    return StructuredCase(
        case_id=result.case_id,
        source_document=result.source_document,
        licence_context=result.licence_context,
        facts=result.structured_facts,
        unknown_fields=result.explicit_missing,
        extraction_metadata={
            "method": result.extraction_method,
            "fixture_only": True,
        },
    )


def to_condition_map(result: CaseIntakeResult) -> dict:
    """Convert category mapping to the workflow's `condition_map.json` shape."""
    return {
        "case_id": result.case_id,
        "licence_context": result.licence_context,
        "categories": [item.model_dump(mode="json") for item in result.category_map],
        "guardrail": "Category mapping only; deterministic rules decide flags/routes/outcomes.",
    }
