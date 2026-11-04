# Clinical review draft — CX-LONG-076

CX-LONG-076: Insufficient information. 2 requested modules; 9 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| diabetes | Insufficient information | human_review | 7 |
| hypertension | Insufficient information | missing_information | 2 |

## Established rule findings

No rule criteria were established from the available verified facts. This does not establish absence of disease or failure of retrieval.


## Information coverage

- diabetes: Source-supported facts available; some facts require confirmation; 1 supported fields; 7 unresolved rule fields.
- hypertension: No source-supported facts for this requested module; some facts require confirmation; 0 supported fields; 2 unresolved rule fields.

## Retrieval activity

Rule-scoped ranking calls: 11.
Symptom discovery searches: 2.
Zero triggered rules does not mean retrieval failed. Retrieved text is not a diagnosis.

### diabetes symptom retrieval

> The driver with established diabetes reports sweating and difficulty concentrating after missing breakfast, but stayed responsive, treated himself with food and has no glucose measurement from the symptoms or evidence that assistance was required; a value of 5.8 mmol/L measured after eating is documented with its later timing, the current medicines cannot be reconciled from two inconsistent lists, and the nurse has not confirmed a severe hypoglycaemic event, impaired awareness or a specific treatment category.

- [AFTD2022-DM-COM-002, PDF 105](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=105)
- [AFTD2022-DM-COM-006, PDF 112](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=112)
- [AFTD2022-DM-COM-008, PDF 113](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=113)
- [AFTD2022-DM-COM-001, PDF 103](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=103)
- [AFTD2022-DM-COM-003, PDF 106](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=106)
### hypertension symptom retrieval

> An additional current doctor-reviewed measurement series confirms persistent BP 176/104 mmHg after repeat resting checks, although the driver recalls lower readings on an unverified home monitor; the initial specialist information and a sustained four-week treatment assessment are not available for this separate blood-pressure concern.

