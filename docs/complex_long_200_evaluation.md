# Evaluation of 200 complex long-form nurse notes

## Inputs and scope

`data/cases/complex_nurse_notes/CX-LONG-001.txt` through `CX-LONG-200.txt`
are English synthetic clinical narratives grounded in the existing AP-G56-22
guideline. They are fictional records, not patient cases extracted from that PDF.
Each contains 231-312 whitespace-separated words and at least three sentences
of 35 words or more. Original inputs remain unchanged.

Forty scenario families have five correlated variants each. There are 40 primary
cases per module and 40 multi-module cases, producing 240 case/module retrieval
scopes. They cover contradictory accounts, older documents, family histories,
uncertain diagnoses, incomplete tests, measurement conditions, boundary values,
waiting intervals and cross-module concerns. They are development stress inputs;
the cohort is not 200 independently sampled or independently labelled patients.

The 200 references include 36 unconditional, 24 conditional, 40 temporary
restriction, 13 both-pathway exclusion and 87 information-insufficient outcomes.
Always predicting information-insufficient therefore agrees with 43.5% of these
engineering references. Overall agreement must be interpreted alongside that
baseline, per-class recall, Macro-F1 and specific error counts.

The input manifest contains file fingerprints and requested modules. Expected
facts, outcomes and original-source labels are in the separate
`data/cases/gold/complex_long_200.json` file. The generator does not call the
production evaluator to create reference outcomes. References are frozen before
system inference and remain pending independent clinical review. They are not
clinical accuracy labels.

## Three measured stages

1. **Broad original-source discovery.** The entire note is the query, without
   reference source IDs or rule outcomes. Real Ollama `nomic-embed-text` embeddings
   in a separate Chroma index, BM25 and Hybrid RRF search the same frozen
   88-original corpus. Metadata filters enforce the predefined disease module,
   commercial-compatible scope, guideline version and corpus identity. Shared
   general guidance is retained; private-only units are excluded. There are
   240 scopes times three methods, or 720 ranked conditions.
2. **Live platform workflow.** Each of the 200 files passes through the existing
   Llama extraction, provenance/type checks, independent semantic review,
   deterministic rules, rule-scoped retrieval and symptom discovery. Optional
   narrative wording is disabled; ordinary English template reports still exist.
   Separate Chroma persistence avoids changing the application's active index.
3. **Experimental Llama judgment.** One additional actual model attempt per
   successful upstream case reads only the accepted patient facts, note context
   and at most five whole Hybrid-retrieved original passages. Round-robin module
   allocation and a 9,000-byte evidence budget are fixed. A passage that does not
   fit is recorded as excluded rather than truncated or replaced by an expected
   source. These proposals never alter the platform's rule result.

The judge uses the original fixed experimental prompt at temperature 0 and seed
0, with 8,192 context tokens and a 2,048-token generation reservation. This study
has one attempt per case, not three repetitions. Runtime and model digests are
pinned in `configs/experiments/complex_long_200.yaml` and the execution plan.
It compares discovery methods but does not repeat the judgment stage with
vector-only or BM25-only evidence, so it does not establish the causal judgment
effect of switching between those methods.

Requested modules are specified before execution, as a user can select them in
the platform. This does not measure automatic disease classification. Additional
unassessed modules can legitimately introduce information insufficiency.

## Metric definitions

| Metric | Meaning |
|---|---|
| Coverage Recall@K | Fraction of labelled originals covered by the Top-K originals, averaged over the 240 scopes |
| Exact-ID Recall@K | Fraction of labelled source IDs actually returned, without containment credit |
| Complete coverage@K | Fraction of scopes for which all labelled originals are covered |
| Hit@K | Fraction of scopes with at least one labelled original covered |
| MRR@K | Reciprocal rank of the first candidate covering any labelled original, or zero if none appears within K |
| Engineering reference agreement | Correct completed outcomes divided by all recorded conditions, including failures |
| Accepted-only agreement | Correct outcomes divided by valid completed outcomes; shown separately from the primary denominator |
| Macro-F1 | Mean F1 over the fixed five outcome classes; failed attempts contribute false negatives |
| Balanced accuracy | Mean recall over reference classes observed in the group |
| Fact value checks | Correct present values among explicitly annotated fields; other fields are not automatically counted as false positives |
| Specified abstention checks | Proportion of nominated unverified fields that remain unconfirmed |
| Excess insufficiency | Information-insufficient predictions whose engineering reference is another class |
| Restriction-to-permission disagreements | Temporary/exclusion references predicted as unconditional or conditional permission |

Containment coverage requires same-module, same-page literal original-text proof
after whitespace normalization. It does not credit an arbitrary semantic match.
Reference lists are not exhaustive relevance judgments, so these measures are
coverage of nominated evidence rather than complete clinical relevance scores.
Hypertension has four available originals: its Top-5/10 coverage saturates and
cannot establish fine ranking quality. Inspect Top-1/3 and module breakdowns.

Mandatory rule-bound source citations are not included in broad discovery recall.
Their identities are required by rules and cannot demonstrate successful open
ranking. A valid source ID or fact field is not proof that the explanation follows
from its original source. Clinical support-review fields remain blank.

## Execution, failure preservation and inspection

```powershell
.venv/Scripts/python.exe -X utf8 -m tools.run_complex_long_study --prepare-only
.venv/Scripts/python.exe -X utf8 -m tools.run_complex_long_study --resume
```

The output is `outputs/evaluation/complex_long_200_20261027`. Open `index.html`
and check `summary.json` for `complete: true` before using final metrics. Raw
rankings, workflow observations and model requests/responses are in
`retrieval.jsonl`, `workflow.jsonl` and `judgments.jsonl`. Scored fact checks are
in `workflow_scored.json`; each ordinary report has its own immutable run bundle.
Use the input inventory to select the correct modules for manual uploads.

Recorded failures are never silently retried, converted into successful
abstentions or replaced by another backend. Resume verifies source/configuration,
input and runtime identities, journal digests and prior checkpoint prefixes.
Interrupted in-flight attempts remain unresolved failures rather than fictional
new successes. Source and runtime failures can stop a run explicitly.

```powershell
.venv/Scripts/python.exe -X utf8 -m tools.audit_complex_long_study
```

The independent audit checks the full condition inventories, raw response
bindings, original input preservation, source pins, case-bundle hashes and
reported outcome counts. It retains examples where an extraction response
returned a type name such as `boolean` or `string` as a value, plus other withheld
proposal reasons, actual evidence-packet coverage and source-reference flags.

A separate diagnostic supplies the authored reference facts directly to the
unchanged rules. It yields 176/200 reference agreements (88%) and isolates the
intake stage. This is neither automatic extraction nor an achieved system
improvement. Its 24 remaining disagreements need source/label/category review.

The audit records observed attempt latency and captured model-call records.
Workflow exception audits may not preserve every failed generation call, so
captured workflow calls are a lower bound. Attempt sums exclude index setup and
report rendering and are not an isolated hardware performance benchmark.

Earlier 33-case results and all existing retrieval methods remain separate.
Different cohorts and query protocols must not be described as a measured
before/after regression. Fixes informed by these 200 cases require a separately
frozen development rerun, followed by untouched independently annotated cases.
