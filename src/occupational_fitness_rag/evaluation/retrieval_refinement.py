"""Experimental literal-facet fusion and protected original-passage allocation.

These functions never accept engineering answers or rule outcomes. They operate
on real ranked candidates and verified, same-page literal containment edges.
Production retrieval and every earlier experimental policy remain unchanged.
"""

from __future__ import annotations

import math
import re

from occupational_fitness_rag.case_intake.narrative_context import MODULE_TERMS

POLICY = "literal_facets_nested_original_coverage_v1"
CHECKPOINTS = (1, 3, 5, 10)


def literal_facets(note, module, maximum=6):
    """Select complete sentences, retaining subject, uncertainty and negation.

    Retrieval context is not a verified fact. In particular, family history and
    negated symptoms remain verbatim search contexts and cannot trigger a rule.
    """
    if module not in MODULE_TERMS or type(maximum) is not int or not 1 <= maximum <= 8:
        raise ValueError("Invalid module or literal facet budget")
    result = []
    for match in re.finditer(r"[^\n]+", note):
        for sentence in re.finditer(r".+?(?:[.!?](?=\s|$)|$)", match[0]):
            quote = sentence[0].strip()
            if not quote or not re.search(MODULE_TERMS[module], quote, re.I):
                continue
            if quote in result:
                continue
            result.append(quote)
    # Spread the fixed budget over the entire note, rather than letting an
    # opening history paragraph consume every search view.
    if len(result) > maximum:
        result = (
            [result[i * (len(result) - 1) // (maximum - 1)] for i in range(maximum)]
            if maximum > 1
            else result[:1]
        )
    if any(quote not in note for quote in result):
        raise ValueError("A facet is not an exact source substring")
    return result


def original_footprints(units, module):
    """Validate literal full-passage containment; metadata alone is insufficient."""
    eligible = {
        sid: u
        for sid, u in units.items()
        if u["module"] == module and u["licence_context"] in {"commercial", "shared"}
    }
    atoms = {}
    for sid, unit in eligible.items():
        if unit["source_id"] != sid:
            raise ValueError("Original source identity differs")
        covered = unit.get("covers_source_ids", [])
        if len(covered) != len(set(covered)):
            raise ValueError("Repeated containment target")
        for child in covered:
            if child not in eligible or eligible[child]["pdf_page"] != unit["pdf_page"]:
                raise ValueError("Containment crosses original scope or page")
            if " ".join(eligible[child]["evidence_text"].split()) not in " ".join(
                unit["evidence_text"].split()
            ):
                raise ValueError("Containment is not a complete literal original")
        atoms[sid] = {sid, *covered}
    return atoms


def fuse_views(channels, anchor_weight=0.65, rrf_k=60):
    """Keep engine ranks separate and cap the total weight of extra views.

    Repeating a sentence/channel cannot amplify its contribution. The original
    method is one anchor; each added sentence has equal share of the remaining
    weight, with BM25 and vector each contributing half of that sentence's RRF.
    """
    if not 0 <= anchor_weight <= 1 or type(rrf_k) is not int or rrf_k < 1:
        raise ValueError("Invalid fixed RRF configuration")
    unique = {}
    for channel in channels:
        ids = channel["source_ids"]
        if len(ids) != len(set(ids)):
            raise ValueError("A ranking channel contains duplicate sources")
        key = channel["view"], channel["engine"]
        if key in unique and unique[key]["source_ids"] != ids:
            raise ValueError("Same query/engine view returned conflicting source orders")
        unique[key] = channel
    views = {c["view"] for c in unique.values() if c["view"] != "anchor"}
    scores, proof = {}, {}
    for c in unique.values():
        peers = sum(d["view"] == c["view"] for d in unique.values())
        weight = (
            anchor_weight if c["view"] == "anchor" else (1 - anchor_weight) / max(1, len(views))
        )
        if not views:
            weight = 1.0
        weight /= peers
        for rank, sid in enumerate(c["source_ids"], 1):
            contribution = weight * (rrf_k + 1) / (rrf_k + rank)
            scores[sid] = scores.get(sid, 0.0) + contribution
            proof.setdefault(sid, []).append(
                {
                    "view": c["view"],
                    "engine": c["engine"],
                    "rank": rank,
                    "contribution": contribution,
                }
            )
    return scores, proof


def refine_ranking(baseline, candidates, units, scores, *, max_steps=32):
    """Apply best-improvement source replacements under nested coverage floors.

    Every proposed replacement or swap must retain the earlier *full original*
    footprint at ranks 1, 3, 5 and 10, not merely typed criteria. The bounded
    search maximizes typed and total source coverage at 5 and 10, then measured
    retrieval relevance. It is a deterministic local optimum, not an exact global
    optimum or a proof of patient applicability. Wider originals are charged
    their actual bytes by the separate, unchanged evidence-budget evaluation.
    """
    if baseline.get("status") != "completed":
        raise ValueError("A failed native condition cannot be silently replaced")
    module = baseline["module"]
    atoms = original_footprints(units, module)
    old = list(baseline["source_ids"])
    pool = list(dict.fromkeys([*old, *candidates]))
    if not old or len(old) > 10 or len(old) != len(set(old)) or any(s not in atoms for s in pool):
        raise ValueError("Invalid retrieved source inventory")
    if any(not math.isfinite(scores.get(s, 0.0)) for s in pool):
        raise ValueError("Non-finite measured relevance")
    bit = {sid: 1 << i for i, sid in enumerate(sorted(atoms))}
    masks = {sid: sum(bit[a] for a in footprint) for sid, footprint in atoms.items()}
    criterion_mask = sum(bit[s] for s in atoms if units[s].get("criterion_type"))

    def footprint(ids):
        mask = 0
        for sid in ids:
            mask |= masks[sid]
        return mask

    floors = {k: footprint(old[:k]) for k in CHECKPOINTS}
    order = {sid: i for i, sid in enumerate(pool)}

    def valid(ids):
        return all(footprint(ids[:k]) & required == required for k, required in floors.items())

    def objective(ids):
        first, all_sources = footprint(ids[:5]), footprint(ids[:10])
        relevance = sum(scores.get(s, 0.0) / math.log2(i + 2) for i, s in enumerate(ids))
        # Typed metadata is a corpus descriptor; no patient/reference label
        # determines these counts. Original IDs are counted separately.
        return (
            (first & criterion_mask).bit_count(),
            first.bit_count(),
            (all_sources & criterion_mask).bit_count(),
            all_sources.bit_count(),
            round(relevance, 12),
        )

    current = old.copy()
    events = []
    for step in range(max_steps):
        value = objective(current)
        best, best_value, event = current, value, None
        for position in range(min(10, len(pool))):
            for sid in pool:
                trial = current.copy()
                if position == len(trial):
                    if sid in trial:
                        continue
                    trial.append(sid)
                elif position < len(trial):
                    if trial[position] == sid:
                        continue
                    if sid in trial:
                        previous = trial.index(sid)
                        trial[position], trial[previous] = trial[previous], trial[position]
                    else:
                        trial[position] = sid
                else:
                    continue
                if not valid(trial):
                    continue
                candidate_value = objective(trial)
                if candidate_value > best_value or (
                    candidate_value == best_value
                    and candidate_value > value
                    and tuple(order[s] for s in trial) < tuple(order[s] for s in best)
                ):
                    best, best_value = trial, candidate_value
                    event = {
                        "step": step + 1,
                        "position": position + 1,
                        "source_id": sid,
                        "objective": list(candidate_value),
                    }
        if event is None:
            break
        current = best
        events.append(event)
    if not valid(current) or len(current) != len(set(current)):
        raise ValueError("Protected allocation violated a source floor")
    return {
        "source_ids": current,
        "diagnostics": {
            "policy": POLICY,
            "candidate_source_ids": pool,
            "protected_original_footprints": {
                str(k): sorted(a for a, b in bit.items() if b & mask) for k, mask in floors.items()
            },
            "coverage_floors_retained": True,
            "optimization_events": events,
            "iterations": len(events),
            "iteration_limit_reached": len(events) == max_steps,
            "objective_before": list(objective(old)),
            "objective_after": list(objective(current)),
            "reference_labels_available_to_ranker": False,
            "source_text_modified": False,
            "mmr_used": False,
            "global_optimum_claimed": False,
        },
    }


def literal_parent_closure(ids, atoms):
    """Add only same-page parents containing an already retrieved full original."""
    selected = set(ids)
    added = [sid for sid, footprint in atoms.items() if (footprint - {sid}) & selected]
    return list(dict.fromkeys([*ids, *added]))
