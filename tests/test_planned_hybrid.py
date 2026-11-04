"""Decision-relevant checks for the additional scoped retrieval method."""

from copy import deepcopy

import pytest

from occupational_fitness_rag.evaluation.module_queries import build_module_query
from occupational_fitness_rag.evaluation.planned_hybrid import (
    diversify,
    execute_plan,
    fuse_channels,
    plan_query,
    search_channels,
)


def fixture():
    note = "No blackout occurred. His father lost consciousness. Event count is 0."
    patient = {
        "licence_context": "commercial",
        "modules": ["blackout"],
        "nurse_note": note,
        "verified_patient_facts": {
            "blackout.occurred": {"value": False, "patient_quotes": ["No blackout occurred."]},
            "blackout.event_count": {"value": 0, "patient_quotes": ["Event count is 0."]},
        },
    }
    text, audit = build_module_query(patient, "blackout")
    query = {
        "query_id": "q1",
        "module": "blackout",
        "licence_context": "commercial",
        "query": text,
        "query_audit": audit,
    }
    units = [
        {
            "source_id": "A",
            "module": "blackout",
            "licence_context": "commercial",
            "evidence_text": "Blackout occurred, event count; unconditional criteria and complete qualifications.",
            "text_sha256": "a",
        },
        {
            "source_id": "B",
            "module": "blackout",
            "licence_context": "commercial",
            "evidence_text": "Specialist investigation and subsequent follow up.",
            "text_sha256": "b",
        },
        {
            "source_id": "PRIVATE",
            "module": "blackout",
            "licence_context": "private",
            "evidence_text": "blackout occurred event count",
            "text_sha256": "p",
        },
        {
            "source_id": "OTHER",
            "module": "diabetes",
            "licence_context": "commercial",
            "evidence_text": "Blackout occurred",
            "text_sha256": "o",
        },
    ]
    config = {
        "max_facets": 4,
        "rrf_k": 60,
        "relevance_weight": 0.7,
        "max_keyword_followups": 2,
        "lexical_coverage_threshold": 0.6,
        "sensitivity_k": 10,
    }
    return patient, query, units, config


def test_plan_preserves_false_zero_and_patient_subject():
    patient, query, _, _ = fixture()
    plan = plan_query(query, patient)
    assert plan["all_documented_fields_retained"]
    assert {
        name: value for facet in plan["facets"] for name, value in facet["field_values"].items()
    } == {
        "blackout.event_count": 0,
        "blackout.occurred": False,
    }
    assert any("No blackout occurred." in facet["query"] for facet in plan["facets"])
    assert "father" not in plan["facets"][0]["query"]
    assert plan["anchor_query"] == query["query"]


def test_planner_rejects_changed_fact_or_invented_quote():
    patient, query, _, _ = fixture()
    changed = deepcopy(patient)
    changed["verified_patient_facts"]["blackout.occurred"]["value"] = True
    with pytest.raises(ValueError, match="facts differ"):
        plan_query(query, changed)
    changed = deepcopy(patient)
    changed["verified_patient_facts"]["blackout.occurred"]["patient_quotes"] = [
        "An invented episode."
    ]
    with pytest.raises(ValueError, match="original patient"):
        plan_query(query, changed)


def test_nested_field_family_stays_together_and_flat_fields_do_not_disappear_at_budget():
    patient, query, _, _ = fixture()
    patient["modules"] = ["vision"]
    patient["nurse_note"] = "Literal assessment recorded."
    names = [
        "vision.uncorrected.left.snellen",
        "vision.uncorrected.right.snellen",
        *[f"vision.field_{index}" for index in range(9)],
    ]
    patient["verified_patient_facts"] = {
        name: {"value": index, "patient_quotes": [patient["nurse_note"]]}
        for index, name in enumerate(names)
    }
    text, audit = build_module_query(patient, "vision")
    query.update(module="vision", query=text, query_audit=audit)
    plan = plan_query(query, patient, 4)
    assert len(plan["facets"]) == 4
    assert sorted(n for f in plan["facets"] for n in f["field_names"]) == sorted(names)
    assert any(
        {"vision.uncorrected.left.snellen", "vision.uncorrected.right.snellen"}
        <= set(f["field_names"])
        for f in plan["facets"]
    )


