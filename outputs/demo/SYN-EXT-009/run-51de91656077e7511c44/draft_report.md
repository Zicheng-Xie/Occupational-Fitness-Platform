# Clinical review draft — SYN-EXT-009

SYN-EXT-009: Insufficient information. 5 requested modules; 2 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| hypertension | Meets unconditional standard | fast_path | 0 |
| vision | Meets unconditional standard | fast_path | 0 |
| hearing | Meets unconditional standard | fast_path | 0 |
| blackout | Insufficient information | missing_information | 2 |
| diabetes | Meets unconditional standard | fast_path | 0 |

[Original case input](source_input.txt)


## Rule-to-source trace

### BLK-COM-UNDIAGNOSED-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.mechanism_status` = UNKNOWN (unknown)
- `blackout.occurred` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-BLK-COM-001](#aftd2022-blk-com-001)

### BLK-COM-VASOVAGAL-EXCEPTION-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.diagnosis` = UNKNOWN (unknown)
- `blackout.occurred` = UNKNOWN (unknown)
- `blackout.provoking_factor_well_defined` = UNKNOWN (unknown)
- `blackout.recurrence_while_driving_unlikely` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-BLK-COM-002](#aftd2022-blk-com-002)

### BLK-COM-UNCERTAIN-UNCONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.mechanism_status` = UNKNOWN (unknown)
- `blackout.occurred` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-BLK-COM-003](#aftd2022-blk-com-003)

### BLK-COM-SINGLE-WAIT-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.episodes_separated_by_24h_count` = UNKNOWN (unknown)
- `blackout.mechanism_status` = UNKNOWN (unknown)
- `blackout.occurred` = UNKNOWN (unknown)
- `blackout.years_since_last_event` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-BLK-COM-004](#aftd2022-blk-com-004)

### BLK-COM-RECURRENT-WAIT-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.episodes_separated_by_24h_count` = UNKNOWN (unknown)
- `blackout.mechanism_status` = UNKNOWN (unknown)
- `blackout.occurred` = UNKNOWN (unknown)
- `blackout.years_since_last_event` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-BLK-COM-005](#aftd2022-blk-com-005)

### BLK-COM-CONDITIONAL-ELIGIBILITY-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.appropriate_specialist_information_available` = UNKNOWN (unknown)
- `blackout.episodes_separated_by_24h_count` = UNKNOWN (unknown)
- `blackout.mechanism_status` = UNKNOWN (unknown)
- `blackout.occurred` = UNKNOWN (unknown)
- `blackout.years_since_last_event` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-BLK-COM-004](#aftd2022-blk-com-004), [AFTD2022-BLK-COM-005](#aftd2022-blk-com-005)

### HTN-COM-SCREEN-001 — triggered

Recorded persistent pressures do not exceed the hypertension threshold; this finding covers hypertension only.

- `cardiovascular.blood_pressure.persistent_diastolic` = 80.0 (present)
  - Source lines 7–7; chars 276:331: cardiovascular.blood_pressure.persistent_diastolic = 80
  - Source lines 7–7; chars 276:331: cardiovascular.blood_pressure.persistent_diastolic = 80
- `cardiovascular.blood_pressure.persistent_systolic` = 120.0 (present)
  - Source lines 6–6; chars 219:274: cardiovascular.blood_pressure.persistent_systolic = 120
  - Source lines 6–6; chars 219:274: cardiovascular.blood_pressure.persistent_systolic = 120

Guideline sources: [AFTD2022-HTN-COM-001](#aftd2022-htn-com-001)

### VIS-COM-SCREEN-001 — triggered

Recorded acuity and explicit visual-field, diplopia and monocular screening satisfy the implemented vision criteria.

- `vision.diplopia.present` = False (present)
  - Source lines 11–11; chars 462:493: vision.diplopia.present = false
  - Source lines 11–11; chars 462:493: vision.diplopia.present = false
- `vision.monocular` = False (present)
  - Source lines 12–12; chars 495:519: vision.monocular = false
- `vision.uncorrected.better_eye` = 6/6 (present)
  - Source lines 8–8; chars 333:373: vision.uncorrected.right.snellen = "6/6"
  - Source lines 9–9; chars 375:414: vision.uncorrected.left.snellen = "6/6"
- `vision.uncorrected.left.snellen` = 6/6 (present)
  - Source lines 9–9; chars 375:414: vision.uncorrected.left.snellen = "6/6"
  - Source lines 9–9; chars 375:414: vision.uncorrected.left.snellen = "6/6"
- `vision.uncorrected.right.snellen` = 6/6 (present)
  - Source lines 8–8; chars 333:373: vision.uncorrected.right.snellen = "6/6"
  - Source lines 8–8; chars 333:373: vision.uncorrected.right.snellen = "6/6"
- `vision.visual_field.confirmed_defect` = False (present)
  - Source lines 10–10; chars 416:460: vision.visual_field.confirmed_defect = false
  - Source lines 10–10; chars 416:460: vision.visual_field.confirmed_defect = false

Guideline sources: [AFTD2022-VIS-COM-002](#aftd2022-vis-com-002), [AFTD2022-VIS-COM-004](#aftd2022-vis-com-004), [AFTD2022-VIS-COM-007](#aftd2022-vis-com-007)

### HEAR-COM-SCREEN-001 — triggered

Explicit clinical screening or a documented four-frequency audiogram satisfies the implemented unaided hearing criterion.

- `hearing.average_frequencies_khz` = UNKNOWN (unknown)
- `hearing.clinical_assessment` = no_hearing_loss (present)
  - Source lines 13–13; chars 521:568: hearing.clinical_assessment = "no_hearing_loss"
  - Source lines 13–13; chars 521:568: hearing.clinical_assessment = "no_hearing_loss"
- `hearing.unaided_better_ear_average_db` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HEAR-COM-001](#aftd2022-hear-com-001), [AFTD2022-HEAR-COM-002](#aftd2022-hear-com-002)

### BLK-COM-NO-HISTORY-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.occurred` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-BLK-COM-001](#aftd2022-blk-com-001)

### DM-COM-NO-HISTORY-001 — triggered

The note explicitly records no diabetes; this is a history-based screening result, not a diabetes diagnosis.

- `diabetes.present` = False (present)
  - Source lines 14–14; chars 570:594: diabetes.present = false
  - Source lines 14–14; chars 570:594: diabetes.present = false

Guideline sources: [AFTD2022-DM-COM-001](#aftd2022-dm-com-001)

### BLK-COM-DIAGNOSED-REFERRAL-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.diagnosis` = UNKNOWN (unknown)
- `blackout.occurred` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-BLK-COM-006](#aftd2022-blk-com-006)

## Guideline evidence

### AFTD2022-BLK-COM-001

[§1.2.1 · printed 57 / PDF 68](../../../../data/knowledge/raw/ap_g56_22.pdf#page=68)

Table/context: Blackout work-up; continuation of general considerations

> cardiovascular and neurological investigations 
> and referral to several specialists. People should 
> be advised not to drive until the mechanism is 
> ascertained and the corresponding standard met.

PDF region: (305.0, 117.0, 545.0, 182.0); text SHA-256: `dd23a937a5e99db2c2440ffc7ef66d4003092af008384c56d49be31234941a55`.

### AFTD2022-BLK-COM-002

[§1.2.2 · printed 57 / PDF 68](../../../../data/knowledge/raw/ap_g56_22.pdf#page=68)

Table/context: Provoked vasovagal syncope

> 1.2.2. Vasovagal syncope5
> The most common cause of transient loss of 
> consciousness is vasovagal syncope (‘fainting’). 
> Where this has been triggered by a well-defined 
> provoking factor or a situation that is unlikely 
> to recur while driving (e.g. prolonged standing, 
> venepuncture or emotional situation), it is not 
> necessary to restrict driving. However, vasovagal 
> syncope may also result from other causes 
> that are not so benign. In such cases, fitness 
> to drive should be assessed according to the 
> cardiovascular conditions standards for syncope 
> (refer to section 2. Cardiovascular conditions).

PDF region: (305.0, 310.0, 545.0, 528.0); text SHA-256: `5112bc351b42fbbccb6f50c74ef3f4ec7399be904ea14184aca1f14eaa7e249b`.

### AFTD2022-BLK-COM-003

[§1.3 · printed 59 / PDF 70](../../../../data/knowledge/raw/ap_g56_22.pdf#page=70)

Table/context: Uncertain blackouts: unconditional

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has experienced blackouts 
> that cannot be diagnosed as syncope, 
> seizure or another condition.

PDF region: (354.0, 309.0, 531.0, 378.0); text SHA-256: `2a4cd0409e88aaf1c7ad208d84640971b8e0793c738d869d949acb17d0803295`.

### AFTD2022-BLK-COM-004

[§1.3 · printed 59 / PDF 70](../../../../data/knowledge/raw/ap_g56_22.pdf#page=70)

Table/context: Single/clustered uncertain blackout; read all qualifications

> A person should not drive for 5 
> years following a single blackout of 
> undetermined nature.
> A person should not drive for 10 years 
> following two or more blackouts of 
> undetermined nature separated by a 24-
> hour period.
> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has experienced blackouts 
> that cannot be diagnosed as syncope, 
> seizure or another condition.
> If there has been a single blackout or more 
> than one blackout within a 24-hour period, 
> a conditional licence may be considered 
> by the driver licensing authority subject to 
> at least annual review, taking into account 
> information provided by an appropriate 
> specialist as to whether the following 
> criterion is met:
> •	 there have been no further blackouts for 
> at least 5 years.

PDF region: (354.0, 219.0, 531.0, 511.0); text SHA-256: `755748eea7c89a47066501c56a6fd8850304b696fcca5f69b0f83faf58ffec59`.

### AFTD2022-BLK-COM-005

[§1.3 · printed 59 / PDF 70](../../../../data/knowledge/raw/ap_g56_22.pdf#page=70)

Table/context: Recurrent uncertain blackout; read all qualifications

> A person should not drive for 10 years 
> following two or more blackouts of 
> undetermined nature separated by a 24-
> hour period.
> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has experienced blackouts 
> that cannot be diagnosed as syncope, 
> seizure or another condition.
> If there has been a single blackout or more 
> than one blackout within a 24-hour period, 
> a conditional licence may be considered 
> by the driver licensing authority subject to 
> at least annual review, taking into account 
> information provided by an appropriate 
> specialist as to whether the following 
> criterion is met:
> •	 there have been no further blackouts for 
> at least 5 years.
> If there have been two or more blackouts 
> separated by at least 24 hours, a 
> conditional licence may be considered by 
> the driver licensing authority subject to at 
> least annual review, taking into account 
> information provided by an appropriate 
> specialist as to whether the following 
> criterion is met:
> •	 there have been no further blackouts for 
> at least 10 years.

PDF region: (354.0, 259.0, 531.0, 642.0); text SHA-256: `518da4f1500d8f8c838d81b4032f1a22f7e592d32c018c48a0242fc3c20bb05e`.

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

### AFTD2022-BLK-COM-006

[§1.3 · printed 58 / PDF 69](../../../../data/knowledge/raw/ap_g56_22.pdf#page=69)

Table/context: Diagnosed blackout cross-referrals

> themselves with the information in this chapter 
> and the tabulated standards before assessing a 
> person’s fitness to drive. 
> Where a firm diagnosis has been made, the 
> standard appropriate to the condition should 
> be referred to in this publication (refer to Figure 
> 6. Management of blackouts and driving). For 
> blackouts due to medical causes not covered 
> in the standard, refer to first principles (refer to 
> Part A section 2. Assessing fitness to drive – 
> general guidance). For blackouts where, after 
> investigation, it is not possible to diagnose one 
> of the conditions covered elsewhere in this 
> publication, refer to the table for blackouts of 
> uncertain nature over the page.

PDF region: (305.0, 50.0, 545.0, 330.0); text SHA-256: `d7a6ad8dd8992110bf369465f78225c9783db872080526349c67d7aa07caf574`.

## Clinician checklist

- [ ] Clinician: review source facts, rule applicability and every provisional conclusion.
- [ ] Confirm the commercial driving task and assess conditions outside the five-module scope.
- [ ] Confirm missing/unverified case fact: blackout.mechanism_status
- [ ] Confirm missing/unverified case fact: blackout.occurred

## Case source

```text
SYNTHETIC VALIDATION FIXTURE — NOT A REAL PATIENT
Commercial driver assessment.
The report contains no blackout history information.

Structured assessment addendum (explicit documented facts; no inferred values):
cardiovascular.blood_pressure.persistent_systolic = 120
cardiovascular.blood_pressure.persistent_diastolic = 80
vision.uncorrected.right.snellen = "6/6"
vision.uncorrected.left.snellen = "6/6"
vision.visual_field.confirmed_defect = false
vision.diplopia.present = false
vision.monocular = false
hearing.clinical_assessment = "no_hearing_loss"
diabetes.present = false

```

Input SHA-256: `402bae8920f4a9d3deb59125a6760dc59e6351762b15616685a789d4778c6ee4`
Rule-result SHA-256: `ab4bd285fce2417e4a5ee6ab3702a9f77d57277d7c1ac00ed3da278d0efabcb1`
Evidence-pack SHA-256: `c88a551055bbf006a766f14bb3837755788215dea9fa5ba46aefa72eb5f7ec20`

## Unverified local-model commentary

This synthetic validation fixture presents a commercial driver assessment with insufficient information regarding the patient's blackout history. The report highlights the importance of ascertaining the mechanism of blackout episodes before issuing a driving licence. The clinician must review the case to determine the patient's fitness to drive.
