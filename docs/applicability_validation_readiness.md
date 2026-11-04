# Applicability validation readiness

Readiness audit: **15 October 2026**. This audit reads the existing reference labels, frozen facts and original-passage preparation artifacts. It does not call a model, execute retrieval, change a label or restore quarantined facts. Current live experiments and their selected configurations remain unchanged.

## Prepared replay and its boundary

`configs/experiments/passage_comparison_full_clean.yaml` prepares all **33 existing reference cases**: **23 engineering** cases and **10 complex** cases. The output directory is separate: `outputs/experiments/passage_comparison_full_clean`.

Its planned matrix is 33 cases × two pinned judges × three evidence policies × two protocols × one repeat = **396 judgment conditions**. The protocols are `quote_contract` and `passage_selection`; this configuration does **not** add the two-stage applicability-first protocol. It can prepare the broader source evidence needed for a later locked applicability comparison, after the development intervention is finalized.

The two ordinary query policies, `mixed_query` and `module_query`, require **154 case/module retrieval records**: 77 requested case/module scopes per policy. Both use actual hybrid RRF and the same documented-module allocation, Top 5 judgment budget, Top 10 retained ranking and original-passage byte limits. The reference-evidence control uses fixed reference passages separately. The source-only preflight loaded all 33 patient/reference payload pairs successfully and found a maximum of five reference-control passages. This is an input preflight, not a new retrieval result or a completed validation run.

The initial command is preparation only:

```powershell
.venv/Scripts/python.exe -m occupational_fitness_rag.evaluation.passage_comparison --config configs/experiments/passage_comparison_full_clean.yaml --retrieval-only
```

The preparation command subsequently completed **154/154 retrieval conditions** and
**99/99 case/policy payloads** on the 94-unit corpus. It records **0/396 judgment
conditions**. `coverage.html` and `retrieval_coverage.json` contain the per-case
reference-availability calculations. This is completed retrieval preparation, not
completed downstream validation. Later package changes have their own source identity;
reuse these frozen artifacts through explicit read-only import rather than rebinding
the historical resume manifest. The configuration itself does not gate judgment
execution; omitting `--retrieval-only` in a fresh run starts its configured matrix.

Judge pins match the current development configuration: `llama3:8b` digest `365c0bd3c000a25d28ddbf732fe1c6add414de7275464c4e4d1c3b5fcb5d8ad1`, and `qwen3.5:4b-q4_K_M` digest `91fa08b9fedfbbda924cd71febc5f6adbf31503cf7811df817dcf93bd56b08ff`. The runtime pin is Ollama `0.40.4`; embeddings are `nomic-embed-text:latest`, 768 dimensions, digest `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f`. Context/output limits are 8192/2048 tokens; payload, complete serialized request and evidence byte limits are 24000/48000/9000. Temperature and seed remain zero in the shared request builder. Each protocol permits at most one recorded structural repair.

## What is and is not independently held out

The eight cases used to develop the current diagnostic and applicability protocol are:

- Engineering: `SYN-EXT-002`, `SYN-EXT-003`, `SYN-EXT-008`, `SYN-EXT-020`.
- Complex: `VAL-MIX-02`, `VAL-MIX-04`, `VAL-MIX-06`, `VAL-MIX-07`.

The remaining **25** cases were not in that eight-case protocol-development matrix:

- Engineering, 19 cases: `SYN-EXT-001`, `SYN-EXT-004`, `SYN-EXT-005`, `SYN-EXT-006`, `SYN-EXT-007`, `SYN-EXT-009`, `SYN-EXT-010`, `SYN-EXT-011`, `SYN-EXT-012`, `SYN-EXT-013`, `SYN-EXT-014`, `SYN-EXT-015`, `SYN-EXT-016`, `SYN-EXT-017`, `SYN-EXT-018`, `SYN-EXT-019`, `SYN-M2-003`, `SYN-M2-009`, `SYN-M2-010`.
- Complex, six cases: `VAL-MIX-01`, `VAL-MIX-03`, `VAL-MIX-05`, `VAL-MIX-08`, `VAL-MIX-09`, `VAL-MIX-10`.

These 25 cases are **not unseen patients or an untouched independent holdout**. All 33 participated in the earlier retrieval/judgment comparison and their labels and some errors have already been inspected. They support a broader, locked engineering replay with separate development and remaining-case reporting. Clinical gold labels remain pending. A future independent validation set requires newly held-out cases, a locked protocol before inspection and independent reference adjudication.

## Outcome support and imbalance

Counts below are fixed reference labels, not model predictions:

| Reference outcome | Engineering 23 | Complex 10 | All 33 | Development 8 | Remaining 25 | Remaining without eight upstream discrepancies, 17 |
|---|---:|---:|---:|---:|---:|---:|
| `meets_unconditional_standard` | 4 | 0 | 4 | 1 | 3 | 1 |
| `may_meet_conditional_standard` | 5 | 0 | 5 | 0 | 5 | 0 |
| `temporarily_unfit` | 5 | 3 | 8 | 4 | 4 | 4 |
| `does_not_meet_standard` | 1 | 1 | 2 | 1 | 1 | 0 |
| `insufficient_information` | 8 | 6 | 14 | 2 | 12 | 12 |
| Total | 23 | 10 | 33 | 8 | 25 | 17 |

