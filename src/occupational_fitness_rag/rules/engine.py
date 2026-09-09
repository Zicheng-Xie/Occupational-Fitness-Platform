from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from occupational_fitness_rag.case_intake.traceable import (
    collect_field_specs,
    snellen_ratio,
    valid_value,
)
from occupational_fitness_rag.provenance import digest
from occupational_fitness_rag.schemas.workflow import (
    ClinicalCase,
    Fact,
    ModuleAssessment,
    Outcome,
    RAGRequest,
    RuleEvaluation,
    WorkflowRoute,
    WorkflowRuleResult,
)

PRECEDENCE = [
    Outcome.DOES_NOT_MEET,
    Outcome.TEMPORARY,
    Outcome.INSUFFICIENT,
    Outcome.CONDITIONAL,
    Outcome.MEETS,
]
OPERATORS = {
    "==",
    ">",
    ">=",
    "<",
    "<=",
    "in",
    "set_equals",
    "worse_than_snellen",
    "at_least_snellen",
}


@dataclass
class PredicateResult:
    truth: bool | None
    missing: set[str]
    trace: dict[str, Any]


def evaluate_predicate(
    node: dict, facts: dict[str, Fact], evaluations: dict[str, RuleEvaluation]
) -> PredicateResult:
    """Kleene three-valued logic: false AND unknown=false; true OR unknown=true."""
    if "triggered_rule" in node:
        previous = evaluations[node["triggered_rule"]]
        truth = None if previous.result == "unknown" else previous.result == "triggered"
        return PredicateResult(
            truth,
            set(previous.missing_fields) if truth is None else set(),
            {"dependency": previous.rule_id, "truth": truth},
        )
    for kind in ("all", "any"):
        if kind in node:
            children = [evaluate_predicate(c, facts, evaluations) for c in node[kind]]
            values = [c.truth for c in children]
            if kind == "all":
                truth = False if False in values else None if None in values else True
            else:
                truth = True if True in values else None if None in values else False
            missing = set().union(*(c.missing for c in children)) if truth is None else set()
            return PredicateResult(
                truth, missing, {kind: [c.trace for c in children], "truth": truth}
            )
    name, op, expected = node["field"], node["operator"], node["value"]
    fact = facts.get(name, Fact())
    trace = {
        "field": name,
        "operator": op,
        "expected": expected,
        "observed": fact.value,
        "status": fact.status,
    }
    if fact.status != "present":
        return PredicateResult(None, {name}, {**trace, "truth": None})
    value = fact.value
    if op == "==":
        truth = type(value) is type(expected) and value == expected
        if type(value) in (int, float) and type(expected) in (int, float):
            truth = value == expected
    elif op == "in":
        truth = value in expected
    elif op == "set_equals":
        truth = set(value) == set(expected)
    elif op == "worse_than_snellen":
        truth = snellen_ratio(value) < snellen_ratio(expected)
    elif op == "at_least_snellen":
        truth = snellen_ratio(value) >= snellen_ratio(expected)
    elif op == ">":
        truth = value > expected
    elif op == ">=":
        truth = value >= expected
    elif op == "<":
        truth = value < expected
    elif op == "<=":
        truth = value <= expected
    else:
        raise ValueError(f"Unsupported operator {op}")
    return PredicateResult(truth, set(), {**trace, "truth": truth})


def _validate_predicate(node, seen):
    if not isinstance(node, dict):
        raise ValueError("Predicate must be a mapping")
    shapes = sum(key in node for key in ("all", "any", "field", "triggered_rule"))
    if shapes != 1:
        raise ValueError("Predicate needs exactly one operator shape")
    if "triggered_rule" in node:
        if set(node) != {"triggered_rule"} or node["triggered_rule"] not in seen:
            raise ValueError(
                "Rule dependency must reference an earlier rule (cycles/forward references forbidden)"
            )
    elif "field" in node:
        if (
            set(node) - {"field", "operator", "value", "unit"}
            or not {"field", "operator", "value"} <= set(node)
            or node["operator"] not in OPERATORS
        ):
            raise ValueError("Malformed or unsupported rule predicate")
    else:
        key = "all" if "all" in node else "any"
        if set(node) != {key} or not isinstance(node[key], list) or not node[key]:
            raise ValueError("Boolean groups must be nonempty")
        for child in node[key]:
            _validate_predicate(child, seen)


