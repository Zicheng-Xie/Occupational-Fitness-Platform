# Clinical review draft — CX-LONG-177

CX-LONG-177: Temporarily unfit. 2 requested modules; 11 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| vision | Insufficient information | human_review | 6 |
| diabetes | Temporarily unfit | human_review | 5 |

## Established rule findings

The provisional outcome reflects the applicable rule priority. Missing information in other modules remains visible and does not erase an established adverse finding.

- diabetes: `DM-COM-ACUTE-UNSTABLE-001` - The person is acutely unwell with metabolically unstable diabetes.

## Information coverage

- vision: No source-supported facts for this requested module; some facts require confirmation; 0 supported fields; 6 unresolved rule fields.
- diabetes: Source-supported facts available; some facts require confirmation; 3 supported fields; 5 unresolved rule fields.

## Retrieval activity

Rule-scoped ranking calls: 16.
Symptom discovery searches: 2.
Zero triggered rules does not mean retrieval failed. Retrieved text is not a diagnosis.

### diabetes symptom retrieval

> The same current clinical review separately confirms that the driver has diabetes and is acutely unwell with metabolically unstable diabetes after vomiting and urgent glucose assessment; an older well-visit result is present in the folder, but the current physician has not documented resolution of this separate acute condition.

- [AFTD2022-DM-COM-003, PDF 106](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=106)
- [AFTD2022-DM-COM-006, PDF 112](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=112)
- [AFTD2022-DM-COM-008, PDF 113](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=113)
- [AFTD2022-DM-COM-002, PDF 105](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=105)
- [AFTD2022-DM-COM-009, PDF 110](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=110)
### vision symptom retrieval

> The current ophthalmologist's signed examination confirms non-physiological diplopia within 19 degrees of central fixation, reproduced during the assessment even though the driver says the two overlapping road-sign images sometimes merge after blinking; an older note reported comfortable reading at a desk, but that earlier description neither contradicts the current reproduced double vision nor establishes that a patch or new lenses have resolved it.

- [AFTD2022-VIS-COM-007, PDF 222](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=222)
- [AFTD2022-VIS-COM-005, PDF 221](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=221)
- [AFTD2022-VIS-COM-003, PDF 220](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=220)
- [AFTD2022-VIS-COM-006, PDF 221](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=221)
- [AFTD2022-VIS-COM-004, PDF 221](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=221)

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: Possible extraction issues require confirmation
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
Confirm diabetes.treatment_category (omission): Independent source reading differs from the extraction. The driver has diabetes and is acutely unwell with metabolically unstable diabetes after vomiting and urgent glucose assessment.
Confirm vision.diplopia.physiological (unsupported): Independent source reading differs from the extraction. The source passages do not explicitly state whether the diplopia is physiological or non-physiological. While passage 2 mentions that the diplopia is reproduced during the assessment, it does not provide a clear indication of whether it is physiological or not.
Confirm vision.diplopia.present (omission): Independent source reading differs from the extraction. The patient explicitly has diplopia (double vision) as confirmed by the current ophthalmologist's signed examination, which reports non-physiological diplopia within 19 degrees of central fixation.
Fields withheld from rule inputs: diabetes.treatment_category, vision.diplopia.physiological, vision.diplopia.present

### diabetes.treatment_category — omission

Independent source reading differs from the extraction. The driver has diabetes and is acutely unwell with metabolically unstable diabetes after vomiting and urgent glucose assessment.

Source lines 9–9; characters 1288:1617
> The same current clinical review separately confirms that the driver has diabetes and is acutely unwell with metabolically unstable diabetes after vomiting and urgent glucose assessment; an older well-visit result is present in the folder, but the current physician has not documented resolution of this separate acute condition.

### vision.diplopia.physiological — unsupported

Independent source reading differs from the extraction. The source passages do not explicitly state whether the diplopia is physiological or non-physiological. While passage 2 mentions that the diplopia is reproduced during the assessment, it does not provide a clear indication of whether it is physiological or not.

