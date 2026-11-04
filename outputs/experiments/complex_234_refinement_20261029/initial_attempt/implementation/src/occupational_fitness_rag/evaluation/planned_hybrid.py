"""Experimental fact-scoped plan/search/inspect/refine retrieval.

This first-party method borrows selected designs documented in
configs/experiments/planned_hybrid_sources.json. It does not execute either
external framework or change the production retrieval pipeline.
"""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict

from occupational_fitness_rag.indexing.base import StoredDocument
from occupational_fitness_rag.provenance import digest
from occupational_fitness_rag.retrieval.bm25 import rank_bm25, tokenize

METHOD = "planned_hybrid"
POLICY = "source_literal_facets_best_channel_rrf_mmr_v1"
GENERIC = frozenset(
    "commercial driving medical fitness standard patient person documented present absent value history clinical assessment blood pressure treated treatment true false none".split()
)


def module_of(field):
    prefix = field.split(".", 1)[0]
    return "hypertension" if prefix == "cardiovascular" else prefix


def plan_query(query, patient, max_facets=4):
    """Partition all verified fields, preserving their values and source quotes.

    No free-form model rewrite, decision label, rule or source catalogue is
    available to this planner. False, zero, negation and timing remain literal.
    """
    if type(max_facets) is not int or not 1 <= max_facets <= 8:
        raise ValueError("Facet budget must be an integer between one and eight")
    module = query["module"]
    if query["licence_context"] != "commercial" or module not in patient["modules"]:
        raise ValueError("Planner scope differs from the frozen query")
    facts = {
        name: record
        for name, record in patient["verified_patient_facts"].items()
        if module_of(name) == module and record.get("value") is not None
    }
    audit = query["query_audit"]
    values = {name: fact["value"] for name, fact in facts.items()}
    if values != audit["field_values"] or sorted(facts) != audit["field_names"]:
        raise ValueError("Planner facts differ from frozen query facts")
    groups = defaultdict(list)
    for name in sorted(facts):
        # Keep a nested field family (e.g. left/right acuity) together. Flat
        # fields form individual groups rather than one entire disease query.
        groups[".".join(name.split(".")[:2])].append(name)
    families = list(groups.values())
    count = min(len(families), max_facets)
    # Bounded contiguous partitions retain every family and every fact.
    buckets = [
        [
            name
            for family in families[
                index * len(families) // count : (index + 1) * len(families) // count
            ]
            for name in family
        ]
        for index in range(count)
    ]
    facets = []
    context = f"{module} commercial driving medical fitness standard"
    for names in buckets:
        quotes = list(
            dict.fromkeys(q for name in names for q in facts[name].get("patient_quotes", []))
        )
        if not quotes or any(
            not isinstance(q, str) or not q.strip() or q not in patient["nurse_note"]
            for q in quotes
        ):
            raise ValueError("Facet requires actual original patient quotations")
        statements = [
            re.sub(r"[._]+", " ", name)
            + " = "
            + json.dumps(facts[name]["value"], ensure_ascii=False, allow_nan=False)
            for name in names
        ]
        facet = {
            "field_names": names,
            "field_values": {name: values[name] for name in names},
            "patient_quotes": quotes,
            "query": " | ".join([context, *statements, *quotes]),
            "keyword_followup_query": " | ".join([context, *quotes]),
        }
        facets.append({**facet, "facet_id": digest(facet)})
    return {
        "policy": POLICY,
        "query_id": query["query_id"],
        "module": module,
        "licence_context": "commercial",
        "anchor_query": query["query"],
        "facets": facets,
        "all_documented_fields_retained": sorted(
            name for facet in facets for name in facet["field_names"]
        )
        == sorted(facts),
        "no_documented_facts": not facts,
    }


