"""Isolated pinned graph retrieval worker; graph summaries are never evidence."""

from __future__ import annotations

import argparse
import asyncio
import importlib.metadata
import json
import os
import sys
from pathlib import Path
from time import perf_counter
from urllib.parse import urlparse

if __package__:
    from .graph_contract import (
        file_hash,
        fingerprint,
        storage_files,
        validate_records,
        verify_index,
        verify_request,
        verify_runtime,
    )
else:
    from graph_contract import (
        file_hash,
        fingerprint,
        storage_files,
        validate_records,
        verify_index,
        verify_request,
        verify_runtime,
    )

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
os.environ["DO_NOT_TRACK"] = "1"
os.environ["NO_PROXY"] = "127.0.0.1,localhost,::1"


def save(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def map_original_sources(rows, by_short, allowed, top_k):
    """Every returned short ID must resolve, including items below the Top-k cut."""
    ids = []
    for row in rows:
        key = str(row.get("id"))
        if key not in by_short or not by_short[key]:
            raise ValueError("GraphRAG returned an unknown text-unit short ID: " + key)
        for source_id in by_short[key]:
            if not isinstance(source_id, str) or source_id not in allowed:
                raise ValueError("GraphRAG returned an unmapped or out-of-module original document")
            if source_id not in ids:
                ids.append(source_id)
    return ids[:top_k]


async def light_engine(work, units, config):
    import numpy as np
    import ollama
    from lightrag import LightRAG
    from lightrag.base import DocStatus
    from lightrag.llm.ollama import ollama_model_complete
    from lightrag.utils import EmbeddingFunc

    async def embed(texts):
        client = ollama.AsyncClient(host=config["endpoint"], timeout=120, trust_env=False)
        result = await client.embed(model=config["embedding_model"], input=texts, truncate=False)
        return np.asarray(result.embeddings)

    reused_llm_cache = (work / work.name / "kv_store_llm_response_cache.json").exists()
    rag = LightRAG(
        working_dir=str(work),
        workspace=work.name,
        llm_model_func=ollama_model_complete,
        llm_model_name=config["graph_model"],
        llm_model_max_async=1,
        llm_model_kwargs={
            "host": config["endpoint"],
            "options": {
                "num_ctx": config["graph_context_length"],
                "num_predict": 2048,
                "temperature": 0,
                "seed": 0,
            },
            "think": False,
            "timeout": config.get("call_timeout_seconds", 240),
        },
        embedding_func=EmbeddingFunc(embedding_dim=768, max_token_size=8192, func=embed),
        embedding_func_max_async=1,
        max_parallel_insert=1,
        chunk_token_size=4096,
        chunk_overlap_token_size=0,
        entity_extract_max_gleaning=0,
        entity_extraction_use_json=True,
        addon_params={
            "language": "English",
            "entity_types": ["Condition", "Symptom", "Standard", "Treatment", "Assessment"],
        },
    )
    await rag.initialize_storages()
    if not (work / "index_complete.json").exists():
        prior_processed = await rag.doc_status.get_docs_by_statuses([DocStatus.PROCESSED])
        started = perf_counter()
        await rag.ainsert(
            [u["evidence_text"] for u in units],
            ids=[u["source_id"] for u in units],
            file_paths=[u["source_id"] for u in units],
        )
        statuses = await rag.doc_status.get_docs_by_statuses(
            [DocStatus.FAILED, DocStatus.PENDING, DocStatus.PROCESSING]
        )
        # Framework duplicate bookkeeping IDs are not source documents. Corpus
        # text is deduplicated before indexing; inspect every requested original.
        statuses = {
            sid: status
            for sid, status in statuses.items()
            if sid in {u["source_id"] for u in units}
        }
        if statuses:
            raise RuntimeError(f"LightRAG indexing failed for {len(statuses)} documents")
        processed = await rag.doc_status.get_docs_by_statuses([DocStatus.PROCESSED])
        if set(processed) - {u["source_id"] for u in units}:
            raise RuntimeError("LightRAG workspace contains documents outside its disease scope")
        missing = {u["source_id"] for u in units} - set(processed)
        if missing:
            raise RuntimeError(f"LightRAG did not index requested originals: {sorted(missing)}")
        save(
            work / "index_complete.json",
            {
                "seconds": perf_counter() - started,
                "documents": len(units),
                "package": importlib.metadata.version("lightrag-hku"),
                "reused_processed_documents": len(prior_processed),
                "llm_cache_reused": reused_llm_cache,
                "timing_scope": "incremental after cache reuse"
                if prior_processed or reused_llm_cache
                else "fresh construction",
            },
        )

    # Read persisted originals, not model-written graph descriptions. Every
    # requested document must survive ingestion with its exact source text.
    base = work / work.name
    originals = json.loads((base / "kv_store_full_docs.json").read_bytes())
    expected = {u["source_id"]: u["evidence_text"] for u in units}
    if set(originals) != set(expected) or any(
        row["content"] != expected[sid] for sid, row in originals.items()
    ):
        raise ValueError("LightRAG persisted originals differ from the frozen module")
    chunks = json.loads((base / "kv_store_text_chunks.json").read_bytes())
    mapping = {}
    for chunk_id, chunk in chunks.items():
        sid = chunk["full_doc_id"]
        if sid not in expected or chunk["file_path"] != sid or chunk["content"] not in expected[sid]:
            raise ValueError("LightRAG chunk is not mapped to an exact original")
        mapping[chunk_id] = {"source_ids": [sid], "text_sha256": fingerprint(chunk["content"])}
    if {sid for row in mapping.values() for sid in row["source_ids"]} != set(expected):
        raise ValueError("LightRAG omitted original-source mappings")
    save(work / "source_mapping.json", mapping)

    async def query(text, k):
        from lightrag import QueryParam

        data = await rag.aquery_data(
            text,
            param=QueryParam(
                mode="mix", top_k=20, chunk_top_k=k, enable_rerank=False, max_total_tokens=12000
            ),
        )
        if data.get("status") == "failure":
            raise RuntimeError(str(data.get("message")))
        chunks = data.get("data", {}).get("chunks", [])
        allowed = {u["source_id"] for u in units}
        ids = []
        for item in chunks:
            sid = item.get("file_path")
            if sid not in allowed:
                raise ValueError("LightRAG returned an unmapped source")
            if not item.get("content") or item["content"] not in expected[sid]:
                raise ValueError("LightRAG returned content outside its original document")
            if sid not in ids:
                ids.append(sid)
        return ids[:k], {"chunk_count": len(chunks), "metadata": data.get("metadata", {}),
                         "original_chunk_records": chunks}

    query.close = rag.finalize_storages
    return query


async def microsoft_engine(work, units, config):
    import pandas as pd
    from graphrag.api.index import build_index
    from graphrag.config.embeddings import entity_description_embedding
    from graphrag.config.models.graph_rag_config import GraphRagConfig
    from graphrag.query.factory import get_local_search_engine
    from graphrag.query.indexer_adapters import (
        read_indexer_entities,
        read_indexer_relationships,
        read_indexer_text_units,
    )
    from graphrag.utils.api import get_embedding_store

    model = {
        "model_provider": "ollama_chat",
        "model": config["graph_model"],
        "api_key": "local",
        "api_base": config["endpoint"],
        "call_args": {
            "temperature": 0,
            "seed": 0,
            "max_tokens": 2048,
            "num_ctx": config["graph_context_length"],
            "think": False,
        },
        "retry": {"type": "immediate", "max_retries": 2},
    }
    embed = {
        "model_provider": "openai",
        "model": config["embedding_model"],
        "api_key": "local",
        "api_base": config["endpoint"] + "/v1",
        "retry": {"type": "immediate", "max_retries": 2},
    }
    settings = GraphRagConfig.model_validate(
        {
            "completion_models": {"default_completion_model": model},
            "embedding_models": {"default_embedding_model": embed},
            "concurrent_requests": 1,
            "async_mode": "asyncio",
            "input_storage": {"type": "file", "base_dir": str(work / "input")},
            "output_storage": {"type": "file", "base_dir": str(work / "output")},
            "reporting": {"type": "file", "base_dir": str(work / "logs")},
            "cache": {"type": "json", "storage": {"type": "file", "base_dir": str(work / "cache")}},
            "chunking": {"size": 4096, "overlap": 0},
            "vector_store": {"type": "lancedb", "db_uri": str(work / "lancedb")},
            "extract_graph": {
                "entity_types": ["condition", "symptom", "standard", "treatment", "assessment"],
                "max_gleanings": 0,
            },
            "community_reports": {"max_length": 1500, "max_input_length": 12000},
            "workflows": [
                "load_input_documents",
                "create_base_text_units",
                "create_final_documents",
                "extract_graph",
                "finalize_graph",
                "extract_covariates",
                "create_communities",
                "create_final_text_units",
                "generate_text_embeddings",
            ],
            "embed_text": {"names": ["entity_description", "text_unit_text"]},
        }
    )
    for schema in settings.vector_store.index_schema.values():
        schema.vector_size = 768
    save(work / "settings.json", settings.model_dump(mode="json"))
    if not (work / "index_complete.json").exists():
        started = perf_counter()
        documents = pd.DataFrame(
            [
                {"id": u["source_id"], "title": u["source_id"], "text": u["evidence_text"]}
                for u in units
            ]
        )
        results = await build_index(settings, input_documents=documents)
        errors = [str(r.error) for r in results if r.error is not None]
        if errors:
            raise RuntimeError("GraphRAG index errors: " + "; ".join(errors))
        save(
            work / "index_complete.json",
            {
                "seconds": perf_counter() - started,
                "documents": len(units),
                "package": importlib.metadata.version("graphrag"),
            },
        )

    def read(name):
        return pd.read_parquet(work / "output" / (name + ".parquet"))

    entities, communities, texts, relationships = [
        read(n) for n in ["entities", "communities", "text_units", "relationships"]
    ]
    engine = get_local_search_engine(
        settings,
        reports=[],
        text_units=read_indexer_text_units(texts),
        entities=read_indexer_entities(entities, communities, 2),
        relationships=read_indexer_relationships(relationships),
        covariates={},
        response_type="Short",
        description_embedding_store=get_embedding_store(
            settings.vector_store, entity_description_embedding
        ),
    )
    allowed = {u["source_id"] for u in units}
    originals = {u["source_id"]: u["evidence_text"] for u in units}
    by_short, mapping = {}, {}
    for row in texts.itertuples():
        key, sid = str(row.human_readable_id), row.document_id
        if key in by_short or sid not in allowed or not row.text or row.text not in originals[sid]:
            raise ValueError("GraphRAG text-unit identity or original mapping differs")
        by_short[key] = [sid]
        mapping[key] = {"source_ids": [sid], "text_sha256": fingerprint(row.text), "text_unit_id": row.id}
    if {sid for values in by_short.values() for sid in values} != allowed:
        raise ValueError("GraphRAG omitted original-source mappings")
    save(work / "source_mapping.json", mapping)

    async def query(text, k):
        context = engine.context_builder.build_context(
            query=text,
            max_context_tokens=12000,
            text_unit_prop=0.8,
            community_prop=0.0,
            top_k_mapped_entities=10,
            top_k_relationships=10,
        )
        sources = context.context_records.get("sources")
        ids = map_original_sources(
            [] if sources is None else sources.to_dict("records"), by_short, allowed, k
        )
        return ids, {"text_units": 0 if sources is None else len(sources),
                     "original_short_ids": [] if sources is None else sources["id"].astype(str).tolist()}

    return query


async def run(args):
    request = json.loads(Path(args.request).read_text(encoding="utf-8"))
    config = request["config"]
    if urlparse(config["endpoint"]).hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Only loopback inference is allowed")
    strict = "request_identity" in request
    corpus = verify_request(request, args.method) if strict else json.loads(
        Path(request["corpus"]).read_text(encoding="utf-8")
    )
    if strict:
        verify_runtime(config)
        if urlparse(config["audit_endpoint"]).hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Only a loopback audit endpoint is allowed")
        cache = Path(config["tokenizer_cache"]).resolve()
        for name, expected in config["tokenizer_sha256"].items():
            if file_hash(cache / name) != expected:
                raise ValueError("Tokenizer vocabulary differs from its official hash")
        os.environ["TIKTOKEN_CACHE_DIR"] = str(cache)
        if request["worker_sha256"] != file_hash(__file__) or request["contract_sha256"] != file_hash(
            Path(__file__).with_name("graph_contract.py")
        ):
            raise ValueError("Frozen graph worker source changed")
        config = {**config, "endpoint": config["audit_endpoint"]}
    work = Path(request["workspace"]).resolve()
    work.mkdir(parents=True, exist_ok=True)
    output = Path(args.response)
    rows = json.loads(output.read_bytes()) if strict and output.exists() else []
    if strict:
        done = validate_records(rows, request["queries"], args.method, corpus["units"], request["experiment_identity"])
    else:
        done = set()

    def record(q, **values):
        extra = {} if not strict else {
            "method": args.method, "experiment_identity": request["experiment_identity"],
            "query_sha256": q["query_audit"]["query_sha256"],
        }
        return dict(q, **extra, **values)

    for module in sorted({q["module"] for q in request["queries"]}):
        directory = work / module
        directory.mkdir(exist_ok=True)
        units = [u for u in corpus["units"] if u["module"] == module]
        queries = [q for q in request["queries"] if q["module"] == module and q["query_id"] not in done]
        if not queries:
            continue
        contract = request.get("index_contracts", {}).get(module)
        engine = None
        try:
            save(work / "phase.json", {"stage": "index", "method": args.method, "module": module})
            if strict:
                if not contract:
                    raise ValueError("Missing module index contract")
                if (directory / "index_manifest.json").exists():
                    verify_index(directory, args.method, contract)
                else:
                    intent = directory / "index_intent.json"
                    if intent.exists():
                        if json.loads(intent.read_bytes()) != contract:
                            raise ValueError("Partial graph index belongs to different inputs")
                    elif any(directory.iterdir()):
                        raise ValueError("Unowned graph index or legacy completion sentinel")
                    else:
                        save(intent, contract)
            build = light_engine if args.method == "lightrag" else microsoft_engine
            engine = await build(directory, units, config)
            index = json.loads((directory / "index_complete.json").read_text())
            if strict:
                verify_runtime(request["config"])
                if (directory / "index_manifest.json").exists():
                    index = verify_index(directory, args.method, contract)
                else:
                    index = {
                        "contract": contract, "contract_sha256": fingerprint(contract),
                        "storage_sha256": storage_files(directory, args.method),
                        "source_mapping_sha256": file_hash(directory / "source_mapping.json"),
                        "completion_sha256": file_hash(directory / "index_complete.json"),
                        "construction": index,
                    }
                    if not index["storage_sha256"]:
                        raise ValueError("Empty graph index storage cannot be frozen")
                    save(directory / "index_manifest.json", index)
                    verify_index(directory, args.method, contract)
        except Exception as exc:
            rows.extend(
                record(q, status="index_failed", error=f"{type(exc).__name__}: {exc}", source_ids=[])
                for q in queries
            )
            save(output, rows)
            continue
        for q in queries:
            started = perf_counter()
            try:
                save(work / "phase.json", {"stage": "retrieval", "method": args.method,
                                          "module": module, "query_id": q["query_id"]})
                if strict:
                    verify_runtime(request["config"])
                    verify_index(directory, args.method, contract)
                ids, audit = await engine(q["query"], request["top_k"])
                if strict:
                    verify_index(directory, args.method, contract)
                rows.append(
                    record(
                        q,
                        status="completed",
                        source_ids=ids,
                        retrieval_audit=audit,
                        retrieval_seconds=perf_counter() - started,
                        **({"index_identity": index["contract_sha256"]} if strict else {"index": index}),
                    )
                )
            except Exception as exc:
                rows.append(
                    record(
                        q,
                        status="retrieval_failed",
                        source_ids=[],
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
            save(output, rows)
            print(f"{args.method}/{module}: {len(rows)}/{len(request['queries'])} recorded", flush=True)
        if engine is not None and hasattr(engine, "close"):
            await engine.close()
        if strict:
            verify_index(directory, args.method, contract)
    if strict:
        if validate_records(rows, request["queries"], args.method, corpus["units"], request["experiment_identity"]) != {
            q["query_id"] for q in request["queries"]
        }:
            raise ValueError("Incomplete graph query inventory")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", choices=["lightrag", "graphrag"], required=True)
    parser.add_argument("--request", required=True)
    parser.add_argument("--response", required=True)
    asyncio.run(run(parser.parse_args()))
