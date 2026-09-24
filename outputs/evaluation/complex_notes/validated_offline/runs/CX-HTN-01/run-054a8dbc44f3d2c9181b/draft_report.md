# Clinical review draft — CX-HTN-01

CX-HTN-01: Insufficient information. 1 requested modules; 2 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| hypertension | Insufficient information | missing_information | 2 |

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: Not performed (disabled)
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### HTN-COM-UNCONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `cardiovascular.blood_pressure.persistent_diastolic` = UNKNOWN (unknown)
- `cardiovascular.blood_pressure.persistent_systolic` = UNKNOWN (unknown)

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

- `cardiovascular.blood_pressure.persistent_diastolic` = UNKNOWN (unknown)
- `cardiovascular.blood_pressure.persistent_systolic` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HTN-COM-001](#aftd2022-htn-com-001)

## Guideline evidence

### AFTD2022-HTN-COM-001

[§2.3.1 · printed 88 / PDF 99](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)

Table/context: Hypertension: unconditional

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has blood pressure 
> consistently > 170 systolic or > 100 diastolic 
> (treated or untreated).

PDF region: (345.0, 177.0, 530.0, 247.0); text SHA-256: `eeacf5b9430b10bb961f6b727f6b4eb638baaf8aeecde7413ad4b4dea2baef7d`.

### AFTD2022-HTN-COM-002

[§2.3.1 · printed 88 / PDF 99](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)

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

## Case source

```text
At the commercial-driver review, the driver says the depot machine displayed 178/104 after unloading and two coffees, whereas the handwritten home sheet contains readings of 138/86 and 142/88 from an unverified cuff; today's seated BP 166/96 mmHg was taken once, and although he describes headaches after late shifts, he denies current chest pain and cannot say whether the headaches coincide with higher readings.

He restarted his blood-pressure tablets nine days ago after missing several doses, sometimes feels light-headed on standing, and has no repeat measurement or specialist letter with him; the nurse cannot establish persistent blood pressure, four weeks of stable control, or whether the symptoms are medication related from this interview.

```

Input SHA-256: `544f300fbd29fcd85a5cca5be02186f7c611314f9e634859bfb429e0c539ed6e`
Rule-result SHA-256: `c95b0cc0bb5ba7473bef5a8d0408f147d3abc277b2ce5dd3eda16adf02beba17`
Evidence-pack SHA-256: `f8f806f1e47484ce7aebcc3d0c60567401a95c582c4e60c81a82afb1714ce2b0`
