"""Exact five-original allocation within an actually retrieved ten-source list.

This is a bounded evidence-allocation hypothesis, not clinical entailment. A
source is a typed criterion only when the frozen corpus declares criterion_type.
No patient labels, expected IDs, diagnoses or rule outcomes enter this API.
"""

from __future__ import annotations

from itertools import combinations

POLICY_VERSION = "exact_actual_top10_prefix_allocation_v6"
POLICIES = frozenset({"full_source_floor", "criterion_floor"})


def allocate_prefix(baseline, units, policy):
    """Reorder real originals, retaining the exact prior ten-source inventory.

    The full-source control preserves every original/containment atom covered
    in the prior Top5. The criterion hypothesis preserves prior typed-criterion
    coverage, then maximizes the number of such criteria covered by five actual
    originals. Both select among the same finite combinations. Ties minimize
    the sum of prior ranks and retain prior order. No passage is appended to a
    returned original or inferred from a retrieved summary.
    """
    if policy not in POLICIES:
        raise ValueError("Use a predefined exact prefix-allocation policy")
    if baseline.get("status") != "completed":
        raise ValueError("Prefix allocation requires a successful actual baseline")
    ids = baseline.get("source_ids")
    module = baseline.get("module")
    if (
        not isinstance(ids, list)
        or not ids
        or len(ids) > 10
        or any(not isinstance(s, str) or not s for s in ids)
        or len(ids) != len(set(ids))
        or any(s not in units for s in ids)
    ):
        raise ValueError("Actual baseline source inventory is empty, repeated or invalid")
    criteria = {
        sid
        for sid, unit in units.items()
        if isinstance(unit.get("criterion_type"), str) and unit["criterion_type"].strip()
    }
    footprints = {}
    for sid in ids:
        unit = units[sid]
        if (
            unit.get("source_id") != sid
            or unit.get("module") != module
            or unit.get("licence_context") not in {"commercial", "shared"}
        ):
            raise ValueError("Retrieved source violates frozen scope or identity")
        contained = unit.get("covers_source_ids", [])
        if (
            not isinstance(contained, list)
            or any(not isinstance(s, str) or not s for s in contained)
            or len(contained) != len(set(contained))
        ):
            raise ValueError("Original containment inventory must be unique")
        for target in contained:
            if (
                target not in units
                or units[target].get("module") != module
                or units[target].get("licence_context") not in {"commercial", "shared"}
            ):
                raise ValueError("Containment target crosses original-source scope")
        footprints[sid] = {sid, *contained}
    size = min(5, len(ids))
    original_prefix = set().union(*(footprints[s] for s in ids[:size]))
    criterion_floor = original_prefix & criteria
    floor = original_prefix if policy == "full_source_floor" else criterion_floor
    target = set().union(*(footprints[s] for s in ids))
    choices = []
    for indexes in combinations(range(len(ids)), size):
        covered = set().union(*(footprints[ids[i]] for i in indexes))
        if floor <= covered:
            choices.append(
                {
                    "indexes": indexes,
                    "covered": covered,
                    "criterion_count": len(covered & criteria),
                    "rank_sum": sum(i + 1 for i in indexes),
                }
            )
    if not choices:
        raise ValueError("The actual prior Top5 cannot satisfy its own source floor")
    best = min(
        choices,
        key=lambda x: (-x["criterion_count"], x["rank_sum"], x["indexes"]),
    )
    first = [ids[i] for i in best["indexes"]]
    ranked = [*first, *[sid for sid in ids if sid not in first]]
    retained = set().union(*(footprints[s] for s in ranked))
    if ranked[:size] != first or retained != target or set(ranked) != set(ids):
        raise ValueError("Exact allocation changed the actual Top10 source inventory")
    return {
        "source_ids": ranked,
        "ranked_sources": [
            {
                "source_id": sid,
                "prior_rank": ids.index(sid) + 1,
                "criterion_atoms": sorted(footprints[sid] & criteria),
                "actual_original_atoms": sorted(footprints[sid]),
            }
            for sid in ranked
        ],
        "diagnostics": {
            "policy_version": POLICY_VERSION,
            "policy": policy,
            "objective": "maximize typed-criterion coverage; tie by prior-rank sum then prior order",
            "candidate_original_ids": ids,
            "selected_prefix_ids": first,
            "prior_top5_original_atoms": sorted(original_prefix),
            "prior_top5_criterion_atoms": sorted(criterion_floor),
            "prefix_covered_criterion_atoms": sorted(best["covered"] & criteria),
            "prefix_original_atoms": sorted(best["covered"]),
            "possible_top10_criterion_atoms": sorted(target & criteria),
            "feasible_prefixes": len(choices),
            "selected_prior_rank_sum": best["rank_sum"],
            "top10_source_inventory_unchanged": True,
            "protected_coverage_retained": True,
            "criterion_floor_retained": criterion_floor <= best["covered"],
            "full_top5_source_floor_retained": original_prefix <= best["covered"],
            "source_text_modified": False,
            "mmr_used": False,
            "reference_labels_available_to_ranker": False,
            "new_model_calls": 0,
            "interpretation": "Corpus-typed criterion coverage, not patient relevance, predicate entailment or clinical accuracy",
        },
    }
