"""Native Neo4j hybrid retrieval over traceable original-source clause anchors.

This standalone worker runs in the isolated retrieval environment. It uses the
installed neo4j-graphrag HybridCypherRetriever, existing real vectors and native
Neo4j indexes. Regex anchors are navigation metadata pending clinical review;
they never replace source text or establish patient applicability.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from time import perf_counter
from urllib.parse import urlsplit

MODULES = {"hypertension", "vision", "hearing", "blackout", "diabetes"}
ANCHOR = re.compile(
    r"\b(if|when|where|following|provided|unless|except|however|subject\s+to|other\s+than)\b", re.I
)
EXCEPTION = re.compile(r"\b(unless|except|however|subject\s+to|other\s+than)\b", re.I)
POLICY = "native_hybrid_cypher_literal_clause_anchors_v1"


def digest(value):
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def text_sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def lexical_query(text):
    """Backend lexical tokenization; retain the unmodified frozen query too."""
    tokens = re.findall(r"[A-Za-z0-9]+", text.lower())
    if not tokens:
        raise ValueError("No lexical terms in frozen query")
    return " ".join(tokens)


def vector(value, dimensions):
    if (
        not isinstance(value, list)
        or len(value) != dimensions
        or any(
            isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)
            for x in value
        )
        or not any(value)
    ):
        raise ValueError("Invalid retained real embedding")
    return value


def validate_input(request):
    identity = request["experiment_identity"]
    if not re.fullmatch(r"[0-9a-f]{64}", identity):
        raise ValueError("A SHA-256 experiment identity is required")
    units, queries = request["corpus"]["units"], request["queries"]
    config = request.get("config", {})
    dimensions = config.get("embedding_dimensions", 768)
    if type(dimensions) is not int or dimensions <= 0:
        raise ValueError("Invalid embedding dimensions")
    if len(units) != len(request["corpus_vectors"]) or not units or not queries:
        raise ValueError("Source and vector inventories differ or are empty")
    inventory = {}
    for unit, values in zip(units, request["corpus_vectors"], strict=True):
        sid = unit["source_id"]
        if (
            sid in inventory
            or unit["module"] not in MODULES
            or unit["licence_context"] not in {"commercial", "shared"}
        ):
            raise ValueError("Repeated, private-only or out-of-module source")
        if not unit["evidence_text"] or text_sha(unit["evidence_text"]) != unit["text_sha256"]:
            raise ValueError("Original source text fingerprint differs")
        vector(values, dimensions)
        inventory[sid] = unit
    seen = set()
    for query in queries:
        qid = query["query_id"]
        if (
            qid in seen
            or query["module"] not in MODULES
            or query.get("licence_context") != "commercial"
        ):
            raise ValueError("Repeated or out-of-scope query")
        if not isinstance(query["query"], str) or not query["query"].strip():
            raise ValueError("A frozen original query is required")
        vector(request["query_vectors"][qid], dimensions)
        lexical_query(query["query"])
        seen.add(qid)
    if set(request["query_vectors"]) != seen:
        raise ValueError("Query vector inventory differs")
    return inventory, dimensions


def source_relations(units):
    """Build only explicit references, verified containment and literal anchors."""
    inventory = {u["source_id"]: u for u in units}
    edges, anchors = [], []
    for unit in units:
        sid, module, text = unit["source_id"], unit["module"], unit["evidence_text"]
        offset = 0
        for line_no, line in enumerate(text.splitlines(keepends=True), 1):
            literal = line.rstrip("\r\n")
            if ANCHOR.search(literal):
                kind = "exception" if EXCEPTION.search(literal) else "condition"
                key = digest(
                    {"module": module, "kind": kind, "literal": " ".join(literal.lower().split())}
                )
                anchors.append(
                    {
                        "source_id": sid,
                        "module": module,
                        "kind": kind,
                        "anchor_id": key,
                        "text": literal,
                        "char_start": offset,
                        "char_end": offset + len(literal),
                        "line_start": line_no,
                        "line_end": line_no,
                        "review_status": "engineering_anchor_pending_clinical_review",
                    }
                )
            offset += len(line)
        for key, relationship in (
            ("cross_references", "EXPLICIT_SECTION_REFERENCE"),
            ("covers_source_ids", "CONTAINS_ORIGINAL"),
        ):
            for target in unit.get(key, []):
                if target == sid or target not in inventory:
                    continue
                other = inventory[target]
                if other["module"] != module or other["licence_context"] not in {
                    "commercial",
                    "shared",
                }:
                    continue
                if relationship == "EXPLICIT_SECTION_REFERENCE":
                    sections = [
                        section
                        for section in unit.get("explicit_section_references", [])
                        if re.search(r"(?<![\d.])" + re.escape(section) + r"(?!\d|\.\d)", text)
                        and (
                            other["section"] == section
                            or other["section"].startswith(section + ".")
                        )
                    ]
                    if not sections:
                        # Curated related-source metadata is retained by the
                        # input corpus, but is not a literal explicit edge.
                        continue
                if relationship == "CONTAINS_ORIGINAL" and (
                    other["pdf_page"] != unit["pdf_page"]
                    or " ".join(other["evidence_text"].split()) not in " ".join(text.split())
                ):
                    raise ValueError(
                        "Corpus containment is not supported by complete original text"
                    )
                edges.append({"source_id": sid, "target_id": target, "relationship": relationship})
    return anchors, list({digest(e): e for e in edges}.values())


RETRIEVAL_QUERY = """
WITH node, score
CALL (node) {
    RETURN node AS candidate, 1.0 AS multiplier, 'native_hybrid_seed' AS graph_path
    UNION
    MATCH (node)-[:CONTAINS_ORIGINAL]-(candidate:OFPOriginalSource)
    RETURN candidate, 0.95 AS multiplier, 'literal_source_containment' AS graph_path
    UNION
    MATCH (node)-[:EXPLICIT_SECTION_REFERENCE]-(candidate:OFPOriginalSource)
    RETURN candidate, 0.85 AS multiplier, 'literal_explicit_section_reference' AS graph_path
    UNION
    MATCH (node)-[:HAS_CLAUSE]->(:OFPClause)-[:HAS_CONDITION|HAS_EXCEPTION]->(a:OFPAnchor)
          <-[:HAS_CONDITION|HAS_EXCEPTION]-(:OFPClause)<-[:HAS_CLAUSE]-(candidate:OFPOriginalSource)
    WHERE candidate <> node
    RETURN candidate, 0.80 AS multiplier, 'shared_literal_clause_anchor' AS graph_path
}
WITH DISTINCT node, score, candidate, multiplier, graph_path
WHERE candidate.experiment_id = $experiment_identity AND candidate.module = $module
  AND candidate.licence_context IN ['commercial', 'shared']
