# Clinical review draft — SYN-EXT-011

SYN-EXT-011: May meet conditional standard. 5 requested modules; 0 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

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

### DM-COM-NONINSULIN-001 — triggered

Commercial drivers treated with a non-insulin glucose-lowering agent do not meet the unconditional standard.

- `diabetes.present` = True (present)
  - Source lines 15–15; chars 660:683: diabetes.present = true
  - Source lines 15–15; chars 660:683: diabetes.present = true
- `diabetes.treatment_category` = glucose_lowering_agent_non_insulin (present)
  - Source lines 24–24; chars 1038:1104: diabetes.treatment_category = "glucose_lowering_agent_non_insulin"

Guideline sources: [AFTD2022-DM-COM-005](#aftd2022-dm-com-005)

### DM-COM-NONINSULIN-CONDITIONAL-001 — triggered

All tabulated criteria are recorded for specialist and licensing-authority conditional consideration.

- `diabetes.driving_relevant_end_organ_effects` = False (present)
  - Source lines 23–23; chars 985:1036: diabetes.driving_relevant_end_organ_effects = false
- `diabetes.hypoglycaemia_awareness` = True (present)
  - Source lines 21–21; chars 895:934: diabetes.hypoglycaemia_awareness = true
- `diabetes.initial_specialist_information_available` = True (present)
  - Source lines 25–25; chars 1106:1162: diabetes.initial_specialist_information_available = true
- `diabetes.present` = True (present)
  - Source lines 15–15; chars 660:683: diabetes.present = true
  - Source lines 15–15; chars 660:683: diabetes.present = true
- `diabetes.recent_severe_hypoglycaemic_event` = False (present)
  - Source lines 20–20; chars 843:893: diabetes.recent_severe_hypoglycaemic_event = false
- `diabetes.regimen_minimises_hypoglycaemia` = True (present)
  - Source lines 22–22; chars 936:983: diabetes.regimen_minimises_hypoglycaemia = true

Guideline sources: [AFTD2022-DM-COM-006](#aftd2022-dm-com-006)

### HTN-COM-SCREEN-001 — triggered

Recorded persistent pressures do not exceed the hypertension threshold; this finding covers hypertension only.

- `cardiovascular.blood_pressure.persistent_diastolic` = 80 (present)
  - Source lines 7–7; chars 339:394: cardiovascular.blood_pressure.persistent_diastolic = 80
- `cardiovascular.blood_pressure.persistent_systolic` = 120 (present)
  - Source lines 6–6; chars 282:337: cardiovascular.blood_pressure.persistent_systolic = 120

Guideline sources: [AFTD2022-HTN-COM-001](#aftd2022-htn-com-001)

### VIS-COM-SCREEN-001 — triggered

Recorded acuity and explicit visual-field, diplopia and monocular screening satisfy the implemented vision criteria.

- `vision.diplopia.present` = False (present)
  - Source lines 11–11; chars 525:556: vision.diplopia.present = false
  - Source lines 11–11; chars 525:556: vision.diplopia.present = false
- `vision.monocular` = False (present)
  - Source lines 12–12; chars 558:582: vision.monocular = false
- `vision.uncorrected.better_eye` = 6/6 (present)
  - Source lines 8–8; chars 396:436: vision.uncorrected.right.snellen = "6/6"
  - Source lines 9–9; chars 438:477: vision.uncorrected.left.snellen = "6/6"
- `vision.uncorrected.left.snellen` = 6/6 (present)
  - Source lines 9–9; chars 438:477: vision.uncorrected.left.snellen = "6/6"
- `vision.uncorrected.right.snellen` = 6/6 (present)
  - Source lines 8–8; chars 396:436: vision.uncorrected.right.snellen = "6/6"
- `vision.visual_field.confirmed_defect` = False (present)
  - Source lines 10–10; chars 479:523: vision.visual_field.confirmed_defect = false
  - Source lines 10–10; chars 479:523: vision.visual_field.confirmed_defect = false

Guideline sources: [AFTD2022-VIS-COM-002](#aftd2022-vis-com-002), [AFTD2022-VIS-COM-004](#aftd2022-vis-com-004), [AFTD2022-VIS-COM-007](#aftd2022-vis-com-007)

### HEAR-COM-SCREEN-001 — triggered

Explicit clinical screening or a documented four-frequency audiogram satisfies the implemented unaided hearing criterion.

- `hearing.average_frequencies_khz` = UNKNOWN (unknown)
- `hearing.clinical_assessment` = no_hearing_loss (present)
  - Source lines 13–13; chars 584:631: hearing.clinical_assessment = "no_hearing_loss"
  - Source lines 13–13; chars 584:631: hearing.clinical_assessment = "no_hearing_loss"
- `hearing.unaided_better_ear_average_db` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HEAR-COM-001](#aftd2022-hear-com-001), [AFTD2022-HEAR-COM-002](#aftd2022-hear-com-002)

### BLK-COM-NO-HISTORY-001 — triggered

The note explicitly records no blackout history; no blackout-specific restriction is identified within this screening scope.

- `blackout.occurred` = False (present)
  - Source lines 14–14; chars 633:658: blackout.occurred = false
  - Source lines 14–14; chars 633:658: blackout.occurred = false

Guideline sources: [AFTD2022-BLK-COM-001](#aftd2022-blk-com-001)

## Guideline evidence

### AFTD2022-DM-COM-005

[§3.3 · printed 101 / PDF 112](../../../../data/knowledge/raw/ap_g56_22.pdf#page=112)

Table/context: Non-insulin agents: unconditional

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has non–insulin treated 
> diabetes mellitus and is being treated with 
> glucose-lowering agents other than insulin.

PDF region: (341.0, 286.0, 532.0, 355.0); text SHA-256: `fc60bdaa37f4ef12dea8c98a87935c4d4903f77cdb13b89aeeba9821dda0241f`.

### AFTD2022-DM-COM-006

[§3.3 · printed 101 / PDF 112](../../../../data/knowledge/raw/ap_g56_22.pdf#page=112)

Table/context: Non-insulin agents: conditional and specialist footnote

> A conditional licence may be considered 
> by the driver licensing authority subject to at 
> least annual review, taking into consideration 
> the nature of the driving task and information 
> provided by an endocrinologist or consultant 
> physician specialising in diabetes* on whether 
> the following criteria are met:
> •	 there is no recent history of a ‘severe 
> hypoglycaemic event’ as assessed by the 
> specialist; and
> •	 the person experiences early warning 
> symptoms (awareness) of hypoglycaemia; 
> and
> •	 the person is following a treatment regimen 
> that minimises the risk of hypoglycaemia; 
> and
> •	 there is an absence of end-organ 
> effects that may affect driving as per this 
> publication.
> * For a commercial driver with type 2 diabetes 
> who is being treated with metformin alone, the 
> annual review for a conditional licence may 
> be undertaken by the driver’s treating doctor 
> upon mutual agreement of the treating doctor, 
> specialist and driver licensing authority. The 
> initial granting of a conditional licence must, 
> however, be based on information provided by 
> the specialist.

PDF region: (341.0, 357.0, 532.0, 723.0); text SHA-256: `f1f98641878471e92379f83a9232cda6864ca59f57eea04909726eae4280e747`.

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
Non-insulin glucose-lowering therapy; all conditional table criteria and initial specialist information documented.

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
diabetes.treatment_category = "glucose_lowering_agent_non_insulin"
diabetes.initial_specialist_information_available = true

```

Input SHA-256: `086d1eb762613874910fabf65f02e445a14fbceb48a9232317f0780c2717280c`
Rule-result SHA-256: `5e435161bd281bc9b25421759f486074f40a9e9fbdff8674df9b28c8c93e8475`
Evidence-pack SHA-256: `2a05d869f018cac78b2a1e370dde189966eb1e77e59d645a35ab6cb87b7112ed`

## Unverified local-model commentary

This synthetic validation fixture presents a commercial driver with non-insulin glucose-lowering therapy, meeting unconditional standards for hypertension, vision, and hearing, and may meet conditional standards for diabetes. The driver's blood pressure is within normal limits, with no diplopia, visual field defects, or uncorrected visual acuity issues. However, the presence of diabetes and potential for hypoglycaemia warrant further evaluation and consideration of a conditional licence, pending annual review and specialist assessment.
