"""Versioned exchange between upstream fact extraction and category-scoped RAG."""

from typing import Literal

from pydantic import Field, model_validator

from occupational_fitness_rag.schemas.workflow import Citation, Contract

Module = Literal["hypertension", "vision", "hearing", "blackout", "diabetes"]


class IndicatorRequest(Contract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    case_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")
    indicator_id: str = Field(min_length=1, max_length=100)
    module: Module
    source_document: str = Field(min_length=1, max_length=200)
    source_text: str = Field(min_length=1, max_length=100000)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    top_k: int = Field(default=5, ge=1, le=20)
    expand_references: bool = True

    @model_validator(mode="after")
    def validate_span(self):
        if not self.start < self.end <= len(self.source_text):
            raise ValueError("Indicator offsets must identify a span in source_text")
        if not self.indicator_text.strip() or len(self.indicator_text) > 2000:
            raise ValueError("Select a non-empty indicator passage of at most 2,000 characters")
        return self

    @property
    def indicator_text(self) -> str:
        return self.source_text[self.start : self.end]


class IndicatorEvidence(Contract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    case_id: str
    indicator_id: str
    module: Module
    query: str
    source_document: str
    source_text_sha256: str
    start: int
    end: int
    index_sha256: str
    backend: str
    status: Literal["candidates_found", "no_candidates"]
    citations: list[Citation]
    related_citations: list[Citation]
    ranked_candidates: list[dict]
    filters: dict[str, str]
    assessment_outcome: None = None
    review_required: Literal[True] = True
