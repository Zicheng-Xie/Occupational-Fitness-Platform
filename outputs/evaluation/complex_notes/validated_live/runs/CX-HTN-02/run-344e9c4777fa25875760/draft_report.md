# Clinical review draft — CX-HTN-02

CX-HTN-02: Insufficient information. 1 requested modules; 2 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| hypertension | Insufficient information | human_review | 2 |

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: Not completed (model unavailable or response invalid)
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### HTN-COM-UNCONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `cardiovascular.blood_pressure.persistent_diastolic` = UNKNOWN (requires_confirmation)
  - Source lines 1–2; chars 132:393: an old clinic letter states Persistent BP 176/102 mmHg before treatment last year, while the driver now recalls a usual home pressure near 132/82 without bringing the log, so the old persistent reading must not be treated as a confirmed current measurement.  
- `cardiovascular.blood_pressure.persistent_systolic` = UNKNOWN (requires_confirmation)
  - Source lines 1–2; chars 132:393: an old clinic letter states Persistent BP 176/102 mmHg before treatment last year, while the driver now recalls a usual home pressure near 132/82 without bringing the log, so the old persistent reading must not be treated as a confirmed current measurement.  

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
  - Source lines 1–2; chars 132:393: an old clinic letter states Persistent BP 176/102 mmHg before treatment last year, while the driver now recalls a usual home pressure near 132/82 without bringing the log, so the old persistent reading must not be treated as a confirmed current measurement.  
- `cardiovascular.blood_pressure.persistent_systolic` = UNKNOWN (requires_confirmation)
  - Source lines 1–2; chars 132:393: an old clinic letter states Persistent BP 176/102 mmHg before treatment last year, while the driver now recalls a usual home pressure near 132/82 without bringing the log, so the old persistent reading must not be treated as a confirmed current measurement.  

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
- [ ] cardiovascular.blood_pressure.observed_diastolic
- [ ] cardiovascular.blood_pressure.observed_systolic
- [ ] unavailable_or_invalid
- [ ] cardiovascular.blood_pressure.observed_diastolic
- [ ] cardiovascular.blood_pressure.observed_systolic
- [ ] cardiovascular.blood_pressure.persistent_diastolic
- [ ] cardiovascular.blood_pressure.persistent_systolic
- [ ] Extraction semantic review: Not completed (model unavailable or response invalid)
- [ ] This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.

## Case source

```text
The driver's father had a myocardial infarction at 54, but the driver has no known myocardial infarction and reports no chest pain; an old clinic letter states Persistent BP 176/102 mmHg before treatment last year, while the driver now recalls a usual home pressure near 132/82 without bringing the log, so the old persistent reading must not be treated as a confirmed current measurement.

Medication was changed three weeks ago because of ankle swelling, and he says that he would stop a long trip if dizziness returned, rather than reporting an actual episode today; a review of treatment tolerance, current persistent pressure and any relevant target-organ effects is still outstanding.

```

Input SHA-256: `ec62dfb50c5fb60aa9b2f57f55de0105b21218f52719ab2b7abef114795920b7`
Rule-result SHA-256: `982defd3b48587aa187944a736a7503abe0ceeeafd541dd8a58b77ed4c597ebf`
Evidence-pack SHA-256: `06da0bddd62b04f5f9ceadbcf02e97c61b8d905f91ef9314eeed659d312d4fc8`
