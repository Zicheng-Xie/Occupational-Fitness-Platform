# Clinical review draft — CX-LONG-185

CX-LONG-185: Meets unconditional standard. 1 requested modules; 0 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| hypertension | Meets unconditional standard | fast_path | 0 |

## Established rule findings

The provisional outcome reflects the applicable rule priority. Missing information in other modules remains visible and does not erase an established adverse finding.

- hypertension: `HTN-COM-SCREEN-001` - Recorded persistent pressures do not exceed the hypertension threshold; this finding covers hypertension only.

## Information coverage

- hypertension: Source-supported facts available; 4 supported fields; 0 unresolved rule fields.

## Retrieval activity

Rule-scoped ranking calls: 0.
Symptom discovery searches: 0.
Zero triggered rules does not mean retrieval failed. Retrieved text is not a diagnosis.


[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: No issues flagged by the model
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### HTN-COM-SCREEN-001 — triggered

Recorded persistent pressures do not exceed the hypertension threshold; this finding covers hypertension only.

- `cardiovascular.blood_pressure.persistent_diastolic` = 100 (present)
  - Source lines 5–5; chars 607:633: persistent BP 170/100 mmHg
- `cardiovascular.blood_pressure.persistent_systolic` = 170 (present)
  - Source lines 5–5; chars 607:633: persistent BP 170/100 mmHg

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

## Clinician checklist

- [ ] Clinician: review source facts, rule applicability and every provisional conclusion.
- [ ] Confirm the commercial driving task and assess conditions outside the five-module scope.

## Case source

```text
Synthetic nurse note for software testing. No real patient data.

During a commercial-driver review after a refrigerated-freight run, the nurse brings together the driver's account, a dated clinical attachment and an employer form copied from an earlier assessment; the documents refer to different times, and the current entry distinguishes a completed examination from recollections, plans and information concerning another person.

After the initial arrival reading was discarded because the cuff was slipping, repeat measurements over several visits were reviewed by the treating doctor, who documents persistent BP 170/100 mmHg with the correct cuff and seated rest; the driver has no current cardiac symptoms, and a depot worker's much higher figure belongs to another person rather than a second measurement of this driver.

Part of the usual route requires reversing near workers and reading changing signs before entering a customer site, although today's assessment takes place in a quiet room; the driver is asked to describe the sequence and timing of difficulties, and the note preserves the difference between an occupational concern, a suspected mechanism and a completed clinical assessment.

The record is prepared for the reviewing clinician with the sequence of events and the provenance of the available findings intact, because the employer summary and the driver's account answer different questions; a completed test is retained as such, but an unresolved detail is not filled in from a family member's history or from an earlier document with different testing conditions.

```

Input SHA-256: `534b0ca47ee78b2557b5529ce8063971e138d0bd68c7dc856e966cbb04410042`
Rule-result SHA-256: `4ddf2b09c0895cd820886b109db17a793d1845277be903b56d26934622b7d10b`
Evidence-pack SHA-256: `595339a2c1c9229ab48e71c68a762a71e8f5934c34fce9daeacc207b21758a2c`
