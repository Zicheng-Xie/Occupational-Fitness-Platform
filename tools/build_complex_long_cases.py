"""Author 200 guideline-grounded English synthetic long-note stress inputs.

Forty scenario families have five documented variants each. They are correlated
engineering fixtures, not 200 independently sampled or clinician-labelled people.
Reference outcomes and source IDs are saved outside the upload directory.
"""

from __future__ import annotations

import json
import random
import re
from collections import Counter
from pathlib import Path

from occupational_fitness_rag.ingestion.source_catalogue import SourceCatalogue
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json

ROOT = Path(__file__).resolve().parents[1]
NOTES = "data/cases/complex_nurse_notes"
GOLD = "data/cases/gold/complex_long_200.json"
MANIFEST = NOTES + "/long_200_manifest.json"
MEETS = "meets_unconditional_standard"
CONDITIONAL = "may_meet_conditional_standard"
TEMPORARY = "temporarily_unfit"
EXCLUDED = "does_not_meet_standard"
UNKNOWN = "insufficient_information"
PRECEDENCE = [EXCLUDED, TEMPORARY, UNKNOWN, CONDITIONAL, MEETS]


def scenario(module, name, text, facts, sources, outcome, *, withheld=(), challenges=()):
    return dict(
        module=module,
        family=name,
        text=text,
        facts=facts,
        sources=sources,
        outcome=outcome,
        withheld=list(withheld),
        challenges=list(challenges),
    )


