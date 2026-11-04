# Clinical review draft — CX-LONG-155

CX-LONG-155: Insufficient information. 2 requested modules; 5 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| blackout | Insufficient information | human_review | 2 |
| hearing | Insufficient information | human_review | 3 |

## Established rule findings

No rule criteria were established from the available verified facts. This does not establish absence of disease or failure of retrieval.


## Information coverage

- blackout: No source-supported facts for this requested module; some facts require confirmation; 0 supported fields; 2 unresolved rule fields.
- hearing: Source-supported facts available; some facts require confirmation; 1 supported fields; 3 unresolved rule fields.

## Retrieval activity

Rule-scoped ranking calls: 13.
Symptom discovery searches: 2.
Zero triggered rules does not mean retrieval failed. Retrieved text is not a diagnosis.

### blackout symptom retrieval

> The specialist's completed investigation found no diagnosable cause for a single confirmed blackout, and the signed chronology documents one event with no further events over 2.7 years; the nurse records that this is a blackout of undetermined nature after investigation, rather than an investigation still pending, while an earlier faint in the driver's father is kept separate from the patient's event count and cannot create a recurrent patient history.

- [AFTD2022-BLK-COM-004, PDF 70](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=70)
- [AFTD2022-BLK-COM-006, PDF 69](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=69)
- [AFTD2022-BLK-COM-005, PDF 70](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=70)
- [AFTD2022-BLK-COM-003, PDF 70](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=70)
- [AFTD2022-BLK-COM-002, PDF 68](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=68)
### hearing symptom retrieval

> The nurse also records possible hearing loss after repeated missed spoken instructions, and audiometry has not been performed; the driver can follow a quiet conversation but no unaided better-ear threshold, complete frequency set or qualified aided-performance result is available for this separate screening concern.

