# Module-query and immutable-passage comparison

This experiment addresses two observed development failures: mixed nurse-note queries can rank a decisive module-specific guideline too low, and model-transcribed quotations can fail provenance validation even when an original passage is available. Production intake, rule evaluation, routing and report generation remain unchanged.

## Run and inspect

```powershell
fitness-rag review-corpus
fitness-rag passage-comparison --retrieval-only
fitness-rag passage-comparison --resume
.venv/Scripts/python.exe -m occupational_fitness_rag.evaluation.passage_analysis outputs/experiments/passage_comparison_v1
```

Use `--max-conditions` to bound newly recorded judgment conditions. The completed first pilot uses `configs/experiments/passage_comparison.yaml` and `outputs/experiments/passage_comparison_v1`; its original source snapshot and records are frozen. The current command defaults to `configs/experiments/passage_comparison_clean.yaml` and a separate `passage_comparison_clean_v1` output using the reviewed corpus described below. Controller changes intentionally prevent incompatible resume into historical outputs. The English `index.html`, immutable input/ranking records, JSONL calls, summary and provenance manifest are written to the configured output directory. A truncated JSONL tail is rejected before append. Failed methods or responses cannot silently become another retrieval method or a successful judgment.

After recording judgments, the independent analysis command exports `paired_analysis.json` and `review.csv`. Protocol effects are paired only on identical patient/evidence payloads and model digests; query effects are paired on identical patient inputs, model digests and judgment protocols. Every explicit raw criterion, including rejected passage choices, is retained for review. Resolution fields distinguish program-selected whole original passages from model-transcribed quotes. A malformed or unknown passage ID remains unresolved; it cannot fall back to a model-invented source or quotation. Existing manual annotations survive a refresh when immutable review material is unchanged.

The first run uses the same eight known diagnostic cases as the preceding development pilot, both pinned local models, three evidence policies and two judgment protocols, with one call per condition. Its 96 conditions are a development comparison, not the original full six-method experiment or independent validation. Three repeats and independent-case acceptance remain separate requirements after the protocol is frozen.

## Query comparison

`evaluation/module_queries.py` builds a module query from that module's frozen verified field names, values and deduplicated original patient quotations. A documented false value or zero is retained. No unverified nurse-note fallback, rule result, expected outcome or expected source identifier enters this query. Original quotations retain negation, time and subject wording; this helper does not re-extract facts or establish a diagnosis. A module with no documented facts uses a visible generic commercial-module query and remains unresolved in judgment.

The `mixed_query` and `module_query` arms use the same frozen corpus, freshly computed embeddings from one pinned embedding-model digest, BM25 implementation, RRF fusion, within-module candidate limit and documented-module evidence allocation. Only their query construction differs. Top 5 original units and the common evidence byte limit are retained. The mixed arm uses the prior full-note query construction. The `reference_evidence` control replays the engineering-selected original passages and is reported separately from ordinary retrieval. Reference sources never fill missing answers in the ordinary arms.

The new queries can improve relevant ranks while harming another module. In particular, a verified negative gestational-diabetes field still contains the lexical concept. Report all included sources and unexpected matches, not only the previously missed diplopia and acute-diabetes examples. A rank improvement is a retrieval result; its effect on judgment is evaluated separately.

## Passage comparison

`evaluation/passage_judgment.py` assigns a content-addressed `PASS-...` identifier to every supplied complete original knowledge unit. The identity binds source ID, source-text fingerprint, module, page, section and text span. Evidence reordering does not rename a passage, while changed text or metadata invalidates its previous ID. A selected ID must exist in the current evidence bundle; the application does not search a larger corpus to repair an unknown ID.

Both protocols receive the same original text and anchor metadata once. The `quote_contract` arm requests short model-transcribed quotations. The `passage_selection` arm instead requests passage IDs; the application resolves them to original source IDs, full original text and offsets. Explicit fact references form the canonical fact citation list. No reference is inferred from explanation prose, and resolution never changes the model's assessment category.

