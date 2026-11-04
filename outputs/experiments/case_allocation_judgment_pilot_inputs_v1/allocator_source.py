"""Label-free allocation of whole retrieved originals across one patient's modules."""

from __future__ import annotations

import json
from itertools import combinations

from occupational_fitness_rag.evaluation.evidence_selection import select_documented_evidence


def source_record(unit):
    return {
        "source_id": unit["source_id"],
        "module": unit["module"],
        "source_text": unit["evidence_text"],
        "section": unit["section"],
        "pdf_page": unit["pdf_page"],
        "printed_page": unit["printed_page"],
    }


def evidence_bytes(sources):
    return len(
        json.dumps(sources, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode(
            "utf-8"
        )
    )


def allocate_case_evidence(patient, rankings, units, *, byte_limit=9000):
    """Select at most five originals from each module's actual Top5 union.

    Preserve the baseline packet's typed-criterion coverage, then maximize module
    coverage, the minimum within-module criterion fraction and their sum. Ties
    prefer original rank and smaller byte count. Neither reference labels nor
    rule outcomes are accepted. This is coverage allocation, not entailment.
    """
    if type(byte_limit) is not int or byte_limit < 2:
        raise ValueError("Whole-original byte budget must be an integer of at least two")
    baseline = select_documented_evidence(patient, rankings, 5)
    active = baseline["documented_modules"] or list(dict.fromkeys(patient["modules"]))
    by_module = {r["module"]: list(r["source_ids"][:5]) for r in rankings}
    ids = [sid for module in active for sid in by_module[module]]
    if len(ids) != len(set(ids)):
        raise ValueError("Actual sources must be unique across module rankings")
    criteria = {sid for sid, u in units.items() if u.get("criterion_type")}
    records, atoms, costs, ranks = {}, {}, {}, {}
    for module in active:
        for rank, sid in enumerate(by_module[module], 1):
            if sid not in units:
                raise ValueError("A ranked original is absent from the frozen corpus")
            u = units[sid]
            if (
                u["source_id"] != sid
                or u["module"] != module
                or u["licence_context"] not in {"commercial", "shared"}
            ):
                raise ValueError("Original scope or identity differs")
            contained = u.get("covers_source_ids", [])
            for target in contained:
                child = units.get(target)
                if (
                    not child
                    or child["module"] != module
                    or child["pdf_page"] != u["pdf_page"]
                    or child["licence_context"] not in {"commercial", "shared"}
                    or " ".join(child["evidence_text"].split())
                    not in " ".join(u["evidence_text"].split())
                ):
                    raise ValueError("Criterion containment lacks same-page literal proof")
            atoms[sid] = {sid, *contained} & criteria
            records[sid] = source_record(u)
            costs[sid] = evidence_bytes([records[sid]]) - 1
            ranks[sid] = rank
    old_supplied, old_bytes = [], 2
    for sid in baseline["source_ids"]:
        size = evidence_bytes([records[s] for s in [*old_supplied, sid]])
        if size <= byte_limit:
            old_supplied.append(sid)
            old_bytes = size
    floor = set().union(*(atoms[sid] for sid in old_supplied))
    totals = {m: set().union(*(atoms[s] for s in by_module[m])) for m in active}
    best, best_key, feasible = [], None, 0
    # All smaller subsets are considered: five long originals may not fit.
    for count in range(min(5, len(ids)) + 1):
        for choice in combinations(ids, count):
            size = 1 + sum(costs[s] for s in choice) if choice else 2
            if size > byte_limit:
                continue
            covered = set().union(*(atoms[s] for s in choice))
            if not floor <= covered:
                continue
            feasible += 1
            modules = {units[s]["module"] for s in choice}
            fractions = [
                len(covered & totals[m]) / len(totals[m]) if totals[m] else 1.0 for m in active
            ]
            score = (
                len(modules),
                min(fractions, default=0),
                sum(fractions),
                -sum(ranks[s] for s in choice),
                -size,
            )
            if best_key is None or score > best_key:
                best, best_key = list(choice), score
    if best_key is None:
        raise ValueError("Baseline supplied originals cannot satisfy their own criterion floor")
    selected = []
    for rank in range(5):
        for module in active:
            if rank < len(by_module[module]) and by_module[module][rank] in best:
                selected.append(by_module[module][rank])
    return {
        "source_ids": selected,
        "documented_modules": baseline["documented_modules"],
        "unmeasured_modules": baseline["unmeasured_modules"],
        "policy": {
            "name": "case_criterion_floor_exact_v1",
            "top_k": 5,
            "candidate_depth_per_module": 5,
            "byte_limit": byte_limit,
            "fallback_to_all_requested": not baseline["documented_modules"],
            "reference_labels_available": False,
            "clinical_entailment": False,
        },
        "diagnostics": {
            "candidate_ids": ids,
            "baseline_supplied_ids": old_supplied,
            "baseline_evidence_bytes": old_bytes,
            "baseline_criterion_floor": sorted(floor),
            "selected_criterion_atoms": sorted(set().union(*(atoms[s] for s in selected))),
            "evidence_bytes": evidence_bytes([records[s] for s in selected]),
            "feasible_subsets": feasible,
            "objective": list(best_key),
        },
    }
