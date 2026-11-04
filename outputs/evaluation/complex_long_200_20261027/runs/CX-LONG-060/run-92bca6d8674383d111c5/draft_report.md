# Clinical review draft — CX-LONG-060

CX-LONG-060: Insufficient information. 1 requested modules; 2 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| blackout | Insufficient information | human_review | 2 |

## Established rule findings

No rule criteria were established from the available verified facts. This does not establish absence of disease or failure of retrieval.


## Information coverage

- blackout: No source-supported facts for this requested module; some facts require confirmation; 0 supported fields; 2 unresolved rule fields.

## Retrieval activity

Rule-scoped ranking calls: 8.
Symptom discovery searches: 1.
Zero triggered rules does not mean retrieval failed. Retrieved text is not a diagnosis.

### blackout symptom retrieval

> The specialist's signed history confirms two blackouts separated by more than 24 hours, with the last event 8.7 years ago and the mechanism still undetermined after completed investigations; the driver has had no more recent confirmed events, but the two episodes were not merely clustered in one day, and a family account that calls them one illness does not change the documented separation or the elapsed interval.

- [AFTD2022-BLK-COM-005, PDF 70](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=70)
- [AFTD2022-BLK-COM-004, PDF 70](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=70)
- [AFTD2022-BLK-COM-006, PDF 69](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=69)
- [AFTD2022-BLK-COM-003, PDF 70](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=70)
- [AFTD2022-BLK-COM-001, PDF 68](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=68)

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: Possible extraction issues require confirmation
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
Confirm blackout.mechanism_status (omission): Independent source reading differs from the extraction. The specialist's signed history confirms two blackouts separated by more than 24 hours, with the last event 8.7 years ago and the mechanism still undetermined after completed investigations; the driver has had no more recent confirmed events, but the two episodes were not merely clustered in one day, and a family account that calls them one illness does not change the documented separation or the elapsed interval.
Confirm blackout.occurred (omission): Independent source reading differs from the extraction. The specialist's signed history confirms two blackouts separated by more than 24 hours, with the last event 8.7 years ago and the mechanism still undetermined after completed investigations.
Fields withheld from rule inputs: blackout.mechanism_status, blackout.occurred

### blackout.mechanism_status — omission

Independent source reading differs from the extraction. The specialist's signed history confirms two blackouts separated by more than 24 hours, with the last event 8.7 years ago and the mechanism still undetermined after completed investigations; the driver has had no more recent confirmed events, but the two episodes were not merely clustered in one day, and a family account that calls them one illness does not change the documented separation or the elapsed interval.

Source lines 5–5; characters 460:877
> The specialist's signed history confirms two blackouts separated by more than 24 hours, with the last event 8.7 years ago and the mechanism still undetermined after completed investigations; the driver has had no more recent confirmed events, but the two episodes were not merely clustered in one day, and a family account that calls them one illness does not change the documented separation or the elapsed interval.

### blackout.occurred — omission

Independent source reading differs from the extraction. The specialist's signed history confirms two blackouts separated by more than 24 hours, with the last event 8.7 years ago and the mechanism still undetermined after completed investigations.

Source lines 5–5; characters 460:877
> The specialist's signed history confirms two blackouts separated by more than 24 hours, with the last event 8.7 years ago and the mechanism still undetermined after completed investigations; the driver has had no more recent confirmed events, but the two episodes were not merely clustered in one day, and a family account that calls them one illness does not change the documented separation or the elapsed interval.

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### BLK-COM-UNDIAGNOSED-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.mechanism_status` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 460:877: The specialist's signed history confirms two blackouts separated by more than 24 hours, with the last event 8.7 years ago and the mechanism still undetermined after completed investigations; the driver has had no more recent confirmed events, but the two episodes were not merely clustered in one day, and a family account that calls them one illness does not change the documented separation or the elapsed interval.
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 460:877: The specialist's signed history confirms two blackouts separated by more than 24 hours, with the last event 8.7 years ago and the mechanism still undetermined after completed investigations; the driver has had no more recent confirmed events, but the two episodes were not merely clustered in one day, and a family account that calls them one illness does not change the documented separation or the elapsed interval.