WITH node, score, candidate, multiplier, graph_path
ORDER BY multiplier DESC, candidate.source_id, graph_path
WITH node, score, collect({source_id:candidate.source_id, text_sha256:candidate.text_sha256,
                          multiplier:multiplier, graph_path:graph_path})[0..5] AS paths
UNWIND paths AS item
RETURN item.source_id AS source_id, item.text_sha256 AS text_sha256,
       score * item.multiplier AS score, score AS seed_score,
       node.source_id AS seed_source_id, item.graph_path AS graph_path
"""


def graph_namespace(identity, module):
    if not re.fullmatch(r"[0-9a-f]{64}", identity) or module not in MODULES:
        raise ValueError("Unsafe graph namespace")
    stem = "ofp_" + identity + "_" + module
    return stem, "OFPSource_" + identity + "_" + module


def aggregate(records, units, module, limit=10):
    scores, paths = {}, defaultdict(list)
    for record in records:
        sid, seed = record["source_id"], record["seed_source_id"]
        if (
            sid not in units
            or seed not in units
            or any(
                units[s]["module"] != module
                or units[s]["licence_context"] not in {"commercial", "shared"}
                for s in (sid, seed)
            )
            or record["text_sha256"] != units[sid]["text_sha256"]
        ):
            raise ValueError("Native graph returned an unmapped or out-of-scope original")
        score = record["score"]
        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not math.isfinite(score)
        ):
            raise ValueError("Native graph returned an invalid score")
        scores[sid] = max(score, scores.get(sid, float("-inf")))
        paths[sid].append(record)
    ordered = sorted(scores, key=lambda sid: (-scores[sid], sid))[:limit]
    if not ordered:
        raise ValueError("Native hybrid/Cypher retrieval returned no original evidence")
    return [{"source_id": sid, "score": scores[sid], "graph_paths": paths[sid]} for sid in ordered]


def run(input_path, output_path, uri, credential_path):
    from neo4j import GraphDatabase
    from neo4j_graphrag.indexes import create_fulltext_index, create_vector_index
    from neo4j_graphrag.retrievers import HybridCypherRetriever
    from neo4j_graphrag.types import RetrieverResultItem

    if output_path.exists():
        raise ValueError("Preserve earlier native worker results")
    endpoint = urlsplit(uri)
    if (
        endpoint.scheme not in {"bolt", "neo4j"}
        or endpoint.hostname not in {"127.0.0.1", "localhost"}
        or endpoint.username
        or endpoint.password
    ):
        raise ValueError("Use the isolated local Neo4j endpoint without URI credentials")
    request = json.loads(input_path.read_bytes())
    units, dimensions = validate_input(request)
    sdk_version = importlib.metadata.version("neo4j-graphrag")
    if sdk_version != request.get("config", {}).get("expected_sdk_version", "1.22.0"):
        raise ValueError("Native Neo4j GraphRAG SDK release differs from the frozen configuration")
    identity = request["experiment_identity"]
    credentials = json.loads(credential_path.read_bytes())
    database = credentials.get("database", "neo4j")
    password = credentials["password"]
    anchors, edges = source_relations(request["corpus"]["units"])
    started = perf_counter()
    with GraphDatabase.driver(uri, auth=(credentials.get("username", "neo4j"), password)) as driver:
        driver.verify_connectivity()

        def query(text, parameters=None):
            return driver.execute_query(text, parameters or {}, database_=database).records

        components = [
            dict(r)
            for r in query(
                "CALL dbms.components() YIELD name, versions, edition RETURN name, versions, edition"
            )
        ]
        expected_server = request.get("config", {}).get("expected_server_version", "2026.10.0")
        if not any(expected_server in r["versions"] for r in components):
            raise ValueError("Native Neo4j server release differs from the frozen configuration")
        existing = query(
            "MATCH (s:OFPOriginalSource {experiment_id:$identity}) RETURN s.source_id AS source_id, s.text_sha256 AS text_sha256, s.vector_sha256 AS vector_sha256",
            {"identity": identity},
        )
        expected = {
            u["source_id"]: (u["text_sha256"], digest(v))
            for u, v in zip(request["corpus"]["units"], request["corpus_vectors"], strict=True)
        }
        if existing and (
            {r["source_id"]: (r["text_sha256"], r["vector_sha256"]) for r in existing} != expected
        ):
            raise ValueError("Existing experiment graph has a different original/vector inventory")
        indexes = {}
        for module in sorted({u["module"] for u in units.values()}):
            stem, label = graph_namespace(identity, module)
            rows = [
                {
                    **u,
                    "key": identity + ":" + u["source_id"],
                    "embedding": v,
                    "vector_sha256": digest(v),
                    "line_end": max(1, len(u["evidence_text"].splitlines())),
                }
                for u, v in zip(request["corpus"]["units"], request["corpus_vectors"], strict=True)
                if u["module"] == module
            ]
            query(
                f"UNWIND $rows AS row MERGE (s:OFPOriginalSource {{key:row.key}}) SET s:`{label}`, s.experiment_id=$identity, s.source_id=row.source_id, s.module=row.module, s.licence_context=row.licence_context, s.source_text=row.evidence_text, s.text_sha256=row.text_sha256, s.embedding=row.embedding, s.vector_sha256=row.vector_sha256, s.pdf_page=row.pdf_page, s.section=row.section WITH s,row MERGE (c:OFPClause {{key:row.key+':clause'}}) SET c.experiment_id=$identity,c.source_id=row.source_id,c.text=row.evidence_text,c.char_start=0,c.char_end=size(row.evidence_text),c.line_start=1,c.line_end=row.line_end MERGE (s)-[:HAS_CLAUSE]->(c)",
                {"rows": rows, "identity": identity},
            )
            create_vector_index(
                driver,
                stem + "_vector",
                label,
                "embedding",
                dimensions,
                "cosine",
                neo4j_database=database,
            )
            create_fulltext_index(
                driver, stem + "_text", label, ["source_text"], neo4j_database=database
            )
            indexes[module] = {
                "vector": stem + "_vector",
                "fulltext": stem + "_text",
                "label": label,
            }
        for kind, relationship in (("condition", "HAS_CONDITION"), ("exception", "HAS_EXCEPTION")):
            selected = [a for a in anchors if a["kind"] == kind]
            query(
                f"UNWIND $anchors AS row MATCH (s:OFPOriginalSource {{key:$identity+':'+row.source_id}})-[:HAS_CLAUSE]->(c) MERGE (a:OFPAnchor {{key:$identity+':'+row.anchor_id}}) SET a.experiment_id=$identity,a.module=row.module,a.kind=row.kind,a.normalized_text=toLower(row.text),a.review_status=row.review_status MERGE (c)-[r:{relationship} {{char_start:row.char_start,char_end:row.char_end}}]->(a) SET r.source_id=row.source_id,r.literal_text=row.text,r.line_start=row.line_start,r.line_end=row.line_end MERGE (a)-[:ANCHORED_IN]->(s)",
                {"anchors": selected, "identity": identity},
            )
        for relationship in ("CONTAINS_ORIGINAL", "EXPLICIT_SECTION_REFERENCE"):
            query(
                f"UNWIND $edges AS row MATCH (a:OFPOriginalSource {{key:$identity+':'+row.source_id}}),(b:OFPOriginalSource {{key:$identity+':'+row.target_id}}) MERGE (a)-[:{relationship}]->(b)",
                {
                    "edges": [e for e in edges if e["relationship"] == relationship],
                    "identity": identity,
                },
            )
        query("CALL db.awaitIndexes(300)")
        native_indexes = [
            dict(r)
            for r in query(
                "SHOW INDEXES YIELD name, type, state, labelsOrTypes, properties WHERE name STARTS WITH $prefix RETURN name,type,state,labelsOrTypes,properties",
                {"prefix": "ofp_" + identity + "_"},
            )
        ]
        if len(native_indexes) != len(indexes) * 2 or any(
            r["state"] != "ONLINE" for r in native_indexes
        ):
            raise ValueError("Native task vector/fulltext indexes are incomplete")
        graph_counts = {
            "nodes": [
                dict(r)
                for r in query(
                    "MATCH (n {experiment_id:$identity}) RETURN labels(n) AS labels, count(*) AS count",
                    {"identity": identity},
                )
            ],
            "relationships": [
                dict(r)
                for r in query(
                    "MATCH (n {experiment_id:$identity})-[r]->(m {experiment_id:$identity}) RETURN type(r) AS relationship, count(*) AS count",
                    {"identity": identity},
                )
            ],
        }
        build_seconds = perf_counter() - started
        results = []
        for item in request["queries"]:
            begin = perf_counter()
            row = {
                "query_id": item["query_id"],
                "case_id": item["case_id"],
                "module": item["module"],
                "method": "neo4j_clause_graph",
                "experiment_identity": identity,
                "frozen_query": item["query"],
                "submitted_fulltext_query": lexical_query(item["query"]),
            }
            try:
                index = indexes[item["module"]]
                retriever = HybridCypherRetriever(
                    driver,
                    index["vector"],
                    index["fulltext"],
                    RETRIEVAL_QUERY,
                    result_formatter=lambda record: RetrieverResultItem(
                        content=record.data(), metadata=record.data()
                    ),
                    neo4j_database=database,
                )
                native = retriever.search(
                    query_text=row["submitted_fulltext_query"],
                    query_vector=request["query_vectors"][item["query_id"]],
                    top_k=20,
                    query_params={"experiment_identity": identity, "module": item["module"]},
                    ranker="naive",
                )
                records = [v.metadata for v in native.items]
                ranked = aggregate(records, units, item["module"])
                row.update(
                    status="completed",
                    source_ids=[r["source_id"] for r in ranked],
                    ranked_sources=ranked,
                    native_record_count=len(records),
                )
            except Exception as exc:
                row.update(
                    status="failed",
                    source_ids=[],
                    error=(type(exc).__name__ + ": " + str(exc)).replace(password, "[redacted]"),
                )
            row["retrieval_seconds"] = perf_counter() - begin
            results.append(row)
    output = {
        "manifest": {
            "policy": POLICY,
            "experiment_identity": identity,
            "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
            "worker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "neo4j_graphrag_version": sdk_version,
            "neo4j_driver_version": importlib.metadata.version("neo4j"),
            "server_components": components,
            "indexes": native_indexes,
            "native_graph_counts": graph_counts,
            "index_build_seconds": build_seconds,
            "original_sources": len(units),
            "original_text_rewritten": False,
            "native_retriever": "neo4j_graphrag.retrievers.HybridCypherRetriever.search",
            "graph_anchor_status": "engineering_regex_anchors_pending_clinical_review",
            "fulltext_policy": "lowercase_alphanumeric_backend_tokens_v1; saved dense query vector remains bound to unchanged raw query",
            "source_scope": "module-specific native index labels; commercial/shared only",
            "llm_calls": 0,
            "production_change": False,
        },
        "graph_relations": {
            "literal_anchors": anchors,
            "source_edges": edges,
            "curated_related_source_metadata_used_as_explicit_edges": False,
        },
        "results": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return {
        "recorded": len(results),
        "completed": sum(r["status"] == "completed" for r in results),
        "failed": sum(r["status"] == "failed" for r in results),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--uri", default="bolt://127.0.0.1:17687")
    parser.add_argument("--credential-file", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.input, args.output, args.uri, args.credential_file)))
