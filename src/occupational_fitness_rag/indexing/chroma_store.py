from __future__ import annotations

from pathlib import Path
from typing import Any

from occupational_fitness_rag.ingestion.models import GuidelineChunk

from .base import StoredDocument


def _serialise_metadata(chunk: GuidelineChunk) -> dict[str, Any]:
    md = dict(chunk.metadata)
    md.update(
        {
            "section": chunk.section,
            "title": chunk.title,
            "pages_csv": ",".join(str(p) for p in chunk.pages),
            "first_page": min(chunk.pages) if chunk.pages else -1,
            "last_page": max(chunk.pages) if chunk.pages else -1,
        }
    )
    # Chroma metadata should remain scalar for broad version compatibility.
    out: dict[str, Any] = {}
    for key, value in md.items():
        if isinstance(value, (str, int, float, bool)):
            out[key] = value
        elif value is not None:
            out[key] = str(value)
    return out


def _parse_pages(metadata: dict[str, Any]) -> list[int]:
    raw = str(metadata.get("pages_csv", ""))
    return [int(x) for x in raw.split(",") if x.strip().isdigit()]


def _where_clause(where: dict[str, str]) -> dict[str, Any] | None:
    if not where:
        return None
    if len(where) == 1:
        key, value = next(iter(where.items()))
        return {key: value}
    return {"$and": [{key: value} for key, value in where.items()]}


class ChromaVectorStore:
    def __init__(
        self, persist_directory: str | Path, collection_name: str, embedding_function=None
    ):
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError("Install the Chroma extra: pip install -e '.[chroma]'") from exc
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(persist_directory))
        options = (
            {"embedding_function": embedding_function} if embedding_function is not None else {}
        )
        self.collection = self.client.get_or_create_collection(name=collection_name, **options)

    def add(self, chunks: list[GuidelineChunk]) -> None:
        if not chunks:
            return
        self.collection.upsert(
            ids=[c.chunk_id for c in chunks],
            documents=[c.text for c in chunks],
            metadatas=[_serialise_metadata(c) for c in chunks],
        )

    def search(self, query: str, where: dict[str, str], k: int) -> list[StoredDocument]:
        if self.collection.count() == 0:
            return []
        result = self.collection.query(
            query_texts=[query],
            where=_where_clause(where),
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        ids = (result.get("ids") or [[]])[0]
        docs = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        out = []
        for chunk_id, text, md, distance in zip(ids, docs, metadatas, distances):
            md = dict(md or {})
            md["pages"] = _parse_pages(md)
            score = 1.0 / (1.0 + max(float(distance), 0.0))
            out.append(StoredDocument(str(chunk_id), str(text or ""), md, score))
        return out

    def get_filtered(self, where: dict[str, str], limit: int | None = None) -> list[StoredDocument]:
        kwargs: dict[str, Any] = {
            "where": _where_clause(where),
            "include": ["documents", "metadatas"],
        }
        if limit is not None:
            kwargs["limit"] = int(limit)
        result = self.collection.get(**kwargs)
        out = []
        for chunk_id, text, md in zip(
            result.get("ids", []), result.get("documents", []), result.get("metadatas", [])
        ):
            md = dict(md or {})
            md["pages"] = _parse_pages(md)
            out.append(StoredDocument(str(chunk_id), str(text or ""), md))
        return out
