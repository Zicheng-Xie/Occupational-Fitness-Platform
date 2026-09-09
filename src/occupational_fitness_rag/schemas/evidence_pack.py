from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RetrievalStatus(StrEnum):
    FOUND = "found"
    NO_EVIDENCE = "no_evidence"
    SKIPPED_FAST_PATH = "skipped_fast_path"
    SKIPPED_MISSING_INFORMATION = "skipped_missing_information"
    INVALID_ROUTE = "invalid_route"


class EvidenceItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    score: float
    section: str
    pages: list[int]
    excerpt: str
    source_name: str
    source_version: str
    vector_score: float | None = None
    bm25_score: float | None = None
    rerank_score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidencePack(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str
    status: RetrievalStatus
    filters: dict[str, str]
    semantic_query: str | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
