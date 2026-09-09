from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Route(StrEnum):
    FAST_PATH = "fast_path"
    RAG_REVIEW = "rag_review"
    MISSING_INFORMATION = "missing_information"
    HUMAN_REVIEW = "human_review"


class RuleTrace(BaseModel):
    rule_id: str
    result: str | bool | None = None
    detail: str | None = None


class RuleResult(BaseModel):
    case_id: str
    category: str
    subcondition: str
    licence_context: str = "commercial"
    rules: list[RuleTrace] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    route: Route
    upstream_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("case_id", "category", "subcondition", "licence_context")
    @classmethod
    def non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must be non-empty")
        return value
