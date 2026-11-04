# Source-bound aggregation support

This is an isolated development diagnostic for known judgment failures. Production extraction, routing, deterministic rules and upload interfaces are unchanged. The historical default aggregation prompt remains available and unchanged.

## Optional revision

Set `judgment_guidance: source_bound_v1` only in a newly frozen experiment. This revision combines three changes:

1. `evaluation/numeric_support.py` compares explicit numeric patient facts with quantity literals found in the supplied original passages. Decimal arithmetic preserves boundaries such as 9.99 versus 10 and 100 versus 100. Each relation records its original source, text fingerprint and Unicode character span. Numbers are not read from a rulebook, expected result or reference-source list.
2. `evaluation/applicability_judgment.py` adds explicit guidance about strict inequalities, OR/AND, unknown prerequisites, conditional opportunities and output-category meanings.
3. Final checks select a program-bound passage slot. Source and module identities are resolved mechanically from that slot, while the clinical finding, explanation and assessment remain model proposals. Source identity resolution does not correct an incorrect medical interpretation.

Numeric support identifies a limited set of quantities: persistent systolic/diastolic pressure, unaided hearing average, years since blackout and weeks since a severe hypoglycaemic event. It is not a complete guideline parser. A matching quantity or a true arithmetic comparison does not establish clinical applicability, satisfy treatment qualifications or decide eligibility. Missing values remain missing, boolean values cannot become numeric zero/one, and no unit conversion or rounding is performed.

The original facts, nurse note and full guideline passages remain intact. The original stage-one proposal is retained even when aggregation disagrees with it. Internal consistency warnings remain review leads; they do not rewrite the model's outcome or count as clinician judgments.

## Matched diagnostic

`tools/compare_reasoning_guidance.py` and `configs/experiments/source_bound_guidance_pilot.yaml` use five previously observed engineering cases, one for each module. Both aggregation arms use the same source-literal fact snapshot, reference evidence and a freshly generated shared first-stage proposal. Three aggregation calls are recorded per arm and judge. Llama 3 8B and Qwen3.5 4B run serially on pinned Ollama 0.40.6, at temperature zero and seed zero.

The planned workload is ten shared first stages and 60 aggregation conditions, before any structural repairs. Shared-ledger generation failures propagate to both arms with zero fictional downstream calls. Failed conditions remain in the denominator. The changed bundle is evaluated as a whole; this does not isolate the causal effect of arithmetic support from guidance wording or source-slot encoding.

```powershell
.venv/Scripts/python.exe -m tools.compare_reasoning_guidance --config configs/experiments/source_bound_guidance_pilot.yaml --prepare-only
.venv/Scripts/python.exe -m tools.compare_reasoning_guidance --config configs/experiments/source_bound_guidance_pilot.yaml --resume
```

Preparation and resume require the same source/configuration/input identities. Historical evidence is imported explicitly as `frozen_read_only`: its original retrieval-runtime declaration is validated independently from the new judge-runtime pin. No old inference results are appended to a new runtime experiment, and no new retrieval is claimed for the imported passages.

Open `outputs/experiments/source_bound_guidance_pilot_v1/index.html` for paired judgments and original-source locations. `inputs.json`, `first_stages.jsonl`, `results.jsonl`, `paired_analysis.json` and `manifest.json` retain the full experiment evidence. Treat the run as complete only when its execution audit verifies all planned keys and result fingerprints.

The completed diagnostic records all 60 conditions, ten shared first stages and 73 actual model calls, including three structural repairs. Both arms have nine engineering agreements across 30 conditions: Llama 3 has 3/15 in each arm, and Qwen has 6/15 in each arm. Three accepted pairs change from wrong to correct and three change from correct to wrong. No overall agreement improvement is demonstrated, so this revision remains optional and the default is retained. Successful final source binding does not establish reliable clinical reasoning.

The paired changes concern Qwen: `SYN-EXT-018` changes from `temporarily_unfit` to the reference category `does_not_meet_standard` in all three repeats; `SYN-EXT-006` makes the same category change, but its reference is `temporarily_unfit`, so all three become disagreements. Precise arithmetic therefore does not resolve the separate problem of licensing-category interpretation. These are observed engineering-label comparisons, not clinician adjudications.

Reference agreement, successful parsing and source-address validity are different measures. These development fixtures are not a new holdout, their labels have not been clinically adjudicated, and engineering reference agreement is not clinical accuracy. Do not compare the scores directly with the earlier original-fact encoding pilot: this diagnostic uses a different fact version and fresh shared ledgers. Compare the two arms within this frozen run.

## Original-table context revision

`tools/build_segmented_context_corpus.py` prepares a separate experimental corpus version for the identified diabetes table-context omission. Three original regions preserve the condition-row heading, the commercial column heading and the exact existing criterion cell. The condition title includes the gestational-diabetes exception; no private criterion is added.

The full composite is addressed by its individual `source_segments`, not by claiming one rectangle spans all three regions. Each segment has its own original text, PDF rectangle, text fingerprint and interval in the composed source. Coverage metadata must be recomputed: a larger commercial-column crop that lacks the condition title must not automatically count as the complete revised canonical source.

This is a targeted correction, not an assertion that all original-source semantics have received independent review. The previous 94-unit corpus and 28 canonical identifiers remain available in their frozen historical experiments. The new corpus has a new content identity. Production catalogues and indexes are not replaced, and the running reasoning diagnostic uses its original frozen corpus rather than this subsequent revision.

`outputs/experiments/corpus_context_v2/index.html` shows the completed targeted revision. It preserves 94 units and 28 canonical IDs, verifies all three segments against their original PDF regions, and recomputes coverage. One larger column crop loses its old coverage claim for the revised canonical unit because it lacks the row title. The semantic corpus fingerprint is `e81da5c99682bd8ee7ff4df7a1dbd778fbf5437e51f030870237c6d86ec7b6ab`.

Six-method query preparation supports an explicit `--corpus` argument for a separately verified revision. New query IDs bind the new corpus fingerprint, while patient facts and query wording remain attributable to the source-literal snapshot. Preparing a new shared-query artifact still executes no embedding, retrieval, graph construction or judgment calls. Strict graph identities, complete query inventories, common judgment contracts and independent source/clinical review remain required before the full comparison.

The Microsoft GraphRAG worker now rejects unknown short IDs and unmapped or out-of-module original documents, including returned context rows below the Top-k cut. It no longer silently skips an unknown text-unit mapping. This is an independently tested mapping correction; it does not mean that the ten new graph workspaces have been built or their complete index identities have been implemented.
