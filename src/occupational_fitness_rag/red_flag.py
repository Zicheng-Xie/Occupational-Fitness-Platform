"""Deterministic Red Flag boundary executed before guideline retrieval.

This module owns assessment classification. Retrieval receives only the
immutable ``RAGInput`` projection and may attach evidence, but cannot change
the decision.
"""

from __future__ import annotations

from occupational_fitness_rag.rules.engine import RuleBook
from occupational_fitness_rag.schemas.red_flag_result import (
    AssessmentContext,
    MissingInformation,
    ProcessingWarning,
    ResultSource,
    RulesetIdentity,
    TriggeredRule,
    WorkflowRuleResult,
)
from occupational_fitness_rag.schemas.workflow import (
    ClinicalCase,
    Fact,
    Outcome,
    RuleEngineResult,
    RuleEvaluation,
    WorkflowRoute,
)

RED_FLAG_OUTCOMES = frozenset({Outcome.TEMPORARY, Outcome.DOES_NOT_MEET})
OUTCOME_LABELS = {
    Outcome.MEETS: "Meets unconditional standard",
    Outcome.CONDITIONAL: "May meet conditional standard",
    Outcome.TEMPORARY: "Temporarily unfit",
    Outcome.DOES_NOT_MEET: "Does not meet standard",
    Outcome.INSUFFICIENT: "Insufficient information / Human review required",
}


class RedFlagEvaluator:
    """Run the approved rule boundary and expose explicit Red Flag findings."""

    def __init__(self, rulebook: RuleBook):
        self.rulebook = rulebook

    def evaluate(self, case: ClinicalCase) -> WorkflowRuleResult:
        internal = self.rulebook.evaluate(case)
        self._validate(internal)
        triggered = [
            self._triggered(rule) for rule in internal.rules_evaluated if rule.result == "triggered"
        ]
        red_flags = [rule for rule in triggered if rule.assessment_outcome in RED_FLAG_OUTCOMES]
        missing = []
        seen = set()
        for rule in internal.rules_evaluated:
            for field in rule.missing_fields:
                key = (rule.rule_id, field)
                if key in seen:
                    continue
                seen.add(key)
                fact = case.facts.get(field, Fact())
                missing.append(
                    MissingInformation(
                        field=field,
                        status=fact.status,
                        category=rule.category,
                        reason="Required information is unknown, conflicting or requires confirmation.",
                        required_by_rule_id=rule.rule_id,
                        source_ids=rule.source_ids,
                        source_evidence=[span.quote for span in fact.evidence],
                        rag_query_key=rule.rag_query_key,
                    )
                )
        warnings = [self._warning(value) for value in internal.processing_warnings]
        return WorkflowRuleResult(
            result_id=internal.result_id,
            case_id=case.case_id,
            case_sha256=internal.case_sha256,
            source=ResultSource(source_file=case.source_document),
            assessment_context=AssessmentContext(
                job_title=self._job_title(case), modules_requested=case.modules_requested
            ),
            ruleset=RulesetIdentity(
                ruleset_id=internal.ruleset_id,
                ruleset_version=internal.ruleset_version,
                ruleset_sha256=internal.ruleset_sha256,
                guideline_version=internal.guideline_version,
                status=internal.ruleset_status,
            ),
            route=internal.route,
            assessment_outcome=internal.assessment_outcome,
            outcome_label=OUTCOME_LABELS[internal.assessment_outcome],
            has_red_flag=bool(red_flags),
            red_flags=red_flags,
            triggered_rules=triggered,
            missing_information=missing,
            modules=internal.modules,
            rules_evaluated=internal.rules_evaluated,
            processing_warnings=warnings,
            requires_human_review=internal.requires_human_review,
            rag_requests=internal.rag_requests,
            internal_metadata={"rule_engine_contract": "internal"},
        )

    @staticmethod
    def _triggered(rule: RuleEvaluation) -> TriggeredRule:
        evidence = []
        seen = set()
        for fact in rule.observed_facts.values():
            for span in fact.evidence:
                key = (span.start, span.end, span.pdf_page)
                if key not in seen:
                    seen.add(key)
                    evidence.append(span.quote)
        return TriggeredRule(
            rule_id=rule.rule_id,
            source_ids=rule.source_ids,
            category=rule.category,
            subcondition=rule.subcondition,
            assessment_outcome=rule.assessment_outcome,
            reason=rule.reason,
            observed_facts=rule.observed_facts,
            source_evidence=evidence,
            rag_query_key=rule.rag_query_key,
        )

    @staticmethod
    def _warning(value: str) -> ProcessingWarning:
        code, separator, detail = value.partition(":")
        return ProcessingWarning(code=code, message=detail if separator else value)

    @staticmethod
    def _job_title(case: ClinicalCase) -> str | None:
        fact = case.facts.get("demographics.occupation")
        return str(fact.value) if fact and fact.status == "present" else None

    @staticmethod
    def red_flag_rules(result: RuleEngineResult | WorkflowRuleResult) -> list[RuleEvaluation]:
        return [
            rule
            for rule in result.rules_evaluated
            if rule.result == "triggered" and rule.assessment_outcome in RED_FLAG_OUTCOMES
        ]

    @classmethod
    def has_red_flag(cls, result: RuleEngineResult | WorkflowRuleResult) -> bool:
        return bool(cls.red_flag_rules(result))

    @classmethod
    def _validate(cls, result: RuleEngineResult) -> None:
        if cls.has_red_flag(result) and result.route == WorkflowRoute.FAST:
            raise ValueError("A Red Flag result cannot use the fast path")
        if result.assessment_outcome in RED_FLAG_OUTCOMES and not cls.has_red_flag(result):
            raise ValueError("A Red Flag outcome requires a triggered Red Flag rule")
