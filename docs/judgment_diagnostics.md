# Frozen-input judgment diagnostics

This development pilot tests two separate interventions after the completed v5 comparison: how evidence slots are allocated and how a local model records a provisional judgment. Production extraction, rules, routing, retrieval configuration and reports remain unchanged.

## Run and preserve the baseline

The completed v2 directory is frozen. Its verified original runtime source is retained in `source_snapshot`. Subsequent controller repairs intentionally change the current code identity, so resuming that completed directory with current source is rejected. Use the new [passage comparison](passage_comparison.md) for the next experiment. To run a fresh instance of this historical protocol with the repaired controller, provide a configuration with a separate output directory; do not overwrite v2.

```powershell
.venv/Scripts/python.exe -m occupational_fitness_rag.commands judgment-diagnostics --config <fresh-diagnostic-config.yaml>
```

The configuration is `configs/experiments/judgment_diagnostics.yaml`. Results are written to `outputs/experiments/judgment_diagnostics_v2`. `--max-calls` limits newly recorded conditions for a technical smoke check; omitted conditions remain pending. Resume rejects changed configuration, source code, input, model or runtime identities. Original v5 cases, corpus, labels, source rankings and 1,584 calls are read as immutable inputs.

The first two-condition smoke is preserved in `judgment_diagnostics`, with its stopped-for-revision reason. Its model repeated criterion fact references but omitted an optional redundant top-level fact list; both failed attempts remain recorded. The revised wire contract avoids asking the model to duplicate mechanically derivable lists. This is a protocol change, so the new run has a separate identity and output directory.

## Fixed conditions

The pilot selects eight known cases: SYN-EXT-002, SYN-EXT-003, SYN-EXT-008, SYN-EXT-020, and VAL-MIX-02/04/06/07. It includes unconditional-only and diagnosed-cause negative controls as well as restrictive cases across all five modules. These cases helped identify the defects, so this is a **targeted diagnostic development set**, not an independent validation or clinical test set.

Eight cases, three evidence policies, two protocols, two models and one call per condition give 96 planned conditions. An explicitly bounded validation repair can add one attempt per condition. Conditions and attempts are reported separately. The common generation budget is 8,192 context tokens and 2,048 output tokens. v5 used a smaller output allowance; compare protocols using this run's contemporaneous baseline, not historical raw accuracy or latency differences.

The Llama model digest matches v5. The installed Qwen tag now has a different digest from v5, modified after the previous experiment. Both current digests are pinned in the diagnostic configuration and recorded in the manifest alongside historical digests and the local runtime version. Every new condition rechecks the configured tag before inference. No weights are downloaded or replaced. Qwen gains across the two experiment directories cannot be attributed to a protocol change; only same-digest contemporary pairs are eligible.

## Evidence allocation

| Policy | Behavior |
|---|---|
| hybrid_fixed | Replays the exact v5 Top-5 evidence payload, including its original byte-budget decisions. |
| documented_modules | Reuses v5 per-module hybrid Top-10 rankings, allocating Top-5 slots across requested modules that have verified non-null facts. |
| reference_evidence | Replays engineering-selected diagnostic evidence; this control intentionally uses reference source selection. |

`evaluation/evidence_selection.py` does not read thresholds, rules, reference labels, expected source IDs or source text. Documented `False` and `0` remain documented facts. If all facts are missing, allocation falls back to all requested modules. Within-module rank and source identity are preserved; failed rankings cannot silently become successful. Requested modules remain in the judge input, so unmeasured modules are unresolved rather than declared normal. Original text still passes through the common evidence byte limit.

The allocation change can recover a lower-ranked paragraph when unmeasured modules previously occupied slots. It cannot recover a relevant source that is ranked too low within its module, determine clinical relevance or complete missing guideline content. Source changes must be checked case by case.

## Judgment protocols

`evaluation/evidence_judgment.py` preserves the v5 baseline prompt and schema for the baseline arm. The `evidence_contract` arm changes both category instructions and the output schema; it is an **evidence-contract intervention**, not a pure prompt-only ablation.

The model records concise criterion checks: module, explicit source ID, short original quotation, verified fact fields, licence pathway, finding and conclusion. The model-facing response contains the outcome, explanation and checks. Canonical source and fact citation lists are derived deterministically from explicit check references, in supplied source/field order. No reference is inferred from free prose, gold labels or expected source lists, and aggregation never changes the predicted outcome.

Checks must cite actual supplied sources, requested modules and verified fields. A restriction check requires a verified fact. Quotations must match the exact original wording and punctuation, allowing PDF whitespace wrapping. The application computes half-open character spans against the original passage; repeated occurrences retain all locations rather than inventing a unique position. These spans are passage-text offsets, not word-level PDF coordinates.

Unconditional licensing failure is distinguished from an explicit exclusion of both unconditional and conditional pathways. An established current no-driving restriction is distinguished from an unknown module. A diagnosed-cause blackout must not automatically inherit an investigation-stage restriction. These meanings define the experimental response categories; final applicability and explanation support still need independent review.

## Bounded validation recovery

