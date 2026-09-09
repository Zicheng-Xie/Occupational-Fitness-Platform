from __future__ import annotations

from occupational_fitness_rag.indexing.chroma_store import ChromaVectorStore
from occupational_fitness_rag.pipeline.austroads_rag import AustroadsRAGPipeline
from occupational_fitness_rag.retrieval.engine import RetrievalEngine
from occupational_fitness_rag.settings import AppSettings


def build_chroma_pipeline(settings: AppSettings) -> AustroadsRAGPipeline:
    store = ChromaVectorStore(settings.index.persist_directory, settings.index.collection_name)
    engine = RetrievalEngine(store, settings.retrieval)
    return AustroadsRAGPipeline(engine, settings)
