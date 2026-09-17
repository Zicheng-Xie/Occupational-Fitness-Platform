# Clinical review draft — SYN-M2-002

SYN-M2-002: Insufficient information. 5 requested modules; 8 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| hypertension | Insufficient information | missing_information | 2 |
| vision | Insufficient information | missing_information | 2 |
| hearing | Meets unconditional standard | fast_path | 0 |
| blackout | Insufficient information | missing_information | 2 |
| diabetes | Insufficient information | missing_information | 2 |

[Original case input](source_input.txt)


## Rule-to-source trace

### HTN-COM-UNCONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `cardiovascular.blood_pressure.persistent_diastolic` = UNKNOWN (unknown)
- `cardiovascular.blood_pressure.persistent_systolic` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HTN-COM-001](#aftd2022-htn-com-001)

### HTN-COM-CONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `cardiovascular.hypertension.antihypertensive_therapy` = UNKNOWN (unknown)
- `cardiovascular.hypertension.controlled_for_4_weeks` = UNKNOWN (unknown)
- `cardiovascular.hypertension.driving_impairing_medication_side_effects` = UNKNOWN (unknown)
- `cardiovascular.hypertension.initial_specialist_information_available` = UNKNOWN (unknown)
- `cardiovascular.hypertension.target_organ_damage_relevant_to_driving` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HTN-COM-002](#aftd2022-htn-com-002)

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

### VIS-COM-MONOCULAR-001 — unknown

Required facts are unknown or unconfirmed.

- `vision.monocular` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-VIS-COM-006](#aftd2022-vis-com-006)

### VIS-COM-MONOCULAR-CONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `vision.monocular` = UNKNOWN (unknown)
- `vision.remaining_eye.field_measured_within_10_degrees_vertical` = UNKNOWN (unknown)
- `vision.remaining_eye.horizontal_field_degrees` = UNKNOWN (unknown)
- `vision.remaining_eye.other_significant_field_loss` = UNKNOWN (unknown)
- `vision.remaining_eye.snellen` = UNKNOWN (unknown)
- `vision.specialist_assessment_available` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-VIS-COM-006](#aftd2022-vis-com-006)

### VIS-COM-DIPLOPIA-001 — unknown

Required facts are unknown or unconfirmed.

- `vision.diplopia.physiological` = UNKNOWN (unknown)
- `vision.diplopia.present` = UNKNOWN (unknown)
- `vision.diplopia.within_20_degrees` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-VIS-COM-007](#aftd2022-vis-com-007)

### DM-COM-DIET-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.driving_relevant_comorbidity_status` = UNKNOWN (unknown)
- `diabetes.present` = UNKNOWN (unknown)
- `diabetes.treatment_category` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-004](#aftd2022-dm-com-004)

### DM-COM-NONINSULIN-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.present` = UNKNOWN (unknown)
- `diabetes.treatment_category` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-005](#aftd2022-dm-com-005)

### DM-COM-NONINSULIN-CONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.driving_relevant_end_organ_effects` = UNKNOWN (unknown)
- `diabetes.hypoglycaemia_awareness` = UNKNOWN (unknown)
- `diabetes.initial_specialist_information_available` = UNKNOWN (unknown)
- `diabetes.present` = UNKNOWN (unknown)
- `diabetes.recent_severe_hypoglycaemic_event` = UNKNOWN (unknown)
- `diabetes.regimen_minimises_hypoglycaemia` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-006](#aftd2022-dm-com-006)

### DM-COM-INSULIN-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.gestational` = UNKNOWN (unknown)
- `diabetes.present` = UNKNOWN (unknown)
- `diabetes.treatment_category` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-007](#aftd2022-dm-com-007)

### DM-COM-SEVERE-HYPO-WAIT-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.present` = UNKNOWN (unknown)
- `diabetes.severe_hypoglycaemic_event.occurred` = UNKNOWN (unknown)
- `diabetes.severe_hypoglycaemic_event.weeks_since_last` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-002](#aftd2022-dm-com-002)

### DM-COM-INSULIN-CONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.driving_relevant_end_organ_effects` = UNKNOWN (unknown)
- `diabetes.glucose_monitoring_records_months` = UNKNOWN (unknown)
- `diabetes.hypoglycaemia_awareness` = UNKNOWN (unknown)
- `diabetes.present` = UNKNOWN (unknown)
- `diabetes.recent_severe_hypoglycaemic_event` = UNKNOWN (unknown)
- `diabetes.regimen_minimises_hypoglycaemia` = UNKNOWN (unknown)
- `diabetes.severe_hypoglycaemic_event.occurred` = UNKNOWN (unknown)
- `diabetes.severe_hypoglycaemic_event.weeks_since_last` = UNKNOWN (unknown)
- `diabetes.specialist_information_available` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-008](#aftd2022-dm-com-008), [AFTD2022-DM-COM-009](#aftd2022-dm-com-009)

### DM-COM-ACUTE-UNSTABLE-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.acutely_unwell` = UNKNOWN (unknown)
- `diabetes.metabolically_unstable` = UNKNOWN (unknown)
- `diabetes.present` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-003](#aftd2022-dm-com-003)

### HTN-COM-SCREEN-001 — unknown

Required facts are unknown or unconfirmed.

- `cardiovascular.blood_pressure.persistent_diastolic` = UNKNOWN (unknown)
- `cardiovascular.blood_pressure.persistent_systolic` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HTN-COM-001](#aftd2022-htn-com-001)

### VIS-COM-SCREEN-001 — unknown

Required facts are unknown or unconfirmed.

- `vision.diplopia.present` = UNKNOWN (unknown)
- `vision.monocular` = UNKNOWN (unknown)
- `vision.uncorrected.better_eye` = 6/6 (present)
  - Source lines 1–1; chars 165:216: Unaided visual acuity: right eye 6/12, left eye 6/6
  - Source lines 1–1; chars 165:216: Unaided visual acuity: right eye 6/12, left eye 6/6
- `vision.uncorrected.left.snellen` = 6/6 (present)
  - Source lines 1–1; chars 165:216: Unaided visual acuity: right eye 6/12, left eye 6/6
- `vision.uncorrected.right.snellen` = 6/12 (present)
  - Source lines 1–1; chars 165:216: Unaided visual acuity: right eye 6/12, left eye 6/6
- `vision.visual_field.confirmed_defect` = False (present)
  - Source lines 1–1; chars 276:296: Visual fields normal

Guideline sources: [AFTD2022-VIS-COM-002](#aftd2022-vis-com-002), [AFTD2022-VIS-COM-004](#aftd2022-vis-com-004), [AFTD2022-VIS-COM-007](#aftd2022-vis-com-007)

### HEAR-COM-SCREEN-001 — triggered

Explicit clinical screening or a documented four-frequency audiogram satisfies the implemented unaided hearing criterion.

- `hearing.average_frequencies_khz` = UNKNOWN (unknown)
- `hearing.clinical_assessment` = no_hearing_loss (present)
  - Source lines 1–1; chars 298:313: Hearing: normal
  - Source lines 1–1; chars 315:330: no hearing loss
  - Source lines 1–1; chars 298:347: Hearing: normal; no hearing loss or hearing aids.
- `hearing.unaided_better_ear_average_db` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HEAR-COM-001](#aftd2022-hear-com-001), [AFTD2022-HEAR-COM-002](#aftd2022-hear-com-002)

### BLK-COM-NO-HISTORY-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.occurred` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-BLK-COM-001](#aftd2022-blk-com-001)

### DM-COM-NO-HISTORY-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.present` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-001](#aftd2022-dm-com-001)

### BLK-COM-DIAGNOSED-REFERRAL-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.diagnosis` = UNKNOWN (unknown)
- `blackout.occurred` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-BLK-COM-006](#aftd2022-blk-com-006)

### DM-COM-GESTATIONAL-REVIEW-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.gestational` = UNKNOWN (unknown)
- `diabetes.present` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-010](#aftd2022-dm-com-010)

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

### AFTD2022-HTN-COM-002

[§2.3.1 · printed 88 / PDF 99](../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)

Table/context: Hypertension: conditional and specialist footnote

> A conditional licence may be considered 
> by the driver licensing authority subject to 
> annual review, taking into account the nature 
> of the driving task and information provided 
> by the treating specialist* as to whether the 
> following criteria are met:
> •	 the person is treated with antihypertensive 
> therapy and effective control of 
> hypertension is achieved over a 4-week 
> follow-up period; and
> •	 there are no side effects from the 
> medication that will impair safe driving; and
> •	 there is no evidence of damage to target 
> organs relevant to driving.
> * Ongoing fitness to drive for commercial 
> vehicle drivers may be assessed by the 
> treating GP provided this is mutually agreed 
> by the specialist, GP and driver licensing 
> authority. The initial granting of a conditional 
> licence must, however, be based on 
> information provided by the specialist.

PDF region: (345.0, 248.0, 530.0, 528.0); text SHA-256: `d83f41571c48dc3b7c6033b230f17179c3146235732afd0f232960104543dc22`.

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

### AFTD2022-VIS-COM-006

[§10.3 · printed 210 / PDF 221](../../../../data/knowledge/raw/ap_g56_22.pdf#page=221)

Table/context: Monocular vision

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person is monocular.
> A conditional licence may be considered 
> by the driver licensing authority subject to 
> 2-yearly review, taking into account the 
> nature of the driving task and information 
> provided by the treating optometrist or 
> ophthalmologist, as to whether the following 
> criteria are met:
> •	 the visual acuity in the remaining eye is 
> 6/9 or better, with or without correction; 
> and
> •	 the visual field in the remaining eye has a 
> horizontal extent of at least 140 degrees 
> within 10 degrees above and below the 
> horizontal midline; and
> •	 there is no other significant visual field 
> loss that is likely to impede driving 
> performance.

PDF region: (350.0, 469.0, 532.0, 741.0); text SHA-256: `ee2c4117abda7e866753cf3ab56f54392eb1f75412f5edc9d95c6aa2ee71f09a`.

### AFTD2022-VIS-COM-007

[§10.3 · printed 211 / PDF 222](../../../../data/knowledge/raw/ap_g56_22.pdf#page=222)

Table/context: Diplopia

> A person is not fit to hold an unconditional 
> licence or a conditional licence:
> •	 if the person experiences any diplopia 
> (other than physiological diplopia) within 
> 20 degrees from central fixation.

PDF region: (349.0, 177.0, 530.0, 247.0); text SHA-256: `23c939289597aecf602313c3e6274cea12bbe4853136c812693bacd460a63883`.

### AFTD2022-DM-COM-004

[§3.3 · printed 101 / PDF 112](../../../../data/knowledge/raw/ap_g56_22.pdf#page=112)

Table/context: Diet and exercise alone

> A person with diabetes treated by diet and 
> exercise alone may drive without licence 
> restriction. They should he reviewed by their 
> treating doctor periodically regarding the 
> progression of their diabetes.

PDF region: (341.0, 208.0, 532.0, 272.0); text SHA-256: `e87d5bc28480bb50a71749bee7186b0af2c922f6ac566d6db2a43313cad68e8c`.

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

### AFTD2022-DM-COM-007

[§3.3 · printed 102 / PDF 113](../../../../data/knowledge/raw/ap_g56_22.pdf#page=113)

Table/context: Insulin-treated diabetes (except gestational diabetes)

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has insulin-treated diabetes.

PDF region: (341.0, 177.0, 532.0, 223.0); text SHA-256: `c282e63a3ed339de957b2bb665974fbe8ba99675e92293609823d9bfae70e2a4`.

### AFTD2022-DM-COM-002

[§3.2.1 · printed 94 / PDF 105](../../../../data/knowledge/raw/ap_g56_22.pdf#page=105)

Table/context: Severe hypoglycaemia non-driving guidance

> Non-driving period after a ‘severe 
> hypoglycaemic event’
> If a severe hypoglycaemic event occurs (as 
> defined in section 3.2.1. Hypoglycaemia), the 
> person should not drive for a significant period 
> of time and will need to be urgently assessed. 
> The minimum period of time before returning 
> to drive is generally six weeks because it often 
> takes many weeks for patterns of glucose 
> control and behaviour to be re-established and 
> for any temporary ‘impaired hypoglycaemia 
> awareness’ to resolve (see below). The non-
> driving period will depend on factors such 
> as identifying the reason for the episode, the 
> specialist’s opinion and the type of motor vehicle 
> licence. The specialist’s recommendation for 
> returning to driving should be based on the 
> patient’s behaviour and objective measures of 
> glycaemic control (documented blood glucose) 
> over a reasonable interval. 
> Impaired hypoglycaemic awareness 10–14

PDF region: (55.0, 50.0, 294.0, 422.0); text SHA-256: `04a88c68536b1ff96803f0262cf8f0f63687a419e4600ceef88ee0e623b06069`.

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

### AFTD2022-DM-COM-010

[§3.2.4 · printed 96 / PDF 107](../../../../data/knowledge/raw/ap_g56_22.pdf#page=107)

Table/context: Gestational diabetes

> 3.2.4. Gestational diabetes mellitus
> The standards in this chapter apply to diabetes 
> mellitus as a chronic condition. The self-limiting 
> condition known as gestational diabetes 
> mellitus does not affect licensing. However, 
> consideration should be given to short-term 
> fitness to drive in women with gestational 
> diabetes mellitus treated with insulin, although 
> severe hypoglycaemia in this condition is rare. 
> Affected women should be counselled to 
> recognise symptoms and to restrict driving when 
> symptoms occur.

PDF region: (55.0, 50.0, 295.0, 282.0); text SHA-256: `8499e71512aec0eb89dca54bbf02a9ba1570e783118d3a618c3e9a303377ac3f`.

## Clinician checklist

- [ ] Clinician: review source facts, rule applicability and every provisional conclusion.
- [ ] Confirm the commercial driving task and assess conditions outside the five-module scope.
- [ ] Confirm missing/unverified case fact: blackout.mechanism_status
- [ ] Confirm missing/unverified case fact: blackout.occurred
- [ ] Confirm missing/unverified case fact: cardiovascular.blood_pressure.persistent_diastolic
- [ ] Confirm missing/unverified case fact: cardiovascular.blood_pressure.persistent_systolic
- [ ] Confirm missing/unverified case fact: diabetes.gestational
- [ ] Confirm missing/unverified case fact: diabetes.present
- [ ] Confirm missing/unverified case fact: vision.diplopia.present
- [ ] Confirm missing/unverified case fact: vision.monocular

## Case source

```text
Commercial driver medical. 46-year-old female operations supervisor. Medical history: stable seasonal rhinitis only. BP 132/82 mmHg; HR 70 bpm. No cardiac symptoms. Unaided visual acuity: right eye 6/12, left eye 6/6; corrected with glasses to right eye 6/6 and left eye 6/6. Visual fields normal. Hearing: normal; no hearing loss or hearing aids.

```

Input SHA-256: `ac86ca9d97ac9acd8e43ce1dae225114cb291742fb54df0de635b68e38b42892`
Rule-result SHA-256: `a756afcc55fdb6b23787616508cb90fa13507aa68cfd4bdb4cd78a213141efbb`
Evidence-pack SHA-256: `ccce754caff916e46b66a218e600e97accc3b3ce90b45d25bb6f06dd322b3912`

## Unverified local-model commentary

This 46-year-old female operations supervisor presents with insufficient information for a commercial driver medical assessment. Her blood pressure is 132/82 mmHg, which does not meet the unconditional licence criteria. Further investigation is required to determine the nature of her hypertension and whether it is effectively controlled. Additionally, her blackout history is unclear, and further evaluation is needed to determine the underlying cause and potential impact on her fitness to drive.
