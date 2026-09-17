# Clinical review draft — SYN-EXT-017

SYN-EXT-017: Insufficient information. 5 requested modules; 2 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| hypertension | Meets unconditional standard | fast_path | 0 |
| vision | Meets unconditional standard | fast_path | 0 |
| hearing | Insufficient information | missing_information | 2 |
| blackout | Meets unconditional standard | fast_path | 0 |
| diabetes | Meets unconditional standard | fast_path | 0 |

[Original case input](source_input.txt)


## Rule-to-source trace

### HEAR-COM-UNCONDITIONAL-001 — triggered

Unaided hearing loss in the better ear is at or above the commercial unconditional threshold.

- `hearing.average_frequencies_khz` = [0.5, 1, 2, 3] (present)
  - Source lines 18–18; chars 758:806: hearing.average_frequencies_khz = [0.5, 1, 2, 3]
- `hearing.clinical_assessment` = possible_hearing_loss (present)
  - Source lines 13–13; chars 569:622: hearing.clinical_assessment = "possible_hearing_loss"
  - Source lines 13–13; chars 569:622: hearing.clinical_assessment = "possible_hearing_loss"
- `hearing.unaided_better_ear_average_db` = 40.0 (present)
  - Source lines 17–17; chars 714:756: hearing.unaided_better_ear_average_db = 40
  - Source lines 17–17; chars 714:756: hearing.unaided_better_ear_average_db = 40