def _fields(node):
    if not node:
        return set()
    return ({node["field"]} if "field" in node else set()) | set().union(
        *(_fields(c) for k in ("all", "any") for c in node.get(k, []))
    )


def _outcome(values, precedence=PRECEDENCE):
    return next((value for value in precedence if value in values), Outcome.INSUFFICIENT)


class RuleBook:
    def __init__(self, path: str | Path):
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        self.metadata, self.rules = data["ruleset"], data["rules"]
        if self.metadata["scope"]["licence_context"] != "commercial":
            raise ValueError("Only the commercial assessment ruleset is supported")
        if self.metadata["status"] != "pending_clinical_review":
            raise ValueError(
                "This runtime is a decision-support application; approved clinical use is not implemented"
            )
        configured_precedence = self.metadata.get("outcome_precedence", PRECEDENCE)
        self.precedence = [Outcome(value) for value in configured_precedence]
        if set(self.precedence) != set(Outcome) or len(self.precedence) != len(Outcome):
            raise ValueError("outcome_precedence must contain every outcome exactly once")
        self.sha256 = digest(data)
        seen = set()
        for rule in self.rules:
            if rule["rule_id"] in seen:
                raise ValueError("Duplicate rule ID")
            _validate_predicate(rule["condition"], seen)
            if rule.get("gate"):
                _validate_predicate(rule["gate"], seen)
            if set(rule["required_facts"]) != _fields(rule["condition"]) | _fields(
                rule.get("gate")
            ):
                raise ValueError(f"Stale required_facts for {rule['rule_id']}")
            if not rule["source_ids"]:
                raise ValueError("Every rule requires source IDs")
            Outcome(rule["outcome"]["assessment_outcome"])
            seen.add(rule["rule_id"])
        self.field_specs = collect_field_specs(self.rules)

    def evaluate(self, case: ClinicalCase) -> WorkflowRuleResult:
        for name, fact in case.facts.items():
            if name not in self.field_specs:
                raise ValueError(f"Unknown canonical fact: {name}")
            if fact.status == "present" and not valid_value(name, fact.value, self.field_specs):
                raise ValueError(f"Fact has wrong type/range: {name}")
            if fact.unit != self.field_specs[name].get("unit"):
                raise ValueError(f"Fact unit mismatch: {name}")
        evaluations: dict[str, RuleEvaluation] = {}
        for rule in self.rules:
            if rule["module"] not in case.modules_requested:
                continue
            gate = (
                evaluate_predicate(rule["gate"], case.facts, evaluations)
                if rule.get("gate")
                else PredicateResult(True, set(), {})
            )
            if gate.truth is False:
                result, predicate = "not_applicable", gate
            elif gate.truth is None:
                condition = evaluate_predicate(rule["condition"], case.facts, evaluations)
                if condition.truth is False:
                    result, predicate = "not_applicable", condition
                else:
                    result = "unknown"
                    predicate = PredicateResult(
                        None, gate.missing, {"all": [gate.trace, condition.trace], "truth": None}
                    )
            else:
                predicate = evaluate_predicate(rule["condition"], case.facts, evaluations)
                result = (
                    "unknown"
                    if predicate.truth is None
                    else "triggered"
                    if predicate.truth
                    else "not_triggered"
                )
            evaluations[rule["rule_id"]] = RuleEvaluation(
                rule_id=rule["rule_id"],
                module=rule["module"],
                category=rule["category"],
                subcondition=rule["subcondition"],
                result=result,
                assessment_outcome=rule["outcome"]["assessment_outcome"]
                if result == "triggered"
                else None,
                reason=rule["reason_template"]
                if result == "triggered"
                else "Required facts are unknown or unconfirmed."
                if result == "unknown"
                else "Predicate is false or rule is not applicable.",
                source_ids=rule["source_ids"],
                rag_query_key=rule["rag_query_key"],
                observed_facts={
                    k: case.facts.get(k, Fact(unit=self.field_specs[k].get("unit")))
                    for k in rule["required_facts"]
                },
                missing_fields=sorted(predicate.missing),
                condition_trace={"gate": gate.trace, "predicate": predicate.trace},
            )

        warnings = list(case.warnings)

        def value(key):
            f = case.facts.get(key, Fact())
            return f.value if f.status == "present" else None

        if value("hearing.unaided_better_ear_average_db") == 40:
            warnings.append(
                "HEARING_40_DB_FIGURE_TABLE_CONFLICT: licensing table uses >= 40; Figure 11 uses > 40; clinical review pending"
            )
        for key in (
            "cardiovascular.myocardial_infarction_history",
            "cardiovascular.chest_pain",
            "cardiovascular.shortness_of_breath",
        ):
            if value(key) is True:
                warnings.append(
                    f"OUTSIDE_HYPERTENSION_SCOPE:{key}: separate cardiovascular assessment required"
                )
        contradictions = set()
        if value("diabetes.present") is False and value("diabetes.treatment_category") not in (
            None,
            "none",
        ):
            contradictions.add("diabetes")
        if value("blackout.occurred") is False and any(
            value(k) is not None
            for k in (
                "blackout.mechanism_status",
                "blackout.episodes_separated_by_24h_count",
                "blackout.years_since_last_event",
            )
        ):
            contradictions.add("blackout")
        if (
            value("hearing.clinical_assessment") == "no_hearing_loss"
            and (value("hearing.unaided_better_ear_average_db") or 0) >= 40
        ):
            contradictions.add("hearing")
        for module in contradictions:
            warnings.append(f"CROSS_FIELD_CONFLICT:{module}")
        modules = []
        for module in case.modules_requested:
            items = [x for x in evaluations.values() if x.module == module]
            missing = sorted({key for x in items for key in x.missing_fields})
            positives = [x for x in items if x.result == "triggered"]
            values = [x.assessment_outcome for x in positives]
            if missing:
                values.append(Outcome.INSUFFICIENT)
            if module in contradictions:
                values = [Outcome.INSUFFICIENT]
            outcome = _outcome(values, self.precedence)
            module_warnings = []
            if module == "hypertension" and any(
                w.startswith("OUTSIDE_HYPERTENSION_SCOPE") for w in warnings
            ):
                module_warnings.append(
                    "Cardiovascular findings outside hypertension require separate human review."
                )
            if module in contradictions:
                module_warnings.append("Conflicting case facts require reconciliation.")
            if module == "vision" and value("vision.visual_field.reported_defect") is True:
                module_warnings.append("A reported field defect requires objective confirmation.")
            route = (
                WorkflowRoute.FAST
                if outcome == Outcome.MEETS
                else WorkflowRoute.MISSING
                if outcome == Outcome.INSUFFICIENT
                else WorkflowRoute.REVIEW
            )
            if module_warnings:
                route = WorkflowRoute.HUMAN
            modules.append(
                ModuleAssessment(
                    module=module,
                    assessment_outcome=outcome,
                    route=route,
                    triggered_rule_ids=[x.rule_id for x in positives],
                    missing_fields=missing,
                    warnings=module_warnings,
                )
            )
        outcome = _outcome([m.assessment_outcome for m in modules], self.precedence)
        route = (
            WorkflowRoute.FAST
            if all(m.route == WorkflowRoute.FAST for m in modules)
            else WorkflowRoute.HUMAN
            if any(m.route == WorkflowRoute.HUMAN for m in modules)
            else WorkflowRoute.MISSING
            if outcome == Outcome.INSUFFICIENT
            else WorkflowRoute.REVIEW
        )
        requests = [
            RAGRequest(
                request_id="RAG-" + digest([case.case_id, x.rule_id])[:16],
                request_type="triggered_rule_evidence"
                if x.result == "triggered"
                else "missing_information_guidance",
                rule_id=x.rule_id,
                source_ids=x.source_ids,
                category=x.category,
                subcondition=x.subcondition,
                rag_query_key=x.rag_query_key,
            )
            for x in evaluations.values()
            if x.result in {"triggered", "unknown"}
        ]
        return WorkflowRuleResult(
            result_id="RR-" + digest([digest(case), self.sha256])[:20],
            case_id=case.case_id,
            case_sha256=digest(case),
            ruleset_id=self.metadata["id"],
            ruleset_version=self.metadata["version"],
            ruleset_sha256=self.sha256,
            route=route,
            assessment_outcome=outcome,
            modules=modules,
            rules_evaluated=list(evaluations.values()),
            rag_requests=requests,
            processing_warnings=sorted(set(warnings)),
        )
