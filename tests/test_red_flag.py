from pathlib import Path

import pytest

from occupational_fitness_rag.case_intake.traceable import extract_traceable_file
from occupational_fitness_rag.pipeline.workflow import OccupationalFitnessWorkflow
from occupational_fitness_rag.red_flag import RedFlagEvaluator
from occupational_fitness_rag.schemas.red_flag_result import RAGInput, WorkflowRuleResult

PUBLIC_FIELDS = {
    "schema_version",
    "result_id",
    "case_id",
    "case_sha256",
    "source",
    "assessment_context",
    "ruleset",
    "route",
    "assessment_outcome",
    "outcome_label",
    "has_red_flag",
    "red_flags",
    "triggered_rules",
    "missing_information",
    "modules",
    "rules_evaluated",
    "processing_warnings",
    "requires_human_review",
    "rag_requests",
    "internal_metadata",
}

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def workflow():
    return OccupationalFitnessWorkflow(ROOT / "configs/workflow.offline.yaml")


def test_red_flag_stage_runs_before_retrieval(workflow):
    source = workflow.root / "data/cases/synthetic_expansion/SYN-EXT-003.txt"
    case = extract_traceable_file(source, workflow.book.field_specs)

    result = workflow.red_flag.evaluate(case)

    assert RedFlagEvaluator.has_red_flag(result)
    assert result.assessment_outcome == "temporarily_unfit"
    assert result.route != "fast_path"
    assert RedFlagEvaluator.red_flag_rules(result)
    assert result.red_flags
    assert result.triggered_rules
    assert set(result.model_dump()) == PUBLIC_FIELDS


def test_missing_information_is_not_mislabeled_as_red_flag(workflow):
    source = workflow.root / "data/cases/nurse_notes/SYN-M2-003.txt"
    case = extract_traceable_file(source, workflow.book.field_specs)

    result = workflow.red_flag.evaluate(case)

    assert result.assessment_outcome == "insufficient_information"
    assert not RedFlagEvaluator.has_red_flag(result)
    assert result.has_red_flag is False
    assert result.missing_information
    assert any(
        request.request_type == "missing_information_guidance" for request in result.rag_requests
    )
    evidence = workflow.retriever.run(result.rag_input())
    assert evidence.retrieval["ranking_calls"] > 0
    assert any(request.ambiguity_reasons for request in result.rag_requests)
    assert all(
        set(request.fact_context) <= set(workflow.book.field_specs)
        for request in result.rag_requests
    )


def test_conflicting_fact_uses_public_ambiguity_reason(workflow):
    _, result = workflow.red_flag_from_text(
        "diabetes.present = true\ndiabetes.present = false",
        "CONFLICTING-AMBIGUITY-001",
        ["diabetes"],
    )

    requests = [
        request
        for request in result.rag_requests
        if request.fact_context.get("diabetes.present") == "conflicting"
    ]
    assert requests
    assert all("conflicting_fact" in request.ambiguity_reasons for request in requests)
    assert all("conflicting" not in request.ambiguity_reasons for request in requests)


def test_non_fast_red_flag_binds_sources_and_ranks_every_request(workflow):
    source = workflow.root / "data/cases/synthetic_expansion/SYN-EXT-003.txt"
    case = extract_traceable_file(source, workflow.book.field_specs)
    result = workflow.red_flag.evaluate(case)

    red_flag_ids = {rule.rule_id for rule in result.red_flags}
    assert red_flag_ids
    assert all(
        request.request_type == "triggered_rule_evidence"
        for request in result.rag_requests
        if request.rule_id in red_flag_ids
    )
    evidence = workflow.retriever.run(result.rag_input())
    assert evidence.retrieval["ranking_calls"] == len(result.rag_requests)
    assert all(item.semantic_query for item in evidence.evidence_items)


def test_workflow_routes_searches_through_original_rag_pipeline(workflow, monkeypatch):
    calls = []
    original_run = workflow.retriever.original_rag.run

    def record_call(result):
        calls.append(result)
        return original_run(result)

    monkeypatch.setattr(workflow.retriever.original_rag, "run", record_call)
    _, result = workflow.red_flag_from_text(
        "Reports reduced hearing. No audiometry or audiogram is available.",
        "ORIGINAL-RAG-ROUTE-001",
        ["hearing"],
    )
    workflow.retriever.run(result.rag_input())

    assert calls
    assert any(call.route == "missing_information" for call in calls)
    assert all(call.route in {"missing_information", "rag_review"} for call in calls)
    assert any(call.missing for call in calls)


