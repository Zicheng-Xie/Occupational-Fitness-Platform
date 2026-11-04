"""Checks for frozen-source fusion and complete-clause consolidation."""

from copy import deepcopy

import pytest

from occupational_fitness_rag.evaluation.anchored_hybrid import rank_channels
from occupational_fitness_rag.evaluation.module_queries import build_module_query
from occupational_fitness_rag.evaluation.planned_hybrid import plan_query
from occupational_fitness_rag.indexing.base import StoredDocument
from occupational_fitness_rag.retrieval.fusion import reciprocal_rank_fusion


def unit(sid, covers=None, **values):
    return {
        "source_id": sid,
        "module": "vision",
        "licence_context": "commercial",
        "evidence_text": "Original clinical criterion " + sid,
        "covers_source_ids": [sid] if covers is None else covers,
        "pdf_page": 220,
        **values,
    }


def channel(name, kind, ids, query="original query"):
    return {
        "channel": name,
        "kind": kind,
        "query": query,
        "hits": [{"source_id": sid, "score": 1 / (i + 1)} for i, sid in enumerate(ids)],
    }


def fixture():
    units = [unit(sid) for sid in "ABCDEF"]
    channels = [
        channel("anchor:vector", "vector", list("ABCDEF")),
        channel("anchor:bm25", "bm25", list("BACDEF")),
        channel("facet:vector", "vector", list("FEDCBA"), "literal facet"),
        channel("facet:bm25", "bm25", list("FEDCBA"), "literal facet"),
    ]
    return channels, units


def test_anchor_only_matches_original_rrf_including_dense_first_ties():
    channels, units = fixture()
    # B is lexically earlier than Z; the stable RRF tie must still retain Z first.
    channels[0] = channel("anchor:vector", "vector", ["Z", "B"])
    channels[1] = channel("anchor:bm25", "bm25", ["B", "Z"])
    channels = channels[:2]
    units = [unit("Z"), unit("B")]
    dense = [StoredDocument(h["source_id"], "text", {}, h["score"]) for h in channels[0]["hits"]]
    sparse = [(StoredDocument(h["source_id"], "text", {}), h["score"]) for h in channels[1]["hits"]]
    expected = [row.doc.chunk_id for row in reciprocal_rank_fusion(dense, sparse)]
    actual = rank_channels(channels, units, {"policy": "anchor_only"})
    assert actual["source_ids"] == expected == ["Z", "B"]
    assert (
        rank_channels(list(reversed(channels)), units, {"policy": "anchor_only"})["source_ids"]
        == expected
    )


def test_anchor_weight_retains_original_query_and_zero_coverage_is_component_control():
    channels, units = fixture()
    old = rank_channels(channels, units, {"policy": "anchor_only"})
    for policy in ("anchor_best", "facet_balanced"):
        assert (
            rank_channels(channels, units, {"policy": policy, "anchor_weight": 1})["source_ids"]
            == old["source_ids"]
        )
    best = rank_channels(channels, units, {"policy": "anchor_best"})
    control = rank_channels(channels, units, {"policy": "containment", "coverage_weight": 0})
    assert best["source_ids"] == control["source_ids"]
    assert best["ranked_sources"] == control["ranked_sources"]


def test_identical_literal_queries_do_not_gain_extra_votes():
    channels, units = fixture()
    duplicated = deepcopy(channels)
    duplicated.extend(
        [
            {**deepcopy(channels[2]), "channel": "another:vector"},
            {**deepcopy(channels[3]), "channel": "another:bm25"},
        ]
    )
    for policy in ("anchor_best", "facet_balanced", "containment"):
        first = rank_channels(channels, units, {"policy": policy})
        second = rank_channels(duplicated, units, {"policy": policy})
        assert first["ranked_sources"] == second["ranked_sources"]
        assert second["diagnostics"]["duplicate_query_channels_ignored"] == [
            "another:vector",
            "another:bm25",
        ]


def test_literal_query_with_conflicting_reused_results_fails():
    channels, units = fixture()
    channels.append(channel("duplicate:vector", "vector", ["B", "A"], "literal facet"))
    with pytest.raises(ValueError, match="conflicting rankings"):
        rank_channels(channels, units, {"policy": "facet_balanced"})


def test_coverage_can_prefer_complete_original_with_verified_corpus_atoms():
    channels, units = fixture()
    units[2]["covers_source_ids"] = ["A", "B", "C"]
    original = deepcopy((channels, units))
    result = rank_channels(channels[:2], units, {"policy": "containment"})
    assert result["source_ids"][0] == "C"
    assert result["ranked_sources"][0]["new_corpus_coverage_atoms"] == ["A", "B", "C"]
    assert original == (channels, units)
    assert result["diagnostics"]["mmr_used"] is False


def test_unknown_canonical_coverage_is_an_independent_atom():
    channels, units = fixture()
    units[0]["covers_source_ids"] = []
    result = rank_channels(channels[:2], units, {"policy": "containment"})
    assert result["source_ids"][0] == "A"
    assert result["ranked_sources"][0]["new_corpus_coverage_atoms"] == ["A"]


