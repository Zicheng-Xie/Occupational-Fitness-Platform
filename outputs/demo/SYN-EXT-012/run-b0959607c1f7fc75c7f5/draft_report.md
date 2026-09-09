# Clinical review draft — SYN-EXT-012

SYN-EXT-012: May meet conditional standard. 5 requested modules; 0 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| hypertension | Meets unconditional standard | fast_path | 0 |
| vision | Meets unconditional standard | fast_path | 0 |
| hearing | Meets unconditional standard | fast_path | 0 |
| blackout | Meets unconditional standard | fast_path | 0 |
| diabetes | May meet conditional standard | rag_review | 0 |

[Original case input](source_input.txt)


## Rule-to-source trace

### DM-COM-INSULIN-001 — triggered

Insulin-treated diabetes does not meet the commercial unconditional standard.

- `diabetes.gestational` = False (present)
  - Source lines 16–16; chars 689:717: diabetes.gestational = false
- `diabetes.present` = True (present)
  - Source lines 15–15; chars 664:687: diabetes.present = true
  - Source lines 15–15; chars 664:687: diabetes.present = true
- `diabetes.treatment_category` = insulin (present)
  - Source lines 24–24; chars 1042:1081: diabetes.treatment_category = "insulin"
  - Source lines 24–24; chars 1042:1081: diabetes.treatment_category = "insulin"

