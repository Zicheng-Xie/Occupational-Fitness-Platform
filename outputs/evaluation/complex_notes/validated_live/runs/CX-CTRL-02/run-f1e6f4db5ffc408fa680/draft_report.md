# Clinical review draft — CX-CTRL-02

CX-CTRL-02: Meets unconditional standard. 1 requested modules; 0 unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.

**DRAFT · pending_clinical_review · Clinical sign-off pending**

| Module | Provisional outcome | Route | Missing fields |
|---|---|---|---|
| blackout | Meets unconditional standard | fast_path | 0 |

[Original case input](source_input.txt)

## Extraction semantic review

Extraction semantic review: No issues flagged by the model
This second-pass model review does not establish clinical accuracy. A clinician must verify the original record and any flagged information.

[Semantic review audit](llm_semantic_review.json)


## Rule-to-source trace

### BLK-COM-NO-HISTORY-001 — triggered

The note explicitly records no blackout history; no blackout-specific restriction is identified within this screening scope.

- `blackout.occurred` = False (present)
  - Source lines 1–1; chars 0:23: No history of blackouts
  - Source lines 1–1; chars 0:24: No history of blackouts.

Guideline sources: [AFTD2022-BLK-COM-001](#aftd2022-blk-com-001)

## Guideline evidence

### AFTD2022-BLK-COM-001

[§1.2.1 · printed 57 / PDF 68](../../../../../../../data/knowledge/raw/ap_g56_22.pdf#page=68)

Table/context: Blackout work-up; continuation of general considerations

> cardiovascular and neurological investigations 
> and referral to several specialists. People should 
> be advised not to drive until the mechanism is 
> ascertained and the corresponding standard met.

PDF region: (305.0, 117.0, 545.0, 182.0); text SHA-256: `dd23a937a5e99db2c2440ffc7ef66d4003092af008384c56d49be31234941a55`.

## Clinician checklist

- [ ] Clinician: review source facts, rule applicability and every provisional conclusion.
- [ ] Confirm the commercial driving task and assess conditions outside the five-module scope.

## Case source

```text
No history of blackouts.

```

Input SHA-256: `df121183aa18f10a082fd43a5c1e3b77cd2dca4068f6afd59bf7b045f42ca65b`
Rule-result SHA-256: `99eb7acf917ab3adb3991c7de754eab30e5b4656a1e4ccac957a479d18c42f29`
Evidence-pack SHA-256: `d40ec361c5b66033979f3d998b560be7651da309e253fea38264b3a980ce098f`
