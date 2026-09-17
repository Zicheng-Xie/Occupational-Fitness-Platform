# Clinical review draft — SYN-EXT-019

SYN-EXT-019: Meets unconditional standard. 5 requested modules; 0 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| hypertension | Meets unconditional standard | fast_path | 0 |
| vision | Meets unconditional standard | fast_path | 0 |
| hearing | Meets unconditional standard | fast_path | 0 |
| blackout | Meets unconditional standard | fast_path | 0 |
| diabetes | Meets unconditional standard | fast_path | 0 |

[Original case input](source_input.txt)


## Rule-to-source trace

### HTN-COM-SCREEN-001 — triggered

Recorded persistent pressures do not exceed the hypertension threshold; this finding covers hypertension only.

- `cardiovascular.blood_pressure.persistent_diastolic` = 100 (present)
  - Source lines 7–7; chars 317:373: cardiovascular.blood_pressure.persistent_diastolic = 100
- `cardiovascular.blood_pressure.persistent_systolic` = 170 (present)
  - Source lines 6–6; chars 260:315: cardiovascular.blood_pressure.persistent_systolic = 170

Guideline sources: [AFTD2022-HTN-COM-001](#aftd2022-htn-com-001)

### VIS-COM-SCREEN-001 — triggered

Recorded acuity and explicit visual-field, diplopia and monocular screening satisfy the implemented vision criteria.

- `vision.diplopia.present` = False (present)
  - Source lines 11–11; chars 504:535: vision.diplopia.present = false
- `vision.monocular` = False (present)
  - Source lines 12–12; chars 537:561: vision.monocular = false
- `vision.uncorrected.better_eye` = 6/6 (present)
  - Source lines 8–8; chars 375:415: vision.uncorrected.right.snellen = "6/6"
  - Source lines 9–9; chars 417:456: vision.uncorrected.left.snellen = "6/6"
- `vision.uncorrected.left.snellen` = 6/6 (present)
  - Source lines 9–9; chars 417:456: vision.uncorrected.left.snellen = "6/6"
- `vision.uncorrected.right.snellen` = 6/6 (present)
  - Source lines 8–8; chars 375:415: vision.uncorrected.right.snellen = "6/6"
- `vision.visual_field.confirmed_defect` = False (present)
  - Source lines 10–10; chars 458:502: vision.visual_field.confirmed_defect = false

Guideline sources: [AFTD2022-VIS-COM-002](#aftd2022-vis-com-002), [AFTD2022-VIS-COM-004](#aftd2022-vis-com-004), [AFTD2022-VIS-COM-007](#aftd2022-vis-com-007)

### HEAR-COM-SCREEN-001 — triggered

Explicit clinical screening or a documented four-frequency audiogram satisfies the implemented unaided hearing criterion.

- `hearing.average_frequencies_khz` = UNKNOWN (unknown)
- `hearing.clinical_assessment` = no_hearing_loss (present)
  - Source lines 13–13; chars 563:610: hearing.clinical_assessment = "no_hearing_loss"
- `hearing.unaided_better_ear_average_db` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HEAR-COM-001](#aftd2022-hear-com-001), [AFTD2022-HEAR-COM-002](#aftd2022-hear-com-002)

### BLK-COM-NO-HISTORY-001 — triggered

The note explicitly records no blackout history; no blackout-specific restriction is identified within this screening scope.

- `blackout.occurred` = False (present)
  - Source lines 14–14; chars 612:637: blackout.occurred = false

Guideline sources: [AFTD2022-BLK-COM-001](#aftd2022-blk-com-001)

### DM-COM-NO-HISTORY-001 — triggered

The note explicitly records no diabetes; this is a history-based screening result, not a diabetes diagnosis.

- `diabetes.present` = False (present)
  - Source lines 15–15; chars 639:663: diabetes.present = false

Guideline sources: [AFTD2022-DM-COM-001](#aftd2022-dm-com-001)

## Guideline evidence

### AFTD2022-HTN-COM-001

[§2.3.1 · printed 88 / PDF 99](../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)

Table/context: Hypertension: unconditional

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has blood pressure 
> consistently > 170 systolic or > 100 diastolic 
> (treated or untreated).

PDF region: (345.0, 177.0, 530.0, 247.0); text SHA-256: `eeacf5b9430b10bb961f6b727f6b4eb638baaf8aeecde7413ad4b4dea2baef7d`.

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

### AFTD2022-VIS-COM-004

[§10.3 · printed 210 / PDF 221](../../../../data/knowledge/raw/ap_g56_22.pdf#page=221)

Table/context: Visual fields: unconditional

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has any visual field defect.

PDF region: (350.0, 177.0, 532.0, 223.0); text SHA-256: `d54b84732d5cc173a2f28c988779c0e5717b436ce27bb2630ccbc25b9dd9ee61`.

### AFTD2022-VIS-COM-007

[§10.3 · printed 211 / PDF 222](../../../../data/knowledge/raw/ap_g56_22.pdf#page=222)

Table/context: Diplopia

> A person is not fit to hold an unconditional 
> licence or a conditional licence:
> •	 if the person experiences any diplopia 
> (other than physiological diplopia) within 
> 20 degrees from central fixation.

PDF region: (349.0, 177.0, 530.0, 247.0); text SHA-256: `23c939289597aecf602313c3e6274cea12bbe4853136c812693bacd460a63883`.

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

### AFTD2022-DM-COM-001

[§3.1.1 · printed 92 / PDF 103](../../../../data/knowledge/raw/ap_g56_22.pdf#page=103)

Table/context: Diabetes driving effects

> Diabetes may affect a person’s ability to drive, 
> either through a ‘severe hypoglycaemic event’ 
> or from end-organ effects on relevant functions, 
> including effects on vision, the heart and the 
> peripheral nerves and vasculature of the 
> extremities, particularly the feet. In people with 
> type 2 diabetes, sleep apnoea is also more 
> common (refer to section 8. Sleep disorders). 
> The main hazard in people with insulin-treated 
> diabetes is the unexpected occurrence of 
> hypoglycaemia.

PDF region: (55.0, 268.0, 294.0, 438.0); text SHA-256: `7e3a2b0eca205bfc449f2f32db095e9511352c4ef45c5c35e4fb5cf1bca71ed0`.

## Clinician checklist

- [ ] Clinician: review source facts, rule applicability and every provisional conclusion.
- [ ] Confirm the commercial driving task and assess conditions outside the five-module scope.

## Case source

```text
SYNTHETIC VALIDATION FIXTURE — NOT A REAL PATIENT
Commercial driver assessment.
Persistent pressure exactly at both commercial thresholds; strict greater-than boundary test.

Structured assessment addendum (explicit documented facts; no inferred values):
cardiovascular.blood_pressure.persistent_systolic = 170
cardiovascular.blood_pressure.persistent_diastolic = 100
vision.uncorrected.right.snellen = "6/6"
vision.uncorrected.left.snellen = "6/6"
vision.visual_field.confirmed_defect = false
vision.diplopia.present = false
vision.monocular = false
hearing.clinical_assessment = "no_hearing_loss"
blackout.occurred = false
diabetes.present = false

```

Input SHA-256: `c51bb42ffb7d17edd93d47ccf3056fa9c3c5eaf0fefd28c166834ce89d78699d`
Rule-result SHA-256: `8d00aa15dd309514a8148db50a5f782401449875eb5cb39eac6d42c8d241a1b7`
Evidence-pack SHA-256: `1371e5359761ed7010d252a2d025e808a15c3b9023f4943768a577f5664b676f`

## Unverified local-model commentary

This synthetic validation fixture meets the unconditional standard for commercial driver assessment. The patient's blood pressure consistently exceeds the threshold of 170 systolic or 100 diastolic, triggering the rule HTN-COM-SCREEN-001. Additionally, the patient's uncorrected visual acuity is 6/6 in both eyes, and there is no visual field defect or diplopia. The patient's hearing is clinically assessed as normal, and there is no history of blackout or diabetes. The patient's assessment outcomes meet the unconditional standard for commercial driver assessment.
