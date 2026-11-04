# Clinical review draft — CX-LONG-041

CX-LONG-041: Insufficient information. 1 requested modules; 2 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| hypertension | Insufficient information | human_review | 2 |

## Established rule findings

No rule criteria were established from the available verified facts. This does not establish absence of disease or failure of retrieval.


## Information coverage

- hypertension: No source-supported facts for this requested module; some facts require confirmation; 0 supported fields; 2 unresolved rule fields.

## Retrieval activity

Rule-scoped ranking calls: 3.
Symptom discovery searches: 1.
Zero triggered rules does not mean retrieval failed. Retrieved text is not a diagnosis.

### hypertension symptom retrieval

> The nurse separates last year's untreated readings of 188/108 mmHg from the current dated clinic record, which confirms persistent BP 134/82 mmHg on repeated measurements during the present review; the driver reports no current chest pain or breathlessness, and a family member's stroke is recorded as family history rather than a cardiovascular event experienced by the driver.

- [AFTD2022-HTN-COM-001, PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)
- [AFTD2022-HTN-COM-002, PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: Possible extraction issues require confirmation
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
Confirm cardiovascular.chest_pain (unsupported): Independent source reading differs from the extraction. The patient fact 'cardiovascular.chest_pain' is not mentioned in the provided source passages.
Fields withheld from rule inputs: cardiovascular.chest_pain

### cardiovascular.chest_pain — unsupported

Independent source reading differs from the extraction. The patient fact 'cardiovascular.chest_pain' is not mentioned in the provided source passages.

Source lines 5–5; characters 657:686
> reports no current chest pain

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### HTN-COM-UNCONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `cardiovascular.blood_pressure.persistent_diastolic` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:646: The nurse separates last year's untreated readings of 188/108 mmHg from the current dated clinic record, which confirms persistent BP 134/82 mmHg on repeated measurements during the present review; 
- `cardiovascular.blood_pressure.persistent_systolic` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:646: The nurse separates last year's untreated readings of 188/108 mmHg from the current dated clinic record, which confirms persistent BP 134/82 mmHg on repeated measurements during the present review; 

Guideline sources: [AFTD2022-HTN-COM-001](#aftd2022-htn-com-001)

### HTN-COM-CONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `cardiovascular.hypertension.antihypertensive_therapy` = UNKNOWN (unknown)
- `cardiovascular.hypertension.controlled_for_4_weeks` = UNKNOWN (unknown)
- `cardiovascular.hypertension.driving_impairing_medication_side_effects` = UNKNOWN (unknown)
- `cardiovascular.hypertension.initial_specialist_information_available` = UNKNOWN (unknown)
- `cardiovascular.hypertension.target_organ_damage_relevant_to_driving` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HTN-COM-002](#aftd2022-htn-com-002)

### HTN-COM-SCREEN-001 — unknown

Required facts are unknown or unconfirmed.

- `cardiovascular.blood_pressure.persistent_diastolic` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:646: The nurse separates last year's untreated readings of 188/108 mmHg from the current dated clinic record, which confirms persistent BP 134/82 mmHg on repeated measurements during the present review; 
- `cardiovascular.blood_pressure.persistent_systolic` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:646: The nurse separates last year's untreated readings of 188/108 mmHg from the current dated clinic record, which confirms persistent BP 134/82 mmHg on repeated measurements during the present review; 

Guideline sources: [AFTD2022-HTN-COM-001](#aftd2022-htn-com-001)

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
- [ ] Confirm missing/unverified case fact: cardiovascular.blood_pressure.persistent_diastolic
- [ ] Confirm missing/unverified case fact: cardiovascular.blood_pressure.persistent_systolic
- [ ] cardiovascular.blood_pressure.observed_diastolic
- [ ] cardiovascular.blood_pressure.observed_systolic
- [ ] requires_confirmation
- [ ] cardiovascular.blood_pressure.observed_diastolic
- [ ] cardiovascular.blood_pressure.observed_systolic
- [ ] cardiovascular.blood_pressure.persistent_diastolic
- [ ] cardiovascular.blood_pressure.persistent_systolic
- [ ] Extraction semantic review: Possible extraction issues require confirmation
- [ ] This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
- [ ] Confirm cardiovascular.chest_pain (unsupported): Independent source reading differs from the extraction. The patient fact 'cardiovascular.chest_pain' is not mentioned in the provided source passages.
- [ ] Fields withheld from rule inputs: cardiovascular.chest_pain

## Case source

```text
Synthetic nurse note for software testing. No real patient data.

The nurse reviews a commercial driver's symptoms alongside information from a witness, the treating team and an older workplace form, because each source describes a different part of the story; the occupational record retains those differences and identifies completed current findings without turning a booking, a family account or a recollection into a measured patient result.

The nurse separates last year's untreated readings of 188/108 mmHg from the current dated clinic record, which confirms persistent BP 134/82 mmHg on repeated measurements during the present review; the driver reports no current chest pain or breathlessness, and a family member's stroke is recorded as family history rather than a cardiovascular event experienced by the driver.

The usual work involves coupling trailers, checking mirrors, interpreting radio messages and responding to pedestrians in a loading area, with breaks that can be delayed when deliveries run late; the driver explains which difficulty occurred while stationary and which was noticed during ordinary duties, rather than claiming that quiet conversation in the clinic reproduces every task in the cab.

The record is prepared for the reviewing clinician with the sequence of events and the provenance of the available findings intact, because the employer summary and the driver's account answer different questions; a completed test is retained as such, but an unresolved detail is not filled in from a family member's history or from an earlier document with different testing conditions.

```

Input SHA-256: `1f95f466f449e617e4bc5f90a88bdc1f4984486807997df5eaff0de90d7b67fd`
Rule-result SHA-256: `281d314150d809b239563515b003cee4b1a1492b358388bfa41377398b626ea3`
Evidence-pack SHA-256: `5952be6374cac818e8f5a84fb43c0e5809822fc98ff1a4fa1b7fa08d3eba2126`