def blueprints(v):
    # Values are authored before any model output; no production evaluator is
    # called to manufacture the reference answer.
    sbp = [176, 182, 174, 188, 179][v]
    dbp = [102, 106, 104, 108, 103][v]
    near_sbp = [170, 169, 170, 168, 170][v]
    near_dbp = [100, 100, 99, 100, 100][v]
    hearing = [40, 42, 45, 48, 41][v]
    low_hearing = [39, 38, 35, 37, 39.5][v]
    years = [4.9, 4.5, 3.8, 4.99, 2.7][v]
    recurrent_years = [9.9, 9.5, 8.7, 9.99, 7.5][v]
    weeks = [2, 3, 4, 5, 1][v]
    p = "cardiovascular.blood_pressure."
    h = "cardiovascular.hypertension."
    freq = [0.5, 1, 2, 3]
    return [
        scenario(
            "hypertension",
            "persistent_systolic_elevation",
            f"The current signed clinic summary documents persistent BP {sbp}/96 mmHg after repeated seated measurements across separate visits, rather than the first reading taken while unloading; the driver describes pressure-like headaches after long shifts but has no current chest pain, while the dates of resumed treatment, sustained control and the specialist's initial assessment cannot be confirmed from the documents available today.",
            {p + "persistent_systolic": sbp, p + "persistent_diastolic": 96},
            ["HTN-COM-001", "HTN-COM-002"],
            UNKNOWN,
            withheld=[h + "controlled_for_4_weeks"],
            challenges=["persistent_vs_observed", "missing_qualification"],
        ),
        scenario(
            "hypertension",
            "isolated_diastolic_elevation",
            f"Although the driver repeatedly points to a systolic figure of 158 as reassurance, the dated treating-doctor record confirms persistent BP 158/{dbp} mmHg after repeat resting checks, and the nurse separately records the lower and upper pressures; the driver cannot provide the specialist information or demonstrate a four-week period of effective treatment, and his account of an old normal check does not replace today's documented diastolic pattern.",
            {p + "persistent_systolic": 158, p + "persistent_diastolic": dbp},
            ["HTN-COM-001", "HTN-COM-002"],
            UNKNOWN,
            challenges=["or_condition", "diastolic_only", "historical_decoy"],
        ),
        scenario(
            "hypertension",
            "strict_boundary_pressure",
            f"After the initial arrival reading was discarded because the cuff was slipping, repeat measurements over several visits were reviewed by the treating doctor, who documents persistent BP {near_sbp}/{near_dbp} mmHg with the correct cuff and seated rest; the driver has no current cardiac symptoms, and a depot worker's much higher figure belongs to another person rather than a second measurement of this driver.",
            {p + "persistent_systolic": near_sbp, p + "persistent_diastolic": near_dbp},
            ["HTN-COM-001"],
            MEETS,
            challenges=["strict_numeric_boundary", "other_person"],
        ),
        scenario(
            "hypertension",
            "unverified_home_pressure",
            f"A cropped phone photograph displays {sbp}/{dbp} mmHg without a patient identifier or date, whereas today's single observed blood pressure is 146/88 mmHg after rest; the driver says the photograph may have been taken before he restarted tablets, the home monitor has not been checked, and the nurse has no repeated current measurements from which to establish persistent systolic or diastolic pressure.",
            {p + "observed_systolic": 146, p + "observed_diastolic": 88},
            ["HTN-COM-001", "HTN-COM-002"],
            UNKNOWN,
            withheld=[p + "persistent_systolic", p + "persistent_diastolic"],
            challenges=["unsigned_measurement", "temporal_uncertainty"],
        ),
        scenario(
            "hypertension",
            "historical_hypertension_current_control",
            f"The nurse separates last year's untreated readings of {sbp}/{dbp} mmHg from the current dated clinic record, which confirms persistent BP 134/82 mmHg on repeated measurements during the present review; the driver reports no current chest pain or breathlessness, and a family member's stroke is recorded as family history rather than a cardiovascular event experienced by the driver.",
            {
                p + "persistent_systolic": 134,
                p + "persistent_diastolic": 82,
                "cardiovascular.chest_pain": False,
            },
            ["HTN-COM-001"],
            MEETS,
            challenges=["history_vs_current", "family_history", "negation"],
        ),
        scenario(
            "hypertension",
            "treatment_restart_incomplete_followup",
            f"The driver restarted antihypertensive tablets twelve days ago after a period of missed doses, and the current clinic letter still records persistent BP {sbp}/{dbp} mmHg on repeat checks; a four-week follow-up period has not yet been completed, the driver brings a booking confirmation rather than a specialist opinion, and occasional improvement on a home display cannot establish sustained control or the absence of relevant treatment problems.",
            {
                p + "persistent_systolic": sbp,
                p + "persistent_diastolic": dbp,
                h + "antihypertensive_therapy": True,
                h + "controlled_for_4_weeks": False,
                h + "initial_specialist_information_available": False,
            },
            ["HTN-COM-001", "HTN-COM-002"],
            UNKNOWN,
            challenges=["incomplete_waiting_period", "appointment_vs_result"],
        ),
        scenario(
            "hypertension",
            "medication_tolerance_concern",
            f"The current doctor-reviewed series confirms persistent BP {sbp}/{dbp} mmHg while the driver is taking antihypertensive therapy, but the medication review also documents dizziness that impairs safe vehicle operation after the morning dose; although the driver feels better when sitting still in the interview, the nurse has no evidence that the side effect has resolved, and a proposed future dose change is not recorded as an accomplished treatment outcome.",
            {
                p + "persistent_systolic": sbp,
                p + "persistent_diastolic": dbp,
                h + "antihypertensive_therapy": True,
                h + "driving_impairing_medication_side_effects": True,
            },
            ["HTN-COM-001", "HTN-COM-002"],
            UNKNOWN,
            challenges=["conditional_prerequisite_failed", "symptom_context"],
        ),
        scenario(
            "hypertension",
            "family_history_without_current_measurement",
            "The driver's father required treatment for high blood pressure and a brother recently had a stroke, but the driver is describing their histories rather than his own diagnosis; he recalls a high pharmacy-machine number after a night shift without knowing the value, no current repeated blood-pressure series is available, and headaches attributed to noise and poor sleep have not been linked to a documented persistent pressure measurement.",
            {},
            ["HTN-COM-001"],
            UNKNOWN,
            withheld=[p + "persistent_systolic", p + "persistent_diastolic"],
            challenges=["other_person", "no_confirmed_numeric_fact"],
        ),
        scenario(
            "vision",
            "confirmed_central_diplopia",
            f"The current ophthalmologist's signed examination confirms non-physiological diplopia within {[12, 15, 18, 10, 19][v]} degrees of central fixation, reproduced during the assessment even though the driver says the two overlapping road-sign images sometimes merge after blinking; an older note reported comfortable reading at a desk, but that earlier description neither contradicts the current reproduced double vision nor establishes that a patch or new lenses have resolved it.",
            {
                "vision.diplopia.present": True,
                "vision.diplopia.physiological": False,
                "vision.diplopia.within_20_degrees": True,
            },
            ["VIS-COM-007"],
            EXCLUDED,
            challenges=[
                "intermittent_symptom",
                "commercial_private_difference",
                "historical_decoy",
            ],
        ),
        scenario(
            "vision",
            "unconfirmed_double_images",
            "The driver describes two offset images of headlights late in a long shift, with improvement when either eye is covered, yet no episode occurs during today's short appointment; the nurse records a suspected symptom rather than a confirmed diagnosis, the position relative to central fixation is not measured, and neither a specialist assessment nor the distinction between physiological and pathological diplopia is available in the current record.",
            {},
            ["VIS-COM-007"],
            UNKNOWN,
            withheld=["vision.diplopia.within_20_degrees", "vision.diplopia.physiological"],
            challenges=["symptom_vs_diagnosis", "missing_angle"],
        ),
        scenario(
            "vision",
            "measured_correction_pathway",
            "The optometrist's current signed sheet records uncorrected visual acuity of 6/12 in the right eye and 6/18 in the left eye, then records corrected visual acuity of 6/6 in the right eye and 6/9 in the left eye with the prescribed lenses; the same specialist assessment documents no visual field defect, no diplopia and binocular rather than monocular vision, while the driver's recollection of driving comfortably without spectacles is retained as an account of behaviour rather than an alternative measurement.",
            {
                "vision.uncorrected.right.snellen": "6/12",
                "vision.uncorrected.left.snellen": "6/18",
                "vision.corrected.right.snellen": "6/6",
                "vision.corrected.left.snellen": "6/9",
                "vision.specialist_assessment_available": True,
                "vision.visual_field.confirmed_defect": False,
                "vision.diplopia.present": False,
                "vision.monocular": False,
            },
            ["VIS-COM-002", "VIS-COM-003"],
            CONDITIONAL,
            challenges=["uncorrected_vs_corrected", "qualified_pathway"],
        ),
        scenario(
            "vision",
            "current_normal_screen_old_slip",
            "Before spectacles were applied, today's separately tested uncorrected visual acuity is 6/6 in each eye, and the current clinician documents no visual field defect, no diplopia and no monocular vision; an old training form listing 6/18 is identified as a previous record with unspecified test conditions, so it is not substituted for the current examination when the driver describes occasional glare from a dirty windscreen after sunset.",
            {
                "vision.uncorrected.right.snellen": "6/6",
                "vision.uncorrected.left.snellen": "6/6",
                "vision.visual_field.confirmed_defect": False,
                "vision.diplopia.present": False,
                "vision.monocular": False,
            },
            ["VIS-COM-002", "VIS-COM-004", "VIS-COM-007"],
            MEETS,
            challenges=["negative_control", "older_document", "environmental_symptom"],
        ),
        scenario(
            "vision",
            "ambiguous_acuity_columns",
            "A loose slip lists 6/12 and 6/18 beside one date and 6/6 and 6/9 beside another, but neither column identifies the eye or whether corrective lenses were worn; the driver thinks the better pair belongs to the newer glasses, the clinic has requested the original signed report, and no current corrected or uncorrected acuity can be attributed to a particular eye from the cropped copy brought to this interview.",
            {},
            ["VIS-COM-002", "VIS-COM-003"],
            UNKNOWN,
            withheld=[
                "vision.uncorrected.right.snellen",
                "vision.uncorrected.left.snellen",
                "vision.corrected.better_eye",
            ],
            challenges=["column_ambiguity", "unverified_measurements"],
        ),
        scenario(
            "vision",
            "field_defect_incomplete_qualification",
            f"A current signed perimetry assessment confirms a visual field defect and reports a binocular horizontal extent of {[132, 135, 138, 130, 139][v]} degrees, although the driver can still read central letters clearly and points to an earlier normal acuity result; the report does not establish the required vertical test extent, stability of the field loss or whether other significant defects affect driving, and the specialist's detailed functional opinion remains pending.",
            {
                "vision.visual_field.confirmed_defect": True,
                "vision.visual_field.binocular_horizontal_extent_degrees": [
                    132,
                    135,
                    138,
                    130,
                    139,
                ][v],
            },
            ["VIS-COM-004", "VIS-COM-005"],
            UNKNOWN,
            withheld=["vision.visual_field.static_and_unlikely_to_progress_rapidly"],
            challenges=["acuity_vs_field", "missing_qualification"],
        ),
        scenario(
            "vision",
            "monocular_specialist_assessment",
            "The current ophthalmologist confirms monocular vision following a remote injury and measures visual acuity of 6/9 in the remaining eye, with a horizontal field of 145 degrees measured within 10 degrees above and below the horizontal midline; the signed specialist report explicitly finds no other significant field loss likely to impede driving, whereas an old binocular screening entry describes the driver's condition before the injury and is retained only as historical context.",
            {
                "vision.monocular": True,
                "vision.remaining_eye.snellen": "6/9",
                "vision.remaining_eye.horizontal_field_degrees": 145,
                "vision.remaining_eye.field_measured_within_10_degrees_vertical": True,
                "vision.remaining_eye.other_significant_field_loss": False,
                "vision.specialist_assessment_available": True,
                "vision.diplopia.present": False,
            },
            ["VIS-COM-006"],
            CONDITIONAL,
            challenges=["remaining_eye", "history_vs_current", "commercial_scope"],
        ),
        scenario(
            "vision",
            "unreliable_field_printout",
            "The driver sometimes notices vehicles late on the left and brings a field printout marked 140 degrees, but its reliability flag is poor and the treating optometrist has not confirmed a defect or a valid horizontal extent; central letters seem clear to the driver, no complete specialist interpretation is attached, and the nurse records the symptoms and the unreliable test separately rather than converting either into a confirmed static visual field disorder.",
            {},
            ["VIS-COM-004", "VIS-COM-005"],
            UNKNOWN,
            withheld=["vision.visual_field.binocular_horizontal_extent_degrees"],
            challenges=["unreliable_test", "symptom_vs_measurement"],
        ),
        scenario(
            "hearing",
            "normal_clinical_screen",
            "The current clinician's recorded hearing assessment finds no hearing loss after examining the driver in suitable conditions, although yesterday's radio conversation was difficult when the cab speaker crackled and the windows were open; a colleague who uses hearing aids is mentioned in the same discussion, but those aids belong to the colleague, and an undated employer checklist is not used to replace today's completed clinical assessment.",
            {"hearing.clinical_assessment": "no_hearing_loss"},
            ["HEAR-COM-001", "HEAR-COM-002"],
            MEETS,
            challenges=["other_person", "equipment_vs_symptom", "negative_control"],
        ),
        scenario(
            "hearing",
            "unaided_below_threshold",
            f"The audiologist's current signed report documents an unaided better-ear average of {low_hearing} dB over 0.5, 1, 2 and 3 kHz, with no aid worn during the measurements and audiometry explicitly completed; the driver sometimes turns the volume up for traffic updates in a noisy loading area, but the nurse separates that environmental complaint from the identified ear, frequencies and unaided testing conditions in the report.",
            {
                "hearing.audiometry.available": True,
                "hearing.average_frequencies_khz": freq,
                "hearing.unaided_better_ear_average_db": low_hearing,
                "hearing.hearing_aid_used": False,
            },
            ["HEAR-COM-002"],
            MEETS,
            challenges=["below_boundary", "test_conditions"],
        ),
        scenario(
            "hearing",
            "aided_qualification_at_boundary",
            f"A signed audiologist assessment records unaided better-ear average hearing loss of {hearing} dB over 0.5, 1, 2 and 3 kHz, then separately confirms that the required hearing standard is met when the prescribed hearing aid is worn; audiometry is complete and the audiologist's information is available, while the driver's earlier comment that conversation was satisfactory without the aid is not entered as a normal unaided clinical assessment.",
            {
                "hearing.audiometry.available": True,
                "hearing.average_frequencies_khz": freq,
                "hearing.unaided_better_ear_average_db": hearing,
                "hearing.hearing_aid_used": True,
                "hearing.aided_standard_met": True,
                "hearing.ent_or_audiologist_information_available": True,
            },
            ["HEAR-COM-002", "HEAR-COM-003"],
            CONDITIONAL,
            challenges=["exact_40_boundary", "aided_vs_unaided", "specialist_information"],
        ),
        scenario(
            "hearing",
            "aided_only_measurement",
            "The available test sheet reports a hearing average of 32 dB while both hearing aids were worn, but it does not supply an unaided better-ear result or a complete frequency list; the driver is able to follow a quiet face-to-face exchange yet repeatedly misses radio instructions beside an idling engine, and the nurse documents possible hearing loss without treating the aided number as an unaided threshold or assuming that all commercial assessment requirements were tested.",
            {
                "hearing.hearing_aid_used": True,
                "hearing.clinical_assessment": "possible_hearing_loss",
            },
            ["HEAR-COM-001", "HEAR-COM-002", "HEAR-COM-003"],
            UNKNOWN,
            withheld=["hearing.unaided_better_ear_average_db", "hearing.average_frequencies_khz"],
            challenges=["aided_only", "missing_frequencies"],
        ),
        scenario(
            "hearing",
            "unaided_loss_pending_aided_test",
            f"The completed audiogram identifies unaided better-ear average hearing loss of {hearing} dB across 0.5, 1, 2 and 3 kHz, and the current clinical assessment records possible hearing loss; a hearing aid has been ordered rather than functionally assessed, the audiologist's advice about aided performance is not yet available, and the driver's belief that amplification will solve the difficulty is retained as an expectation rather than evidence that an aided standard has already been met.",
            {
                "hearing.audiometry.available": True,
                "hearing.clinical_assessment": "possible_hearing_loss",
                "hearing.average_frequencies_khz": freq,
                "hearing.unaided_better_ear_average_db": hearing,
                "hearing.ent_or_audiologist_information_available": False,
            },
            ["HEAR-COM-002", "HEAR-COM-003"],
            UNKNOWN,
            withheld=["hearing.aided_standard_met"],
            challenges=["ordered_vs_completed", "unknown_qualification"],
        ),
        scenario(
            "hearing",
            "aid_inadequate_individual_assessment",
            f"The audiologist reports an unaided better-ear average of {hearing + 10} dB over 0.5, 1, 2 and 3 kHz and confirms that the hearing standard is not met with the currently fitted aid; the driver says speech is louder but less clear when the reversing alarm sounds, and the completed specialist letter recommends further individual assessment without supplying a practical driver assessment result or a finding that the present equipment resolves the functional difficulty.",
            {
                "hearing.audiometry.available": True,
                "hearing.average_frequencies_khz": freq,
                "hearing.unaided_better_ear_average_db": hearing + 10,
                "hearing.aided_standard_met": False,
                "hearing.ent_or_audiologist_information_available": True,
            },
            ["HEAR-COM-003", "HEAR-COM-004"],
            UNKNOWN,
            challenges=["failed_aided_qualification", "individual_assessment"],
        ),
        scenario(
            "hearing",
            "suspected_loss_without_audiometry",
            "The current nurse assessment records possible hearing loss after the driver repeatedly asks for spoken instructions to be repeated, while the driver explains that he can hear a television at home and an older employer form called his hearing satisfactory; audiometry has not been performed, the ENT appointment is booked rather than completed, and no quantified unaided threshold or qualified aided assessment is available to resolve the disagreement.",
            {
                "hearing.clinical_assessment": "possible_hearing_loss",
                "hearing.audiometry.available": False,
            },
            ["HEAR-COM-001"],
            UNKNOWN,
            withheld=["hearing.unaided_better_ear_average_db"],
            challenges=["conflicting_accounts", "missing_audiometry"],
        ),
        scenario(
            "hearing",
            "unsigned_conflicting_audiogram",
            f"An unsigned worksheet appears to show an unaided better-ear average of {hearing} dB, but its patient identifier and date are missing and the driver remembers wearing both aids for the test; the current nurse notes possible hearing loss after missed instructions, the original audiology report has been requested, and neither the worksheet nor the recollection establishes a verified unaided result or the complete set of averaging frequencies.",
            {
                "hearing.clinical_assessment": "possible_hearing_loss",
                "hearing.hearing_aid_used": True,
            },
            ["HEAR-COM-001", "HEAR-COM-002"],
            UNKNOWN,
            withheld=["hearing.unaided_better_ear_average_db", "hearing.average_frequencies_khz"],
            challenges=["unsigned_document", "contradictory_test_conditions"],
        ),
        scenario(
            "blackout",
            "confirmed_event_investigation_pending",
            f"A colleague witnessed the driver lose consciousness and fail to respond for {[12, 18, 25, 20, 15][v]} seconds during a break, and the current physician referral explicitly records a blackout with the mechanism under investigation; although the driver recalls heat, hunger and a racing heartbeat beforehand, neither syncope, seizure nor hypoglycaemia has been confirmed, cardiac monitoring is pending, and uncertainty about a remote dizzy spell does not erase the documented recent event.",
            {"blackout.occurred": True, "blackout.mechanism_status": "under_investigation"},
            ["BLK-COM-001", "BLK-COM-006"],
            TEMPORARY,
            challenges=["cross_disease_symptoms", "pending_mechanism", "witness_account"],
        ),
        scenario(
            "blackout",
            "disputed_awareness_episode",
            "The driver recalls a short gap in a radio conversation while seated after unloading, but a colleague says he remained responsive and might simply have been distracted by paperwork; the nurse cannot confirm loss of consciousness or a blackout from the conflicting accounts, a pulse reading taken later does not resolve awareness during the episode, and the physician has requested further history rather than diagnosing a specific cause.",
            {},
            ["BLK-COM-001", "BLK-COM-006"],
            UNKNOWN,
            withheld=["blackout.occurred", "blackout.diagnosis"],
            challenges=["conflicting_witness", "uncertain_event"],
        ),
        scenario(
            "blackout",
            "single_event_before_five_years",
            f"The specialist's completed investigation found no diagnosable cause for a single confirmed blackout, and the signed chronology documents one event with no further events over {years} years; the nurse records that this is a blackout of undetermined nature after investigation, rather than an investigation still pending, while an earlier faint in the driver's father is kept separate from the patient's event count and cannot create a recurrent patient history.",
            {
                "blackout.occurred": True,
                "blackout.mechanism_status": "undetermined_after_investigation",
                "blackout.episodes_separated_by_24h_count": 1,
                "blackout.years_since_last_event": years,
            },
            ["BLK-COM-003", "BLK-COM-004"],
            TEMPORARY,
            challenges=["strict_waiting_boundary", "post_investigation", "other_person"],
        ),
        scenario(
            "blackout",
            "single_event_after_five_years",
            f"A signed specialist review confirms a single blackout of undetermined nature after completed investigations, no recurrent blackout and an event-free interval of {[5, 5.5, 6, 7, 5.1][v]} years; appropriate specialist information is available for the commercial assessment, whereas the driver's recollection of feeling light-headed during a recent blood draw is explicitly documented as preserved awareness rather than another blackout, so it is not added to the confirmed event count.",
            {
                "blackout.occurred": True,
                "blackout.mechanism_status": "undetermined_after_investigation",
                "blackout.episodes_separated_by_24h_count": 1,
                "blackout.years_since_last_event": [5, 5.5, 6, 7, 5.1][v],
                "blackout.appropriate_specialist_information_available": True,
            },
            ["BLK-COM-003", "BLK-COM-004"],
            CONDITIONAL,
            challenges=["waiting_boundary_met", "specialist_information", "preserved_awareness"],
        ),
        scenario(
            "blackout",
            "recurrent_events_before_ten_years",
            f"The specialist's signed history confirms two blackouts separated by more than 24 hours, with the last event {recurrent_years} years ago and the mechanism still undetermined after completed investigations; the driver has had no more recent confirmed events, but the two episodes were not merely clustered in one day, and a family account that calls them one illness does not change the documented separation or the elapsed interval.",
            {
                "blackout.occurred": True,
                "blackout.mechanism_status": "undetermined_after_investigation",
                "blackout.episodes_separated_by_24h_count": 2,
                "blackout.years_since_last_event": recurrent_years,
            },
            ["BLK-COM-003", "BLK-COM-005"],
            TEMPORARY,
            challenges=["recurrent_vs_clustered", "ten_year_boundary"],
        ),
        scenario(
            "blackout",
            "provoked_vasovagal_exception",
            "The treating specialist confirms vasovagal syncope during venepuncture, identifies the well-defined provoking factor and explicitly assesses recurrence while driving as unlikely; the driver describes nausea and sweating before that observed faint, but has not had unprovoked events, and the nurse records the specialist's current assessment separately from a draft referral that had initially listed arrhythmia as an unconfirmed differential diagnosis.",
            {
                "blackout.occurred": True,
                "blackout.diagnosis": "vasovagal_syncope",
                "blackout.provoking_factor_well_defined": True,
                "blackout.recurrence_while_driving_unlikely": True,
                "blackout.mechanism_status": "diagnosed",
            },
            ["BLK-COM-002", "BLK-COM-006"],
            MEETS,
            challenges=["specific_exception", "differential_vs_diagnosis"],
        ),
        scenario(
            "blackout",
            "no_patient_history_family_faint",
            "The driver explicitly denies any lifetime blackout, loss of consciousness or episode of impaired awareness, and the current nurse history confirms no blackout history; a sister's faint after standing in a hot room is recorded as family information, while the driver's own tiredness after an overnight route occurred with preserved awareness and no witness-reported unresponsiveness, rather than a confirmed episode being denied or reclassified after the fact.",
            {"blackout.occurred": False},
            ["BLK-COM-001"],
            MEETS,
            challenges=["negation_scope", "family_history", "fatigue_not_blackout"],
        ),
        scenario(
            "blackout",
            "diagnosed_hypoglycaemic_referral",
            "The hospital discharge report confirms that the driver's documented loss of consciousness was caused by hypoglycaemia after investigation, rather than remaining of undetermined nature; the current referral therefore names hypoglycaemia as the diagnosis, but the diabetes treatment history, recurrence risk and return-to-driving specialist advice are not attached, and a glucose value obtained after treatment cannot supply the missing longitudinal assessment.",
            {
                "blackout.occurred": True,
                "blackout.mechanism_status": "diagnosed",
                "blackout.diagnosis": "hypoglycaemia",
            },
            ["BLK-COM-006"],
            UNKNOWN,
            challenges=["cross_chapter_referral", "known_cause", "missing_longitudinal_data"],
        ),
        scenario(
            "diabetes",
            "diet_exercise_assessed_comorbidity",
            "The current GP and medication review confirm established type 2 diabetes managed by diet and exercise alone, with no glucose-lowering medicine or insulin prescribed, and document that driving-relevant comorbidities have been assessed with no disqualifying effect; the driver mentions that an uncle uses injections, but those medicines belong to the uncle, and a previous referral proposing tablets was never implemented as a current treatment change.",
            {
                "diabetes.present": True,
                "diabetes.treatment_category": "diet_and_exercise_only",
                "diabetes.driving_relevant_comorbidity_status": "assessed_no_disqualifying_effect",
                "diabetes.gestational": False,
                "diabetes.acutely_unwell": False,
                "diabetes.metabolically_unstable": False,
            },
            ["DM-COM-004"],
            MEETS,
            challenges=["other_person_medication", "proposed_vs_current", "comorbidity_assessment"],
        ),
        scenario(
            "diabetes",
            "noninsulin_specialist_qualification",
            "The signed current medication list confirms diabetes treated with glucose-lowering tablets other than insulin, and the initial diabetes specialist's information is available with an assessment of no recent severe hypoglycaemic event, retained early warning awareness, a regimen that minimises hypoglycaemia and no driving-relevant end-organ effects; the driver is not acutely unwell or metabolically unstable, while an older insulin prescription is explicitly marked discontinued and is not the current treatment.",
            {
                "diabetes.present": True,
                "diabetes.treatment_category": "glucose_lowering_agent_non_insulin",
                "diabetes.recent_severe_hypoglycaemic_event": False,
                "diabetes.hypoglycaemia_awareness": True,
                "diabetes.regimen_minimises_hypoglycaemia": True,
                "diabetes.driving_relevant_end_organ_effects": False,
                "diabetes.initial_specialist_information_available": True,
                "diabetes.gestational": False,
                "diabetes.acutely_unwell": False,
                "diabetes.metabolically_unstable": False,
                "diabetes.severe_hypoglycaemic_event.occurred": False,
            },
            ["DM-COM-005", "DM-COM-006", "DM-COM-009"],
            CONDITIONAL,
            challenges=["treatment_timeline", "qualified_conditional_pathway"],
        ),
        scenario(
            "diabetes",
            "insulin_monitoring_complete",
            "The endocrinologist's current signed assessment confirms insulin-treated diabetes with three months of glucose monitoring records, preserved hypoglycaemia awareness, a regimen designed to minimise hypoglycaemia and no driving-relevant end-organ effects; specialist information is available and explicitly records no recent severe hypoglycaemic event and no history of such an event, while the driver is currently neither acutely unwell nor metabolically unstable and the old diet-only plan predates the documented treatment change.",
            {
                "diabetes.present": True,
                "diabetes.treatment_category": "insulin",
                "diabetes.glucose_monitoring_records_months": 3,
                "diabetes.hypoglycaemia_awareness": True,
                "diabetes.regimen_minimises_hypoglycaemia": True,
                "diabetes.driving_relevant_end_organ_effects": False,
                "diabetes.specialist_information_available": True,
                "diabetes.recent_severe_hypoglycaemic_event": False,
                "diabetes.severe_hypoglycaemic_event.occurred": False,
                "diabetes.gestational": False,
                "diabetes.acutely_unwell": False,
                "diabetes.metabolically_unstable": False,
            },
            ["DM-COM-007", "DM-COM-008", "DM-COM-009"],
            CONDITIONAL,
            challenges=["monitoring_duration", "specialist_vs_patient_account"],
        ),
        scenario(
            "diabetes",
            "recent_assisted_hypoglycaemia",
            f"The discharge summary confirms a severe hypoglycaemic event {weeks} weeks ago in a driver with insulin-treated diabetes, when confusion prevented self-treatment and another person had to give assistance, with contemporaneous glucose of 2.2 mmol/L; the nurse records the event and interval from the signed document, while a later glucose of 6.1 after treatment and the driver's improved appearance today do not erase the documented recent severe episode or supply a specialist return-to-driving assessment.",
            {
                "diabetes.present": True,
                "diabetes.treatment_category": "insulin",
                "diabetes.severe_hypoglycaemic_event.occurred": True,
                "diabetes.severe_hypoglycaemic_event.weeks_since_last": weeks,
                "diabetes.recent_severe_hypoglycaemic_event": True,
                "diabetes.gestational": False,
            },
            ["DM-COM-001", "DM-COM-002", "DM-COM-008"],
            TEMPORARY,
            challenges=["six_week_interval", "assistance_required", "post_treatment_decoy"],
        ),
        scenario(
            "diabetes",
            "acute_metabolic_instability",
            f"The current physician assessment explicitly describes the driver with established diabetes as acutely unwell with metabolically unstable diabetes, after vomiting and a measured glucose of {[24, 27, 25, 29, 26][v]} mmol/L prompted urgent assessment; the driver says the nausea eased after fluids, but the signed current review has not documented resolution of the instability, and a normal measurement copied from an earlier well visit is not evidence of the present metabolic state.",
            {
                "diabetes.present": True,
                "diabetes.acutely_unwell": True,
                "diabetes.metabolically_unstable": True,
            },
            ["DM-COM-003"],
            TEMPORARY,
            challenges=["current_vs_old_measurement", "acute_restriction"],
        ),
        scenario(
            "diabetes",
            "possible_hypoglycaemia_unconfirmed",
            "The driver with established diabetes reports sweating and difficulty concentrating after missing breakfast, but stayed responsive, treated himself with food and has no glucose measurement from the symptoms or evidence that assistance was required; a value of 5.8 mmol/L measured after eating is documented with its later timing, the current medicines cannot be reconciled from two inconsistent lists, and the nurse has not confirmed a severe hypoglycaemic event, impaired awareness or a specific treatment category.",
            {"diabetes.present": True},
            ["DM-COM-001", "DM-COM-002"],
            UNKNOWN,
            withheld=[
                "diabetes.severe_hypoglycaemic_event.occurred",
                "diabetes.treatment_category",
            ],
            challenges=["suspected_vs_severe_event", "glucose_timing", "conflicting_medicines"],
        ),
        scenario(
            "diabetes",
            "no_diabetes_patient_family_history",
            "The driver confirms that he has never been diagnosed with diabetes, and the current treating-doctor history records no diabetes rather than an unreviewed employer assumption; a parent's insulin use is discussed as family history, while transient hunger after a missed meal occurred without loss of awareness, a recorded low glucose or medical confirmation of hypoglycaemia, and the nurse does not convert those separate details into a current patient diabetes diagnosis.",
            {"diabetes.present": False},
            ["DM-COM-001"],
            MEETS,
            challenges=["negation", "family_medication", "symptom_without_diagnosis"],
        ),
        scenario(
            "diabetes",
            "gestational_short_term_review",
            "The specialist's current referral identifies gestational diabetes during pregnancy and confirms that insulin has recently been introduced, rather than documenting pre-existing chronic diabetes; the driver reports variable appetite on early starts but no confirmed severe hypoglycaemic event is described, and the nurse distinguishes the self-limiting pregnancy-related condition from chronic insulin-treated diabetes while requesting advice about current symptoms and short-term driving fitness.",
            {
                "diabetes.present": True,
                "diabetes.gestational": True,
                "diabetes.treatment_category": "insulin",
            },
            ["DM-COM-010"],
            UNKNOWN,
            challenges=["gestational_exception", "short_term_review", "treatment_scope"],
        ),
    ]


