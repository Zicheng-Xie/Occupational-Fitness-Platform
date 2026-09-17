from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field

from occupational_fitness_rag.pipeline.workflow import OccupationalFitnessWorkflow
from occupational_fitness_rag.schemas.red_flag_result import RAGInput, WorkflowRuleResult
from occupational_fitness_rag.schemas.workflow import (
    MODULES,
    ClinicalCase,
    ReviewNote,
    WorkflowEvidencePack,
)


class AssessmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")
    text: str = Field(min_length=1, max_length=100000)
    modules_requested: list[
        Literal["hypertension", "vision", "hearing", "blackout", "diabetes"]
    ] = Field(default_factory=lambda: list(MODULES), min_length=1)


class AssessmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    structured_case: ClinicalCase
    rule_result: WorkflowRuleResult
    rag_input: RAGInput
    evidence_pack: WorkflowEvidencePack
    gp_review_note: ReviewNote


class RelevantSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    section: str
    printed_page: int
    pdf_page: int


class RedFlagAssessmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    structured_case: ClinicalCase
    routing_category: Literal["local_result", "needs_more_information", "rag_fusion"]
    rule_result: WorkflowRuleResult
    relevant_sections: list[RelevantSection]
    rag_input: RAGInput | None = None


RedFlagClassification = Literal["RED_FLAG", "NEEDS_MORE_INFORMATION", "NO_RED_FLAG"]


class ExperimentCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    module: Literal["hypertension", "vision", "hearing", "blackout", "diabetes", "all"]
    format: str
    text: str
    expected_red_flag_classification: RedFlagClassification | None = None
    expected_outcome: str | None = None


class GuidelineReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    document: Literal["AP-G56-22"]
    section: str
    printed_page: int
    pdf_page: int
    table_row: str | None = None
    source_text: str
    source_path: str
    verified_against_source: Literal[True]


class ExtractedFactSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str
    value: Any = None
    status: Literal["present", "unknown", "conflicting", "requires_confirmation"]
    method: str
    evidence_quotes: list[str]


class ProcessingStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step: int
    name: Literal[
        "case_loaded",
        "text_structured",
        "ollama_grounding",
        "red_flag_rules",
        "route_selected",
        "rag_retrieval",
        "pdf_evidence_bound",
        "final_output_prepared",
    ]
    status: Literal["completed", "needs_attention"]
    summary: str


class FinalTextOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["DIRECT_RESULT", "RAG_INPUT"]
    filename: str
    media_type: Literal["text/plain"] = "text/plain"
    text: str


class RAGExecutionSummary(BaseModel):
    """Human-readable proof that the downstream retrieval stage ran."""

    model_config = ConfigDict(extra="forbid")
    invoked: bool
    request_count: int
    backend: str
    embedding_model: str
    ranking_calls: int
    evidence_item_count: int
    unresolved_request_count: int
    rule_result_fields_modified_by_rag: bool
    requests: list[dict[str, Any]]
    ranked_candidates: list[dict[str, Any]]


class ExperimentAssessmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    module: str
    input_format: str
    input_text: str
    red_flag_classification: RedFlagClassification
    has_red_flag: bool
    assessment_outcome: str
    route: str
    triggered_rule_ids: list[str]
    red_flag_rule_ids: list[str]
    missing_fields: list[str]
    extracted_facts: list[ExtractedFactSummary]
    processing_steps: list[ProcessingStep]
    rag_execution: RAGExecutionSummary
    guideline_references: list[GuidelineReference]
    final_output: FinalTextOutput
    expected_red_flag_classification: RedFlagClassification | None = None
    matches_expected_classification: bool | None = None
    expected_assessment_outcome: str | None = None
    matches_expected_outcome: bool | None = None


def _red_flag_classification(result: WorkflowRuleResult) -> RedFlagClassification:
    if result.has_red_flag:
        return "RED_FLAG"
    if result.assessment_outcome == "insufficient_information" or result.missing_information:
        return "NEEDS_MORE_INFORMATION"
    return "NO_RED_FLAG"