The development set has no positive conditional-standard reference. All five conditional-reference cases occur among the eight upstream discrepancies. Excluding those discrepancies leaves the remaining 17 cases with **zero** conditional references and **zero** `does_not_meet_standard` references. That sensitivity subset cannot establish performance for either class. It also contains 12 insufficient-information references, so an always-insufficient predictor reaches **12/17** agreement without recognizing any restriction. Report class-specific recall, balanced accuracy, confusion matrices and failure denominators, rather than using aggregate agreement alone.

Requested scopes comprise 11 multi-module cases, three hypertension-only, seven blackout-only, seven diabetes-only, four hearing-only and one vision-only case. Multi-module cases have an overall reference outcome; they do not provide five independently labelled disease outcomes.

## Eight known upstream discrepancies

The existing `upstream_audit.json` records deterministic extraction/rule agreement with all 33 references, while the frozen post-model-review rule outputs agree with **25/33**. This is an upstream diagnostic contrast, not proof of clinical labels. All eight differences are in the engineering cohort and outside the current eight-case development matrix. Their frozen rule outcome is `insufficient_information`. Explicitly documented values were withheld as `requires_confirmation`; the labels were not rewritten.

| Case | Fixed reference | Principal documented fields withheld in the frozen input |
|---|---|---|
| `SYN-EXT-001` | `meets_unconditional_standard` | Six fields: confirmed visual-field defect=false, diplopia=false, monocular=false, hearing assessment=`no_hearing_loss`, blackout occurrence=false, diabetes presence=false. |
| `SYN-EXT-005` | `may_meet_conditional_standard` | `blackout.diagnosis="undetermined"`. |
| `SYN-EXT-007` | `may_meet_conditional_standard` | `blackout.diagnosis="undetermined"`. |
| `SYN-EXT-010` | `meets_unconditional_standard` | Five explicit false diabetes findings: acutely unwell, metabolically unstable, severe hypoglycaemic event occurrence, recent severe hypoglycaemic event and driving-relevant end-organ effects. |
| `SYN-EXT-011` | `may_meet_conditional_standard` | The same five explicit false diabetes findings as `SYN-EXT-010`. |
| `SYN-EXT-012` | `may_meet_conditional_standard` | The same five explicit false diabetes findings as `SYN-EXT-010`. |
| `SYN-EXT-014` | `may_meet_conditional_standard` | `diabetes.metabolically_unstable=false` and `diabetes.recent_severe_hypoglycaemic_event=false`. |
| `SYN-EXT-018` | `does_not_meet_standard` | `vision.diplopia.physiological=false`, `vision.visual_field.confirmed_defect=false` and `vision.monocular=false`. |

An evidence-only intervention cannot recover these values by treating the raw note as a verified fact source; doing so changes the agreed experimental input contract. Report all 33 unchanged as the main replay, flag the eight affected cases explicitly and provide the fixed 25-case sensitivity subset. For the non-development partition, report the 17-case sensitivity separately with its missing classes. Do not relabel the eight as retrieval failures or assume their references are wrong.

If the team resolves these quarantines, preserve the original frozen inputs and create a separately versioned, adjudicated-facts condition. Record each restored/changed field, supporting original span, reviewer, rationale and version. Do not mix restored facts into one method while retaining quarantined facts for another. A separate oracle-fact diagnostic may help localize an upstream problem, but it is not a production fix or an independent clinical reference.

## Corpus readiness and exclusions

The prepared replay uses **94** original knowledge units, corpus identity `f4c53ea86f9c6e87a7edfb953a9c5c3305d8a6255116072a30ddf43c001c40cc`: hypertension 4, blackout 16, vision 33, hearing 13 and diabetes 28. All 28 protected canonical reference sources remain available. Two fragmented Figure 11 units from PDF page 119 were quarantined after engineering visual review because the flowchart's branches and qualifications were not preserved as self-contained passages.

The quality-review scope explicitly covers that layout failure. It does **not** certify the semantics of all 94 remaining units, establish clinical approval or resolve every excluded figure/cross-reference. Call this the **94-unit corpus after engineering layout quarantine**, rather than a clinically reviewed corpus.

## Remaining requirements before a broader applicability claim

