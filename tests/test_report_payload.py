from occupational_fitness_rag.integration.report_payload import build_guarded_report_payload
from occupational_fitness_rag.schemas.evidence_pack import EvidencePack, RetrievalStatus
from occupational_fitness_rag.schemas.rule_result import RuleResult
from occupational_fitness_rag.schemas.structured_case import StructuredCase


def test_report_payload_preserves_guardrails():
    case = StructuredCase(case_id="x", facts={"bp": "unknown"}, unknown_fields=["bp"])
    rule = RuleResult(
        case_id="x",
        category="cardiovascular",
        subcondition="hypertension",
        missing=["bp"],
        route="missing_information",
    )
    evidence = EvidencePack(
        case_id="x", status=RetrievalStatus.SKIPPED_MISSING_INFORMATION, filters={}
    )
    payload = build_guarded_report_payload(case, rule, evidence)
    assert payload["guardrails"]["rules_flags_citations_are_fixed"] is True
    assert payload["guardrails"]["final_clinical_authorization_required"] is True
    assert payload["guardrails"]["output_status"] == "DRAFT"
