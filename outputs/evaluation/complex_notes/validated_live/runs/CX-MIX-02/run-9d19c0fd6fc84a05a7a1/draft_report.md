# Clinical review draft — CX-MIX-02

CX-MIX-02: Insufficient information. 3 requested modules; 11 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| hypertension | Insufficient information | human_review | 2 |
| vision | Insufficient information | human_review | 6 |
| hearing | Insufficient information | human_review | 3 |

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: Not completed (model unavailable or response invalid)
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.

[Semantic review audit](llm_semantic_review.json)


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

### VIS-COM-ACUITY-UNCONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `vision.uncorrected.better_eye` = UNKNOWN (unknown)
- `vision.uncorrected.left.snellen` = UNKNOWN (unknown)
- `vision.uncorrected.right.snellen` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-VIS-COM-002](#aftd2022-vis-com-002)

### VIS-COM-ACUITY-CONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `vision.corrected.better_eye` = UNKNOWN (unknown)
- `vision.specialist_assessment_available` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-VIS-COM-003](#aftd2022-vis-com-003)

### VIS-COM-FIELD-UNCONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `vision.visual_field.confirmed_defect` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-VIS-COM-004](#aftd2022-vis-com-004)

### VIS-COM-FIELD-CONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `vision.specialist_assessment_available` = UNKNOWN (unknown)
- `vision.visual_field.binocular_horizontal_extent_degrees` = UNKNOWN (unknown)
- `vision.visual_field.confirmed_defect` = UNKNOWN (unknown)
- `vision.visual_field.measured_within_10_degrees_vertical` = UNKNOWN (unknown)
- `vision.visual_field.significant_loss_likely_to_impede_driving` = UNKNOWN (unknown)
- `vision.visual_field.static_and_unlikely_to_progress_rapidly` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-VIS-COM-005](#aftd2022-vis-com-005)

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

### HEAR-COM-AUDIOMETRY-MISSING-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.audiometry.available` = UNKNOWN (unknown)
- `hearing.clinical_assessment` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HEAR-COM-001](#aftd2022-hear-com-001)

### HEAR-COM-UNCONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.average_frequencies_khz` = UNKNOWN (unknown)
- `hearing.clinical_assessment` = UNKNOWN (unknown)
- `hearing.unaided_better_ear_average_db` = UNKNOWN (unknown)

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

### HTN-COM-SCREEN-001 — unknown

Required facts are unknown or unconfirmed.

- `cardiovascular.blood_pressure.persistent_diastolic` = UNKNOWN (unknown)
- `cardiovascular.blood_pressure.persistent_systolic` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HTN-COM-001](#aftd2022-htn-com-001)

### VIS-COM-SCREEN-001 — unknown

Required facts are unknown or unconfirmed.

- `vision.diplopia.present` = UNKNOWN (unknown)
- `vision.monocular` = UNKNOWN (unknown)
- `vision.uncorrected.better_eye` = UNKNOWN (unknown)
- `vision.uncorrected.left.snellen` = UNKNOWN (unknown)
- `vision.uncorrected.right.snellen` = UNKNOWN (unknown)
- `vision.visual_field.confirmed_defect` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-VIS-COM-002](#aftd2022-vis-com-002), [AFTD2022-VIS-COM-004](#aftd2022-vis-com-004), [AFTD2022-VIS-COM-007](#aftd2022-vis-com-007)

### HEAR-COM-SCREEN-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.average_frequencies_khz` = UNKNOWN (unknown)
- `hearing.clinical_assessment` = UNKNOWN (unknown)
- `hearing.unaided_better_ear_average_db` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HEAR-COM-001](#aftd2022-hear-com-001), [AFTD2022-HEAR-COM-002](#aftd2022-hear-com-002)

## Guideline evidence

### AFTD2022-HTN-COM-001

[§2.3.1 · printed 88 / PDF 99](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)

Table/context: Hypertension: unconditional

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has blood pressure 
> consistently > 170 systolic or > 100 diastolic 
> (treated or untreated).

PDF region: (345.0, 177.0, 530.0, 247.0); text SHA-256: `eeacf5b9430b10bb961f6b727f6b4eb638baaf8aeecde7413ad4b4dea2baef7d`.

### AFTD2022-HTN-COM-002

[§2.3.1 · printed 88 / PDF 99](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)

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

### AFTD2022-VIS-COM-002

[§10.3 · printed 209 / PDF 220](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=220)

Table/context: Visual acuity: unconditional

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person’s uncorrected visual acuity is 
> worse than 6/9 in the better eye; or
> •	 if the person’s uncorrected visual acuity is 
> worse than 6/18 in either eye.

PDF region: (349.0, 261.0, 530.0, 349.0); text SHA-256: `598a3da216c03def0f6bcbdcd6bd036f57c5cf7a1e99d224b1fd08d5908bcc39`.

### AFTD2022-VIS-COM-003

[§10.3 · printed 209 / PDF 220](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=220)

Table/context: Visual acuity: conditional and qualifications

> A conditional licence may be considered 
> by the driver licensing authority subject to 
> periodic review if the standard is met with 
> corrective lenses*.
> If the person’s vision is worse than 6/18 in 
> the worse eye, a conditional licence may be 
> considered by the driver licensing authority 
> subject to periodic review, provided the 
> visual acuity in the better eye is 6/9 (with or 
> without corrective lenses*) according to the 
> treating optometrist or ophthalmologist. 
> The driver licensing authority will take into 
> account:
> •	 the nature of the driving task; and
> •	 the nature of any underlying disorder; and
> •	 any other restriction advised by the 
> optometrist or ophthalmologist.
> * Refer to section 10.2.7. Orthokeratology 
> therapy for information on meeting the 
> standard using orthokeratology therapy.

PDF region: (349.0, 350.0, 530.0, 623.0); text SHA-256: `bd2558dd515de6ad6f25390240e1eaf6ec2ec99ce42167f4094b447d750b3dd0`.

### AFTD2022-VIS-COM-004

[§10.3 · printed 210 / PDF 221](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=221)

Table/context: Visual fields: unconditional

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has any visual field defect.

PDF region: (350.0, 177.0, 532.0, 223.0); text SHA-256: `d54b84732d5cc173a2f28c988779c0e5717b436ce27bb2630ccbc25b9dd9ee61`.

### AFTD2022-VIS-COM-005

[§10.3 · printed 210 / PDF 221](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=221)

Table/context: Visual fields: conditional

> A conditional licence may be considered 
> by the driver licensing authority subject 
> to annual review, taking into account the 
> nature of the driving task and information 
> provided by the treating optometrist or 
> ophthalmologist as to whether the following 
> criteria are met:
> •	 the binocular visual field has an extent of 
> at least 140 degrees within 10 degrees 
> above and below the horizontal midline; 
> and
> •	 the person has no significant visual 
> field loss (scotoma, hemianopia, 
> quadrantanopia) that is likely to impede 
> driving performance; and
> •	 the visual field loss is static and unlikely to 
> progress rapidly.

PDF region: (350.0, 224.0, 532.0, 449.0); text SHA-256: `c62fcf5e0027b492c61b0ec8b0288b1b380cbe0141893c731bc5ddfcf9e85653`.

### AFTD2022-VIS-COM-006

[§10.3 · printed 210 / PDF 221](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=221)

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

[§10.3 · printed 211 / PDF 222](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=222)

Table/context: Diplopia

> A person is not fit to hold an unconditional 
> licence or a conditional licence:
> •	 if the person experiences any diplopia 
> (other than physiological diplopia) within 
> 20 degrees from central fixation.

PDF region: (349.0, 177.0, 530.0, 247.0); text SHA-256: `23c939289597aecf602313c3e6274cea12bbe4853136c812693bacd460a63883`.

### AFTD2022-HEAR-COM-001

[§4.3 · printed 109 / PDF 120](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)

Table/context: Hearing: clinical assessment and audiometry

> Compliance with the standard should be clinically 
> assessed initially. If the initial clinical assessment 
> indicates possible hearing loss, the person should 
> be referred for audiometry.

PDF region: (320.0, 273.0, 531.0, 325.0); text SHA-256: `658c8e0d61ff7a066d001e669c6673a4dca8fd439d85009a8ecef07432d5ddbb`.

### AFTD2022-HEAR-COM-002

[§4.3 · printed 109 / PDF 120](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)

Table/context: Hearing: unaided four-frequency average

> A person is not fit to hold an unconditional licence:
> •	 if the person has unaided hearing loss ≥ 40 dB 
> in the better ear (averaged over the frequencies 
> 0.5, 1, 2 and 3 KHz).

PDF region: (320.0, 327.0, 531.0, 385.0); text SHA-256: `78ef0b09576857072cbc395e26ad22ce08bd7e94bca53ee68bf36f48facb0b6a`.

### AFTD2022-HEAR-COM-003

[§4.3 · printed 109 / PDF 120](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)

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

[§4.3 · printed 109 / PDF 120](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)

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

## Clinician checklist

- [ ] Clinician: review source facts, rule applicability and every provisional conclusion.
- [ ] Confirm the commercial driving task and assess conditions outside the five-module scope.
- [ ] Confirm missing/unverified case fact: cardiovascular.blood_pressure.persistent_diastolic
- [ ] Confirm missing/unverified case fact: cardiovascular.blood_pressure.persistent_systolic
- [ ] Confirm missing/unverified case fact: hearing.average_frequencies_khz
- [ ] Confirm missing/unverified case fact: hearing.clinical_assessment
- [ ] Confirm missing/unverified case fact: hearing.unaided_better_ear_average_db
- [ ] Confirm missing/unverified case fact: vision.diplopia.present
- [ ] Confirm missing/unverified case fact: vision.monocular
- [ ] Confirm missing/unverified case fact: vision.uncorrected.better_eye
- [ ] Confirm missing/unverified case fact: vision.uncorrected.left.snellen
- [ ] Confirm missing/unverified case fact: vision.uncorrected.right.snellen
- [ ] Confirm missing/unverified case fact: vision.visual_field.confirmed_defect
- [ ] unavailable_or_invalid
- [ ] Extraction semantic review: Not completed (model unavailable or response invalid)
- [ ] This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.

## Case source

```text
At today's assessment BP 172/98 mmHg was recorded after the driver hurried up the stairs, but he recalls lower readings at home and no repeat has been taken; he recently changed tablets and feels briefly light-headed when rising, so persistent pressure, treatment stability and driving-impairing side effects remain to be clarified.

He also says headlights split into two after several hours at night, although the effect disappeared before examination and he cannot say whether covering one eye changes it; a six-month-old slip with 6/9 and 6/12 does not identify correction status, and no current acuity or specialist report is available.

In the noisy depot he misses spoken dispatch instructions despite using an aid, while a screening sheet marked 45 dB does not identify the ear or test frequencies; the nurse cannot use that number as an unaided better-ear average and has requested formal audiometry.

```

Input SHA-256: `3544dc70cf2f289e852a58540ad60b0bd61a16c9870c6d9fbeafb9ea30a0fac2`
Rule-result SHA-256: `02742c6eb541cd9616bcf7625ac52dc8a45f292ff9bf9d9639cbad7f415e9aa6`
Evidence-pack SHA-256: `acf3b9de46517988bd38e8579c305c4044220889ff80368d868107fb449e74ad`
