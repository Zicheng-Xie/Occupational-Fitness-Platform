"""Execute the first four retrievers on one frozen query/corpus preparation.

External graph frameworks remain pending; no substitute is counted for either.
Judgments and clinical labels are not used to rank sources.
"""

import argparse
import json
import math
import os
from collections import Counter
from datetime import datetime, timezone
from html import escape
from itertools import product
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

import yaml

from occupational_fitness_rag.evaluation.comparison_corpus import verify_corpus
from occupational_fitness_rag.evaluation.judgment_comparison import local_post
from occupational_fitness_rag.evaluation.passage_comparison import (
    HybridRetriever,
    pinned_environment,
    read_records,
    source_snapshot,
)
from occupational_fitness_rag.indexing.base import StoredDocument
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json
from occupational_fitness_rag.retrieval.bm25 import rank_bm25
from occupational_fitness_rag.retrieval.fusion import reciprocal_rank_fusion
from occupational_fitness_rag.retrieval.graph_local import expand_local_graph
from occupational_fitness_rag.rules.engine import RuleBook

METHODS = ("vector", "bm25", "hybrid", "graph_local")
PENDING = ("lightrag", "graphrag")


def rank_method(query, module, method, docs, vectors, query_vector, units, book, top_k):
    if method not in METHODS:
        raise ValueError("No substitute is implemented for an external graph framework")
    candidates = [doc for doc in docs if doc.metadata["module"] == module]
    sparse = rank_bm25(query, candidates, 30)
    if method == "bm25":
        return [{"source_id": doc.chunk_id, "bm25_score": score} for doc, score in sparse[:top_k]]
    if query_vector is None:
        raise ValueError("The shared query embedding failed; no lexical fallback is permitted")
    qnorm = math.sqrt(sum(v * v for v in query_vector))
    dense = []
    for doc, vector in zip(docs, vectors, strict=True):
        if doc.metadata["module"] != module:
            continue
        if len(vector) != len(query_vector):
            raise ValueError("Dense vector dimensions differ")
        norm = math.sqrt(sum(v * v for v in vector))
        if not norm or not qnorm:
            raise ValueError("Dense vectors must be nonzero")
        score = sum(a * b for a, b in zip(query_vector, vector, strict=True)) / (qnorm * norm)
        dense.append(StoredDocument(doc.chunk_id, doc.text, doc.metadata, score))
    dense.sort(key=lambda doc: (-doc.vector_score, doc.chunk_id))
    if method == "vector":
        return [{"source_id": doc.chunk_id, "vector_score": doc.vector_score} for doc in dense[:top_k]]
    fused = reciprocal_rank_fusion(dense[:20], sparse, 60)
    if method == "graph_local":
        fused = expand_local_graph(fused, candidates, book, SimpleNamespace(units=units), module, query, top_k)
    return [{"source_id": hit.doc.chunk_id, "score": hit.score,
             "vector_score": hit.vector_score, "bm25_score": hit.bm25_score,
             "graph_paths": hit.graph_paths} for hit in fused[:top_k]]


