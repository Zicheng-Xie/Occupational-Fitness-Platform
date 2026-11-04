"""No-MMR source-coverage selection with a fixed original-RRF coverage floor.

The guard uses only retrieved originals and corpus-defined literal containment.
It never receives a patient's expected source IDs, outcome or rule decisions.
Its floor preserves the original query's Top10 original-source footprint under
the same ten-source budget. Better patient relevance still requires evaluation.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from functools import lru_cache

from occupational_fitness_rag.evaluation.anchored_hybrid import (
    _atoms,
)
from occupational_fitness_rag.evaluation.anchored_hybrid import (
    rank_channels as rank_anchored,
)

POLICY_VERSION = "wide_candidates_original_rrf_coverage_floor_v3"
POLICIES = frozenset({"wide_coverage", "guarded_coverage", "guarded_facet_coverage"})


def _configuration(config):
    allowed = {
        "policy",
        "anchor_weight",
        "coverage_weight",
        "rrf_k",
        "candidate_k",
        "sensitivity_k",
    }
    if set(config) - allowed or config.get("policy") not in POLICIES:
        raise ValueError("Unknown guarded retrieval policy or configuration")
    result = {
        "policy": config["policy"],
        "anchor_weight": config.get("anchor_weight", 0.75),
        "coverage_weight": config.get("coverage_weight", 0.15),
        "rrf_k": config.get("rrf_k", 60),
        "candidate_k": config.get("candidate_k", 30),
        "sensitivity_k": config.get("sensitivity_k", 10),
    }
    for name in ("anchor_weight", "coverage_weight"):
        value = result[name]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not 0 <= value <= 1
        ):
            raise ValueError("Guarded retrieval weights must be finite and between zero and one")
    if type(result["rrf_k"]) is not int or result["rrf_k"] < 1:
        raise ValueError("RRF rank constant must be a positive integer")
    if (
        type(result["candidate_k"]) is not int
        or not 10 <= result["candidate_k"] <= 60
        or type(result["sensitivity_k"]) is not int
        or result["sensitivity_k"] != 10
    ):
        raise ValueError("Use a ten-source output budget and a candidate budget from ten to sixty")
    return result


def _inventory(units):
    if isinstance(units, Mapping):
        if any(key != unit.get("source_id") for key, unit in units.items()):
            raise ValueError("Original source mapping keys differ")
        rows = list(units.values())
    else:
        rows = list(units)
    by_id = {unit["source_id"]: unit for unit in rows}
    if not rows or len(rows) != len(by_id):
        raise ValueError("Guarded retrieval requires unique original source IDs")
    return by_id


def _completion_solver(pool, guard_atoms, protected):
    """Return an exact at-most-k set-cover solver for the original footprint.

    The fixed target consists of the original query's retrieved source
    footprints, not patient reference answers. A selected source cannot be
    chosen twice: once its complete mask has been covered, it contributes
    nothing to any later uncovered mask and is ignored by the recursion.
    """
    bit = {sid: 1 << index for index, sid in enumerate(sorted(protected))}
    target = sum(bit.values())
    masks = {
        row["source_id"]: sum(bit[sid] for sid in guard_atoms[row["source_id"]] if sid in bit)
        for row in pool
    }
    order = {row["source_id"]: index for index, row in enumerate(pool)}

    @lru_cache(maxsize=None)
    def solve(uncovered, slots):
        if not uncovered:
            return ()
        if slots < 1:
            return None
        available = [(sid, mask & uncovered) for sid, mask in masks.items() if mask & uncovered]
        total = 0
        maximum = 0
        for _, mask in available:
            total |= mask
            maximum = max(maximum, mask.bit_count())
        if total != uncovered or not maximum or math.ceil(uncovered.bit_count() / maximum) > slots:
            return None
        # Every source costs one slot. A subset cannot make a feasible cover
        # smaller than an available superset; keep stable representatives of
        # equal masks. This is dominance pruning of a feasibility search only.
        maximal = []
        for sid, mask in available:
            dominated = any(
                mask | other == other and (mask != other or order[other_sid] < order[sid])
                for other_sid, other in available
                if other_sid != sid
            )
            if not dominated:
                maximal.append((sid, mask))
        # Branch on the least-supported remaining source atom. Private original
        # identifiers often force a source and make this small search cheap.
        atoms = [1 << index for index in range(uncovered.bit_length()) if uncovered & (1 << index)]
        pivot = min(atoms, key=lambda atom: sum(bool(mask & atom) for _, mask in maximal))
        options = sorted(
            ((sid, mask) for sid, mask in maximal if mask & pivot),
            key=lambda item: (-item[1].bit_count(), order[item[0]]),
        )
        for sid, mask in options:
            tail = solve(uncovered & ~mask, slots - 1)
            if tail is not None:
                return (sid, *tail)
        return None

    return target, masks, solve


def rank_channels(channels, units, config):
    """Return unchanged originals, selection scores and coverage-guard traces.

    The pool is the first N anchor-aware candidates union the original-query
    RRF Top10. The unguarded controls use the identical pool. The guarded
    selector considers candidates in source-coverage score order and accepts
    one only if the remaining original-source footprint still fits within the
    remaining ten-source budget. The output always contains at most ten real
    original units; it does not attach hidden passages to a Top5 item.
    """
    cfg = _configuration(config)
    inventory = _inventory(units)
    channels = list(channels)
    anchor = rank_anchored(channels, inventory, {"policy": "anchor_only"})
    module = anchor["diagnostics"]["module"]
    unique_hits = {hit["source_id"] for channel in channels for hit in channel["hits"]}
    full_budget = max(10, len(unique_hits))
    base = rank_anchored(
        channels,
        inventory,
        {
            "policy": "facet_balanced"
            if cfg["policy"] == "guarded_facet_coverage"
            else "anchor_best",
            "anchor_weight": cfg["anchor_weight"],
            "rrf_k": cfg["rrf_k"],
            "candidate_k": full_budget,
            "sensitivity_k": full_budget,
        },
    )
    by_id = {row["source_id"]: row for row in base["ranked_sources"]}
    pool_ids = list(
        dict.fromkeys(
            [
                *[row["source_id"] for row in base["ranked_sources"][: cfg["candidate_k"]]],
                *anchor["source_ids"],
            ]
        )
    )
    pool = [by_id[sid] for sid in pool_ids]
    pool_order = {sid: index for index, sid in enumerate(pool_ids)}
    # Ranking novelty retains the v2 corpus atoms. The stronger guard additionally
    # retains each original ID, including an expanded passage with no canonical
    # containment, matching the report's original-text coverage definition.
    atoms = {sid: _atoms(inventory[sid], inventory, module) for sid in pool_ids}
    guard_atoms = {sid: atoms[sid] | {sid} for sid in pool_ids}
    protected = set().union(*(guard_atoms[sid] for sid in anchor["source_ids"]))
    maximum = max(len(value) for value in atoms.values())
    budget = min(cfg["sensitivity_k"], len(pool))
    target, masks, solve = _completion_solver(pool, guard_atoms, protected)
    if solve(target, budget) is None:
        raise ValueError(
            "The accessible original anchor sources cannot satisfy their own coverage floor"
        )

    def select(guarded):
        selected, covered, selected_mask, rejected = [], set(), 0, []
        remaining = list(pool)
        while remaining and len(selected) < budget:
            evaluated = []
            for row in remaining:
                sid = row["source_id"]
                novel = atoms[sid] - covered
                score = (1 - cfg["coverage_weight"]) * row["score"] + cfg["coverage_weight"] * len(
                    novel
                ) / maximum
                evaluated.append((score, row, novel))
            evaluated.sort(key=lambda item: (-item[0], pool_order[item[1]["source_id"]]))
            chosen = None
            for value, row, novel in evaluated:
                sid = row["source_id"]
                uncovered = target & ~(selected_mask | masks[sid])
                completion = solve(uncovered, budget - len(selected) - 1) if guarded else ()
                if completion is None:
                    rejected.append(
                        {
                            "position": len(selected) + 1,
                            "source_id": sid,
                            "reason": "original_source_coverage_cannot_fit_remaining_budget",
                            "uncovered_original_atoms": uncovered.bit_count(),
                        }
                    )
                    continue
                chosen = {
                    **row,
                    "selection_score": value,
                    "corpus_coverage_atoms": sorted(atoms[sid]),
                    "new_corpus_coverage_atoms": sorted(novel),
                    "guard_remaining_completion": list(completion),
                }
                break
            if chosen is None:
                return (
                    [],
                    rejected,
                    "No feasible candidate under the original-source coverage floor",
                )
            sid = chosen["source_id"]
            selected.append(chosen)
            covered.update(atoms[sid])
            selected_mask |= masks[sid]
            remaining.remove(by_id[sid])
        return selected, rejected, None

    guarded = cfg["policy"] != "wide_coverage"
    unconstrained, _, _ = select(False)
    selected, rejected, fallback = select(guarded) if guarded else (unconstrained, [], None)
    if fallback:
        # This branch is explicit, source-bound and auditable. The exact solver
        # should make it unreachable for valid frozen channels. It never claims
        # a successful new ranking while silently dropping protected originals.
        selected = [
            {**by_id[sid], "guard_fallback_to_original_rrf": True} for sid in anchor["source_ids"]
        ]
    ids = [row["source_id"] for row in selected]
    returned = set().union(*(guard_atoms[sid] for sid in ids))
    retained = protected <= returned
    if guarded and not retained:
        raise ValueError("Guarded retrieval lost an original-query source footprint")
    return {
        "source_ids": ids,
        "ranked_sources": selected,
        "diagnostics": {
            "policy_version": POLICY_VERSION,
            "config": cfg,
            "module": module,
            "licence_context": "commercial",
            "candidate_source_ids": pool_ids,
            "candidate_pool_size": len(pool),
            "original_rrf_source_ids": anchor["source_ids"],
            "protected_original_source_footprint": sorted(protected),
            "guard_enabled": guarded,
            "protected_coverage_retained": retained,
            "unconstrained_source_ids": [r["source_id"] for r in unconstrained],
            "guard_rejected_candidates": rejected,
            "guard_fallback_reason": fallback,
            "set_cover_cached_states": solve.cache_info().currsize,
            "mmr_used": False,
            "reference_labels_available_to_ranker": False,
            "source_text_modified": False,
            "guard_interpretation": "Original-source coverage floor, not patient relevance, guideline applicability or clinical accuracy",
        },
    }
