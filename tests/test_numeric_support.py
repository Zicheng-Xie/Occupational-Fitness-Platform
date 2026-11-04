"""Exact source-addressed arithmetic must not become a clinical decision."""

from copy import deepcopy

import pytest

from occupational_fitness_rag.evaluation.numeric_support import numeric_relations


def payload(module, field, value, text):
    return {
        "licence_context": "commercial", "modules": [module], "nurse_note": "Synthetic input",
        "verified_patient_facts": {field: {"value": value, "patient_quotes": ["Synthetic fact"]}},
        "guideline_evidence": [{
            "source_id": "synthetic-original", "source_text": text, "module": module,
            "section": "fixture", "pdf_page": 1, "printed_page": 1,
        }],
    }


def test_boundary_is_compared_as_decimal_with_an_exact_unicode_source_address():
    text = "Synthetic original \U0001f600: at least 10 years; review at 5 years."
    item = payload("blackout", "blackout.years_since_last_event", 9.99, text)
    before = deepcopy(item)
    rows = numeric_relations(item)
    assert [(r["source_number_literal"], r["relation"]) for r in rows] == [
        ("10", "less_than"), ("5", "greater_than"),
    ]
    assert rows[0]["exact_difference"] == "-0.01"
    for row in rows:
        assert text[row["char_start"]:row["char_end"]] == row["original_quote"]
        assert "outcome" not in row and "applicable" not in row and "rule_id" not in row
    assert item == before


def test_systolic_and_diastolic_literals_do_not_get_swapped():
    item = payload(
        "hypertension", "cardiovascular.blood_pressure.persistent_systolic", 171,
        "Synthetic original: > 170 systolic or > 100 diastolic.",
    )
    item["verified_patient_facts"]["cardiovascular.blood_pressure.persistent_diastolic"] = {
        "value": 100, "patient_quotes": ["Synthetic diastolic fact"],
    }
    rows = numeric_relations(item)
    assert [(r["patient_value"], r["source_number_literal"], r["relation"]) for r in rows] == [
        (171, "170", "greater_than"), (100, "100", "equal_to"),
    ]
    # No OR/AND result or medical standard is inserted by the arithmetic tool.
    assert len(rows) == 2


@pytest.mark.parametrize("value", [True, "40", float("nan"), float("inf")])
def test_non_numeric_or_non_finite_values_are_rejected(value):
    item = payload("hearing", "hearing.unaided_better_ear_average_db", value, "Synthetic original >= 40 dB.")
    with pytest.raises(ValueError, match="numeric scalar|non-finite"):
        numeric_relations(item)


def test_zero_is_kept_missing_is_unknown_and_foreign_modules_are_not_matched():
    item = payload("hearing", "hearing.unaided_better_ear_average_db", 0, "Synthetic original >= 40 dB.")
    assert numeric_relations(item)[0]["patient_value"] == 0
    item["verified_patient_facts"]["hearing.unaided_better_ear_average_db"]["value"] = None
    assert numeric_relations(item) == []
    item["verified_patient_facts"] = {
        "blackout.years_since_last_event": {"value": 9.99, "patient_quotes": ["Synthetic"]},
    }
    assert numeric_relations(item) == []
