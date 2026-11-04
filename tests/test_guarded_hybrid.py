"""Coverage-floor checks use constructed originals, not patient reference labels."""

from copy import deepcopy
from itertools import combinations
from random import Random

import pytest

from occupational_fitness_rag.evaluation.guarded_hybrid import (
    _completion_solver,
    rank_channels,
)


def unit(sid, covers=None, **values):
    return {
        "source_id": sid,
        "module": "vision",
        "licence_context": "commercial",
        "evidence_text": "Original visual standard and full qualification " + sid,
        "pdf_page": 220,
        "covers_source_ids": [sid] if covers is None else covers,
        **values,
    }


def channel(name, kind, ids, query="original query"):
    return {
        "channel": name,
        "kind": kind,
        "query": query,
        "hits": [{"source_id": sid, "score": 1 / (index + 1)} for index, sid in enumerate(ids)],
    }


def fixture():
    ids = list("ABCDEFGHIJKL")
    units = [unit(sid) for sid in ids]
    channels = [
        channel("anchor:vector", "vector", ids),
        channel("anchor:bm25", "bm25", ids),
        channel("facet:vector", "vector", ["L", *ids[:-1]], "source literal facet"),
        channel("facet:bm25", "bm25", ["L", *ids[:-1]], "source literal facet"),
    ]
    return channels, units


def footprint(ids, units):
    by_id = {u["source_id"]: u for u in units}
    return {atom for sid in ids for atom in [sid, *by_id[sid]["covers_source_ids"]]}


def test_guard_repairs_wider_pool_displacement_under_the_same_ten_source_budget():
    channels, units = fixture()
    wide = rank_channels(channels, units, {"policy": "wide_coverage"})
    guarded = rank_channels(channels, units, {"policy": "guarded_coverage"})
    assert len(wide["source_ids"]) == len(guarded["source_ids"]) == 10
    assert "L" in wide["source_ids"] and "J" not in wide["source_ids"]
    assert guarded["source_ids"] == list("ABCDEFGHIJ")
    assert guarded["diagnostics"]["protected_coverage_retained"]
    assert any(r["source_id"] == "L" for r in guarded["diagnostics"]["guard_rejected_candidates"])
    assert guarded["diagnostics"]["guard_fallback_reason"] is None


def test_complete_original_can_replace_a_narrow_source_without_losing_its_text_coverage():
    channels, units = fixture()
    units[-1]["covers_source_ids"] = ["J"]
    units[-1]["evidence_text"] += "\n" + units[9]["evidence_text"]
    guarded = rank_channels(channels, units, {"policy": "guarded_coverage"})
    assert "L" in guarded["source_ids"]
    required = footprint(list("ABCDEFGHIJ"), units)
    assert required <= footprint(guarded["source_ids"], units)
    assert len(guarded["source_ids"]) == 10


def test_noncanonical_original_is_protected_as_an_independent_source():
    channels, units = fixture()
    units[9]["covers_source_ids"] = []
    guarded = rank_channels(channels, units, {"policy": "guarded_coverage"})
    assert "J" in guarded["source_ids"]
    assert "J" in guarded["diagnostics"]["protected_original_source_footprint"]


def test_wider_candidate_and_original_anchor_union_stays_source_bound():
    channels, units = fixture()
    # A source outside the first ten fusion candidates remains accessible when
    # it belongs to the original query's protected first ten.
    actual = rank_channels(channels, units, {"policy": "guarded_coverage", "candidate_k": 10})
    assert "J" in actual["diagnostics"]["candidate_source_ids"]
    assert set(actual["source_ids"]) <= set(actual["diagnostics"]["candidate_source_ids"])
    assert actual["diagnostics"]["candidate_pool_size"] == 11


