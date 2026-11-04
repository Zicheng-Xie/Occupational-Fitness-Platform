# Clinical review draft — CX-LONG-030

CX-LONG-030: Insufficient information. 1 requested modules; 5 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| hypertension | Insufficient information | human_review | 5 |

## Established rule findings

1 rules triggered from source-supported facts. The overall assessment is incomplete; this does not erase the findings below. Missing facts in any requested module can prevent an overall clearance.

- hypertension: `HTN-COM-UNCONDITIONAL-001` - Persistent blood pressure exceeds the commercial unconditional-licence threshold.

## Information coverage

- hypertension: Source-supported facts available; some facts require confirmation; 4 supported fields; 5 unresolved rule fields.

## Retrieval activity

Rule-scoped ranking calls: 2.
Symptom discovery searches: 1.
Zero triggered rules does not mean retrieval failed. Retrieved text is not a diagnosis.

### hypertension symptom retrieval

> The current signed clinic summary documents persistent BP 188/96 mmHg after repeated seated measurements across separate visits, rather than the first reading taken while unloading; the driver describes pressure-like headaches after long shifts but has no current chest pain, while the dates of resumed treatment, sustained control and the specialist's initial assessment cannot be confirmed from the documents available today.

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

Source lines 5–5; characters 695:716
> no current chest pain

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### HTN-COM-UNCONDITIONAL-001 — triggered

Persistent blood pressure exceeds the commercial unconditional-licence threshold.

- `cardiovascular.blood_pressure.persistent_diastolic` = 96.0 (present)
  - Source lines 5–5; chars 486:511: persistent BP 188/96 mmHg
  - Source lines 5–5; chars 486:511: persistent BP 188/96 mmHg
- `cardiovascular.blood_pressure.persistent_systolic` = 188.0 (present)
  - Source lines 5–5; chars 486:511: persistent BP 188/96 mmHg
  - Source lines 5–5; chars 486:511: persistent BP 188/96 mmHg

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
- [ ] Confirm cardiovascular.chest_pain (unsupported): Independent source reading differs from the extraction. The patient fact 'cardiovascular.chest_pain' is not mentioned in the provided source passages.
- [ ] Fields withheld from rule inputs: cardiovascular.chest_pain

## Case source

```text
Synthetic nurse note for software testing. No real patient data.

In a commercial-driver follow-up arranged after an occupational screening concern, the nurse interviews the driver and checks the accompanying documents against the reported sequence of events; the employer wants a quick answer before allocating a vehicle, but the record separates present evidence, historical findings and questions that the clinician has not yet resolved.

The current signed clinic summary documents persistent BP 188/96 mmHg after repeated seated measurements across separate visits, rather than the first reading taken while unloading; the driver describes pressure-like headaches after long shifts but has no current chest pain, while the dates of resumed treatment, sustained control and the specialist's initial assessment cannot be confirmed from the documents available today.

The usual work involves coupling trailers, checking mirrors, interpreting radio messages and responding to pedestrians in a loading area, with breaks that can be delayed when deliveries run late; the driver explains which difficulty occurred while stationary and which was noticed during ordinary duties, rather than claiming that quiet conversation in the clinic reproduces every task in the cab.

The nurse reads the summary back to the driver to check the chronology and separates agreement about the wording from verification of a medical finding, then attaches the identified clinical material; any decision about further investigation or work allocation remains for the reviewing professional, and the note itself does not certify that all relevant clinical questions have been answered.

```

Input SHA-256: `60e93ae391df360d4a976f9722f7ec64c1ec1113593e46649e89629ee5f7304e`
Rule-result SHA-256: `15a108a968eaf2b2232bd51c336f9a2febedc1a439f654e9bac95dd35580418c`
Evidence-pack SHA-256: `612259206755cbda24a497a3c757a29fcd3a78676e88f50f288ac4f02426938e`
