"""Chroma integration using an explicitly configured local Ollama embedding model."""

from occupational_fitness_rag.llm import require_local_url
from occupational_fitness_rag.provenance import digest


def build_local_chroma(root, config, index_sha256):
    try:
        from .local_embedding import LocalOllamaEmbedding
    except ImportError as exc:
        raise RuntimeError(
            "Install the chroma extra and start a local Ollama embedding service"
        ) from exc
    from .chroma_store import ChromaVectorStore

    url = require_local_url(config.ollama_url)
    embedding = LocalOllamaEmbedding(url=url, model_name=config.embedding_model)
    # Model/index changes use a new collection instead of leaving stale vectors.
    identity = digest([index_sha256, config.embedding_model, "direct_local_v1"])[:12]
    return ChromaVectorStore(
        root / config.persist_directory, config.collection_name + "_" + identity, embedding
    )