def test_short_scopes_return_only_real_originals_and_leave_inputs_unchanged():
    channels, units = fixture()
    units = units[:4]
    for row in channels:
        row["hits"] = [hit for hit in row["hits"] if hit["source_id"] in "ABCD"]
    original = deepcopy((channels, units))
    result = rank_channels(channels, units, {"policy": "guarded_coverage"})
    assert len(result["source_ids"]) == 4
    assert len(set(result["source_ids"])) == 4
    assert original == (channels, units)
    assert result["diagnostics"]["mmr_used"] is False
    assert result["diagnostics"]["reference_labels_available_to_ranker"] is False


def test_duplicate_literal_query_channels_do_not_create_additional_votes():
    channels, units = fixture()
    first = rank_channels(channels, units, {"policy": "guarded_facet_coverage"})
    channels.extend(
        [
            {**deepcopy(channels[2]), "channel": "repeat:vector"},
            {**deepcopy(channels[3]), "channel": "repeat:bm25"},
        ]
    )
    second = rank_channels(channels, units, {"policy": "guarded_facet_coverage"})
    assert first["source_ids"] == second["source_ids"]
    assert first["ranked_sources"] == second["ranked_sources"]


def test_feasibility_solver_handles_a_case_where_greedy_set_cover_fails():
    pool = [{"source_id": sid} for sid in "ABC"]
    atoms = {"A": {"1", "2", "3", "4"}, "B": {"1", "2", "5"}, "C": {"3", "4", "6"}}
    target, _, solve = _completion_solver(pool, atoms, set("123456"))
    assert set(solve(target, 2)) == {"B", "C"}
    assert solve(target, 1) is None


def test_exact_feasibility_matches_exhaustive_small_budget_oracle():
    random = Random(17)
    names = list("ABCDEFGH")
    target_atoms = set("12345678")
    pool = [{"source_id": sid} for sid in names]
    for _ in range(20):
        atoms = {sid: {a for a in target_atoms if random.random() < 0.35} for sid in names}
        target, _, solve = _completion_solver(pool, atoms, target_atoms)
        for budget in (1, 2, 3):
            possible = any(
                set().union(*(atoms[sid] for sid in selection)) >= target_atoms
                for size in range(1, budget + 1)
                for selection in combinations(names, size)
            )
            result = solve(target, budget)
            assert (result is not None) == possible
            if result is not None:
                assert len(result) <= budget and len(result) == len(set(result))
                assert set().union(*(atoms[sid] for sid in result)) >= target_atoms


@pytest.mark.parametrize("policy", ["guarded_coverage", "guarded_facet_coverage"])
def test_both_guarded_fusions_preserve_all_original_rrf_coverage(policy):
    channels, units = fixture()
    result = rank_channels(channels, units, {"policy": policy})
    assert footprint(result["diagnostics"]["original_rrf_source_ids"], units) <= footprint(
        result["source_ids"], units
    )


@pytest.mark.parametrize(
    "config",
    [
        {"policy": "unknown"},
        {"policy": "guarded_coverage", "expected_source_ids": ["A"]},
        {"policy": "guarded_coverage", "sensitivity_k": 11},
        {"policy": "guarded_coverage", "candidate_k": 9},
        {"policy": "guarded_coverage", "candidate_k": True},
        {"policy": "guarded_coverage", "coverage_weight": float("nan")},
    ],
)
def test_invalid_budget_weights_and_label_inputs_are_rejected(config):
    channels, units = fixture()
    with pytest.raises(ValueError):
        rank_channels(channels, units, config)


@pytest.mark.parametrize(
    "change",
    [
        lambda c, u: u[0].update(licence_context="private"),
        lambda c, u: u[0].update(module="diabetes"),
        lambda c, u: u[0].update(covers_source_ids=["unknown"]),
    ],
)
def test_invalid_or_inaccessible_originals_cannot_satisfy_the_guard(change):
    channels, units = fixture()
    change(channels, units)
    with pytest.raises(ValueError):
        rank_channels(channels, units, {"policy": "guarded_coverage"})