def test_red_flag_contract_round_trip_and_rag_boundary(workflow):
    source = workflow.root / "data/cases/synthetic_expansion/SYN-EXT-003.txt"
    case = extract_traceable_file(source, workflow.book.field_specs)
    result = workflow.red_flag.evaluate(case)

    restored = WorkflowRuleResult.model_validate_json(result.model_dump_json())
    rag_input = restored.rag_input()

    assert rag_input.red_flag_result_sha256
    assert rag_input.rag_requests == restored.rag_requests
    assert "rules_evaluated" not in rag_input.model_dump()
    assert "triggered_rules" not in rag_input.model_dump()
    assert "missing_information" not in rag_input.model_dump()


def test_workflow_rule_result_is_strictly_v1_3(workflow):
    source = workflow.root / "data/cases/synthetic_expansion/SYN-EXT-003.txt"
    case = extract_traceable_file(source, workflow.book.field_specs)
    payload = workflow.red_flag.evaluate(case).model_dump(mode="json")

    assert payload["schema_version"] == "1.3.0"
    for obsolete in ("ruleset_id", "ruleset_version", "ruleset_sha256"):
        payload[obsolete] = "obsolete-v1.2-field"
    with pytest.raises(ValueError):
        WorkflowRuleResult.model_validate(payload)


def test_rag_input_rejects_full_red_flag_payload(workflow):
    source = workflow.root / "data/cases/synthetic_expansion/SYN-EXT-003.txt"
    case = extract_traceable_file(source, workflow.book.field_specs)
    payload = workflow.red_flag.evaluate(case).model_dump(mode="json")

    try:
        RAGInput.model_validate(payload)
    except ValueError:
        pass
    else:
        raise AssertionError("RAG must not accept the complete Red Flag decision payload")


def test_diagnosed_blackout_preserves_insufficient_route_and_retrieves_evidence(workflow):
    case, result = workflow.red_flag_from_text(
        "SYNTHETIC VALIDATION FIXTURE - NOT A REAL PATIENT.\n"
        "blackout.occurred = true\n"
        'blackout.mechanism_status = "diagnosed"\n'
        'blackout.diagnosis = "cardiac_syncope"',
        "API-BLACKOUT-RAG-ROUTE-001",
        ["blackout"],
    )

    assert case.modules_requested == ["blackout"]
    assert result.assessment_outcome == "insufficient_information"
    assert result.route == "missing_information"
    assert result.modules[0].route == "missing_information"
    assert result.missing_information == []
    assert result.has_red_flag is False
    assert [rule.rule_id for rule in result.triggered_rules] == ["BLK-COM-DIAGNOSED-REFERRAL-001"]
    assert [request.rule_id for request in result.rag_requests] == [
        "BLK-COM-DIAGNOSED-REFERRAL-001"
    ]
    assert result.rag_requests[0].request_type == "triggered_rule_evidence"
    assert workflow.retriever.run(result.rag_input()).retrieval["ranking_calls"] == 1


def test_grounded_route_model_can_escalate_but_not_downgrade(workflow):
    _, fast = workflow.red_flag_from_text(
        'hearing.clinical_assessment = "no_hearing_loss"',
        "ROUTE-MODEL-FAST-001",
        ["hearing"],
    )
    escalated = workflow.red_flag.apply_route_suggestion(
        fast,
        {
            "status": "grounded",
            "route": "rag_fusion",
            "reason": "Complex wording requires guideline synthesis.",
            "evidence_quotes": ['hearing.clinical_assessment = "no_hearing_loss"'],
        },
    )
    assert fast.route == "fast_path"
    assert escalated.route == "rag_review"

    _, missing = workflow.red_flag_from_text(
        "Reports reduced hearing. No audiometry or audiogram is available.",
        "ROUTE-MODEL-MISSING-001",
        ["hearing"],
    )
    not_downgraded = workflow.red_flag.apply_route_suggestion(
        missing,
        {
            "status": "grounded",
            "route": "local_result",
            "reason": "Model suggested a local result.",
            "evidence_quotes": ["Reports reduced hearing"],
        },
    )
    assert not_downgraded.route == "missing_information"


@pytest.mark.parametrize(
    "provoking,recurrence,triggered",
    [
        (True, True, True),
        (True, False, False),
        (False, True, False),
        (True, None, False),
        (None, True, False),
        (None, None, False),
    ],
)
def test_vasovagal_exception_preserves_original_and_condition(
    workflow, provoking, recurrence, triggered
):
    fields = {
        "blackout.provoking_factor_well_defined": provoking,
        "blackout.recurrence_while_driving_unlikely": recurrence,
    }
    import json

    _, result = workflow.red_flag_from_text(
        "blackout.occurred = true\n"
        'blackout.diagnosis = "vasovagal_syncope"\n'
        + "\n".join(
            f"{key} = {json.dumps(value)}" for key, value in fields.items() if value is not None
        ),
        "VASOVAGAL-AND-001",
        ["blackout"],
    )

    assert (
        "BLK-COM-VASOVAGAL-EXCEPTION-001" in {item.rule_id for item in result.triggered_rules}
    ) is triggered
