# Clinical review draft — CX-LONG-193

CX-LONG-193: Insufficient information. 1 requested modules; 5 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

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

> The driver restarted antihypertensive tablets twelve days ago after a period of missed doses, and the current clinic letter still records persistent BP 176/102 mmHg on repeat checks; a four-week follow-up period has not yet been completed, the driver brings a booking confirmation rather than a specialist opinion, and occasional improvement on a home display cannot establish sustained control or the absence of relevant treatment problems.

- [AFTD2022-HTN-COM-002, PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)
- [AFTD2022-HTN-COM-001, PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: Possible extraction issues require confirmation
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
Confirm cardiovascular.blood_pressure.observed_diastolic (unsupported): Independent source reading differs from the extraction. The patient fact 'cardiovascular.blood_pressure.observed_diastolic' is not documented in the provided source passages.
Fields withheld from rule inputs: cardiovascular.blood_pressure.observed_diastolic

### cardiovascular.blood_pressure.observed_diastolic — unsupported

Independent source reading differs from the extraction. The patient fact 'cardiovascular.blood_pressure.observed_diastolic' is not documented in the provided source passages.

Source lines 5–5; characters 591:606
> BP 176/102 mmHg

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### HTN-COM-UNCONDITIONAL-001 — triggered

Persistent blood pressure exceeds the commercial unconditional-licence threshold.

- `cardiovascular.blood_pressure.persistent_diastolic` = 102.0 (present)
  - Source lines 5–5; chars 580:606: persistent BP 176/102 mmHg
  - Source lines 5–5; chars 580:606: persistent BP 176/102 mmHg
- `cardiovascular.blood_pressure.persistent_systolic` = 176.0 (present)
  - Source lines 5–5; chars 580:606: persistent BP 176/102 mmHg
  - Source lines 5–5; chars 580:606: persistent BP 176/102 mmHg

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
- [ ] Confirm cardiovascular.blood_pressure.observed_diastolic (unsupported): Independent source reading differs from the extraction. The patient fact 'cardiovascular.blood_pressure.observed_diastolic' is not documented in the provided source passages.
- [ ] Fields withheld from rule inputs: cardiovascular.blood_pressure.observed_diastolic

## Case source

```text
Synthetic nurse note for software testing. No real patient data.

In a commercial-driver follow-up arranged after an occupational screening concern, the nurse interviews the driver and checks the accompanying documents against the reported sequence of events; the employer wants a quick answer before allocating a vehicle, but the record separates present evidence, historical findings and questions that the clinician has not yet resolved.

The driver restarted antihypertensive tablets twelve days ago after a period of missed doses, and the current clinic letter still records persistent BP 176/102 mmHg on repeat checks; a four-week follow-up period has not yet been completed, the driver brings a booking confirmation rather than a specialist opinion, and occasional improvement on a home display cannot establish sustained control or the absence of relevant treatment problems.

The employer's copied form relates to an earlier period of work and contains a broad satisfactory box without the measurements underlying it, whereas the current nurse entry identifies the source of each specific finding; the driver's wish to continue scheduled duties is recorded as a preference, not as proof that the present assessment has resolved the documented concern.

The nurse keeps the relevant current attachment with the record and identifies the older account by its timing, so a later reviewer can distinguish what was observed, what the driver reported and what remains unresolved; no additional measurement, specialist conclusion or diagnosis is added merely because it would make the occupational decision easier to complete.

```

Input SHA-256: `c4854ce90d04816b60eef229700f9e120d75545edf67fa2aaf24d4f4710e1b9c`
Rule-result SHA-256: `c7afd8a684209bc136e7d4f372c68e730cf865a411e0a521985118073ac0270e`
Evidence-pack SHA-256: `768e16a126200f58db51363c6c7383700a22b1bd9092b19550a2f93ac30ec43e`
