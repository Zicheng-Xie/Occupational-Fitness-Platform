# Clinical review draft — CX-LONG-175

CX-LONG-175: Insufficient information. 2 requested modules; 4 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| blackout | Insufficient information | human_review | 1 |
| hearing | Insufficient information | human_review | 3 |

## Established rule findings

No rule criteria were established from the available verified facts. This does not establish absence of disease or failure of retrieval.


## Information coverage

- blackout: Source-supported facts available; some facts require confirmation; 1 supported fields; 1 unresolved rule fields.
- hearing: Source-supported facts available; some facts require confirmation; 1 supported fields; 3 unresolved rule fields.

## Retrieval activity

Rule-scoped ranking calls: 9.
Symptom discovery searches: 2.
Zero triggered rules does not mean retrieval failed. Retrieved text is not a diagnosis.

### blackout symptom retrieval

> A colleague witnessed the driver lose consciousness and fail to respond for 15 seconds during a break, and the current physician referral explicitly records a blackout with the mechanism under investigation; although the driver recalls heat, hunger and a racing heartbeat beforehand, neither syncope, seizure nor hypoglycaemia has been confirmed, cardiac monitoring is pending, and uncertainty about a remote dizzy spell does not erase the documented recent event.

- [AFTD2022-BLK-COM-004, PDF 70](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=70)
- [AFTD2022-BLK-COM-002, PDF 68](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=68)
- [AFTD2022-BLK-COM-006, PDF 69](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=69)
- [AFTD2022-BLK-COM-001, PDF 68](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=68)
- [AFTD2022-BLK-COM-005, PDF 70](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=70)
### hearing symptom retrieval

> A colleague witnessed the driver lose consciousness and fail to respond for 15 seconds during a break, and the current physician referral explicitly records a blackout with the mechanism under investigation; although the driver recalls heat, hunger and a racing heartbeat beforehand, neither syncope, seizure nor hypoglycaemia has been confirmed, cardiac monitoring is pending, and uncertainty about a remote dizzy spell does not erase the documented recent event. The nurse also records possible hearing loss after repeated missed spoken instructions, and audiometry has not been performed; the driver can follow a quiet conversation but no unaided better-ear threshold, complete frequency set or qualified aided-performance result is available for this separate screening concern.

