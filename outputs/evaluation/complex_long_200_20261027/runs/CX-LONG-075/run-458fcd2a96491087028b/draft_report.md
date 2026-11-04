# Clinical review draft — CX-LONG-075

CX-LONG-075: Insufficient information. 1 requested modules; 3 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| hearing | Insufficient information | human_review | 3 |

## Established rule findings

No rule criteria were established from the available verified facts. This does not establish absence of disease or failure of retrieval.


## Information coverage

- hearing: Source-supported facts available; some facts require confirmation; 1 supported fields; 3 unresolved rule fields.

## Retrieval activity

Rule-scoped ranking calls: 5.
Symptom discovery searches: 1.
Zero triggered rules does not mean retrieval failed. Retrieved text is not a diagnosis.

### hearing symptom retrieval

> The current nurse assessment records possible hearing loss after the driver repeatedly asks for spoken instructions to be repeated, while the driver explains that he can hear a television at home and an older employer form called his hearing satisfactory; audiometry has not been performed, the ENT appointment is booked rather than completed, and no quantified unaided threshold or qualified aided assessment is available to resolve the disagreement.

- [AFTD2022-HEAR-COM-004, PDF 120](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)
- [AFTD2022-HEAR-COM-003, PDF 120](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)
- [AFTD2022-HEAR-COM-001, PDF 120](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)
- [AFTD2022-HEAR-COM-002, PDF 120](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: Possible extraction issues require confirmation
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
Confirm hearing.clinical_assessment (omission): Independent source reading differs from the extraction. A screening impression of possible hearing_loss is a documented classification possible_hearing_loss, not confirmation of a measured hearing threshold.
Fields withheld from rule inputs: hearing.clinical_assessment

### hearing.clinical_assessment — omission

Independent source reading differs from the extraction. A screening impression of possible hearing_loss is a documented classification possible_hearing_loss, not confirmation of a measured hearing threshold.

Source lines 5–5; characters 460:911
> The current nurse assessment records possible hearing loss after the driver repeatedly asks for spoken instructions to be repeated, while the driver explains that he can hear a television at home and an older employer form called his hearing satisfactory; audiometry has not been performed, the ENT appointment is booked rather than completed, and no quantified unaided threshold or qualified aided assessment is available to resolve the disagreement.

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### HEAR-COM-AUDIOMETRY-MISSING-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.audiometry.available` = False (present)
  - Source lines 5–6; chars 716:913: audiometry has not been performed, the ENT appointment is booked rather than completed, and no quantified unaided threshold or qualified aided assessment is available to resolve the disagreement.  
- `hearing.clinical_assessment` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 460:911: The current nurse assessment records possible hearing loss after the driver repeatedly asks for spoken instructions to be repeated, while the driver explains that he can hear a television at home and an older employer form called his hearing satisfactory; audiometry has not been performed, the ENT appointment is booked rather than completed, and no quantified unaided threshold or qualified aided assessment is available to resolve the disagreement.

Guideline sources: [AFTD2022-HEAR-COM-001](#aftd2022-hear-com-001)

### HEAR-COM-UNCONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.average_frequencies_khz` = UNKNOWN (unknown)
- `hearing.clinical_assessment` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 460:911: The current nurse assessment records possible hearing loss after the driver repeatedly asks for spoken instructions to be repeated, while the driver explains that he can hear a television at home and an older employer form called his hearing satisfactory; audiometry has not been performed, the ENT appointment is booked rather than completed, and no quantified unaided threshold or qualified aided assessment is available to resolve the disagreement.
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
  - Source lines 5–5; chars 460:911: The current nurse assessment records possible hearing loss after the driver repeatedly asks for spoken instructions to be repeated, while the driver explains that he can hear a television at home and an older employer form called his hearing satisfactory; audiometry has not been performed, the ENT appointment is booked rather than completed, and no quantified unaided threshold or qualified aided assessment is available to resolve the disagreement.
- `hearing.unaided_better_ear_average_db` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HEAR-COM-001](#aftd2022-hear-com-001), [AFTD2022-HEAR-COM-002](#aftd2022-hear-com-002)

## Guideline evidence

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

## Clinician checklist

- [ ] Clinician: review source facts, rule applicability and every provisional conclusion.
- [ ] Confirm the commercial driving task and assess conditions outside the five-module scope.
- [ ] Confirm missing/unverified case fact: hearing.average_frequencies_khz
- [ ] Confirm missing/unverified case fact: hearing.clinical_assessment
- [ ] Confirm missing/unverified case fact: hearing.unaided_better_ear_average_db
- [ ] requires_confirmation
- [ ] Extraction semantic review: Possible extraction issues require confirmation
- [ ] This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
- [ ] Confirm hearing.clinical_assessment (omission): Independent source reading differs from the extraction. A screening impression of possible hearing_loss is a documented classification possible_hearing_loss, not confirmation of a measured hearing threshold.
- [ ] Fields withheld from rule inputs: hearing.clinical_assessment

## Case source

```text
Synthetic nurse note for software testing. No real patient data.

The commercial driver attends after a long shift with a folder containing a current signed letter, older screening paperwork and a handwritten personal account, and the nurse reconstructs the chronology before recording the present findings; differences between the records are described explicitly rather than resolved by treating the newest-looking photocopy as automatically authoritative.

The current nurse assessment records possible hearing loss after the driver repeatedly asks for spoken instructions to be repeated, while the driver explains that he can hear a television at home and an older employer form called his hearing satisfactory; audiometry has not been performed, the ENT appointment is booked rather than completed, and no quantified unaided threshold or qualified aided assessment is available to resolve the disagreement.

Part of the usual route requires reversing near workers and reading changing signs before entering a customer site, although today's assessment takes place in a quiet room; the driver is asked to describe the sequence and timing of difficulties, and the note preserves the difference between an occupational concern, a suspected mechanism and a completed clinical assessment.

For the occupational reviewer, the nurse retains both the definite findings and the limitations of the available account, including the timing and testing conditions where they matter, rather than producing a single reassuring label; the driver is told which information is on file and which details still require confirmation, without replacing the recorded clinical evidence with an employer's preference.

```

Input SHA-256: `37f2887c42514e5b2ceda5e16f3332141a506fba5085b1369762070c8416eac6`
Rule-result SHA-256: `a9e656923cbe5c32060101ba58ab1b517c450018270b666c22ec48c34e361ebc`
Evidence-pack SHA-256: `2a83154c63f73621d1283a6b5c58cb95d8c735561396b12aa5b22cfbe5f89627`
