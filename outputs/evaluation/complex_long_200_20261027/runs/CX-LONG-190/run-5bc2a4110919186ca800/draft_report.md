# Clinical review draft — CX-LONG-190

CX-LONG-190: Insufficient information. 1 requested modules; 5 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| hypertension | Insufficient information | missing_information | 5 |

## Established rule findings

1 rules triggered from source-supported facts. The overall assessment is incomplete; this does not erase the findings below. Missing facts in any requested module can prevent an overall clearance.

- hypertension: `HTN-COM-UNCONDITIONAL-001` - Persistent blood pressure exceeds the commercial unconditional-licence threshold.

## Information coverage

- hypertension: Source-supported facts available; 4 supported fields; 5 unresolved rule fields.

## Retrieval activity

Rule-scoped ranking calls: 2.
Symptom discovery searches: 1.
Zero triggered rules does not mean retrieval failed. Retrieved text is not a diagnosis.

### hypertension symptom retrieval

> Although the driver repeatedly points to a systolic figure of 158 as reassurance, the dated treating-doctor record confirms persistent BP 158/104 mmHg after repeat resting checks, and the nurse separately records the lower and upper pressures; the driver cannot provide the specialist information or demonstrate a four-week period of effective treatment, and his account of an old normal check does not replace today's documented diastolic pattern.

- [AFTD2022-HTN-COM-001, PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)
- [AFTD2022-HTN-COM-002, PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: No issues flagged by the model
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### HTN-COM-UNCONDITIONAL-001 — triggered

Persistent blood pressure exceeds the commercial unconditional-licence threshold.

- `cardiovascular.blood_pressure.persistent_diastolic` = 104.0 (present)
  - Source lines 5–5; chars 584:610: persistent BP 158/104 mmHg
  - Source lines 5–5; chars 584:610: persistent BP 158/104 mmHg
- `cardiovascular.blood_pressure.persistent_systolic` = 158.0 (present)
  - Source lines 5–5; chars 584:610: persistent BP 158/104 mmHg
  - Source lines 5–5; chars 584:610: persistent BP 158/104 mmHg

Guideline sources: [AFTD2022-HTN-COM-001](#aftd2022-htn-com-001)

### HTN-COM-CONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `cardiovascular.hypertension.antihypertensive_therapy` = UNKNOWN (unknown)
- `cardiovascular.hypertension.controlled_for_4_weeks` = UNKNOWN (unknown)
- `cardiovascular.hypertension.driving_impairing_medication_side_effects` = UNKNOWN (unknown)
- `cardiovascular.hypertension.initial_specialist_information_available` = UNKNOWN (unknown)
- `cardiovascular.hypertension.target_organ_damage_relevant_to_driving` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HTN-COM-002](#aftd2022-htn-com-002)

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

## Clinician checklist

- [ ] Clinician: review source facts, rule applicability and every provisional conclusion.
- [ ] Confirm the commercial driving task and assess conditions outside the five-module scope.
- [ ] Confirm missing/unverified case fact: cardiovascular.hypertension.antihypertensive_therapy
- [ ] Confirm missing/unverified case fact: cardiovascular.hypertension.controlled_for_4_weeks
- [ ] Confirm missing/unverified case fact: cardiovascular.hypertension.driving_impairing_medication_side_effects
- [ ] Confirm missing/unverified case fact: cardiovascular.hypertension.initial_specialist_information_available
- [ ] Confirm missing/unverified case fact: cardiovascular.hypertension.target_organ_damage_relevant_to_driving

## Case source

```text
Synthetic nurse note for software testing. No real patient data.

The commercial driver attends after a long shift with a folder containing a current signed letter, older screening paperwork and a handwritten personal account, and the nurse reconstructs the chronology before recording the present findings; differences between the records are described explicitly rather than resolved by treating the newest-looking photocopy as automatically authoritative.

Although the driver repeatedly points to a systolic figure of 158 as reassurance, the dated treating-doctor record confirms persistent BP 158/104 mmHg after repeat resting checks, and the nurse separately records the lower and upper pressures; the driver cannot provide the specialist information or demonstrate a four-week period of effective treatment, and his account of an old normal check does not replace today's documented diastolic pattern.

The driver alternates urban deliveries with a longer motorway leg and describes a busy depot where engine noise, glare and interrupted meals can complicate an account of symptoms; the nurse records the work setting as context, while keeping the dated clinical findings distinct from the driver's explanation for why a symptom might have occurred on that shift.

The nurse reads the summary back to the driver to check the chronology and separates agreement about the wording from verification of a medical finding, then attaches the identified clinical material; any decision about further investigation or work allocation remains for the reviewing professional, and the note itself does not certify that all relevant clinical questions have been answered.

```

Input SHA-256: `74267aec36a47c389f12c5759dc4f9110dfc20eedf0d1a18506d89a06f9fc456`
Rule-result SHA-256: `9cfad02ae9bf118ad34ab6020030ebf847175fb661e28b66b5795b1c1b3b11e9`
Evidence-pack SHA-256: `7b5b43331169f368e6895f245904bb6e6ce3e0d42a551328dafb236b6adb5363`
