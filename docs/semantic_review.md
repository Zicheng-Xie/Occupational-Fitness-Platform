# Extraction semantic review

The default local workflow now performs a second model pass after deterministic extraction
validation and before rules or guideline retrieval. This pass independently re-reads the original note; the program compares that reading with
the validated facts. It is an extraction quality check, not a diagnosis or an accuracy certificate.

## Processing order

1. Read a UTF-8 TXT/Markdown file or a text-bearing PDF.
2. Extract facts using local Llama 3 8B, with deterministic extraction as a fallback.
3. Check field types, ranges, source quotations, context and conflicts.
4. Review the meaning against the original note in a separate local model call.
5. Quarantine flagged fields and dependent derived fields for human confirmation.
6. Evaluate deterministic rules and retrieve source-bound guideline evidence.
7. Generate the English draft and clinician checklist, including review status and concerns.
8. Verify the saved artifacts and await clinician review.

`case_intake/semantic_review.py` owns the second pass. It receives the original note,
the requested modules, the permitted field dictionary and extracted facts. The model itself
receives only the original note, permitted fields and field names to check: previous extracted
values, guideline evidence, rule outcomes and evaluation labels are withheld. It returns a
source observation for every requested field, plus any explicitly documented omissions. The
program compares the two readings and records discrepancies. Missing information alone is
not an error; an unknown field is never silently converted to false.

## How concerns are handled

The review targets negation, subject, uncertainty, time and measurements. The comparison
records contradictions, omissions and unsupported assertions. Each concern must identify a permitted in-scope field and
quote the original note exactly. If the second pass cannot find support for a recorded fact,
the disputed original extraction span is retained as its review location. Quotes receive character offsets, line numbers and PDF pages
when available. Repeated quotes retain every matching location instead of guessing one.

Independent observation values are retained only in the audit and never used as replacement
case facts. A flagged field becomes `requires_confirmation`
with no authoritative value; an existing `conflicting` status remains conflicting. Fields derived
from a flagged value are also withheld. The audit preserves the pre-review facts, so a reviewer
can inspect what was extracted before it was withheld. The rules are replayable from the final
structured case. Modules with review concerns use the human-review route.

The second model can itself be wrong. A valid quote proves the location of the concern, not its
clinical correctness. No issue found means only that the independent source reading did not
produce a discrepancy for the fields reviewed. In
particular, two passes using the same model do not provide independent validation.

## Failure and configuration

`configs/workflow.yaml` enables `llm.semantic_review_enabled: true`. The step also requires
`llm.enabled: true`; offline mode records it as disabled and makes no model request.

Oversized review payloads are not truncated: they are recorded as `skipped_context_budget`.
Timeouts, malformed JSON, fabricated quotations, incomplete checked-field lists and fields
outside the requested scope are recorded as `unavailable_or_invalid`. Invalid answers receive
at most one fresh review attempt with a stricter format reminder; transport failures are not
retried. Both attempts and their prompt hashes are recorded. In these cases, the
validated input facts are retained and requested modules require human review. These states
are never displayed as successful checks. Processing can still produce a traceable draft.
Retrieval may use the original wording of a disputed field, explicitly marked unconfirmed,
without using its withheld value as a confirmed rule input.

The browser shows an explicit review stage. HTML and Markdown drafts display the status,
concerns and original text locations. New run bundles contain `llm_semantic_review.json`, also
embedded in `structured_case.json` under `extraction_metadata.semantic_review`. The manifest
records the review status and includes the audit's file hash. Verification checks the audit
against the structured case and its final facts. Older run bundles remain readable and unchanged.

## Two different model tests

The pre-retrieval semantic review is part of normal note intake. The post-retrieval model judgment
study remains a separate opt-in experiment: `fitness-rag judgment-study`. That experiment tests
whether the model can use retrieved evidence to form an assessment; its answers do not replace
deterministic rule decisions in reports. Calling `workflow.assess` directly on an already
structured case performs rules and retrieval only; text/file intake performs the extraction review.

To measure the new reviewer independently of the first extraction pass:

```powershell
.\.venv\Scripts\fitness-rag.exe semantic-review-study --config configs/workflow.offline.yaml
```

This command explicitly calls the configured local model even with the offline workflow config.
It uses `data/cases/gold/semantic_review_cases.json`, which includes deliberate extraction errors
and clean controls across all five modules. Expected issue fields never enter the model prompt.
Results are saved to `outputs/evaluation/semantic_review.json`, including failed/skipped counts,
model fingerprints, source locations and detected/missed fields. This small development set
measures seeded error detection, not independently reviewed clinical accuracy.

Retrieval strategy and knowledge coverage are unchanged by this addition. The assessment still
defaults to vector plus BM25 with RRF for eligible review requests. Full cross-disease Blackout
retrieval remains a separate open requirement.

## Local validation on 17 September 2026

The final independent-reading design completed 7 of 8 synthetic review scenarios. All seven
completed scenarios matched their expected issue fields, and both clean controls had no flags.
One vision omission scenario returned an invalid unconfirmed value and was routed for human
review after two attempts. Counting that failed scenario, 6 of 7 seeded issue fields were
detected (85.7%). This is a development result, not clinical accuracy or a holdout result.
Earlier direct-critique prompt trials are preserved in `outputs/evaluation/semantic_review_development/`.
