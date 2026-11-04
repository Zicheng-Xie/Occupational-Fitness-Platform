# Clinical review draft — CX-LONG-098

CX-LONG-098: Insufficient information. 1 requested modules; 6 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| diabetes | Insufficient information | missing_information | 6 |

## Established rule findings

No rule criteria were established from the available verified facts. This does not establish absence of disease or failure of retrieval.


## Information coverage

- diabetes: Source-supported facts available; 2 supported fields; 6 unresolved rule fields.

## Retrieval activity

Rule-scoped ranking calls: 4.
Symptom discovery searches: 1.
Zero triggered rules does not mean retrieval failed. Retrieved text is not a diagnosis.

### diabetes symptom retrieval

> The current GP and medication review confirm established type 2 diabetes managed by diet and exercise alone, with no glucose-lowering medicine or insulin prescribed, and document that driving-relevant comorbidities have been assessed with no disqualifying effect; the driver mentions that an uncle uses injections, but those medicines belong to the uncle, and a previous referral proposing tablets was never implemented as a current treatment change.

- [AFTD2022-DM-COM-006, PDF 112](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=112)
- [AFTD2022-DM-COM-004, PDF 112](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=112)
- [AFTD2022-DM-COM-008, PDF 113](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=113)
- [AFTD2022-DM-COM-005, PDF 112](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=112)
- [AFTD2022-DM-COM-009, PDF 110](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=110)

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: No issues flagged by the model
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### DM-COM-DIET-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.driving_relevant_comorbidity_status` = UNKNOWN (unknown)
- `diabetes.present` = True (present)
  - Source lines 5–5; chars 448:712: The current GP and medication review confirm established type 2 diabetes managed by diet and exercise alone, with no glucose-lowering medicine or insulin prescribed, and document that driving-relevant comorbidities have been assessed with no disqualifying effect; 
  - Source lines 5–5; chars 448:520: The current GP and medication review confirm established type 2 diabetes
- `diabetes.treatment_category` = diet_and_exercise_only (present)
  - Source lines 5–5; chars 512:555: diabetes managed by diet and exercise alone