Anchors cover complete upstream units to retain conditions, bullets and qualifications. They are called passages, not verified clinically complete clauses. Offsets are half-open Python Unicode-code-point positions in `source_text`, not word-level PDF coordinates or JavaScript UTF-16 positions. Original PDF page/section metadata remain attached. Selecting an original passage establishes a mechanical source link; it does not prove that the chosen standard applies or that the explanation follows from it.

Both protocols validate source-module binding and verified-field references. Structural consistency flags record contradictions among the model's own outcome, licence pathway and finding. These flags do not reject or repair the answer and do not override the model's result. A flag-free answer can still be unsupported or clinically wrong. Applicability, source support and clinical review remain pending.

## Execution integrity

Model and embedding digests, local runtime, code snapshots, configuration, corpus and upstream inputs are bound to the run. Resume requires the same identities and exact planned condition keys. Judge models run serially. Original requests, full responses, validation failures and repair attempts remain inspectable; no reference label or rule outcome is supplied to inference or validation recovery.

Patient-payload bytes, full serialized HTTP-request bytes and measured model tokens are recorded separately. Full-request limits apply again after a repair message is added. A measured context reserve is an engineering guard, not proof of semantic completeness. Transport errors, malformed provider envelopes, truncation and provenance-materialization errors are preserved rather than repeatedly sent back to the model.

The preceding diagnostic controller was repaired after its verified source code was archived under the v2 output's `source_snapshot`. A provenance-materialization failure can no longer remain marked accepted. Resume rejects an incomplete JSONL tail before writing, and posthoc completeness checks compare the manifest's complete condition set instead of only row counts. Existing v2 records were not reclassified or regenerated; their original source snapshot and output hashes preserve their historical identity.

## Acceptance

First reconcile all planned conditions, first/final validity, raw attempts, failures and provenance. Then compare unchanged-payload protocol pairs separately from unchanged-protocol query pairs. Keep reference controls separate from normal retrieval. Inspect both corrected and regressed judgments, and list failures separately. Report engineering reference agreement; clinical accuracy requires independent clinician labels.

A production change requires improved evidence coverage without unacceptable scope errors, repeated judgment evaluation on cases not used to design the change, and human review of guideline applicability and explanation support. Passing unit tests or replacing a copied quotation with a valid identifier does not satisfy those requirements by itself.

Before broadening judgment comparisons, retain the v5 upstream-fact audit: cases whose required facts were quarantined or unresolved cannot silently be treated as fully observable engineering-label tests. Audit that alignment separately, report the sensitivity cohort and preserve the original labels. The eight selected diagnostic cases do not resolve the previously documented upstream cohort issues.

## Observed retrieval development results

The pinned fresh hybrid run completed all 48 case/module/query-policy rankings. Twelve embedding batches covered the same 96 original units for both query policies. Every evidence-policy payload was prepared successfully.

| Case and module | Original reference source | Mixed-query module rank | Module-query module rank | Included in mixed/query Top-5 payload |
|---|---|---:|---:|---|
| VAL-MIX-04, vision | AFTD2022-VIS-COM-007 | 4 | 1 | No / Yes |
| VAL-MIX-07, diabetes | AFTD2022-DM-COM-003 | 8 | 2 | No / Yes |

`retrieval_coverage.json` retains all eight cases and 13 engineering-selected reference units. Exact-identifier coverage in the supplied evidence increases from 4/13 to 8/13 units; the equal-case macro average increases from 37.5% to 62.5%. Including the separate frozen-corpus `covers_source_ids` associations gives 8/13 versus 11/13 units, with equal-case macro averages of 68.75% and 87.5%. Exact and mapped coverage have different meanings and must not be merged or called clinical accuracy. The engineering-selected reference control has full coverage by construction.

This development result improves evidence availability for the two observed misses, but it does not establish generalization, passage relevance or judgment correctness. The module query also promotes a gestational-diabetes source in a case where the corresponding field is negative. Such candidates require applicability review and remain visible in the retained rankings.

## Reviewed layout quarantine

