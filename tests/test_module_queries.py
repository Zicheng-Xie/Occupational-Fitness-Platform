"""Module query isolation and faithful input rendering, without clinical labels."""

from copy import deepcopy
from hashlib import sha256

import pytest

from occupational_fitness_rag.evaluation.module_queries import build_module_query


def test_query_uses_only_requested_module_verified_fields_and_original_quotes():
    payload = {
        "modules": ["vision", "diabetes"],
        "licence_context": "commercial",
        "nurse_note": "UNVERIFIED_NOTE_SENTINEL",
        "verified_patient_facts": {
            "vision.diplopia.present": {
                "value": True,
                "patient_quotes": ["The ophthalmologist documents double vision."],
            },
            "diabetes.present": {"value": True, "patient_quotes": ["OTHER_MODULE_SENTINEL"]},
        },
    }
    before = deepcopy(payload)
    query, audit = build_module_query(payload, "vision")
    assert "vision diplopia present = true" in query
    assert "The ophthalmologist documents double vision." in query
    assert "UNVERIFIED_NOTE_SENTINEL" not in query
    assert "OTHER_MODULE_SENTINEL" not in query
    assert audit["field_names"] == ["vision.diplopia.present"]
    assert audit["query_sha256"] == sha256(query.encode("utf-8")).hexdigest()
    assert audit["query_utf8_bytes"] == len(query.encode("utf-8"))
    assert payload == before


def test_false_zero_and_quoted_negation_history_subject_are_preserved():
    original = "Mother had fainting; the driver denies blackout now, and a remote episode remains uncertain."
    payload = {
        "modules": ["blackout"],
        "verified_patient_facts": {
            "blackout.occurred": {"value": False, "patient_quotes": [original]},
            "blackout.recorded_count": {"value": 0, "patient_quotes": []},
        },
    }
    query, audit = build_module_query(payload, "blackout")
    assert "blackout occurred = false" in query
    assert "blackout recorded count = 0" in query
    assert original in query
    assert audit["patient_quotes"] == [original]
    assert audit["no_documented_facts"] is False


def test_whitespace_dedup_retains_first_verbatim_string():
    original = "  Current assessment:\nno hearing loss.  "
    payload = {
        "modules": ["hearing"],
        "verified_patient_facts": {
            "hearing.a": {"value": False, "patient_quotes": [original]},
            "hearing.b": {
                "value": False,
                "patient_quotes": ["Current assessment: no hearing loss.", "   "],
            },
        },
    }
    query, audit = build_module_query(payload, "hearing")
    assert audit["patient_quotes"] == [original]
    assert original in query
    assert query.count("no hearing loss.") == 1


def test_missing_or_unverified_fields_do_not_invent_facts_or_use_note_fallback():
    payload = {
        "modules": ["diabetes"],
        "nurse_note": "UNVERIFIED_SEVERE_SYMPTOM_SENTINEL",
        "verified_patient_facts": {
            "diabetes.a": {"value": None, "patient_quotes": ["MISSING_QUOTE"]},
            "diabetes.b": {
                "value": True,
                "status": "requires_confirmation",
                "patient_quotes": ["UNCONFIRMED_QUOTE"],
            },
        },
    }
    query, audit = build_module_query(payload, "diabetes")
    assert query == "diabetes commercial driving medical fitness standard"
    assert audit["no_documented_facts"] is True
    assert audit["field_names"] == []
    assert audit["patient_quotes"] == []


def test_cardiovascular_fields_map_to_hypertension_with_patient_value_unchanged():
    payload = {
        "modules": ["hypertension"],
        "verified_patient_facts": {
            "cardiovascular.blood_pressure.persistent_systolic": {
                "value": 123.4,
                "patient_quotes": ["Persistent systolic pressure measured 123.4."],
            },
        },
    }
    query, audit = build_module_query(payload, "hypertension")
    assert "cardiovascular blood pressure persistent systolic = 123.4" in query
    assert audit["field_values"] == {"cardiovascular.blood_pressure.persistent_systolic": 123.4}


def test_rules_labels_expected_ids_threshold_metadata_and_extra_modules_cannot_change_query():
    payload = {
        "modules": ["vision"],
        "verified_patient_facts": {
            "vision.a": {"value": False, "patient_quotes": ["No diplopia."]}
        },
    }
    clean = build_module_query(payload, "vision")
    payload.update(
        reference_outcome="GOLD_SENTINEL",
        rule_outcome="RULE_SENTINEL",
        expected_source_ids=["SOURCE_SENTINEL"],
        clinical_thresholds={"vision.a": "THRESHOLD_SENTINEL"},
        guideline_evidence=[{"source_id": "EVIDENCE_SENTINEL", "source_text": "DO_NOT_COPY"}],
    )
    assert build_module_query(payload, "vision") == clean
    payload["modules"].append("hearing")
    assert build_module_query(payload, "vision") == clean


@pytest.mark.parametrize("module", ["diabetes", "unknown"])
def test_out_of_scope_module_is_rejected(module):
    with pytest.raises(ValueError, match="requested"):
        build_module_query({"modules": ["vision"], "verified_patient_facts": {}}, module)


def test_noncommercial_context_and_nonverbatim_quote_records_are_rejected():
    with pytest.raises(ValueError, match="commercial"):
        build_module_query(
            {"modules": ["vision"], "licence_context": "private", "verified_patient_facts": {}},
            "vision",
        )
    with pytest.raises(ValueError, match="original strings"):
        build_module_query(
            {
                "modules": ["vision"],
                "verified_patient_facts": {"vision.a": {"value": True, "patient_quotes": "text"}},
            },
            "vision",
        )