Guideline sources: [AFTD2022-DM-COM-004](#aftd2022-dm-com-004)

### DM-COM-SEVERE-HYPO-WAIT-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.present` = True (present)
  - Source lines 5–5; chars 448:712: The current GP and medication review confirm established type 2 diabetes managed by diet and exercise alone, with no glucose-lowering medicine or insulin prescribed, and document that driving-relevant comorbidities have been assessed with no disqualifying effect; 
  - Source lines 5–5; chars 448:520: The current GP and medication review confirm established type 2 diabetes
- `diabetes.severe_hypoglycaemic_event.occurred` = UNKNOWN (unknown)
- `diabetes.severe_hypoglycaemic_event.weeks_since_last` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-002](#aftd2022-dm-com-002)

### DM-COM-ACUTE-UNSTABLE-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.acutely_unwell` = UNKNOWN (unknown)
- `diabetes.metabolically_unstable` = UNKNOWN (unknown)
- `diabetes.present` = True (present)
  - Source lines 5–5; chars 448:712: The current GP and medication review confirm established type 2 diabetes managed by diet and exercise alone, with no glucose-lowering medicine or insulin prescribed, and document that driving-relevant comorbidities have been assessed with no disqualifying effect; 
  - Source lines 5–5; chars 448:520: The current GP and medication review confirm established type 2 diabetes

Guideline sources: [AFTD2022-DM-COM-003](#aftd2022-dm-com-003)

### DM-COM-GESTATIONAL-REVIEW-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.gestational` = UNKNOWN (unknown)
- `diabetes.present` = True (present)
  - Source lines 5–5; chars 448:712: The current GP and medication review confirm established type 2 diabetes managed by diet and exercise alone, with no glucose-lowering medicine or insulin prescribed, and document that driving-relevant comorbidities have been assessed with no disqualifying effect; 
  - Source lines 5–5; chars 448:520: The current GP and medication review confirm established type 2 diabetes

Guideline sources: [AFTD2022-DM-COM-010](#aftd2022-dm-com-010)

## Guideline evidence

### AFTD2022-DM-COM-004

[§3.3 · printed 101 / PDF 112](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=112)

Table/context: Diet and exercise alone

> A person with diabetes treated by diet and 
> exercise alone may drive without licence 
> restriction. They should he reviewed by their 
> treating doctor periodically regarding the 
> progression of their diabetes.

PDF region: (341.0, 208.0, 532.0, 272.0); text SHA-256: `e87d5bc28480bb50a71749bee7186b0af2c922f6ac566d6db2a43313cad68e8c`.

### AFTD2022-DM-COM-002

[§3.2.1 · printed 94 / PDF 105](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=105)

Table/context: Severe hypoglycaemia non-driving guidance

> Non-driving period after a ‘severe 
> hypoglycaemic event’
> If a severe hypoglycaemic event occurs (as 
> defined in section 3.2.1. Hypoglycaemia), the 
> person should not drive for a significant period 
> of time and will need to be urgently assessed. 
> The minimum period of time before returning 
> to drive is generally six weeks because it often 
> takes many weeks for patterns of glucose 
> control and behaviour to be re-established and 
> for any temporary ‘impaired hypoglycaemia 
> awareness’ to resolve (see below). The non-
> driving period will depend on factors such 
> as identifying the reason for the episode, the 
> specialist’s opinion and the type of motor vehicle 
> licence. The specialist’s recommendation for 
> returning to driving should be based on the 
> patient’s behaviour and objective measures of 
> glycaemic control (documented blood glucose) 
> over a reasonable interval. 
> Impaired hypoglycaemic awareness 10–14

PDF region: (55.0, 50.0, 294.0, 422.0); text SHA-256: `04a88c68536b1ff96803f0262cf8f0f63687a419e4600ceef88ee0e623b06069`.

### AFTD2022-DM-COM-003

[§3.2.2 · printed 95 / PDF 106](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=106)

Table/context: Acute metabolic instability

> 3.2.2. Acute hyperglycaemia
> While acute hyperglycaemia may affect some 
> aspects of brain function, there is not enough 
> evidence to determine the regular effects on 
> driving performance and related crash risk. Each 
> person with diabetes should be counselled 
> about managing their diabetes during days 
> when they are unwell and should be advised 
> not to drive if they are acutely unwell with 
> metabolically unstable diabetes.

PDF region: (55.0, 265.0, 294.0, 438.0); text SHA-256: `0ba4927e7248164977d80cbeb75c7ce270e2ccd2fd071e70b41323db1ee10cda`.

### AFTD2022-DM-COM-010

[§3.2.4 · printed 96 / PDF 107](../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=107)

Table/context: Gestational diabetes

> 3.2.4. Gestational diabetes mellitus
> The standards in this chapter apply to diabetes 
> mellitus as a chronic condition. The self-limiting 
> condition known as gestational diabetes 
> mellitus does not affect licensing. However, 
> consideration should be given to short-term 
> fitness to drive in women with gestational 
> diabetes mellitus treated with insulin, although 
> severe hypoglycaemia in this condition is rare. 
> Affected women should be counselled to 
> recognise symptoms and to restrict driving when 
> symptoms occur.

PDF region: (55.0, 50.0, 295.0, 282.0); text SHA-256: `8499e71512aec0eb89dca54bbf02a9ba1570e783118d3a618c3e9a303377ac3f`.

## Clinician checklist

- [ ] Clinician: review source facts, rule applicability and every provisional conclusion.
- [ ] Confirm the commercial driving task and assess conditions outside the five-module scope.
- [ ] Confirm missing/unverified case fact: diabetes.acutely_unwell
- [ ] Confirm missing/unverified case fact: diabetes.driving_relevant_comorbidity_status
- [ ] Confirm missing/unverified case fact: diabetes.gestational
- [ ] Confirm missing/unverified case fact: diabetes.metabolically_unstable
- [ ] Confirm missing/unverified case fact: diabetes.severe_hypoglycaemic_event.occurred
- [ ] Confirm missing/unverified case fact: diabetes.severe_hypoglycaemic_event.weeks_since_last

## Case source

```text
Synthetic nurse note for software testing. No real patient data.

The nurse reviews a commercial driver's symptoms alongside information from a witness, the treating team and an older workplace form, because each source describes a different part of the story; the occupational record retains those differences and identifies completed current findings without turning a booking, a family account or a recollection into a measured patient result.

The current GP and medication review confirm established type 2 diabetes managed by diet and exercise alone, with no glucose-lowering medicine or insulin prescribed, and document that driving-relevant comorbidities have been assessed with no disqualifying effect; the driver mentions that an uncle uses injections, but those medicines belong to the uncle, and a previous referral proposing tablets was never implemented as a current treatment change.

The usual work involves coupling trailers, checking mirrors, interpreting radio messages and responding to pedestrians in a loading area, with breaks that can be delayed when deliveries run late; the driver explains which difficulty occurred while stationary and which was noticed during ordinary duties, rather than claiming that quiet conversation in the clinic reproduces every task in the cab.

The nurse reads the summary back to the driver to check the chronology and separates agreement about the wording from verification of a medical finding, then attaches the identified clinical material; any decision about further investigation or work allocation remains for the reviewing professional, and the note itself does not certify that all relevant clinical questions have been answered.

```

Input SHA-256: `2f6fae9f03752cc71b32b52cfd738301aa0f9cfa984a9cf99fb900b3237fa459`
Rule-result SHA-256: `2cc2cc8e01cd5374d4e2cf93344fa1bed7ccbb7dac6d3f8cfba05b1f18496083`
Evidence-pack SHA-256: `8fc3551532dbd89d24507c7f97eda900c9d53e94e294095c2bd6d48b7143b900`
