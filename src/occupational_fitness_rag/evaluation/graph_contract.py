"""Standard-library contracts shared with isolated graph framework runtimes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request, build_opener


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def local_get(endpoint, route):
    if urlparse(endpoint).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Only loopback inference is allowed")
    with build_opener(ProxyHandler({})).open(Request(endpoint + route), timeout=30) as response:
        return json.load(response)


def verify_runtime(config):
    endpoint = config["endpoint"]
    version = local_get(endpoint, "/api/version")["version"]
    models = {m["name"]: m["digest"] for m in local_get(endpoint, "/api/tags")["models"]}
    if version != config["expected_runtime_version"]:
        raise ValueError("Graph worker runtime version drift")
    for key, pin in (("graph_model", "graph_model_digest"),
                     ("embedding_model", "embedding_model_digest")):
        if models.get(config[key]) != config[pin]:
            raise ValueError("Graph worker model weight drift: " + config[key])


def verify_request(request, method):
    expected = fingerprint({k: v for k, v in request.items() if k != "request_identity"})
    if request["request_identity"] != expected or request["method"] != method:
        raise ValueError("Graph request identity or method differs")
    corpus = json.loads(Path(request["corpus"]).read_bytes())
    if (file_hash(request["corpus"]) != request["corpus_file_sha256"]
            or corpus["corpus_sha256"] != request["corpus_sha256"]
            or fingerprint({k: v for k, v in corpus.items() if k != "corpus_sha256"})
            != corpus["corpus_sha256"]):
        raise ValueError("Graph corpus identity differs")
    queries = request["queries"]
    if not queries or len({q["query_id"] for q in queries}) != len(queries):
        raise ValueError("Empty or duplicate graph query inventory")
    by_id = {u["source_id"]: u for u in corpus["units"]}
    if len(by_id) != len(corpus["units"]):
        raise ValueError("Duplicate corpus source ID")
    for unit in by_id.values():
        if unit["licence_context"] not in {"commercial", "shared"}:
            raise ValueError("Private-only original entered a commercial index")
    for q in queries:
        if (q["corpus_sha256"] != corpus["corpus_sha256"]
                or q["licence_context"] != "commercial"
                or hashlib.sha256(q["query"].encode()).hexdigest()
                != q["query_audit"]["query_sha256"]
                or fingerprint({k: v for k, v in q.items() if k != "query_id"}) != q["query_id"]):
            raise ValueError("Frozen graph query differs")
    return corpus


def storage_files(work, method):
    """Index content only; explicitly exclude mutable query/LLM caches and logs."""
    work = Path(work)
    if method == "lightrag":
        directory = work / work.name
        files = [p for p in directory.glob("*") if p.is_file()
                 and p.name != "kv_store_llm_response_cache.json"
                 and (p.name.startswith(("kv_store_", "vdb_")) or p.suffix == ".graphml")]
    else:
        files = [p for name in ("output", "lancedb") for p in (work / name).rglob("*")
                 if p.is_file() and p.suffix not in {".log", ".lock"}]
        files += [work / "settings.json"] if (work / "settings.json").exists() else []
    return {p.relative_to(work).as_posix(): file_hash(p) for p in sorted(files)}


def verify_index(work, method, contract):
    work = Path(work)
    saved = json.loads((work / "index_manifest.json").read_bytes())
    if saved["contract"] != contract or saved["contract_sha256"] != fingerprint(contract):
        raise ValueError("Graph index corpus/model/settings/worker identity differs")
    if not saved["storage_sha256"] or storage_files(work, method) != saved["storage_sha256"]:
        raise ValueError("Frozen graph index storage changed")
    if file_hash(work / "source_mapping.json") != saved["source_mapping_sha256"]:
        raise ValueError("Frozen graph source mapping changed")
    if file_hash(work / "index_complete.json") != saved["completion_sha256"]:
        raise ValueError("Frozen graph completion record changed")
    return saved


def validate_records(rows, queries, method, units, experiment_identity):
    planned = {q["query_id"]: q for q in queries}
    seen = set()
    by_id = {u["source_id"]: u for u in units}
    for row in rows:
        key = row["query_id"]
        if key not in planned or key in seen:
            raise ValueError("Unknown or duplicate graph result")
        seen.add(key)
        q = planned[key]
        if any(row.get(k) != q[k] for k in ("case_id", "module", "query_id")):
            raise ValueError("Graph result query scope differs")
        if row["query_sha256"] != q["query_audit"]["query_sha256"]:
            raise ValueError("Graph result query hash differs")
        if row["method"] != method or row["experiment_identity"] != experiment_identity:
            raise ValueError("Graph result experiment identity differs")
        if row["status"] not in {"completed", "index_failed", "retrieval_failed", "worker_failed"}:
            raise ValueError("Unknown graph execution status")
        ids = row["source_ids"]
        if len(ids) > 10 or len(set(ids)) != len(ids):
            raise ValueError("Repeated or excessive graph originals")
        if row["status"] != "completed" and (ids or not row.get("error")):
            raise ValueError("A failed graph run must retain its error and no substitute sources")
        if any(sid not in by_id or by_id[sid]["module"] != q["module"] for sid in ids):
            raise ValueError("Graph result original is unmapped or outside its module")
    return seen
