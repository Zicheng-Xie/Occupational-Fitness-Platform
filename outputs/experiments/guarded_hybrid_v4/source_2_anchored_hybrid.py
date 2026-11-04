"""Label-free, anchor-aware fusion ablations without passage-similarity MMR.

Only already ranked channels and frozen corpus metadata are accepted. Patient
reference answers, expected sources and rule outcomes are outside this API.
``covers_source_ids`` denotes verified original-text containment in the corpus;
it is not a list of sources expected for a patient.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping

from occupational_fitness_rag.evaluation.planned_hybrid import fuse_channels

POLICIES = frozenset(
    {
        "anchor_only",
        "facet_balanced",
        "anchor_best",
        "containment",
        "complete_clause",
        "query_balanced_clause",
    }
)
POLICY_VERSION = "anchor_aware_original_coverage_v2"


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def _configuration(config):
    allowed = {
        "policy",
        "rrf_k",
        "anchor_weight",
        "coverage_weight",
        "candidate_k",
        "sensitivity_k",
    }
    if set(config) - allowed:
        raise ValueError("Unknown anchor-aware ranking configuration")
    policy = config.get("policy")
    if policy not in POLICIES:
        raise ValueError("Unknown anchor-aware ranking policy")
    result = {
        "policy": policy,
        "rrf_k": config.get("rrf_k", 60),
        "anchor_weight": config.get("anchor_weight", 0.75),
        "coverage_weight": config.get("coverage_weight", 0.15),
        "candidate_k": config.get("candidate_k", 10),
        "sensitivity_k": config.get("sensitivity_k", 10),
    }
    for name in ("rrf_k", "candidate_k", "sensitivity_k"):
        if type(result[name]) is not int or result[name] < 1:
            raise ValueError(f"{name} must be a positive integer")
    for name in ("anchor_weight", "coverage_weight"):
        if not 0 <= _number(result[name], name) <= 1:
            raise ValueError(f"{name} must be between zero and one")
    if result["candidate_k"] < result["sensitivity_k"]:
        raise ValueError("Candidate budget cannot be smaller than the output budget")
    return result


def _inventory(units):
    if isinstance(units, Mapping):
        rows = list(units.values())
        if any(key != unit.get("source_id") for key, unit in units.items()):
            raise ValueError("Corpus mapping keys differ from original source IDs")
    else:
        rows = list(units)
    result = {}
    for unit in rows:
        sid = unit.get("source_id")
        if not isinstance(sid, str) or not sid or sid in result:
            raise ValueError("Corpus requires unique original source IDs")
        result[sid] = unit
    if not result:
        raise ValueError("Original corpus inventory is empty")
    return result


def _validate_channels(channels, units):
    """Validate scope, then collapse repeated literal query/engine results."""
    channels = list(channels)
    names = [channel.get("channel") for channel in channels]
    if len(set(names)) != len(names) or any(not isinstance(n, str) or not n for n in names):
        raise ValueError("Channel identities must be unique nonempty strings")
    by_name = dict(zip(names, channels, strict=True))
    if not {"anchor:vector", "anchor:bm25"} <= set(names):
        raise ValueError("Both original anchor retrieval channels are required")
    anchors = [by_name["anchor:vector"], by_name["anchor:bm25"]]
    if [c.get("kind") for c in anchors] != ["vector", "bm25"]:
        raise ValueError("Anchor channel identities differ from their engines")
    anchor_query = anchors[0].get("query")
    if not isinstance(anchor_query, str) or not anchor_query.strip():
        raise ValueError("A literal original anchor query is required")
    if anchors[1].get("query") != anchor_query:
        raise ValueError("Original anchor query differs between engines")
    if not any(channel.get("hits") for channel in anchors):
        raise ValueError("Original anchor channels contain no accessible evidence")
    module = None
    seen_queries = {}
    retained = []
    duplicate_names = []
    # Dense-first anchor insertion matches the existing production RRF ties.
    ordered = [*anchors, *(c for c in channels if c not in anchors)]
    for channel in ordered:
        kind, text = channel.get("kind"), channel.get("query")
        if kind not in {"vector", "bm25"}:
            raise ValueError("Unknown ranked retrieval engine")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("A literal retrieval query is required")
        if not isinstance(channel.get("hits"), list):
            raise ValueError("A retrieval channel requires an ordered hit list")
        seen_hits = set()
        for hit in channel["hits"]:
            sid = hit.get("source_id")
            if not isinstance(sid, str) or sid not in units or sid in seen_hits:
                raise ValueError("Unknown or repeated original source inside a channel")
            seen_hits.add(sid)
            _number(hit.get("score"), "Raw retrieval score")
            unit = units[sid]
            if unit.get("licence_context") not in {"commercial", "shared"}:
                raise ValueError("A ranked source violates commercial/shared scope")
            if not isinstance(unit.get("module"), str) or not unit["module"]:
                raise ValueError("A ranked source requires a disease module")
            if module is None:
                module = unit["module"]
            if unit["module"] != module:
                raise ValueError("Ranked channels cross the frozen disease module")
        identity = (text, kind)
        previous = seen_queries.get(identity)
        if previous is not None:
            if previous["hits"] != channel.get("hits", []):
                raise ValueError("The same literal query and engine have conflicting rankings")
            duplicate_names.append(channel["channel"])
        else:
            seen_queries[identity] = channel
            retained.append(channel)
    if module is None:
        raise ValueError("Original search channels contain no accessible evidence")
    return retained, anchors, module, duplicate_names


def _score_map(channels, rrf_k):
    return {row["source_id"]: row for row in fuse_channels(channels, rrf_k)}


def _atoms(unit, units, module):
    ids = unit.get("covers_source_ids", [])
    if not isinstance(ids, list) or any(not isinstance(s, str) for s in ids):
        raise ValueError("Original-text containment IDs must be a list of source IDs")
    if len(set(ids)) != len(ids):
        raise ValueError("Repeated corpus containment source ID")
    for sid in ids:
        if sid not in units:
            raise ValueError("Original-text containment points outside the frozen corpus")
        other = units[sid]
        if other.get("module") != module or other.get("licence_context") not in {
            "commercial",
            "shared",
        }:
            raise ValueError("Original-text containment crosses the accessible source scope")
    # An expanded paragraph without canonical containment remains an independent
    # source atom; it is not assigned zero relevance or zero coverage by default.
    return set(ids) if ids else {unit["source_id"]}


def _consolidate_clauses(rows, units, cfg):
    """Promote whole original clauses, with an exact-text containment test."""
    pool = rows[: cfg["candidate_k"]]
    texts = {
        row["source_id"]: " ".join(units[row["source_id"]].get("evidence_text", "").split())
        for row in pool
    }
    proposals = []
    for index, parent in enumerate(pool):
        pid = parent["source_id"]
        punit = units[pid]
        if punit.get("licence_context") != "commercial" or not punit.get("pdf_page"):
            continue
        children = []
        for child in pool[:index]:
            cid = child["source_id"]
            cunit = units[cid]
            if (
                cunit.get("licence_context") == "commercial"
                and cunit.get("pdf_page") == punit["pdf_page"]
                and len(texts[cid]) >= 40
                and len(texts[pid]) > len(texts[cid])
                and texts[cid] in texts[pid]
            ):
                children.append(cid)
        if len(children) >= 2:
            proposals.append((index, pid, children))
    # A broader complete clause wins overlapping proposals, then base relevance.
    proposals.sort(key=lambda item: (-len(item[2]), item[0]))
    parents, child_to_parent = {}, {}
    for _, pid, children in proposals:
        if pid in child_to_parent or any(cid in parents for cid in children):
            continue
        available = [cid for cid in children if cid not in child_to_parent]
        if len(available) < 2:
            continue
        parents[pid] = available
        child_to_parent.update(dict.fromkeys(available, pid))
    by_id = {row["source_id"]: row for row in rows}
    primary, seen = [], set()
    for row in rows:
        sid = row["source_id"]
        if sid in child_to_parent:
            pid = child_to_parent[sid]
            if pid not in seen:
                primary.append(
                    {
                        **by_id[pid],
                        "selection_score": max(by_id[cid]["score"] for cid in parents[pid]),
                        "literal_contained_child_sources": parents[pid],
                        "clause_promoted": True,
                    }
                )
                seen.add(pid)
        elif sid not in seen:
            primary.append(row)
            seen.add(sid)
    # Consolidation affects the main five-source evidence budget. The original
    # narrower sources remain available after that budget for Top10 analysis.
    first = primary[: min(5, cfg["sensitivity_k"])]
    first_ids = {row["source_id"] for row in first}
    tail = [row for row in rows if row["source_id"] not in first_ids]
    return [*first, *tail][: cfg["sensitivity_k"]], {
        "literal_clause_promotions": [
            {"parent_source_id": sid, "contained_child_source_ids": children}
            for sid, children in parents.items()
        ],
        "consolidation_main_budget": 5,
        "minimum_contained_text_characters": 40,
    }


def rank_channels(channels, units, config):
    """Rank frozen original sources and return scores plus audit diagnostics.

    ``facet_balanced`` first fuses each distinct literal query independently,
    averages its scores with missing hits worth zero, then blends that mean with
    the original query. ``anchor_best`` blends the anchor and the old best-rank
    fusion. Both retain the original query at the configured anchor weight.

    ``containment`` applies anchor-best scores to the first ``candidate_k``
    originals. A greedy selection uses ``(1-w)*relevance + w*novel_atoms/M``,
    where M is the largest initial atom count in that candidate pool. This is
    corpus-source coverage, not token similarity, and does not remove or edit
    passages. Zero coverage weight reproduces anchor-best exactly.
    """
    cfg = _configuration(config)
    inventory = _inventory(units)
    retained, anchors, module, duplicates = _validate_channels(channels, inventory)
    anchor = _score_map(anchors, cfg["rrf_k"])
    best = _score_map(retained, cfg["rrf_k"])
    first_seen = {}
    for channel in retained:
        for hit in channel["hits"]:
            first_seen.setdefault(hit["source_id"], len(first_seen))
    groups = defaultdict(list)
    for channel in retained:
        if channel["query"] != anchors[0]["query"]:
            groups[channel["query"]].append(channel)
    facet_maps = [_score_map(group, cfg["rrf_k"]) for group in groups.values()]
    rows = []
    for sid, row in best.items():
        a = anchor.get(sid, {}).get("score", 0.0)
        b = row["score"]
        f = (
            sum(scores.get(sid, {}).get("score", 0.0) for scores in facet_maps) / len(facet_maps)
            if facet_maps
            else a
        )
        policy = cfg["policy"]
        if policy == "anchor_only":
            if sid not in anchor:
                continue
            score = a
        else:
            other = f if policy in {"facet_balanced", "query_balanced_clause"} else b
            score = cfg["anchor_weight"] * a + (1 - cfg["anchor_weight"]) * other
        rows.append(
            {
                "source_id": sid,
                "score": score,
                "anchor_score": a,
                "facet_mean_score": f,
                "best_channel_score": b,
                "first_seen": first_seen[sid],
                "retrieval_paths": row["retrieval_paths"],
            }
        )
    rows.sort(key=lambda row: (-row["score"], row["first_seen"]))
    before = [row["source_id"] for row in rows]
    selected = rows[: cfg["sensitivity_k"]]
    clause_diagnostics = {}
    if cfg["policy"] == "containment" and cfg["coverage_weight"] > 0:
        candidates = rows[: cfg["candidate_k"]]
        atoms = {
            row["source_id"]: _atoms(inventory[row["source_id"]], inventory, module)
            for row in candidates
        }
        maximum = max(len(value) for value in atoms.values())
        covered = set()
        selected = []
        remaining = list(candidates)
        while remaining and len(selected) < cfg["sensitivity_k"]:
            scored = []
            for row in remaining:
                novel = atoms[row["source_id"]] - covered
                value = (1 - cfg["coverage_weight"]) * row["score"] + cfg["coverage_weight"] * len(
                    novel
                ) / maximum
                scored.append((value, row, novel))
            value, pick, novel = max(scored, key=lambda item: (item[0], -item[1]["first_seen"]))
            selected.append(
                {
                    **pick,
                    "selection_score": value,
                    "corpus_coverage_atoms": sorted(atoms[pick["source_id"]]),
                    "new_corpus_coverage_atoms": sorted(novel),
                }
            )
            covered.update(atoms[pick["source_id"]])
            remaining.remove(pick)
    elif cfg["policy"] in {"complete_clause", "query_balanced_clause"}:
        selected, clause_diagnostics = _consolidate_clauses(rows, inventory, cfg)
    return {
        "source_ids": [row["source_id"] for row in selected],
        "ranked_sources": selected,
        "diagnostics": {
            "policy_version": POLICY_VERSION,
            "config": cfg,
            "module": module,
            "licence_context": "commercial",
            "distinct_channels": len(retained),
            "duplicate_query_channels_ignored": duplicates,
            "distinct_non_anchor_queries": len(facet_maps),
            "candidate_sources": len(rows),
            "before_coverage_source_ids": before[: cfg["sensitivity_k"]],
            "mmr_used": False,
            "reference_labels_available_to_ranker": False,
            "source_text_modified": False,
            **clause_diagnostics,
        },
    }
