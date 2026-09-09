"""Author explicit synthetic validation fixtures and independent expected outcomes.

This does not label real patients and never obtains expected outcomes from the engine.
The structured addenda intentionally exercise canonical rule fields beyond prose parsing.
"""

import json
from pathlib import Path

from occupational_fitness_rag.provenance import sha256_bytes, write_json

ROOT = Path(__file__).resolve().parents[1]
BASE = {
    "cardiovascular.blood_pressure.persistent_systolic": 120,
    "cardiovascular.blood_pressure.persistent_diastolic": 80,
    "vision.uncorrected.right.snellen": "6/6",
    "vision.uncorrected.left.snellen": "6/6",
    "vision.visual_field.confirmed_defect": False,
    "vision.diplopia.present": False,
    "vision.monocular": False,
    "hearing.clinical_assessment": "no_hearing_loss",
    "blackout.occurred": False,
    "diabetes.present": False,
}
MEETS = "meets_unconditional_standard"
MISSING = "insufficient_information"
CONDITIONAL = "may_meet_conditional_standard"
TEMP = "temporarily_unfit"
FAIL = "does_not_meet_standard"


def main():
    expectations, manifest = [], []

    def add(n, description, changes, module, outcome, triggered=(), not_triggered=(), missing=()):
        facts = {**BASE, **changes}
        case_id = f"SYN-EXT-{n:03d}"
        text = (
            "SYNTHETIC VALIDATION FIXTURE — NOT A REAL PATIENT\nCommercial driver assessment.\n"
            + description
            + "\n\nStructured assessment addendum (explicit documented facts; no inferred values):\n"
        )
        text += "".join(
            k + " = " + json.dumps(v, ensure_ascii=False) + "\n"
            for k, v in facts.items()
            if v is not None
        )
        path = ROOT / "data/cases/synthetic_expansion" / (case_id + ".txt")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        expectations.append(
            dict(
                case_id=case_id,
                input=path.relative_to(ROOT).as_posix(),
                module=module,
                expected_outcome=outcome,
                triggered_rules=list(triggered),
                not_triggered_rules=list(not_triggered),
                missing_fields=list(missing),
                label_origin="engineering_source_based_expectation",
                clinical_review_status="pending",
            )
        )
        manifest.append(
            dict(
                case_id=case_id,
                path=path.relative_to(ROOT).as_posix(),
                sha256=sha256_bytes(path.read_bytes()),
                origin="new_synthetic_expansion",
                purpose=description,
                split="development_regression",
                clinical_review_status="pending",
            )
        )

    add(1, "Complete normal screening across all five pilot modules.", {}, "all", MEETS)
    add(
        2,
        "Persistent systolic pressure just above the commercial boundary; conditional follow-up is not documented.",
        {
            "cardiovascular.blood_pressure.persistent_systolic": 171,
            "cardiovascular.blood_pressure.persistent_diastolic": 100,
        },
        "hypertension",
        MISSING,
        ["HTN-COM-UNCONDITIONAL-001"],
    )
    add(
        3,
        "A reported blackout is still being investigated.",
        {"blackout.occurred": True, "blackout.mechanism_status": "under_investigation"},
        "blackout",
        TEMP,
        ["BLK-COM-UNDIAGNOSED-001"],
        ["BLK-COM-SINGLE-WAIT-001"],
    )

    def blackout(count, years):
        return {
            "blackout.occurred": True,
            "blackout.mechanism_status": "undetermined_after_investigation",
            "blackout.diagnosis": "undetermined",
            "blackout.episodes_separated_by_24h_count": count,
            "blackout.years_since_last_event": years,
            "blackout.appropriate_specialist_information_available": True,
        }

    add(
        4,
        "A single uncertain blackout; 4.99 event-free years documented.",
        blackout(1, 4.99),
        "blackout",
        TEMP,
        ["BLK-COM-SINGLE-WAIT-001"],
    )
    add(
        5,
        "A single uncertain blackout; exactly five event-free years and specialist information documented.",
        blackout(1, 5),
        "blackout",
        CONDITIONAL,
        ["BLK-COM-CONDITIONAL-ELIGIBILITY-001"],
        ["BLK-COM-SINGLE-WAIT-001"],
    )
    add(
        6,
        "Recurrent uncertain blackouts separated by at least 24 hours; 9.99 event-free years.",
        blackout(2, 9.99),
        "blackout",
        TEMP,
        ["BLK-COM-RECURRENT-WAIT-001"],
    )
    add(
        7,
        "Recurrent uncertain blackouts separated by at least 24 hours; exactly ten event-free years with specialist information.",
        blackout(2, 10),
        "blackout",
        CONDITIONAL,
        ["BLK-COM-CONDITIONAL-ELIGIBILITY-001"],
        ["BLK-COM-RECURRENT-WAIT-001"],
    )
    add(
        8,
        "A blackout is diagnosed as hypoglycaemia; assess the cause under the diabetes chapter.",
        {
            "blackout.occurred": True,
            "blackout.mechanism_status": "diagnosed",
            "blackout.diagnosis": "hypoglycaemia",
        },
        "blackout",
        MISSING,
        ["BLK-COM-DIAGNOSED-REFERRAL-001"],
        ["BLK-COM-SINGLE-WAIT-001", "BLK-COM-RECURRENT-WAIT-001"],
    )
    add(
        9,
        "The report contains no blackout history information.",
        {"blackout.occurred": None},
        "blackout",
        MISSING,
        missing=["blackout.occurred"],
    )
    dm = {
        "diabetes.present": True,
        "diabetes.gestational": False,
        "diabetes.acutely_unwell": False,
        "diabetes.metabolically_unstable": False,
        "diabetes.severe_hypoglycaemic_event.occurred": False,
        "diabetes.recent_severe_hypoglycaemic_event": False,
        "diabetes.hypoglycaemia_awareness": True,
        "diabetes.regimen_minimises_hypoglycaemia": True,
        "diabetes.driving_relevant_end_organ_effects": False,
    }
    add(
        10,
        "Diabetes managed by diet and exercise only; driving-relevant comorbidities explicitly assessed.",
        {
            **dm,
            "diabetes.treatment_category": "diet_and_exercise_only",
            "diabetes.driving_relevant_comorbidity_status": "assessed_no_disqualifying_effect",
        },
        "diabetes",
        MEETS,
        ["DM-COM-DIET-001"],
    )
    add(
        11,
        "Non-insulin glucose-lowering therapy; all conditional table criteria and initial specialist information documented.",
        {
            **dm,
            "diabetes.treatment_category": "glucose_lowering_agent_non_insulin",
            "diabetes.initial_specialist_information_available": True,
        },
        "diabetes",
        CONDITIONAL,
        ["DM-COM-NONINSULIN-001", "DM-COM-NONINSULIN-CONDITIONAL-001"],
    )
    insulin = {
        **dm,
        "diabetes.treatment_category": "insulin",
        "diabetes.glucose_monitoring_records_months": 3,
        "diabetes.specialist_information_available": True,
    }
    add(
        12,
        "Insulin treatment with no lifetime severe hypoglycaemic event; monitoring records and specialist assessment documented.",
        insulin,
        "diabetes",
        CONDITIONAL,
        ["DM-COM-INSULIN-CONDITIONAL-001"],
        ["DM-COM-SEVERE-HYPO-WAIT-001"],
    )
    add(
        13,
        "Insulin-treated diabetes with a severe hypoglycaemic event two weeks ago.",
        {
            **insulin,
            "diabetes.severe_hypoglycaemic_event.occurred": True,
            "diabetes.severe_hypoglycaemic_event.weeks_since_last": 2,
            "diabetes.recent_severe_hypoglycaemic_event": True,
        },
        "diabetes",
        TEMP,
        ["DM-COM-SEVERE-HYPO-WAIT-001"],
        ["DM-COM-INSULIN-CONDITIONAL-001"],
    )
    add(
        14,
        "Severe hypoglycaemic event six weeks ago; current specialist assessment documents that the recent-event criterion is satisfied.",
        {
            **insulin,
            "diabetes.severe_hypoglycaemic_event.occurred": True,
            "diabetes.severe_hypoglycaemic_event.weeks_since_last": 6,
        },
        "diabetes",
        CONDITIONAL,
        ["DM-COM-INSULIN-CONDITIONAL-001"],
        ["DM-COM-SEVERE-HYPO-WAIT-001"],
    )
    add(
        15,
        "Diabetes with acute illness and metabolic instability.",
        {
            **dm,
            "diabetes.treatment_category": "other",
            "diabetes.acutely_unwell": True,
            "diabetes.metabolically_unstable": True,
        },
        "diabetes",
        TEMP,
        ["DM-COM-ACUTE-UNSTABLE-001"],
    )
    add(
        16,
        "Gestational diabetes treated with insulin; chronic insulin licensing row must not be applied.",
        {**insulin, "diabetes.gestational": True},
        "diabetes",
        MISSING,
        ["DM-COM-GESTATIONAL-REVIEW-001"],
        ["DM-COM-INSULIN-001"],
    )
    add(
        17,
        "A confirmed four-frequency better-ear hearing average is exactly 40 dB; aided assessment is missing.",
        {
            "hearing.clinical_assessment": "possible_hearing_loss",
            "hearing.audiometry.available": True,
            "hearing.unaided_better_ear_average_db": 40,
            "hearing.average_frequencies_khz": [0.5, 1, 2, 3],
        },
        "hearing",
        MISSING,
        ["HEAR-COM-UNCONDITIONAL-001"],
    )
    add(
        18,
        "Non-physiological diplopia within twenty degrees of central fixation is documented.",
        {
            "vision.diplopia.present": True,
            "vision.diplopia.physiological": False,
            "vision.diplopia.within_20_degrees": True,
        },
        "vision",
        FAIL,
        ["VIS-COM-DIPLOPIA-001"],
    )
    add(
        19,
        "Persistent pressure exactly at both commercial thresholds; strict greater-than boundary test.",
        {
            "cardiovascular.blood_pressure.persistent_systolic": 170,
            "cardiovascular.blood_pressure.persistent_diastolic": 100,
        },
        "hypertension",
        MEETS,
        ["HTN-COM-SCREEN-001"],
        ["HTN-COM-UNCONDITIONAL-001"],
    )
    add(
        20,
        "Confirmed four-frequency unaided hearing below the 40 dB boundary.",
        {
            "hearing.clinical_assessment": "possible_hearing_loss",
            "hearing.audiometry.available": True,
            "hearing.unaided_better_ear_average_db": 39.9,
            "hearing.average_frequencies_khz": [0.5, 1, 2, 3],
        },
        "hearing",
        MEETS,
        ["HEAR-COM-SCREEN-001"],
        ["HEAR-COM-UNCONDITIONAL-001"],
    )
    for n, module, missing, not_triggered in [
        (
            3,
            "hypertension",
            ["cardiovascular.blood_pressure.persistent_systolic"],
            ["HTN-COM-UNCONDITIONAL-001"],
        ),
        (9, "hearing", ["hearing.average_frequencies_khz"], ["HEAR-COM-UNCONDITIONAL-001"]),
        (10, "hearing", ["hearing.unaided_better_ear_average_db"], []),
    ]:
        expectations.append(
            dict(
                case_id=f"SYN-M2-{n:03d}",
                input=f"data/cases/nurse_notes/SYN-M2-{n:03d}.txt",
                module=module,
                expected_outcome=MISSING,
                triggered_rules=[],
                not_triggered_rules=not_triggered,
                missing_fields=missing,
                label_origin="engineering_source_based_expectation",
                clinical_review_status="pending",
            )
        )
    write_json(ROOT / "data/cases/synthetic_expansion/manifest.json", manifest)
    write_json(
        ROOT / "data/cases/gold/workflow_expectations.json",
        {
            "schema_version": "1.2.0",
            "split": "development_regression",
            "independent_clinical_gold": False,
            "cases": expectations,
        },
    )
    print("Authored 20 new synthetic inputs and 23 explicit regression expectations")


if __name__ == "__main__":
    main()
