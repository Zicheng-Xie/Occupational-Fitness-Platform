# Clinical review draft — CX-LONG-045

CX-LONG-045: Insufficient information. 2 requested modules; 8 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| diabetes | Insufficient information | missing_information | 6 |
| hypertension | Insufficient information | missing_information | 2 |

## Established rule findings

No rule criteria were established from the available verified facts. This does not establish absence of disease or failure of retrieval.


## Information coverage

- diabetes: Source-supported facts available; 2 supported fields; 6 unresolved rule fields.
- hypertension: No source-supported facts for this requested module; some facts require confirmation; 0 supported fields; 2 unresolved rule fields.

## Retrieval activity

Rule-scoped ranking calls: 7.
Symptom discovery searches: 2.
Zero triggered rules does not mean retrieval failed. Retrieved text is not a diagnosis.

### diabetes symptom retrieval

> The current GP and medication review confirm established type 2 diabetes managed by diet and exercise alone, with no glucose-lowering medicine or insulin prescribed, and document that driving-relevant comorbidities have been assessed with no disqualifying effect; the driver mentions that an uncle uses injections, but those medicines belong to the uncle, and a previous referral proposing tablets was never implemented as a current treatment change.

- [AFTD2022-DM-COM-006, PDF 112](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=112)
- [AFTD2022-DM-COM-004, PDF 112](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=112)
- [AFTD2022-DM-COM-008, PDF 113](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=113)
- [AFTD2022-DM-COM-005, PDF 112](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=112)
- [AFTD2022-DM-COM-009, PDF 110](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=110)
### hypertension symptom retrieval

> An additional current doctor-reviewed measurement series confirms persistent BP 176/104 mmHg after repeat resting checks, although the driver recalls lower readings on an unverified home monitor; the initial specialist information and a sustained four-week treatment assessment are not available for this separate blood-pressure concern.

