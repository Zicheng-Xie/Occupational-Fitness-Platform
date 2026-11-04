"""Pure contract tests for the frozen native-score coverage blend.

Synthetic sources and measured-score stand-ins keep these tests independent of
patient labels, model packages, checkpoint downloads and experiment artifacts.
"""

from copy import deepcopy

import pytest

from occupational_fitness_rag.evaluation.semantic_guarded_hybrid import rank_semantic


def inputs(count=10):
    ids = [f"a{i}" for i in range(count)]
    units = {
        sid: {
            "source_id": sid,
            "module": "diabetes",
            "licence_context": "commercial",
            "covers_source_ids": [],
        }
        for sid in [*ids, "extra", "parent"]
    }
    baseline = {
        "query_id": "query",
        "case_id": "case",
        "module": "diabetes",
        "status": "completed",
        "source_ids": ids,
    }
    native = {
        **{k: baseline[k] for k in ("query_id", "case_id", "module", "status")},
        "candidate_trace": [{"source_id": sid, "native_score": 0.1} for sid in ids],
    }
    return baseline, native, units


def test_ten_independent_baseline_originals_block_an_attractive_extra():
    before, native, units = inputs()
    native["candidate_trace"].insert(0, {"source_id": "extra", "native_score": 1.0})
    result = rank_semantic(before, native, units, 0.5)
    assert set(result["source_ids"]) == set(before["source_ids"])
    assert len(result["source_ids"]) == 10
    diagnostics = result["diagnostics"]
    assert diagnostics["protected_coverage_retained"] is True
    assert any(r["source_id"] == "extra" for r in diagnostics["guard_rejected_candidates"])
    assert diagnostics["mmr_used"] is False
    assert diagnostics["reference_labels_available_to_ranker"] is False
    assert diagnostics["guard_fallback_reason"] is None


def test_complete_original_can_cover_baseline_children_without_losing_footprint():
    before, native, units = inputs()
    units["parent"]["covers_source_ids"] = ["a0", "a1"]
    native["candidate_trace"].insert(0, {"source_id": "parent", "native_score": 1.0})
    result = rank_semantic(before, native, units, 0.5)
    assert result["source_ids"][0] == "parent"
    assert len(result["source_ids"]) == 10
    assert set(result["source_ids"]) != set(before["source_ids"])
    covered = {
        sid
        for source in result["source_ids"]
        for sid in [source, *units[source]["covers_source_ids"]]
    }
    assert set(before["source_ids"]) <= covered
    assert result["diagnostics"]["protected_original_source_footprint"] == sorted(
        before["source_ids"]
    )


def test_guard_also_preserves_an_expanded_baseline_source_own_identifier():
    before, native, units = inputs()
    units["a0"]["covers_source_ids"] = ["a1"]
    units["parent"]["covers_source_ids"] = ["a1"]
    native["candidate_trace"].insert(0, {"source_id": "parent", "native_score": 1.0})
    result = rank_semantic(before, native, units, 0.5)
    assert "a0" in result["source_ids"]
    assert "a0" in result["diagnostics"]["protected_original_source_footprint"]


def test_missing_native_measurement_is_explicit_zero_and_never_a_new_call():
    before, native, units = inputs()
    native["candidate_trace"] = [{"source_id": "extra", "native_score": 0.9}]
    result = rank_semantic(before, native, units, 0.25)
    diagnostics = result["diagnostics"]
    assert diagnostics["native_missing_source_ids"] == before["source_ids"]
    assert diagnostics["actual_new_native_calls"] == 0
    trace = {r["source_id"]: r for r in diagnostics["candidate_score_trace"]}
    assert trace["a0"]["native_score_missing"] is True
    assert trace["a0"]["native_sigmoid"] == 0.0
    assert trace["a0"]["native_missing_policy"] == "explicit_zero_without_native_call"
    assert trace["extra"]["native_score_missing"] is False
    assert trace["extra"]["prior_kind"] == "original_rrf_top20_rank"
    assert trace["extra"]["prior_rank"] == 1


