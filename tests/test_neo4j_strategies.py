"""Test native-rank fusion, literal path proof and the actual Top10 coverage floor."""

from copy import deepcopy

import pytest

from occupational_fitness_rag.evaluation.neo4j_strategies import VARIANTS, native_rrf, rank
from occupational_fitness_rag.provenance import sha256_bytes
from tools.run_neo4j_strategies import GRAPH_QUERY, inputs


def units():
    result = {}
    for i in range(12):
        sid, text = f"s{i}", f"Complete original criterion number {i}."
        result[sid] = {
            "source_id": sid,
            "module": "vision",
            "licence_context": "commercial",
            "evidence_text": text,
            "text_sha256": sha256_bytes(text.encode()),
            "covers_source_ids": [],
            "pdf_page": 220,
            "section": "10.3",
            "cross_references": [],
            "explicit_section_references": [],
        }
    return result


def hit(sid, inventory, score):
    return {"source_id": sid, "text_sha256": inventory[sid]["text_sha256"], "score": score}


def test_native_rrf_uses_rank_rather_than_incompatible_engine_score_scale():
    inventory = units()
    dense = [hit("s0", inventory, 0.9), hit("s1", inventory, 0.8)]
    sparse = [hit("s1", inventory, 4000.0), hit("s0", inventory, 5.0)]
    before = deepcopy([dense, sparse])
    result = native_rrf(dense, sparse, inventory, "vision")
    assert result[0]["source_id"] == "s0"  # Dense-first stable RRF tie.
    assert result[0]["score"] == pytest.approx(1 / 61 + 1 / 62)
    assert before == [dense, sparse]


@pytest.mark.parametrize("mutation", ["scope", "sha", "nan", "duplicate"])
def test_invalid_native_originals_are_rejected(mutation):
    inventory = units()
    dense = [hit("s0", inventory, 0.9)]
    if mutation == "scope":
        inventory["s0"]["module"] = "diabetes"
    elif mutation == "sha":
        dense[0]["text_sha256"] = "changed"
    elif mutation == "nan":
        dense[0]["score"] = float("nan")
    else:
        dense.append(dense[0])
    with pytest.raises(ValueError):
        native_rrf(dense, [], inventory, "vision")


def test_graph_shared_anchor_is_not_an_allowed_source_relation():
    inventory = units()
    native = native_rrf([hit(s, inventory, 1.0) for s in inventory], [], inventory, "vision")
    false_path = {
        "source_id": "s11",
        "seed_source_id": "s0",
        "text_sha256": inventory["s11"]["text_sha256"],
        "graph_path": "shared_literal_clause_anchor",
    }
    with pytest.raises(ValueError, match="allowed literal edge"):
        rank(VARIANTS[2], list(inventory)[:10], native, [false_path], inventory, "vision")


@pytest.mark.parametrize(
    "path", ["literal_source_containment", "literal_explicit_section_reference"]
)
def test_graph_path_needs_actual_literal_relation(path):
    inventory = units()
    native = native_rrf([hit(s, inventory, 1.0) for s in inventory], [], inventory, "vision")
    false_path = {
        "source_id": "s11",
        "seed_source_id": "s0",
        "text_sha256": inventory["s11"]["text_sha256"],
        "graph_path": path,
    }
    with pytest.raises(ValueError, match="same-page|explicit"):
        rank(VARIANTS[2], list(inventory)[:10], native, [false_path], inventory, "vision")


def test_native_control_exactly_preserves_actual_native_rrf_order():
    inventory = units()
    native = native_rrf([hit(s, inventory, 1.0) for s in inventory], [], inventory, "vision")
    result = rank(VARIANTS[0], list(inventory)[:10], native, [], inventory, "vision")
    assert result["source_ids"] == list(inventory)[:10]
    assert not result["diagnostics"]["graph_used"]


def test_guard_preserves_entire_actual_top10_footprint_and_originals():
    inventory = units()
    inventory["s11"]["evidence_text"] = "\n".join(
        inventory[s]["evidence_text"] for s in ("s0", "s1", "s2")
    )
    inventory["s11"]["text_sha256"] = sha256_bytes(inventory["s11"]["evidence_text"].encode())
    inventory["s11"]["covers_source_ids"] = ["s0", "s1", "s2"]
    before = deepcopy(inventory)
    native = native_rrf([hit(s, inventory, 1.0) for s in inventory], [], inventory, "vision")
    path = {
        "source_id": "s11",
        "seed_source_id": "s0",
        "text_sha256": inventory["s11"]["text_sha256"],
        "graph_path": "literal_source_containment",
    }
    result = rank(VARIANTS[2], list(inventory)[:10], native, [path], inventory, "vision")
    covered = set()
    for sid in result["source_ids"]:
        covered.update(inventory[sid]["covers_source_ids"])
        covered.add(sid)
    assert set(list(inventory)[:10]) <= covered
    assert len(result["source_ids"]) == len(set(result["source_ids"])) == 10
    assert result["diagnostics"]["protected_coverage_retained"]
    assert result["diagnostics"]["reference_labels_available"] is False
    assert inventory == before


def test_graph_query_has_no_generic_shared_anchor_or_arbitrary_target_limit_order():
    assert "HAS_CONDITION" not in GRAPH_QUERY
    assert "candidate_ranks[candidate.source_id]" in GRAPH_QUERY
    assert "[0..5]" in GRAPH_QUERY


def test_real_shared_input_contract_reads_only_new_reviewed_inputs():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    folder = root / "outputs/experiments/scope88_shared_retrieval_v2"
    if not folder.exists():
        pytest.skip("Frozen shared88 engineering fixture not present")
    manifest, _, corpus, queries, vectors, qvectors, anchors = inputs(folder)
    assert manifest["identity"]
    assert len(corpus["units"]) == len(vectors) == 88
    assert len(queries) == len(qvectors) == len(anchors) == 77


def test_old88_inventory_with94_query_metadata_is_explicitly_rejected():
    from pathlib import Path

    folder = Path(__file__).resolve().parents[1] / "outputs/experiments/scope88_shared_retrieval_v1"
    if not folder.exists():
        pytest.skip("Historical metadata diagnostic fixture not present")
    with pytest.raises(ValueError, match="Query corpus identity"):
        inputs(folder)