- [AFTD2022-HTN-COM-001, PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)
- [AFTD2022-HTN-COM-002, PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: No issues flagged by the model
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### HTN-COM-UNCONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `cardiovascular.blood_pressure.persistent_diastolic` = UNKNOWN (conflicting)
  - Source lines 9–9; chars 1277:1473: An additional current doctor-reviewed measurement series confirms persistent BP 176/104 mmHg after repeat resting checks, although the driver recalls lower readings on an unverified home monitor; 
  - Source lines 9–9; chars 1343:1369: persistent BP 176/104 mmHg
- `cardiovascular.blood_pressure.persistent_systolic` = UNKNOWN (conflicting)
  - Source lines 9–9; chars 1277:1473: An additional current doctor-reviewed measurement series confirms persistent BP 176/104 mmHg after repeat resting checks, although the driver recalls lower readings on an unverified home monitor; 
  - Source lines 9–9; chars 1343:1369: persistent BP 176/104 mmHg

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
  - Source lines 5–5; chars 448:712: The current GP and medication review confirm established type 2 diabetes managed by diet and exercise alone, with no glucose-lowering medicine or insulin prescribed, and document that driving-relevant comorbidities have been assessed with no disqualifying effect; 
  - Source lines 5–5; chars 493:520: established type 2 diabetes
- `diabetes.treatment_category` = diet_and_exercise_only (present)
  - Source lines 5–5; chars 512:555: diabetes managed by diet and exercise alone

Guideline sources: [AFTD2022-DM-COM-004](#aftd2022-dm-com-004)

### DM-COM-SEVERE-HYPO-WAIT-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.present` = True (present)
  - Source lines 5–5; chars 448:712: The current GP and medication review confirm established type 2 diabetes managed by diet and exercise alone, with no glucose-lowering medicine or insulin prescribed, and document that driving-relevant comorbidities have been assessed with no disqualifying effect; 
  - Source lines 5–5; chars 493:520: established type 2 diabetes
- `diabetes.severe_hypoglycaemic_event.occurred` = UNKNOWN (unknown)
- `diabetes.severe_hypoglycaemic_event.weeks_since_last` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-002](#aftd2022-dm-com-002)

### DM-COM-ACUTE-UNSTABLE-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.acutely_unwell` = UNKNOWN (unknown)
- `diabetes.metabolically_unstable` = UNKNOWN (unknown)
- `diabetes.present` = True (present)
  - Source lines 5–5; chars 448:712: The current GP and medication review confirm established type 2 diabetes managed by diet and exercise alone, with no glucose-lowering medicine or insulin prescribed, and document that driving-relevant comorbidities have been assessed with no disqualifying effect; 
  - Source lines 5–5; chars 493:520: established type 2 diabetes

Guideline sources: [AFTD2022-DM-COM-003](#aftd2022-dm-com-003)

### HTN-COM-SCREEN-001 — unknown

Required facts are unknown or unconfirmed.

- `cardiovascular.blood_pressure.persistent_diastolic` = UNKNOWN (conflicting)
  - Source lines 9–9; chars 1277:1473: An additional current doctor-reviewed measurement series confirms persistent BP 176/104 mmHg after repeat resting checks, although the driver recalls lower readings on an unverified home monitor; 
  - Source lines 9–9; chars 1343:1369: persistent BP 176/104 mmHg
- `cardiovascular.blood_pressure.persistent_systolic` = UNKNOWN (conflicting)
  - Source lines 9–9; chars 1277:1473: An additional current doctor-reviewed measurement series confirms persistent BP 176/104 mmHg after repeat resting checks, although the driver recalls lower readings on an unverified home monitor; 
  - Source lines 9–9; chars 1343:1369: persistent BP 176/104 mmHg

Guideline sources: [AFTD2022-HTN-COM-001](#aftd2022-htn-com-001)

### DM-COM-GESTATIONAL-REVIEW-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.gestational` = UNKNOWN (unknown)
- `diabetes.present` = True (present)
  - Source lines 5–5; chars 448:712: The current GP and medication review confirm established type 2 diabetes managed by diet and exercise alone, with no glucose-lowering medicine or insulin prescribed, and document that driving-relevant comorbidities have been assessed with no disqualifying effect; 
  - Source lines 5–5; chars 493:520: established type 2 diabetes

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
- [ ] cardiovascular.blood_pressure.persistent_diastolic
- [ ] cardiovascular.blood_pressure.persistent_systolic
- [ ] cardiovascular.blood_pressure.observed_diastolic
- [ ] cardiovascular.blood_pressure.observed_systolic
- [ ] cardiovascular.blood_pressure.persistent_diastolic
- [ ] cardiovascular.blood_pressure.persistent_systolic

## Case source

```text
Synthetic nurse note for software testing. No real patient data.

The nurse reviews a commercial driver's symptoms alongside information from a witness, the treating team and an older workplace form, because each source describes a different part of the story; the occupational record retains those differences and identifies completed current findings without turning a booking, a family account or a recollection into a measured patient result.

The current GP and medication review confirm established type 2 diabetes managed by diet and exercise alone, with no glucose-lowering medicine or insulin prescribed, and document that driving-relevant comorbidities have been assessed with no disqualifying effect; the driver mentions that an uncle uses injections, but those medicines belong to the uncle, and a previous referral proposing tablets was never implemented as a current treatment change.

Part of the usual route requires reversing near workers and reading changing signs before entering a customer site, although today's assessment takes place in a quiet room; the driver is asked to describe the sequence and timing of difficulties, and the note preserves the difference between an occupational concern, a suspected mechanism and a completed clinical assessment.

An additional current doctor-reviewed measurement series confirms persistent BP 176/104 mmHg after repeat resting checks, although the driver recalls lower readings on an unverified home monitor; the initial specialist information and a sustained four-week treatment assessment are not available for this separate blood-pressure concern.

Before closing the interview, the nurse checks that the driver's recollection and the supplied clinical document have not been merged into a single undated finding, and records the outstanding documents separately; the completed entries remain current findings, while any missing qualification, conflicting detail or unperformed examination stays available for review rather than being silently treated as normal.

```

Input SHA-256: `21d6f66deabf1e5c75c93745bfe8555c7b6e9bdd59a0cd9f7f156a57205ac21c`
Rule-result SHA-256: `7c7f46079e0fee6a5e2442e9c9debcd0c2769ec41616f3e8bf0d1f10a191c9e8`
Evidence-pack SHA-256: `6d9b0f7389f5917b04580f782170b6c3a75c80df3eb78d5798a952bd95e2a255`