1. The two bounded development comparisons are complete at 192 conditions each. Preserve their first-attempt, repaired, failed and truncated outputs separately. A broader locked replay must not change package code, input facts or its selected configuration mid-run.
2. The program-bound applicability intervention is frozen in `applicability_comparison_full33_original_v3.yaml`: 33 cases, two judges, two evidence policies, two protocols and three repeats, or 792 conditions. It imports prepared retrieval through an explicit verified identity. Execution status and accepted results must be read from that run's manifest and completed execution audit, not inferred from configuration. Earlier prefixes stopped at 100 and 81 conditions when an eight-field bound affected the derived union and then its provenance bridge. Both interruption audits and raw failures remain preserved. The new union bound is 48, and source locations are resolved directly outside the model-written final-proposal contract. Model-written component bounds and first requests remain unchanged. The 12-condition real pilot completed all stages with both models; its execution success does not establish semantic improvement.
3. Preparation completed all 154 retrieval records and 99 case/policy payloads. Automated preflight verifies complete original text, source/module bindings, commercial/shared corpus scope and initial request byte budgets. This does not establish that all clinical qualifications are semantically complete; independent source review remains pending.
4. Resolve or explicitly stratify the eight upstream discrepancies. Preserve both original and any adjudicated fact versions; do not repair them from model outcomes.
5. Report both cohorts and the eight-case development/25-case remaining partitions. Include all five outcome counts, the 17-case sensitivity's absent classes, failures, unjustified permission, excessive abstention and paired improvements/regressions.
6. Retain exact prompts, raw stage outputs, all attempts and total/stage costs. For two-stage inference, a failed first applicability stage is not an ordinary incorrect final judgment; stage completion and resume identities need explicit handling.
7. Complete independent original-evidence applicability and explanation-support review. The engineering fixtures have no clinician-approved gold labels. Quote/ID validity and internally consistent model findings are not clinical correctness.
8. Run three independent calls per final condition only after the protocol is locked. The selected two-policy applicability replay has **792 conditions**; the separate source-literal sensitivity has **312** across its 13 uniformly eligible changed cases. These are conditions, not patients or actual provider-call counts. A three-policy comparison would have 1,188 conditions, but is not the selected matrix. Independent new-case validation remains a separate requirement.

Production extraction, semantic review, deterministic rules, upload entry points and final clinical review remain unchanged by this readiness work.

## Completed literal audit and broader coverage

`tools/audit_frozen_fact_literals.py` independently locates JSON literal addendum
lines in the original source files. Across all upstream field changes, 16 cases
contain 44 changed-field occurrences: 41 have matching explicit literals and three
are not explicit addendum literals. All 44 previously recorded source spans match
the original decoded text with CRLF preserved. In the eight outcome-discrepancy
cases specifically, **all 28 occurrences** are explicit literal revalidation
candidates. The audit restores **zero** facts and changes no label or production
decision. It records exact types, source hashes, Unicode offsets and pending review.
False is not coerced to zero, nor a string to a boolean. Clinical interpretation of
the SYN-EXT-014 recent-event/interval relationship remains separate.

The broader prepared Top-5 payloads have these equal-case reference coverage values:

| Cohort | Mixed exact | Module exact | Mixed mapped | Module mapped |
|---|---:|---:|---:|---:|
| All 33 | 44.0% | 61.3% | 83.5% | 85.6% |
| Engineering 23 | 61.0% | 70.6% | 93.8% | 88.0% |
| Complex 10 | 5.0% | 40.0% | 60.0% | 80.0% |

Mapped coverage credits frozen `covers_source_ids` associations; it must not be
merged with exact-ID coverage. Reference controls are 100% by construction.
Module queries improve mapped availability in VAL-MIX-02/04/07/09 but regress in
SYN-EXT-009 and SYN-EXT-013. The full set of reference passages is supplied in 24/33
mixed payloads and 26/33 module payloads under mapped coverage. This establishes
neither passage relevance precision nor downstream classification improvement.
There is no universal query-policy winner from these data.

The two regressions have different interpretation. SYN-EXT-009 has no verified
blackout-specific facts, so the module query is explicitly generic; reference
coverage alone cannot establish which uncertain-history passages are most relevant.
SYN-EXT-013 does have verified insulin treatment, a recent severe hypoglycaemic
event and a two-week interval. Its flat module query repeats both translated field
labels and the original structured-addendum quotations, including many general
management fields. The returned Top 5 prioritizes general treatment and gestational
material while omitting the severe-event reference passage. This is a concrete
query-organization target for a later locked indicator-query ablation, not evidence
that every module query should be replaced or that a negated disease is present.

## Audited source fingerprints

The following are file SHA-256 values, distinct from the semantic corpus identity:

| Artifact | File SHA-256 |
|---|---|
| `outputs/experiments/judgment_comparison_v5/labels.json` | `b6b7161df9b0b0d0566158f9ad0a6864a76ce50b937d7f13f787222470004af0` |
| `outputs/experiments/judgment_comparison_v5/upstream_audit.json` | `8e911c2da851e0ee83e95c38aeabcf5e734ce5a562b48a4cf583fd62af7f12c0` |
| `outputs/experiments/corpus_quality_v1/corpus.json` | `70d853acfc7344cd2dc4b57d9af76b308acf800de0b40cde367c2e75663ff259` |
| `outputs/experiments/corpus_quality_v1/quality_review.json` | `0a69fcbfbe1eee345360b85d97833b076cf7d26cd1d19c003661618ced9d3f1f` |
