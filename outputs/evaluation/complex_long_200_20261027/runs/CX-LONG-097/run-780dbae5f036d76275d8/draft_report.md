# Clinical review draft — CX-LONG-097

CX-LONG-097: Insufficient information. 2 requested modules; 1 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| hypertension | Meets unconditional standard | fast_path | 0 |
| blackout | Insufficient information | human_review | 1 |

## Established rule findings

1 rules triggered from source-supported facts. The overall assessment is incomplete; this does not erase the findings below. Missing facts in any requested module can prevent an overall clearance.

- hypertension: `HTN-COM-SCREEN-001` - Recorded persistent pressures do not exceed the hypertension threshold; this finding covers hypertension only.

## Information coverage

- hypertension: Source-supported facts available; 4 supported fields; 0 unresolved rule fields.
- blackout: Source-supported facts available; some facts require confirmation; 1 supported fields; 1 unresolved rule fields.

## Retrieval activity

Rule-scoped ranking calls: 5.
Symptom discovery searches: 2.
Zero triggered rules does not mean retrieval failed. Retrieved text is not a diagnosis.

### blackout symptom retrieval

> A separate current referral documents a witnessed blackout with loss of consciousness during a break and states that the mechanism is under investigation; the driver remembers feeling hot before the event, but neither a benign faint nor a metabolic cause has been confirmed, and cardiac monitoring remains pending.

- [AFTD2022-BLK-COM-006, PDF 69](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=69)
- [AFTD2022-BLK-COM-002, PDF 68](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=68)
- [AFTD2022-BLK-COM-001, PDF 68](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=68)
- [AFTD2022-BLK-COM-005, PDF 70](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=70)
- [AFTD2022-BLK-COM-004, PDF 70](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=70)
### hypertension symptom retrieval

> After the initial arrival reading was discarded because the cuff was slipping, repeat measurements over several visits were reviewed by the treating doctor, who documents persistent BP 170/100 mmHg with the correct cuff and seated rest; the driver has no current cardiac symptoms, and a depot worker's much higher figure belongs to another person rather than a second measurement of this driver.

