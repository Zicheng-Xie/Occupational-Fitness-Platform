"""Transfer typed-source allocation to a frozen, actually searched Neo4j frontier.

The objective concerns corpus criterion metadata, not whether a patient meets
the criterion. Every candidate must occur in an actual native engine or graph
response. The current graph Top10 footprint and its Top5 criterion floor are
retained; reference source IDs and clinical outcomes are absent from this API.
"""

from __future__ import annotations

from itertools import combinations

from occupational_fitness_rag.evaluation.guarded_hybrid import _completion_solver
from occupational_fitness_rag.evaluation.prefix_allocation import allocate_prefix

POLICY = "native_frontier_typed_criterion_transfer_v3"
VARIANTS = ("neo4j_existing_prefix_v3", "neo4j_frontier_criterion_v3")


def footprints(ids, units, module):
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Actual source frontier must be nonempty and unique")
    result = {}
    for sid in ids:
        if sid not in units:
            raise ValueError("Native frontier contains an unknown original")
        u = units[sid]
        if (
            u.get("source_id") != sid
            or u.get("module") != module
            or u.get("licence_context") not in {"commercial", "shared"}
        ):
            raise ValueError("Native frontier source violates identity or module scope")
        covered = u.get("covers_source_ids", [])
        if (
            not isinstance(covered, list)
            or any(not isinstance(s, str) for s in covered)
            or len(covered) != len(set(covered))
        ):
            raise ValueError("Literal original containment must be a unique source list")
        text = " ".join(u["evidence_text"].split())
        for other in covered:
            if (
                other not in units
                or units[other].get("module") != module
                or units[other].get("licence_context") not in {"commercial", "shared"}
            ):
                raise ValueError("Contained original violates source scope")
            if other != sid and (
                units[other]["pdf_page"] != u["pdf_page"]
                or " ".join(units[other]["evidence_text"].split()) not in text
            ):
                raise ValueError("Containment lacks complete same-page original-text proof")
        result[sid] = {sid, *covered}
    return result


def native_frontier(trace, baseline, units):
    if (
        any(
            not isinstance(baseline.get(k), str) or not baseline[k]
            for k in ("query_id", "case_id", "module")
        )
        or baseline.get("status") != "completed"
        or trace.get("status") != "completed"
        or any(baseline.get(k) != trace.get(k) for k in ("query_id", "case_id", "module"))
    ):
        raise ValueError("Transfer requires matching successful actual graph and native conditions")
    baseline_ids = baseline.get("source_ids")
    if (
        not isinstance(baseline_ids, list)
        or not baseline_ids
        or len(baseline_ids) > 10
        or len(baseline_ids) != len(set(baseline_ids))
    ):
        raise ValueError("Actual graph baseline source inventory is invalid")
    ids, proof = [], {}
    for engine, key in (
        ("vector", "vector_records"),
        ("fulltext", "fulltext_records"),
        ("literal_graph", "graph_records"),
    ):
        rows = trace.get(key)
        if not isinstance(rows, list):
            raise ValueError("Every native frontier channel must have an actual response list")
        for i, row in enumerate(rows, 1):
            sid = row["source_id"]
            if sid not in units or row["text_sha256"] != units[sid]["text_sha256"]:
                raise ValueError("Native frontier original hash differs")
            if sid not in proof:
                ids.append(sid)
                proof[sid] = []
            proof[sid].append({"engine": engine, "actual_record_position": i})
    if not set(baseline_ids) <= set(ids):
        raise ValueError("Graph baseline is not contained in the actual native response frontier")
    native_ids = [r["source_id"] for r in trace.get("native_rrf", [])]
    if (
        not native_ids
        or len(native_ids) != len(set(native_ids))
        or any(
            sid not in proof or not any(p["engine"] in {"vector", "fulltext"} for p in proof[sid])
            for sid in native_ids
        )
    ):
        raise ValueError("Native RRF prior is not supported by actual engine response IDs")
    ordered = [*baseline_ids, *[sid for sid in ids if sid not in baseline_ids]]
    return ordered, proof, footprints(ordered, units, baseline["module"])


def exact_prefix_with_floor(ids, covered, criteria, floor):
    size = min(5, len(ids))
    options = []
    for indexes in combinations(range(len(ids)), size):
        atoms = set().union(*(covered[ids[i]] for i in indexes))
        if floor <= atoms:
            options.append((indexes, atoms))
    if not options:
        raise ValueError("No real five-original prefix preserves the earlier criterion floor")
    indexes, atoms = min(
        options, key=lambda pair: (-len(pair[1] & criteria), sum(i + 1 for i in pair[0]), pair[0])
    )
    prefix = [ids[i] for i in indexes]
    return [*prefix, *[s for s in ids if s not in prefix]], atoms, len(options)