INTRODUCTIONS = [
    "During a commercial-driver review after a refrigerated-freight run, the nurse brings together the driver's account, a dated clinical attachment and an employer form copied from an earlier assessment; the documents refer to different times, and the current entry distinguishes a completed examination from recollections, plans and information concerning another person.",
    "At a scheduled commercial-driver medical, the driver answers questions in several stages because a dispatcher keeps calling about the next route, while the nurse checks a current clinical document against a copied workplace summary; an observation described confidently in conversation is kept separate from a finding actually recorded in an identified examination.",
    "The commercial driver attends after a long shift with a folder containing a current signed letter, older screening paperwork and a handwritten personal account, and the nurse reconstructs the chronology before recording the present findings; differences between the records are described explicitly rather than resolved by treating the newest-looking photocopy as automatically authoritative.",
    "In a commercial-driver follow-up arranged after an occupational screening concern, the nurse interviews the driver and checks the accompanying documents against the reported sequence of events; the employer wants a quick answer before allocating a vehicle, but the record separates present evidence, historical findings and questions that the clinician has not yet resolved.",
    "The nurse reviews a commercial driver's symptoms alongside information from a witness, the treating team and an older workplace form, because each source describes a different part of the story; the occupational record retains those differences and identifies completed current findings without turning a booking, a family account or a recollection into a measured patient result.",
]

