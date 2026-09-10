from __future__ import annotations

import os
from contextlib import asynccontextmanager
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


class RedFlagAssessmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    structured_case: ClinicalCase
    rule_result: WorkflowRuleResult
    rag_input: RAGInput


def create_app(config_path: str | None = None) -> FastAPI:
    config_path = config_path or os.environ.get("FITNESS_WORKFLOW_CONFIG", "configs/workflow.yaml")

    @asynccontextmanager
    async def lifespan(app):
        app.state.workflow = OccupationalFitnessWorkflow(config_path)
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
        return {
            "structured_case": case.model_dump(mode="json"),
            "rule_result": result.model_dump(mode="json"),
            "rag_input": result.rag_input().model_dump(mode="json"),
        }

    @app.post("/rag/retrieve", response_model=WorkflowEvidencePack)
    def retrieve(result: RAGInput):
        try:
            return app.state.workflow.retriever.run(result)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    return app


app = create_app()