def transfer(variant, baseline, trace, units):
    if variant not in VARIANTS:
        raise ValueError("Unknown prespecified Neo4j criterion-transfer hypothesis")
    ids, proof, covered = native_frontier(trace, baseline, units)
    original = baseline["source_ids"]
    criteria = {
        s
        for s, u in units.items()
        if isinstance(u.get("criterion_type"), str) and u["criterion_type"].strip()
    }
    old_source_floor = set().union(*(covered[s] for s in original))
    old_criterion_floor = set().union(*(covered[s] for s in original[:5])) & criteria
    if variant == VARIANTS[0]:
        result = allocate_prefix(baseline, units, "criterion_floor")
        result["diagnostics"].update(
            transfer_policy=POLICY,
            native_frontier_source_ids=ids,
            actual_native_candidate_proof=proof,
            new_native_calls=0,
            old_top10_source_footprint=sorted(old_source_floor),
        )
        return result
    pool = [{"source_id": sid} for sid in ids]
    target, masks, solve = _completion_solver(pool, covered, old_source_floor)
    budget = min(10, len(pool))
    if solve(target, budget) is None:
        raise ValueError("The actual source frontier cannot preserve the actual graph footprint")
    native_order = {r["source_id"]: i + 1 for i, r in enumerate(trace["native_rrf"])}
    baseline_order = {s: i + 1 for i, s in enumerate(original)}
    prior = {s: baseline_order.get(s, 10 + native_order.get(s, len(ids))) for s in ids}
    remaining, selected, selected_mask, criterion_covered, rejected = list(ids), [], 0, set(), []
    while remaining and len(selected) < budget:
        candidates = sorted(
            remaining,
            key=lambda sid: (
                -len((covered[sid] & criteria) - criterion_covered),
                prior[sid],
                ids.index(sid),
            ),
        )
        chosen = None
        for sid in candidates:
            completion = solve(target & ~(selected_mask | masks[sid]), budget - len(selected) - 1)
            if completion is None:
                rejected.append({"position": len(selected) + 1, "source_id": sid})
                continue
            chosen = sid
            break
        if chosen is None:
            raise ValueError("Typed criterion selection cannot retain the graph source floor")
        selected.append(chosen)
        selected_mask |= masks[chosen]
        criterion_covered.update(covered[chosen] & criteria)
        remaining.remove(chosen)
    result_ids, prefix_atoms, combinations_checked = exact_prefix_with_floor(
        selected, covered, criteria, old_criterion_floor
    )
    returned = set().union(*(covered[s] for s in result_ids))
    if not old_source_floor <= returned or not old_criterion_floor <= prefix_atoms:
        raise ValueError("Criterion transfer lost a protected original source or typed criterion")
    return {
        "source_ids": result_ids,
        "ranked_sources": [
            {
                "source_id": sid,
                "prior_graph_rank": baseline_order.get(sid),
                "native_rrf_rank": native_order.get(sid),
                "actual_native_candidate_proof": proof[sid],
                "criterion_atoms": sorted(covered[sid] & criteria),
            }
            for sid in result_ids
        ],
        "diagnostics": {
            "policy_version": POLICY,
            "native_frontier_source_ids": ids,
            "actual_native_candidate_proof": proof,
            "wide_top10_before_prefix": selected,
            "wide_selection_objective": "maximum newly covered corpus-typed criteria per feasible step; ties actual graph/native prior rank",
            "prefix_objective": "exact maximum typed criteria; preserve old graph Top5 criterion floor; tie by wide prior rank sum",
            "old_top10_source_footprint": sorted(old_source_floor),
            "old_top5_criterion_floor": sorted(old_criterion_floor),
            "selected_top5_criterion_atoms": sorted(prefix_atoms & criteria),
            "top10_criterion_atoms": sorted(returned & criteria),
            "top10_source_floor_retained": True,
            "top5_criterion_floor_retained": True,
            "guard_rejected_candidates": rejected,
            "exact_prefix_combinations": combinations_checked,
            "candidate_inventory_contains_only_actual_native_responses": True,
            "new_native_calls": 0,
            "new_model_calls": 0,
            "reference_labels_available_to_ranker": False,
            "clinical_applicability_verified": False,
            "source_text_modified": False,
        },
    }
