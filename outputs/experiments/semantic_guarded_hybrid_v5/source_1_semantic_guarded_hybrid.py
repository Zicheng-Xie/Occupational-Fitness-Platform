"""Blend a frozen native query/passage score with protected no-MMR retrieval.

The source-coverage target is the earlier actual Top10 footprint, never a
patient's expected answer. Native sigmoid scores are relevance measurements,
not medical truth. Two prespecified semantic weights are evaluated separately.
"""

from __future__ import annotations

import math

from occupational_fitness_rag.evaluation.anchored_hybrid import _atoms
from occupational_fitness_rag.evaluation.guarded_hybrid import _completion_solver, _inventory

POLICY_VERSION = "native_semantic_blend_v3_footprint_floor_v5"
SEMANTIC_WEIGHTS = frozenset({0.25, 0.50})


def rank_semantic(v3_row, native_row, units, semantic_weight):
    """Select ten real originals while retaining the entire earlier footprint."""
    if isinstance(semantic_weight, bool) or semantic_weight not in SEMANTIC_WEIGHTS:
        raise ValueError("Use one of the two prespecified semantic weights")
    units = _inventory(units)
    if (
        v3_row.get("status") != "completed"
        or native_row.get("status") != "completed"
        or any(v3_row.get(k) != native_row.get(k) for k in ("query_id", "case_id", "module"))
    ):
        raise ValueError("Require completed matching real retrieval/native conditions")
    baseline = v3_row["source_ids"]
    trace = native_row["candidate_trace"]
    native_ids = [r["source_id"] for r in trace]
    if (
        not baseline
        or len(baseline) > 10
        or len(baseline) != len(set(baseline))
        or not native_ids
        or len(native_ids) > 20
        or len(native_ids) != len(set(native_ids))
    ):
        raise ValueError("Source inventories must be nonempty unique and within frozen budgets")
    native_scores = {}
    for row in trace:
        score = row["native_score"]
        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not math.isfinite(score)
            or not 0 <= score <= 1
        ):
            raise ValueError("The actual native sigmoid score must be finite in [0,1]")
        native_scores[row["source_id"]] = score
    ids = list(dict.fromkeys([*baseline, *native_ids]))
    module = v3_row["module"]
    if any(
        sid not in units
        or units[sid].get("module") != module
        or units[sid].get("licence_context") not in {"commercial", "shared"}
        for sid in ids
    ):
        raise ValueError("Candidate source is unknown or outside the frozen commercial module")
    v3_ranks = {sid: i + 1 for i, sid in enumerate(baseline)}
    anchor_ranks = {sid: i + 1 for i, sid in enumerate(native_ids)}
    atoms = {sid: _atoms(units[sid], units, module) for sid in ids}
    guard_atoms = {sid: atoms[sid] | {sid} for sid in ids}
    protected = set().union(*(guard_atoms[sid] for sid in baseline))
    maximum = max(len(a) for a in atoms.values())
    pool = []
    for sid in ids:
        rank = v3_ranks.get(sid, anchor_ranks.get(sid))
        prior = 61 / (60 + rank)
        native = native_scores.get(sid, 0.0)
        pool.append(
            {
                "source_id": sid,
                "score": (1 - semantic_weight) * prior + semantic_weight * native,
                "prior_relevance": prior,
                "prior_rank": rank,
                "prior_kind": "v3_top10_rank" if sid in v3_ranks else "original_rrf_top20_rank",
                "native_sigmoid": native,
                "native_score_missing": sid not in native_scores,
                "native_missing_policy": "explicit_zero_without_native_call"
                if sid not in native_scores
                else None,
            }
        )
    budget = min(10, len(pool))
    target, masks, solve = _completion_solver(pool, guard_atoms, protected)
    if solve(target, budget) is None:
        raise ValueError("Accessible baseline sources cannot satisfy their own footprint")
    selected, covered, selected_mask, rejected = [], set(), 0, []
    remaining = list(pool)
    order = {sid: i for i, sid in enumerate(ids)}
    while remaining and len(selected) < budget:
        evaluated = [
            (
                0.85 * row["score"] + 0.15 * len(atoms[row["source_id"]] - covered) / maximum,
                row,
            )
            for row in remaining
        ]
        evaluated.sort(key=lambda p: (-p[0], order[p[1]["source_id"]]))
        chosen = None
        for value, row in evaluated:
            sid = row["source_id"]
            uncovered = target & ~(selected_mask | masks[sid])
            completion = solve(uncovered, budget - len(selected) - 1)
            if completion is None:
                rejected.append(
                    {
                        "position": len(selected) + 1,
                        "source_id": sid,
                        "reason": "v3_source_footprint_cannot_fit_remaining_budget",
                    }
                )
                continue
            chosen = {
                **row,
                "selection_score": value,
                "corpus_coverage_atoms": sorted(atoms[sid]),
                "new_corpus_coverage_atoms": sorted(atoms[sid] - covered),
                "guard_remaining_completion": list(completion),
            }
            break
        if chosen is None:
            raise ValueError("Exact coverage solver yielded no feasible semantic selection")
        sid = chosen["source_id"]
        selected.append(chosen)
        covered.update(atoms[sid])
        selected_mask |= masks[sid]
        remaining = [r for r in remaining if r["source_id"] != sid]
    result = [r["source_id"] for r in selected]
    returned = set().union(*(guard_atoms[sid] for sid in result))
    if not protected <= returned:
        raise ValueError("Semantic selection lost the actual v3 original-source footprint")
    return {
        "source_ids": result,
        "ranked_sources": selected,
        "diagnostics": {
            "policy_version": POLICY_VERSION,
            "semantic_weight": semantic_weight,
            "formula": "0.85*((1-w)*61/(60+prior_rank)+w*native_sigmoid)+0.15*novel_corpus_atoms/M",
            "module": module,
            "licence_context": "commercial",
            "candidate_source_ids": ids,
            "candidate_pool_size": len(ids),
            "native_candidate_source_ids_original_rrf_order": native_ids,
            "native_missing_source_ids": [sid for sid in ids if sid not in native_scores],
            "protected_v3_source_ids": list(baseline),
            "protected_original_source_footprint": sorted(protected),
            "protected_coverage_retained": True,
            "guard_enabled": True,
            "guard_rejected_candidates": rejected,
            "guard_fallback_reason": None,
            "set_cover_cached_states": solve.cache_info().currsize,
            "candidate_score_trace": pool,
            "mmr_used": False,
            "reference_labels_available_to_ranker": False,
            "source_text_modified": False,
            "actual_new_native_calls": 0,
            "guard_interpretation": "Retained original-source coverage, not clinical applicability or accuracy",
        },
    }
