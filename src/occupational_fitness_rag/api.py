from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
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
    module: Literal["hypertension", "vision", "hearing", "blackout", "diabetes"]
    format: str
    text: str
    expected_red_flag_classification: RedFlagClassification
    expected_outcome: str


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
    guideline_references: list[GuidelineReference]
    expected_red_flag_classification: RedFlagClassification
    matches_expected_classification: bool
    expected_assessment_outcome: str
    matches_expected_outcome: bool


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
        case = app.state.experiment_cases.get(case_id)
        if case is None:
            raise HTTPException(404, "Experiment case not found")
        return case

    @app.post(
        "/experiment/cases/{case_id}/evaluate",
        response_model=ExperimentAssessmentResponse,
        tags=["Red Flag experiment"],
        summary="Evaluate a stored case and show the three-way result with PDF quotations",
    )
    def evaluate_experiment_case(case_id: str):
        experiment = app.state.experiment_cases.get(case_id)
        if experiment is None:
            raise HTTPException(404, "Experiment case not found")
        try:
            _, result, evidence, _ = app.state.workflow.from_text(
                experiment.text,
                experiment.case_id,
                modules=[experiment.module],
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
            guideline_references=list(references.values()),
            expected_red_flag_classification=experiment.expected_red_flag_classification,
            matches_expected_classification=(
                classification == experiment.expected_red_flag_classification
            ),
            expected_assessment_outcome=experiment.expected_outcome,
            matches_expected_outcome=result.assessment_outcome == experiment.expected_outcome,
        )

    @app.post("/rag/retrieve", response_model=WorkflowEvidencePack)
    def retrieve(result: RAGInput):
        try:
            return app.state.workflow.retriever.run(result)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    return app


app = create_app()
