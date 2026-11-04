# Clinical review draft — CX-LONG-055

CX-LONG-055: Insufficient information. 1 requested modules; 5 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| hypertension | Insufficient information | human_review | 5 |

## Established rule findings

1 rules triggered from source-supported facts. The overall assessment is incomplete; this does not erase the findings below. Missing facts in any requested module can prevent an overall clearance.

- hypertension: `HTN-COM-UNCONDITIONAL-001` - Persistent blood pressure exceeds the commercial unconditional-licence threshold.

## Information coverage

- hypertension: Source-supported facts available; some facts require confirmation; 3 supported fields; 5 unresolved rule fields.

## Retrieval activity

Rule-scoped ranking calls: 2.
Symptom discovery searches: 1.
Zero triggered rules does not mean retrieval failed. Retrieved text is not a diagnosis.

### hypertension symptom retrieval

> The current doctor-reviewed series confirms persistent BP 174/104 mmHg while the driver is taking antihypertensive therapy, but the medication review also documents dizziness that impairs safe vehicle operation after the morning dose; although the driver feels better when sitting still in the interview, the nurse has no evidence that the side effect has resolved, and a proposed future dose change is not recorded as an accomplished treatment outcome.

- [AFTD2022-HTN-COM-002, PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)
- [AFTD2022-HTN-COM-001, PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: Possible extraction issues require confirmation
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
Confirm cardiovascular.blood_pressure.persistent_diastolic (contradiction): Independent source reading differs from the extraction. 174/104 mmHg
Fields withheld from rule inputs: cardiovascular.blood_pressure.persistent_diastolic

### cardiovascular.blood_pressure.persistent_diastolic — contradiction

Independent source reading differs from the extraction. 174/104 mmHg

Source lines 5–5; characters 460:913
> The current doctor-reviewed series confirms persistent BP 174/104 mmHg while the driver is taking antihypertensive therapy, but the medication review also documents dizziness that impairs safe vehicle operation after the morning dose; although the driver feels better when sitting still in the interview, the nurse has no evidence that the side effect has resolved, and a proposed future dose change is not recorded as an accomplished treatment outcome.

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### HTN-COM-UNCONDITIONAL-001 — triggered

Persistent blood pressure exceeds the commercial unconditional-licence threshold.

- `cardiovascular.blood_pressure.persistent_diastolic` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 504:530: persistent BP 174/104 mmHg
  - Source lines 5–5; chars 504:530: persistent BP 174/104 mmHg
  - Source lines 5–5; chars 460:913: The current doctor-reviewed series confirms persistent BP 174/104 mmHg while the driver is taking antihypertensive therapy, but the medication review also documents dizziness that impairs safe vehicle operation after the morning dose; although the driver feels better when sitting still in the interview, the nurse has no evidence that the side effect has resolved, and a proposed future dose change is not recorded as an accomplished treatment outcome.
- `cardiovascular.blood_pressure.persistent_systolic` = 174.0 (present)
  - Source lines 5–5; chars 504:530: persistent BP 174/104 mmHg
  - Source lines 5–5; chars 504:530: persistent BP 174/104 mmHg

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
- [ ] requires_confirmation
- [ ] Extraction semantic review: Possible extraction issues require confirmation
- [ ] This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
- [ ] Confirm cardiovascular.blood_pressure.persistent_diastolic (contradiction): Independent source reading differs from the extraction. 174/104 mmHg
- [ ] Fields withheld from rule inputs: cardiovascular.blood_pressure.persistent_diastolic

## Case source

```text
Synthetic nurse note for software testing. No real patient data.

The commercial driver attends after a long shift with a folder containing a current signed letter, older screening paperwork and a handwritten personal account, and the nurse reconstructs the chronology before recording the present findings; differences between the records are described explicitly rather than resolved by treating the newest-looking photocopy as automatically authoritative.

The current doctor-reviewed series confirms persistent BP 174/104 mmHg while the driver is taking antihypertensive therapy, but the medication review also documents dizziness that impairs safe vehicle operation after the morning dose; although the driver feels better when sitting still in the interview, the nurse has no evidence that the side effect has resolved, and a proposed future dose change is not recorded as an accomplished treatment outcome.

The driver alternates urban deliveries with a longer motorway leg and describes a busy depot where engine noise, glare and interrupted meals can complicate an account of symptoms; the nurse records the work setting as context, while keeping the dated clinical findings distinct from the driver's explanation for why a symptom might have occurred on that shift.

The nurse reads the summary back to the driver to check the chronology and separates agreement about the wording from verification of a medical finding, then attaches the identified clinical material; any decision about further investigation or work allocation remains for the reviewing professional, and the note itself does not certify that all relevant clinical questions have been answered.

```

Input SHA-256: `6727c14f1142e93bedbd3f78e5075b025033d5e96079d0b1087290ce5cc3a234`
Rule-result SHA-256: `96341e980b687ba924e556ca5de3bf4cb7b09c7f242e2866698b5e2b83c9c111`
Evidence-pack SHA-256: `0bdd5d72b259b3e0f1e93a94bd04b7e5975b513c43cee917d5c3749e20dc2ceb`
