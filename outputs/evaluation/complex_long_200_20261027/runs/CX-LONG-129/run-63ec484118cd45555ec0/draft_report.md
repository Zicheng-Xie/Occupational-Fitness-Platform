# Clinical review draft — CX-LONG-129

CX-LONG-129: Insufficient information. 1 requested modules; 1 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| blackout | Insufficient information | human_review | 1 |

## Established rule findings

No rule criteria were established from the available verified facts. This does not establish absence of disease or failure of retrieval.


## Information coverage

- blackout: Source-supported facts available; some facts require confirmation; 1 supported fields; 1 unresolved rule fields.

## Retrieval activity

Rule-scoped ranking calls: 4.
Symptom discovery searches: 1.
Zero triggered rules does not mean retrieval failed. Retrieved text is not a diagnosis.

### blackout symptom retrieval

> A colleague witnessed the driver lose consciousness and fail to respond for 18 seconds during a break, and the current physician referral explicitly records a blackout with the mechanism under investigation; although the driver recalls heat, hunger and a racing heartbeat beforehand, neither syncope, seizure nor hypoglycaemia has been confirmed, cardiac monitoring is pending, and uncertainty about a remote dizzy spell does not erase the documented recent event.

- [AFTD2022-BLK-COM-004, PDF 70](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=70)
- [AFTD2022-BLK-COM-002, PDF 68](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=68)
- [AFTD2022-BLK-COM-006, PDF 69](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=69)
- [AFTD2022-BLK-COM-001, PDF 68](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=68)
- [AFTD2022-BLK-COM-005, PDF 70](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=70)

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: Possible extraction issues require confirmation
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
Confirm blackout.occurred (omission): Independent source reading differs from the extraction. The colleague witnessed the driver lose consciousness and fail to respond for 18 seconds during a break, and the current physician referral explicitly records a blackout with the mechanism under investigation.
Fields withheld from rule inputs: blackout.occurred

### blackout.occurred — omission

Independent source reading differs from the extraction. The colleague witnessed the driver lose consciousness and fail to respond for 18 seconds during a break, and the current physician referral explicitly records a blackout with the mechanism under investigation.

Source lines 5–5; characters 436:900
> A colleague witnessed the driver lose consciousness and fail to respond for 18 seconds during a break, and the current physician referral explicitly records a blackout with the mechanism under investigation; although the driver recalls heat, hunger and a racing heartbeat beforehand, neither syncope, seizure nor hypoglycaemia has been confirmed, cardiac monitoring is pending, and uncertainty about a remote dizzy spell does not erase the documented recent event.

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### BLK-COM-UNDIAGNOSED-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.mechanism_status` = under_investigation (present)
  - Source lines 5–5; chars 609:642: the mechanism under investigation
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 436:900: A colleague witnessed the driver lose consciousness and fail to respond for 18 seconds during a break, and the current physician referral explicitly records a blackout with the mechanism under investigation; although the driver recalls heat, hunger and a racing heartbeat beforehand, neither syncope, seizure nor hypoglycaemia has been confirmed, cardiac monitoring is pending, and uncertainty about a remote dizzy spell does not erase the documented recent event.

Guideline sources: [AFTD2022-BLK-COM-001](#aftd2022-blk-com-001)

### BLK-COM-VASOVAGAL-EXCEPTION-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.diagnosis` = UNKNOWN (unknown)
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 436:900: A colleague witnessed the driver lose consciousness and fail to respond for 18 seconds during a break, and the current physician referral explicitly records a blackout with the mechanism under investigation; although the driver recalls heat, hunger and a racing heartbeat beforehand, neither syncope, seizure nor hypoglycaemia has been confirmed, cardiac monitoring is pending, and uncertainty about a remote dizzy spell does not erase the documented recent event.
- `blackout.provoking_factor_well_defined` = UNKNOWN (unknown)
- `blackout.recurrence_while_driving_unlikely` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-BLK-COM-002](#aftd2022-blk-com-002)

### BLK-COM-NO-HISTORY-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 436:900: A colleague witnessed the driver lose consciousness and fail to respond for 18 seconds during a break, and the current physician referral explicitly records a blackout with the mechanism under investigation; although the driver recalls heat, hunger and a racing heartbeat beforehand, neither syncope, seizure nor hypoglycaemia has been confirmed, cardiac monitoring is pending, and uncertainty about a remote dizzy spell does not erase the documented recent event.

Guideline sources: [AFTD2022-BLK-COM-001](#aftd2022-blk-com-001)

### BLK-COM-DIAGNOSED-REFERRAL-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.diagnosis` = UNKNOWN (unknown)
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 436:900: A colleague witnessed the driver lose consciousness and fail to respond for 18 seconds during a break, and the current physician referral explicitly records a blackout with the mechanism under investigation; although the driver recalls heat, hunger and a racing heartbeat beforehand, neither syncope, seizure nor hypoglycaemia has been confirmed, cardiac monitoring is pending, and uncertainty about a remote dizzy spell does not erase the documented recent event.

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
- [ ] Confirm blackout.occurred (omission): Independent source reading differs from the extraction. The colleague witnessed the driver lose consciousness and fail to respond for 18 seconds during a break, and the current physician referral explicitly records a blackout with the mechanism under investigation.
- [ ] Fields withheld from rule inputs: blackout.occurred

## Case source

```text
Synthetic nurse note for software testing. No real patient data.

During a commercial-driver review after a refrigerated-freight run, the nurse brings together the driver's account, a dated clinical attachment and an employer form copied from an earlier assessment; the documents refer to different times, and the current entry distinguishes a completed examination from recollections, plans and information concerning another person.

A colleague witnessed the driver lose consciousness and fail to respond for 18 seconds during a break, and the current physician referral explicitly records a blackout with the mechanism under investigation; although the driver recalls heat, hunger and a racing heartbeat beforehand, neither syncope, seizure nor hypoglycaemia has been confirmed, cardiac monitoring is pending, and uncertainty about a remote dizzy spell does not erase the documented recent event.

The employer's copied form relates to an earlier period of work and contains a broad satisfactory box without the measurements underlying it, whereas the current nurse entry identifies the source of each specific finding; the driver's wish to continue scheduled duties is recorded as a preference, not as proof that the present assessment has resolved the documented concern.

The nurse keeps the relevant current attachment with the record and identifies the older account by its timing, so a later reviewer can distinguish what was observed, what the driver reported and what remains unresolved; no additional measurement, specialist conclusion or diagnosis is added merely because it would make the occupational decision easier to complete.

```

Input SHA-256: `2597a2edc87f457a95a3bda2b267592334ab5bb4ce834ae1c9234288282ff6de`
Rule-result SHA-256: `d301e68e5ea988054695aba728837d3d3b5e0137b60d25cc09be80693d7316c0`
Evidence-pack SHA-256: `5a6f81a143746f9491278b26f34e56cbebca751bf781961d46f78de24cbef8a3`