def test_coverage_promotion_never_reaches_outside_candidate_budget():
    channels, units = fixture()
    units[5]["covers_source_ids"] = list("ABCDEF")
    result = rank_channels(
        channels[:2],
        units,
        {
            "policy": "containment",
            "candidate_k": 5,
            "sensitivity_k": 5,
        },
    )
    assert "F" not in result["source_ids"]


def test_complete_clause_requires_literal_full_text_and_retains_children_in_top10():
    channels, units = fixture()
    first = "Visual acuity commercial driving standard first complete original criterion."
    second = "Visual acuity second complete original qualification and specialist footnote."
    units[0]["evidence_text"] = first
    units[1]["evidence_text"] = second
    units[4]["evidence_text"] = "COMMERCIAL STANDARDS\n" + first + "\n" + second
    result = rank_channels(channels[:2], units, {"policy": "complete_clause"})
    assert result["source_ids"][0] == "E"
    assert set(result["source_ids"]) == set("ABCDEF")
    assert result["source_ids"].index("A") >= 4  # Available again after the main budget.
    assert result["ranked_sources"][0]["literal_contained_child_sources"] == ["A", "B"]
    broken = deepcopy(units)
    broken[4]["evidence_text"] = "A clinical summary with similar vocabulary, not the originals."
    assert (
        rank_channels(channels[:2], broken, {"policy": "complete_clause"})["diagnostics"][
            "literal_clause_promotions"
        ]
        == []
    )


def test_clause_parent_must_share_page_and_be_retrieved_in_top_budget():
    channels, units = fixture()
    text = "A full original clinical criterion with enough length to be a real passage."
    units[0]["evidence_text"] = text + " First."
    units[1]["evidence_text"] = text + " Second."
    units[5]["evidence_text"] = units[0]["evidence_text"] + "\n" + units[1]["evidence_text"]
    for changed in (units, [{**u, "pdf_page": 221} if u["source_id"] == "F" else u for u in units]):
        config = {"policy": "complete_clause", "candidate_k": 5, "sensitivity_k": 5}
        result = rank_channels(channels[:2], changed, config)
        assert result["diagnostics"]["literal_clause_promotions"] == []
    changed = [{**u, "pdf_page": 221} if u["source_id"] == "F" else u for u in units]
    assert (
        rank_channels(channels[:2], changed, {"policy": "query_balanced_clause"})["diagnostics"][
            "literal_clause_promotions"
        ]
        == []
    )


@pytest.mark.parametrize(
    "change, expected",
    [
        (lambda c, u: c.append(deepcopy(c[0])), "identities"),
        (lambda c, u: c[0]["hits"].append({"source_id": "A", "score": 0.1}), "repeated"),
        (lambda c, u: c[0]["hits"].append({"source_id": "UNKNOWN", "score": 0.1}), "Unknown"),
        (lambda c, u: u[0].update(licence_context="private"), "scope"),
        (lambda c, u: u[0].update(module="diabetes"), "module"),
        (lambda c, u: c[0]["hits"][0].update(score=float("nan")), "finite"),
        (lambda c, u: c[1].update(query="different"), "differs"),
    ],
)
def test_inconsistent_or_inaccessible_channels_fail_closed(change, expected):
    channels, units = fixture()
    change(channels, units)
    with pytest.raises(ValueError, match=expected):
        rank_channels(channels, units, {"policy": "anchor_best"})


@pytest.mark.parametrize(
    "config",
    [
        {"policy": "other"},
        {"policy": "anchor_best", "rrf_k": True},
        {"policy": "anchor_best", "anchor_weight": float("nan")},
        {"policy": "anchor_best", "coverage_weight": 1.1},
        {"policy": "anchor_best", "candidate_k": 3, "sensitivity_k": 5},
        {"policy": "anchor_best", "expected_source_ids": ["A"]},
    ],
)
def test_invalid_configuration_or_label_input_is_rejected(config):
    channels, units = fixture()
    with pytest.raises(ValueError):
        rank_channels(channels, units, config)


def test_reused_literal_planner_preserves_false_zero_and_quoted_negation():
    patient = {
        "modules": ["blackout"],
        "nurse_note": "No episode occurred. Episode count is zero.",
        "verified_patient_facts": {
            "blackout.occurred": {"value": False, "patient_quotes": ["No episode occurred."]},
            "blackout.event_count": {"value": 0, "patient_quotes": ["Episode count is zero."]},
        },
    }
    text, audit = build_module_query(patient, "blackout")
    query = {
        "query_id": "q",
        "module": "blackout",
        "licence_context": "commercial",
        "query": text,
        "query_audit": audit,
    }
    plan = plan_query(query, patient)
    values = {name: value for f in plan["facets"] for name, value in f["field_values"].items()}
    assert values["blackout.occurred"] is False
    assert type(values["blackout.event_count"]) is int and values["blackout.event_count"] == 0
    assert any("No episode occurred." in f["query"] for f in plan["facets"])
