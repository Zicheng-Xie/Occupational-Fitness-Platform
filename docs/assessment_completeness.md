# Assessment completeness and established findings

The five-module assessment distinguishes rule findings, information completeness and retrieval activity. Selecting all five modules requests all five assessments; it does not provide the missing facts or imply that the patient has all five conditions.

An `insufficient_information` outcome can coexist with triggered rules. A treatment-category or unconditional-threshold rule may trigger while the conditional-standard criteria remain unresolved. Established adverse outcomes retain the precedence defined in the unchanged rulebook. Neither symptoms nor retrieved passages replace missing patient measurements.

## Reading the report

- **Overall provisional outcome:** the rulebook aggregate for the requested modules, pending clinical review.
- **Established rule findings:** triggered rule IDs and their source-supported reasons, even when the overall assessment is incomplete.
- **Information coverage:** supported facts and unresolved rule fields for each selected module. These fields are not a mandatory list of medical tests.
- **Retrieval activity:** searches and candidates, independent of rule-trigger counts. Returning candidates is not evidence of clinical accuracy.
- **Extraction semantic review:** an independent local-model source reading. Disagreement may withhold facts; model agreement is not clinical validation.

## Source review corrections

The indexed reviewer asks for information status before the typed value. Explicit absence remains a documented false value; omitted information stays unknown. Direct questions clarify audiometry availability and physiological versus non-physiological diplopia. Standalone synthetic-note headers are excluded from clinical passages. Unrelated Blackout passages and inconsistent missing-information responses are rejected and retried. Invalid review output remains visible for human review.

The context vocabulary no longer treats bare `awareness` in `hypoglycaemia awareness` as a Blackout symptom. Actual loss or alteration of awareness still qualifies for review context. Versioned context selection preserves replay of historical report bundles.

## Ten-case validation

Inputs remain unchanged in `data/cases/validation_nurse_notes/`. Engineering expectations are in `data/cases/gold/validation_complex_expectations.json` and are not supplied to the model or the rule engine.

| Cases | Expected all-module outcome | Interpretation |
|---|---|---|
| VAL-MIX-02, 06, 07 | `temporarily_unfit` | Established adverse rule criteria retain priority over missing information elsewhere. |
| VAL-MIX-04 | `does_not_meet_standard` | The diplopia rule establishes the provisional adverse outcome. |
| VAL-MIX-01, 03, 05, 08 | `insufficient_information` | Positive rule findings exist, but the assessment remains incomplete. |
| VAL-MIX-09, 10 | `insufficient_information` | Uncertain-control notes must not be promoted into verified adverse findings. |

Run the unchanged ten notes with local extraction, source review and Chroma retrieval:

```powershell
.\.venv\Scripts\python.exe -m occupational_fitness_rag.evaluation.note_batch --input-dir data/cases/validation_nurse_notes --output outputs/evaluation/assessment_completeness --expectations data/cases/gold/validation_complex_expectations.json
```

Open `outputs/evaluation/assessment_completeness/index.html` for per-case reports, expected-trigger checks, overall-outcome checks, review status and audit details. The batch disables only optional narrative wording; live workspace uploads also exercise narrative generation. Old reports are immutable: create a new assessment to see the updated processing and presentation.

These are developer-authored synthetic regression checks, not an independent clinical accuracy study. Semantic review can still flag uncertain or misread fields; retain human review and inspect its audit.