- [AFTD2022-HTN-COM-001, PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)
- [AFTD2022-HTN-COM-002, PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: Possible extraction issues require confirmation
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
Confirm blackout.occurred (omission): Independent source reading differs from the extraction. The driver remembers feeling hot before the event, but neither a benign faint nor a metabolic cause has been confirmed, and cardiac monitoring remains pending.
Fields withheld from rule inputs: blackout.occurred

### blackout.occurred — omission

Independent source reading differs from the extraction. The driver remembers feeling hot before the event, but neither a benign faint nor a metabolic cause has been confirmed, and cardiac monitoring remains pending.

Source lines 9–9; characters 1199:1513
> A separate current referral documents a witnessed blackout with loss of consciousness during a break and states that the mechanism is under investigation; the driver remembers feeling hot before the event, but neither a benign faint nor a metabolic cause has been confirmed, and cardiac monitoring remains pending.

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### BLK-COM-UNDIAGNOSED-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.mechanism_status` = under_investigation (present)
  - Source lines 9–9; chars 1316:1352: the mechanism is under investigation
  - Source lines 9–9; chars 1199:1354: A separate current referral documents a witnessed blackout with loss of consciousness during a break and states that the mechanism is under investigation; 
  - Source lines 9–9; chars 1316:1352: the mechanism is under investigation
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 9–9; chars 1199:1513: A separate current referral documents a witnessed blackout with loss of consciousness during a break and states that the mechanism is under investigation; the driver remembers feeling hot before the event, but neither a benign faint nor a metabolic cause has been confirmed, and cardiac monitoring remains pending.

Guideline sources: [AFTD2022-BLK-COM-001](#aftd2022-blk-com-001)

### BLK-COM-VASOVAGAL-EXCEPTION-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.diagnosis` = UNKNOWN (unknown)
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 9–9; chars 1199:1513: A separate current referral documents a witnessed blackout with loss of consciousness during a break and states that the mechanism is under investigation; the driver remembers feeling hot before the event, but neither a benign faint nor a metabolic cause has been confirmed, and cardiac monitoring remains pending.
- `blackout.provoking_factor_well_defined` = UNKNOWN (unknown)
- `blackout.recurrence_while_driving_unlikely` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-BLK-COM-002](#aftd2022-blk-com-002)

### HTN-COM-SCREEN-001 — triggered

Recorded persistent pressures do not exceed the hypertension threshold; this finding covers hypertension only.

- `cardiovascular.blood_pressure.persistent_diastolic` = 100.0 (present)
  - Source lines 5–5; chars 604:630: persistent BP 170/100 mmHg
  - Source lines 5–5; chars 604:630: persistent BP 170/100 mmHg
- `cardiovascular.blood_pressure.persistent_systolic` = 170.0 (present)
  - Source lines 5–5; chars 604:630: persistent BP 170/100 mmHg
  - Source lines 5–5; chars 604:630: persistent BP 170/100 mmHg

Guideline sources: [AFTD2022-HTN-COM-001](#aftd2022-htn-com-001)

### BLK-COM-NO-HISTORY-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 9–9; chars 1199:1513: A separate current referral documents a witnessed blackout with loss of consciousness during a break and states that the mechanism is under investigation; the driver remembers feeling hot before the event, but neither a benign faint nor a metabolic cause has been confirmed, and cardiac monitoring remains pending.

Guideline sources: [AFTD2022-BLK-COM-001](#aftd2022-blk-com-001)

### BLK-COM-DIAGNOSED-REFERRAL-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.diagnosis` = UNKNOWN (unknown)
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 9–9; chars 1199:1513: A separate current referral documents a witnessed blackout with loss of consciousness during a break and states that the mechanism is under investigation; the driver remembers feeling hot before the event, but neither a benign faint nor a metabolic cause has been confirmed, and cardiac monitoring remains pending.

Guideline sources: [AFTD2022-BLK-COM-006](#aftd2022-blk-com-006)

## Guideline evidence

### AFTD2022-BLK-COM-001

[§1.2.1 · printed 57 / PDF 68](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=68)

Table/context: Blackout work-up; continuation of general considerations

> cardiovascular and neurological investigations 
> and referral to several specialists. People should 
> be advised not to drive until the mechanism is 
> ascertained and the corresponding standard met.

PDF region: (305.0, 117.0, 545.0, 182.0); text SHA-256: `dd23a937a5e99db2c2440ffc7ef66d4003092af008384c56d49be31234941a55`.

### AFTD2022-BLK-COM-002

[§1.2.2 · printed 57 / PDF 68](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=68)

Table/context: Provoked vasovagal syncope

> 1.2.2. Vasovagal syncope5
> The most common cause of transient loss of 
> consciousness is vasovagal syncope (‘fainting’). 
> Where this has been triggered by a well-defined 
> provoking factor or a situation that is unlikely 
> to recur while driving (e.g. prolonged standing, 
> venepuncture or emotional situation), it is not 
> necessary to restrict driving. However, vasovagal 
> syncope may also result from other causes 
> that are not so benign. In such cases, fitness 
> to drive should be assessed according to the 
> cardiovascular conditions standards for syncope 
> (refer to section 2. Cardiovascular conditions).

PDF region: (305.0, 310.0, 545.0, 528.0); text SHA-256: `5112bc351b42fbbccb6f50c74ef3f4ec7399be904ea14184aca1f14eaa7e249b`.

### AFTD2022-HTN-COM-001

[§2.3.1 · printed 88 / PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)

Table/context: Hypertension: unconditional

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has blood pressure 
> consistently > 170 systolic or > 100 diastolic 
> (treated or untreated).

PDF region: (345.0, 177.0, 530.0, 247.0); text SHA-256: `eeacf5b9430b10bb961f6b727f6b4eb638baaf8aeecde7413ad4b4dea2baef7d`.

### AFTD2022-BLK-COM-006

[§1.3 · printed 58 / PDF 69](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=69)

Table/context: Diagnosed blackout cross-referrals

> themselves with the information in this chapter 
> and the tabulated standards before assessing a 
> person’s fitness to drive. 
> Where a firm diagnosis has been made, the 
> standard appropriate to the condition should 
> be referred to in this publication (refer to Figure 
> 6. Management of blackouts and driving). For 
> blackouts due to medical causes not covered 
> in the standard, refer to first principles (refer to 
> Part A section 2. Assessing fitness to drive – 
> general guidance). For blackouts where, after 
> investigation, it is not possible to diagnose one 
> of the conditions covered elsewhere in this 
> publication, refer to the table for blackouts of 
> uncertain nature over the page.

PDF region: (305.0, 50.0, 545.0, 330.0); text SHA-256: `d7a6ad8dd8992110bf369465f78225c9783db872080526349c67d7aa07caf574`.

## Clinician checklist

- [ ] Clinician: review source facts, rule applicability and every provisional conclusion.
- [ ] Confirm the commercial driving task and assess conditions outside the five-module scope.
- [ ] Confirm missing/unverified case fact: blackout.occurred
- [ ] requires_confirmation
- [ ] Extraction semantic review: Possible extraction issues require confirmation
- [ ] This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
- [ ] Confirm blackout.occurred (omission): Independent source reading differs from the extraction. The driver remembers feeling hot before the event, but neither a benign faint nor a metabolic cause has been confirmed, and cardiac monitoring remains pending.
- [ ] Fields withheld from rule inputs: blackout.occurred

## Case source

```text
Synthetic nurse note for software testing. No real patient data.

At a scheduled commercial-driver medical, the driver answers questions in several stages because a dispatcher keeps calling about the next route, while the nurse checks a current clinical document against a copied workplace summary; an observation described confidently in conversation is kept separate from a finding actually recorded in an identified examination.

After the initial arrival reading was discarded because the cuff was slipping, repeat measurements over several visits were reviewed by the treating doctor, who documents persistent BP 170/100 mmHg with the correct cuff and seated rest; the driver has no current cardiac symptoms, and a depot worker's much higher figure belongs to another person rather than a second measurement of this driver.

The interview takes place before the driver's next planned roster, and the nurse records changes in symptoms, treatment and available documents without assuming that a future specialist appointment has already occurred; any letter that has been requested but not supplied remains separate from the findings actually available when this occupational record is written.

A separate current referral documents a witnessed blackout with loss of consciousness during a break and states that the mechanism is under investigation; the driver remembers feeling hot before the event, but neither a benign faint nor a metabolic cause has been confirmed, and cardiac monitoring remains pending.

Before closing the interview, the nurse checks that the driver's recollection and the supplied clinical document have not been merged into a single undated finding, and records the outstanding documents separately; the completed entries remain current findings, while any missing qualification, conflicting detail or unperformed examination stays available for review rather than being silently treated as normal.

```

Input SHA-256: `fe6695864294ca0e231091ad9f4aa83ea182f97e2eed4d95cfea99ca708109e3`
Rule-result SHA-256: `6863b4bce37fe8fc0c91f64f670fac32ec08329081956c380db4484a52e91bac`
Evidence-pack SHA-256: `82988fbdfe667b34146a0b43e9fdd6b6d1254d44c5cec01bac661fea75889981`