def cosine(left, right):
    if (
        len(left) != len(right)
        or not left
        or any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
            for v in [*left, *right]
        )
    ):
        raise ValueError("Invalid dense embedding dimensions or values")
    norm = math.sqrt(sum(v * v for v in left) * sum(v * v for v in right))
    if not norm:
        raise ValueError("Zero dense embedding")
    return sum(a * b for a, b in zip(left, right, strict=True)) / norm


def search_channels(text, module, units, vectors, query_vector, channel_id):
    """Return independent ranked lists; never flatten them before assigning rank."""
    if len(units) != len(vectors):
        raise ValueError("Original corpus vector inventory differs")
    docs = [
        StoredDocument(u["source_id"], u["evidence_text"], {"module": module})
        for u in units
        if u["module"] == module and u["licence_context"] in {"commercial", "shared"}
    ]
    if not docs:
        raise ValueError("No accessible originals in the requested scope")
    sparse = rank_bm25(text, docs, 30)
    dense = [
        (u["source_id"], cosine(query_vector, v))
        for u, v in zip(units, vectors, strict=True)
        if u["module"] == module and u["licence_context"] in {"commercial", "shared"}
    ]
    dense.sort(key=lambda item: (-item[1], item[0]))
    return [
        {
            "channel": channel_id + ":vector",
            "kind": "vector",
            "query": text,
            "hits": [{"source_id": sid, "score": value} for sid, value in dense[:20]],
        },
        {
            "channel": channel_id + ":bm25",
            "kind": "bm25",
            "query": text,
            "hits": [{"source_id": doc.chunk_id, "score": value} for doc, value in sparse],
        },
    ]


def fuse_channels(channels, rrf_k=60):
    """Best rank per type prevents duplicated query variants from adding votes."""
    if type(rrf_k) is not int or rrf_k < 1:
        raise ValueError("RRF rank constant must be positive")
    ranks, paths = defaultdict(dict), defaultdict(list)
    for channel in channels:
        if channel["kind"] not in {"vector", "bm25"}:
            raise ValueError("Unknown retrieval channel type")
        seen = set()
        for rank, hit in enumerate(channel["hits"], 1):
            sid = hit["source_id"]
            if sid in seen:
                raise ValueError("Repeated original ID inside one channel")
            seen.add(sid)
            kind = channel["kind"]
            ranks[sid][kind] = min(rank, ranks[sid].get(kind, rank))
            paths[sid].append(
                {"channel": channel["channel"], "rank": rank, "raw_score": hit["score"]}
            )
    maximum = 2 / (rrf_k + 1)
    rows = [
        {
            "source_id": sid,
            "score": sum(1 / (rrf_k + rank) for rank in by_type.values()) / maximum,
            "best_ranks": by_type,
            "retrieval_paths": paths[sid],
        }
        for sid, by_type in ranks.items()
    ]
    return sorted(rows, key=lambda row: (-row["score"], row["source_id"]))


def inspect_facets(plan, selected_ids, units):
    """Lexical query coverage only: never medical support or sufficiency."""
    visible = set(tokenize(" ".join(units[sid]["evidence_text"] for sid in selected_ids)))
    audit = []
    for facet in plan["facets"]:
        words = set(
            tokenize(" ".join(re.sub(r"[._]+", " ", name) for name in facet["field_names"]))
        )
        terms = words - GENERIC - {plan["module"]}
        matched = terms & visible
        audit.append(
            {
                "facet_id": facet["facet_id"],
                "terms": sorted(terms),
                "matched_terms": sorted(matched),
                "fraction": len(matched) / len(terms) if terms else None,
                "interpretation": "Lexical overlap; does not establish guideline applicability or patient sufficiency",
            }
        )
    return audit


