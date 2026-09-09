from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StructuredCase(BaseModel):
    """Upstream output. RAG does not infer or modify these clinical facts."""

    case_id: str
    source_document: str | None = None
    licence_context: str = "commercial"
    facts: dict[str, Any] = Field(default_factory=dict)
    unknown_fields: list[str] = Field(default_factory=list)
    extraction_metadata: dict[str, Any] = Field(default_factory=dict)