def _load_experiment_cases(root: Path) -> dict[str, ExperimentCase]:
    directory = (root / "data/cases/red_flag_experiment").resolve()
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    cases = {}
    for entry in manifest["cases"]:
        source = (directory / entry["file"]).resolve()
        if source.parent != directory or source.suffix.lower() != ".txt":
            raise ValueError("Experiment manifest contains an invalid case path")
        case = ExperimentCase(
            case_id=entry["case_id"],
            module=entry["module"],
            format=entry["format"],
            text=source.read_text(encoding="utf-8"),
            expected_red_flag_classification=entry["expected_red_flag_classification"],
            expected_outcome=entry["expected_outcome"],
        )
        cases[case.case_id] = case
    return cases


def _load_existing_text_case(root: Path, case_id: str) -> ExperimentCase | None:
    """Resolve an existing repository TXT case without accepting arbitrary paths."""

    if not case_id or any(
        character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-"
        for character in case_id
    ):
        return None
    for relative_directory in ("data/cases/synthetic_expansion", "data/cases/nurse_notes"):
        directory = (root / relative_directory).resolve()
        source = (directory / f"{case_id}.txt").resolve()
        if source.parent == directory and source.is_file():
            return ExperimentCase(
                case_id=case_id,
                module="all",
                format="existing UTF-8 text case",
                text=source.read_text(encoding="utf-8"),
            )
    return None


def _final_text_output(result: WorkflowRuleResult, classification: str) -> FinalTextOutput:
    use_rag = result.has_red_flag or result.route in {"rag_review", "human_review"}
    mode = "RAG_INPUT" if use_rag else "DIRECT_RESULT"
    classification_label = {
        "RED_FLAG": "Red flag: an explicit driving-safety risk is present",
        "NEEDS_MORE_INFORMATION": "Insufficient information: more evidence is required",
        "NO_RED_FLAG": "No red flag identified",
    }[classification]
    outcome_label = {
        "meets_unconditional_standard": "Meets the unconditional standard",
        "may_meet_conditional_standard": "May meet a conditional standard; review required",
        "temporarily_unfit": "Temporarily unfit to drive",
        "does_not_meet_standard": "Does not meet the standard",
        "insufficient_information": "Insufficient information to complete the assessment",
    }[result.assessment_outcome]
    next_action = (
        "Send the specified PDF evidence request to RAG and retain the rule result for clinical review."
        if use_rag
        else "Return the deterministic local result directly; RAG is not required."
    )
    red_flag_ids = [rule.rule_id for rule in result.red_flags]
    primary_requests = [
        request for request in result.rag_requests if request.rule_id in red_flag_ids
    ]
    supplementary_requests = [
        request for request in result.rag_requests if request.rule_id not in red_flag_ids
    ]
    missing = sorted({item.field for item in result.missing_information})
    lines = [
        "Occupational Fitness RED FLAG Assessment",
        "=" * 52,
        "",
        "[1. Final determination]",
        f"Case: {result.case_id}",
        f"Classification: {classification_label}",
        f"Fitness outcome: {outcome_label}",
        f"Next action: {next_action}",
        "",
        "[2. Decision basis]",
    ]
    if result.red_flags:
        for rule in result.red_flags:
            lines += [f"- Red-flag rule: {rule.rule_id}", f"  Reason: {rule.reason}"]
    elif result.triggered_rules:
        for rule in result.triggered_rules:
            lines += [f"- Triggered rule: {rule.rule_id}", f"  Reason: {rule.reason}"]
    else:
        lines.append("- No deterministic rule was triggered.")
    lines += ["", "[3. Information still required]"]
    if missing:
        lines.append(
            "These fields support further assessment and do not revoke an established red flag:"
        )
        lines += [f"- {field}" for field in missing]
    else:
        lines.append("- None.")
    if use_rag:
        lines += ["", "[4. Primary RAG tasks]"]
        if primary_requests:
            for request in primary_requests:
                lines += [
                    f"- Rule: {request.rule_id}",
                    f"  Retrieval key: {request.rag_query_key}",
                    f"  Required PDF sources: {', '.join(request.source_ids)}",
                    "  Purpose: retrieve original guideline evidence supporting the red-flag result.",
                ]
        else:
            lines.append(
                "- No standalone red-flag rule; RAG supports complex or cross-section review."
            )
        lines += ["", "[5. Supplementary RAG tasks]"]
        if supplementary_requests:
            lines.append(
                "These tasks add context and must not alter the deterministic rule result:"
            )
        for request in supplementary_requests:
            lines += [
                f"- Related rule: {request.rule_id}",
                f"  Ambiguity reasons: {', '.join(request.ambiguity_reasons) or 'none'}",
                f"  Required PDF sources: {', '.join(request.source_ids)}",
            ]
        if not supplementary_requests:
            lines.append("- None.")
    else:
        lines += [
            "",
            "[4. RAG processing]",
            "- RAG is not invoked; return the rule result directly.",
        ]
    lines += [
        "",
        "[Machine-readable summary]",
        f"CASE_ID={result.case_id}",
        f"CLASSIFICATION={classification}",
        f"ASSESSMENT_OUTCOME={result.assessment_outcome}",
        f"HAS_RED_FLAG={str(result.has_red_flag).lower()}",
        f"RULE_ROUTE={result.route}",
        "TRIGGERED_RULES=" + (",".join(rule.rule_id for rule in result.triggered_rules) or "none"),
        "RED_FLAG_RULES=" + (",".join(red_flag_ids) or "none"),
        "MISSING_FIELDS=" + (",".join(missing) or "none"),
        f"OUTPUT_MODE={mode}",
    ]
    return FinalTextOutput(
        mode=mode,
        filename=f"{result.case_id}.{'rag-input' if use_rag else 'direct-result'}.txt",
        text="\n".join(lines) + "\n",
    )


