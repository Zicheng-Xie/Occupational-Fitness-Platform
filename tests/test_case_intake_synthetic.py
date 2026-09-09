from pathlib import Path

from occupational_fitness_rag.case_intake.batch import prepare_case_directory
from occupational_fitness_rag.case_intake.evaluation import exact_field_accuracy, load_jsonl

ROOT = Path(__file__).resolve().parents[1]


def test_all_ten_supplied_cases_are_loaded():
    results = prepare_case_directory(ROOT / "data/cases/nurse_notes")
    assert len(results) == 10
    assert [r.case_id for r in results] == [f"SYN-M2-{i:03d}" for i in range(1, 11)]


def test_fixture_extraction_matches_curated_gold():
    results = prepare_case_directory(ROOT / "data/cases/nurse_notes")
    predictions = [r.model_dump(mode="json") for r in results]
    gold = load_jsonl(ROOT / "data/cases/gold/structured_cases.jsonl")
    metrics = exact_field_accuracy(predictions, gold)
    assert metrics["field_accuracy"] == 1.0


def test_explicit_missing_information_is_preserved():
    by_id = {r.case_id: r for r in prepare_case_directory(ROOT / "data/cases/nurse_notes")}
    assert by_id["SYN-M2-003"].explicit_missing == ["repeat_blood_pressure"]
    assert by_id["SYN-M2-005"].explicit_missing == ["specialist_report"]
    assert by_id["SYN-M2-008"].explicit_missing == ["optometrist_report"]
    assert by_id["SYN-M2-009"].explicit_missing == ["audiologist_report"]
    assert by_id["SYN-M2-010"].explicit_missing == ["audiometry_or_audiogram"]


def test_category_map_stays_non_diagnostic():
    result = prepare_case_directory(ROOT / "data/cases/nurse_notes")[5]
    assert [x.category for x in result.category_map] == ["cardiovascular", "vision", "hearing"]
    assert all("fitness" not in str(x.model_dump()).lower() for x in result.category_map)