Visual inspection of Figure 11 on PDF page 119 (printed page 108) confirmed that the expanded hearing units `AFTD2022-EXP-9310f6f3ee69bc9e` and `AFTD2022-EXP-3fca0d58cbc61c75` are broken column fragments of a connected flowchart. Text was cut through boxes and the Yes/No branch relations were lost. Matching those fragments to their PDF crop proves extraction provenance but does not make them interpretable guideline evidence. Their presence means the original corpus cannot be described as having excluded every figure fragment.

`evaluation/corpus_quality.py` and `configs/experiments/corpus_quality_review.json` now produce a separate reviewed-exclusion corpus with 94 units, preserving all 28 canonical source IDs and every retained original text. The review pins the original corpus, source PDF and exact excluded unit fingerprints. Stale or unreviewed exclusions, protected-source removal and incompatible output reuse are rejected. Any removed graph edges remain recorded as unresolved quarantined targets. No figure meaning or new clinical criterion is reconstructed automatically.

`review-corpus` checks the original and revised PDF text regions, then writes `outputs/experiments/corpus_quality_v1`. The comparison loader explicitly supports this reviewed override and rejects removal of a reference-control source. A fresh retrieval-only run on the revised corpus is separate from the completed 96-condition pilot. Its judgment conditions remain pending; historical pilot scores cannot be relabeled as results on the revised corpus. This quarantine addresses two confirmed layout failures and is not full semantic or clinical approval of the remaining 94 units. Production knowledge is unchanged.

## Completed first-pilot judgment results

All 96 planned conditions were recorded with 119 model attempts: 78 accepted final outputs and 18 failures. Sixteen failures were quotation mismatches and two were source-module mismatches. The original runtime source matched its snapshot when execution completed; subsequent quality-revision code has a separate identity.

| Model | Protocol | First valid | Final valid | First engineering agreement | Final engineering agreement |
|---|---|---:|---:|---:|---:|
| Llama 3 8B | quote_contract | 16/24 | 19/24 | 2/24 | 2/24 |
| Llama 3 8B | passage_selection | 23/24 | 24/24 | 1/24 | 1/24 |
| Qwen 3.5 4B | quote_contract | 11/24 | 12/24 | 4/24 | 5/24 |
| Qwen 3.5 4B | passage_selection | 23/24 | 23/24 | 11/24 | 11/24 |

These denominators include failures and pool three evidence policies, including the engineering-selected reference control. They are not independent patient counts or clinical accuracy. Passage selection improves final output validity from 31/48 to 47/48. Qwen's agreement increase chiefly comes from previously failed conditions becoming valid: seven such conditions now agree with the engineering reference, while one previously accepted correct condition regresses. Among accepted, identity-matched protocol pairs there are no wrong-to-correct transitions. Llama also has one correct-to-wrong transition. Query-policy pairs show no accepted wrong-to-correct transitions despite better reference-source coverage. Thus retrieval availability, output validity and correct evidence application remain separate outcomes.

Structural flags appear in 23/24 Llama passage conditions and 10/24 Qwen passage conditions. Flag absence does not establish support: a model can consistently assert an incorrect interpretation of an unconditional-only clause or a diagnosed blackout. VAL-MIX-04 still receives an incorrect category after the commercial diplopia exclusion is supplied. VAL-MIX-07 demonstrates that a retrieved acute restriction can be ignored in favour of general treatment text. These failures require applicability, polarity, prerequisites and numerical interpretation work rather than further relaxing citation validation.

`review.csv` preserves 328 raw criterion-attempt items with pending human review. The current quality-revised retrieval stage has completed 48/48 rankings using 94 units and returns neither quarantined unit; the two target clauses remain supplied at module ranks 1 and 2. It records 0/96 judgment conditions. The project suite passed 390 tests after the quality revision, with Ruff passing for `src` and `tests`. Repeated independent-case judgment evaluation and clinician review remain outstanding.

The next [applicability-first experiment](applicability_comparison.md) imports those
reviewed-corpus retrieval inputs unchanged into a separately fingerprinted run. Its
contemporary control is `passage_selection`; the new arm records passage applicability
before independent aggregation. This does not complete or rebind the historical
`passage_comparison_clean_v1` judgment manifest, which remains at 0/96. The new run has
its own planned conditions, code snapshot and measured results.
