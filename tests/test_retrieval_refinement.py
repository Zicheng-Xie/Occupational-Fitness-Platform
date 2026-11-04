"""Critical isolation and no-regression contracts for experimental refinement."""

from copy import deepcopy

import pytest

from occupational_fitness_rag.evaluation.retrieval_refinement import (
    fuse_views,
    literal_facets,
    literal_parent_closure,
    original_footprints,
    refine_ranking,
)


def example():
    units = {}
    for i in range(12):
        sid = str(i)
        units[sid] = {
            "source_id": sid,
            "module": "hearing",
            "licence_context": "commercial",
            "pdf_page": 120,
            "evidence_text": f"Original statement {i}.",
            "covers_source_ids": [],
            "criterion_type": "general" if i < 6 else None,
        }
    units["parent"] = {
        "source_id": "parent",
        "module": "hearing",
        "licence_context": "commercial",
        "pdf_page": 120,
        "evidence_text": " ".join(units[str(i)]["evidence_text"] for i in range(4)),
        "covers_source_ids": [str(i) for i in range(4)],
    }
    baseline = {
        "status": "completed",
        "module": "hearing",
        "source_ids": [str(i) for i in range(10)],
    }
    return units, baseline


def test_complete_parents_free_slots_without_losing_any_nested_footprint():
    units, baseline = example()
    saved = deepcopy((units, baseline))
    atoms = original_footprints(units, "hearing")
    candidates = literal_parent_closure(list(units), atoms)
    result = refine_ranking(baseline, candidates, units, {s: 1.0 for s in units})
    assert "parent" in result["source_ids"][:5]
    for k in (1, 3, 5, 10):
        old = set().union(*(atoms[s] for s in baseline["source_ids"][:k]))
        new = set().union(*(atoms[s] for s in result["source_ids"][:k]))
        assert old <= new
    assert len(result["source_ids"]) == len(set(result["source_ids"])) == 10
    assert (units, baseline) == saved


def test_parent_metadata_requires_complete_same_page_original_text():
    units, _ = example()
    units["parent"]["evidence_text"] = "A generated summary without the original."
    with pytest.raises(ValueError, match="complete literal"):
        original_footprints(units, "hearing")
    units, _ = example()
    units["parent"]["pdf_page"] = 121
    with pytest.raises(ValueError, match="page"):
        original_footprints(units, "hearing")


def test_reordering_an_existing_parent_never_duplicates_its_source_id():
    units, baseline = example()
    baseline["source_ids"] = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "parent"]
    result = refine_ranking(baseline, list(units), units, {s: 1.0 for s in units})
    assert len(result["source_ids"]) == len(set(result["source_ids"])) == 10
    assert "parent" in result["source_ids"][:5]


def test_literal_context_retains_negation_family_subject_and_time():
    note = "His mother has diabetes. He denies insulin use, and glucose is unmeasured today. Audiometry is pending."
    result = literal_facets(note, "diabetes")
    assert result == [
        "His mother has diabetes.",
        "He denies insulin use, and glucose is unmeasured today.",
    ]
    assert all(q in note for q in result)
    assert "Audiometry is pending." not in result


def test_duplicate_view_cannot_amplify_fusion_and_labels_cannot_change_allocation():
    channel = {"view": "anchor", "engine": "hybrid", "source_ids": ["0", "1"]}
    assert fuse_views([channel]) == fuse_views([channel, channel])
    units, baseline = example()
    result = refine_ranking(baseline, list(units), units, {s: 1.0 for s in units})
    baseline.update(expected_source_ids=["11"], reference_outcome="not_fit")
    assert refine_ranking(baseline, list(units), units, {s: 1.0 for s in units}) == result
    baseline["status"] = "failed"
    with pytest.raises(ValueError, match="failed native"):
        refine_ranking(baseline, list(units), units, {})


def test_joint_prefix_can_replace_multiple_redundant_children_together():
    from occupational_fitness_rag.evaluation.retrieval_prefix_search import joint_prefix

    units, baseline = example()
    atoms = original_footprints(units, "hearing")
    result = joint_prefix(baseline, list(units), units, {s: 1.0 for s in units})
    assert result["diagnostics"]["typed_top5_after"] > result["diagnostics"]["typed_top5_before"]
    for k in (1, 3, 5, 10):
        before = set().union(*(atoms[s] for s in baseline["source_ids"][:k]))
        after = set().union(*(atoms[s] for s in result["source_ids"][:k]))
        assert before <= after
    assert len(result["source_ids"]) == len(set(result["source_ids"])) == 10


def test_joint_prefix_rejects_failed_baselines_without_substitution():
    from occupational_fitness_rag.evaluation.retrieval_prefix_search import joint_prefix

    units, baseline = example()
    baseline["status"] = "failed"
    with pytest.raises(ValueError, match="successful measured"):
        joint_prefix(baseline, list(units), units, {})
