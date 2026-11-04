# Clinical review draft — CX-LONG-056

CX-LONG-056: Insufficient information. 1 requested modules; 3 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

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

> The completed audiogram identifies unaided better-ear average hearing loss of 48 dB across 0.5, 1, 2 and 3 kHz, and the current clinical assessment records possible hearing loss; a hearing aid has been ordered rather than functionally assessed, the audiologist's advice about aided performance is not yet available, and the driver's belief that amplification will solve the difficulty is retained as an expectation rather than evidence that an aided standard has already been met.

- [AFTD2022-HEAR-COM-002, PDF 120](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)
- [AFTD2022-HEAR-COM-001, PDF 120](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)
- [AFTD2022-HEAR-COM-003, PDF 120](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)
- [AFTD2022-HEAR-COM-004, PDF 120](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=120)

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: Possible extraction issues require confirmation
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
Confirm hearing.audiometry.available (omission): Independent source reading differs from the extraction. The audiogram is explicitly mentioned in the passage, indicating that a formal audiogram is available.
Confirm hearing.clinical_assessment (omission): Independent source reading differs from the extraction. A screening impression of possible hearing_loss is a documented classification possible_hearing_loss, not confirmation of a measured hearing threshold.
Fields withheld from rule inputs: hearing.audiometry.available, hearing.clinical_assessment

### hearing.audiometry.available — omission

Independent source reading differs from the extraction. The audiogram is explicitly mentioned in the passage, indicating that a formal audiogram is available.

Source lines 5–5; characters 448:928
> The completed audiogram identifies unaided better-ear average hearing loss of 48 dB across 0.5, 1, 2 and 3 kHz, and the current clinical assessment records possible hearing loss; a hearing aid has been ordered rather than functionally assessed, the audiologist's advice about aided performance is not yet available, and the driver's belief that amplification will solve the difficulty is retained as an expectation rather than evidence that an aided standard has already been met.

### hearing.clinical_assessment — omission

Independent source reading differs from the extraction. A screening impression of possible hearing_loss is a documented classification possible_hearing_loss, not confirmation of a measured hearing threshold.

Source lines 5–5; characters 448:928
> The completed audiogram identifies unaided better-ear average hearing loss of 48 dB across 0.5, 1, 2 and 3 kHz, and the current clinical assessment records possible hearing loss; a hearing aid has been ordered rather than functionally assessed, the audiologist's advice about aided performance is not yet available, and the driver's belief that amplification will solve the difficulty is retained as an expectation rather than evidence that an aided standard has already been met.

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### HEAR-COM-AUDIOMETRY-MISSING-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.audiometry.available` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:928: The completed audiogram identifies unaided better-ear average hearing loss of 48 dB across 0.5, 1, 2 and 3 kHz, and the current clinical assessment records possible hearing loss; a hearing aid has been ordered rather than functionally assessed, the audiologist's advice about aided performance is not yet available, and the driver's belief that amplification will solve the difficulty is retained as an expectation rather than evidence that an aided standard has already been met.
- `hearing.clinical_assessment` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:928: The completed audiogram identifies unaided better-ear average hearing loss of 48 dB across 0.5, 1, 2 and 3 kHz, and the current clinical assessment records possible hearing loss; a hearing aid has been ordered rather than functionally assessed, the audiologist's advice about aided performance is not yet available, and the driver's belief that amplification will solve the difficulty is retained as an expectation rather than evidence that an aided standard has already been met.

Guideline sources: [AFTD2022-HEAR-COM-001](#aftd2022-hear-com-001)

### HEAR-COM-UNCONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.average_frequencies_khz` = UNKNOWN (unknown)
- `hearing.clinical_assessment` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 448:928: The completed audiogram identifies unaided better-ear average hearing loss of 48 dB across 0.5, 1, 2 and 3 kHz, and the current clinical assessment records possible hearing loss; a hearing aid has been ordered rather than functionally assessed, the audiologist's advice about aided performance is not yet available, and the driver's belief that amplification will solve the difficulty is retained as an expectation rather than evidence that an aided standard has already been met.
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
  - Source lines 5–5; chars 448:928: The completed audiogram identifies unaided better-ear average hearing loss of 48 dB across 0.5, 1, 2 and 3 kHz, and the current clinical assessment records possible hearing loss; a hearing aid has been ordered rather than functionally assessed, the audiologist's advice about aided performance is not yet available, and the driver's belief that amplification will solve the difficulty is retained as an expectation rather than evidence that an aided standard has already been met.
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
- [ ] Confirm hearing.audiometry.available (omission): Independent source reading differs from the extraction. The audiogram is explicitly mentioned in the passage, indicating that a formal audiogram is available.
- [ ] Confirm hearing.clinical_assessment (omission): Independent source reading differs from the extraction. A screening impression of possible hearing_loss is a documented classification possible_hearing_loss, not confirmation of a measured hearing threshold.
- [ ] Fields withheld from rule inputs: hearing.audiometry.available, hearing.clinical_assessment

## Case source

```text
Synthetic nurse note for software testing. No real patient data.

The nurse reviews a commercial driver's symptoms alongside information from a witness, the treating team and an older workplace form, because each source describes a different part of the story; the occupational record retains those differences and identifies completed current findings without turning a booking, a family account or a recollection into a measured patient result.

The completed audiogram identifies unaided better-ear average hearing loss of 48 dB across 0.5, 1, 2 and 3 kHz, and the current clinical assessment records possible hearing loss; a hearing aid has been ordered rather than functionally assessed, the audiologist's advice about aided performance is not yet available, and the driver's belief that amplification will solve the difficulty is retained as an expectation rather than evidence that an aided standard has already been met.

The driver alternates urban deliveries with a longer motorway leg and describes a busy depot where engine noise, glare and interrupted meals can complicate an account of symptoms; the nurse records the work setting as context, while keeping the dated clinical findings distinct from the driver's explanation for why a symptom might have occurred on that shift.

The nurse reads the summary back to the driver to check the chronology and separates agreement about the wording from verification of a medical finding, then attaches the identified clinical material; any decision about further investigation or work allocation remains for the reviewing professional, and the note itself does not certify that all relevant clinical questions have been answered.

```

Input SHA-256: `e80bfe93e21aa82d5202ebca0a50406df5dd348ea6842911f5c24edc48455153`
Rule-result SHA-256: `2da4570b2dc9a36427527df3a29b08b4fe7c42ec534ff684b5e37502420aa7f3`
Evidence-pack SHA-256: `b35b41166dd989ac339f543f1ef84fc0d28dd22b241569bd671f24ecefe51d15`
