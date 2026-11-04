# Clinical review draft — CX-LONG-052

CX-LONG-052: Insufficient information. 1 requested modules; 6 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| vision | Insufficient information | human_review | 6 |

## Established rule findings

No rule criteria were established from the available verified facts. This does not establish absence of disease or failure of retrieval.


## Information coverage

- vision: No source-supported facts for this requested module; some facts require confirmation; 0 supported fields; 6 unresolved rule fields.

## Retrieval activity

Rule-scoped ranking calls: 8.
Symptom discovery searches: 1.
Zero triggered rules does not mean retrieval failed. Retrieved text is not a diagnosis.

### vision symptom retrieval

> The current ophthalmologist's signed examination confirms non-physiological diplopia within 18 degrees of central fixation, reproduced during the assessment even though the driver says the two overlapping road-sign images sometimes merge after blinking; an older note reported comfortable reading at a desk, but that earlier description neither contradicts the current reproduced double vision nor establishes that a patch or new lenses have resolved it.

- [AFTD2022-VIS-COM-007, PDF 222](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=222)
- [AFTD2022-VIS-COM-005, PDF 221](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=221)
- [AFTD2022-VIS-COM-003, PDF 220](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=220)
- [AFTD2022-VIS-COM-006, PDF 221](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=221)
- [AFTD2022-VIS-COM-004, PDF 221](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=221)

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: Possible extraction issues require confirmation
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
Confirm vision.diplopia.physiological (unsupported): Independent source reading differs from the extraction. The question is about the exact meaning of the diplopia, not whether the patient is fit to drive. The source passages do not explicitly state whether the diplopia is physiological or non-physiological.
Confirm vision.diplopia.present (omission): Independent source reading differs from the extraction. The patient explicitly has diplopia (double vision) as confirmed by the current ophthalmologist's signed examination, which reports non-physiological diplopia within 18 degrees of central fixation, reproduced during the assessment.
Fields withheld from rule inputs: vision.diplopia.physiological, vision.diplopia.present

### vision.diplopia.physiological — unsupported

Independent source reading differs from the extraction. The question is about the exact meaning of the diplopia, not whether the patient is fit to drive. The source passages do not explicitly state whether the diplopia is physiological or non-physiological.

Source lines 5–5; characters 448:702
> The current ophthalmologist's signed examination confirms non-physiological diplopia within 18 degrees of central fixation, reproduced during the assessment even though the driver says the two overlapping road-sign images sometimes merge after blinking; 

### vision.diplopia.present — omission

Independent source reading differs from the extraction. The patient explicitly has diplopia (double vision) as confirmed by the current ophthalmologist's signed examination, which reports non-physiological diplopia within 18 degrees of central fixation, reproduced during the assessment.

Source lines 5–5; characters 448:902
> The current ophthalmologist's signed examination confirms non-physiological diplopia within 18 degrees of central fixation, reproduced during the assessment even though the driver says the two overlapping road-sign images sometimes merge after blinking; an older note reported comfortable reading at a desk, but that earlier description neither contradicts the current reproduced double vision nor establishes that a patch or new lenses have resolved it.

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
  - Source lines 5–5; chars 448:702: The current ophthalmologist's signed examination confirms non-physiological diplopia within 18 degrees of central fixation, reproduced during the assessment even though the driver says the two overlapping road-sign images sometimes merge after blinking; 
  - Source lines 5–5; chars 448:702: The current ophthalmologist's signed examination confirms non-physiological diplopia within 18 degrees of central fixation, reproduced during the assessment even though the driver says the two overlapping road-sign images sometimes merge after blinking; 
