"""Experimental query-aware source/rule graph ranking over verified anchors.

The graph contains only existing catalogue sources, rule links and section links.
It has no LLM-extracted entities or community reports and is not full GraphRAG.
It never changes production rule outcomes or source quotations.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict

from occupational_fitness_rag.retrieval.fusion import FusedResult

_STOP = {
    "a", "an", "and", "are", "as", "at", "be", "by", "commercial", "diabetes",
    "driver", "driving", "for", "from", "has", "he", "her", "his", "in", "is",
    "licence", "nurse", "of", "on", "or", "patient", "she", "the", "to", "was",
    "were", "with", "blackout", "hearing", "hypertension", "vision",
}


def graph_manifest(book, catalogue):
    """Export the rule/source/section graph for provenance and clinical review."""
    nodes, edges = {}, set()
    for source_id, unit in catalogue.units.items():
        nodes[f"source:{source_id}"] = {
            "type": "verified_source",
            "source_id": source_id,
            "section": unit["section"],
            "pdf_page": unit["pdf_page"],
            "table_row": unit["table_row"],
        }
        section = f"section:{unit['section']}"
        nodes.setdefault(section, {"type": "guideline_section", "section": unit["section"]})
        edges.add((section, f"source:{source_id}", "contains_source"))
        for other in unit["cross_references"]:
            if other not in catalogue.units:
                raise ValueError("Graph cross-reference names an unknown source")
            edges.add((f"source:{source_id}", f"source:{other}", "catalogue_reference"))
    for rule in book.rules:
        rule_node = f"rule:{rule['rule_id']}"
        nodes[rule_node] = {
            "type": "rule",
            "module": rule["module"],
            "subcondition": rule.get("subcondition"),
        }
        for source_id in rule["source_ids"]:
            if source_id not in catalogue.units:
                raise ValueError("Graph rule names an unknown source")
            edges.add((rule_node, f"source:{source_id}", "cites_source"))
    return {
        "schema_version": "1.0.0",
        "graph_type": "curated_rule_source_section_graph",
        "full_graphrag": False,
        "clinical_review_status": "pending",
        "index_sha256": catalogue.index_sha256,
        "ruleset_sha256": book.sha256,
        "nodes": [{"id": node_id, **nodes[node_id]} for node_id in sorted(nodes)],
        "edges": [
            {"from": left, "to": right, "kind": kind}
            for left, right, kind in sorted(edges)
        ],
    }


def _terms(text):
    # Keep "non-insulin" distinct from insulin; split other clinical compounds.
    text = re.sub(r"\bnon[- ]insulin\b", "noninsulin", text.lower())
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text)
        if len(token) >= 3 and token not in _STOP
    }


def expand_local_graph(seeds, filtered_documents, book, catalogue, module, query, top_k):
    """Combine query-to-rule/source matches with inspectable graph paths."""
    source_docs = {}
    for doc in filtered_documents:
        for source_id in doc.metadata["source_ids_csv"].split(","):
            if source_id not in catalogue.units or doc.metadata["module"] != module:
                raise ValueError("Graph source crossed its verified module boundary")
            source_docs[source_id] = doc
    if not source_docs:
        return []
    query_terms = _terms(query)
    scores = defaultdict(float)
    paths = defaultdict(set)
    seed_by_chunk = {hit.doc.chunk_id: hit for hit in seeds}
    for rank, hit in enumerate(seeds, 1):
        if hit.doc.chunk_id not in {doc.chunk_id for doc in filtered_documents}:
            raise ValueError("Graph seed crossed its metadata filter")
        for source_id in hit.doc.metadata["source_ids_csv"].split(","):
            scores[source_id] += 0.8 / math.sqrt(rank)
            paths[source_id].add(f"hybrid_seed_rank:{rank}")
    for source_id in source_docs:
        unit = catalogue.units[source_id]
        title_matches = query_terms & _terms(unit["table_row"] or "")
        evidence_matches = query_terms & _terms(unit["evidence_text"])
        if title_matches:
            scores[source_id] += min(0.42, 0.16 * len(title_matches))
            paths[source_id].add("source_title:" + ",".join(sorted(title_matches)))
        if evidence_matches:
            scores[source_id] += min(0.12, 0.025 * len(evidence_matches))
            paths[source_id].add("source_text_terms:" + ",".join(sorted(evidence_matches)))
    neighbours = defaultdict(dict)

    def connect(left, right, weight, reason):
        if left == right or left not in source_docs or right not in source_docs:
            return
        if weight > neighbours[left].get(right, (0, ""))[0]:
            neighbours[left][right] = (weight, reason)
            neighbours[right][left] = (weight, reason)

    for rule in book.rules:
        if rule["module"] != module:
            continue
        sources = [source_id for source_id in rule["source_ids"] if source_id in source_docs]
        matched = query_terms & _terms(
            " ".join((rule.get("subcondition") or "", rule.get("rag_query_key") or ""))
        )
        if matched:
            for source_id in sources:
                scores[source_id] += min(0.36, 0.18 * len(matched))
                paths[source_id].add(
                    f"rule:{rule['rule_id']}:" + ",".join(sorted(matched))
                )
        for left in sources:
            for right in sources:
                connect(left, right, 0.70, f"shared_rule:{rule['rule_id']}")
    for source_id in source_docs:
        unit = catalogue.units[source_id]
        for other in unit["cross_references"]:
            connect(source_id, other, 0.9, f"catalogue_reference:{source_id}")
        for other in source_docs:
            if unit["section"] == catalogue.units[other]["section"]:
                connect(source_id, other, 0.22, f"same_section:{unit['section']}")
    direct = dict(scores)
    for source_id, value in direct.items():
        for neighbour, (weight, reason) in neighbours[source_id].items():
            scores[neighbour] += 0.12 * weight * value
            paths[neighbour].add(reason)
    # Unit-level comparison has one source per chunk. Aggregate defensively for
    # grouped units while preserving exactly the filtered source documents.
    chunk_scores = defaultdict(float)
    chunk_paths = defaultdict(set)
    docs_by_chunk = {doc.chunk_id: doc for doc in filtered_documents}
    for source_id, value in scores.items():
        chunk_id = source_docs[source_id].chunk_id
        chunk_scores[chunk_id] = max(chunk_scores[chunk_id], value)
        chunk_paths[chunk_id].update(paths[source_id])
    ranked = sorted(chunk_scores, key=lambda key: (-chunk_scores[key], key))[:top_k]
    return [
        FusedResult(
            doc=docs_by_chunk[chunk_id],
            score=chunk_scores[chunk_id],
            vector_score=(
                seed_by_chunk[chunk_id].vector_score if chunk_id in seed_by_chunk else None
            ),
            bm25_score=(seed_by_chunk[chunk_id].bm25_score if chunk_id in seed_by_chunk else None),
            graph_paths=sorted(chunk_paths[chunk_id]),
        )
        for chunk_id in ranked
    ]
