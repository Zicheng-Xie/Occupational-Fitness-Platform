"""Public contract between deterministic Red Flag assessment and RAG."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from .workflow import (
    Contract,
    Fact,
    ModuleAssessment,
    Outcome,
    RAGRequest,
    RuleEvaluation,
    WorkflowRoute,
)


class ResultSource(Contract):
    type: Literal["nurse_note"] = "nurse_note"
    source_file: str


class AssessmentContext(Contract):
    framework: Literal["Austroads"] = "Austroads"
    licence_context: Literal["commercial"] = "commercial"
    job_title: str | None = None
    modules_requested: list[str]


class RulesetIdentity(Contract):
    ruleset_id: str
    ruleset_version: str
    ruleset_sha256: str
    guideline_version: Literal["AP-G56-22"] = "AP-G56-22"
    status: str


class TriggeredRule(Contract):
    rule_id: str
    source_ids: list[str] = Field(min_length=1)
    category: str
    subcondition: str
    rule_result: Literal["triggered"] = "triggered"
    assessment_outcome: Outcome
    reason: str
    observed_facts: dict[str, Fact]
    source_evidence: list[str]
    rag_query_key: str


class MissingInformation(Contract):
    field: str
    status: Literal["unknown", "conflicting", "requires_confirmation"]
    category: str
    reason: str
    required_by_rule_id: str
    source_ids: list[str] = Field(min_length=1)
    source_evidence: list[str]
    rag_query_key: str


class ProcessingWarning(Contract):
    code: str
    message: str
    requires_human_review: bool = True


class RAGInput(Contract):
    """Minimal immutable envelope accepted by retrieval."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    result_id: str
    case_id: str
    red_flag_result_sha256: str
    ruleset_sha256: str
    guideline_version: Literal["AP-G56-22"] = "AP-G56-22"
    route: WorkflowRoute
    rag_requests: list[RAGRequest]


class WorkflowRuleResult(Contract):
    schema_version: Literal["1.3.0"] = "1.3.0"
    result_id: str
    case_id: str
    case_sha256: str
    source: ResultSource
    assessment_context: AssessmentContext
    ruleset: RulesetIdentity
    route: WorkflowRoute
    assessment_outcome: Outcome
    outcome_label: str
    has_red_flag: bool
    red_flags: list[TriggeredRule]
    triggered_rules: list[TriggeredRule]
    missing_information: list[MissingInformation]
    modules: list[ModuleAssessment]
    rules_evaluated: list[RuleEvaluation]
    processing_warnings: list[ProcessingWarning]
    requires_human_review: bool
    rag_requests: list[RAGRequest]
    internal_metadata: dict[str, Any] = Field(default_factory=dict)

    def rag_input(self) -> RAGInput:
        from occupational_fitness_rag.provenance import digest

        return RAGInput(
            result_id=self.result_id,
            case_id=self.case_id,
            red_flag_result_sha256=digest(self),
            ruleset_sha256=self.ruleset.ruleset_sha256,
            guideline_version=self.ruleset.guideline_version,
            route=self.route,
            rag_requests=self.rag_requests,
        )
