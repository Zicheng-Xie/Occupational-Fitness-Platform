"""Joint five-passage allocation over measured candidates, without answer labels."""

from __future__ import annotations

import math
from itertools import combinations

from occupational_fitness_rag.evaluation.retrieval_refinement import original_footprints

POLICY = "joint_prefix_nested_original_floor_v1"


def joint_prefix(baseline, candidates, units, scores):
    """Enumerate five-source sets; retain full original floors at 1/3/5/10.

    This removes the single-replacement local-search restriction. It maximizes
    corpus-typed and total original atoms at five, never patient reference IDs.
    Equal-coverage sets retain the earlier ranking; no claim of globally optimal
    full ten-passage ranking or clinically applicable evidence is made.
    """
    if baseline.get("status") != "completed":
        raise ValueError("Joint allocation requires successful measured retrieval")
    old = baseline["source_ids"]
    pool = list(dict.fromkeys([*old, *candidates]))
    atoms = original_footprints(units, baseline["module"])
    if not old or len(old) > 10 or len(old) != len(set(old)) or any(s not in atoms for s in pool):
        raise ValueError("Invalid measured candidate inventory")
    if any(not math.isfinite(scores.get(s, 0.0)) for s in pool):
        raise ValueError("Non-finite measured relevance")
    bit = {sid: 1 << i for i, sid in enumerate(sorted(atoms))}
    masks = {sid: sum(bit[a] for a in footprint) for sid, footprint in atoms.items()}
    criteria = sum(bit[s] for s in atoms if units[s].get("criterion_type"))

    def covered(ids):
        result = 0
        for sid in ids:
            result |= masks[sid]
        return result

    floors = {k: covered(old[:k]) for k in (1, 3, 5, 10)}
    best_mask, selected, checked, improved = floors[5], old.copy(), 0, 0
    best = ((best_mask & criteria).bit_count(), best_mask.bit_count())
    size = min(5, len(pool))
    for subset in combinations(pool, size):
        checked += 1
        mask = covered(subset)
        if mask & floors[5] != floors[5]:
            continue
        objective = ((mask & criteria).bit_count(), mask.bit_count())
        if objective <= best:
            continue
        # A first passage must contain the previous first passage's footprint;
        # a three-passage subset containing it must cover the previous Top3.
        orders = []
        for first in subset:
            if masks[first] & floors[1] != floors[1]:
                continue
            rest = [s for s in subset if s != first]
            for middle in combinations(rest, min(2, len(rest))):
                prefix3 = [
                    first,
                    *sorted(middle, key=lambda s: (-scores.get(s, 0.0), pool.index(s))),
                ]
                if covered(prefix3) & floors[3] != floors[3]:
                    continue
                tail = sorted(
                    (s for s in rest if s not in middle),
                    key=lambda s: (-scores.get(s, 0.0), pool.index(s)),
                )
                prefix = [*prefix3, *tail]
                utility = sum(scores.get(s, 0.0) / math.log2(i + 2) for i, s in enumerate(prefix))
                orders.append((utility, prefix))
        if not orders:
            continue
        prefix = max(orders, key=lambda p: p[0])[1]
        # The old final five passages are a constructive feasibility witness:
        # a prefix covering old Top5 + old tail always covers old Top10.
        trial = list(dict.fromkeys([*prefix, *old[5:]]))
        if len(trial) > 10:
            raise ValueError("Constructive tail exceeded the whole-original budget")
        remainder = sorted(
            (s for s in pool if s not in trial), key=lambda s: (-scores.get(s, 0.0), pool.index(s))
        )
        trial.extend(remainder[: 10 - len(trial)])
        if any(covered(trial[:k]) & floor != floor for k, floor in floors.items()):
            raise ValueError("Joint allocation violated a nested original floor")
        best, best_mask, selected = objective, mask, trial
        improved += 1
    return {
        "source_ids": selected,
        "diagnostics": {
            "policy": POLICY,
            "five_source_combinations": checked,
            "strict_coverage_improvements": improved,
            "typed_top5_before": (floors[5] & criteria).bit_count(),
            "typed_top5_after": (best_mask & criteria).bit_count(),
            "original_top5_before": floors[5].bit_count(),
            "original_top5_after": best_mask.bit_count(),
            "coverage_floors_retained": True,
            "source_text_modified": False,
            "reference_labels_available_to_ranker": False,
            "scope": "maximum lexicographic typed/all-original Top5 coverage among this actual candidate pool with protected prefixes; old-tail constructive completion",
        },
    }