CONTEXT = [
    "The usual work involves coupling trailers, checking mirrors, interpreting radio messages and responding to pedestrians in a loading area, with breaks that can be delayed when deliveries run late; the driver explains which difficulty occurred while stationary and which was noticed during ordinary duties, rather than claiming that quiet conversation in the clinic reproduces every task in the cab.",
    "The driver alternates urban deliveries with a longer motorway leg and describes a busy depot where engine noise, glare and interrupted meals can complicate an account of symptoms; the nurse records the work setting as context, while keeping the dated clinical findings distinct from the driver's explanation for why a symptom might have occurred on that shift.",
    "Part of the usual route requires reversing near workers and reading changing signs before entering a customer site, although today's assessment takes place in a quiet room; the driver is asked to describe the sequence and timing of difficulties, and the note preserves the difference between an occupational concern, a suspected mechanism and a completed clinical assessment.",
    "The employer's copied form relates to an earlier period of work and contains a broad satisfactory box without the measurements underlying it, whereas the current nurse entry identifies the source of each specific finding; the driver's wish to continue scheduled duties is recorded as a preference, not as proof that the present assessment has resolved the documented concern.",
    "The interview takes place before the driver's next planned roster, and the nurse records changes in symptoms, treatment and available documents without assuming that a future specialist appointment has already occurred; any letter that has been requested but not supplied remains separate from the findings actually available when this occupational record is written.",
]

