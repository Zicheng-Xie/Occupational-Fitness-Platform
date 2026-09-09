"""Versioned, strict contracts for the complete assessment workflow."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MODULES = ("hypertension", "vision", "hearing", "blackout", "diabetes")


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class Outcome(StrEnum):
    MEETS = "meets_unconditional_standard"
    CONDITIONAL = "may_meet_conditional_standard"
    TEMPORARY = "temporarily_unfit"
    DOES_NOT_MEET = "does_not_meet_standard"
    INSUFFICIENT = "insufficient_information"


class WorkflowRoute(StrEnum):
    FAST = "fast_path"
    REVIEW = "rag_review"
    MISSING = "missing_information"
    HUMAN = "human_review"


class TextSpan(Contract):
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: str = Field(min_length=1)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    pdf_page: int | None = Field(default=None, ge=1)


class Fact(Contract):
    value: Any = None
    status: Literal["present", "unknown", "conflicting", "requires_confirmation"] = "unknown"
    unit: str | None = None
    evidence: list[TextSpan] = Field(default_factory=list)
    method: str = "not_recorded"
    derived_from: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_present(self):
        if self.status == "present" and (self.value is None or not self.evidence):
            raise ValueError("Present facts require a value and case-source evidence")
        if self.status != "present" and self.value is not None:
            raise ValueError("Unconfirmed facts must not carry an authoritative value")
        return self


class ClinicalCase(Contract):
    schema_version: Literal["1.2.0"] = "1.2.0"
    case_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")
    licence_context: Literal["commercial"] = "commercial"
    modules_requested: list[
        Literal["hypertension", "vision", "hearing", "blackout", "diabetes"]
    ] = Field(default_factory=lambda: list(MODULES), min_length=1)
    source_document: str
    source_kind: Literal["text", "pdf", "structured"] = "text"
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    text_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_text: str
    facts: dict[str, Fact] = Field(default_factory=dict)
    extraction_method: str = "deterministic"
    extraction_metadata: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def verify_source_spans(self):
        import hashlib

        if hashlib.sha256(self.source_text.encode("utf-8")).hexdigest() != self.text_sha256:
            raise ValueError("Case text hash mismatch")
        if len(self.modules_requested) != len(set(self.modules_requested)):
            raise ValueError("Duplicate requested module")
        for fact in self.facts.values():
            for span in fact.evidence:
                if self.source_text[span.start : span.end] != span.quote:
                    raise ValueError("Case citation does not match source text")
                if span.line_start != self.source_text.count("\n", 0, span.start) + 1:
                    raise ValueError("Case citation line number mismatch")
                if span.line_end != self.source_text.count("\n", 0, span.end - 1) + 1:
                    raise ValueError("Case citation end line mismatch")
        return self


class RuleEvaluation(Contract):
    rule_id: str
    module: str
    category: str
    subcondition: str
    result: Literal["triggered", "not_triggered", "unknown", "not_applicable"]
    assessment_outcome: Outcome | None = None
    reason: str
    source_ids: list[str]
    rag_query_key: str
    observed_facts: dict[str, Fact] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    condition_trace: dict[str, Any] = Field(default_factory=dict)


class RAGRequest(Contract):
    request_id: str
    request_type: Literal["triggered_rule_evidence", "missing_information_guidance"]
    rule_id: str
    source_ids: list[str] = Field(min_length=1)
    category: str
    subcondition: str
    licence_context: Literal["commercial"] = "commercial"
    rag_query_key: str


class ModuleAssessment(Contract):
    module: str
    assessment_outcome: Outcome
    route: WorkflowRoute
    triggered_rule_ids: list[str]
    missing_fields: list[str]
    warnings: list[str] = Field(default_factory=list)


class WorkflowRuleResult(Contract):
    schema_version: Literal["1.2.0"] = "1.2.0"
    result_id: str
    case_id: str
    case_sha256: str
    ruleset_id: str
    ruleset_version: str
    ruleset_sha256: str
    guideline_version: Literal["AP-G56-22"] = "AP-G56-22"
    ruleset_status: str = "pending_clinical_review"
    route: WorkflowRoute
    assessment_outcome: Outcome
    modules: list[ModuleAssessment]
    rules_evaluated: list[RuleEvaluation]
    rag_requests: list[RAGRequest]
    processing_warnings: list[str] = Field(default_factory=list)
    requires_human_review: Literal[True] = True


class Citation(Contract):
    source_id: str
    chunk_id: str
    document_id: Literal["AP-G56-22"] = "AP-G56-22"
    guideline_version: Literal["AP-G56-22"] = "AP-G56-22"
    document_sha256: str
    source_path: str
    section: str
    printed_page: int
    pdf_page: int = Field(ge=1)
    bbox: tuple[float, float, float, float]
    table_row: str | None = None
    licence_context: Literal["commercial"] = "commercial"
    applicability: Literal["commercial_table", "shared_guidance"]
    evidence_text: str
    text_sha256: str
    retrieval_score: float
    score_type: str
    verified_against_source: Literal[True] = True
    clinical_review_status: Literal["pending"] = "pending"
    condition: str
    standard: Literal["commercial"] = "commercial"
    criterion_type: Literal["unconditional", "conditional", "mixed", "general"]
    source_text: str
    bounding_box: tuple[float, float, float, float]
    cross_references: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_source_aliases(self):
        if self.source_text != self.evidence_text or self.bounding_box != self.bbox:
            raise ValueError("Source contract text/region aliases disagree")
        return self


class RequestEvidence(Contract):
    request_id: str
    rule_id: str
    status: Literal["complete", "partial", "no_evidence"]
    requested_source_ids: list[str]
    citations: list[Citation]
    unresolved_source_ids: list[str]
    metadata_filters: dict[str, str] = Field(default_factory=dict)
    semantic_query: str | None = None
    ranked_candidates: list[dict[str, Any]] = Field(default_factory=list)


class WorkflowEvidencePack(Contract):
    schema_version: Literal["1.2.0"] = "1.2.0"
    evidence_pack_id: str
    result_id: str
    case_id: str
    rule_result_sha256: str
    index_sha256: str
    retrieval: dict[str, Any]
    evidence_items: list[RequestEvidence]
    unresolved_requests: list[str]
    integrity: dict[str, bool]


class ReviewNote(Contract):
    schema_version: Literal["1.2.0"] = "1.2.0"
    case_id: str
    status: Literal["DRAFT"] = "DRAFT"
    assessment_outcome: Outcome
    modules: list[ModuleAssessment]
    rule_result_sha256: str
    evidence_pack_sha256: str
    summary: str
    review_checklist: list[str]
    llm_commentary: str | None = None
    clinician_name: None = None
    signed_at: None = None
    final_clinical_authorization_required: Literal[True] = True