Guideline sources: [AFTD2022-HEAR-COM-002](#aftd2022-hear-com-002)

### HEAR-COM-CONDITIONAL-AID-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.aided_standard_met` = UNKNOWN (unknown)
- `hearing.ent_or_audiologist_information_available` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HEAR-COM-003](#aftd2022-hear-com-003)

### HEAR-COM-INDIVIDUAL-ASSESSMENT-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.aided_standard_met` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HEAR-COM-004](#aftd2022-hear-com-004)

### HTN-COM-SCREEN-001 — triggered

Recorded persistent pressures do not exceed the hypertension threshold; this finding covers hypertension only.

- `cardiovascular.blood_pressure.persistent_diastolic` = 80.0 (present)
  - Source lines 7–7; chars 324:379: cardiovascular.blood_pressure.persistent_diastolic = 80
  - Source lines 7–7; chars 324:379: cardiovascular.blood_pressure.persistent_diastolic = 80
- `cardiovascular.blood_pressure.persistent_systolic` = 120.0 (present)
  - Source lines 6–6; chars 267:322: cardiovascular.blood_pressure.persistent_systolic = 120
  - Source lines 6–6; chars 267:322: cardiovascular.blood_pressure.persistent_systolic = 120

Guideline sources: [AFTD2022-HTN-COM-001](#aftd2022-htn-com-001)

### VIS-COM-SCREEN-001 — triggered

Recorded acuity and explicit visual-field, diplopia and monocular screening satisfy the implemented vision criteria.

- `vision.diplopia.present` = False (present)
  - Source lines 11–11; chars 510:541: vision.diplopia.present = false
  - Source lines 11–11; chars 510:541: vision.diplopia.present = false
- `vision.monocular` = False (present)
  - Source lines 12–12; chars 543:567: vision.monocular = false
- `vision.uncorrected.better_eye` = 6/6 (present)
  - Source lines 8–8; chars 381:421: vision.uncorrected.right.snellen = "6/6"
  - Source lines 9–9; chars 423:462: vision.uncorrected.left.snellen = "6/6"
- `vision.uncorrected.left.snellen` = 6/6 (present)
  - Source lines 9–9; chars 423:462: vision.uncorrected.left.snellen = "6/6"
  - Source lines 9–9; chars 423:462: vision.uncorrected.left.snellen = "6/6"
- `vision.uncorrected.right.snellen` = 6/6 (present)
  - Source lines 8–8; chars 381:421: vision.uncorrected.right.snellen = "6/6"
  - Source lines 8–8; chars 381:421: vision.uncorrected.right.snellen = "6/6"
- `vision.visual_field.confirmed_defect` = False (present)
  - Source lines 10–10; chars 464:508: vision.visual_field.confirmed_defect = false
  - Source lines 10–10; chars 464:508: vision.visual_field.confirmed_defect = false

Guideline sources: [AFTD2022-VIS-COM-002](#aftd2022-vis-com-002), [AFTD2022-VIS-COM-004](#aftd2022-vis-com-004), [AFTD2022-VIS-COM-007](#aftd2022-vis-com-007)

### BLK-COM-NO-HISTORY-001 — triggered

The note explicitly records no blackout history; no blackout-specific restriction is identified within this screening scope.

- `blackout.occurred` = False (present)
  - Source lines 14–14; chars 624:649: blackout.occurred = false

Guideline sources: [AFTD2022-BLK-COM-001](#aftd2022-blk-com-001)

### DM-COM-NO-HISTORY-001 — triggered

The note explicitly records no diabetes; this is a history-based screening result, not a diabetes diagnosis.

- `diabetes.present` = False (present)
  - Source lines 15–15; chars 651:675: diabetes.present = false
  - Source lines 15–15; chars 651:675: diabetes.present = false

Guideline sources: [AFTD2022-DM-COM-001](#aftd2022-dm-com-001)

## Guideline evidence

### AFTD2022-HEAR-COM-002

[§4.3 · printed 109 / PDF 120](../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)

Table/context: Hearing: unaided four-frequency average

> A person is not fit to hold an unconditional licence:
> •	 if the person has unaided hearing loss ≥ 40 dB 
> in the better ear (averaged over the frequencies 
> 0.5, 1, 2 and 3 KHz).

PDF region: (320.0, 327.0, 531.0, 385.0); text SHA-256: `78ef0b09576857072cbc395e26ad22ce08bd7e94bca53ee68bf36f48facb0b6a`.

### AFTD2022-HEAR-COM-003

[§4.3 · printed 109 / PDF 120](../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)

Table/context: Hearing: conditional and all footnotes

> A conditional licence may be considered by the 
> driver licensing authority subject to periodic review*, 
> taking into account the nature of the driving task 
> and information provided by an ENT specialist or 
> audiologist**, as to whether:
> •	 the standard is able to be met with a hearing 
> aid***.
> If the standard is not able to be met with a hearing 
> aid, further individualised assessment should be 
> offered. 
> A conditional licence may be considered by the 
> driver licensing authority subject to periodic review*, 
> taking into account:
> •	 the nature of the driving task; and
> •	 information provided by an ENT specialist or 
> audiologist**; and
> •	 the results of a practical driver assessment if 
> required. 
> * Stable conditions may not require periodic review. 
> ** Refer to section 4.2. General assessment and 
> management guidelines.
> *** In some cases, noise amplification as a result of 
> wearing hearing aids may lead to driver distraction 
> and may warrant individualised assessment to 
> determine fitness to drive without the hearing aid 
> (refer to 4.2. General assessment and management 
> guidelines).

PDF region: (320.0, 386.0, 531.0, 766.0); text SHA-256: `ab9dffe6e58bb057a616adb6dda7ea391a340994027e84e369cf4ede3ec7cd88`.

### AFTD2022-HEAR-COM-004

[§4.3 · printed 109 / PDF 120](../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)

Table/context: Hearing: individualised assessment and all footnotes

> If the standard is not able to be met with a hearing 
> aid, further individualised assessment should be 
> offered. 
> A conditional licence may be considered by the 
> driver licensing authority subject to periodic review*, 
> taking into account:
> •	 the nature of the driving task; and
> •	 information provided by an ENT specialist or 
> audiologist**; and
> •	 the results of a practical driver assessment if 
> required. 
> * Stable conditions may not require periodic review. 
> ** Refer to section 4.2. General assessment and 
> management guidelines.
> *** In some cases, noise amplification as a result of 
> wearing hearing aids may lead to driver distraction 
> and may warrant individualised assessment to 
> determine fitness to drive without the hearing aid 
> (refer to 4.2. General assessment and management 
> guidelines).

PDF region: (320.0, 481.0, 531.0, 766.0); text SHA-256: `2dc9b07eb871ca8d70fd21cc22b6c624418fe6268ac1684b14853dc91cbf2f18`.

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
- [ ] Confirm missing/unverified case fact: hearing.aided_standard_met
- [ ] Confirm missing/unverified case fact: hearing.ent_or_audiologist_information_available
- [ ] HEARING_40_DB_FIGURE_TABLE_CONFLICT: licensing table uses >= 40; Figure 11 uses > 40; clinical review pending

## Case source

```text
SYNTHETIC VALIDATION FIXTURE — NOT A REAL PATIENT
Commercial driver assessment.
A confirmed four-frequency better-ear hearing average is exactly 40 dB; aided assessment is missing.

Structured assessment addendum (explicit documented facts; no inferred values):
cardiovascular.blood_pressure.persistent_systolic = 120
cardiovascular.blood_pressure.persistent_diastolic = 80
vision.uncorrected.right.snellen = "6/6"
vision.uncorrected.left.snellen = "6/6"
vision.visual_field.confirmed_defect = false
vision.diplopia.present = false
vision.monocular = false
hearing.clinical_assessment = "possible_hearing_loss"
blackout.occurred = false
diabetes.present = false
hearing.audiometry.available = true
hearing.unaided_better_ear_average_db = 40
hearing.average_frequencies_khz = [0.5, 1, 2, 3]

```

Input SHA-256: `7d4685263114420140e87dcc2029868cad8618a004b940a8c1cc457d3cd771a7`
Rule-result SHA-256: `99df96a8fa60f34e65ff280ba942938c638539c84d3a88307cdbddc95efd0805`
Evidence-pack SHA-256: `9fe11586ea72b57ec7eabf41e4679ab1ab7e2ecc4d551fc2d0b284a0c995f3d1`

## Unverified local-model commentary

This synthetic validation fixture presents a commercial driver assessment with insufficient information in the hearing module. The unaided better-ear average is 40 dB, which meets the unconditional standard for hearing. However, the aided assessment is missing, and the individualised assessment should be offered. The presence of possible hearing loss and the availability of audiometry suggest that further evaluation is necessary. A clinician must review the case to determine the appropriate assessment outcome.