FOLLOWUPS = [
    "The nurse keeps the relevant current attachment with the record and identifies the older account by its timing, so a later reviewer can distinguish what was observed, what the driver reported and what remains unresolved; no additional measurement, specialist conclusion or diagnosis is added merely because it would make the occupational decision easier to complete.",
    "Before closing the interview, the nurse checks that the driver's recollection and the supplied clinical document have not been merged into a single undated finding, and records the outstanding documents separately; the completed entries remain current findings, while any missing qualification, conflicting detail or unperformed examination stays available for review rather than being silently treated as normal.",
    "The record is prepared for the reviewing clinician with the sequence of events and the provenance of the available findings intact, because the employer summary and the driver's account answer different questions; a completed test is retained as such, but an unresolved detail is not filled in from a family member's history or from an earlier document with different testing conditions.",
    "The nurse reads the summary back to the driver to check the chronology and separates agreement about the wording from verification of a medical finding, then attaches the identified clinical material; any decision about further investigation or work allocation remains for the reviewing professional, and the note itself does not certify that all relevant clinical questions have been answered.",
    "For the occupational reviewer, the nurse retains both the definite findings and the limitations of the available account, including the timing and testing conditions where they matter, rather than producing a single reassuring label; the driver is told which information is on file and which details still require confirmation, without replacing the recorded clinical evidence with an employer's preference.",
]