def render(output, rows, queries, corpus, references, manifest):
    units = {unit["source_id"]: unit for unit in corpus["units"]}
    qmap = {q["query_id"]: q for q in queries}
    scored, metrics = [], []
    for row in rows:
        required = {source["source_id"] for source in references[row["case_id"]]["reference_payload"]["guideline_evidence"] if source["module"] == row["module"]}
        result = {"method": row["method"], "query_id": row["query_id"], "reference_sources": sorted(required)}
        for k in (5, 10):
            returned = row.get("source_ids", [])[:k]
            covered = {sid for source in returned for sid in [source, *units[source].get("covers_source_ids", [])]}
            result[f"exact_recall_{k}"] = len(required & set(returned)) / len(required) if required else None
            result[f"coverage_recall_{k}"] = len(required & covered) / len(required) if required else None
        scored.append(result)
    for method in METHODS:
        group = [r for r in rows if r["method"] == method]
        labels = [r for r in scored if r["method"] == method and r["exact_recall_5"] is not None]
        metrics.append({
            "method": method, "records": len(group), "completed": sum(r["status"] == "completed" for r in group),
            "labeled_scopes": len(labels),
            **{field: sum(r[field] for r in labels) / len(labels) if labels else None
               for field in ("exact_recall_5", "exact_recall_10", "coverage_recall_5", "coverage_recall_10")},
            "fully_covered_5": sum(r["coverage_recall_5"] == 1 for r in labels),
        })
    summary = {
        "recorded": len(rows), "planned_executed_methods": len(manifest["planned_keys"]),
        "execution_complete": len(rows) == len(manifest["planned_keys"]),
        "distinct_cases": len({q["case_id"] for q in queries}), "module_queries": len(queries),
        "executed_methods": list(METHODS), "pending_methods": list(PENDING),
        "full_six_method_comparison_complete": False, "metrics": metrics,
        "failures": dict(Counter(r["error"] for r in rows if r["status"] == "failed")),
        "interpretation": "Engineering source-reference recall, not judgment accuracy or clinical accuracy. Reference lists are opened only after ranking. Unlabeled source candidates are not automatically irrelevant. Shared embedding calls are recorded once; rank timings exclude those shared costs and are not isolated latency benchmarks.",
        "judgment_calls": 0, "production_change": False,
    }
    write_json(output / "summary.json", summary)
    write_json(output / "retrieval_metrics.json", scored)
    headers = list(metrics[0])
    table = ''.join('<tr>' + ''.join('<td>' + escape(str(item[key])) + '</td>' for key in headers) + '</tr>' for item in metrics)
    cards = ''
    for row in rows:
        q = qmap[row["query_id"]]
        evidence = ''.join('<details><summary>' + escape(source) + ' · PDF ' + str(units[source]["pdf_page"]) + '</summary><pre>'
            + escape(units[source]["evidence_text"]) + '</pre></details>' for source in row.get("source_ids", [])[:5])
        cards += ('<article data-case="' + escape(row["case_id"]) + '" data-method="' + row["method"] + '"><h3>'
            + escape(row["case_id"] + ' / ' + row["module"] + ' / ' + row["method"]) + '</h3><details><summary>Frozen shared query</summary><pre>'
            + escape(q["query"]) + '</pre></details><p>' + escape(row.get("error", row["status"])) + '</p>' + evidence + '</article>')
    controls = ''.join('<label>' + label + '<select data-field="' + field + '"><option value="">All</option>'
        + ''.join('<option>' + escape(value) + '</option>' for value in values) + '</select></label>'
        for label, field, values in [("Case", "case", sorted({q["case_id"] for q in queries})), ("Method", "method", METHODS)])
    html = ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Shared-query retrieval comparison</title><style>body{font:14px/1.6 system-ui;color:#243748;background:#f5f7f9;'
        'max-width:1350px;margin:36px auto;padding:24px}table{width:100%;border-collapse:collapse}td,th{padding:10px;text-align:left;'
        'border-bottom:1px solid #dce3ea}article{background:white;border:1px solid #dce3ea;margin:14px 0;padding:20px;border-radius:8px}'
        'pre{white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer;padding:8px}label{display:inline-block;margin:12px}'
        'select{padding:8px;margin-left:8px}[hidden]{display:none}</style><small>OCCUPATIONAL FITNESS PLATFORM</small>'
        '<h1>Shared-query retrieval comparison: four executed methods</h1><p>LightRAG mix and Microsoft GraphRAG Local Search '
        'remain pending. They are not replaced by local graph-assisted retrieval.</p><p>' + escape(summary["interpretation"])
        + '</p><p>' + str(len(rows)) + '/' + str(len(manifest["planned_keys"])) + ' executed-method records; no new judgment calls.</p>'
        '<table><tr>' + ''.join('<th>' + escape(key) + '</th>' for key in headers) + '</tr>' + table + '</table>'
        + controls + cards + '<p><a href="results.jsonl">Raw rankings</a> · <a href="summary.json">Metrics</a> · '
        '<a href="manifest.json">Frozen configuration</a> · <a href="corpus.json">Original source text and geometry</a> · '
        '<a href="embedding_calls.jsonl">Actual embedding calls</a></p><script>document.querySelectorAll("select").forEach(s=>s.onchange=()=>'
        '{const a=[...document.querySelectorAll("select")];document.querySelectorAll("article[data-case]").forEach(d=>d.hidden='
        'a.some(x=>x.value&&d.dataset[x.dataset.field]!==x.value))});</script></html>')
    (output / "index.html").write_text(html, encoding="utf-8")
    return summary


