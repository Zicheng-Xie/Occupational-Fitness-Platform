# Clinical review draft — CX-CTRL-01

CX-CTRL-01: Meets unconditional standard. 1 requested modules; 0 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| diabetes | Meets unconditional standard | fast_path | 0 |

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: Not performed (disabled)
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### DM-COM-NO-HISTORY-001 — triggered

The note explicitly records no diabetes; this is a history-based screening result, not a diabetes diagnosis.

- `diabetes.present` = False (present)
  - Source lines 1–1; chars 0:11: No diabetes

Guideline sources: [AFTD2022-DM-COM-001](#aftd2022-dm-com-001)

## Guideline evidence

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

## Clinician checklist

- [ ] Clinician: review source facts, rule applicability and every provisional conclusion.
- [ ] Confirm the commercial driving task and assess conditions outside the five-module scope.

## Case source

```text
No diabetes.

```

Input SHA-256: `ca63efa25a2d0a37e5ca30bf927b5603a4cef1c0122e1fb49a2a7eeb5d15c608`
Rule-result SHA-256: `3f5d38dadcdbbff1c122fc512626421c922afb054c72a6265c1f6d1598de56fe`
Evidence-pack SHA-256: `5e282b7ec421410354a0435d320fcb161b7cb1269b17ebebfd1cac7067818e01`
