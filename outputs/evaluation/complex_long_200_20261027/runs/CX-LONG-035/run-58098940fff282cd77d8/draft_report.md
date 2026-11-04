# Clinical review draft — CX-LONG-035

CX-LONG-035: Insufficient information. 1 requested modules; 3 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| hearing | Insufficient information | human_review | 3 |

## Established rule findings

No rule criteria were established from the available verified facts. This does not establish absence of disease or failure of retrieval.


## Information coverage

- hearing: No source-supported facts for this requested module; some facts require confirmation; 0 supported fields; 3 unresolved rule fields.

## Retrieval activity

Rule-scoped ranking calls: 5.
Symptom discovery searches: 1.
Zero triggered rules does not mean retrieval failed. Retrieved text is not a diagnosis.

### hearing symptom retrieval

> The current clinician's recorded hearing assessment finds no hearing loss after examining the driver in suitable conditions, although yesterday's radio conversation was difficult when the cab speaker crackled and the windows were open; a colleague who uses hearing aids is mentioned in the same discussion, but those aids belong to the colleague, and an undated employer checklist is not used to replace today's completed clinical assessment.

- [AFTD2022-HEAR-COM-004, PDF 120](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)
- [AFTD2022-HEAR-COM-003, PDF 120](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)
- [AFTD2022-HEAR-COM-001, PDF 120](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)
- [AFTD2022-HEAR-COM-002, PDF 120](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: Possible extraction issues require confirmation
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
Confirm hearing.audiometry.available (omission): Independent source reading differs from the extraction. The question is about the availability of a formal audiogram, not the quality or interpretation of the audiogram. The answer is based on the explicit information provided in the source passages, not the audiogram itself. The audiogram is not explicitly mentioned as unavailable or not performed in any of the source passages. Therefore, the answer is documented as true.
Confirm hearing.clinical_assessment (contradiction): Independent source reading differs from the extraction. A screening impression of possible hearing_loss is a documented classification possible_hearing_loss, not confirmation of a measured hearing threshold.
Confirm hearing.hearing_aid_used (unsupported): Independent source reading differs from the extraction. There is no information provided about the patient's use of a hearing aid.
Fields withheld from rule inputs: hearing.audiometry.available, hearing.clinical_assessment, hearing.hearing_aid_used

### hearing.audiometry.available — omission

Independent source reading differs from the extraction. The question is about the availability of a formal audiogram, not the quality or interpretation of the audiogram. The answer is based on the explicit information provided in the source passages, not the audiogram itself. The audiogram is not explicitly mentioned as unavailable or not performed in any of the source passages. Therefore, the answer is documented as true.

Source lines 5–5; characters 436:878
> The current clinician's recorded hearing assessment finds no hearing loss after examining the driver in suitable conditions, although yesterday's radio conversation was difficult when the cab speaker crackled and the windows were open; a colleague who uses hearing aids is mentioned in the same discussion, but those aids belong to the colleague, and an undated employer checklist is not used to replace today's completed clinical assessment.

### hearing.clinical_assessment — contradiction

Independent source reading differs from the extraction. A screening impression of possible hearing_loss is a documented classification possible_hearing_loss, not confirmation of a measured hearing threshold.

Source lines 1–1; characters 0:64
> Synthetic nurse note for software testing. No real patient data.

### hearing.hearing_aid_used — unsupported

Independent source reading differs from the extraction. There is no information provided about the patient's use of a hearing aid.

Source lines 5–5; characters 688:705
> uses hearing aids

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### HEAR-COM-AUDIOMETRY-MISSING-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.audiometry.available` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 436:878: The current clinician's recorded hearing assessment finds no hearing loss after examining the driver in suitable conditions, although yesterday's radio conversation was difficult when the cab speaker crackled and the windows were open; a colleague who uses hearing aids is mentioned in the same discussion, but those aids belong to the colleague, and an undated employer checklist is not used to replace today's completed clinical assessment.
- `hearing.clinical_assessment` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 494:509: no hearing loss
  - Source lines 5–5; chars 436:509: The current clinician's recorded hearing assessment finds no hearing loss
  - Source lines 1–1; chars 0:64: Synthetic nurse note for software testing. No real patient data.

Guideline sources: [AFTD2022-HEAR-COM-001](#aftd2022-hear-com-001)

### HEAR-COM-UNCONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.average_frequencies_khz` = UNKNOWN (unknown)
- `hearing.clinical_assessment` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 494:509: no hearing loss
  - Source lines 5–5; chars 436:509: The current clinician's recorded hearing assessment finds no hearing loss
  - Source lines 1–1; chars 0:64: Synthetic nurse note for software testing. No real patient data.
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
  - Source lines 5–5; chars 494:509: no hearing loss
  - Source lines 5–5; chars 436:509: The current clinician's recorded hearing assessment finds no hearing loss
  - Source lines 1–1; chars 0:64: Synthetic nurse note for software testing. No real patient data.
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
- [ ] Confirm hearing.audiometry.available (omission): Independent source reading differs from the extraction. The question is about the availability of a formal audiogram, not the quality or interpretation of the audiogram. The answer is based on the explicit information provided in the source passages, not the audiogram itself. The audiogram is not explicitly mentioned as unavailable or not performed in any of the source passages. Therefore, the answer is documented as true.
- [ ] Confirm hearing.clinical_assessment (contradiction): Independent source reading differs from the extraction. A screening impression of possible hearing_loss is a documented classification possible_hearing_loss, not confirmation of a measured hearing threshold.
- [ ] Confirm hearing.hearing_aid_used (unsupported): Independent source reading differs from the extraction. There is no information provided about the patient's use of a hearing aid.
- [ ] Fields withheld from rule inputs: hearing.audiometry.available, hearing.clinical_assessment, hearing.hearing_aid_used

## Case source

```text
Synthetic nurse note for software testing. No real patient data.

During a commercial-driver review after a refrigerated-freight run, the nurse brings together the driver's account, a dated clinical attachment and an employer form copied from an earlier assessment; the documents refer to different times, and the current entry distinguishes a completed examination from recollections, plans and information concerning another person.

The current clinician's recorded hearing assessment finds no hearing loss after examining the driver in suitable conditions, although yesterday's radio conversation was difficult when the cab speaker crackled and the windows were open; a colleague who uses hearing aids is mentioned in the same discussion, but those aids belong to the colleague, and an undated employer checklist is not used to replace today's completed clinical assessment.

The driver alternates urban deliveries with a longer motorway leg and describes a busy depot where engine noise, glare and interrupted meals can complicate an account of symptoms; the nurse records the work setting as context, while keeping the dated clinical findings distinct from the driver's explanation for why a symptom might have occurred on that shift.

Before closing the interview, the nurse checks that the driver's recollection and the supplied clinical document have not been merged into a single undated finding, and records the outstanding documents separately; the completed entries remain current findings, while any missing qualification, conflicting detail or unperformed examination stays available for review rather than being silently treated as normal.

```

Input SHA-256: `767c6e485d7c982f321bf138d7cddf189a0e563814f1f877f1883439af8f201f`
Rule-result SHA-256: `9e9ff5939b8f64e3161fc3c631c3201294437e6834ed58bf073287dead53ee84`
Evidence-pack SHA-256: `bc67a41f0e16b9ba9cf7d4a9599b8735855581a951a28e0fb69a51ddef053ca7`
