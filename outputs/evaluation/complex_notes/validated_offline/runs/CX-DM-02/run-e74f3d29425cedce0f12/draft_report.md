# Clinical review draft — CX-DM-02

CX-DM-02: Insufficient information. 1 requested modules; 2 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| diabetes | Insufficient information | missing_information | 2 |

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: Not performed (disabled)
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### DM-COM-DIET-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.driving_relevant_comorbidity_status` = UNKNOWN (unknown)
- `diabetes.present` = UNKNOWN (unknown)
- `diabetes.treatment_category` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-004](#aftd2022-dm-com-004)

### DM-COM-NONINSULIN-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.present` = UNKNOWN (unknown)
- `diabetes.treatment_category` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-005](#aftd2022-dm-com-005)

### DM-COM-NONINSULIN-CONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.driving_relevant_end_organ_effects` = UNKNOWN (unknown)
- `diabetes.hypoglycaemia_awareness` = UNKNOWN (unknown)
- `diabetes.initial_specialist_information_available` = UNKNOWN (unknown)
- `diabetes.present` = UNKNOWN (unknown)
- `diabetes.recent_severe_hypoglycaemic_event` = UNKNOWN (unknown)
- `diabetes.regimen_minimises_hypoglycaemia` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-006](#aftd2022-dm-com-006)

### DM-COM-INSULIN-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.gestational` = UNKNOWN (unknown)
- `diabetes.present` = UNKNOWN (unknown)
- `diabetes.treatment_category` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-007](#aftd2022-dm-com-007)

### DM-COM-SEVERE-HYPO-WAIT-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.present` = UNKNOWN (unknown)
- `diabetes.severe_hypoglycaemic_event.occurred` = UNKNOWN (unknown)
- `diabetes.severe_hypoglycaemic_event.weeks_since_last` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-002](#aftd2022-dm-com-002)

### DM-COM-INSULIN-CONDITIONAL-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.driving_relevant_end_organ_effects` = UNKNOWN (unknown)
- `diabetes.glucose_monitoring_records_months` = UNKNOWN (unknown)
- `diabetes.hypoglycaemia_awareness` = UNKNOWN (unknown)
- `diabetes.present` = UNKNOWN (unknown)
- `diabetes.recent_severe_hypoglycaemic_event` = UNKNOWN (unknown)
- `diabetes.regimen_minimises_hypoglycaemia` = UNKNOWN (unknown)
- `diabetes.severe_hypoglycaemic_event.occurred` = UNKNOWN (unknown)
- `diabetes.severe_hypoglycaemic_event.weeks_since_last` = UNKNOWN (unknown)
- `diabetes.specialist_information_available` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-008](#aftd2022-dm-com-008), [AFTD2022-DM-COM-009](#aftd2022-dm-com-009)

### DM-COM-ACUTE-UNSTABLE-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.acutely_unwell` = UNKNOWN (unknown)
- `diabetes.metabolically_unstable` = UNKNOWN (unknown)
- `diabetes.present` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-003](#aftd2022-dm-com-003)

### DM-COM-NO-HISTORY-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.present` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-001](#aftd2022-dm-com-001)

### DM-COM-GESTATIONAL-REVIEW-001 — unknown

Required facts are unknown or unconfirmed.

- `diabetes.gestational` = UNKNOWN (unknown)
- `diabetes.present` = UNKNOWN (unknown)

Guideline sources: [AFTD2022-DM-COM-010](#aftd2022-dm-com-010)

## Guideline evidence

### AFTD2022-DM-COM-004

[§3.3 · printed 101 / PDF 112](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=112)

Table/context: Diet and exercise alone

> A person with diabetes treated by diet and 
> exercise alone may drive without licence 
> restriction. They should he reviewed by their 
> treating doctor periodically regarding the 
> progression of their diabetes.

PDF region: (341.0, 208.0, 532.0, 272.0); text SHA-256: `e87d5bc28480bb50a71749bee7186b0af2c922f6ac566d6db2a43313cad68e8c`.

### AFTD2022-DM-COM-005

[§3.3 · printed 101 / PDF 112](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=112)

Table/context: Non-insulin agents: unconditional

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has non–insulin treated 
> diabetes mellitus and is being treated with 
> glucose-lowering agents other than insulin.

PDF region: (341.0, 286.0, 532.0, 355.0); text SHA-256: `fc60bdaa37f4ef12dea8c98a87935c4d4903f77cdb13b89aeeba9821dda0241f`.

### AFTD2022-DM-COM-006

[§3.3 · printed 101 / PDF 112](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=112)

Table/context: Non-insulin agents: conditional and specialist footnote

> A conditional licence may be considered 
> by the driver licensing authority subject to at 
> least annual review, taking into consideration 
> the nature of the driving task and information 
> provided by an endocrinologist or consultant 
> physician specialising in diabetes* on whether 
> the following criteria are met:
> •	 there is no recent history of a ‘severe 
> hypoglycaemic event’ as assessed by the 
> specialist; and
> •	 the person experiences early warning 
> symptoms (awareness) of hypoglycaemia; 
> and
> •	 the person is following a treatment regimen 
> that minimises the risk of hypoglycaemia; 
> and
> •	 there is an absence of end-organ 
> effects that may affect driving as per this 
> publication.
> * For a commercial driver with type 2 diabetes 
> who is being treated with metformin alone, the 
> annual review for a conditional licence may 
> be undertaken by the driver’s treating doctor 
> upon mutual agreement of the treating doctor, 
> specialist and driver licensing authority. The 
> initial granting of a conditional licence must, 
> however, be based on information provided by 
> the specialist.

PDF region: (341.0, 357.0, 532.0, 723.0); text SHA-256: `f1f98641878471e92379f83a9232cda6864ca59f57eea04909726eae4280e747`.

### AFTD2022-DM-COM-007

[§3.3 · printed 102 / PDF 113](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=113)

Table/context: Insulin-treated diabetes (except gestational diabetes)

> A person is not fit to hold an unconditional 
> licence:
> •	 if the person has insulin-treated diabetes.

PDF region: (341.0, 177.0, 532.0, 223.0); text SHA-256: `c282e63a3ed339de957b2bb665974fbe8ba99675e92293609823d9bfae70e2a4`.

### AFTD2022-DM-COM-002

[§3.2.1 · printed 94 / PDF 105](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=105)

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

### AFTD2022-DM-COM-008

[§3.3 · printed 102 / PDF 113](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=113)

Table/context: Insulin: conditional

> A conditional licence may be considered 
> by the driver licensing authority subject to at 
> least annual review, taking into consideration 
> the nature of the driving task and information 
> provided by an endocrinologist or consultant 
> physician specialising in diabetes on whether 
> the following criteria are met:
> •	 there is no recent history (generally at least 
> 6 weeks) of a ‘severe hypoglycaemic event’ 
> as assessed by the specialist; and
> •	 the person is following a treatment regimen 
> that minimises the risk of hypoglycaemia; 
> and
> •	 the person experiences early warning 
> symptoms (awareness) of hypoglycaemia 
> (refer to section 3.2.1); and
> •	 there are no end-organ effects that may 
> affect driving as per this publication.

PDF region: (341.0, 224.0, 532.0, 467.0); text SHA-256: `eb5eeaab23d2d51445f18bbcbf9e72dd9b472061317b753187c271bdf353cc53`.

### AFTD2022-DM-COM-009

[§3.3.2 · printed 99 / PDF 110](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=110)

Table/context: Commercial specialist review and glucose records

> 3.3.2. Recommendation and 
> review of conditional licences for 
> commercial vehicle drivers
> It is a general requirement that conditional 
> licences for commercial vehicle drivers are 
> issued by the driver licensing authority based on 
> advice from an appropriate medical specialist 
> (endocrinologist or consultant physician 
> specialising in diabetes) and that these drivers 
> are reviewed periodically by the specialist to 
> determine their ongoing fitness to drive (refer 
> to Part A section 4.4. Conditional licences). For 
> commercial drivers receiving insulin treatment, at 
> least three months of blood glucose monitoring 
> records should be reviewed in assessing fitness 
> to drive.

PDF region: (55.0, 370.0, 295.0, 634.0); text SHA-256: `426a6e52e563cfedd137a95b8eddcd0cbefaedd3b6ab9ccc78ad7917d1eb810d`.

### AFTD2022-DM-COM-003

[§3.2.2 · printed 95 / PDF 106](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=106)

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

### AFTD2022-DM-COM-001

[§3.1.1 · printed 92 / PDF 103](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=103)

Table/context: Diabetes driving effects

> Diabetes may affect a person’s ability to drive, 
> either through a ‘severe hypoglycaemic event’ 
> or from end-organ effects on relevant functions, 
> including effects on vision, the heart and the 
> peripheral nerves and vasculature of the 
> extremities, particularly the feet. In people with 
> type 2 diabetes, sleep apnoea is also more 
> common (refer to section 8. Sleep disorders). 
> The main hazard in people with insulin-treated 
> diabetes is the unexpected occurrence of 
> hypoglycaemia.

PDF region: (55.0, 268.0, 294.0, 438.0); text SHA-256: `7e3a2b0eca205bfc449f2f32db095e9511352c4ef45c5c35e4fb5cf1bca71ed0`.

### AFTD2022-DM-COM-010

[§3.2.4 · printed 96 / PDF 107](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=107)

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
- [ ] Confirm missing/unverified case fact: diabetes.gestational
- [ ] Confirm missing/unverified case fact: diabetes.present

## Case source

```text
There is a family history of diabetes in the driver's mother, but he says nobody has diagnosed him; over the last fortnight he has been unusually thirsty, getting up several times at night to pass urine and noticing intermittent blur after long shifts, while a borrowed meter displayed 17.8 mmol/L once without a verified testing protocol or confirmatory laboratory result.

He felt nauseated this morning and asks whether the reading means diabetes, but medication history is empty and the nurse records suspected metabolic disturbance requiring clinical assessment rather than a confirmed diagnosis, insulin treatment or an established complication; a normal reading remembered from last year does not resolve today's symptoms.

```

Input SHA-256: `701cc771b5a5558fdf7e81e26f89d88bfe1853f0a4cb334b192654ef62d7be1f`
Rule-result SHA-256: `792c43127b298d955dcda976c54f640dcc7497d96080cb9b404ef9ab46218cd6`
Evidence-pack SHA-256: `717c35be2968301a8796f25d678ec8e816c72f6b6d33a2c5d949e17e91881e89`
