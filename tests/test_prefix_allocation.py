"""Coverage optimization cannot invent or silently extend retrieved evidence."""

from copy import deepcopy

import pytest

from occupational_fitness_rag.evaluation.prefix_allocation import allocate_prefix


def fixture():
    def unit(sid, covered=None, criterion=False):
        return {
            "source_id": sid,
            "module": "example",
            "licence_context": "commercial",
            "covers_source_ids": list(covered or []),
            **({"criterion_type": "general"} if criterion else {}),
        }

    units = {str(i): unit(str(i), criterion=i in (1, 2, 6, 7)) for i in range(1, 9)}
    units["8"] = unit("8", ["1", "2", "6", "7"])
    row = {"status": "completed", "module": "example", "source_ids": list(units)}
    return row, units


def test_criterion_allocation_reorders_only_actual_sources_and_preserves_floor():
    row, units = fixture()
    before = deepcopy((row, units))
    result = allocate_prefix(row, units, "criterion_floor")
    assert set(result["source_ids"]) == set(row["source_ids"])
    assert "8" in result["source_ids"][:5]
    assert set(result["diagnostics"]["prefix_covered_criterion_atoms"]) == {"1", "2", "6", "7"}
    assert result["diagnostics"]["criterion_floor_retained"] is True
    assert before == (row, units)


def test_full_original_floor_never_drops_prior_background_evidence():
    row, units = fixture()
    result = allocate_prefix(row, units, "full_source_floor")
    assert result["diagnostics"]["full_top5_source_floor_retained"] is True
    covered = set(result["diagnostics"]["prefix_original_atoms"])
    assert set(row["source_ids"][:5]) <= covered


def test_no_criteria_preserves_original_order():
    row, units = fixture()
    for unit in units.values():
        unit.pop("criterion_type", None)
    assert allocate_prefix(row, units, "criterion_floor")["source_ids"] == row["source_ids"]


def test_small_inventory_is_not_padded():
    row, units = fixture()
    row["source_ids"] = row["source_ids"][:3]
    assert allocate_prefix(row, units, "criterion_floor")["source_ids"] == ["1", "2", "3"]


@pytest.mark.parametrize(
    "change", ["duplicate", "unknown", "module", "scope", "containment", "failed"]
)
def test_invalid_scope_or_actual_inventory_is_rejected(change):
    row, units = fixture()
    if change == "duplicate":
        row["source_ids"].append("1")
    elif change == "unknown":
        row["source_ids"][0] = "missing"
    elif change == "module":
        units["1"]["module"] = "other"
    elif change == "scope":
        units["1"]["licence_context"] = "private"
    elif change == "containment":
        units["8"]["covers_source_ids"] = ["missing"]
    else:
        row["status"] = "failed"
    with pytest.raises(ValueError):
        allocate_prefix(row, units, "criterion_floor")


def test_unknown_policy_rejected():
    row, units = fixture()
    with pytest.raises(ValueError):
        allocate_prefix(row, units, "unfrozen")


def test_expected_source_fields_in_case_cannot_influence_ranking():
    row, units = fixture()
    before = allocate_prefix(row, units, "criterion_floor")
    row.update(expected_source_ids=["3"], reference_outcome="unused")
    assert allocate_prefix(row, units, "criterion_floor") == before
