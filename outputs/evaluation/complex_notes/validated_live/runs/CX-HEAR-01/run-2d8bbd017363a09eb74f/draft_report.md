# Clinical review draft — CX-HEAR-01

CX-HEAR-01: Insufficient information. 1 requested modules; 3 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| hearing | Insufficient information | human_review | 3 |

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: Possible extraction issues require confirmation
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
Confirm hearing.hearing_aid_used (unsupported): Independent source reading differs from the extraction. The patient uses hearing aids inconsistently because one whistles, but it is not explicitly stated whether they were used during the audiometry test.
Confirm hearing.audiometry.available (omission): Independent source reading differs from the extraction. The patient has a phone photograph showing audiometry results, but it is incomplete and does not indicate whether an aid was worn.
Confirm hearing.ent_or_audiologist_information_available (omission): Independent source reading differs from the extraction. The patient's audiologist's signed report is requested, but not yet available.
Fields withheld from rule inputs: hearing.audiometry.available, hearing.ent_or_audiologist_information_available, hearing.hearing_aid_used

### hearing.hearing_aid_used — unsupported

Independent source reading differs from the extraction. The patient uses hearing aids inconsistently because one whistles, but it is not explicitly stated whether they were used during the audiometry test.

Source lines 1–1; characters 246:263
> uses hearing aids

### hearing.audiometry.available — omission

Independent source reading differs from the extraction. The patient has a phone photograph showing audiometry results, but it is incomplete and does not indicate whether an aid was worn.

Source lines 3–3; characters 397:572
> A phone photograph shows 35 dB at 500 Hz and 50 dB at 1000 Hz without an identified ear, with the 2000 and 3000 Hz values cut off and no indication of whether an aid was worn;

### hearing.ent_or_audiologist_information_available — omission

Independent source reading differs from the extraction. The patient's audiologist's signed report is requested, but not yet available.

Source lines 3–3; characters 695:745
> the audiologist's signed report has been requested

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### HEAR-COM-AUDIOMETRY-MISSING-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.audiometry.available` = UNKNOWN (requires_confirmation)
  - Source lines 3–3; chars 397:572: A phone photograph shows 35 dB at 500 Hz and 50 dB at 1000 Hz without an identified ear, with the 2000 and 3000 Hz values cut off and no indication of whether an aid was worn;
- `hearing.clinical_assessment` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HEAR-COM-001](#aftd2022-hear-com-001)

### HEAR-COM-UNCONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.average_frequencies_khz` = UNKNOWN (unknown)
- `hearing.clinical_assessment` = UNKNOWN (unknown)
- `hearing.unaided_better_ear_average_db` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HEAR-COM-002](#aftd2022-hear-com-002)

### HEAR-COM-CONDITIONAL-AID-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.aided_standard_met` = UNKNOWN (unknown)
- `hearing.ent_or_audiologist_information_available` = UNKNOWN (requires_confirmation)
  - Source lines 3–3; chars 695:745: the audiologist's signed report has been requested

Guideline sources: [AFTD2022-HEAR-COM-003](#aftd2022-hear-com-003)

### HEAR-COM-INDIVIDUAL-ASSESSMENT-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.aided_standard_met` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HEAR-COM-004](#aftd2022-hear-com-004)

### HEAR-COM-SCREEN-001 — unknown

Required facts are unknown or unconfirmed.

- `hearing.average_frequencies_khz` = UNKNOWN (unknown)
- `hearing.clinical_assessment` = UNKNOWN (unknown)
- `hearing.unaided_better_ear_average_db` = UNKNOWN (unknown)

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
- [ ] Confirm missing/unverified case fact: hearing.average_frequencies_khz
- [ ] Confirm missing/unverified case fact: hearing.clinical_assessment
- [ ] Confirm missing/unverified case fact: hearing.unaided_better_ear_average_db
- [ ] requires_confirmation
- [ ] Extraction semantic review: Possible extraction issues require confirmation
- [ ] This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
- [ ] Confirm hearing.hearing_aid_used (unsupported): Independent source reading differs from the extraction. The patient uses hearing aids inconsistently because one whistles, but it is not explicitly stated whether they were used during the audiometry test.
- [ ] Confirm hearing.audiometry.available (omission): Independent source reading differs from the extraction. The patient has a phone photograph showing audiometry results, but it is incomplete and does not indicate whether an aid was worn.
- [ ] Confirm hearing.ent_or_audiologist_information_available (omission): Independent source reading differs from the extraction. The patient's audiologist's signed report is requested, but not yet available.
- [ ] Fields withheld from rule inputs: hearing.audiometry.available, hearing.ent_or_audiologist_information_available, hearing.hearing_aid_used

## Case source

```text
The driver can follow a quiet face-to-face conversation but repeatedly asks dispatch to repeat radio instructions when the engine is running, turns his left ear toward the nurse and says the reversing alarm seems much quieter than last month; he uses hearing aids inconsistently because one whistles, although being able to hear the nurse today does not establish an unaided hearing threshold.

A phone photograph shows 35 dB at 500 Hz and 50 dB at 1000 Hz without an identified ear, with the 2000 and 3000 Hz values cut off and no indication of whether an aid was worn; the nurse therefore cannot calculate an unaided better-ear average or regard this photograph as a complete audiogram, and the audiologist's signed report has been requested.

```

Input SHA-256: `3d34ea9896edc0c207f877385e10cdaf8eb24c3bafa9e32b1079fd29f86f8831`
Rule-result SHA-256: `d8b3af22dfd52f3e1af042580b72a5f66332deb08cd45b787f3f042ded043a54`
Evidence-pack SHA-256: `80adab6b6f7451944baafbbf702b509a4c56ada8b40c7574ceb9206cf2129c43`
