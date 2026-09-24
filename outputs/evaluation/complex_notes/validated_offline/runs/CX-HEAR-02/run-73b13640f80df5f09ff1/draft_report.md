# Clinical review draft — CX-HEAR-02

CX-HEAR-02: Insufficient information. 1 requested modules; 2 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| hearing | Insufficient information | missing_information | 2 |

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: Not performed (disabled)
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### HEAR-COM-AUDIOMETRY-MISSING-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.audiometry.available` = UNKNOWN (unknown)
- `hearing.clinical_assessment` = UNKNOWN (requires_confirmation)
  - Source lines 1–1; chars 19:34: no hearing loss
  - Source lines 1–2; chars 139:382: the employment form copied from last year says Hearing: normal, whereas the nurse observes repeated requests for instructions today and cannot decide whether background noise, equipment failure or a hearing problem explains the difference.  

Guideline sources: [AFTD2022-HEAR-COM-001](#aftd2022-hear-com-001)

### HEAR-COM-UNCONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.average_frequencies_khz` = [0.5, 1, 2, 3] (present)
  - Source lines 3–3; chars 445:478: averaged over 0.5, 1, 2 and 3 kHz
- `hearing.clinical_assessment` = UNKNOWN (requires_confirmation)
  - Source lines 1–1; chars 19:34: no hearing loss
  - Source lines 1–2; chars 139:382: the employment form copied from last year says Hearing: normal, whereas the nurse observes repeated requests for instructions today and cannot decide whether background noise, equipment failure or a hearing problem explains the difference.  
- `hearing.unaided_better_ear_average_db` = UNKNOWN (requires_confirmation)
  - Source lines 3–3; chars 382:577: An unsigned worksheet records unaided better ear average 42 dB averaged over 0.5, 1, 2 and 3 kHz, but the driver remembers wearing both aids during that test and the worksheet's date is missing; 

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

- `hearing.average_frequencies_khz` = [0.5, 1, 2, 3] (present)
  - Source lines 3–3; chars 445:478: averaged over 0.5, 1, 2 and 3 kHz
- `hearing.clinical_assessment` = UNKNOWN (requires_confirmation)
  - Source lines 1–1; chars 19:34: no hearing loss
  - Source lines 1–2; chars 139:382: the employment form copied from last year says Hearing: normal, whereas the nurse observes repeated requests for instructions today and cannot decide whether background noise, equipment failure or a hearing problem explains the difference.  
- `hearing.unaided_better_ear_average_db` = UNKNOWN (requires_confirmation)
  - Source lines 3–3; chars 382:577: An unsigned worksheet records unaided better ear average 42 dB averaged over 0.5, 1, 2 and 3 kHz, but the driver remembers wearing both aids during that test and the worksheet's date is missing; 

Guideline sources: [AFTD2022-HEAR-COM-001](#aftd2022-hear-com-001), [AFTD2022-HEAR-COM-002](#aftd2022-hear-com-002)

## Guideline evidence

### AFTD2022-HEAR-COM-001

[§4.3 · printed 109 / PDF 120](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)

Table/context: Hearing: clinical assessment and audiometry

> Compliance with the standard should be clinically 
> assessed initially. If the initial clinical assessment 
> indicates possible hearing loss, the person should 
> be referred for audiometry.

PDF region: (320.0, 273.0, 531.0, 325.0); text SHA-256: `658c8e0d61ff7a066d001e669c6673a4dca8fd439d85009a8ecef07432d5ddbb`.

### AFTD2022-HEAR-COM-002

[§4.3 · printed 109 / PDF 120](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)

Table/context: Hearing: unaided four-frequency average

> A person is not fit to hold an unconditional licence:
> •	 if the person has unaided hearing loss ≥ 40 dB 
> in the better ear (averaged over the frequencies 
> 0.5, 1, 2 and 3 KHz).

PDF region: (320.0, 327.0, 531.0, 385.0); text SHA-256: `78ef0b09576857072cbc395e26ad22ce08bd7e94bca53ee68bf36f48facb0b6a`.

### AFTD2022-HEAR-COM-003

[§4.3 · printed 109 / PDF 120](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)

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

[§4.3 · printed 109 / PDF 120](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)

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

## Clinician checklist

- [ ] Clinician: review source facts, rule applicability and every provisional conclusion.
- [ ] Confirm the commercial driving task and assess conditions outside the five-module scope.
- [ ] Confirm missing/unverified case fact: hearing.clinical_assessment
- [ ] Confirm missing/unverified case fact: hearing.unaided_better_ear_average_db
- [ ] hearing.clinical_assessment
- [ ] hearing.unaided_better_ear_average_db

## Case source

```text
The driver reports no hearing loss during ordinary conversation, yet his partner says he has started missing the doorbell and radio calls; the employment form copied from last year says Hearing: normal, whereas the nurse observes repeated requests for instructions today and cannot decide whether background noise, equipment failure or a hearing problem explains the difference.

An unsigned worksheet records unaided better ear average 42 dB averaged over 0.5, 1, 2 and 3 kHz, but the driver remembers wearing both aids during that test and the worksheet's date is missing; the number should remain unconfirmed until the testing conditions and an audiologist's assessment are checked.

```

Input SHA-256: `912acea299a9fdca12def8557568cfc8db7083bf9ea40f4222374c5c3a4a7d81`
Rule-result SHA-256: `e55550e3c760760f04b4757e672083ec982b81c4079a708ee3869a6370e8ed7f`
Evidence-pack SHA-256: `bce1aaa28ed830dcfb744215ab29134ff324545b127683b8422a30961e9dbf87`
