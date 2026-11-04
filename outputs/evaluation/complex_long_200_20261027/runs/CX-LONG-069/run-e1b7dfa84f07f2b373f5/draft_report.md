# Clinical review draft — CX-LONG-069

CX-LONG-069: Insufficient information. 2 requested modules; 3 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| hypertension | Insufficient information | human_review | 2 |
| blackout | Insufficient information | human_review | 1 |

## Established rule findings

No rule criteria were established from the available verified facts. This does not establish absence of disease or failure of retrieval.


## Information coverage

- hypertension: No source-supported facts for this requested module; some facts require confirmation; 0 supported fields; 2 unresolved rule fields.
- blackout: Source-supported facts available; some facts require confirmation; 1 supported fields; 1 unresolved rule fields.

## Retrieval activity

Rule-scoped ranking calls: 7.
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

> The driver restarted antihypertensive tablets twelve days ago after a period of missed doses, and the current clinic letter still records persistent BP 179/103 mmHg on repeat checks; a four-week follow-up period has not yet been completed, the driver brings a booking confirmation rather than a specialist opinion, and occasional improvement on a home display cannot establish sustained control or the absence of relevant treatment problems.

- [AFTD2022-HTN-COM-002, PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)
- [AFTD2022-HTN-COM-001, PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: Possible extraction issues require confirmation
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
Confirm blackout.occurred (omission): Independent source reading differs from the extraction. The source passage 4 explicitly reports a witnessed blackout with loss of consciousness during a break, and the mechanism is under investigation.
Confirm cardiovascular.blood_pressure.observed_diastolic (unsupported): Independent source reading differs from the extraction. The passages do not provide a direct measurement of the patient's diastolic blood pressure.
Confirm cardiovascular.blood_pressure.observed_systolic (unsupported): Independent source reading differs from the extraction. The patient fact is not mentioned in the provided source passages.
Confirm cardiovascular.blood_pressure.persistent_diastolic (unsupported): Independent source reading differs from the extraction. The patient fact 'cardiovascular.blood_pressure.persistent_diastolic' is not documented in the provided source passages.
Confirm cardiovascular.blood_pressure.persistent_systolic (unsupported): Independent source reading differs from the extraction. The patient fact 'cardiovascular.blood_pressure.persistent_systolic' is not documented in the provided source passages.
Fields withheld from rule inputs: blackout.occurred, cardiovascular.blood_pressure.observed_diastolic, cardiovascular.blood_pressure.observed_systolic, cardiovascular.blood_pressure.persistent_diastolic, cardiovascular.blood_pressure.persistent_systolic

### blackout.occurred — omission

Independent source reading differs from the extraction. The source passage 4 explicitly reports a witnessed blackout with loss of consciousness during a break, and the mechanism is under investigation.

Source lines 9–9; characters 1254:1568
> A separate current referral documents a witnessed blackout with loss of consciousness during a break and states that the mechanism is under investigation; the driver remembers feeling hot before the event, but neither a benign faint nor a metabolic cause has been confirmed, and cardiac monitoring remains pending.

### cardiovascular.blood_pressure.observed_diastolic — unsupported

Independent source reading differs from the extraction. The passages do not provide a direct measurement of the patient's diastolic blood pressure.

Source lines 5–5; characters 591:606
> BP 179/103 mmHg

### cardiovascular.blood_pressure.observed_systolic — unsupported

Independent source reading differs from the extraction. The patient fact is not mentioned in the provided source passages.

Source lines 5–5; characters 591:606
> BP 179/103 mmHg

### cardiovascular.blood_pressure.persistent_diastolic — unsupported

Independent source reading differs from the extraction. The patient fact 'cardiovascular.blood_pressure.persistent_diastolic' is not documented in the provided source passages.

Source lines 5–5; characters 580:606
> persistent BP 179/103 mmHg

### cardiovascular.blood_pressure.persistent_systolic — unsupported

Independent source reading differs from the extraction. The patient fact 'cardiovascular.blood_pressure.persistent_systolic' is not documented in the provided source passages.

Source lines 5–5; characters 580:606
> persistent BP 179/103 mmHg

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### HTN-COM-UNCONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `cardiovascular.blood_pressure.persistent_diastolic` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 580:606: persistent BP 179/103 mmHg
  - Source lines 5–5; chars 580:606: persistent BP 179/103 mmHg
- `cardiovascular.blood_pressure.persistent_systolic` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 580:606: persistent BP 179/103 mmHg
  - Source lines 5–5; chars 580:606: persistent BP 179/103 mmHg

Guideline sources: [AFTD2022-HTN-COM-001](#aftd2022-htn-com-001)

### HTN-COM-CONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `cardiovascular.hypertension.antihypertensive_therapy` = UNKNOWN (unknown)
- `cardiovascular.hypertension.controlled_for_4_weeks` = UNKNOWN (unknown)
- `cardiovascular.hypertension.driving_impairing_medication_side_effects` = UNKNOWN (unknown)
- `cardiovascular.hypertension.initial_specialist_information_available` = UNKNOWN (unknown)
- `cardiovascular.hypertension.target_organ_damage_relevant_to_driving` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-HTN-COM-002](#aftd2022-htn-com-002)

### BLK-COM-UNDIAGNOSED-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.mechanism_status` = under_investigation (present)
  - Source lines 9–9; chars 1371:1407: the mechanism is under investigation
  - Source lines 9–9; chars 1254:1409: A separate current referral documents a witnessed blackout with loss of consciousness during a break and states that the mechanism is under investigation; 
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 9–9; chars 1254:1568: A separate current referral documents a witnessed blackout with loss of consciousness during a break and states that the mechanism is under investigation; the driver remembers feeling hot before the event, but neither a benign faint nor a metabolic cause has been confirmed, and cardiac monitoring remains pending.

Guideline sources: [AFTD2022-BLK-COM-001](#aftd2022-blk-com-001)

### BLK-COM-VASOVAGAL-EXCEPTION-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.diagnosis` = UNKNOWN (unknown)
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 9–9; chars 1254:1568: A separate current referral documents a witnessed blackout with loss of consciousness during a break and states that the mechanism is under investigation; the driver remembers feeling hot before the event, but neither a benign faint nor a metabolic cause has been confirmed, and cardiac monitoring remains pending.
- `blackout.provoking_factor_well_defined` = UNKNOWN (unknown)
- `blackout.recurrence_while_driving_unlikely` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-BLK-COM-002](#aftd2022-blk-com-002)

### HTN-COM-SCREEN-001 — unknown

Required facts are unknown or unconfirmed.

- `cardiovascular.blood_pressure.persistent_diastolic` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 580:606: persistent BP 179/103 mmHg
  - Source lines 5–5; chars 580:606: persistent BP 179/103 mmHg
- `cardiovascular.blood_pressure.persistent_systolic` = UNKNOWN (requires_confirmation)
  - Source lines 5–5; chars 580:606: persistent BP 179/103 mmHg
  - Source lines 5–5; chars 580:606: persistent BP 179/103 mmHg

Guideline sources: [AFTD2022-HTN-COM-001](#aftd2022-htn-com-001)

### BLK-COM-NO-HISTORY-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 9–9; chars 1254:1568: A separate current referral documents a witnessed blackout with loss of consciousness during a break and states that the mechanism is under investigation; the driver remembers feeling hot before the event, but neither a benign faint nor a metabolic cause has been confirmed, and cardiac monitoring remains pending.

Guideline sources: [AFTD2022-BLK-COM-001](#aftd2022-blk-com-001)

### BLK-COM-DIAGNOSED-REFERRAL-001 — unknown

Required facts are unknown or unconfirmed.

- `blackout.diagnosis` = UNKNOWN (unknown)
- `blackout.occurred` = UNKNOWN (requires_confirmation)
  - Source lines 9–9; chars 1254:1568: A separate current referral documents a witnessed blackout with loss of consciousness during a break and states that the mechanism is under investigation; the driver remembers feeling hot before the event, but neither a benign faint nor a metabolic cause has been confirmed, and cardiac monitoring remains pending.

Guideline sources: [AFTD2022-BLK-COM-006](#aftd2022-blk-com-006)

## Guideline evidence

### AFTD2022-HTN-COM-001

[§2.3.1 · printed 88 / PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)

Table/context: Hypertension: unconditional

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has blood pressure 
> consistently > 170 systolic or > 100 diastolic 
> (treated or untreated).

PDF region: (345.0, 177.0, 530.0, 247.0); text SHA-256: `eeacf5b9430b10bb961f6b727f6b4eb638baaf8aeecde7413ad4b4dea2baef7d`.

### AFTD2022-HTN-COM-002

[§2.3.1 · printed 88 / PDF 99](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=99)

Table/context: Hypertension: conditional and specialist footnote

> A conditional licence may be considered 
> by the driver licensing authority subject to 
> annual review, taking into account the nature 
> of the driving task and information provided 
> by the treating specialist* as to whether the 
> following criteria are met:
> •	 the person is treated with antihypertensive 
> therapy and effective control of 
> hypertension is achieved over a 4-week 
> follow-up period; and
> •	 there are no side effects from the 
> medication that will impair safe driving; and
> •	 there is no evidence of damage to target 
> organs relevant to driving.
> * Ongoing fitness to drive for commercial 
> vehicle drivers may be assessed by the 
> treating GP provided this is mutually agreed 
> by the specialist, GP and driver licensing 
> authority. The initial granting of a conditional 
> licence must, however, be based on 
> information provided by the specialist.

PDF region: (345.0, 248.0, 530.0, 528.0); text SHA-256: `d83f41571c48dc3b7c6033b230f17179c3146235732afd0f232960104543dc22`.

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
- [ ] Confirm missing/unverified case fact: cardiovascular.blood_pressure.persistent_diastolic
- [ ] Confirm missing/unverified case fact: cardiovascular.blood_pressure.persistent_systolic
- [ ] requires_confirmation
- [ ] Extraction semantic review: Possible extraction issues require confirmation
- [ ] This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.
- [ ] Confirm blackout.occurred (omission): Independent source reading differs from the extraction. The source passage 4 explicitly reports a witnessed blackout with loss of consciousness during a break, and the mechanism is under investigation.
- [ ] Confirm cardiovascular.blood_pressure.observed_diastolic (unsupported): Independent source reading differs from the extraction. The passages do not provide a direct measurement of the patient's diastolic blood pressure.
- [ ] Confirm cardiovascular.blood_pressure.observed_systolic (unsupported): Independent source reading differs from the extraction. The patient fact is not mentioned in the provided source passages.
- [ ] Confirm cardiovascular.blood_pressure.persistent_diastolic (unsupported): Independent source reading differs from the extraction. The patient fact 'cardiovascular.blood_pressure.persistent_diastolic' is not documented in the provided source passages.
- [ ] Confirm cardiovascular.blood_pressure.persistent_systolic (unsupported): Independent source reading differs from the extraction. The patient fact 'cardiovascular.blood_pressure.persistent_systolic' is not documented in the provided source passages.
- [ ] Fields withheld from rule inputs: blackout.occurred, cardiovascular.blood_pressure.observed_diastolic, cardiovascular.blood_pressure.observed_systolic, cardiovascular.blood_pressure.persistent_diastolic, cardiovascular.blood_pressure.persistent_systolic

## Case source

```text
Synthetic nurse note for software testing. No real patient data.

In a commercial-driver follow-up arranged after an occupational screening concern, the nurse interviews the driver and checks the accompanying documents against the reported sequence of events; the employer wants a quick answer before allocating a vehicle, but the record separates present evidence, historical findings and questions that the clinician has not yet resolved.

The driver restarted antihypertensive tablets twelve days ago after a period of missed doses, and the current clinic letter still records persistent BP 179/103 mmHg on repeat checks; a four-week follow-up period has not yet been completed, the driver brings a booking confirmation rather than a specialist opinion, and occasional improvement on a home display cannot establish sustained control or the absence of relevant treatment problems.

The interview takes place before the driver's next planned roster, and the nurse records changes in symptoms, treatment and available documents without assuming that a future specialist appointment has already occurred; any letter that has been requested but not supplied remains separate from the findings actually available when this occupational record is written.

A separate current referral documents a witnessed blackout with loss of consciousness during a break and states that the mechanism is under investigation; the driver remembers feeling hot before the event, but neither a benign faint nor a metabolic cause has been confirmed, and cardiac monitoring remains pending.

For the occupational reviewer, the nurse retains both the definite findings and the limitations of the available account, including the timing and testing conditions where they matter, rather than producing a single reassuring label; the driver is told which information is on file and which details still require confirmation, without replacing the recorded clinical evidence with an employer's preference.

```

Input SHA-256: `dd242a815ad24235f1784636ac1dbd56616a2030e411224c1b8d9e84819a0018`
Rule-result SHA-256: `515d02430382d487e6488aa4060976d37c4fd93f46058164aa57ded302335eb1`
Evidence-pack SHA-256: `01cd93f4fac063b207d4bc3b05c0767d26c537288ce13ea7871505bd17e65a19`
