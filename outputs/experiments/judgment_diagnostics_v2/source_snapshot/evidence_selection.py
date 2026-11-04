"""Experimental evidence allocation using documented fact presence only.

This helper does not retrieve, interpret a diagnosis, or change the requested
assessment scope. Original-passage byte limits remain the caller's responsibility.
"""

from collections.abc import Mapping, Sequence
from typing import Any

MODULES = frozenset({"hypertension", "vision", "hearing", "blackout", "diabetes"})


def _documented_module(field: str, fact: Any):
    if not isinstance(fact, Mapping) or fact.get("value") is None:
        return None
    if fact.get("status", "present") != "present":
        return None
    prefix = field.split(".", 1)[0]
    return "hypertension" if prefix == "cardiovascular" else prefix


def select_documented_evidence(payload, rankings, top_k=5):
    """Allocate existing ranked source IDs without consulting reference labels.

    ``rankings`` contains one row per requested module, with ``module`` and
    ``source_ids``. Optional status must be ``completed``. When documented facts
    exist, only those modules receive evidence slots. Otherwise every requested
    module participates. Neither case asserts that an unmeasured module is normal.
    False and zero are documented values, not missing values. The function never
    mutates ``payload`` or the within-module rankings.
    """
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 0:
        raise ValueError("top_k must be a non-negative integer")
    requested = list(dict.fromkeys(payload["modules"]))
    if set(requested) - MODULES:
        raise ValueError("Unknown requested assessment module")
    documented = {
        _documented_module(field, fact) for field, fact in payload["verified_patient_facts"].items()
    }
    documented_modules = [module for module in requested if module in documented]
    unmeasured_modules = [module for module in requested if module not in documented]
    active = documented_modules or requested
    ordered = {}
    for row in rankings:
        module = row["module"]
        if module not in requested:
            raise ValueError("Ranking module is outside the requested assessment scope")
        if module in ordered:
            raise ValueError("Provide exactly one ranking per module")
        if row.get("status", "completed") != "completed":
            raise ValueError("Failed retrieval cannot be used as a successful ranking")
        ids = row["source_ids"]
        if isinstance(ids, (str, bytes)) or not isinstance(ids, Sequence):
            raise ValueError("Ranked source IDs must be a sequence")
        if any(not isinstance(source_id, str) or not source_id for source_id in ids):
            raise ValueError("Ranked source IDs must be non-empty strings")
        ordered[module] = ids
    if set(active) - ordered.keys():
        raise ValueError("An active module ranking is missing")
    selected, seen = [], set()
    for rank in range(max((len(ordered[module]) for module in active), default=0)):
        for module in active:
            ids = ordered[module]
            if rank >= len(ids) or ids[rank] in seen:
                continue
            if len(selected) == top_k:
                break
            selected.append(ids[rank])
            seen.add(ids[rank])
        if len(selected) == top_k:
            break
    fallback = not documented_modules
    return {
        "source_ids": selected,
        "documented_modules": documented_modules,
        "unmeasured_modules": unmeasured_modules,
        "policy": {
            "name": "documented_modules_round_robin_v1",
            "fallback_to_all_requested": fallback,
            "rationale": (
                "No requested module has a documented fact; allocate across all requested modules."
                if fallback
                else "Allocate only across requested modules with documented facts; unmeasured modules remain unresolved."
            ),
        },
    }
