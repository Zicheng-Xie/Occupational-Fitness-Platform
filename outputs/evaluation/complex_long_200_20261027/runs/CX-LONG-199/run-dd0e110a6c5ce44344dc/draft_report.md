# Clinical review draft — CX-LONG-199

CX-LONG-199: Meets unconditional standard. 1 requested modules; 0 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

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

- `cardiovascular.blood_pressure.persistent_diastolic` = 99 (present)
  - Source lines 5–5; chars 604:629: persistent BP 170/99 mmHg
- `cardiovascular.blood_pressure.persistent_systolic` = 170 (present)
  - Source lines 5–5; chars 604:629: persistent BP 170/99 mmHg

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

After the initial arrival reading was discarded because the cuff was slipping, repeat measurements over several visits were reviewed by the treating doctor, who documents persistent BP 170/99 mmHg with the correct cuff and seated rest; the driver has no current cardiac symptoms, and a depot worker's much higher figure belongs to another person rather than a second measurement of this driver.

The driver alternates urban deliveries with a longer motorway leg and describes a busy depot where engine noise, glare and interrupted meals can complicate an account of symptoms; the nurse records the work setting as context, while keeping the dated clinical findings distinct from the driver's explanation for why a symptom might have occurred on that shift.

For the occupational reviewer, the nurse retains both the definite findings and the limitations of the available account, including the timing and testing conditions where they matter, rather than producing a single reassuring label; the driver is told which information is on file and which details still require confirmation, without replacing the recorded clinical evidence with an employer's preference.

```

Input SHA-256: `1e81b6203ce124d6a9e8215a92d7c838997948dc23f339c123d427c15c379adf`
Rule-result SHA-256: `581a00f33b4e6a729d0a5b8bf9c3217795c65880b0b97c15352a6e40ba0ceeea`
Evidence-pack SHA-256: `b4deba7e084f7b79903304167e730902f382eccef46e9d25ff11ecb5b07efc4f`