def run(config_path, resume=False):
    text = Path(config_path).read_text(encoding="utf-8")
    config = yaml.safe_load(text)
    prep = Path(config["preparation_dir"]).resolve()
    pins = json.loads((prep / "artifacts.json").read_bytes())
    if pins["identity"] != config["expected_preparation_identity"]:
        raise ValueError("Unexpected shared-query preparation")
    for name, pin in pins["artifacts"].items():
        if sha256_bytes((prep / name).read_bytes()) != pin:
            raise ValueError("Prepared artifact changed: " + name)
    queries = json.loads((prep / "queries.json").read_bytes())
    corpus = json.loads((prep / "corpus.json").read_bytes())
    prep_manifest = json.loads((prep / "manifest.json").read_bytes())
    if digest({key: value for key, value in prep_manifest.items() if key != "identity"}) != pins["identity"]:
        raise ValueError("Prepared manifest self-identity differs")
    if digest(queries) != prep_manifest["queries_sha256"]:
        raise ValueError("Shared query content differs")
    root = Path(__file__).resolve().parents[1]
    verify_corpus(root, corpus)
    units = {unit["source_id"]: unit for unit in corpus["units"]}
    planned = [(q["query_id"], method) for q, method in product(queries, METHODS)]
    if len(planned) != len(set(planned)):
        raise ValueError("Duplicate query/method plan")
    reference_path = Path(config["reference_inputs"])
    reference_pin = sha256_bytes(reference_path.read_bytes())
    book = RuleBook(config["rules"])
    identity_data = {"config": config, "preparation_artifacts": pins,
        "source_snapshot": source_snapshot(text), "tool_source": Path(__file__).read_text(encoding="utf-8"),
        "environment": pinned_environment(config), "rules_sha256": book.sha256,
        "reference_inputs_sha256": reference_pin, "planned_keys": planned}
    manifest = {**identity_data, "identity": digest(identity_data), "production_change": False}
    output = Path(config["output"]).resolve()
    if output == prep or output.is_relative_to(prep) or prep.is_relative_to(output):
        raise ValueError("Retrieval output must be separate from query preparation")
    output.mkdir(parents=True, exist_ok=True)
    lock = output / ".run.lock"
    with lock.open("x", encoding="ascii") as stream:
        stream.write(str(os.getpid()))
    try:
        target = output / "manifest.json"
        if target.exists():
            if not resume or json.loads(target.read_bytes()) != json.loads(json.dumps(manifest)):
                raise ValueError("Resume requires identical frozen retrieval inputs and environment")
        else:
            if any(path.name != ".run.lock" for path in output.iterdir()):
                raise ValueError("Non-empty retrieval output lacks a manifest")
            write_json(target, manifest)
            write_json(output / "corpus.json", corpus)
            write_json(output / "queries.json", queries)
        rows = read_records(output / "results.jsonl")
        done = {(r["query_id"], r["method"]) for r in rows}
        if len(rows) != len(done) or not done <= set(planned) or any(r["experiment_identity"] != manifest["identity"] for r in rows):
            raise ValueError("Unexpected or repeated saved ranking identity")

        def observed_post(endpoint, route, body, timeout):
            pinned_environment(config)
            record = {"route": route, "request": body, "request_sha256": digest(body)}
            started = perf_counter()
            try:
                response = local_post(endpoint, route, body, timeout)
                record.update(status="completed", raw_response=response)
                return response
            except Exception as exc:
                record.update(status="failed", error=f"{type(exc).__name__}: {exc}")
                raise
            finally:
                record["seconds"] = perf_counter() - started
                with (output / "embedding_calls.jsonl").open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(record, allow_nan=False) + "\n")

        helper = HybridRetriever(corpus, config, output, manifest["identity"], post=observed_post)
        helper.ensure_vectors()
        docs = [StoredDocument(d.chunk_id, d.text, {**d.metadata, "source_ids_csv": d.chunk_id}) for d in helper.docs]
        for query in queries:
            if all((query["query_id"], method) in done for method in METHODS):
                continue
            qpath = output / "query_embeddings" / (query["query_id"] + ".json")
            if qpath.exists():
                cache = json.loads(qpath.read_bytes())
                if cache["identity"] != manifest["identity"] or cache["query_sha256"] != query["query_audit"]["query_sha256"]:
                    raise ValueError("Shared query-vector cache identity differs")
                if cache["status"] == "completed":
                    helper.validate_vectors([cache["vector"]], 1)
                    if digest(cache["vector"]) != cache["vector_sha256"]:
                        raise ValueError("Shared query vector changed")
            else:
                cache = {"identity": manifest["identity"], "query_sha256": query["query_audit"]["query_sha256"]}
                try:
                    vector, _ = helper.embed([query["query"]])
                    cache.update(status="completed", vector=vector[0], vector_sha256=digest(vector[0]))
                except Exception as exc:
                    cache.update(status="failed", error=f"{type(exc).__name__}: {exc}")
                write_json(qpath, cache)
            for method in METHODS:
                if (query["query_id"], method) in done:
                    continue
                row = {"query_id": query["query_id"], "case_id": query["case_id"], "module": query["module"],
                       "query_sha256": query["query_audit"]["query_sha256"], "method": method,
                       "experiment_identity": manifest["identity"], "query_embedding_status": cache["status"]}
                started = perf_counter()
                try:
                    ranked = rank_method(query["query"], query["module"], method, docs, helper.vectors,
                                         cache.get("vector"), units, book, config["sensitivity_k"])
                    ids = [hit["source_id"] for hit in ranked]
                    if len(ids) != len(set(ids)) or any(units[sid]["module"] != query["module"] for sid in ids):
                        raise ValueError("Ranked source crossed its module or repeated an ID")
                    row.update(status="completed", source_ids=ids, ranked_sources=ranked)
                except Exception as exc:
                    row.update(status="failed", source_ids=[], ranked_sources=[], error=f"{type(exc).__name__}: {exc}")
                row["ranking_seconds_excluding_shared_embeddings"] = perf_counter() - started
                with (output / "results.jsonl").open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
                rows.append(row)
                done.add((query["query_id"], method))
            print(f"Recorded {len(rows)}/{len(planned)} ranking records", flush=True)
        if done != set(planned) or source_snapshot(text) != manifest["source_snapshot"] or pinned_environment(config) != manifest["environment"]:
            raise ValueError("Incomplete retrieval or source/runtime drift")
        if Path(__file__).read_text(encoding="utf-8") != manifest["tool_source"] or RuleBook(config["rules"]).sha256 != book.sha256:
            raise ValueError("Retrieval tool or knowledge graph rules changed during execution")
        if json.loads((output / "corpus.json").read_bytes()) != corpus or json.loads((output / "queries.json").read_bytes()) != queries:
            raise ValueError("Saved report inputs differ from the frozen preparation")
        for name, pin in pins["artifacts"].items():
            if sha256_bytes((prep / name).read_bytes()) != pin:
                raise ValueError("Prepared input changed during retrieval")
        qmap = {query["query_id"]: query for query in queries}
        for row in rows:
            query = qmap[row["query_id"]]
            if row["case_id"] != query["case_id"] or row["module"] != query["module"] or row["query_sha256"] != query["query_audit"]["query_sha256"]:
                raise ValueError("A saved ranking changed its case, scope or query")
            cache = json.loads((output / "query_embeddings" / (query["query_id"] + ".json")).read_bytes())
            try:
                expected = rank_method(query["query"], query["module"], row["method"], docs,
                                       helper.vectors, cache.get("vector"), units, book, config["sensitivity_k"])
            except Exception as exc:
                if row["status"] != "failed" or row["error"] != f"{type(exc).__name__}: {exc}":
                    raise ValueError("Saved ranking failure differs from frozen inputs") from exc
            else:
                if row["status"] != "completed" or row["ranked_sources"] != expected or row["source_ids"] != [hit["source_id"] for hit in expected]:
                    raise ValueError("Saved ranking differs from deterministic reconstruction")
        # Reference answers become accessible only after every ranking is fixed.
        if sha256_bytes(reference_path.read_bytes()) != reference_pin:
            raise ValueError("Reference input bytes changed")
        references = json.loads(reference_path.read_bytes())
        summary = render(output, rows, queries, corpus, references, manifest)
        calls = read_records(output / "embedding_calls.jsonl")
        write_json(output / "execution_audit.json", {
            "utc": datetime.now(timezone.utc).isoformat(), "planned_keys_complete": True,
            "records": len(rows), "reference_loaded_after_ranking": True,
            "embedding_calls": len(calls), "embedding_failures": sum(r["status"] == "failed" for r in calls),
            "results_sha256": sha256_bytes((output / "results.jsonl").read_bytes()),
            "manifest_sha256": sha256_bytes((output / "manifest.json").read_bytes()),
            "embedding_calls_sha256": sha256_bytes((output / "embedding_calls.jsonl").read_bytes()),
            "judgment_calls": 0, "pending_methods": list(PENDING), "production_change": False,
        })
        return summary
    finally:
        lock.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.config, args.resume), indent=2))