Guideline sources: [AFTD2022-BLK-COM-001](#aftd2022-blk-com-001)

### BLK-COM-VASOVAGAL-EXCEPTION-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.diagnosis` = UNKNOWN (unknown)
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 460:877: The specialist's signed history confirms two blackouts separated by more than 24 hours, with the last event 8.7 years ago and the mechanism still undetermined after completed investigations; the driver has had no more recent confirmed events, but the two episodes were not merely clustered in one day, and a family account that calls them one illness does not change the documented separation or the elapsed interval.
- `blackout.provoking_factor_well_defined` = UNKNOWN (unknown)
- `blackout.recurrence_while_driving_unlikely` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-BLK-COM-002](#aftd2022-blk-com-002)

### BLK-COM-UNCERTAIN-UNCONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.mechanism_status` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 460:877: The specialist's signed history confirms two blackouts separated by more than 24 hours, with the last event 8.7 years ago and the mechanism still undetermined after completed investigations; the driver has had no more recent confirmed events, but the two episodes were not merely clustered in one day, and a family account that calls them one illness does not change the documented separation or the elapsed interval.
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 460:877: The specialist's signed history confirms two blackouts separated by more than 24 hours, with the last event 8.7 years ago and the mechanism still undetermined after completed investigations; the driver has had no more recent confirmed events, but the two episodes were not merely clustered in one day, and a family account that calls them one illness does not change the documented separation or the elapsed interval.

Guideline sources: [AFTD2022-BLK-COM-003](#aftd2022-blk-com-003)

### BLK-COM-SINGLE-WAIT-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.episodes_separated_by_24h_count` = UNKNOWN (unknown)
- `blackout.mechanism_status` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 460:877: The specialist's signed history confirms two blackouts separated by more than 24 hours, with the last event 8.7 years ago and the mechanism still undetermined after completed investigations; the driver has had no more recent confirmed events, but the two episodes were not merely clustered in one day, and a family account that calls them one illness does not change the documented separation or the elapsed interval.
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 460:877: The specialist's signed history confirms two blackouts separated by more than 24 hours, with the last event 8.7 years ago and the mechanism still undetermined after completed investigations; the driver has had no more recent confirmed events, but the two episodes were not merely clustered in one day, and a family account that calls them one illness does not change the documented separation or the elapsed interval.
- `blackout.years_since_last_event` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-BLK-COM-004](#aftd2022-blk-com-004)

### BLK-COM-RECURRENT-WAIT-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.episodes_separated_by_24h_count` = UNKNOWN (unknown)
- `blackout.mechanism_status` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 460:877: The specialist's signed history confirms two blackouts separated by more than 24 hours, with the last event 8.7 years ago and the mechanism still undetermined after completed investigations; the driver has had no more recent confirmed events, but the two episodes were not merely clustered in one day, and a family account that calls them one illness does not change the documented separation or the elapsed interval.
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 460:877: The specialist's signed history confirms two blackouts separated by more than 24 hours, with the last event 8.7 years ago and the mechanism still undetermined after completed investigations; the driver has had no more recent confirmed events, but the two episodes were not merely clustered in one day, and a family account that calls them one illness does not change the documented separation or the elapsed interval.
- `blackout.years_since_last_event` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-BLK-COM-005](#aftd2022-blk-com-005)

### BLK-COM-CONDITIONAL-ELIGIBILITY-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.appropriate_specialist_information_available` = UNKNOWN (unknown)
- `blackout.episodes_separated_by_24h_count` = UNKNOWN (unknown)
- `blackout.mechanism_status` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 460:877: The specialist's signed history confirms two blackouts separated by more than 24 hours, with the last event 8.7 years ago and the mechanism still undetermined after completed investigations; the driver has had no more recent confirmed events, but the two episodes were not merely clustered in one day, and a family account that calls them one illness does not change the documented separation or the elapsed interval.
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 460:877: The specialist's signed history confirms two blackouts separated by more than 24 hours, with the last event 8.7 years ago and the mechanism still undetermined after completed investigations; the driver has had no more recent confirmed events, but the two episodes were not merely clustered in one day, and a family account that calls them one illness does not change the documented separation or the elapsed interval.
- `blackout.years_since_last_event` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-BLK-COM-004](#aftd2022-blk-com-004), [AFTD2022-BLK-COM-005](#aftd2022-blk-com-005)

### BLK-COM-NO-HISTORY-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 460:877: The specialist's signed history confirms two blackouts separated by more than 24 hours, with the last event 8.7 years ago and the mechanism still undetermined after completed investigations; the driver has had no more recent confirmed events, but the two episodes were not merely clustered in one day, and a family account that calls them one illness does not change the documented separation or the elapsed interval.

Guideline sources: [AFTD2022-BLK-COM-001](#aftd2022-blk-com-001)

### BLK-COM-DIAGNOSED-REFERRAL-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.diagnosis` = UNKNOWN (unknown)
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 460:877: The specialist's signed history confirms two blackouts separated by more than 24 hours, with the last event 8.7 years ago and the mechanism still undetermined after completed investigations; the driver has had no more recent confirmed events, but the two episodes were not merely clustered in one day, and a family account that calls them one illness does not change the documented separation or the elapsed interval.

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

### AFTD2022-BLK-COM-003

[§1.3 · printed 59 / PDF 70](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=70)

Table/context: Uncertain blackouts: unconditional

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has experienced blackouts 
> that cannot be diagnosed as syncope, 
> seizure or another condition.

PDF region: (354.0, 309.0, 531.0, 378.0); text SHA-256: `2a4cd0409e88aaf1c7ad208d84640971b8e0793c738d869d949acb17d0803295`.

### AFTD2022-BLK-COM-004

[§1.3 · printed 59 / PDF 70](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=70)

Table/context: Single/clustered uncertain blackout; read all qualifications

> A person should not drive for 5 
> years following a single blackout of 
> undetermined nature.
> A person should not drive for 10 years 
> following two or more blackouts of 
> undetermined nature separated by a 24-
> hour period.
> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has experienced blackouts 
> that cannot be diagnosed as syncope, 
> seizure or another condition.
> If there has been a single blackout or more 
> than one blackout within a 24-hour period, 
> a conditional licence may be considered 
> by the driver licensing authority subject to 
> at least annual review, taking into account 
> information provided by an appropriate 
> specialist as to whether the following 
> criterion is met:
> •	 there have been no further blackouts for 
> at least 5 years.

PDF region: (354.0, 219.0, 531.0, 511.0); text SHA-256: `755748eea7c89a47066501c56a6fd8850304b696fcca5f69b0f83faf58ffec59`.

### AFTD2022-BLK-COM-005

[§1.3 · printed 59 / PDF 70](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=70)

Table/context: Recurrent uncertain blackout; read all qualifications

> A person should not drive for 10 years 
> following two or more blackouts of 
> undetermined nature separated by a 24-
> hour period.
> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has experienced blackouts 
> that cannot be diagnosed as syncope, 
> seizure or another condition.
> If there has been a single blackout or more 
> than one blackout within a 24-hour period, 
> a conditional licence may be considered 
> by the driver licensing authority subject to 
> at least annual review, taking into account 
> information provided by an appropriate 
> specialist as to whether the following 
> criterion is met:
> •	 there have been no further blackouts for 
> at least 5 years.
> If there have been two or more blackouts 
> separated by at least 24 hours, a 
> conditional licence may be considered by 
> the driver licensing authority subject to at 
> least annual review, taking into account 
> information provided by an appropriate 
> specialist as to whether the following 
> criterion is met:
> •	 there have been no further blackouts for 
> at least 10 years.

PDF region: (354.0, 259.0, 531.0, 642.0); text SHA-256: `518da4f1500d8f8c838d81b4032f1a22f7e592d32c018c48a0242fc3c20bb05e`.

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
- [ ] Confirm missing/unverified case fact: blackout.mechanism_status
- [ ] Confirm missing/unverified case fact: blackout.occurred
- [ ] requires_confirmation
- [ ] Extraction semantic review: Possible extraction issues require confirmation
- [ ] This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
- [ ] Confirm blackout.mechanism_status (omission): Independent source reading differs from the extraction. The specialist's signed history confirms two blackouts separated by more than 24 hours, with the last event 8.7 years ago and the mechanism still undetermined after completed investigations; the driver has had no more recent confirmed events, but the two episodes were not merely clustered in one day, and a family account that calls them one illness does not change the documented separation or the elapsed interval.
- [ ] Confirm blackout.occurred (omission): Independent source reading differs from the extraction. The specialist's signed history confirms two blackouts separated by more than 24 hours, with the last event 8.7 years ago and the mechanism still undetermined after completed investigations.
- [ ] Fields withheld from rule inputs: blackout.mechanism_status, blackout.occurred

## Case source

```text
Synthetic nurse note for software testing. No real patient data.

The commercial driver attends after a long shift with a folder containing a current signed letter, older screening paperwork and a handwritten personal account, and the nurse reconstructs the chronology before recording the present findings; differences between the records are described explicitly rather than resolved by treating the newest-looking photocopy as automatically authoritative.

The specialist's signed history confirms two blackouts separated by more than 24 hours, with the last event 8.7 years ago and the mechanism still undetermined after completed investigations; the driver has had no more recent confirmed events, but the two episodes were not merely clustered in one day, and a family account that calls them one illness does not change the documented separation or the elapsed interval.

The employer's copied form relates to an earlier period of work and contains a broad satisfactory box without the measurements underlying it, whereas the current nurse entry identifies the source of each specific finding; the driver's wish to continue scheduled duties is recorded as a preference, not as proof that the present assessment has resolved the documented concern.

The nurse keeps the relevant current attachment with the record and identifies the older account by its timing, so a later reviewer can distinguish what was observed, what the driver reported and what remains unresolved; no additional measurement, specialist conclusion or diagnosis is added merely because it would make the occupational decision easier to complete.

```

Input SHA-256: `8ea7dc3605ee23497c17c4dace8fa15f066b3e2aad1334b283fec1f2dc50b563`
Rule-result SHA-256: `53a597339a07ede694fb849ed669c3212b8401efd8cee9fb61571513c9de9d41`
Evidence-pack SHA-256: `b0d8424f74383e6909699e6191a8fd5aa683d0a367e88e7f308966e729d6a7cf`