def mixed_addition(module):
    extras = {
        "hypertension": (
            "blackout",
            "A separate current referral documents a witnessed blackout with loss of consciousness during a break and states that the mechanism is under investigation; the driver remembers feeling hot before the event, but neither a benign faint nor a metabolic cause has been confirmed, and cardiac monitoring remains pending.",
            {"blackout.occurred": True, "blackout.mechanism_status": "under_investigation"},
            ["BLK-COM-001", "BLK-COM-006"],
            TEMPORARY,
        ),
        "vision": (
            "diabetes",
            "The same current clinical review separately confirms that the driver has diabetes and is acutely unwell with metabolically unstable diabetes after vomiting and urgent glucose assessment; an older well-visit result is present in the folder, but the current physician has not documented resolution of this separate acute condition.",
            {
                "diabetes.present": True,
                "diabetes.acutely_unwell": True,
                "diabetes.metabolically_unstable": True,
            },
            ["DM-COM-003"],
            TEMPORARY,
        ),
        "hearing": (
            "vision",
            "In a separate current examination, the ophthalmologist confirms non-physiological diplopia within 15 degrees of central fixation, reproduced when the driver follows a target; the driver's impression that covering one eye makes the road signs look clearer is documented without claiming that the confirmed finding has resolved.",
            {
                "vision.diplopia.present": True,
                "vision.diplopia.physiological": False,
                "vision.diplopia.within_20_degrees": True,
            },
            ["VIS-COM-007"],
            EXCLUDED,
        ),
        "blackout": (
            "hearing",
            "The nurse also records possible hearing loss after repeated missed spoken instructions, and audiometry has not been performed; the driver can follow a quiet conversation but no unaided better-ear threshold, complete frequency set or qualified aided-performance result is available for this separate screening concern.",
            {
                "hearing.clinical_assessment": "possible_hearing_loss",
                "hearing.audiometry.available": False,
            },
            ["HEAR-COM-001", "HEAR-COM-002"],
            UNKNOWN,
        ),
        "diabetes": (
            "hypertension",
            "An additional current doctor-reviewed measurement series confirms persistent BP 176/104 mmHg after repeat resting checks, although the driver recalls lower readings on an unverified home monitor; the initial specialist information and a sustained four-week treatment assessment are not available for this separate blood-pressure concern.",
            {
                "cardiovascular.blood_pressure.persistent_systolic": 176,
                "cardiovascular.blood_pressure.persistent_diastolic": 104,
            },
            ["HTN-COM-001", "HTN-COM-002"],
            UNKNOWN,
        ),
    }
    return extras[module]


