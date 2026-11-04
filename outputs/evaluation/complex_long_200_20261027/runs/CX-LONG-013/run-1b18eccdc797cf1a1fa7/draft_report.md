# Clinical review draft — CX-LONG-013

CX-LONG-013: Insufficient information. 1 requested modules; 2 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| hypertension | Insufficient information | human_review | 2 |

## Established rule findings

No rule criteria were established from the available verified facts. This does not establish absence of disease or failure of retrieval.


## Information coverage

- hypertension: Source-supported facts available; some facts require confirmation; 1 supported fields; 2 unresolved rule fields.

## Retrieval activity

Rule-scoped ranking calls: 3.
Symptom discovery searches: 1.
Zero triggered rules does not mean retrieval failed. Retrieved text is not a diagnosis.

### hypertension symptom retrieval

> The driver restarted antihypertensive tablets twelve days ago after a period of missed doses, and the current clinic letter still records persistent BP 174/104 mmHg on repeat checks; a four-week follow-up period has not yet been completed, the driver brings a booking confirmation rather than a specialist opinion, and occasional improvement on a home display cannot establish sustained control or the absence of relevant treatment problems.

- [AFTD2022-HTN-COM-002, PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)
- [AFTD2022-HTN-COM-001, PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: Possible extraction issues require confirmation
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
Confirm cardiovascular.blood_pressure.observed_diastolic (unsupported): Independent source reading differs from the extraction. The patient fact 'cardiovascular.blood_pressure.observed_diastolic' is not documented in the provided source passages.
Confirm cardiovascular.blood_pressure.persistent_diastolic (unsupported): Independent source reading differs from the extraction. The patient fact 'cardiovascular.blood_pressure.persistent_diastolic' is not documented in the provided source passages.
Confirm cardiovascular.blood_pressure.persistent_systolic (unsupported): Independent source reading differs from the extraction. The patient fact 'cardiovascular.blood_pressure.persistent_systolic' is not documented in the provided source passages.
Fields withheld from rule inputs: cardiovascular.blood_pressure.observed_diastolic, cardiovascular.blood_pressure.persistent_diastolic, cardiovascular.blood_pressure.persistent_systolic

### cardiovascular.blood_pressure.observed_diastolic — unsupported

Independent source reading differs from the extraction. The patient fact 'cardiovascular.blood_pressure.observed_diastolic' is not documented in the provided source passages.

Source lines 5–5; characters 585:600
> BP 174/104 mmHg

### cardiovascular.blood_pressure.persistent_diastolic — unsupported

Independent source reading differs from the extraction. The patient fact 'cardiovascular.blood_pressure.persistent_diastolic' is not documented in the provided source passages.

Source lines 5–5; characters 574:600
> persistent BP 174/104 mmHg

### cardiovascular.blood_pressure.persistent_systolic — unsupported

Independent source reading differs from the extraction. The patient fact 'cardiovascular.blood_pressure.persistent_systolic' is not documented in the provided source passages.

Source lines 5–5; characters 574:600
> persistent BP 174/104 mmHg

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### HTN-COM-UNCONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `cardiovascular.blood_pressure.persistent_diastolic` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 574:600: persistent BP 174/104 mmHg
  - Source lines 5–5; chars 574:600: persistent BP 174/104 mmHg
- `cardiovascular.blood_pressure.persistent_systolic` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 574:600: persistent BP 174/104 mmHg
  - Source lines 5–5; chars 574:600: persistent BP 174/104 mmHg

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
  - Source lines 5–5; chars 574:600: persistent BP 174/104 mmHg
  - Source lines 5–5; chars 574:600: persistent BP 174/104 mmHg
- `cardiovascular.blood_pressure.persistent_systolic` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 574:600: persistent BP 174/104 mmHg
  - Source lines 5–5; chars 574:600: persistent BP 174/104 mmHg

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
- [ ] requires_confirmation
- [ ] Extraction semantic review: Possible extraction issues require confirmation
- [ ] This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
- [ ] Confirm cardiovascular.blood_pressure.observed_diastolic (unsupported): Independent source reading differs from the extraction. The patient fact 'cardiovascular.blood_pressure.observed_diastolic' is not documented in the provided source passages.
- [ ] Confirm cardiovascular.blood_pressure.persistent_diastolic (unsupported): Independent source reading differs from the extraction. The patient fact 'cardiovascular.blood_pressure.persistent_diastolic' is not documented in the provided source passages.
- [ ] Confirm cardiovascular.blood_pressure.persistent_systolic (unsupported): Independent source reading differs from the extraction. The patient fact 'cardiovascular.blood_pressure.persistent_systolic' is not documented in the provided source passages.
- [ ] Fields withheld from rule inputs: cardiovascular.blood_pressure.observed_diastolic, cardiovascular.blood_pressure.persistent_diastolic, cardiovascular.blood_pressure.persistent_systolic

## Case source

```text
Synthetic nurse note for software testing. No real patient data.

During a commercial-driver review after a refrigerated-freight run, the nurse brings together the driver's account, a dated clinical attachment and an employer form copied from an earlier assessment; the documents refer to different times, and the current entry distinguishes a completed examination from recollections, plans and information concerning another person.

The driver restarted antihypertensive tablets twelve days ago after a period of missed doses, and the current clinic letter still records persistent BP 174/104 mmHg on repeat checks; a four-week follow-up period has not yet been completed, the driver brings a booking confirmation rather than a specialist opinion, and occasional improvement on a home display cannot establish sustained control or the absence of relevant treatment problems.

The employer's copied form relates to an earlier period of work and contains a broad satisfactory box without the measurements underlying it, whereas the current nurse entry identifies the source of each specific finding; the driver's wish to continue scheduled duties is recorded as a preference, not as proof that the present assessment has resolved the documented concern.

The record is prepared for the reviewing clinician with the sequence of events and the provenance of the available findings intact, because the employer summary and the driver's account answer different questions; a completed test is retained as such, but an unresolved detail is not filled in from a family member's history or from an earlier document with different testing conditions.

```

Input SHA-256: `20b680d491c80f87a9b0ef10b145c2a5a3464e3046d3fcc7e72e2705ce00f896`
Rule-result SHA-256: `9f912efd2c11d4a250f2d96b03c7b48724983f7c9d480ebdfd74a861b378b4f4`
Evidence-pack SHA-256: `8a5a05094f1a0bd7c6c53323bb68b3719b07d03f4a089ad45d2cbc16c53eee33`