Source lines 5–5; characters 433:687
> The current ophthalmologist's signed examination confirms non-physiological diplopia within 19 degrees of central fixation, reproduced during the assessment even though the driver says the two overlapping road-sign images sometimes merge after blinking; 

### vision.diplopia.present — omission

Independent source reading differs from the extraction. The patient explicitly has diplopia (double vision) as confirmed by the current ophthalmologist's signed examination, which reports non-physiological diplopia within 19 degrees of central fixation.

Source lines 5–5; characters 433:887
> The current ophthalmologist's signed examination confirms non-physiological diplopia within 19 degrees of central fixation, reproduced during the assessment even though the driver says the two overlapping road-sign images sometimes merge after blinking; an older note reported comfortable reading at a desk, but that earlier description neither contradicts the current reproduced double vision nor establishes that a patch or new lenses have resolved it.

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

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

- `vision.diplopia.physiological` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 433:687: The current ophthalmologist's signed examination confirms non-physiological diplopia within 19 degrees of central fixation, reproduced during the assessment even though the driver says the two overlapping road-sign images sometimes merge after blinking; 
  - Source lines 5–5; chars 433:687: The current ophthalmologist's signed examination confirms non-physiological diplopia within 19 degrees of central fixation, reproduced during the assessment even though the driver says the two overlapping road-sign images sometimes merge after blinking; 