def full_source(short):
    return "AFTD2022-" + short


def make_cases():
    rng = random.Random(20261027)
    inventory = [(family, variant) for family in range(40) for variant in range(5)]
    rng.shuffle(inventory)  # IDs do not reveal the disease or reference outcome.
    records = []
    for number, (family, variant) in enumerate(inventory, 1):
        b = blueprints(variant)[family]
        paragraphs = [
            INTRODUCTIONS[(number + variant) % 5],
            b["text"],
            CONTEXT[(number + family) % 5],
        ]
        modules = [b["module"]]
        module_outcomes = {b["module"]: b["outcome"]}
        facts = dict(b["facts"])
        sources = {b["module"]: [full_source(s) for s in b["sources"]]}
        challenges = list(b["challenges"])
        if variant == 4:
            module, text, extra_facts, extra_sources, outcome = mixed_addition(b["module"])
            paragraphs.append(text)
            modules.append(module)
            module_outcomes[module] = outcome
            facts.update(extra_facts)
            sources[module] = [full_source(s) for s in extra_sources]
            challenges.append("multiple_current_modules")
        paragraphs.append(FOLLOWUPS[(family + variant) % 5])
        text = (
            "Synthetic nurse note for software testing. No real patient data.\n\n"
            + "\n\n".join(paragraphs)
            + "\n"
        )
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text.strip())
        lengths = [len(s.split()) for s in sentences]
        outcome = min(module_outcomes.values(), key=PRECEDENCE.index)
        records.append(
            {
                "case_id": f"CX-LONG-{number:03d}",
                "family": b["family"],
                "variant": variant + 1,
                "modules": modules,
                "primary_module": b["module"],
                "text": text,
                "expected_outcome": outcome,
                "module_outcomes": module_outcomes,
                "fact_checks": [
                    {"field": k, "kind": "equals", "value": value} for k, value in facts.items()
                ]
                + [{"field": k, "kind": "not_present"} for k in b["withheld"] if k not in facts],
                "expected_sources": sources,
                "challenges": challenges,
                "complexity": {
                    "words": len(text.split()),
                    "characters": len(text),
                    "long_sentences_35_words": sum(n >= 35 for n in lengths),
                    "longest_sentence_words": max(lengths),
                },
            }
        )
    return records


