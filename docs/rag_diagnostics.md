# Complex-note RAG diagnostics

The 24 September investigation separates three different outcomes: clinical fact
extraction, deterministic rule triggering and actual guideline retrieval. A
symptom can be relevant to a module without establishing every fact required by
a rule. Missing information is not evidence of a failed search.

## Inputs and evaluation

The original `CX-MIX-03` through `CX-MIX-12` files are unchanged. They mainly
contain unverified measurements, disputed symptoms and pending investigations.
All ten were run with real local Llama 3 and Chroma before and after the changes.

Ten additional notes, `VAL-MIX-01` through `VAL-MIX-10`, are in
`data/cases/validation_nurse_notes`. The first eight contain explicit positive
facts embedded in complex mixed-condition histories. The final two are uncertainty
controls. Source-based expectations are recorded separately in
`data/cases/gold/validation_complex_expectations.json`, never passed to the model
or retriever. These are synthetic engineering validation cases, not independently
adjudicated clinical gold. They were generated after the initial implementation;
follow-up repairs informed by their results make them development regression data.

All batch tests request all five modules, as in the browser's default selection.
An undocumented module can keep the overall outcome insufficient even when rules
in a documented module trigger. Inspect module-level outcomes as well as totals.

## Implementation

`case_intake/prose.py` recognizes bounded explicit clinical paraphrases and keeps
whole source clauses. Family history, uncertainty, historical-only records and
unverified data do not become current patient facts. `model_intake.py` also guards
against model quotations that omit family-subject context or historical timing.
The additional patterns are bounded language coverage, not complete clinical NLU.
An explicitly unverified current medication statement remains unknown, including
when a model supplies a shortened quotation that omits the verification qualifier.

`case_intake/indexed_review.py` reviews longer notes one field at a time,
hiding all prior extracted values. A fixed response object prevents
missing and duplicated keys. Disjoint schemas enforce documented/uncertain/missing
value semantics. The model selects source passage IDs; software reconstructs the
exact original quotation. Source review can withhold facts but cannot invent a
replacement value. Field guidance distinguishes an unknown disease mechanism from
a documented investigation status, and a missing test from unknown test availability.
Derived values retain deterministic calculation; quarantining an input also quarantines
its dependants. The model does not recompute derived arithmetic. Grammar validation
does not prove semantic correctness, and model review can still require confirmation.
Rejected first-pass proposals remain in the intake audit; they do not expand the
mandatory second-pass fields. Core module fields still support omission checks.

`retrieval/discovery.py` adds symptom-led discovery inside the existing retrieval
stage. It deduplicates the module-scoped original passages and uses the existing
Chroma embeddings plus BM25/RRF to search the module's knowledge units at Top 5.
Filters retain module, commercial context, guideline version and index identity.
This search is independent of the narrow `rag_query_key` filter used for mandatory
rule-bound citations. It runs on non-fast cases with source context, including
cases with zero triggered rules. It does not replace required citations, change
rule outcomes, infer diagnoses or build a full cross-disease knowledge graph.

Results appear under `evidence_pack.json -> retrieval.symptom_discovery`, including
original passages, source hash, filters, ranked candidates and verified citations.
The ordinary `ranking_calls` field still counts rule-scoped calls;
`symptom_discovery_calls` counts the additional searches. Do not conflate them.

`reporting/retrieval_status.py` displays those counts and original queries in the
new **Retrieval activity** section, with expandable candidate quotations and PDF
links. Mandatory rule references and ranked symptom candidates remain labelled
separately. Markdown reports also include the search activity and source links.

`pipeline/workflow.py` verifies saved symptom passages against original note
offsets and checks the retrieved citations against the verified source catalogue.
The established order remains extraction, validation, source review, deterministic
rules, retrieval, draft and human review. The clinical rulebook is unchanged.

## Reproduce

With Ollama running, from the project root:

```powershell
.\.venv\Scripts\python.exe -m occupational_fitness_rag.evaluation.note_batch --ids CX-MIX-03 CX-MIX-04 CX-MIX-05 CX-MIX-06 CX-MIX-07 CX-MIX-08 CX-MIX-09 CX-MIX-10 CX-MIX-11 CX-MIX-12 --output outputs/evaluation/rag_diagnostics/my_original_run
.\.venv\Scripts\python.exe -m occupational_fitness_rag.evaluation.note_batch --input-dir data/cases/validation_nurse_notes --expectations data/cases/gold/validation_complex_expectations.json --output outputs/evaluation/rag_diagnostics/my_validation_run
```

Each output folder has an `index.html` and `results.json`, and each case has a
complete saved draft, extraction/review audits and evidence pack. The batch runner
disables only optional model-written report commentary; clinical intake and
retrieval use the normal configured services. Use a new output folder per run.
Expected rules and sources measure engineering behavior only; source hits are
not diagnostic accuracy, and a short catalogue can make Top 5 coverage easy.

For browser testing, start the workspace with `scripts/start_workspace.ps1`, upload
one note and retain all five modules to match these batches. Reports generated
before an update remain historical snapshots; submit again for a current result.

## Recorded results: 24 September 2026

Open `outputs/evaluation/rag_diagnostics/index.html`. Its final collections are
`original_complete` and `validation_complete`; `baseline` contains the historical
comparison. Other folders retain development attempts and are not the acceptance
collection. All original input hashes, the clinical rulebook and the source
catalogue remained unchanged during this investigation.

- All 20 final cases performed rule-scoped ranking and returned symptom candidates.
- The original ten retain insufficient-information outcomes and zero triggers.
  Their unverified or incomplete statements do not establish the required clinical
  predicates. A scoped negative in the historical baseline was incorrectly treated
  as general absence; that false-trigger behavior was removed.
- All eight new positive cases matched all 14 expected rule instances. Both
  uncertainty controls avoided their specified forbidden rules.
- All 20 source reviews returned valid responses: 19 requested confirmation and
  one reported no issues. This is response validity, not semantic or clinical accuracy.
- Symptom Top 5 found 14 of 18 target-source instances; the four misses are listed
  in `summary.json`. Rule-bound citations retained all 18 target instances. Do not
  combine mandatory citation coverage with ranked-retrieval coverage.
- All 217 regression tests passed. Thirty saved bundles (baseline plus final)
  passed fingerprint checks, rule replay, source-citation verification and audit-chain
  verification. A real browser file upload of `VAL-MIX-04` returned both expected rules.

For example, `CX-MIX-09` documents poor fixation on a field test, unassigned acuity
and only a single current BP reading. Those passages support guideline retrieval
without establishing the corresponding thresholds. `VAL-MIX-04` supplies current
documented insulin treatment and specialist-confirmed diplopia, providing a positive
comparison through the same workflow.
