from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SourceSettings:
    name: str
    version: str
    jurisdiction: str
    default_licence_context: str = "commercial"


@dataclass(frozen=True)
class IndexSettings:
    provider: str
    persist_directory: str
    collection_name: str


@dataclass(frozen=True)
class RetrievalSettings:
    candidate_k: int = 20
    bm25_k: int = 30
    top_k: int = 5
    use_bm25: bool = True
    rrf_k: int = 60
    reranker: str = "none"
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    max_filtered_documents: int = 2000


@dataclass(frozen=True)
class RoutingSettings:
    retrieve_on_routes: tuple[str, ...] = ("rag_review", "human_review")
    missing_info_policy: str = "short_circuit"


@dataclass(frozen=True)
class ChunkingSettings:
    max_chars: int = 1800
    overlap_chars: int = 180
    heading_size_ratio: float = 1.15


@dataclass(frozen=True)
class AppSettings:
    source: SourceSettings
    index: IndexSettings
    retrieval: RetrievalSettings
    routing: RoutingSettings
    chunking: ChunkingSettings
    annotations_file: str
    pilot_modules: tuple[str, ...]


def _get(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise ValueError(f"Expected mapping for config section '{key}'")
    return value


def load_settings(path: str | Path) -> AppSettings:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    src = _get(data, "source")
    idx = _get(data, "index")
    ret = _get(data, "retrieval")
    routing = _get(data, "routing")
    chunk = _get(data, "chunking")
    return AppSettings(
        source=SourceSettings(**src),
        index=IndexSettings(**idx),
        retrieval=RetrievalSettings(**ret),
        routing=RoutingSettings(
            retrieve_on_routes=tuple(
                routing.get("retrieve_on_routes", ["rag_review", "human_review"])
            ),
            missing_info_policy=routing.get("missing_info_policy", "short_circuit"),
        ),
        chunking=ChunkingSettings(**chunk),
        annotations_file=str(data.get("annotations_file", "configs/austroads_annotations.yaml")),
        pilot_modules=tuple(data.get("pilot_modules", [])),
    )