def test_scoped_search_never_broadens_to_private_or_other_disease():
    _, query, units, _ = fixture()
    channels = search_channels(
        query["query"], "blackout", units, [[1.0, 0.0]] * 4, [1.0, 0.0], "test"
    )
    assert channels
    assert all(h["source_id"] in {"A", "B"} for c in channels for h in c["hits"])


def test_duplicate_query_channels_do_not_add_votes_and_order_is_stable():
    first = {
        "channel": "one",
        "kind": "vector",
        "hits": [{"source_id": "A", "score": 0.9}, {"source_id": "B", "score": 0.8}],
    }
    second = {
        "channel": "two",
        "kind": "bm25",
        "hits": [{"source_id": "B", "score": 100}, {"source_id": "A", "score": 9}],
    }
    base = fuse_channels([first, second])
    repeated = fuse_channels([first, second, first, first])
    assert [(r["source_id"], r["score"]) for r in base] == [
        (r["source_id"], r["score"]) for r in repeated
    ]
    assert [(r["source_id"], r["score"]) for r in base] == [
        (r["source_id"], r["score"]) for r in fuse_channels([second, first])
    ]
    assert max(r["score"] for r in base) <= 1


def test_pipeline_records_bounded_keyword_refinement_and_keeps_originals():
    patient, query, units, config = fixture()
    config["lexical_coverage_threshold"] = 0.8
    query = deepcopy(query)
    patient = deepcopy(patient)
    patient["verified_patient_facts"]["blackout.mechanism_review"] = {
        "value": "pending",
        "patient_quotes": ["No blackout occurred."],
    }
    text, audit = build_module_query(patient, "blackout")
    query.update(query=text, query_audit=audit)
    seen = []

    def embed(texts):
        seen.extend(texts)
        return [[1.0, 0.0] for _ in texts]

    before = deepcopy(units)
    result = execute_plan(
        query, patient, {"units": units}, [[1.0, 0.0]] * 4, [1.0, 0.0], embed, config
    )
    assert result["keyword_followups"] == 1
    assert len(seen) == result["new_embedding_inputs"] == 3
    assert [e["stage"] for e in result["events"]] == [
        "plan",
        "search",
        "inspect",
        "refine",
        "finalize",
    ]
    assert set(result["source_ids"]) == {"A", "B"}
    assert before == units  # No generated summaries, trimmed qualifiers or edited source text.


def test_embedding_failure_aborts_instead_of_lexical_fallback():
    patient, query, units, config = fixture()

    def failed(texts):
        raise TimeoutError("actual embedding failure")

    with pytest.raises(TimeoutError, match="actual embedding"):
        execute_plan(query, patient, {"units": units}, [[1.0, 0.0]] * 4, [1.0, 0.0], failed, config)


def test_absent_information_is_not_made_normal_or_into_a_synthetic_fact():
    patient, query, units, config = fixture()
    patient["verified_patient_facts"] = {}
    text, audit = build_module_query(patient, "blackout")
    query.update(query=text, query_audit=audit)
    result = execute_plan(
        query,
        patient,
        {"units": units},
        [[1.0, 0.0]] * 4,
        [1.0, 0.0],
        lambda texts: pytest.fail("No facet embedding should run for absent facts"),
        config,
    )
    assert result["events"][0]["plan"]["no_documented_facts"]
    assert result["new_embedding_inputs"] == 0


def test_diversity_selects_complementary_original_but_does_not_cut_any_text():
    units = {
        "A": {"evidence_text": "one two three four"},
        "B": {"evidence_text": "one two three four"},
        "C": {"evidence_text": "another relevant qualification"},
    }
    rows = [
        {"source_id": "A", "score": 1.0},
        {"source_id": "B", "score": 0.99},
        {"source_id": "C", "score": 0.8},
    ]
    assert [r["source_id"] for r in diversify(rows, units, 2)] == ["A", "C"]
    assert [r["source_id"] for r in diversify(rows, units, 2, 1.0)] == ["A", "B"]
