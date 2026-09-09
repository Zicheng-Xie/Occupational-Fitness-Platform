from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CategoryFacts(BaseModel):
    """Facts routed to one deterministic rule module.

    This is a category mapping object only. It does not express a fitness outcome.
    """

    model_config = ConfigDict(frozen=True)

    category: str
    facts: dict[str, Any] = Field(default_factory=dict)
    explicit_missing: list[str] = Field(default_factory=list)


class CaseIntakeResult(BaseModel):
    """Output of the test-fixture nurse-note intake adapter."""

    model_config = ConfigDict(frozen=True)

    case_id: str
    source_document: str
    licence_context: str = "commercial"
    structured_facts: dict[str, Any] = Field(default_factory=dict)
    explicit_missing: list[str] = Field(default_factory=list)
    category_map: list[CategoryFacts] = Field(default_factory=list)
    extraction_method: str = "deterministic_regex_fixture_parser"
    notes: list[str] = Field(default_factory=list)