def test_score_formula_and_prior_rank_sources_are_auditable():
    before, native, units = inputs(3)
    native["candidate_trace"] = [
        {"source_id": "extra", "native_score": 0.7},
        {"source_id": "a2", "native_score": 0.0},
        {"source_id": "a1", "native_score": 1.0},
        {"source_id": "a0", "native_score": 0.0},
    ]
    result = rank_semantic(before, native, units, 0.5)
    first = result["ranked_sources"][0]
    assert first["source_id"] == "a1"
    assert first["prior_kind"] == "v3_top10_rank"
    assert first["prior_rank"] == 2
    assert first["selection_score"] == pytest.approx(0.85 * (0.5 * 61 / 62 + 0.5) + 0.15)


def test_ranking_is_deterministic_and_inputs_are_unchanged():
    args = inputs(5)
    copy = deepcopy(args)
    first = rank_semantic(*args, 0.25)
    assert rank_semantic(*args, 0.25) == first
    assert args == copy


@pytest.mark.parametrize("weight", [True, False, 0, 0.15, 0.75, 1.0, float("nan"), "0.25"])
def test_only_the_two_predeclared_semantic_weights_are_allowed(weight):
    with pytest.raises(ValueError, match="prespecified"):
        rank_semantic(*inputs(), weight)


@pytest.mark.parametrize("score", [True, -0.01, 1.01, float("nan"), float("inf"), "0.5"])
def test_native_scores_must_be_real_finite_sigmoid_measurements(score):
    before, native, units = inputs()
    native["candidate_trace"][0]["native_score"] = score
    with pytest.raises(ValueError, match="sigmoid"):
        rank_semantic(before, native, units, 0.25)


@pytest.mark.parametrize("field", ["query_id", "case_id", "module"])
def test_native_and_baseline_conditions_must_match(field):
    before, native, units = inputs()
    native[field] = "other"
    with pytest.raises(ValueError, match="matching"):
        rank_semantic(before, native, units, 0.25)


@pytest.mark.parametrize("failed", ["baseline", "native"])
def test_failed_imported_retrieval_is_not_silently_replaced(failed):
    before, native, units = inputs()
    (before if failed == "baseline" else native)["status"] = "failed"
    with pytest.raises(ValueError, match="completed"):
        rank_semantic(before, native, units, 0.25)


@pytest.mark.parametrize("violation", ["unknown", "private", "cross_module", "containment_scope"])
def test_every_original_and_its_containment_must_be_accessible(violation):
    before, native, units = inputs()
    if violation == "unknown":
        del units["a0"]
    elif violation == "private":
        units["a0"]["licence_context"] = "private"
    elif violation == "cross_module":
        units["a0"]["module"] = "blackout"
    else:
        units["a0"]["covers_source_ids"] = ["extra"]
        units["extra"]["module"] = "blackout"
    with pytest.raises(ValueError):
        rank_semantic(before, native, units, 0.25)


@pytest.mark.parametrize(
    "violation",
    [
        "duplicate_native",
        "duplicate_baseline",
        "empty_native",
        "empty_baseline",
        "oversized_baseline",
        "oversized_native",
    ],
)
def test_source_inventories_obey_frozen_budgets(violation):
    before, native, units = inputs()
    if violation == "duplicate_native":
        native["candidate_trace"].append(deepcopy(native["candidate_trace"][0]))
    elif violation == "duplicate_baseline":
        before["source_ids"][1] = before["source_ids"][0]
    elif violation == "empty_native":
        native["candidate_trace"] = []
    elif violation == "empty_baseline":
        before["source_ids"] = []
    elif violation == "oversized_baseline":
        before["source_ids"].append("extra")
    else:
        native["candidate_trace"] = [
            {"source_id": f"item{i}", "native_score": 0.5} for i in range(21)
        ]
    with pytest.raises(ValueError, match="inventories"):
        rank_semantic(before, native, units, 0.25)
