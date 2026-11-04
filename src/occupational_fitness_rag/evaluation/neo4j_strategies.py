"""Original-query fusion and bounded literal graph support over real Neo4j hits.

This ranker receives actual retrieval records and complete original passages.
It has no patient reference answers, expected sources or outcome labels. Graph
relations are source-navigation facts, not proof of clinical applicability.
"""

from __future__ import annotations

import math
import re

from occupational_fitness_rag.evaluation.anchored_hybrid import _atoms
from occupational_fitness_rag.evaluation.guarded_hybrid import _completion_solver

POLICY = "native_rrf_bounded_literal_graph_original_coverage_v2"
VARIANTS = (
    "neo4j_native_rrf_v2",
    "neo4j_anchor_graph_v2",
    "neo4j_anchor_graph_guard_v2",
)
PATH_WEIGHTS = {"literal_source_containment": 0.95, "literal_explicit_section_reference": 0.85}


def validate_ids(ids, units, module, maximum=60):
    if not ids or len(ids) > maximum or len(ids) != len(set(ids)):
        raise ValueError("Real retrieval requires nonempty unique source IDs within budget")
    if any(
        sid not in units
        or units[sid]["module"] != module
        or units[sid]["licence_context"] not in {"commercial", "shared"}
        for sid in ids
    ):
        raise ValueError("An original source is unknown or outside the frozen module scope")


def native_rrf(vector, fulltext, units, module, k=60):
    """Fuse native per-engine ranks; do not compare raw score scales."""
    if type(k) is not int or k < 1:
        raise ValueError("RRF rank constant must be a positive integer")
    scores, provenance, insertion = {}, {}, {}
    for engine, rows in (("vector", vector), ("fulltext", fulltext)):
        ids = [r["source_id"] for r in rows]
        if ids:
            validate_ids(ids, units, module)
        for rank, row in enumerate(rows, 1):
            sid, raw = row["source_id"], row["score"]
            if (
                isinstance(raw, bool)
                or not isinstance(raw, (int, float))
                or not math.isfinite(raw)
                or row["text_sha256"] != units[sid]["text_sha256"]
            ):
                raise ValueError("Native score or original text fingerprint differs")
            insertion.setdefault(sid, len(insertion))
            scores[sid] = scores.get(sid, 0) + 1 / (k + rank)
            provenance.setdefault(sid, []).append(
                {
                    "engine": engine,
                    "rank": rank,
                    "raw_score": raw,
                    "rrf_contribution": 1 / (k + rank),
                }
            )
    if not scores:
        raise ValueError("Both native retrieval engines returned empty results")
    ordered = sorted(scores, key=lambda sid: (-scores[sid], insertion[sid]))
    return [
        {"source_id": sid, "score": scores[sid], "native_engine_ranks": provenance[sid]}
        for sid in ordered
    ]


