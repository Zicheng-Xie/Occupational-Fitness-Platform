"""Verify typed-allocation transfer uses only actual, source-bound native responses."""

from copy import deepcopy

import pytest

from occupational_fitness_rag.evaluation.neo4j_criterion_transfer import VARIANTS, transfer
from occupational_fitness_rag.provenance import sha256_bytes


def fixture():
    units = {}
    for i in range(12):
        sid, text = f"s{i}", f"Complete original source {i}."
        units[sid] = {
            "source_id": sid,
            "evidence_text": text,
            "text_sha256": sha256_bytes(text.encode()),
            "pdf_page": 220,
            "module": "vision",
            "licence_context": "commercial",
            "covers_source_ids": [],
        }
        if i in (0, 6, 7, 8, 9, 11):
            units[sid]["criterion_type"] = "unconditional"
    units["s10"]["evidence_text"] = "\n".join(units[f"s{i}"]["evidence_text"] for i in (6, 7, 8))
    units["s10"]["text_sha256"] = sha256_bytes(units["s10"]["evidence_text"].encode())
    units["s10"]["covers_source_ids"] = ["s6", "s7", "s8"]
    baseline = {
        "query_id": "actual-query",
        "case_id": "synthetic-case",
        "module": "vision",
        "status": "completed",
        "source_ids": list(units)[:10],
    }
    trace = {
        "query_id": "actual-query",
        "case_id": "synthetic-case",
        "module": "vision",
        "status": "completed",
        "vector_records": [{"source_id": s, "text_sha256": units[s]["text_sha256"]} for s in units],
        "fulltext_records": [],
        "graph_records": [],
        "native_rrf": [{"source_id": s} for s in units],
    }
    return baseline, trace, units


def test_control_reuses_exact_top10_inventory_and_shared_prefix_objective():
    base, trace, units = fixture()
    before = deepcopy((base, trace, units))
    result = transfer(VARIANTS[0], base, trace, units)
    assert set(result["source_ids"]) == set(base["source_ids"])
    assert result["source_ids"][:5] == ["s0", "s6", "s7", "s8", "s9"]
    assert result["diagnostics"]["new_native_calls"] == 0
    assert before == (base, trace, units)


def test_wide_typed_criteria_retain_actual_source_and_prior_criterion_floors():
    base, trace, units = fixture()
    result = transfer(VARIANTS[1], base, trace, units)
    all_atoms, prefix_atoms = set(), set()
    for rank, sid in enumerate(result["source_ids"]):
        atoms = {sid, *units[sid]["covers_source_ids"]}
        all_atoms.update(atoms)
        if rank < 5:
            prefix_atoms.update(atoms)
    assert set(base["source_ids"]) <= all_atoms
    assert "s0" in prefix_atoms
    assert {"s0", "s6", "s7", "s8", "s9", "s11"} <= prefix_atoms
    assert len(result["source_ids"]) == len(set(result["source_ids"])) == 10
    assert set(result["source_ids"]) <= {r["source_id"] for r in trace["vector_records"]}
    assert result["diagnostics"]["top10_source_floor_retained"]
    assert result["diagnostics"]["top5_criterion_floor_retained"]


@pytest.mark.parametrize(
    "change", ["unknown", "hash", "scope", "baseline_missing", "query", "unmeasured_prior"]
)
def test_native_frontier_identity_and_provenance_are_required(change):
    base, trace, units = fixture()
    if change == "unknown":
        trace["vector_records"][0]["source_id"] = "not-a-retrieved-original"
    elif change == "hash":
        trace["vector_records"][0]["text_sha256"] = "changed"
    elif change == "scope":
        units["s11"]["module"] = "diabetes"
    elif change == "baseline_missing":
        trace["vector_records"] = trace["vector_records"][1:]
    elif change == "query":
        trace["query_id"] = "other-query"
    else:
        trace["native_rrf"].append({"source_id": "invented-prior"})
    with pytest.raises(ValueError):
        transfer(VARIANTS[1], base, trace, units)


def test_typing_does_not_override_false_containment_or_truncated_text():
    base, trace, units = fixture()
    units["s10"]["evidence_text"] = "Truncated source."
    units["s10"]["text_sha256"] = sha256_bytes(b"Truncated source.")
    trace["vector_records"][10]["text_sha256"] = units["s10"]["text_sha256"]
    with pytest.raises(ValueError, match="same-page"):
        transfer(VARIANTS[1], base, trace, units)


def test_failed_native_condition_cannot_silently_become_a_transfer_success():
    base, trace, units = fixture()
    trace.update(status="failed", error="Native source retrieval failed")
    with pytest.raises(ValueError, match="successful"):
        transfer(VARIANTS[0], base, trace, units)