def create_app(config_path: str | None = None) -> FastAPI:
    config_path = config_path or os.environ.get("FITNESS_WORKFLOW_CONFIG", "configs/workflow.yaml")

    @asynccontextmanager
    async def lifespan(app):
        app.state.workflow = OccupationalFitnessWorkflow(config_path)
        app.state.experiment_cases = _load_experiment_cases(app.state.workflow.root)
        yield

    app = FastAPI(
        title="Occupational Fitness Platform",
        version="0.4.0",
        lifespan=lifespan,
    )

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "ruleset_status": "pending_clinical_review",
            "index_sha256": app.state.workflow.catalogue.index_sha256,
        }

    @app.post("/assess", response_model=AssessmentResponse)
    def assess(request: AssessmentInput):
        try:
            case, result, evidence, note = app.state.workflow.from_text(
                request.text, request.case_id, modules=request.modules_requested
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return {
            "structured_case": case.model_dump(mode="json"),
            "rule_result": result.model_dump(mode="json"),
            "rag_input": result.rag_input().model_dump(mode="json"),
            "evidence_pack": evidence.model_dump(mode="json"),
            "gp_review_note": note.model_dump(mode="json"),
        }

    @app.post("/red-flag/evaluate", response_model=RedFlagAssessmentResponse)
    def evaluate_red_flag(request: AssessmentInput):
        try:
            case, result = app.state.workflow.red_flag_from_text(
                request.text, request.case_id, modules=request.modules_requested
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        category = {
            "fast_path": "local_result",
            "missing_information": "needs_more_information",
            "rag_review": "rag_fusion",
            "human_review": "rag_fusion",
        }[result.route]
        source_ids = sorted(
            {source_id for item in result.rag_requests for source_id in item.source_ids}
        )
        citations = [app.state.workflow.catalogue.citation(source_id) for source_id in source_ids]
        return {
            "structured_case": case.model_dump(mode="json"),
            "routing_category": category,
            "rule_result": result.model_dump(mode="json"),
            "relevant_sections": [
                {
                    "source_id": citation.source_id,
                    "section": citation.section,
                    "printed_page": citation.printed_page,
                    "pdf_page": citation.pdf_page,
                }
                for citation in citations
                if citation is not None
            ],
            "rag_input": result.rag_input().model_dump(mode="json")
            if category == "rag_fusion"
            else None,
        }

    @app.get(
        "/experiment/cases",
        response_model=list[ExperimentCase],
        tags=["Red Flag experiment"],
        summary="List the 15 varied synthetic cases",
    )
    def list_experiment_cases():
        return list(app.state.experiment_cases.values())

    @app.get(
        "/experiment/cases/{case_id}",
        response_model=ExperimentCase,
        tags=["Red Flag experiment"],
        summary="Read one synthetic case and its expected class",
    )
    def get_experiment_case(case_id: str):
        case = app.state.experiment_cases.get(case_id) or _load_existing_text_case(
            app.state.workflow.root, case_id
        )
        if case is None:
            raise HTTPException(404, "Experiment case not found")
        return case

    def run_experiment_case(case_id: str) -> ExperimentAssessmentResponse:
        experiment = app.state.experiment_cases.get(case_id) or _load_existing_text_case(
            app.state.workflow.root, case_id
        )
        if experiment is None:
            raise HTTPException(404, "Experiment case not found")
        try:
            case, result, evidence, _ = app.state.workflow.from_text(
                experiment.text,
                experiment.case_id,
                modules=None if experiment.module == "all" else [experiment.module],
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

        references = {}
        for item in evidence.evidence_items:
            for citation in item.citations:
                references[citation.source_id] = GuidelineReference(
                    source_id=citation.source_id,
                    document=citation.document_id,
                    section=citation.section,
                    printed_page=citation.printed_page,
                    pdf_page=citation.pdf_page,
                    table_row=citation.table_row,
                    source_text=citation.source_text,
                    source_path=citation.source_path,
                    verified_against_source=citation.verified_against_source,
                )
        classification = _red_flag_classification(result)
        missing_fields = sorted({item.field for item in result.missing_information})
        extracted_facts = [
            ExtractedFactSummary(
                field=field,
                value=fact.value,
                status=fact.status,
                method=fact.method,
                evidence_quotes=[span.quote for span in fact.evidence],
            )
            for field, fact in case.facts.items()
            if fact.status != "unknown"
        ]
        intake = case.extraction_metadata
        accepted = intake.get("accepted_fields", [])
        withheld = intake.get("withheld", [])
        final_output = _final_text_output(result, classification)
        ranked_candidates = [
            {
                "request_id": item.request_id,
                **candidate,
            }
            for item in evidence.evidence_items
            for candidate in item.ranked_candidates
        ]
        rag_execution = RAGExecutionSummary(
            invoked=bool(result.rag_requests),
            request_count=len(result.rag_requests),
            backend=evidence.retrieval["backend"],
            embedding_model=evidence.retrieval["embedding_model"],
            ranking_calls=evidence.retrieval["ranking_calls"],
            evidence_item_count=len(evidence.evidence_items),
            unresolved_request_count=len(evidence.unresolved_requests),
            rule_result_fields_modified_by_rag=evidence.integrity[
                "rule_result_fields_modified_by_rag"
            ],
            requests=[request.model_dump(mode="json") for request in result.rag_requests],
            ranked_candidates=ranked_candidates,
        )
        processing_steps = [
            ProcessingStep(
                step=1,
                name="case_loaded",
                status="completed",
                summary=(
                    f"Loaded {experiment.format} UTF-8 text for the {experiment.module} module."
                ),
            ),
            ProcessingStep(
                step=2,
                name="text_structured",
                status="completed" if extracted_facts else "needs_attention",
                summary=(
                    f"Validated {len(extracted_facts)} non-unknown dictionary facts with exact "
                    "source quotations."
                ),
            ),
            ProcessingStep(
                step=3,
                name="ollama_grounding",
                status=(
                    "needs_attention"
                    if str(intake.get("status", "")).startswith("unavailable")
                    else "completed"
                ),
                summary=(
                    f"Ollama status={intake.get('status', 'not_recorded')}; "
                    f"model={intake.get('model', 'not_recorded')}; "
                    f"accepted={len(accepted)}; withheld={len(withheld)}. "
                    "Deterministic grounded facts remain available as fallback."
                ),
            ),
            ProcessingStep(
                step=4,
                name="red_flag_rules",
                status="completed",
                summary=(
                    f"Evaluated {len(result.rules_evaluated)} rules; triggered "
                    f"{len(result.triggered_rules)}; Red Flag rules={len(result.red_flags)}; "
                    f"outcome={result.assessment_outcome}."
                ),
            ),
            ProcessingStep(
                step=5,
                name="route_selected",
                status="needs_attention" if missing_fields else "completed",
                summary=(
                    f"Three-way classification={classification}; rule route={result.route}; "
                    f"missing fields={len(missing_fields)}."
                ),
            ),
            ProcessingStep(
                step=6,
                name="rag_retrieval",
                status="completed" if not evidence.unresolved_requests else "needs_attention",
                summary=(
                    f"Downstream RAG invoked={rag_execution.invoked}; backend="
                    f"{rag_execution.backend}; embedding={rag_execution.embedding_model}; "
                    f"requests={rag_execution.request_count}; ranking calls="
                    f"{rag_execution.ranking_calls}; candidates={len(ranked_candidates)}; "
                    f"unresolved={rag_execution.unresolved_request_count}."
                ),
            ),
            ProcessingStep(
                step=7,
                name="pdf_evidence_bound",
                status="completed" if references else "needs_attention",
                summary=(
                    f"Bound {len(references)} AP-G56-22 quotations verified against the source PDF."
                ),
            ),
            ProcessingStep(
                step=8,
                name="final_output_prepared",
                status="completed",
                summary=f"Prepared {final_output.mode} as {final_output.filename}.",
            ),
        ]
        return ExperimentAssessmentResponse(
            case_id=experiment.case_id,
            module=experiment.module,
            input_format=experiment.format,
            input_text=experiment.text,
            red_flag_classification=classification,
            has_red_flag=result.has_red_flag,
            assessment_outcome=result.assessment_outcome,
            route=result.route,
            triggered_rule_ids=[rule.rule_id for rule in result.triggered_rules],
            red_flag_rule_ids=[rule.rule_id for rule in result.red_flags],
            missing_fields=missing_fields,
            extracted_facts=extracted_facts,
            processing_steps=processing_steps,
            rag_execution=rag_execution,
            guideline_references=list(references.values()),
            final_output=final_output,
            expected_red_flag_classification=experiment.expected_red_flag_classification,
            matches_expected_classification=(
                classification == experiment.expected_red_flag_classification
                if experiment.expected_red_flag_classification is not None
                else None
            ),
            expected_assessment_outcome=experiment.expected_outcome,
            matches_expected_outcome=(
                result.assessment_outcome == experiment.expected_outcome
                if experiment.expected_outcome is not None
                else None
            ),
        )

    @app.post(
        "/experiment/cases/{case_id}/evaluate",
        response_model=ExperimentAssessmentResponse,
        tags=["Red Flag experiment"],
        summary="Evaluate a stored case and show the three-way result with PDF quotations",
    )
    def evaluate_experiment_case(case_id: str):
        return run_experiment_case(case_id)

    @app.post(
        "/experiment/cases/{case_id}/evaluate.txt",
        response_class=PlainTextResponse,
        tags=["Red Flag experiment"],
        summary="Show the final RAG input or direct decision as UTF-8 text",
        responses={
            200: {
                "content": {
                    "text/plain": {
                        "example": (
                            "Occupational Fitness RED FLAG Assessment\n"
                            "\n[1. Final determination]\n"
                            "Classification: Red flag: an explicit driving-safety risk is present\n"
                            "Fitness outcome: Temporarily unfit to drive\n"
                            "\n[2. Decision basis]\n"
                            "- Red-flag rule: BLK-COM-UNDIAGNOSED-001\n"
                        )
                    }
                }
            }
        },
    )
    def evaluate_experiment_case_text(case_id: str):
        output = run_experiment_case(case_id).final_output
        return PlainTextResponse(
            output.text,
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f'inline; filename="{output.filename}"',
                "X-Result-Mode": output.mode,
            },
        )

    @app.post("/rag/retrieve", response_model=WorkflowEvidencePack)
    def retrieve(result: RAGInput):
        try:
            return app.state.workflow.retriever.run(result)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    return app


app = create_app()