Guideline sources: [AFTD2022-DM-COM-007](#aftd2022-dm-com-007)

### DM-COM-INSULIN-CONDITIONAL-001 — triggered

The recorded facts satisfy the tabulated and monitoring gates for specialist conditional-licence consideration.

- `diabetes.driving_relevant_end_organ_effects` = False (present)
  - Source lines 23–23; chars 989:1040: diabetes.driving_relevant_end_organ_effects = false
  - Source lines 23–23; chars 989:1040: diabetes.driving_relevant_end_organ_effects = false
- `diabetes.glucose_monitoring_records_months` = 3.0 (present)
  - Source lines 25–25; chars 1083:1129: diabetes.glucose_monitoring_records_months = 3
  - Source lines 25–25; chars 1083:1129: diabetes.glucose_monitoring_records_months = 3
- `diabetes.hypoglycaemia_awareness` = True (present)
  - Source lines 21–21; chars 899:938: diabetes.hypoglycaemia_awareness = true
  - Source lines 21–21; chars 899:938: diabetes.hypoglycaemia_awareness = true
- `diabetes.present` = True (present)
  - Source lines 15–15; chars 664:687: diabetes.present = true
  - Source lines 15–15; chars 664:687: diabetes.present = true
- `diabetes.recent_severe_hypoglycaemic_event` = False (present)
  - Source lines 20–20; chars 847:897: diabetes.recent_severe_hypoglycaemic_event = false
  - Source lines 20–20; chars 847:897: diabetes.recent_severe_hypoglycaemic_event = false
- `diabetes.regimen_minimises_hypoglycaemia` = True (present)
  - Source lines 22–22; chars 940:987: diabetes.regimen_minimises_hypoglycaemia = true
  - Source lines 22–22; chars 940:987: diabetes.regimen_minimises_hypoglycaemia = true
- `diabetes.severe_hypoglycaemic_event.occurred` = False (present)
  - Source lines 19–19; chars 793:845: diabetes.severe_hypoglycaemic_event.occurred = false
- `diabetes.severe_hypoglycaemic_event.weeks_since_last` = UNKNOWN (unknown)
- `diabetes.specialist_information_available` = True (present)
  - Source lines 26–26; chars 1131:1179: diabetes.specialist_information_available = true
  - Source lines 26–26; chars 1131:1179: diabetes.specialist_information_available = true

Guideline sources: [AFTD2022-DM-COM-008](#aftd2022-dm-com-008), [AFTD2022-DM-COM-009](#aftd2022-dm-com-009)

### HTN-COM-SCREEN-001 — triggered

Recorded persistent pressures do not exceed the hypertension threshold; this finding covers hypertension only.

- `cardiovascular.blood_pressure.persistent_diastolic` = 80 (present)
  - Source lines 7–7; chars 343:398: cardiovascular.blood_pressure.persistent_diastolic = 80
- `cardiovascular.blood_pressure.persistent_systolic` = 120 (present)
  - Source lines 6–6; chars 286:341: cardiovascular.blood_pressure.persistent_systolic = 120

Guideline sources: [AFTD2022-HTN-COM-001](#aftd2022-htn-com-001)

### VIS-COM-SCREEN-001 — triggered

Recorded acuity and explicit visual-field, diplopia and monocular screening satisfy the implemented vision criteria.

- `vision.diplopia.present` = False (present)
  - Source lines 11–11; chars 529:560: vision.diplopia.present = false
  - Source lines 11–11; chars 529:560: vision.diplopia.present = false
- `vision.monocular` = False (present)
  - Source lines 12–12; chars 562:586: vision.monocular = false
- `vision.uncorrected.better_eye` = 6/6 (present)
  - Source lines 8–8; chars 400:440: vision.uncorrected.right.snellen = "6/6"
  - Source lines 9–9; chars 442:481: vision.uncorrected.left.snellen = "6/6"
- `vision.uncorrected.left.snellen` = 6/6 (present)
  - Source lines 9–9; chars 442:481: vision.uncorrected.left.snellen = "6/6"
- `vision.uncorrected.right.snellen` = 6/6 (present)
  - Source lines 8–8; chars 400:440: vision.uncorrected.right.snellen = "6/6"
- `vision.visual_field.confirmed_defect` = False (present)
  - Source lines 10–10; chars 483:527: vision.visual_field.confirmed_defect = false
  - Source lines 10–10; chars 483:527: vision.visual_field.confirmed_defect = false

Guideline sources: [AFTD2022-VIS-COM-002](#aftd2022-vis-com-002), [AFTD2022-VIS-COM-004](#aftd2022-vis-com-004), [AFTD2022-VIS-COM-007](#aftd2022-vis-com-007)

### HEAR-COM-SCREEN-001 — triggered

Explicit clinical screening or a documented four-frequency audiogram satisfies the implemented unaided hearing criterion.

- `hearing.average_frequencies_khz` = UNKNOWN (unknown)
- `hearing.clinical_assessment` = no_hearing_loss (present)
  - Source lines 13–13; chars 588:635: hearing.clinical_assessment = "no_hearing_loss"
  - Source lines 13–13; chars 588:635: hearing.clinical_assessment = "no_hearing_loss"
- `hearing.unaided_better_ear_average_db` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HEAR-COM-001](#aftd2022-hear-com-001), [AFTD2022-HEAR-COM-002](#aftd2022-hear-com-002)

### BLK-COM-NO-HISTORY-001 — triggered

The note explicitly records no blackout history; no blackout-specific restriction is identified within this screening scope.

- `blackout.occurred` = False (present)
  - Source lines 14–14; chars 637:662: blackout.occurred = false

Guideline sources: [AFTD2022-BLK-COM-001](#aftd2022-blk-com-001)

## Guideline evidence

### AFTD2022-DM-COM-007

[§3.3 · printed 102 / PDF 113](../../../../data/knowledge/raw/ap_g56_22.pdf#page=113)

Table/context: Insulin-treated diabetes (except gestational diabetes)

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has insulin-treated diabetes.

PDF region: (341.0, 177.0, 532.0, 223.0); text SHA-256: `c282e63a3ed339de957b2bb665974fbe8ba99675e92293609823d9bfae70e2a4`.

### AFTD2022-DM-COM-009

[§3.3.2 · printed 99 / PDF 110](../../../../data/knowledge/raw/ap_g56_22.pdf#page=110)

Table/context: Commercial specialist review and glucose records

> 3.3.2. Recommendation and 
> review of conditional licences for 
> commercial vehicle drivers
> It is a general requirement that conditional 
> licences for commercial vehicle drivers are 
> issued by the driver licensing authority based on 
> advice from an appropriate medical specialist 
> (endocrinologist or consultant physician 
> specialising in diabetes) and that these drivers 
> are reviewed periodically by the specialist to 
> determine their ongoing fitness to drive (refer 
> to Part A section 4.4. Conditional licences). For 
> commercial drivers receiving insulin treatment, at 
> least three months of blood glucose monitoring 
> records should be reviewed in assessing fitness 
> to drive.

PDF region: (55.0, 370.0, 295.0, 634.0); text SHA-256: `426a6e52e563cfedd137a95b8eddcd0cbefaedd3b6ab9ccc78ad7917d1eb810d`.

### AFTD2022-DM-COM-008

[§3.3 · printed 102 / PDF 113](../../../../data/knowledge/raw/ap_g56_22.pdf#page=113)

Table/context: Insulin: conditional

> A conditional licence may be considered 
> by the driver licensing authority subject to at 
> least annual review, taking into consideration 
> the nature of the driving task and information 
> provided by an endocrinologist or consultant 
> physician specialising in diabetes on whether 
> the following criteria are met:
> •	 there is no recent history (generally at least 
> 6 weeks) of a ‘severe hypoglycaemic event’ 
> as assessed by the specialist; and
> •	 the person is following a treatment regimen 
> that minimises the risk of hypoglycaemia; 
> and
> •	 the person experiences early warning 
> symptoms (awareness) of hypoglycaemia 
> (refer to section 3.2.1); and
> •	 there are no end-organ effects that may 
> affect driving as per this publication.

PDF region: (341.0, 224.0, 532.0, 467.0); text SHA-256: `eb5eeaab23d2d51445f18bbcbf9e72dd9b472061317b753187c271bdf353cc53`.

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
Insulin treatment with no lifetime severe hypoglycaemic event; monitoring records and specialist assessment documented.

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
diabetes.acutely_unwell = false
diabetes.metabolically_unstable = false
diabetes.severe_hypoglycaemic_event.occurred = false
diabetes.recent_severe_hypoglycaemic_event = false
diabetes.hypoglycaemia_awareness = true
diabetes.regimen_minimises_hypoglycaemia = true
diabetes.driving_relevant_end_organ_effects = false
diabetes.treatment_category = "insulin"
diabetes.glucose_monitoring_records_months = 3
diabetes.specialist_information_available = true

```

Input SHA-256: `3ff40129bde7a41ad93447c12a50ca39a8715c0ef49ba06ecd20169d14c5f130`
Rule-result SHA-256: `048e5529994b2b2b65cd092c1ef186cbdaf0d39b45364229b3391be473d8b2fa`
Evidence-pack SHA-256: `f17f558fcf2a3bd07e76ed482f3df90d662e61ffa43840940fa1267790efd0a6`

## Unverified local-model commentary

This synthetic validation fixture presents a commercial driver with insulin-treated diabetes, hypertension, and uncorrected vision of 6/6 in both eyes. The driver's blood pressure is persistently 120/80 mmHg, and there is no history of severe hypoglycaemic events. The driver's treatment regimen minimises the risk of hypoglycaemia, and they experience early warning symptoms of hypoglycaemia. The driver's visual field is confirmed to be normal, and there is no diplopia or monocular vision. The driver's hearing is clinically assessed as normal, and there is no history of blackout. The driver's hypertension meets the unconditional standard, and their vision and hearing also meet the unconditional standard. However, the driver's diabetes may meet the conditional standard, requiring a specialist assessment and review. A clinician must review the commentary.
