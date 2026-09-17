# Clinical review draft — SYN-EXT-005

SYN-EXT-005: May meet conditional standard. 5 requested modules; 0 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| hypertension | Meets unconditional standard | fast_path | 0 |
| vision | Meets unconditional standard | fast_path | 0 |
| hearing | Meets unconditional standard | fast_path | 0 |
| blackout | May meet conditional standard | rag_review | 0 |
| diabetes | Meets unconditional standard | fast_path | 0 |

[Original case input](source_input.txt)


## Rule-to-source trace

### BLK-COM-UNCERTAIN-UNCONDITIONAL-001 — triggered

The blackout remains of uncertain nature after investigation, so the unconditional commercial standard is not met.

- `blackout.mechanism_status` = undetermined_after_investigation (present)
  - Source lines 16–16; chars 667:729: blackout.mechanism_status = "undetermined_after_investigation"
- `blackout.occurred` = True (present)
  - Source lines 14–14; chars 615:639: blackout.occurred = true
  - Source lines 14–14; chars 615:639: blackout.occurred = true

Guideline sources: [AFTD2022-BLK-COM-003](#aftd2022-blk-com-003)

### BLK-COM-CONDITIONAL-ELIGIBILITY-001 — triggered

The applicable event-free interval is recorded and specialist information is available; the licensing authority may consider a conditional licence.

- `blackout.appropriate_specialist_information_available` = True (present)
  - Source lines 20–20; chars 851:911: blackout.appropriate_specialist_information_available = true
- `blackout.episodes_separated_by_24h_count` = 1 (present)
  - Source lines 18–18; chars 768:812: blackout.episodes_separated_by_24h_count = 1
- `blackout.mechanism_status` = undetermined_after_investigation (present)
  - Source lines 16–16; chars 667:729: blackout.mechanism_status = "undetermined_after_investigation"
- `blackout.occurred` = True (present)
  - Source lines 14–14; chars 615:639: blackout.occurred = true
  - Source lines 14–14; chars 615:639: blackout.occurred = true
- `blackout.years_since_last_event` = 5 (present)
  - Source lines 19–19; chars 814:849: blackout.years_since_last_event = 5

Guideline sources: [AFTD2022-BLK-COM-004](#aftd2022-blk-com-004), [AFTD2022-BLK-COM-005](#aftd2022-blk-com-005)

### HTN-COM-SCREEN-001 — triggered

Recorded persistent pressures do not exceed the hypertension threshold; this finding covers hypertension only.

- `cardiovascular.blood_pressure.persistent_diastolic` = 80.0 (present)
  - Source lines 7–7; chars 321:376: cardiovascular.blood_pressure.persistent_diastolic = 80
  - Source lines 7–7; chars 321:376: cardiovascular.blood_pressure.persistent_diastolic = 80
- `cardiovascular.blood_pressure.persistent_systolic` = 120.0 (present)
  - Source lines 6–6; chars 264:319: cardiovascular.blood_pressure.persistent_systolic = 120
  - Source lines 6–6; chars 264:319: cardiovascular.blood_pressure.persistent_systolic = 120

Guideline sources: [AFTD2022-HTN-COM-001](#aftd2022-htn-com-001)

### VIS-COM-SCREEN-001 — triggered

Recorded acuity and explicit visual-field, diplopia and monocular screening satisfy the implemented vision criteria.

- `vision.diplopia.present` = False (present)
  - Source lines 11–11; chars 507:538: vision.diplopia.present = false
  - Source lines 11–11; chars 507:538: vision.diplopia.present = false
- `vision.monocular` = False (present)
  - Source lines 12–12; chars 540:564: vision.monocular = false
- `vision.uncorrected.better_eye` = 6/6 (present)
  - Source lines 8–8; chars 378:418: vision.uncorrected.right.snellen = "6/6"
  - Source lines 9–9; chars 420:459: vision.uncorrected.left.snellen = "6/6"
- `vision.uncorrected.left.snellen` = 6/6 (present)
  - Source lines 9–9; chars 420:459: vision.uncorrected.left.snellen = "6/6"
  - Source lines 9–9; chars 420:459: vision.uncorrected.left.snellen = "6/6"
- `vision.uncorrected.right.snellen` = 6/6 (present)
  - Source lines 8–8; chars 378:418: vision.uncorrected.right.snellen = "6/6"
  - Source lines 8–8; chars 378:418: vision.uncorrected.right.snellen = "6/6"
- `vision.visual_field.confirmed_defect` = False (present)
  - Source lines 10–10; chars 461:505: vision.visual_field.confirmed_defect = false
  - Source lines 10–10; chars 461:505: vision.visual_field.confirmed_defect = false

Guideline sources: [AFTD2022-VIS-COM-002](#aftd2022-vis-com-002), [AFTD2022-VIS-COM-004](#aftd2022-vis-com-004), [AFTD2022-VIS-COM-007](#aftd2022-vis-com-007)

### HEAR-COM-SCREEN-001 — triggered

Explicit clinical screening or a documented four-frequency audiogram satisfies the implemented unaided hearing criterion.

- `hearing.average_frequencies_khz` = UNKNOWN (unknown)
- `hearing.clinical_assessment` = no_hearing_loss (present)
  - Source lines 13–13; chars 566:613: hearing.clinical_assessment = "no_hearing_loss"
  - Source lines 13–13; chars 566:613: hearing.clinical_assessment = "no_hearing_loss"
- `hearing.unaided_better_ear_average_db` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HEAR-COM-001](#aftd2022-hear-com-001), [AFTD2022-HEAR-COM-002](#aftd2022-hear-com-002)

### DM-COM-NO-HISTORY-001 — triggered

The note explicitly records no diabetes; this is a history-based screening result, not a diabetes diagnosis.

- `diabetes.present` = False (present)
  - Source lines 15–15; chars 641:665: diabetes.present = false
  - Source lines 15–15; chars 641:665: diabetes.present = false

Guideline sources: [AFTD2022-DM-COM-001](#aftd2022-dm-com-001)

## Guideline evidence

### AFTD2022-BLK-COM-003

[§1.3 · printed 59 / PDF 70](../../../../data/knowledge/raw/ap_g56_22.pdf#page=70)

Table/context: Uncertain blackouts: unconditional

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has experienced blackouts 
> that cannot be diagnosed as syncope, 
> seizure or another condition.

PDF region: (354.0, 309.0, 531.0, 378.0); text SHA-256: `2a4cd0409e88aaf1c7ad208d84640971b8e0793c738d869d949acb17d0803295`.

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

## Clinician checklist

- [ ] Clinician: review source facts, rule applicability and every provisional conclusion.
- [ ] Confirm the commercial driving task and assess conditions outside the five-module scope.

## Case source

```text
SYNTHETIC VALIDATION FIXTURE — NOT A REAL PATIENT
Commercial driver assessment.
A single uncertain blackout; exactly five event-free years and specialist information documented.

Structured assessment addendum (explicit documented facts; no inferred values):
cardiovascular.blood_pressure.persistent_systolic = 120
cardiovascular.blood_pressure.persistent_diastolic = 80
vision.uncorrected.right.snellen = "6/6"
vision.uncorrected.left.snellen = "6/6"
vision.visual_field.confirmed_defect = false
vision.diplopia.present = false
vision.monocular = false
hearing.clinical_assessment = "no_hearing_loss"
blackout.occurred = true
diabetes.present = false
blackout.mechanism_status = "undetermined_after_investigation"
blackout.diagnosis = "undetermined"
blackout.episodes_separated_by_24h_count = 1
blackout.years_since_last_event = 5
blackout.appropriate_specialist_information_available = true

```

Input SHA-256: `dc5e5f231ce4d12a698c56f67465032cd0e4abb35184bc44dc821807db479f4a`
Rule-result SHA-256: `8e03a62dc23aec84dbcf5d4f351b98d8093380126900a5cdcd5f44300678b8a3`
Evidence-pack SHA-256: `4320cf13b0f773b45d620b7ba35ec2b6cb50506bc293d0effe806f65427225dc`

## Unverified local-model commentary

This synthetic validation fixture presents a commercial driver assessment with a single uncertain blackout episode, separated from previous events by exactly five years, and specialist information documented. The patient meets unconditional standards for hypertension, vision, and hearing, but may meet conditional standards for blackout due to the uncertain nature of the episode. A clinician must review the case to determine the appropriate licence outcome.