- `vision.diplopia.present` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 433:887: The current ophthalmologist's signed examination confirms non-physiological diplopia within 19 degrees of central fixation, reproduced during the assessment even though the driver says the two overlapping road-sign images sometimes merge after blinking; an older note reported comfortable reading at a desk, but that earlier description neither contradicts the current reproduced double vision nor establishes that a patch or new lenses have resolved it.
- `vision.diplopia.within_20_degrees` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-VIS-COM-007](#aftd2022-vis-com-007)

### DM-COM-DIET-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.driving_relevant_comorbidity_status` = UNKNOWN (unknown)
- `diabetes.present` = True (present)
  - Source lines 9–9; chars 1288:1475: The same current clinical review separately confirms that the driver has diabetes and is acutely unwell with metabolically unstable diabetes after vomiting and urgent glucose assessment; 
- `diabetes.treatment_category` = UNKNOWN (requires_confirmation)
  - Source lines 9–9; chars 1288:1617: The same current clinical review separately confirms that the driver has diabetes and is acutely unwell with metabolically unstable diabetes after vomiting and urgent glucose assessment; an older well-visit result is present in the folder, but the current physician has not documented resolution of this separate acute condition.

Guideline sources: [AFTD2022-DM-COM-004](#aftd2022-dm-com-004)

### DM-COM-NONINSULIN-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.present` = True (present)
  - Source lines 9–9; chars 1288:1475: The same current clinical review separately confirms that the driver has diabetes and is acutely unwell with metabolically unstable diabetes after vomiting and urgent glucose assessment; 
- `diabetes.treatment_category` = UNKNOWN (requires_confirmation)
  - Source lines 9–9; chars 1288:1617: The same current clinical review separately confirms that the driver has diabetes and is acutely unwell with metabolically unstable diabetes after vomiting and urgent glucose assessment; an older well-visit result is present in the folder, but the current physician has not documented resolution of this separate acute condition.

Guideline sources: [AFTD2022-DM-COM-005](#aftd2022-dm-com-005)

### DM-COM-NONINSULIN-CONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.driving_relevant_end_organ_effects` = UNKNOWN (unknown)
- `diabetes.hypoglycaemia_awareness` = UNKNOWN (unknown)
- `diabetes.initial_specialist_information_available` = UNKNOWN (unknown)
- `diabetes.present` = True (present)
  - Source lines 9–9; chars 1288:1475: The same current clinical review separately confirms that the driver has diabetes and is acutely unwell with metabolically unstable diabetes after vomiting and urgent glucose assessment; 
- `diabetes.recent_severe_hypoglycaemic_event` = UNKNOWN (unknown)
- `diabetes.regimen_minimises_hypoglycaemia` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-006](#aftd2022-dm-com-006)

### DM-COM-INSULIN-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.gestational` = UNKNOWN (unknown)
- `diabetes.present` = True (present)
  - Source lines 9–9; chars 1288:1475: The same current clinical review separately confirms that the driver has diabetes and is acutely unwell with metabolically unstable diabetes after vomiting and urgent glucose assessment; 
- `diabetes.treatment_category` = UNKNOWN (requires_confirmation)
  - Source lines 9–9; chars 1288:1617: The same current clinical review separately confirms that the driver has diabetes and is acutely unwell with metabolically unstable diabetes after vomiting and urgent glucose assessment; an older well-visit result is present in the folder, but the current physician has not documented resolution of this separate acute condition.

Guideline sources: [AFTD2022-DM-COM-007](#aftd2022-dm-com-007)

### DM-COM-SEVERE-HYPO-WAIT-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.present` = True (present)
  - Source lines 9–9; chars 1288:1475: The same current clinical review separately confirms that the driver has diabetes and is acutely unwell with metabolically unstable diabetes after vomiting and urgent glucose assessment; 
- `diabetes.severe_hypoglycaemic_event.occurred` = UNKNOWN (unknown)
- `diabetes.severe_hypoglycaemic_event.weeks_since_last` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-002](#aftd2022-dm-com-002)

### DM-COM-INSULIN-CONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.driving_relevant_end_organ_effects` = UNKNOWN (unknown)
- `diabetes.glucose_monitoring_records_months` = UNKNOWN (unknown)
- `diabetes.hypoglycaemia_awareness` = UNKNOWN (unknown)
- `diabetes.present` = True (present)
  - Source lines 9–9; chars 1288:1475: The same current clinical review separately confirms that the driver has diabetes and is acutely unwell with metabolically unstable diabetes after vomiting and urgent glucose assessment; 
- `diabetes.recent_severe_hypoglycaemic_event` = UNKNOWN (unknown)
- `diabetes.regimen_minimises_hypoglycaemia` = UNKNOWN (unknown)
- `diabetes.severe_hypoglycaemic_event.occurred` = UNKNOWN (unknown)
- `diabetes.severe_hypoglycaemic_event.weeks_since_last` = UNKNOWN (unknown)
- `diabetes.specialist_information_available` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-008](#aftd2022-dm-com-008), [AFTD2022-DM-COM-009](#aftd2022-dm-com-009)

### DM-COM-ACUTE-UNSTABLE-001 — triggered

The person is acutely unwell with metabolically unstable diabetes.

- `diabetes.acutely_unwell` = True (present)
  - Source lines 9–9; chars 1288:1475: The same current clinical review separately confirms that the driver has diabetes and is acutely unwell with metabolically unstable diabetes after vomiting and urgent glucose assessment; 
- `diabetes.metabolically_unstable` = True (present)
  - Source lines 9–9; chars 1288:1475: The same current clinical review separately confirms that the driver has diabetes and is acutely unwell with metabolically unstable diabetes after vomiting and urgent glucose assessment; 
  - Source lines 9–9; chars 1397:1428: metabolically unstable diabetes
- `diabetes.present` = True (present)
  - Source lines 9–9; chars 1288:1475: The same current clinical review separately confirms that the driver has diabetes and is acutely unwell with metabolically unstable diabetes after vomiting and urgent glucose assessment; 

Guideline sources: [AFTD2022-DM-COM-003](#aftd2022-dm-com-003)

### VIS-COM-SCREEN-001 — unknown

Required facts are unknown or unconfirmed.

- `vision.diplopia.present` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 433:887: The current ophthalmologist's signed examination confirms non-physiological diplopia within 19 degrees of central fixation, reproduced during the assessment even though the driver says the two overlapping road-sign images sometimes merge after blinking; an older note reported comfortable reading at a desk, but that earlier description neither contradicts the current reproduced double vision nor establishes that a patch or new lenses have resolved it.
- `vision.monocular` = UNKNOWN (unknown)
- `vision.uncorrected.better_eye` = UNKNOWN (unknown)
- `vision.uncorrected.left.snellen` = UNKNOWN (unknown)
- `vision.uncorrected.right.snellen` = UNKNOWN (unknown)
- `vision.visual_field.confirmed_defect` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-VIS-COM-002](#aftd2022-vis-com-002), [AFTD2022-VIS-COM-004](#aftd2022-vis-com-004), [AFTD2022-VIS-COM-007](#aftd2022-vis-com-007)

### DM-COM-GESTATIONAL-REVIEW-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.gestational` = UNKNOWN (unknown)
- `diabetes.present` = True (present)
  - Source lines 9–9; chars 1288:1475: The same current clinical review separately confirms that the driver has diabetes and is acutely unwell with metabolically unstable diabetes after vomiting and urgent glucose assessment; 

Guideline sources: [AFTD2022-DM-COM-010](#aftd2022-dm-com-010)

## Guideline evidence

### AFTD2022-VIS-COM-002

[§10.3 · printed 209 / PDF 220](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=220)

Table/context: Visual acuity: unconditional

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person’s uncorrected visual acuity is 
> worse than 6/9 in the better eye; or
> •	 if the person’s uncorrected visual acuity is 
> worse than 6/18 in either eye.

PDF region: (349.0, 261.0, 530.0, 349.0); text SHA-256: `598a3da216c03def0f6bcbdcd6bd036f57c5cf7a1e99d224b1fd08d5908bcc39`.

### AFTD2022-VIS-COM-003

[§10.3 · printed 209 / PDF 220](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=220)

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

[§10.3 · printed 210 / PDF 221](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=221)

Table/context: Visual fields: unconditional

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has any visual field defect.

PDF region: (350.0, 177.0, 532.0, 223.0); text SHA-256: `d54b84732d5cc173a2f28c988779c0e5717b436ce27bb2630ccbc25b9dd9ee61`.

### AFTD2022-VIS-COM-005

[§10.3 · printed 210 / PDF 221](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=221)

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

[§10.3 · printed 210 / PDF 221](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=221)

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

[§10.3 · printed 211 / PDF 222](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=222)

Table/context: Diplopia

> A person is not fit to hold an unconditional 
> licence or a conditional licence:
> •	 if the person experiences any diplopia 
> (other than physiological diplopia) within 
> 20 degrees from central fixation.

PDF region: (349.0, 177.0, 530.0, 247.0); text SHA-256: `23c939289597aecf602313c3e6274cea12bbe4853136c812693bacd460a63883`.

### AFTD2022-DM-COM-004

[§3.3 · printed 101 / PDF 112](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=112)

Table/context: Diet and exercise alone

> A person with diabetes treated by diet and 
> exercise alone may drive without licence 
> restriction. They should he reviewed by their 
> treating doctor periodically regarding the 
> progression of their diabetes.

PDF region: (341.0, 208.0, 532.0, 272.0); text SHA-256: `e87d5bc28480bb50a71749bee7186b0af2c922f6ac566d6db2a43313cad68e8c`.

### AFTD2022-DM-COM-005

[§3.3 · printed 101 / PDF 112](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=112)

Table/context: Non-insulin agents: unconditional

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has non–insulin treated 
> diabetes mellitus and is being treated with 
> glucose-lowering agents other than insulin.

PDF region: (341.0, 286.0, 532.0, 355.0); text SHA-256: `fc60bdaa37f4ef12dea8c98a87935c4d4903f77cdb13b89aeeba9821dda0241f`.

### AFTD2022-DM-COM-006

[§3.3 · printed 101 / PDF 112](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=112)

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

[§3.3 · printed 102 / PDF 113](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=113)

Table/context: Insulin-treated diabetes (except gestational diabetes)

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has insulin-treated diabetes.

PDF region: (341.0, 177.0, 532.0, 223.0); text SHA-256: `c282e63a3ed339de957b2bb665974fbe8ba99675e92293609823d9bfae70e2a4`.

### AFTD2022-DM-COM-002

[§3.2.1 · printed 94 / PDF 105](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=105)

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

### AFTD2022-DM-COM-008

[§3.3 · printed 102 / PDF 113](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=113)

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

### AFTD2022-DM-COM-009

[§3.3.2 · printed 99 / PDF 110](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=110)

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

### AFTD2022-DM-COM-003

[§3.2.2 · printed 95 / PDF 106](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=106)

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

### AFTD2022-DM-COM-010

[§3.2.4 · printed 96 / PDF 107](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=107)

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
- [ ] Confirm missing/unverified case fact: diabetes.driving_relevant_comorbidity_status
- [ ] Confirm missing/unverified case fact: diabetes.gestational
- [ ] Confirm missing/unverified case fact: diabetes.severe_hypoglycaemic_event.occurred
- [ ] Confirm missing/unverified case fact: diabetes.severe_hypoglycaemic_event.weeks_since_last
- [ ] Confirm missing/unverified case fact: diabetes.treatment_category
- [ ] Confirm missing/unverified case fact: vision.diplopia.present
- [ ] Confirm missing/unverified case fact: vision.monocular
- [ ] Confirm missing/unverified case fact: vision.uncorrected.better_eye
- [ ] Confirm missing/unverified case fact: vision.uncorrected.left.snellen
- [ ] Confirm missing/unverified case fact: vision.uncorrected.right.snellen
- [ ] Confirm missing/unverified case fact: vision.visual_field.confirmed_defect
- [ ] requires_confirmation
- [ ] Extraction semantic review: Possible extraction issues require confirmation
- [ ] This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
- [ ] Confirm diabetes.treatment_category (omission): Independent source reading differs from the extraction. The driver has diabetes and is acutely unwell with metabolically unstable diabetes after vomiting and urgent glucose assessment.
- [ ] Confirm vision.diplopia.physiological (unsupported): Independent source reading differs from the extraction. The source passages do not explicitly state whether the diplopia is physiological or non-physiological. While passage 2 mentions that the diplopia is reproduced during the assessment, it does not provide a clear indication of whether it is physiological or not.
- [ ] Confirm vision.diplopia.present (omission): Independent source reading differs from the extraction. The patient explicitly has diplopia (double vision) as confirmed by the current ophthalmologist's signed examination, which reports non-physiological diplopia within 19 degrees of central fixation.
- [ ] Fields withheld from rule inputs: diabetes.treatment_category, vision.diplopia.physiological, vision.diplopia.present

## Case source

```text
Synthetic nurse note for software testing. No real patient data.

At a scheduled commercial-driver medical, the driver answers questions in several stages because a dispatcher keeps calling about the next route, while the nurse checks a current clinical document against a copied workplace summary; an observation described confidently in conversation is kept separate from a finding actually recorded in an identified examination.

The current ophthalmologist's signed examination confirms non-physiological diplopia within 19 degrees of central fixation, reproduced during the assessment even though the driver says the two overlapping road-sign images sometimes merge after blinking; an older note reported comfortable reading at a desk, but that earlier description neither contradicts the current reproduced double vision nor establishes that a patch or new lenses have resolved it.

The usual work involves coupling trailers, checking mirrors, interpreting radio messages and responding to pedestrians in a loading area, with breaks that can be delayed when deliveries run late; the driver explains which difficulty occurred while stationary and which was noticed during ordinary duties, rather than claiming that quiet conversation in the clinic reproduces every task in the cab.

The same current clinical review separately confirms that the driver has diabetes and is acutely unwell with metabolically unstable diabetes after vomiting and urgent glucose assessment; an older well-visit result is present in the folder, but the current physician has not documented resolution of this separate acute condition.

The record is prepared for the reviewing clinician with the sequence of events and the provenance of the available findings intact, because the employer summary and the driver's account answer different questions; a completed test is retained as such, but an unresolved detail is not filled in from a family member's history or from an earlier document with different testing conditions.

```

Input SHA-256: `5db50408d37aee6048916f716b4b2b312b63047d27c49bb35a45eb1b684311d2`
Rule-result SHA-256: `fc857f2b34e6a61039a1870c9b94b4652928961af66b163a7a3ebb3dc3de7e7b`
Evidence-pack SHA-256: `0a3fd1491071614bd73fdc5284c591f9e61e4f476904916090d0d6ee3020188b`
