from __future__ import annotations

from typing import Any

from occupational_fitness_rag.schemas.evidence_pack import EvidencePack
from occupational_fitness_rag.schemas.rule_result import RuleResult
from occupational_fitness_rag.schemas.structured_case import StructuredCase


def build_guarded_report_payload(
    structured_case: StructuredCase,
    rule_result: RuleResult,
    evidence_pack: EvidencePack,
) -> dict[str, Any]:
    """Prepare fixed upstream inputs for the separate guarded report builder.

    This function does not call an LLM and does not alter rules, flags or citations.
    """
    if (
        structured_case.case_id != rule_result.case_id
        or rule_result.case_id != evidence_pack.case_id
    ):
        raise ValueError("case_id mismatch across structured_case, rule_result and evidence_pack")
    return {
        "structured_case": structured_case.model_dump(mode="json"),
        "rule_result": rule_result.model_dump(mode="json"),
        "evidence_pack": evidence_pack.model_dump(mode="json"),
        "guardrails": {
            "rules_flags_citations_are_fixed": True,
            "final_clinical_authorization_required": True,
            "output_status": "DRAFT",
        },
    }