- [AFTD2022-HTN-COM-001, PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)
- [AFTD2022-HTN-COM-002, PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: Possible extraction issues require confirmation
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
Confirm diabetes.treatment_category (omission): Independent source reading differs from the extraction. The driver with established diabetes reports sweating and difficulty concentrating after missing breakfast, but stayed responsive, treated himself with food and has no glucose measurement from the symptoms or evidence that assistance was required; a value of 5.8 mmol/L measured after eating is documented with its later timing, the current medicines cannot be reconciled from two inconsistent lists, and the nurse has not confirmed a severe hypoglycaemic event, impaired awareness or a specific treatment category.
Fields withheld from rule inputs: diabetes.treatment_category

### diabetes.treatment_category — omission

Independent source reading differs from the extraction. The driver with established diabetes reports sweating and difficulty concentrating after missing breakfast, but stayed responsive, treated himself with food and has no glucose measurement from the symptoms or evidence that assistance was required; a value of 5.8 mmol/L measured after eating is documented with its later timing, the current medicines cannot be reconciled from two inconsistent lists, and the nurse has not confirmed a severe hypoglycaemic event, impaired awareness or a specific treatment category.

Source lines 5–5; characters 436:951
> The driver with established diabetes reports sweating and difficulty concentrating after missing breakfast, but stayed responsive, treated himself with food and has no glucose measurement from the symptoms or evidence that assistance was required; a value of 5.8 mmol/L measured after eating is documented with its later timing, the current medicines cannot be reconciled from two inconsistent lists, and the nurse has not confirmed a severe hypoglycaemic event, impaired awareness or a specific treatment category.

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### HTN-COM-UNCONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `cardiovascular.blood_pressure.persistent_diastolic` = UNKNOWN (requires_confirmation)
  - Source lines 9–9; chars 1330:1526: An additional current doctor-reviewed measurement series confirms persistent BP 176/104 mmHg after repeat resting checks, although the driver recalls lower readings on an unverified home monitor; 
- `cardiovascular.blood_pressure.persistent_systolic` = UNKNOWN (requires_confirmation)
  - Source lines 9–9; chars 1330:1526: An additional current doctor-reviewed measurement series confirms persistent BP 176/104 mmHg after repeat resting checks, although the driver recalls lower readings on an unverified home monitor; 

Guideline sources: [AFTD2022-HTN-COM-001](#aftd2022-htn-com-001)

### HTN-COM-CONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `cardiovascular.hypertension.antihypertensive_therapy` = UNKNOWN (unknown)
- `cardiovascular.hypertension.controlled_for_4_weeks` = UNKNOWN (unknown)
- `cardiovascular.hypertension.driving_impairing_medication_side_effects` = UNKNOWN (unknown)
- `cardiovascular.hypertension.initial_specialist_information_available` = UNKNOWN (unknown)
- `cardiovascular.hypertension.target_organ_damage_relevant_to_driving` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HTN-COM-002](#aftd2022-htn-com-002)

### DM-COM-DIET-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.driving_relevant_comorbidity_status` = UNKNOWN (unknown)
- `diabetes.present` = True (present)
  - Source lines 5–5; chars 436:684: The driver with established diabetes reports sweating and difficulty concentrating after missing breakfast, but stayed responsive, treated himself with food and has no glucose measurement from the symptoms or evidence that assistance was required; 
- `diabetes.treatment_category` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 436:951: The driver with established diabetes reports sweating and difficulty concentrating after missing breakfast, but stayed responsive, treated himself with food and has no glucose measurement from the symptoms or evidence that assistance was required; a value of 5.8 mmol/L measured after eating is documented with its later timing, the current medicines cannot be reconciled from two inconsistent lists, and the nurse has not confirmed a severe hypoglycaemic event, impaired awareness or a specific treatment category.

Guideline sources: [AFTD2022-DM-COM-004](#aftd2022-dm-com-004)

### DM-COM-NONINSULIN-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.present` = True (present)
  - Source lines 5–5; chars 436:684: The driver with established diabetes reports sweating and difficulty concentrating after missing breakfast, but stayed responsive, treated himself with food and has no glucose measurement from the symptoms or evidence that assistance was required; 
- `diabetes.treatment_category` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 436:951: The driver with established diabetes reports sweating and difficulty concentrating after missing breakfast, but stayed responsive, treated himself with food and has no glucose measurement from the symptoms or evidence that assistance was required; a value of 5.8 mmol/L measured after eating is documented with its later timing, the current medicines cannot be reconciled from two inconsistent lists, and the nurse has not confirmed a severe hypoglycaemic event, impaired awareness or a specific treatment category.

Guideline sources: [AFTD2022-DM-COM-005](#aftd2022-dm-com-005)

### DM-COM-NONINSULIN-CONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.driving_relevant_end_organ_effects` = UNKNOWN (unknown)
- `diabetes.hypoglycaemia_awareness` = UNKNOWN (unknown)
- `diabetes.initial_specialist_information_available` = UNKNOWN (unknown)
- `diabetes.present` = True (present)
  - Source lines 5–5; chars 436:684: The driver with established diabetes reports sweating and difficulty concentrating after missing breakfast, but stayed responsive, treated himself with food and has no glucose measurement from the symptoms or evidence that assistance was required; 
- `diabetes.recent_severe_hypoglycaemic_event` = UNKNOWN (unknown)
- `diabetes.regimen_minimises_hypoglycaemia` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-006](#aftd2022-dm-com-006)

### DM-COM-INSULIN-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.gestational` = UNKNOWN (unknown)
- `diabetes.present` = True (present)
  - Source lines 5–5; chars 436:684: The driver with established diabetes reports sweating and difficulty concentrating after missing breakfast, but stayed responsive, treated himself with food and has no glucose measurement from the symptoms or evidence that assistance was required; 
- `diabetes.treatment_category` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 436:951: The driver with established diabetes reports sweating and difficulty concentrating after missing breakfast, but stayed responsive, treated himself with food and has no glucose measurement from the symptoms or evidence that assistance was required; a value of 5.8 mmol/L measured after eating is documented with its later timing, the current medicines cannot be reconciled from two inconsistent lists, and the nurse has not confirmed a severe hypoglycaemic event, impaired awareness or a specific treatment category.

Guideline sources: [AFTD2022-DM-COM-007](#aftd2022-dm-com-007)

### DM-COM-SEVERE-HYPO-WAIT-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.present` = True (present)
  - Source lines 5–5; chars 436:684: The driver with established diabetes reports sweating and difficulty concentrating after missing breakfast, but stayed responsive, treated himself with food and has no glucose measurement from the symptoms or evidence that assistance was required; 
- `diabetes.severe_hypoglycaemic_event.occurred` = UNKNOWN (unknown)
- `diabetes.severe_hypoglycaemic_event.weeks_since_last` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-002](#aftd2022-dm-com-002)

### DM-COM-INSULIN-CONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.driving_relevant_end_organ_effects` = UNKNOWN (unknown)
- `diabetes.glucose_monitoring_records_months` = UNKNOWN (unknown)
- `diabetes.hypoglycaemia_awareness` = UNKNOWN (unknown)
- `diabetes.present` = True (present)
  - Source lines 5–5; chars 436:684: The driver with established diabetes reports sweating and difficulty concentrating after missing breakfast, but stayed responsive, treated himself with food and has no glucose measurement from the symptoms or evidence that assistance was required; 
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
- `diabetes.present` = True (present)
  - Source lines 5–5; chars 436:684: The driver with established diabetes reports sweating and difficulty concentrating after missing breakfast, but stayed responsive, treated himself with food and has no glucose measurement from the symptoms or evidence that assistance was required; 

Guideline sources: [AFTD2022-DM-COM-003](#aftd2022-dm-com-003)

### HTN-COM-SCREEN-001 — unknown

Required facts are unknown or unconfirmed.

- `cardiovascular.blood_pressure.persistent_diastolic` = UNKNOWN (requires_confirmation)
  - Source lines 9–9; chars 1330:1526: An additional current doctor-reviewed measurement series confirms persistent BP 176/104 mmHg after repeat resting checks, although the driver recalls lower readings on an unverified home monitor; 
- `cardiovascular.blood_pressure.persistent_systolic` = UNKNOWN (requires_confirmation)
  - Source lines 9–9; chars 1330:1526: An additional current doctor-reviewed measurement series confirms persistent BP 176/104 mmHg after repeat resting checks, although the driver recalls lower readings on an unverified home monitor; 

Guideline sources: [AFTD2022-HTN-COM-001](#aftd2022-htn-com-001)

### DM-COM-GESTATIONAL-REVIEW-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.gestational` = UNKNOWN (unknown)
- `diabetes.present` = True (present)
  - Source lines 5–5; chars 436:684: The driver with established diabetes reports sweating and difficulty concentrating after missing breakfast, but stayed responsive, treated himself with food and has no glucose measurement from the symptoms or evidence that assistance was required; 

Guideline sources: [AFTD2022-DM-COM-010](#aftd2022-dm-com-010)

## Guideline evidence

### AFTD2022-HTN-COM-001

[§2.3.1 · printed 88 / PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)

Table/context: Hypertension: unconditional

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has blood pressure 
> consistently > 170 systolic or > 100 diastolic 
> (treated or untreated).

PDF region: (345.0, 177.0, 530.0, 247.0); text SHA-256: `eeacf5b9430b10bb961f6b727f6b4eb638baaf8aeecde7413ad4b4dea2baef7d`.

### AFTD2022-HTN-COM-002

[§2.3.1 · printed 88 / PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)

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
- [ ] Confirm missing/unverified case fact: cardiovascular.blood_pressure.persistent_diastolic
- [ ] Confirm missing/unverified case fact: cardiovascular.blood_pressure.persistent_systolic
- [ ] Confirm missing/unverified case fact: diabetes.acutely_unwell
- [ ] Confirm missing/unverified case fact: diabetes.driving_relevant_comorbidity_status
- [ ] Confirm missing/unverified case fact: diabetes.gestational
- [ ] Confirm missing/unverified case fact: diabetes.metabolically_unstable
- [ ] Confirm missing/unverified case fact: diabetes.severe_hypoglycaemic_event.occurred
- [ ] Confirm missing/unverified case fact: diabetes.severe_hypoglycaemic_event.weeks_since_last
- [ ] Confirm missing/unverified case fact: diabetes.treatment_category
- [ ] cardiovascular.blood_pressure.observed_diastolic
- [ ] cardiovascular.blood_pressure.observed_systolic
- [ ] requires_confirmation
- [ ] cardiovascular.blood_pressure.observed_diastolic
- [ ] cardiovascular.blood_pressure.observed_systolic
- [ ] cardiovascular.blood_pressure.persistent_diastolic
- [ ] cardiovascular.blood_pressure.persistent_systolic
- [ ] Extraction semantic review: Possible extraction issues require confirmation
- [ ] This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
- [ ] Confirm diabetes.treatment_category (omission): Independent source reading differs from the extraction. The driver with established diabetes reports sweating and difficulty concentrating after missing breakfast, but stayed responsive, treated himself with food and has no glucose measurement from the symptoms or evidence that assistance was required; a value of 5.8 mmol/L measured after eating is documented with its later timing, the current medicines cannot be reconciled from two inconsistent lists, and the nurse has not confirmed a severe hypoglycaemic event, impaired awareness or a specific treatment category.
- [ ] Fields withheld from rule inputs: diabetes.treatment_category

## Case source

```text
Synthetic nurse note for software testing. No real patient data.

During a commercial-driver review after a refrigerated-freight run, the nurse brings together the driver's account, a dated clinical attachment and an employer form copied from an earlier assessment; the documents refer to different times, and the current entry distinguishes a completed examination from recollections, plans and information concerning another person.

The driver with established diabetes reports sweating and difficulty concentrating after missing breakfast, but stayed responsive, treated himself with food and has no glucose measurement from the symptoms or evidence that assistance was required; a value of 5.8 mmol/L measured after eating is documented with its later timing, the current medicines cannot be reconciled from two inconsistent lists, and the nurse has not confirmed a severe hypoglycaemic event, impaired awareness or a specific treatment category.

The employer's copied form relates to an earlier period of work and contains a broad satisfactory box without the measurements underlying it, whereas the current nurse entry identifies the source of each specific finding; the driver's wish to continue scheduled duties is recorded as a preference, not as proof that the present assessment has resolved the documented concern.

An additional current doctor-reviewed measurement series confirms persistent BP 176/104 mmHg after repeat resting checks, although the driver recalls lower readings on an unverified home monitor; the initial specialist information and a sustained four-week treatment assessment are not available for this separate blood-pressure concern.

Before closing the interview, the nurse checks that the driver's recollection and the supplied clinical document have not been merged into a single undated finding, and records the outstanding documents separately; the completed entries remain current findings, while any missing qualification, conflicting detail or unperformed examination stays available for review rather than being silently treated as normal.

```

Input SHA-256: `2eff60267e5ee7e1e2518a2482ee7d87ec3e514eff72aaa743ac538d7da0cfb1`
Rule-result SHA-256: `c41fe28e75f0e9480d8b277a542c555536dd73f39bf0030251cf067914ffe614`
Evidence-pack SHA-256: `df2fe5fa4f635c09a86937c2c1169d11200b7408126e170e4bc3a58465e8e509`
