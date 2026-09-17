# Clinical review draft — SYN-EXT-015

SYN-EXT-015: Temporarily unfit. 5 requested modules; 0 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| hypertension | Meets unconditional standard | fast_path | 0 |
| vision | Meets unconditional standard | fast_path | 0 |
| hearing | Meets unconditional standard | fast_path | 0 |
| blackout | Meets unconditional standard | fast_path | 0 |
| diabetes | Temporarily unfit | rag_review | 0 |

[Original case input](source_input.txt)


## Rule-to-source trace

### DM-COM-ACUTE-UNSTABLE-001 — triggered

The person is acutely unwell with metabolically unstable diabetes.

- `diabetes.acutely_unwell` = True (present)
  - Source lines 17–17; chars 654:684: diabetes.acutely_unwell = true
  - Source lines 17–17; chars 654:684: diabetes.acutely_unwell = true
- `diabetes.metabolically_unstable` = True (present)
  - Source lines 18–18; chars 686:724: diabetes.metabolically_unstable = true
  - Source lines 18–18; chars 686:724: diabetes.metabolically_unstable = true
- `diabetes.present` = True (present)
  - Source lines 15–15; chars 599:622: diabetes.present = true

Guideline sources: [AFTD2022-DM-COM-003](#aftd2022-dm-com-003)

### HTN-COM-SCREEN-001 — triggered

Recorded persistent pressures do not exceed the hypertension threshold; this finding covers hypertension only.

- `cardiovascular.blood_pressure.persistent_diastolic` = 80.0 (present)
  - Source lines 7–7; chars 278:333: cardiovascular.blood_pressure.persistent_diastolic = 80
  - Source lines 7–7; chars 278:333: cardiovascular.blood_pressure.persistent_diastolic = 80
- `cardiovascular.blood_pressure.persistent_systolic` = 120.0 (present)
  - Source lines 6–6; chars 221:276: cardiovascular.blood_pressure.persistent_systolic = 120
  - Source lines 6–6; chars 221:276: cardiovascular.blood_pressure.persistent_systolic = 120

Guideline sources: [AFTD2022-HTN-COM-001](#aftd2022-htn-com-001)

### VIS-COM-SCREEN-001 — triggered

Recorded acuity and explicit visual-field, diplopia and monocular screening satisfy the implemented vision criteria.

- `vision.diplopia.present` = False (present)
  - Source lines 11–11; chars 464:495: vision.diplopia.present = false
  - Source lines 11–11; chars 464:495: vision.diplopia.present = false
- `vision.monocular` = False (present)
  - Source lines 12–12; chars 497:521: vision.monocular = false
- `vision.uncorrected.better_eye` = 6/6 (present)
  - Source lines 8–8; chars 335:375: vision.uncorrected.right.snellen = "6/6"
  - Source lines 9–9; chars 377:416: vision.uncorrected.left.snellen = "6/6"
- `vision.uncorrected.left.snellen` = 6/6 (present)
  - Source lines 9–9; chars 377:416: vision.uncorrected.left.snellen = "6/6"
  - Source lines 9–9; chars 377:416: vision.uncorrected.left.snellen = "6/6"
- `vision.uncorrected.right.snellen` = 6/6 (present)
  - Source lines 8–8; chars 335:375: vision.uncorrected.right.snellen = "6/6"
  - Source lines 8–8; chars 335:375: vision.uncorrected.right.snellen = "6/6"
- `vision.visual_field.confirmed_defect` = False (present)
  - Source lines 10–10; chars 418:462: vision.visual_field.confirmed_defect = false
  - Source lines 10–10; chars 418:462: vision.visual_field.confirmed_defect = false

Guideline sources: [AFTD2022-VIS-COM-002](#aftd2022-vis-com-002), [AFTD2022-VIS-COM-004](#aftd2022-vis-com-004), [AFTD2022-VIS-COM-007](#aftd2022-vis-com-007)

### HEAR-COM-SCREEN-001 — triggered

Explicit clinical screening or a documented four-frequency audiogram satisfies the implemented unaided hearing criterion.

- `hearing.average_frequencies_khz` = UNKNOWN (unknown)
- `hearing.clinical_assessment` = no_hearing_loss (present)
  - Source lines 13–13; chars 523:570: hearing.clinical_assessment = "no_hearing_loss"
  - Source lines 13–13; chars 523:570: hearing.clinical_assessment = "no_hearing_loss"
- `hearing.unaided_better_ear_average_db` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HEAR-COM-001](#aftd2022-hear-com-001), [AFTD2022-HEAR-COM-002](#aftd2022-hear-com-002)

### BLK-COM-NO-HISTORY-001 — triggered

The note explicitly records no blackout history; no blackout-specific restriction is identified within this screening scope.

- `blackout.occurred` = False (present)
  - Source lines 14–14; chars 572:597: blackout.occurred = false

Guideline sources: [AFTD2022-BLK-COM-001](#aftd2022-blk-com-001)

## Guideline evidence

### AFTD2022-DM-COM-003

[§3.2.2 · printed 95 / PDF 106](../../../../data/knowledge/raw/ap_g56_22.pdf#page=106)

Table/context: Acute metabolic instability

> 3.2.2. Acute hyperglycaemia
> While acute hyperglycaemia may affect some 
> aspects of brain function, there is not enough 
> evidence to determine the regular effects on 
> driving performance and related crash risk. Each 
> person with diabetes should be counselled 
> about managing their diabetes during days 
> when they are unwell and should be advised 
> not to drive if they are acutely unwell with 
> metabolically unstable diabetes.

PDF region: (55.0, 265.0, 294.0, 438.0); text SHA-256: `0ba4927e7248164977d80cbeb75c7ce270e2ccd2fd071e70b41323db1ee10cda`.

### AFTD2022-HTN-COM-001

[§2.3.1 · printed 88 / PDF 99](../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)

Table/context: Hypertension: unconditional

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has blood pressure 
> consistently > 170 systolic or > 100 diastolic 
> (treated or untreated).

PDF region: (345.0, 177.0, 530.0, 247.0); text SHA-256: `eeacf5b9430b10bb961f6b727f6b4eb638baaf8aeecde7413ad4b4dea2baef7d`.

### AFTD2022-VIS-COM-007

[§10.3 · printed 211 / PDF 222](../../../../data/knowledge/raw/ap_g56_22.pdf#page=222)

Table/context: Diplopia

> A person is not fit to hold an unconditional 
> licence or a conditional licence:
> •	 if the person experiences any diplopia 
> (other than physiological diplopia) within 
> 20 degrees from central fixation.

PDF region: (349.0, 177.0, 530.0, 247.0); text SHA-256: `23c939289597aecf602313c3e6274cea12bbe4853136c812693bacd460a63883`.

### AFTD2022-VIS-COM-004

[§10.3 · printed 210 / PDF 221](../../../../data/knowledge/raw/ap_g56_22.pdf#page=221)

Table/context: Visual fields: unconditional

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has any visual field defect.

PDF region: (350.0, 177.0, 532.0, 223.0); text SHA-256: `d54b84732d5cc173a2f28c988779c0e5717b436ce27bb2630ccbc25b9dd9ee61`.

### AFTD2022-VIS-COM-002

[§10.3 · printed 209 / PDF 220](../../../../data/knowledge/raw/ap_g56_22.pdf#page=220)

Table/context: Visual acuity: unconditional

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person’s uncorrected visual acuity is 
> worse than 6/9 in the better eye; or
> •	 if the person’s uncorrected visual acuity is 
> worse than 6/18 in either eye.

PDF region: (349.0, 261.0, 530.0, 349.0); text SHA-256: `598a3da216c03def0f6bcbdcd6bd036f57c5cf7a1e99d224b1fd08d5908bcc39`.

### AFTD2022-HEAR-COM-001

[§4.3 · printed 109 / PDF 120](../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)

Table/context: Hearing: clinical assessment and audiometry

> Compliance with the standard should be clinically 
> assessed initially. If the initial clinical assessment 
> indicates possible hearing loss, the person should 
> be referred for audiometry.

PDF region: (320.0, 273.0, 531.0, 325.0); text SHA-256: `658c8e0d61ff7a066d001e669c6673a4dca8fd439d85009a8ecef07432d5ddbb`.

### AFTD2022-HEAR-COM-002

[§4.3 · printed 109 / PDF 120](../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)

Table/context: Hearing: unaided four-frequency average

> A person is not fit to hold an unconditional licence:
> •	 if the person has unaided hearing loss ≥ 40 dB 
> in the better ear (averaged over the frequencies 
> 0.5, 1, 2 and 3 KHz).

PDF region: (320.0, 327.0, 531.0, 385.0); text SHA-256: `78ef0b09576857072cbc395e26ad22ce08bd7e94bca53ee68bf36f48facb0b6a`.

### AFTD2022-BLK-COM-001

[§1.2.1 · printed 57 / PDF 68](../../../../data/knowledge/raw/ap_g56_22.pdf#page=68)

Table/context: Blackout work-up; continuation of general considerations

> cardiovascular and neurological investigations 
> and referral to several specialists. People should 
> be advised not to drive until the mechanism is 
> ascertained and the corresponding standard met.

PDF region: (305.0, 117.0, 545.0, 182.0); text SHA-256: `dd23a937a5e99db2c2440ffc7ef66d4003092af008384c56d49be31234941a55`.

## Clinician checklist

- [ ] Clinician: review source facts, rule applicability and every provisional conclusion.
- [ ] Confirm the commercial driving task and assess conditions outside the five-module scope.

## Case source

```text
SYNTHETIC VALIDATION FIXTURE — NOT A REAL PATIENT
Commercial driver assessment.
Diabetes with acute illness and metabolic instability.

Structured assessment addendum (explicit documented facts; no inferred values):
cardiovascular.blood_pressure.persistent_systolic = 120
cardiovascular.blood_pressure.persistent_diastolic = 80
vision.uncorrected.right.snellen = "6/6"
vision.uncorrected.left.snellen = "6/6"
vision.visual_field.confirmed_defect = false
vision.diplopia.present = false
vision.monocular = false
hearing.clinical_assessment = "no_hearing_loss"
blackout.occurred = false
diabetes.present = true
diabetes.gestational = false
diabetes.acutely_unwell = true
diabetes.metabolically_unstable = true
diabetes.severe_hypoglycaemic_event.occurred = false
diabetes.recent_severe_hypoglycaemic_event = false
diabetes.hypoglycaemia_awareness = true
diabetes.regimen_minimises_hypoglycaemia = true
diabetes.driving_relevant_end_organ_effects = false
diabetes.treatment_category = "other"

```

Input SHA-256: `d517c07797ef2798466e09f31fa98303333e6da507822168ea8122cba16606ad`
Rule-result SHA-256: `6e4087b27fba21ee6aea4f307357f1387e89ab77e47b3825c7bc1adaa136a4b2`
Evidence-pack SHA-256: `2feb70291a7fdb1695075f2ad512e694a4e45dade89effa9cccbbc06155c51dd`

## Unverified local-model commentary

This synthetic validation fixture presents a commercial driver assessment with a diagnosis of diabetes and acute illness. The patient's blood pressure is 120/80 mmHg, which meets the unconditional standard. However, the patient's diabetes is acutely unstable, and they are not fit to drive due to the risk of hypoglycaemia. The patient's vision, hearing, and blackout assessments are all normal. A clinician must review this case to determine the patient's fitness to drive.
