# Clinical review draft — SYN-EXT-014

SYN-EXT-014: May meet conditional standard. 5 requested modules; 0 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

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
  - Source lines 16–16; chars 697:725: diabetes.gestational = false
- `diabetes.present` = True (present)
  - Source lines 15–15; chars 672:695: diabetes.present = true
  - Source lines 15–15; chars 672:695: diabetes.present = true
- `diabetes.treatment_category` = insulin (present)
  - Source lines 24–24; chars 1049:1088: diabetes.treatment_category = "insulin"

Guideline sources: [AFTD2022-DM-COM-007](#aftd2022-dm-com-007)

### DM-COM-INSULIN-CONDITIONAL-001 — triggered

The recorded facts satisfy the tabulated and monitoring gates for specialist conditional-licence consideration.

- `diabetes.driving_relevant_end_organ_effects` = False (present)
  - Source lines 23–23; chars 996:1047: diabetes.driving_relevant_end_organ_effects = false
- `diabetes.glucose_monitoring_records_months` = 3 (present)
  - Source lines 25–25; chars 1090:1136: diabetes.glucose_monitoring_records_months = 3
- `diabetes.hypoglycaemia_awareness` = True (present)
  - Source lines 21–21; chars 906:945: diabetes.hypoglycaemia_awareness = true
- `diabetes.present` = True (present)
  - Source lines 15–15; chars 672:695: diabetes.present = true
  - Source lines 15–15; chars 672:695: diabetes.present = true
- `diabetes.recent_severe_hypoglycaemic_event` = False (present)
  - Source lines 20–20; chars 854:904: diabetes.recent_severe_hypoglycaemic_event = false
- `diabetes.regimen_minimises_hypoglycaemia` = True (present)
  - Source lines 22–22; chars 947:994: diabetes.regimen_minimises_hypoglycaemia = true
- `diabetes.severe_hypoglycaemic_event.occurred` = True (present)
  - Source lines 19–19; chars 801:852: diabetes.severe_hypoglycaemic_event.occurred = true
  - Source lines 19–19; chars 801:852: diabetes.severe_hypoglycaemic_event.occurred = true
- `diabetes.severe_hypoglycaemic_event.weeks_since_last` = 6 (present)
  - Source lines 27–27; chars 1188:1244: diabetes.severe_hypoglycaemic_event.weeks_since_last = 6
- `diabetes.specialist_information_available` = True (present)
  - Source lines 26–26; chars 1138:1186: diabetes.specialist_information_available = true

Guideline sources: [AFTD2022-DM-COM-008](#aftd2022-dm-com-008), [AFTD2022-DM-COM-009](#aftd2022-dm-com-009)

### HTN-COM-SCREEN-001 — triggered

Recorded persistent pressures do not exceed the hypertension threshold; this finding covers hypertension only.

- `cardiovascular.blood_pressure.persistent_diastolic` = 80.0 (present)
  - Source lines 7–7; chars 351:406: cardiovascular.blood_pressure.persistent_diastolic = 80
  - Source lines 7–7; chars 351:406: cardiovascular.blood_pressure.persistent_diastolic = 80
- `cardiovascular.blood_pressure.persistent_systolic` = 120.0 (present)
  - Source lines 6–6; chars 294:349: cardiovascular.blood_pressure.persistent_systolic = 120
  - Source lines 6–6; chars 294:349: cardiovascular.blood_pressure.persistent_systolic = 120

Guideline sources: [AFTD2022-HTN-COM-001](#aftd2022-htn-com-001)

### VIS-COM-SCREEN-001 — triggered

Recorded acuity and explicit visual-field, diplopia and monocular screening satisfy the implemented vision criteria.

- `vision.diplopia.present` = False (present)
  - Source lines 11–11; chars 537:568: vision.diplopia.present = false
  - Source lines 11–11; chars 537:568: vision.diplopia.present = false
- `vision.monocular` = False (present)
  - Source lines 12–12; chars 570:594: vision.monocular = false
- `vision.uncorrected.better_eye` = 6/6 (present)
  - Source lines 8–8; chars 408:448: vision.uncorrected.right.snellen = "6/6"
  - Source lines 9–9; chars 450:489: vision.uncorrected.left.snellen = "6/6"
- `vision.uncorrected.left.snellen` = 6/6 (present)
  - Source lines 9–9; chars 450:489: vision.uncorrected.left.snellen = "6/6"
  - Source lines 9–9; chars 450:489: vision.uncorrected.left.snellen = "6/6"
- `vision.uncorrected.right.snellen` = 6/6 (present)
  - Source lines 8–8; chars 408:448: vision.uncorrected.right.snellen = "6/6"
  - Source lines 8–8; chars 408:448: vision.uncorrected.right.snellen = "6/6"
- `vision.visual_field.confirmed_defect` = False (present)
  - Source lines 10–10; chars 491:535: vision.visual_field.confirmed_defect = false
  - Source lines 10–10; chars 491:535: vision.visual_field.confirmed_defect = false

Guideline sources: [AFTD2022-VIS-COM-002](#aftd2022-vis-com-002), [AFTD2022-VIS-COM-004](#aftd2022-vis-com-004), [AFTD2022-VIS-COM-007](#aftd2022-vis-com-007)

### HEAR-COM-SCREEN-001 — triggered

Explicit clinical screening or a documented four-frequency audiogram satisfies the implemented unaided hearing criterion.

- `hearing.average_frequencies_khz` = UNKNOWN (unknown)
- `hearing.clinical_assessment` = no_hearing_loss (present)
  - Source lines 13–13; chars 596:643: hearing.clinical_assessment = "no_hearing_loss"
  - Source lines 13–13; chars 596:643: hearing.clinical_assessment = "no_hearing_loss"
- `hearing.unaided_better_ear_average_db` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HEAR-COM-001](#aftd2022-hear-com-001), [AFTD2022-HEAR-COM-002](#aftd2022-hear-com-002)

### BLK-COM-NO-HISTORY-001 — triggered

The note explicitly records no blackout history; no blackout-specific restriction is identified within this screening scope.

- `blackout.occurred` = False (present)
  - Source lines 14–14; chars 645:670: blackout.occurred = false

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
Severe hypoglycaemic event six weeks ago; current specialist assessment documents that the recent-event criterion is satisfied.

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
diabetes.severe_hypoglycaemic_event.occurred = true
diabetes.recent_severe_hypoglycaemic_event = false
diabetes.hypoglycaemia_awareness = true
diabetes.regimen_minimises_hypoglycaemia = true
diabetes.driving_relevant_end_organ_effects = false
diabetes.treatment_category = "insulin"
diabetes.glucose_monitoring_records_months = 3
diabetes.specialist_information_available = true
diabetes.severe_hypoglycaemic_event.weeks_since_last = 6

```

Input SHA-256: `6629e34fc9ba52357e355c1a374553f924f6e7de99450cb51e8bc109390fbf71`
Rule-result SHA-256: `7b35d33e942364b8599c3f2461393f7454a7d99dbe3c7502df775fced4f3c8e8`
Evidence-pack SHA-256: `53dea73432e53059f5053af02045d80322f2c9817c9f3bbb3259f72bb4f4d3a7`

## Unverified local-model commentary

This synthetic validation fixture presents a commercial driver with insulin-treated diabetes, who has recently experienced a severe hypoglycaemic event. The driver's specialist assessment indicates that the recent-event criterion is satisfied, and the driver is following a treatment regimen that minimises the risk of hypoglycaemia. However, the driver's blood pressure is persistently elevated, and their visual field is confirmed to be normal. The driver's hypertension and vision meet unconditional standards, but their diabetes assessment outcome is 'may meet conditional standard'. The driver's case note highlights the importance of reviewing their conditional licence periodically, considering the nature of the driving task and information provided by an endocrinologist or consultant physician specialising in diabetes. A clinician must review the commentary.
