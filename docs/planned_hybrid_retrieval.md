# Planned Hybrid RRF

This is a seventh, independently versioned experimental retrieval method. It
does not change production routing, extraction, semantic review or rule decisions.
The original six methods and their saved results remain separate.

## Reviewed implementations

The connected GitHub service was used on 23 October 2026 to inspect the user's
forks, not an assumed upstream branch. The project repository does not contain
local copies of these checkouts.

| Fork | Inspected revision | Relevant designs |
|---|---|---|
| [WeKnora](https://github.com/Zicheng-Xie/WeKnora/tree/eecfe4b3c8c34c94e9b559e5dd02187b4ae447cd) | `eecfe4b3c8c34c94e9b559e5dd02187b4ae447cd` | Independent retrieval channels, best rank per retriever type, normalized fusion, bounded keyword expansion, passage diversity |
| [DeerFlow](https://github.com/Zicheng-Xie/deer-flow/tree/18ca09b2dac76e26cbdcbbc6936be4f6f166283f) | `18ca09b2dac76e26cbdcbbc6936be4f6f166283f` | Explicit step tracking, scoped knowledge contracts, source identity tied to returned evidence, evidence-preserving budgets |

Exact file paths, Git blob identifiers, URLs, license observations and adaptation
boundaries are in `configs/experiments/planned_hybrid_sources.json`. These are
design adaptations implemented here; neither complete external framework is
installed or executed by this method. No third-party source directory is copied.

## Implementation map

| File | Responsibility |
|---|---|
| `src/occupational_fitness_rag/evaluation/planned_hybrid.py` | Fact-family planning, scoped dense/BM25 channels, best-channel RRF, lexical inspection, one bounded refinement round and MMR |
| `tools/run_planned_hybrid.py` | Verify shared inputs and actual vector responses; pin sources and runtime; record new calls; reconstruct rankings before finalizing |
| `tools/report_planned_hybrid.py` | Import the six methods without editing them; score only after ranking; compare recall changes and the diversity ablation |
| `tools/run_frozen_retrieval_judgments.py` | Submit exact common requests with independent repetitions; append the seventh arm with identical patient and evidence-allocation contracts; retain raw failures and paired judgment changes |
| `configs/experiments/planned_hybrid_v1.yaml` | Explicit query, model, corpus and bounded execution settings |
| `configs/experiments/planned_hybrid_sources.json` | Reviewed fork revisions, file identities, license observations and limits of adaptation |

`plan_query` keeps nested families such as left/right acuity together, while
flat disease fields remain separate groups. More than four groups are combined
into bounded contiguous partitions; no documented field is discarded. The
planner does not use a model to invent search facts or clinical conclusions.

## Retrieval sequence

1. **Plan:** retain the original shared query. Partition all verified fields into
   at most four facets, retaining values and exact source quotations. No free-form
   model rewrite is used. Missing information creates no synthetic normal fact.
2. **Search:** run vector and BM25 retrieval for the original query and each
   facet. Reuse audited original-corpus and original-query vectors. Facet vectors
   are real new embedding calls with raw responses and model digest pins.
3. **Inspect:** record lexical overlap between facet field terms and the first
   five fused original passages. This is a query coverage diagnostic, not medical
   evidence support, criterion satisfaction or clinical sufficiency.
4. **Refine:** for weak lexical coverage, run at most two keyword-only searches
   using unchanged patient quotations. There is at most one refinement round.
5. **Finalize:** fuse by best rank within each retriever type, then select up to
   ten original units with MMR (relevance weight 0.7). Retain all source metadata
   and original text. Never truncate a medical qualifier or generate replacement
   evidence. A separate ablation removes only this final diversity selection.

The fusion score is `(1/(60+best_vector_rank) + 1/(60+best_bm25_rank)) / (2/61)`;
an absent channel contributes zero. Repeated copies of the same query do not add
votes. Raw channel scores and every source's channel/rank path remain visible.
MMR uses normalized fusion relevance and token-set Jaccard passage redundancy.

All search stages enforce the requested disease and commercial/shared scope.
Private-only evidence is excluded. Failed embeddings or empty retrieval produce
recorded failures, never an unannounced BM25-only or unfiltered substitute.

## Fixed comparison and execution

The method uses the existing 94-unit corpus, 33 frozen patients and 77 shared
module queries. Engineering reference source IDs and expected outcomes are not
available to the planner or retriever. References are opened by the reporter
only after the new ranking inventory is complete. No reference source is added
to fill a missed answer. The remaining 32 source-unlabeled scopes do not receive
fabricated relevance scores.

Run serially after any active local graph/model experiment:

```powershell
.venv\Scripts\python.exe -m tools.run_planned_hybrid --config configs/experiments/planned_hybrid_v1.yaml
```

Use `--resume` only for exactly matching source, model, corpus and query identities.
Do not edit bound source files during a run. Completed rankings reconstruct from
retained real embedding responses before an execution audit is written.

Generate a new report, keeping the imported six-method version intact:

```powershell
.venv\Scripts\python.exe -m tools.report_planned_hybrid --six outputs/experiments/six_method_retrieval_v2 --output outputs/experiments/seven_method_retrieval_v1
```

The English HTML compares original passages side by side, exposes the stage
trace, and filters cases, diseases and recall changes. JSONL, CSV, source pins and
actual new model-call counts accompany it. The diversity ablation is labeled
separately from the seven main methods and makes no additional embedding calls.

Retrieval recall is not fitness judgment accuracy. The shared-model comparison
must keep patient facts, judge prompts, evidence budgets and repetitions fixed;
it must separately report changes in judgment and their agreement with the
engineering reference. Extra query embedding costs must remain visible.

After a new common preparation passes its graph-completion and source gates,
run the first single-module case of each disease, retaining three independent
calls per model and method:

```powershell
.venv\Scripts\python.exe -m tools.run_frozen_retrieval_judgments --preparation outputs/experiments/retrieval_judgment_preparation_v2 --additional outputs/experiments/planned_hybrid_v1 --output outputs/experiments/seven_method_judgment_pilot_v1 --pilot
```

The original six methods plus two controls still form their own 1,584-condition
matrix. Appending the seventh method adds 198 conditions (33 patients, two
judges, three calls), for 1,782 conditions; it does not rename or overwrite the
original matrix. The five-disease pilot contains 270 of these conditions, with
its own identity and scope. Omit `--pilot` and use a new output directory for the
full comparison. No identical-body deduplication replaces an independent call.
Incomplete completions, invalid citations and context failures retain their raw
responses. They are not repaired silently or dropped from recorded denominators.

## Observed first-version retrieval results

The completed run is `outputs/experiments/planned_hybrid_v1`, with 77/77
successful rankings, 41 actual new embedding calls, 108 facet inputs and 45
keyword follow-ups. The seven-method report is
`outputs/experiments/seven_method_retrieval_v1/index.html`. The original
six-method report and graph reconstruction have separate versioned directories.

| Method / separate ablation | Original-text coverage R@5 | Coverage R@10 | Fully covered @5 |
|---|---:|---:|---:|
| Existing hybrid RRF | 91.85% | 98.89% | 40/45 |
| Planned Hybrid RRF | 78.89% | 89.26% | 34/45 |
| Same planned channels without final diversity | 87.41% | 98.89% | 38/45 |

Against existing hybrid RRF, the new method has seven lower-coverage scopes,
38 unchanged scopes and 32 unlabeled scopes. No labeled scope improved its
Top-5 coverage. The engineering cohort is 90.12% versus 68.52%; the complex
validation cohort is 94.44% for both. This first version is an experimental
comparison arm, not a recommended replacement for production RRF.

The diversity ablation improves six scopes and worsens one relative to the
full new method. For example, the Blackout standards unit
`AFTD2022-EXP-bbf242d555576d02` is in the first five results before diversity for
`SYN-EXT-006`, but absent from the first ten afterwards. In `SYN-EXT-001` vision,
the complete commercial-standards unit `AFTD2022-EXP-a09b64ac70a92828` also leaves
the first five. Broad topical diversity can displace complementary medical
criteria and qualifications. A future revision should test original-criterion
coverage and main-query relevance before adopting a generic diversity penalty;
it must preserve this first run and use a new experiment identity.

These are retrieval findings. Whether a change produces a correct or incorrect
fitness judgment is measured separately by the fixed-request model comparison.
No clinical accuracy or general superiority is inferred from these fixtures.

## Original comparison status

The stricter external graph reconstruction, `external_graph_retrieval_v3`, has
completed 154/154 rankings and ten module indexes with a 4,096-token output cap
and rejection of incomplete native completions. Its 882 actual model/embedding
calls had no failures or completion rejections. The new six-method report
`six_method_retrieval_v2` has zero length-stop flags; original-source checks pass.
The refreshed common preparation has 264 ready payloads and 1,584 planned calls.
The separate seventh-arm pilot has completed 270 actual calls: 267 outputs
passed the fixed contract and three BM25/Qwen vision outputs failed the required
source-citation check. Raw responses are retained. In this five-case pilot,
existing RRF and the new method each have 60% engineering reference agreement
for both judges. Qwen gains agreement on `SYN-EXT-018` but loses agreement on
`SYN-EXT-010`; repeated calls do not turn these into additional independent
patients. The separate 33-case, 1,782-condition comparison is running.

`tools/report_judgment_evidence_changes.py` produces a read-only paired view at
`outputs/experiments/seven_method_judgment_evidence_v1/index.html`. It verifies
identical patient data, judge settings and original text for shared source IDs,
then exposes additions, removals and changed evidence order. The view does not
attribute a change to one passage alone. An auxiliary literal audit in
`outputs/experiments/planned_hybrid_validation_v1/claim_trace_audit.json` flags
prose citation identifiers and possible assertions that a supplied fact is
missing; these checks do not substitute for clinical explanation review.

Historical length-limited results remain available. The seventh method does not
replace either graph framework or complete the pending independent clinical review.