- `vision.diplopia.present` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:902: The current ophthalmologist's signed examination confirms non-physiological diplopia within 18 degrees of central fixation, reproduced during the assessment even though the driver says the two overlapping road-sign images sometimes merge after blinking; an older note reported comfortable reading at a desk, but that earlier description neither contradicts the current reproduced double vision nor establishes that a patch or new lenses have resolved it.
- `vision.diplopia.within_20_degrees` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-VIS-COM-007](#aftd2022-vis-com-007)

### VIS-COM-SCREEN-001 — unknown

Required facts are unknown or unconfirmed.

- `vision.diplopia.present` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:902: The current ophthalmologist's signed examination confirms non-physiological diplopia within 18 degrees of central fixation, reproduced during the assessment even though the driver says the two overlapping road-sign images sometimes merge after blinking; an older note reported comfortable reading at a desk, but that earlier description neither contradicts the current reproduced double vision nor establishes that a patch or new lenses have resolved it.
- `vision.monocular` = UNKNOWN (unknown)
- `vision.uncorrected.better_eye` = UNKNOWN (unknown)
- `vision.uncorrected.left.snellen` = UNKNOWN (unknown)
- `vision.uncorrected.right.snellen` = UNKNOWN (unknown)
- `vision.visual_field.confirmed_defect` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-VIS-COM-002](#aftd2022-vis-com-002), [AFTD2022-VIS-COM-004](#aftd2022-vis-com-004), [AFTD2022-VIS-COM-007](#aftd2022-vis-com-007)

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

## Clinician checklist

- [ ] Clinician: review source facts, rule applicability and every provisional conclusion.
- [ ] Confirm the commercial driving task and assess conditions outside the five-module scope.
- [ ] Confirm missing/unverified case fact: vision.diplopia.present
- [ ] Confirm missing/unverified case fact: vision.monocular
- [ ] Confirm missing/unverified case fact: vision.uncorrected.better_eye
- [ ] Confirm missing/unverified case fact: vision.uncorrected.left.snellen
- [ ] Confirm missing/unverified case fact: vision.uncorrected.right.snellen
- [ ] Confirm missing/unverified case fact: vision.visual_field.confirmed_defect
- [ ] requires_confirmation
- [ ] Extraction semantic review: Possible extraction issues require confirmation
- [ ] This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
- [ ] Confirm vision.diplopia.physiological (unsupported): Independent source reading differs from the extraction. The question is about the exact meaning of the diplopia, not whether the patient is fit to drive. The source passages do not explicitly state whether the diplopia is physiological or non-physiological.
- [ ] Confirm vision.diplopia.present (omission): Independent source reading differs from the extraction. The patient explicitly has diplopia (double vision) as confirmed by the current ophthalmologist's signed examination, which reports non-physiological diplopia within 18 degrees of central fixation, reproduced during the assessment.
- [ ] Fields withheld from rule inputs: vision.diplopia.physiological, vision.diplopia.present

## Case source

```text
Synthetic nurse note for software testing. No real patient data.

The nurse reviews a commercial driver's symptoms alongside information from a witness, the treating team and an older workplace form, because each source describes a different part of the story; the occupational record retains those differences and identifies completed current findings without turning a booking, a family account or a recollection into a measured patient result.

The current ophthalmologist's signed examination confirms non-physiological diplopia within 18 degrees of central fixation, reproduced during the assessment even though the driver says the two overlapping road-sign images sometimes merge after blinking; an older note reported comfortable reading at a desk, but that earlier description neither contradicts the current reproduced double vision nor establishes that a patch or new lenses have resolved it.

The usual work involves coupling trailers, checking mirrors, interpreting radio messages and responding to pedestrians in a loading area, with breaks that can be delayed when deliveries run late; the driver explains which difficulty occurred while stationary and which was noticed during ordinary duties, rather than claiming that quiet conversation in the clinic reproduces every task in the cab.

The nurse keeps the relevant current attachment with the record and identifies the older account by its timing, so a later reviewer can distinguish what was observed, what the driver reported and what remains unresolved; no additional measurement, specialist conclusion or diagnosis is added merely because it would make the occupational decision easier to complete.

```

Input SHA-256: `26cc3d5b8d3855db66f5a8a33a4877ff3304db2c7f88091cb3b70359e0893734`
Rule-result SHA-256: `7e9595c57071e3e80a3ca03a912fa31ddf760f54cd1212f3a32ca51ec0d0bd02`
Evidence-pack SHA-256: `2087aba24a76c24e2c92cf457c06900b5656e0d8bca822432c10107f34b76bd2`
