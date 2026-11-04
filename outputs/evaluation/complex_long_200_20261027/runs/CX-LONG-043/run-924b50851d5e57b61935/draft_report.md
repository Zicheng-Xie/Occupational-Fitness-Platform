# Clinical review draft — CX-LONG-043

CX-LONG-043: Meets unconditional standard. 1 requested modules; 0 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

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
  - Source lines 5–5; chars 604:630: persistent BP 168/100 mmHg
- `cardiovascular.blood_pressure.persistent_systolic` = 168 (present)
  - Source lines 5–5; chars 604:630: persistent BP 168/100 mmHg

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

At a scheduled commercial-driver medical, the driver answers questions in several stages because a dispatcher keeps calling about the next route, while the nurse checks a current clinical document against a copied workplace summary; an observation described confidently in conversation is kept separate from a finding actually recorded in an identified examination.

After the initial arrival reading was discarded because the cuff was slipping, repeat measurements over several visits were reviewed by the treating doctor, who documents persistent BP 168/100 mmHg with the correct cuff and seated rest; the driver has no current cardiac symptoms, and a depot worker's much higher figure belongs to another person rather than a second measurement of this driver.

The usual work involves coupling trailers, checking mirrors, interpreting radio messages and responding to pedestrians in a loading area, with breaks that can be delayed when deliveries run late; the driver explains which difficulty occurred while stationary and which was noticed during ordinary duties, rather than claiming that quiet conversation in the clinic reproduces every task in the cab.

The nurse keeps the relevant current attachment with the record and identifies the older account by its timing, so a later reviewer can distinguish what was observed, what the driver reported and what remains unresolved; no additional measurement, specialist conclusion or diagnosis is added merely because it would make the occupational decision easier to complete.

```

Input SHA-256: `33a806f2f580ffa34ea9d23081159ca2f237261ffc6ecc54ab9b9d3014ed975d`
Rule-result SHA-256: `c409cf8756e7c4d2ad2e5c2d7941e525e9e2f04a86290e0ab2d0746878dfbb0d`
Evidence-pack SHA-256: `356723d370f0a41a0745466fb626c4f242eb62c3978b626dc3513f6f2458b131`
