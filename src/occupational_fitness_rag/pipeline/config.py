from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class RetrievalConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["exact", "hybrid_local", "chroma"] = "hybrid_local"
    top_k: int = Field(default=5, ge=1, le=50)
    candidate_k: int = Field(default=20, ge=1, le=200)
    collection_name: str = "aftd_commercial_v1_1"
    persist_directory: str = "data/knowledge/indexes/chroma"
    embedding_model: str = "nomic-embed-text"
    ollama_url: str = "http://127.0.0.1:11434"


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    provider: Literal["ollama"] = "ollama"
    base_url: str = "http://127.0.0.1:11434"
    model: str = "llama3:8b"
    timeout_seconds: int = Field(default=60, ge=1, le=120)
    extraction_enabled: bool = True
    narrative_enabled: bool = False
    context_length: int = Field(default=8192, ge=2048, le=32768)
    max_output_tokens: int = Field(default=2048, ge=128, le=4096)
    max_input_chars: int = Field(default=10000, ge=100, le=30000)
    think: bool | None = None
    model_digest: str | None = None


class WorkflowConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.2.0"] = "1.2.0"
    project_root: str = ".."
    rules: str
    anchors: str
    catalogue: str
    output_directory: str = "outputs/runs"
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)


def load_workflow_config(path: str | Path) -> tuple[WorkflowConfig, Path]:
    path = Path(path).resolve()
    config = WorkflowConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    root = (path.parent / config.project_root).resolve()
    for value in (
        config.rules,
        config.anchors,
        config.catalogue,
        config.output_directory,
        config.retrieval.persist_directory,
    ):
        if not (root / value).resolve().is_relative_to(root):
            raise ValueError("Configured path must remain inside the project root")
    return config, root