- [AFTD2022-HEAR-COM-003, PDF 120](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)
- [AFTD2022-HEAR-COM-004, PDF 120](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)
- [AFTD2022-HEAR-COM-002, PDF 120](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)
- [AFTD2022-HEAR-COM-001, PDF 120](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: Possible extraction issues require confirmation
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
Confirm blackout.occurred (omission): Independent source reading differs from the extraction. A colleague witnessed the driver lose consciousness and fail to respond for 15 seconds during a break, and the current physician referral explicitly records a blackout with the mechanism under investigation.
Confirm hearing.clinical_assessment (omission): Independent source reading differs from the extraction. A screening impression of possible hearing loss is a documented classification possible_hearing_loss, not confirmation of a measured hearing threshold.
Fields withheld from rule inputs: blackout.occurred, hearing.clinical_assessment

### blackout.occurred — omission

Independent source reading differs from the extraction. A colleague witnessed the driver lose consciousness and fail to respond for 15 seconds during a break, and the current physician referral explicitly records a blackout with the mechanism under investigation.

Source lines 5–5; characters 448:912
> A colleague witnessed the driver lose consciousness and fail to respond for 15 seconds during a break, and the current physician referral explicitly records a blackout with the mechanism under investigation; although the driver recalls heat, hunger and a racing heartbeat beforehand, neither syncope, seizure nor hypoglycaemia has been confirmed, cardiac monitoring is pending, and uncertainty about a remote dizzy spell does not erase the documented recent event.

### hearing.clinical_assessment — omission

Independent source reading differs from the extraction. A screening impression of possible hearing loss is a documented classification possible_hearing_loss, not confirmation of a measured hearing threshold.

Source lines 9–9; characters 1283:1600
> The nurse also records possible hearing loss after repeated missed spoken instructions, and audiometry has not been performed; the driver can follow a quiet conversation but no unaided better-ear threshold, complete frequency set or qualified aided-performance result is available for this separate screening concern.

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### BLK-COM-UNDIAGNOSED-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.mechanism_status` = under_investigation (present)
  - Source lines 5–5; chars 621:654: the mechanism under investigation
  - Source lines 5–5; chars 607:654: blackout with the mechanism under investigation
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:912: A colleague witnessed the driver lose consciousness and fail to respond for 15 seconds during a break, and the current physician referral explicitly records a blackout with the mechanism under investigation; although the driver recalls heat, hunger and a racing heartbeat beforehand, neither syncope, seizure nor hypoglycaemia has been confirmed, cardiac monitoring is pending, and uncertainty about a remote dizzy spell does not erase the documented recent event.

Guideline sources: [AFTD2022-BLK-COM-001](#aftd2022-blk-com-001)

### BLK-COM-VASOVAGAL-EXCEPTION-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.diagnosis` = UNKNOWN (unknown)
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:912: A colleague witnessed the driver lose consciousness and fail to respond for 15 seconds during a break, and the current physician referral explicitly records a blackout with the mechanism under investigation; although the driver recalls heat, hunger and a racing heartbeat beforehand, neither syncope, seizure nor hypoglycaemia has been confirmed, cardiac monitoring is pending, and uncertainty about a remote dizzy spell does not erase the documented recent event.
- `blackout.provoking_factor_well_defined` = UNKNOWN (unknown)
- `blackout.recurrence_while_driving_unlikely` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-BLK-COM-002](#aftd2022-blk-com-002)

### HEAR-COM-AUDIOMETRY-MISSING-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.audiometry.available` = False (present)
  - Source lines 9–9; chars 1283:1410: The nurse also records possible hearing loss after repeated missed spoken instructions, and audiometry has not been performed; 
- `hearing.clinical_assessment` = UNKNOWN (requires_confirmation)
  - Source lines 9–9; chars 1283:1600: The nurse also records possible hearing loss after repeated missed spoken instructions, and audiometry has not been performed; the driver can follow a quiet conversation but no unaided better-ear threshold, complete frequency set or qualified aided-performance result is available for this separate screening concern.

Guideline sources: [AFTD2022-HEAR-COM-001](#aftd2022-hear-com-001)

### HEAR-COM-UNCONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.average_frequencies_khz` = UNKNOWN (unknown)
- `hearing.clinical_assessment` = UNKNOWN (requires_confirmation)
  - Source lines 9–9; chars 1283:1600: The nurse also records possible hearing loss after repeated missed spoken instructions, and audiometry has not been performed; the driver can follow a quiet conversation but no unaided better-ear threshold, complete frequency set or qualified aided-performance result is available for this separate screening concern.
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
  - Source lines 9–9; chars 1283:1600: The nurse also records possible hearing loss after repeated missed spoken instructions, and audiometry has not been performed; the driver can follow a quiet conversation but no unaided better-ear threshold, complete frequency set or qualified aided-performance result is available for this separate screening concern.
- `hearing.unaided_better_ear_average_db` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HEAR-COM-001](#aftd2022-hear-com-001), [AFTD2022-HEAR-COM-002](#aftd2022-hear-com-002)

### BLK-COM-NO-HISTORY-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:912: A colleague witnessed the driver lose consciousness and fail to respond for 15 seconds during a break, and the current physician referral explicitly records a blackout with the mechanism under investigation; although the driver recalls heat, hunger and a racing heartbeat beforehand, neither syncope, seizure nor hypoglycaemia has been confirmed, cardiac monitoring is pending, and uncertainty about a remote dizzy spell does not erase the documented recent event.

Guideline sources: [AFTD2022-BLK-COM-001](#aftd2022-blk-com-001)

### BLK-COM-DIAGNOSED-REFERRAL-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.diagnosis` = UNKNOWN (unknown)
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:912: A colleague witnessed the driver lose consciousness and fail to respond for 15 seconds during a break, and the current physician referral explicitly records a blackout with the mechanism under investigation; although the driver recalls heat, hunger and a racing heartbeat beforehand, neither syncope, seizure nor hypoglycaemia has been confirmed, cardiac monitoring is pending, and uncertainty about a remote dizzy spell does not erase the documented recent event.

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
- [ ] Confirm missing/unverified case fact: blackout.occurred
- [ ] Confirm missing/unverified case fact: hearing.average_frequencies_khz
- [ ] Confirm missing/unverified case fact: hearing.clinical_assessment
- [ ] Confirm missing/unverified case fact: hearing.unaided_better_ear_average_db
- [ ] requires_confirmation
- [ ] Extraction semantic review: Possible extraction issues require confirmation
- [ ] This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
- [ ] Confirm blackout.occurred (omission): Independent source reading differs from the extraction. A colleague witnessed the driver lose consciousness and fail to respond for 15 seconds during a break, and the current physician referral explicitly records a blackout with the mechanism under investigation.
- [ ] Confirm hearing.clinical_assessment (omission): Independent source reading differs from the extraction. A screening impression of possible hearing loss is a documented classification possible_hearing_loss, not confirmation of a measured hearing threshold.
- [ ] Fields withheld from rule inputs: blackout.occurred, hearing.clinical_assessment

## Case source

```text
Synthetic nurse note for software testing. No real patient data.

The nurse reviews a commercial driver's symptoms alongside information from a witness, the treating team and an older workplace form, because each source describes a different part of the story; the occupational record retains those differences and identifies completed current findings without turning a booking, a family account or a recollection into a measured patient result.

A colleague witnessed the driver lose consciousness and fail to respond for 15 seconds during a break, and the current physician referral explicitly records a blackout with the mechanism under investigation; although the driver recalls heat, hunger and a racing heartbeat beforehand, neither syncope, seizure nor hypoglycaemia has been confirmed, cardiac monitoring is pending, and uncertainty about a remote dizzy spell does not erase the documented recent event.

The interview takes place before the driver's next planned roster, and the nurse records changes in symptoms, treatment and available documents without assuming that a future specialist appointment has already occurred; any letter that has been requested but not supplied remains separate from the findings actually available when this occupational record is written.

The nurse also records possible hearing loss after repeated missed spoken instructions, and audiometry has not been performed; the driver can follow a quiet conversation but no unaided better-ear threshold, complete frequency set or qualified aided-performance result is available for this separate screening concern.

The nurse reads the summary back to the driver to check the chronology and separates agreement about the wording from verification of a medical finding, then attaches the identified clinical material; any decision about further investigation or work allocation remains for the reviewing professional, and the note itself does not certify that all relevant clinical questions have been answered.

```

Input SHA-256: `4516a09854bb10f34b18b2cb975995611ac2972bec033c2f8f0ccb0fa6072641`
Rule-result SHA-256: `e7ce4b02497e66022f2487f64eefb3f7fa5404bcb45764c9a8367784600eb1ee`
Evidence-pack SHA-256: `04fded71d10cce6b1fb0d4ac526f9483b8f7cedc2655444747908e34fba3374c`