`evaluation/judgment_diagnostics.py` saves every attempted request fingerprint, raw response, error and duration. One repair is allowed for response validation failures. The correction message contains the validation error and previous output but no correct outcome, reference label, rule result or expected source. A transport failure, truncated response or exhausted context is recorded and not repaired. The controller does not insert a quotation, source, patient fact or assessment outcome itself.

First-attempt validity/agreement and final validity/agreement are separate metrics. The same recovery limit applies to both protocols. A recovered response does not erase the first failure. Success means the output contract passed; it does not establish semantic support or clinical correctness.

## Interpretation and source designs

Open `index.html` in the diagnostic output to inspect original evidence, frozen facts, criterion checks, quotation locations and every failed attempt. `summary.json` contains same-input/same-digest protocol pairs. The independent posthoc analysis compares evidence-policy pairs separately from protocol pairs. A failed pair is not counted as a successful wrong-to-correct judgment. Changed evidence bundles support an association, not the causal contribution of a single passage.

The inspected upstream implementations and pinned source files are documented in [the open-source design review](open_source_design_review.md). The local implementation uses its own small contracts and adapters; no third-party source tree or new framework dependency is introduced. Quote provenance follows citation-builder discipline, validation recovery follows explicit bounded branches, and support-review records separate claims from source validity. Automated quotation matching is not a Ragas faithfulness score and does not replace a clinician.

After this pilot, review regressions and support failures, then freeze a revised protocol and run repeated, independent-case evaluation before proposing a production change. Known-error development performance cannot establish generalization.

## Completed development pilot: 15 October 2026

All 96 unique conditions were recorded, with 120 model attempts including bounded validation repairs. There are 75 accepted final outputs and 21 final failures: 19 quotation mismatches and two non-English criterion conclusions. The raw file has no incomplete trailing record. Experiment code identities match the manifest, and the four original v5 baseline artifacts retain their recorded hashes.

The following agreement counts use **all 24 planned conditions per model/protocol**, including failed outputs in the denominator. They pool three evidence policies, including a reference-evidence control, and therefore are not a ranking of deployed retrieval methods.

| Model | Protocol | First accepted | Final accepted | First agreement | Final agreement | Model attempts |
|---|---|---:|---:|---:|---:|---:|
| Llama 3 8B | baseline | 23/24 | 24/24 | 6/24 | 6/24 | 25 |
| Llama 3 8B | evidence_contract | 15/24 | 15/24 | 2/24 | 2/24 | 33 |
| Qwen 3.5 4B, current pinned digest | baseline | 24/24 | 24/24 | 4/24 | 4/24 | 24 |
| Qwen 3.5 4B, current pinned digest | evidence_contract | 10/24 | 12/24 | 5/24 | 7/24 | 38 |

The intervention is not accepted for production. Qwen has some corrected judgments but substantial contract failures and regressions; Llama regresses overall. Under the reference-evidence control, Llama corrects SYN-EXT-003 and VAL-MIX-06 but breaks SYN-EXT-002 and SYN-EXT-008. Exact quotations can pass while the model still misinterprets licence scope or the final category. For example, VAL-MIX-04 supplies the commercial diplopia exclusion, but neither model's accepted contract answer matches the engineering category. Its accepted output is not evidence that the interpretation is supported.

Reallocating evidence slots recovers a lower-ranked blackout passage for VAL-MIX-06, but still misses the decisive commercial diplopia entry for VAL-MIX-04 and the acute diabetes entry for VAL-MIX-07. In the baseline protocol it produces no correct/incorrect transition in either model. In the contract protocol too many failed pairs remain to claim an evidence-policy gain. These observations distinguish evidence coverage from judgment performance; simply changing retrieval allocation does not resolve the reasoning defects.

The quotation failures include altered punctuation/spacing, but also wrong-source attribution and patient wording presented as guideline text. Do not weaken matching globally to increase acceptance. A subsequent, separately versioned experiment should give immutable passage/clause identifiers to the model and derive quoted text and locations from selected identifiers. This can remove copying errors without repairing a wrong clinical interpretation. Scope, polarity, conditional prerequisites and conclusion support still need separate review.

Export the independent analysis and review worksheet after a run:

```powershell
.venv/Scripts/python.exe -m occupational_fitness_rag.evaluation.diagnostic_analysis outputs/experiments/judgment_diagnostics_v2
```

`diagnostic_analysis.json` contains both protocol and evidence-policy comparisons, first/final stages, identity exclusions, changed sources and snapshot fingerprints. Its 160 paired-stage records are comparisons of the 96 conditions, not extra model runs. `review.csv` contains 201 criterion-attempt review items, including parseable checks in rejected attempts. It retains full original passages, quoted spans and referenced facts; all support, applicability and clinical review fields start pending. Refresh preserves manual annotations and rejects changed immutable source material. These 201 items are separate from the v5 retrieval review queue; neither queue has been automatically approved.

The full project test suite passed 328 tests, and Ruff passed for `src` and `tests`. Browser checks verified the English report, case/model selectors, source details and failed-attempt visibility. Remaining acceptance work is a revised clause-selection protocol, targeted per-module evidence coverage, repeated evaluation on independent cases, and human source/applicability/support review. The completed v5 experiment and the production workflow remain unchanged.