def rank(variant, anchor_ids, native_rows, graph_rows, units, module):
    """Apply one of three prespecified policies to the same actual search evidence."""
    if variant not in VARIANTS:
        raise ValueError("Unknown Neo4j strategy variant")
    validate_ids(anchor_ids, units, module, 20)
    native_ids = [r["source_id"] for r in native_rows]
    validate_ids(native_ids, units, module)
    if variant == VARIANTS[0]:
        chosen = native_rows[:10]
        return {
            "source_ids": [r["source_id"] for r in chosen],
            "ranked_sources": chosen,
            "diagnostics": {"policy": POLICY, "graph_used": False, "guard_enabled": False},
        }
    anchor_rank = {sid: i + 1 for i, sid in enumerate(anchor_ids)}
    native_rank = {sid: i + 1 for i, sid in enumerate(native_ids)}
    ids = list(anchor_ids)
    support = {sid: 61 / (60 + anchor_rank[sid]) for sid in anchor_ids}
    paths = {sid: [] for sid in ids}
    for row in graph_rows:
        sid, seed, path = row["source_id"], row["seed_source_id"], row["graph_path"]
        validate_ids([sid], units, module)
        if seed not in anchor_rank or path not in PATH_WEIGHTS:
            raise ValueError(
                "Graph path is not a retrieved original-query seed or allowed literal edge"
            )
        if row["text_sha256"] != units[sid]["text_sha256"]:
            raise ValueError("Graph path original fingerprint differs")
        source, target_unit = units[seed], units[sid]
        if path == "literal_source_containment":
            source_text = " ".join(source["evidence_text"].split())
            target_text = " ".join(target_unit["evidence_text"].split())
            metadata_edge = sid in source.get("covers_source_ids", []) or seed in target_unit.get(
                "covers_source_ids", []
            )
            if (
                source["pdf_page"] != target_unit["pdf_page"]
                or not metadata_edge
                or not (source_text in target_text or target_text in source_text)
            ):
                raise ValueError(
                    "Graph containment is not a complete same-page original-text relation"
                )
        else:
            literal_sections = [
                section
                for section in source.get("explicit_section_references", [])
                if re.search(
                    r"(?<![\d.])" + re.escape(section) + r"(?!\d|\.\d)", source["evidence_text"]
                )
                and (
                    target_unit["section"] == section
                    or target_unit["section"].startswith(section + ".")
                )
            ]
            if sid not in source.get("cross_references", []) or not literal_sections:
                raise ValueError("Graph reference is not explicit in the original source")
        expected = PATH_WEIGHTS[path] * 61 / (60 + anchor_rank[seed])
        if sid not in ids:
            ids.append(sid)
            paths[sid] = []
        support[sid] = max(support.get(sid, 0), expected)
        paths[sid].append({**row, "derived_graph_support": expected})
    rows = []
    for sid in ids:
        # Outside the original RRF Top20, reuse the actual same-query native
        # engine rank if present. A graph-only source gets an explicit zero
        # retrieval prior, not an invented anchor rank or expected-source fill.
        measured_rank = anchor_rank.get(sid, native_rank.get(sid))
        prior = 61 / (60 + measured_rank) if measured_rank is not None else 0.0
        rows.append(
            {
                "source_id": sid,
                "score": 0.8 * prior + 0.2 * support[sid],
                "original_query_prior": prior,
                "original_query_rank": anchor_rank.get(sid),
                "retrieval_prior_kind": "original_rrf_rank"
                if sid in anchor_rank
                else "actual_native_rrf_rank"
                if sid in native_rank
                else "graph_only_zero",
                "native_rrf_rank": native_rank.get(sid),
                "literal_graph_support": support[sid],
                "graph_paths": paths[sid],
            }
        )
    order = {sid: i for i, sid in enumerate(ids)}
    rows.sort(key=lambda row: (-row["score"], order[row["source_id"]]))
    pool = rows[:30]
    if variant == VARIANTS[1]:
        selected = pool[:10]
        return {
            "source_ids": [r["source_id"] for r in selected],
            "ranked_sources": selected,
            "diagnostics": {
                "policy": POLICY,
                "graph_used": True,
                "guard_enabled": False,
                "candidate_source_ids": [r["source_id"] for r in pool],
                "reference_labels_available": False,
            },
        }
    # Guarantee accessible original-query Top10 are not lost through candidate
    # truncation; this is a retrieval footprint, never a reference answer set.
    protected_ids = anchor_ids[:10]
    by_id = {r["source_id"]: r for r in rows}
    missing = [sid for sid in protected_ids if sid not in {r["source_id"] for r in pool}]
    if missing:
        protected_set = set(protected_ids)
        removable = [r for r in reversed(pool) if r["source_id"] not in protected_set]
        for sid, old in zip(missing, removable, strict=False):
            pool.remove(old)
            pool.append(by_id[sid])
    atoms = {r["source_id"]: _atoms(units[r["source_id"]], units, module) for r in pool}
    guard_atoms = {sid: covered | {sid} for sid, covered in atoms.items()}
    protected = set().union(*(guard_atoms[sid] for sid in protected_ids))
    target, masks, solve = _completion_solver(pool, guard_atoms, protected)
    budget = min(10, len(pool))
    if solve(target, budget) is None:
        raise ValueError("Accessible originals cannot preserve their own retrieved footprint")
    maximum = max(map(len, atoms.values()))
    selected, selected_mask, covered, rejected = [], 0, set(), []
    remaining = list(pool)
    while remaining and len(selected) < budget:
        evaluated = sorted(
            (
                (0.85 * r["score"] + 0.15 * len(atoms[r["source_id"]] - covered) / maximum, r)
                for r in remaining
            ),
            key=lambda pair: (-pair[0], order[pair[1]["source_id"]]),
        )
        chosen = None
        for score, row in evaluated:
            sid = row["source_id"]
            completion = solve(target & ~(selected_mask | masks[sid]), budget - len(selected) - 1)
            if completion is None:
                rejected.append({"position": len(selected) + 1, "source_id": sid})
                continue
            chosen = {**row, "selection_score": score, "remaining_cover": list(completion)}
            break
        if chosen is None:
            raise ValueError("No graph-supported selection can preserve the original footprint")
        sid = chosen["source_id"]
        selected.append(chosen)
        selected_mask |= masks[sid]
        covered.update(atoms[sid])
        remaining = [r for r in remaining if r["source_id"] != sid]
    returned = set().union(*(guard_atoms[r["source_id"]] for r in selected))
    if not protected <= returned:
        raise ValueError("Selected originals lost the actual anchor Top10 footprint")
    return {
        "source_ids": [r["source_id"] for r in selected],
        "ranked_sources": selected,
        "diagnostics": {
            "policy": POLICY,
            "graph_used": True,
            "guard_enabled": True,
            "protected_original_query_source_ids": protected_ids,
            "protected_original_source_footprint": sorted(protected),
            "protected_coverage_retained": True,
            "guard_rejected_candidates": rejected,
            "candidate_source_ids": [r["source_id"] for r in pool],
            "formula": "0.85*(0.8*original_query_prior+0.2*literal_graph_support)+0.15*novel_original_atoms/M",
            "reference_labels_available": False,
            "mmr_used": False,
            "clinical_predicate_applicability_verified": False,
        },
    }
