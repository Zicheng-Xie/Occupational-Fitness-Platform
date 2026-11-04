# Completed case-allocation judgment comparison

All 990 actual conditions completed: 33 previously observed development cases,
five evidence arms, two local models and three calls per case/model/arm. There
were 957 accepted responses and 33 failures, all caused by empty source-citation
arrays. Failed responses are retained in the all-call agreement denominator.
The independent audit verified 990 unique provider responses, fixed requests,
patient facts, versions and source inventories, with zero pilot responses imported.

These results measure **Engineering reference agreement**, not clinical accuracy.
Repeated calls are aggregated within 33 patients; they are not 990 patients.

## Evidence coverage versus actual judgment

| Evidence arm | Case-packet coverage | Llama correct /99 | Qwen correct /99 | Llama majority-correct /33 | Qwen majority-correct /33 |
|---|---:|---:|---:|---:|---:|
| Hybrid RRF, original allocation | 80.74% | 45 | 46 | 15 | 15 |
| Method 7, original allocation | 82.22% | 39 | 45 | 13 | 15 |
| Method 7, case allocation | 86.67% | 42 | 42 | 14 | 14 |
| Method 9, original allocation | 84.44% | 42 | 45 | 14 | 15 |
| Method 9, case allocation | 84.44% | 45 | 42 | 15 | 14 |

Coverage uses the same 45 source-labeled module scopes, at most five whole original
passages and 9,000 evidence bytes per patient packet. It is distinct from
module-level Top-5 recall and fitness classification agreement.

Llama's new allocation gains three correct calls for each method, entirely from
citation-contract recovery. Neither method produces a valid wrong-to-correct
classification for Llama. Six identical-request differences in the seventh arm
are contract/status variations, with zero net correctness gain; they cannot be
attributed to changed evidence.

For Qwen, retrieval changes relative to RRF correct two repeated calls on
`SYN-EXT-008` but lose three on `SYN-EXT-015`: a valid-classification net of minus
one, not five independent patients. New allocation additionally loses all three
calls on `SYN-M2-009` for both methods. Thus neither new allocation demonstrates
improved overall judgment; production retrieval and rule decisions are unchanged.

## VAL-MIX-02 and VAL-MIX-06

Each case has 30 conditions. All 60 accepted outcomes remain
`insufficient_information`, against the frozen engineering reference
`temporarily_unfit`. Method 7's Blackout packet coverage rises from zero to full
coverage in both cases, without changing the structured judgment.

The added source `AFTD2022-EXP-05643c50d6cf5973` is section 1.2.1, PDF page 68,
printed page 57. Its frozen text matches the native PDF rectangle. The two records
document a Blackout with a mechanism still under investigation; a specific
vasovagal diagnosis is not established. This is an engineering consistency check;
independent clinical applicability review remains pending.

The exact original responses show distinct issues requiring separate review:

- Qwen on VAL-MIX-02 explicitly describes the no-driving-until-investigation
  restriction, but emits an insufficient-information overall outcome. This is a
  potential aggregation or output-mapping problem, not simply missing retrieval.
- Qwen on VAL-MIX-06 moves from a pending investigation to an undetermined-nature
  long-term restriction pathway. Pending work-up and completed-but-unexplained
  investigations must be distinguished.
- Llama on VAL-MIX-02 describes uncorrected 6/12 and 6/18 as meeting commercial
  vision standards. The actual supplied commercial column states the unconditional
  better-eye threshold of 6/9, with separate conditional qualifications. Native
  PDF page 220, section 10.3, printed page 209 matches the supplied original.

## Regression and explanation consistency

For `SYN-M2-009`, new packets retain one hearing original instead of five companion
passages, with unchanged facts: 45 dB unaided better-ear average, hearing-aid use,
and unresolved frequency/aided measurements. Qwen changes from reference-consistent
`insufficient_information` to `meets_unconditional_standard` in all three repeats
for both methods. Its explanation recognizes the 45-versus-40 exclusion while its
structured label declares unconditional fitness, and borrows vision wording into
hearing. One explanation is semantically unfinished despite a complete JSON
response. These observations require a separate companion-evidence ablation and
judgment consistency checks; they do not identify one passage as the sole cause.

A separate post-hoc literal audit flags 110 of 957 accepted explanations for
source-like identifiers absent from their actual packets. There are four distinct
flagged literals, including a repeated missing-character Blackout ID. Structured
source arrays remain valid. This is not an additional measured contract-failure
count or a clinical hallucination rate. The case-sensitive ASCII matcher has
documented suffix/spacing limitations, and each flag requires review. Raw statuses
and explanations are unchanged.

## Reports and independent review

- [Completion report](../outputs/experiments/case_allocation_completion_v1/index.html)
- [Interactive paired viewer](../outputs/experiments/case_allocation_judgment_comparison_v1/index.html)
- [Independent patient-level analysis](../outputs/experiments/case_allocation_effect_analysis_v1/index.html)
- [Independent execution audit](../outputs/experiments/case_allocation_full_integrity_v1/checks.json)
- [Literal prose-ID audit](../outputs/experiments/case_allocation_prose_reference_audit_v1/index.html)
- [Native commercial-vision region](../outputs/experiments/vision_source_visual_review_v1/source_region.png)
- [Focus support-review worksheets](../outputs/experiments/case_allocation_focus_support_review_v1/index.html)
- [Prospective annotation packet](../outputs/experiments/prospective_case_review_v2/index.html)

The support-review packet preserves 60 actual focus occurrences in 18 exact-context
groups and 90 per-source review rows. Every human decision field is blank;
completed independent reviews remain zero. Twelve new prospective notes have no
model predictions or reference labels. Their annotation, source verification,
runner integration and live native-index checks are pending and fail closed.

Follow the separately proposed [judgment ablation protocol](case_allocation_followup_protocol.md).
Review explicit outcome semantics, criterion applicability, numeric consistency
and companion evidence as separate interventions. Freeze subsequent choices
before prospective evaluation. Preserve this experiment and all earlier methods;
do not replace production based on these development results.
