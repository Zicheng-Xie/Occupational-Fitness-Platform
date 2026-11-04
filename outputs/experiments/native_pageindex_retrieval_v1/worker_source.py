"""Native PageIndex Markdown indexing with a bounded local navigation adapter.

PageIndex builds the actual hierarchical index. Query navigation is first-party
code, not the framework's full chat-agent retriever. Every result resolves to
the unchanged frozen original corpus, and no expected source labels are read.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request, build_opener

METHOD = "pageindex_tree_adapter"
MODEL_KEYS = {"model", "expected_model_digest", "expected_runtime_version", "endpoint"}


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def read_records(path):
    return (
        [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if path.exists()
        else []
    )


def settings(config):
    allowed = MODEL_KEYS | {
        "expected_pageindex_version",
        "context_length",
        "max_branches",
        "source_preview_characters",
        "candidate_max_bytes",
        "top_k",
        "timeout_seconds",
        "branch_output_tokens",
        "ranking_output_tokens",
    }
    if set(config) - allowed or not MODEL_KEYS <= set(config):
        raise ValueError("Unknown or missing local tree-navigation configuration")
    result = {
        "expected_pageindex_version": "0.4.5",
        "context_length": 8192,
        "max_branches": 3,
        "source_preview_characters": 240,
        "candidate_max_bytes": 20000,
        "top_k": 10,
        "timeout_seconds": 180,
        "branch_output_tokens": 512,
        "ranking_output_tokens": 1024,
        **config,
    }
    for name in (
        "context_length",
        "max_branches",
        "source_preview_characters",
        "candidate_max_bytes",
        "top_k",
        "timeout_seconds",
        "branch_output_tokens",
        "ranking_output_tokens",
    ):
        if type(result[name]) is not int or result[name] < 1:
            raise ValueError("Navigation budgets must be positive integers")
    endpoint = urlparse(result["endpoint"])
    if (
        endpoint.scheme != "http"
        or endpoint.hostname != "127.0.0.1"
        or endpoint.path not in {"", "/"}
    ):
        raise ValueError("The experimental model endpoint must be local IPv4 HTTP")
    if result["top_k"] != 10 or result["max_branches"] > 5 or result["context_length"] < 2048:
        raise ValueError("Unsupported bounded navigation policy")
    return result


def validate_inputs(corpus, queries):
    units = {}
    for unit in corpus["units"]:
        sid = unit.get("source_id")
        if (
            not isinstance(sid, str)
            or not sid
            or sid in units
            or unit.get("licence_context") not in {"commercial", "shared"}
        ):
            raise ValueError("Original sources must be unique commercial/shared units")
        text = unit.get("evidence_text")
        if (
            not isinstance(text, str)
            or not text.strip()
            or hashlib.sha256(text.encode()).hexdigest() != unit.get("text_sha256")
        ):
            raise ValueError("Original source text fingerprint differs")
        if not isinstance(unit.get("module"), str) or not unit["module"]:
            raise ValueError("Every original source requires a disease module")
        if type(unit.get("pdf_page")) is not int or unit["pdf_page"] < 1:
            raise ValueError("Every original source requires a PDF page")
        units[sid] = unit
    seen = set()
    for query in queries:
        if query["query_id"] in seen or query.get("licence_context") != "commercial":
            raise ValueError("Frozen queries are repeated or outside commercial scope")
        seen.add(query["query_id"])
        if not any(u["module"] == query["module"] for u in units.values()):
            raise ValueError("The frozen query has no original source scope")
        if not isinstance(query.get("query"), str) or not query["query"].strip():
            raise ValueError("A literal frozen query is required")
    return units


def markdown_document(module, units):
    """Use exact source text inside fences so PDF headings cannot change the tree."""
    selected = sorted(
        (u for u in units.values() if u["module"] == module),
        key=lambda u: (u["section"], u["pdf_page"], u["source_id"]),
    )
    lines, section, page = ["# " + module, ""], None, None
    for unit in selected:
        if unit["section"] != section:
            section, page = unit["section"], None
            lines.extend(["## Section " + str(section), ""])
        if unit["pdf_page"] != page:
            page = unit["pdf_page"]
            lines.extend(["### PDF " + str(page), ""])
        title = str(
            unit.get("table_row") or unit.get("criterion_type") or "Original guideline passage"
        )
        title = " ".join(title.split())
        if "```" in unit["evidence_text"] or "\n" in unit["source_id"] or "|" in unit["source_id"]:
            raise ValueError(
                "Original text or source identity collides with native index delimiters"
            )
        lines.extend(
            [
                "#### " + unit["source_id"] + " | " + title,
                "",
                "```text",
                unit["evidence_text"],
                "```",
                "",
            ]
        )
    if not selected:
        raise ValueError("Cannot build a native tree without scoped originals")
    return "\n".join(lines)


def map_native_tree(module, native, units):
    """Bind native PageIndex nodes to exact original source identities and text."""
    leaves, branches = {}, []
    seen_nodes = set()

    def walk(nodes, section=None, page=None):
        for node in nodes:
            nid, title = node.get("node_id"), node.get("title", "")
            if not isinstance(nid, str) or not nid or nid in seen_nodes:
                raise ValueError("Native tree requires unique nonempty node identities")
            seen_nodes.add(nid)
            local_section = str(title)[8:] if str(title).startswith("Section ") else section
            local_page = int(str(title)[4:]) if str(title).startswith("PDF ") else page
            if " | " in title:
                sid = title.split(" | ", 1)[0]
                if (
                    sid not in units
                    or units[sid]["module"] != module
                    or sid in {v["source_id"] for v in leaves.values()}
                ):
                    raise ValueError(
                        "Native tree contains an unknown, repeated or cross-module source"
                    )
                unit = units[sid]
                if unit["evidence_text"] not in node.get("text", ""):
                    raise ValueError("Native index did not retain the exact full original passage")
                if unit["pdf_page"] != local_page or str(unit["section"]) != str(local_section):
                    raise ValueError("Native tree page or section differs from source provenance")
                leaves[nid] = {
                    "source_id": sid,
                    "title": title,
                    "node_id": nid,
                    "section": local_section,
                    "pdf_page": local_page,
                }
            children = node.get("nodes", [])
            before = set(leaves)
            walk(children, local_section, local_page)
            if str(title).startswith("PDF "):
                ids = [key for key in leaves if key not in before]
                branches.append(
                    {
                        "node_id": nid,
                        "title": title,
                        "section": local_section,
                        "pdf_page": local_page,
                        "leaf_node_ids": ids,
                    }
                )

    walk(native["structure"])
    expected = {u["source_id"] for u in units.values() if u["module"] == module}
    if {v["source_id"] for v in leaves.values()} != expected or not branches:
        raise ValueError("Native index does not map every frozen original exactly once")
    return {"module": module, "leaves": leaves, "branches": branches}


async def build_index(output, units, config):
    """Call the installed native indexer; no model summaries or thinning run."""
    from pageindex.page_index_md import md_to_tree

    directory = output / "native_index"
    directory.mkdir(exist_ok=True)
    mappings = {}
    for module in sorted({u["module"] for u in units.values()}):
        path = directory / (module + ".md")
        raw = markdown_document(module, units)
        native_path = directory / (module + ".json")
        if native_path.exists():
            if path.read_text(encoding="utf-8") != raw:
                raise ValueError("The resumed native index Markdown differs")
            native = json.loads(native_path.read_bytes())
        else:
            path.write_text(raw, encoding="utf-8")
            native = await md_to_tree(
                str(path),
                if_thinning=False,
                if_add_node_summary="no",
                if_add_doc_description="no",
                if_add_node_text="yes",
                if_add_node_id="yes",
            )
            save(native_path, native)
        mappings[module] = map_native_tree(module, native, units)
    save(directory / "source_mapping.json", mappings)
    return mappings


def request_body(query, mapping, units, config, phase, selected=None):
    if phase == "branches":
        tree = []
        for branch in mapping["branches"]:
            leaves = []
            for nid in branch["leaf_node_ids"]:
                leaf = mapping["leaves"][nid]
                original = units[leaf["source_id"]]["evidence_text"]
                leaves.append(
                    {
                        "node_id": nid,
                        "title": leaf["title"],
                        "original_prefix": original[: config["source_preview_characters"]],
                        "prefix_is_complete": len(original) <= config["source_preview_characters"],
                    }
                )
            tree.append({**branch, "leaves": leaves})
        data = {
            "module": query["module"],
            "licence_context": "commercial",
            "query": query["query"],
            "native_tree": tree,
        }
        field, limit = "branch_ids", config["max_branches"]
        system = "Select the most relevant PDF branches in this native document tree for the frozen clinical query. Return ordered branch_ids only. Select branches needed for criteria, conditions and exceptions. Do not assess driving fitness. Use only supplied branch node IDs; no guessed IDs."
        allowed = {b["node_id"] for b in mapping["branches"]}
        excluded = []
    elif phase == "originals":
        by_branch = {b["node_id"]: b for b in mapping["branches"]}
        candidates, excluded, seen = [], [], set()
        for bid in selected:
            for nid in by_branch[bid]["leaf_node_ids"]:
                if nid in seen:
                    continue
                seen.add(nid)
                leaf = mapping["leaves"][nid]
                unit = units[leaf["source_id"]]
                source = {**leaf, "original_text": unit["evidence_text"]}
                if (
                    len(json.dumps([*candidates, source], ensure_ascii=False).encode())
                    > config["candidate_max_bytes"]
                ):
                    excluded.append(nid)
                else:
                    candidates.append(source)
        if not candidates:
            raise ValueError("No full original passage survives the fixed navigation budget")
        data = {
            "module": query["module"],
            "licence_context": "commercial",
            "query": query["query"],
            "originals": candidates,
        }
        field, limit = "node_ids", config["top_k"]
        allowed = {v["node_id"] for v in candidates}
        system = "Rank the supplied original guideline passages by relevance to the frozen clinical query. Return ordered node_ids only, up to ten. Include relevant criteria, qualifications and exceptions, distinguish commercial standards from general background. Do not assess driving fitness, infer facts or create source text. Use only supplied node IDs."
    else:
        raise ValueError("Unknown tree navigation phase")
    schema = {
        "type": "object",
        "properties": {
            field: {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": min(limit, len(allowed)),
            }
        },
        "required": [field],
        "additionalProperties": False,
    }
    body = {
        "model": config["model"],
        "stream": False,
        "think": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(data, ensure_ascii=False, allow_nan=False)},
        ],
        "format": schema,
        "options": {
            "temperature": 0,
            "seed": 0,
            "num_ctx": config["context_length"],
            "num_predict": config["branch_output_tokens"]
            if phase == "branches"
            else config["ranking_output_tokens"],
        },
    }
    return body, field, allowed, excluded


def parse_selection(raw, body, field, allowed, config):
    if raw.get("done") is not True or raw.get("done_reason") != "stop":
        raise ValueError("Local navigation completion is incomplete")
    count = raw.get("prompt_eval_count")
    if (
        type(count) is not int
        or not 0 < count <= config["context_length"] - body["options"]["num_predict"]
    ):
        raise ValueError("Navigation input exceeds the pinned context budget")
    value = json.loads(raw["message"]["content"])
    if not isinstance(value, dict) or set(value) != {field}:
        raise ValueError("Navigation output differs from the structured selection contract")
    ids = value[field]
    limit = body["format"]["properties"][field]["maxItems"]
    if (
        not isinstance(ids, list)
        or not ids
        or len(ids) > limit
        or any(not isinstance(nid, str) or nid not in allowed for nid in ids)
        or len(ids) != len(set(ids))
    ):
        raise ValueError("Navigation returned an unknown, repeated or excessive native node ID")
    return ids


def local_json(config, route, body=None):
    request = Request(
        config["endpoint"].rstrip("/") + route,
        data=json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
        if body is not None
        else None,
        headers={"Content-Type": "application/json"},
    )
    with build_opener(ProxyHandler({})).open(
        request, timeout=config["timeout_seconds"]
    ) as response:
        return json.load(response)


def runtime(config):
    version = local_json(config, "/api/version")
    models = local_json(config, "/api/tags")
    inventory = {m["name"]: m["digest"] for m in models["models"]}
    if (
        version.get("version") != config["expected_runtime_version"]
        or inventory.get(config["model"]) != config["expected_model_digest"]
    ):
        raise ValueError("The local model or runtime differs from the frozen contract")
    return {"version": version["version"], "model_digest": inventory[config["model"]]}


def call(query, body, field, allowed, config, phase, output):
    runtime(config)
    started = perf_counter()
    record = {
        "query_id": query["query_id"],
        "case_id": query["case_id"],
        "module": query["module"],
        "phase": phase,
        "utc": datetime.now(timezone.utc).isoformat(),
        "request": body,
        "request_sha256": digest(body),
        "provider_called": False,
    }
    try:
        record["provider_called"] = True
        raw = local_json(config, "/api/chat", body)
        record["raw_response"] = raw
        ids = parse_selection(raw, body, field, allowed, config)
        record.update(status="completed", selected_native_node_ids=ids)
        return ids
    except Exception as exc:
        record.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        record["seconds"] = perf_counter() - started
        with (output / "model_calls.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")


def audit_results(rows, queries, mappings, units, config, calls, identity):
    """Reconstruct successful selections from exact observed request/response pairs."""
    qmap = {q["query_id"]: q for q in queries}
    seen = set()
    for row in rows:
        qid = row["query_id"]
        if qid in seen or qid not in qmap or row["experiment_identity"] != identity:
            raise ValueError("Saved navigation condition is repeated or misidentified")
        seen.add(qid)
        query = qmap[qid]
        if (
            row["case_id"] != query["case_id"]
            or row["module"] != query["module"]
            or row["method"] != METHOD
        ):
            raise ValueError("Saved navigation condition differs from its frozen query")
        if row["status"] != "completed":
            if row["source_ids"]:
                raise ValueError("Failed navigation cannot contain fallback sources")
            continue
        mapping = mappings[query["module"]]
        selected = None
        for phase in ("branches", "originals"):
            body, field, allowed, excluded = request_body(
                query, mapping, units, config, phase, selected
            )
            matches = [
                c
                for c in calls
                if c["query_id"] == qid and c["phase"] == phase and c["status"] == "completed"
            ]
            if len(matches) != 1 or matches[0].get("provider_called") is not True:
                raise ValueError(
                    "A successful navigation phase lacks its actual recorded model call"
                )
            observed = matches[0]
            if observed["request"] != body or observed["request_sha256"] != digest(body):
                raise ValueError(
                    "Observed navigation request differs from its frozen query and evidence"
                )
            selected = parse_selection(observed["raw_response"], body, field, allowed, config)
            if observed["selected_native_node_ids"] != selected:
                raise ValueError("Saved navigation phase differs from its raw model output")
            if phase == "branches" and row["selected_branch_node_ids"] != selected:
                raise ValueError("Saved selected tree branches differ from the actual model output")
        ids = [mapping["leaves"][nid]["source_id"] for nid in selected]
        if (
            row["source_ids"] != ids
            or row["selected_leaf_node_ids"] != selected
            or row["excluded_native_nodes_by_navigation_budget"] != excluded
            or row["original_text_hashes"] != {s: units[s]["text_sha256"] for s in ids}
        ):
            raise ValueError(
                "Saved originals do not reconstruct from native nodes and observed responses"
            )


def run(request_path, resume=False, index_only=False):
    request = json.loads(Path(request_path).read_bytes())
    if set(request) != {"corpus", "queries", "output", "preparation_identity", "config"}:
        raise ValueError("Unexpected worker input keys; reference labels are not accepted")
    config = settings(request["config"])
    root = Path(__file__).resolve().parents[1]
    paths = {key: (root / request[key]).resolve() for key in ("corpus", "queries", "output")}
    output = paths["output"]
    if not output.is_relative_to(root / "outputs/experiments") or any(
        output == paths[k] for k in ("corpus", "queries")
    ):
        raise ValueError("Keep worker output in a separate experimental directory")
    corpus, queries = [json.loads(paths[k].read_bytes()) for k in ("corpus", "queries")]
    units = validate_inputs(corpus, queries)
    version = importlib.metadata.version("pageindex")
    if version != config["expected_pageindex_version"]:
        raise ValueError("Unexpected native PageIndex package version")
    package = Path(importlib.metadata.distribution("pageindex").locate_file("pageindex"))
    native_sources = {name: file_hash(package / name) for name in ("page_index_md.py", "utils.py")}
    data = {
        "kind": "native_pageindex_md_index_first_party_local_navigation",
        "method": METHOD,
        "config": config,
        "corpus_sha256": file_hash(paths["corpus"]),
        "queries_sha256": file_hash(paths["queries"]),
        "preparation_identity": request["preparation_identity"],
        "native_pageindex_version": version,
        "native_sources": native_sources,
        "worker_sha256": file_hash(__file__),
        "python": sys.version,
        "index_model_calls": 0,
        "native_chat_retrieval_used": False,
        "reference_labels_available": False,
    }
    manifest = {**data, "identity": digest(data), "production_change": False}
    if output.exists():
        if not resume or json.loads((output / "manifest.json").read_bytes()) != manifest:
            raise ValueError("Resume requires the exact frozen native index and adapter version")
        if (output / "artifacts.json").exists():
            for name, pin in json.loads((output / "artifacts.json").read_bytes()).items():
                if file_hash(output / name) != pin:
                    raise ValueError("Existing worker artifact changed: " + name)
    else:
        output.mkdir(parents=True)
        save(output / "manifest.json", manifest)
        save(output / "corpus.json", corpus)
        save(output / "queries.json", queries)
        (output / "worker_source.py").write_bytes(Path(__file__).read_bytes())
    lock = output / ".run.lock"
    with lock.open("x", encoding="ascii") as stream:
        stream.write(str(os.getpid()))
    try:
        start = perf_counter()
        mappings = asyncio.run(build_index(output, units, config))
        index_seconds = perf_counter() - start
        if not index_only:
            environment = runtime(config)
            rows = read_records(output / "results.jsonl")
            audit_results(
                rows,
                queries,
                mappings,
                units,
                config,
                read_records(output / "model_calls.jsonl"),
                manifest["identity"],
            )
            done = {r["query_id"] for r in rows}
            if (
                len(done) != len(rows)
                or not done <= {q["query_id"] for q in queries}
                or any(r["experiment_identity"] != manifest["identity"] for r in rows)
            ):
                raise ValueError("Repeated or mismatched navigation checkpoints")
            for query in queries:
                if query["query_id"] in done:
                    continue
                started = perf_counter()
                row = {k: query[k] for k in ("query_id", "case_id", "module")}
                row.update(method=METHOD, experiment_identity=manifest["identity"], source_ids=[])
                try:
                    mapping = mappings[query["module"]]
                    body, field, allowed, _ = request_body(
                        query, mapping, units, config, "branches"
                    )
                    branches = call(query, body, field, allowed, config, "branches", output)
                    body, field, allowed, excluded = request_body(
                        query, mapping, units, config, "originals", branches
                    )
                    leaves = call(query, body, field, allowed, config, "originals", output)
                    ids = [mapping["leaves"][nid]["source_id"] for nid in leaves]
                    row.update(
                        status="completed",
                        source_ids=ids,
                        selected_branch_node_ids=branches,
                        selected_leaf_node_ids=leaves,
                        original_text_hashes={s: units[s]["text_sha256"] for s in ids},
                        excluded_native_nodes_by_navigation_budget=excluded,
                        native_index_module=query["module"],
                    )
                except Exception as exc:
                    row.update(status="failed", error=f"{type(exc).__name__}: {exc}")
                row["retrieval_seconds"] = perf_counter() - started
                with (output / "results.jsonl").open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
                rows.append(row)
                print(
                    f"{METHOD} {len(rows)}/{len(queries)} {query['case_id']}/{query['module']} {row['status']}",
                    flush=True,
                )
            if runtime(config) != environment:
                raise ValueError("Local navigation environment changed during execution")
        else:
            rows = read_records(output / "results.jsonl")
        if file_hash(__file__) != data["worker_sha256"] or any(
            file_hash(package / name) != pin for name, pin in native_sources.items()
        ):
            raise ValueError("Native index or adapter source changed during execution")
        if any(file_hash(paths[name]) != data[name + "_sha256"] for name in ("corpus", "queries")):
            raise ValueError("Frozen original corpus or queries changed during navigation")
        calls = read_records(output / "model_calls.jsonl")
        audit_results(rows, queries, mappings, units, config, calls, manifest["identity"])
        summary = {
            "identity": manifest["identity"],
            "method": METHOD,
            "planned": len(queries),
            "recorded": len(rows),
            "completed": sum(r["status"] == "completed" for r in rows),
            "failed": sum(r["status"] != "completed" for r in rows),
            "native_indexed_units": sum(len(m["leaves"]) for m in mappings.values()),
            "native_module_indexes": len(mappings),
            "index_model_calls": 0,
            "actual_navigation_model_calls": len(calls),
            "index_seconds_this_invocation": index_seconds,
            "index_only": index_only,
            "native_chat_retrieval_used": False,
            "production_change": False,
        }
        save(output / "summary.json", summary)
        save(
            output / "artifacts.json",
            {
                str(p.relative_to(output)).replace("\\", "/"): file_hash(p)
                for p in output.rglob("*")
                if p.is_file() and p.name not in {"artifacts.json", ".run.lock"}
            },
        )
        return summary
    finally:
        lock.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--index-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.request, args.resume, args.index_only), indent=2))
