# Clinical review draft — CX-LONG-123

CX-LONG-123: Insufficient information. 1 requested modules; 5 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

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

> The current doctor-reviewed series confirms persistent BP 182/106 mmHg while the driver is taking antihypertensive therapy, but the medication review also documents dizziness that impairs safe vehicle operation after the morning dose; although the driver feels better when sitting still in the interview, the nurse has no evidence that the side effect has resolved, and a proposed future dose change is not recorded as an accomplished treatment outcome.

- [AFTD2022-HTN-COM-002, PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)
- [AFTD2022-HTN-COM-001, PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: No issues flagged by the model
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### HTN-COM-UNCONDITIONAL-001 — triggered

Persistent blood pressure exceeds the commercial unconditional-licence threshold.

- `cardiovascular.blood_pressure.persistent_diastolic` = 106 (present)
  - Source lines 5–5; chars 492:518: persistent BP 182/106 mmHg
- `cardiovascular.blood_pressure.persistent_systolic` = 182 (present)
  - Source lines 5–5; chars 492:518: persistent BP 182/106 mmHg

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

The nurse reviews a commercial driver's symptoms alongside information from a witness, the treating team and an older workplace form, because each source describes a different part of the story; the occupational record retains those differences and identifies completed current findings without turning a booking, a family account or a recollection into a measured patient result.

The current doctor-reviewed series confirms persistent BP 182/106 mmHg while the driver is taking antihypertensive therapy, but the medication review also documents dizziness that impairs safe vehicle operation after the morning dose; although the driver feels better when sitting still in the interview, the nurse has no evidence that the side effect has resolved, and a proposed future dose change is not recorded as an accomplished treatment outcome.

The interview takes place before the driver's next planned roster, and the nurse records changes in symptoms, treatment and available documents without assuming that a future specialist appointment has already occurred; any letter that has been requested but not supplied remains separate from the findings actually available when this occupational record is written.

The record is prepared for the reviewing clinician with the sequence of events and the provenance of the available findings intact, because the employer summary and the driver's account answer different questions; a completed test is retained as such, but an unresolved detail is not filled in from a family member's history or from an earlier document with different testing conditions.

```

Input SHA-256: `f009820becd336e8a7a474ce9ac12edce9bf5ace9b3e01c513ed3822555388a0`
Rule-result SHA-256: `7c93055c87c18d37b50468293ad8c96357d421d265a04e66d1107a37de7ddc74`
Evidence-pack SHA-256: `67a352d5e974e2d535fe826ca4a0246902449c86273a8dd2d3123d2c1bda5851`