- [AFTD2022-HEAR-COM-001, PDF 120](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)
- [AFTD2022-HEAR-COM-002, PDF 120](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)
- [AFTD2022-HEAR-COM-004, PDF 120](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)
- [AFTD2022-HEAR-COM-003, PDF 120](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: Possible extraction issues require confirmation
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
Confirm blackout.mechanism_status (omission): Independent source reading differs from the extraction. The specialist's completed investigation found no diagnosable cause for a single confirmed blackout, and the signed chronology documents one event with no further events over 2.7 years; the nurse records that this is a blackout of undetermined nature after investigation, rather than an investigation still pending, while an earlier faint in the driver's father is kept separate from the patient's event count and cannot create a recurrent patient history.
Confirm blackout.occurred (omission): Independent source reading differs from the extraction. The specialist's completed investigation found no diagnosable cause for a single confirmed blackout, and the signed chronology documents one event with no further events over 2.7 years; the nurse records that this is a blackout of undetermined nature after investigation, rather than an investigation still pending, while an earlier faint in the driver's father is kept separate from the patient's event count and cannot create a recurrent patient history.
Confirm hearing.clinical_assessment (omission): Independent source reading differs from the extraction. A screening impression of possible hearing_loss is a documented classification possible_hearing_loss, not confirmation of a measured hearing threshold.
Fields withheld from rule inputs: blackout.mechanism_status, blackout.occurred, hearing.clinical_assessment

### blackout.mechanism_status — omission

Independent source reading differs from the extraction. The specialist's completed investigation found no diagnosable cause for a single confirmed blackout, and the signed chronology documents one event with no further events over 2.7 years; the nurse records that this is a blackout of undetermined nature after investigation, rather than an investigation still pending, while an earlier faint in the driver's father is kept separate from the patient's event count and cannot create a recurrent patient history.

Source lines 5–5; characters 448:904
> The specialist's completed investigation found no diagnosable cause for a single confirmed blackout, and the signed chronology documents one event with no further events over 2.7 years; the nurse records that this is a blackout of undetermined nature after investigation, rather than an investigation still pending, while an earlier faint in the driver's father is kept separate from the patient's event count and cannot create a recurrent patient history.

### blackout.occurred — omission

Independent source reading differs from the extraction. The specialist's completed investigation found no diagnosable cause for a single confirmed blackout, and the signed chronology documents one event with no further events over 2.7 years; the nurse records that this is a blackout of undetermined nature after investigation, rather than an investigation still pending, while an earlier faint in the driver's father is kept separate from the patient's event count and cannot create a recurrent patient history.

Source lines 5–5; characters 448:904
> The specialist's completed investigation found no diagnosable cause for a single confirmed blackout, and the signed chronology documents one event with no further events over 2.7 years; the nurse records that this is a blackout of undetermined nature after investigation, rather than an investigation still pending, while an earlier faint in the driver's father is kept separate from the patient's event count and cannot create a recurrent patient history.

### hearing.clinical_assessment — omission

Independent source reading differs from the extraction. A screening impression of possible hearing_loss is a documented classification possible_hearing_loss, not confirmation of a measured hearing threshold.

Source lines 9–9; characters 1268:1585
> The nurse also records possible hearing loss after repeated missed spoken instructions, and audiometry has not been performed; the driver can follow a quiet conversation but no unaided better-ear threshold, complete frequency set or qualified aided-performance result is available for this separate screening concern.

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### BLK-COM-UNDIAGNOSED-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.mechanism_status` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:904: The specialist's completed investigation found no diagnosable cause for a single confirmed blackout, and the signed chronology documents one event with no further events over 2.7 years; the nurse records that this is a blackout of undetermined nature after investigation, rather than an investigation still pending, while an earlier faint in the driver's father is kept separate from the patient's event count and cannot create a recurrent patient history.
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:904: The specialist's completed investigation found no diagnosable cause for a single confirmed blackout, and the signed chronology documents one event with no further events over 2.7 years; the nurse records that this is a blackout of undetermined nature after investigation, rather than an investigation still pending, while an earlier faint in the driver's father is kept separate from the patient's event count and cannot create a recurrent patient history.

Guideline sources: [AFTD2022-BLK-COM-001](#aftd2022-blk-com-001)

### BLK-COM-VASOVAGAL-EXCEPTION-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.diagnosis` = UNKNOWN (unknown)
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:904: The specialist's completed investigation found no diagnosable cause for a single confirmed blackout, and the signed chronology documents one event with no further events over 2.7 years; the nurse records that this is a blackout of undetermined nature after investigation, rather than an investigation still pending, while an earlier faint in the driver's father is kept separate from the patient's event count and cannot create a recurrent patient history.
- `blackout.provoking_factor_well_defined` = UNKNOWN (unknown)
- `blackout.recurrence_while_driving_unlikely` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-BLK-COM-002](#aftd2022-blk-com-002)

### BLK-COM-UNCERTAIN-UNCONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.mechanism_status` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:904: The specialist's completed investigation found no diagnosable cause for a single confirmed blackout, and the signed chronology documents one event with no further events over 2.7 years; the nurse records that this is a blackout of undetermined nature after investigation, rather than an investigation still pending, while an earlier faint in the driver's father is kept separate from the patient's event count and cannot create a recurrent patient history.
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:904: The specialist's completed investigation found no diagnosable cause for a single confirmed blackout, and the signed chronology documents one event with no further events over 2.7 years; the nurse records that this is a blackout of undetermined nature after investigation, rather than an investigation still pending, while an earlier faint in the driver's father is kept separate from the patient's event count and cannot create a recurrent patient history.

Guideline sources: [AFTD2022-BLK-COM-003](#aftd2022-blk-com-003)

### BLK-COM-SINGLE-WAIT-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.episodes_separated_by_24h_count` = UNKNOWN (unknown)
- `blackout.mechanism_status` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:904: The specialist's completed investigation found no diagnosable cause for a single confirmed blackout, and the signed chronology documents one event with no further events over 2.7 years; the nurse records that this is a blackout of undetermined nature after investigation, rather than an investigation still pending, while an earlier faint in the driver's father is kept separate from the patient's event count and cannot create a recurrent patient history.
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:904: The specialist's completed investigation found no diagnosable cause for a single confirmed blackout, and the signed chronology documents one event with no further events over 2.7 years; the nurse records that this is a blackout of undetermined nature after investigation, rather than an investigation still pending, while an earlier faint in the driver's father is kept separate from the patient's event count and cannot create a recurrent patient history.
- `blackout.years_since_last_event` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-BLK-COM-004](#aftd2022-blk-com-004)

### BLK-COM-RECURRENT-WAIT-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.episodes_separated_by_24h_count` = UNKNOWN (unknown)
- `blackout.mechanism_status` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:904: The specialist's completed investigation found no diagnosable cause for a single confirmed blackout, and the signed chronology documents one event with no further events over 2.7 years; the nurse records that this is a blackout of undetermined nature after investigation, rather than an investigation still pending, while an earlier faint in the driver's father is kept separate from the patient's event count and cannot create a recurrent patient history.
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:904: The specialist's completed investigation found no diagnosable cause for a single confirmed blackout, and the signed chronology documents one event with no further events over 2.7 years; the nurse records that this is a blackout of undetermined nature after investigation, rather than an investigation still pending, while an earlier faint in the driver's father is kept separate from the patient's event count and cannot create a recurrent patient history.
- `blackout.years_since_last_event` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-BLK-COM-005](#aftd2022-blk-com-005)

### BLK-COM-CONDITIONAL-ELIGIBILITY-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.appropriate_specialist_information_available` = UNKNOWN (unknown)
- `blackout.episodes_separated_by_24h_count` = UNKNOWN (unknown)
- `blackout.mechanism_status` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:904: The specialist's completed investigation found no diagnosable cause for a single confirmed blackout, and the signed chronology documents one event with no further events over 2.7 years; the nurse records that this is a blackout of undetermined nature after investigation, rather than an investigation still pending, while an earlier faint in the driver's father is kept separate from the patient's event count and cannot create a recurrent patient history.
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:904: The specialist's completed investigation found no diagnosable cause for a single confirmed blackout, and the signed chronology documents one event with no further events over 2.7 years; the nurse records that this is a blackout of undetermined nature after investigation, rather than an investigation still pending, while an earlier faint in the driver's father is kept separate from the patient's event count and cannot create a recurrent patient history.
- `blackout.years_since_last_event` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-BLK-COM-004](#aftd2022-blk-com-004), [AFTD2022-BLK-COM-005](#aftd2022-blk-com-005)

### HEAR-COM-AUDIOMETRY-MISSING-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.audiometry.available` = False (present)
  - Source lines 9–9; chars 1268:1395: The nurse also records possible hearing loss after repeated missed spoken instructions, and audiometry has not been performed; 
- `hearing.clinical_assessment` = UNKNOWN (requires_confirmation)
  - Source lines 9–9; chars 1268:1585: The nurse also records possible hearing loss after repeated missed spoken instructions, and audiometry has not been performed; the driver can follow a quiet conversation but no unaided better-ear threshold, complete frequency set or qualified aided-performance result is available for this separate screening concern.

Guideline sources: [AFTD2022-HEAR-COM-001](#aftd2022-hear-com-001)

### HEAR-COM-UNCONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.average_frequencies_khz` = UNKNOWN (unknown)
- `hearing.clinical_assessment` = UNKNOWN (requires_confirmation)
  - Source lines 9–9; chars 1268:1585: The nurse also records possible hearing loss after repeated missed spoken instructions, and audiometry has not been performed; the driver can follow a quiet conversation but no unaided better-ear threshold, complete frequency set or qualified aided-performance result is available for this separate screening concern.
- `hearing.unaided_better_ear_average_db` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HEAR-COM-002](#aftd2022-hear-com-002)

### HEAR-COM-CONDITIONAL-AID-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.aided_standard_met` = UNKNOWN (unknown)
- `hearing.ent_or_audiologist_information_available` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HEAR-COM-003](#aftd2022-hear-com-003)

### HEAR-COM-INDIVIDUAL-ASSESSMENT-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.aided_standard_met` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HEAR-COM-004](#aftd2022-hear-com-004)

### HEAR-COM-SCREEN-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.average_frequencies_khz` = UNKNOWN (unknown)
- `hearing.clinical_assessment` = UNKNOWN (requires_confirmation)
  - Source lines 9–9; chars 1268:1585: The nurse also records possible hearing loss after repeated missed spoken instructions, and audiometry has not been performed; the driver can follow a quiet conversation but no unaided better-ear threshold, complete frequency set or qualified aided-performance result is available for this separate screening concern.
- `hearing.unaided_better_ear_average_db` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HEAR-COM-001](#aftd2022-hear-com-001), [AFTD2022-HEAR-COM-002](#aftd2022-hear-com-002)

### BLK-COM-NO-HISTORY-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:904: The specialist's completed investigation found no diagnosable cause for a single confirmed blackout, and the signed chronology documents one event with no further events over 2.7 years; the nurse records that this is a blackout of undetermined nature after investigation, rather than an investigation still pending, while an earlier faint in the driver's father is kept separate from the patient's event count and cannot create a recurrent patient history.

Guideline sources: [AFTD2022-BLK-COM-001](#aftd2022-blk-com-001)

### BLK-COM-DIAGNOSED-REFERRAL-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.diagnosis` = UNKNOWN (unknown)
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:904: The specialist's completed investigation found no diagnosable cause for a single confirmed blackout, and the signed chronology documents one event with no further events over 2.7 years; the nurse records that this is a blackout of undetermined nature after investigation, rather than an investigation still pending, while an earlier faint in the driver's father is kept separate from the patient's event count and cannot create a recurrent patient history.

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

### AFTD2022-HEAR-COM-001

[§4.3 · printed 109 / PDF 120](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)

Table/context: Hearing: clinical assessment and audiometry

> Compliance with the standard should be clinically 
> assessed initially. If the initial clinical assessment 
> indicates possible hearing loss, the person should 
> be referred for audiometry.

PDF region: (320.0, 273.0, 531.0, 325.0); text SHA-256: `658c8e0d61ff7a066d001e669c6673a4dca8fd439d85009a8ecef07432d5ddbb`.

### AFTD2022-HEAR-COM-002

[§4.3 · printed 109 / PDF 120](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)

Table/context: Hearing: unaided four-frequency average

> A person is not fit to hold an unconditional licence:
> •	 if the person has unaided hearing loss ≥ 40 dB 
> in the better ear (averaged over the frequencies 
> 0.5, 1, 2 and 3 KHz).

PDF region: (320.0, 327.0, 531.0, 385.0); text SHA-256: `78ef0b09576857072cbc395e26ad22ce08bd7e94bca53ee68bf36f48facb0b6a`.

### AFTD2022-HEAR-COM-003

[§4.3 · printed 109 / PDF 120](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)

Table/context: Hearing: conditional and all footnotes

> A conditional licence may be considered by the 
> driver licensing authority subject to periodic review*, 
> taking into account the nature of the driving task 
> and information provided by an ENT specialist or 
> audiologist**, as to whether:
> •	 the standard is able to be met with a hearing 
> aid***.
> If the standard is not able to be met with a hearing 
> aid, further individualised assessment should be 
> offered. 
> A conditional licence may be considered by the 
> driver licensing authority subject to periodic review*, 
> taking into account:
> •	 the nature of the driving task; and
> •	 information provided by an ENT specialist or 
> audiologist**; and
> •	 the results of a practical driver assessment if 
> required. 
> * Stable conditions may not require periodic review. 
> ** Refer to section 4.2. General assessment and 
> management guidelines.
> *** In some cases, noise amplification as a result of 
> wearing hearing aids may lead to driver distraction 
> and may warrant individualised assessment to 
> determine fitness to drive without the hearing aid 
> (refer to 4.2. General assessment and management 
> guidelines).

PDF region: (320.0, 386.0, 531.0, 766.0); text SHA-256: `ab9dffe6e58bb057a616adb6dda7ea391a340994027e84e369cf4ede3ec7cd88`.

### AFTD2022-HEAR-COM-004

[§4.3 · printed 109 / PDF 120](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)

Table/context: Hearing: individualised assessment and all footnotes

> If the standard is not able to be met with a hearing 
> aid, further individualised assessment should be 
> offered. 
> A conditional licence may be considered by the 
> driver licensing authority subject to periodic review*, 
> taking into account:
> •	 the nature of the driving task; and
> •	 information provided by an ENT specialist or 
> audiologist**; and
> •	 the results of a practical driver assessment if 
> required. 
> * Stable conditions may not require periodic review. 
> ** Refer to section 4.2. General assessment and 
> management guidelines.
> *** In some cases, noise amplification as a result of 
> wearing hearing aids may lead to driver distraction 
> and may warrant individualised assessment to 
> determine fitness to drive without the hearing aid 
> (refer to 4.2. General assessment and management 
> guidelines).

PDF region: (320.0, 481.0, 531.0, 766.0); text SHA-256: `2dc9b07eb871ca8d70fd21cc22b6c624418fe6268ac1684b14853dc91cbf2f18`.

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
- [ ] Confirm missing/unverified case fact: hearing.average_frequencies_khz
- [ ] Confirm missing/unverified case fact: hearing.clinical_assessment
- [ ] Confirm missing/unverified case fact: hearing.unaided_better_ear_average_db
- [ ] requires_confirmation
- [ ] Extraction semantic review: Possible extraction issues require confirmation
- [ ] This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
- [ ] Confirm blackout.mechanism_status (omission): Independent source reading differs from the extraction. The specialist's completed investigation found no diagnosable cause for a single confirmed blackout, and the signed chronology documents one event with no further events over 2.7 years; the nurse records that this is a blackout of undetermined nature after investigation, rather than an investigation still pending, while an earlier faint in the driver's father is kept separate from the patient's event count and cannot create a recurrent patient history.
- [ ] Confirm blackout.occurred (omission): Independent source reading differs from the extraction. The specialist's completed investigation found no diagnosable cause for a single confirmed blackout, and the signed chronology documents one event with no further events over 2.7 years; the nurse records that this is a blackout of undetermined nature after investigation, rather than an investigation still pending, while an earlier faint in the driver's father is kept separate from the patient's event count and cannot create a recurrent patient history.
- [ ] Confirm hearing.clinical_assessment (omission): Independent source reading differs from the extraction. A screening impression of possible hearing_loss is a documented classification possible_hearing_loss, not confirmation of a measured hearing threshold.
- [ ] Fields withheld from rule inputs: blackout.mechanism_status, blackout.occurred, hearing.clinical_assessment

## Case source

```text
Synthetic nurse note for software testing. No real patient data.

The nurse reviews a commercial driver's symptoms alongside information from a witness, the treating team and an older workplace form, because each source describes a different part of the story; the occupational record retains those differences and identifies completed current findings without turning a booking, a family account or a recollection into a measured patient result.

The specialist's completed investigation found no diagnosable cause for a single confirmed blackout, and the signed chronology documents one event with no further events over 2.7 years; the nurse records that this is a blackout of undetermined nature after investigation, rather than an investigation still pending, while an earlier faint in the driver's father is kept separate from the patient's event count and cannot create a recurrent patient history.

The driver alternates urban deliveries with a longer motorway leg and describes a busy depot where engine noise, glare and interrupted meals can complicate an account of symptoms; the nurse records the work setting as context, while keeping the dated clinical findings distinct from the driver's explanation for why a symptom might have occurred on that shift.

The nurse also records possible hearing loss after repeated missed spoken instructions, and audiometry has not been performed; the driver can follow a quiet conversation but no unaided better-ear threshold, complete frequency set or qualified aided-performance result is available for this separate screening concern.

The nurse keeps the relevant current attachment with the record and identifies the older account by its timing, so a later reviewer can distinguish what was observed, what the driver reported and what remains unresolved; no additional measurement, specialist conclusion or diagnosis is added merely because it would make the occupational decision easier to complete.

```

Input SHA-256: `d10c4039e6d34980ae3fc4189ac53891b08dde7712765d8fdd1de0f491192e9c`
Rule-result SHA-256: `533036a7bfc029a93f7abf0076d38b9e53dfc1f30ba6dd33ddf2deaf514ef205`
Evidence-pack SHA-256: `1e8649600a71ca80e70cd375d378457ecc896e27be35f049da3ccdd29b47e940`