def diversify(rows, units, k=10, relevance_weight=0.7):
    """MMR on normalized RRF relevance and Jaccard passage redundancy."""
    if not 0 < relevance_weight <= 1 or type(k) is not int or k <= 0:
        raise ValueError("Invalid diversity budget")
    remaining, chosen = list(rows), []
    tokens = {
        row["source_id"]: set(tokenize(units[row["source_id"]]["evidence_text"])) for row in rows
    }
    while remaining and len(chosen) < k:
        evaluated = []
        for row in remaining:
            terms = tokens[row["source_id"]]
            redundancy = max(
                (
                    len(terms & tokens[pick["source_id"]])
                    / max(1, len(terms | tokens[pick["source_id"]]))
                    for pick in chosen
                ),
                default=0,
            )
            score = relevance_weight * row["score"] - (1 - relevance_weight) * redundancy
            evaluated.append((score, row, redundancy))
        score, best, redundancy = max(
            evaluated, key=lambda item: item[0]
        )  # Stable input-order tie break.
        chosen.append({**best, "selection_score": score, "max_passage_redundancy": redundancy})
        remaining.remove(best)
    return chosen


def execute_plan(query, patient, corpus, vectors, anchor_vector, embed, config):
    """Run a bounded plan using only frozen facts and accessible original units.

    ``embed`` is the experiment's audited model transport, not a silent cache or
    fallback. A failure aborts this condition; the caller retains all attempts.
    """
    units = {u["source_id"]: u for u in corpus["units"]}
    plan = plan_query(query, patient, config["max_facets"])
    events = [{"stage": "plan", "plan": plan}]
    channels = search_channels(
        plan["anchor_query"], plan["module"], corpus["units"], vectors, anchor_vector, "anchor"
    )
    if plan["facets"]:
        facet_vectors = embed([f["query"] for f in plan["facets"]])
        if len(facet_vectors) != len(plan["facets"]):
            raise ValueError("Facet embedding response count differs")
        for facet, vector in zip(plan["facets"], facet_vectors, strict=True):
            channels.extend(
                search_channels(
                    facet["query"],
                    plan["module"],
                    corpus["units"],
                    vectors,
                    vector,
                    facet["facet_id"],
                )
            )
    ranked = fuse_channels(channels, config["rrf_k"])
    events.append({"stage": "search", "channels": channels, "fused": ranked})
    coverage = inspect_facets(plan, [r["source_id"] for r in ranked[:5]], units)
    events.append({"stage": "inspect", "query_term_coverage": coverage})
    missing = sorted(
        (
            r
            for r in coverage
            if r["fraction"] is not None and r["fraction"] < config["lexical_coverage_threshold"]
        ),
        key=lambda row: (row["fraction"], row["facet_id"]),
    )[: config["max_keyword_followups"]]
    followups = []
    for item in missing:
        facet = next(f for f in plan["facets"] if f["facet_id"] == item["facet_id"])
        text = facet["keyword_followup_query"]
        docs = [
            StoredDocument(u["source_id"], u["evidence_text"], {"module": plan["module"]})
            for u in units.values()
            if u["module"] == plan["module"] and u["licence_context"] in {"commercial", "shared"}
        ]
        followup = {
            "channel": "followup:" + facet["facet_id"],
            "kind": "bm25",
            "query": text,
            "hits": [{"source_id": d.chunk_id, "score": s} for d, s in rank_bm25(text, docs, 30)],
        }
        channels.append(followup)
        followups.append(followup)
    events.append({"stage": "refine", "keyword_only_followups": followups, "round_limit": 1})
    ranked = fuse_channels(channels, config["rrf_k"])
    selected = diversify(ranked, units, config["sensitivity_k"], config["relevance_weight"])
    if not selected:
        raise ValueError("The scoped search returned no original source evidence")
    ids = [row["source_id"] for row in selected]
    events.append(
        {
            "stage": "finalize",
            "source_ids": ids,
            "original_text_hashes": {sid: units[sid]["text_sha256"] for sid in ids},
        }
    )
    return {
        "source_ids": ids,
        "ranked_sources": selected,
        "without_diversity_source_ids": [
            row["source_id"] for row in ranked[: config["sensitivity_k"]]
        ],
        "events": events,
        "new_embedding_inputs": len(plan["facets"]),
        "keyword_followups": len(followups),
        "channel_searches": len(channels),
    }