def build(root=ROOT):
    root = Path(root)
    cases = make_cases()
    catalogue = SourceCatalogue(root, root / "data/knowledge/processed/source_catalogue.json")
    before = {
        p.name: sha256_bytes(p.read_bytes())
        for p in (root / NOTES).glob("*.txt")
        if not p.name.startswith("CX-LONG-")
    }
    if (
        len(cases) != 200
        or len({r["case_id"] for r in cases}) != 200
        or len({r["text"] for r in cases}) != 200
    ):
        raise ValueError("Exactly 200 distinct new inputs are required")
    labels, inputs = [], []
    for r in cases:
        if r["complexity"]["words"] < 220 or r["complexity"]["long_sentences_35_words"] < 3:
            raise ValueError("Insufficient long-form complexity: " + r["case_id"])
        if re.search(r"[\u3400-\u9fff]|AFTD2022|assessment_outcome|source_id|rag_query", r["text"]):
            raise ValueError("English clinical narrative must not contain scoring labels")
        refs = {s for group in r["expected_sources"].values() for s in group}
        if not refs <= catalogue.units.keys():
            raise ValueError("Unknown guideline reference")
        path = root / NOTES / (r["case_id"] + ".txt")
        body = r["text"].encode("utf-8")
        if path.exists() and path.read_bytes() != body:
            raise ValueError("Preserve an existing input with different bytes: " + str(path))
        labels.append({k: v for k, v in r.items() if k != "text"})
        inputs.append(
            {
                "case_id": r["case_id"],
                "input": path.relative_to(root).as_posix(),
                "sha256": sha256_bytes(body),
                "modules": r["modules"],
                "family": r["family"],
                "complexity": r["complexity"],
            }
        )
    # All validation precedes input creation. Existing 24 notes are never rewritten.
    for r in cases:
        path = root / NOTES / (r["case_id"] + ".txt")
        if not path.exists():
            path.write_bytes(r["text"].encode("utf-8"))
    source_ids = sorted(
        {s for r in labels for group in r["expected_sources"].values() for s in group}
    )
    references = {sid: catalogue.citation(sid).model_dump(mode="json") for sid in source_ids}
    gold = {
        "schema_version": "1.0.0",
        "split": "synthetic_development_stress_test",
        "clinical_review_status": "pending",
        "independent_clinical_gold": False,
        "family_count": 40,
        "variants_per_family": 5,
        "label_policy": "Authored guideline-based engineering expectations, frozen before system inference; never generated by evaluating these cases with the system.",
        "reference_sources": references,
        "cases": labels,
    }
    manifest = {
        "schema_version": "1.0.0",
        "case_count": 200,
        "seed": 20261027,
        "guideline_sha256": sha256_bytes((root / "data/knowledge/raw/ap_g56_22.pdf").read_bytes()),
        "catalogue_index_sha256": catalogue.index_sha256,
        "gold_sha256": digest(gold),
        "generator_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "preexisting_notes_sha256": before,
        "primary_module_counts": dict(Counter(r["primary_module"] for r in labels)),
        "multi_module_cases": sum(len(r["modules"]) > 1 for r in labels),
        "cases": inputs,
    }
    manifest["identity"] = digest(manifest)
    for path, value in [(root / GOLD, gold), (root / MANIFEST, manifest)]:
        if path.exists() and json.loads(path.read_bytes()) != value:
            raise ValueError("Preserve an existing frozen dataset manifest: " + str(path))
        write_json(path, value)
    if any(sha256_bytes((root / NOTES / name).read_bytes()) != pin for name, pin in before.items()):
        raise ValueError("An original note changed")
    return {
        "cases": 200,
        "families": 40,
        "multi_module_cases": manifest["multi_module_cases"],
        "word_range": [
            min(r["complexity"]["words"] for r in labels),
            max(r["complexity"]["words"] for r in labels),
        ],
        "outcomes": dict(Counter(r["expected_outcome"] for r in labels)),
        "identity": manifest["identity"],
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
