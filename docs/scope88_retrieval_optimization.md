# Retrieval optimization on the scope-reviewed corpus

This experiment improves the seventh, ninth and tenth retrieval routes while
preserving production extraction, semantic review, rule routing and decisions.
The original 94-unit experiments remain immutable. Current measurements use the
same reviewed 88 originals, 33 observed development cases and 77 module queries.
Six known private/mixed-scope or incomplete vision sources are quarantined;
the remaining sources still require layout, textual applicability and clinical
review. In particular, retained Blackout source
`AFTD2022-EXP-1292b0286ae90dcd` contains truncated Figure 6 branch fragments.
Its frozen text is not silently repaired during this comparison; a future
pinned layout review must resolve it before claiming a clean production corpus.

## Shared preparation and query lineage

The shared preparation is `outputs/experiments/scope88_shared_retrieval_v2`,
identity `9078f138685815a62c44e654d7535f631658e90120e11e36d48245a738970b88`.
Its corpus identity is
`71f41fdccbcafad1a212641b906724c5ced5f486188daee98b7e6af4ffb0d70f`.
Every query metadata record now binds this corpus, with a freshly computed
query ID and an explicit mapping to the historical query ID. Literal query
text, patient facts and original source text are unchanged.

The earlier preparation v1 retained historical query metadata. Its native
FlagEmbedding execution is saved as development history, including all actual
calls. It does not replace the corrected v2 comparison. The two preparations
have identical logical rankings and channels after query-lineage mapping.

Vector and lexical candidate lists are recomputed over the reviewed corpus.
BM25 document statistics and RRF fusion therefore use the actual retained
sources, rather than a filtered copy of an old Top10 list. The original
embedding vectors are reused only after exact query/source-text verification
against recorded native embedding responses. New indexing and model calls are
distinguished from imported historical work.

## Seventh route: exact criterion-prefix allocation

The fresh guarded-v3 control starts from the recomputed 88-source channels.
The new prefix policy retains its ten actual source IDs and chooses the first
five by exact coverage of corpus-defined criterion atoms, preserving the
control's existing Top5 criterion coverage. Ties use original ranking relevance.
A stricter full-original-footprint policy is retained as a separate control.
No expected patient source IDs, reference outcomes, inferred clinical predicates
or new passages enter ranking.

On the 45 source-labeled development scopes, the fixed criterion-prefix policy
reaches 95.56% Top5 and 100.00% Top10 original-text coverage, compared with
92.59%/100.00% for guarded v3 and 91.85%/98.89% for original RRF on this corpus.
Fully covered Top5 scopes increase from 40 to 42. Both gains occur in queries
without verified module facts; they establish broader criterion allocation,
not better patient-predicate understanding. Query-level recall and actual
case-level evidence allocation must be reported separately.

Implementation: `evaluation/prefix_allocation.py` and the corresponding isolated
runner/report tools are experimental. The authoritative file names and hashes
are recorded in `scope88_prefix_allocation_v6/manifest.json` and its artifacts.

## Ninth route: native engine fusion and bounded literal graph paths

Neo4j supplies real module-scoped vector/full-text indexes and native queries.
The revision fuses native engine ranks and restricts traversal to verified
literal containment and explicit references. Generic shared-condition anchors
no longer dominate the final ranking. Candidate paths are prioritized by
actual query relevance rather than source-ID ordering. Separate controls test
engine fusion, graph fusion and coverage protection.

The first frozen run is `scope88_neo4j_strategies_v2`; its original native
control reaches 89.63%/94.81% coverage and its guarded graph revision reaches
92.59%/98.89%. A separately frozen adaptive transfer experiment tests typed
criterion allocation using only the recorded native candidate frontier. Its
results are separate from this first comparison. The native-frontier criterion
allocation variant reaches **95.56% Top5 and 100.00% Top10**, with 42/45 fully
covered Top5 scopes, compared with 40/45 for the first guarded graph revision.
It reuses actual native candidate and Cypher results, rather than synthesizing
new graph retrieval. Exact-ID Top5 recall is 48.89%. These operations make no
clinical predicate-entailment claim.

## Tenth route: native tree control and hybrid branch coverage

The pure-tree control rebuilds the native PageIndex hierarchy for the reviewed
corpus. Unchanged module executions may be reused only when source inventory,
literal prompts, actual native nodes and raw outputs remain equivalent through
query lineage. Changed vision branches are evaluated anew.

The hybrid branch-coverage revision seeds additional native branches from the
actual reviewed-corpus RRF Top20. Whole originals are packed with a 20,000-byte
candidate limit, and the local model ranks exactly `min(10, available)` unique
native leaf IDs. A second ablation adds explicit negation and temporal-state
instructions. Neither arm fills results from reference labels. This is native
PageIndex indexing with first-party local navigation, not the framework's full
chat retriever. See `tools/run_scope88_tree.py` and `tests/test_scope88_tree.py`.

All 231 tree conditions complete without failures. They use 178 new local-model
calls and 130 actual historical calls for unchanged contexts. The fresh pure
tree control scores 60.74%/60.74%; RRF branch coverage scores 87.04%/92.22%;
the predicate-instruction ablation scores 87.04%/97.78%. The latter is the best
observed development variant by Top5 then Top10 coverage. It was a predefined
ablation, not the prespecified primary; development selection must remain
explicit. The native Markdown tree is real, while the navigation and RRF
seeding are first-party hybrid strategies.

## Measurements and remaining evidence

All methods share corpus version, query wording, disease scope and source
reference labels. Expected references are read only after the corresponding
rankings are frozen. Report exact-ID recall separately from verified original
containment coverage, and count failed attempted queries in their denominators.
The 32 query scopes without source labels do not receive invented recall values.

The unchanged judgment allocator supplies at most five whole originals per
case within 9,000 UTF-8 JSON bytes, using documented-module round robin.
Query-level Top5 improvement can therefore differ from the coverage actually
supplied to a model. Replay both selection and byte limits before describing
downstream effects. No new fitness judgment is implied by retrieval completion.
The seventh and ninth primary routes reach 82.22% and 84.44% actual packet
coverage, respectively, versus 80.74% for RRF. The selected tenth-route variant
reaches 84.81%. These measurements use the same 45 labeled scopes; reference
lists are incomplete and additional criteria are not automatically irrelevant.

For the two seventh-route gains, the single-module `SYN-EXT-009` source pack
does improve from 66.67% to 100% blackout reference coverage. The five-module
`VAL-MIX-10` pack remains byte-identical under round robin; its blackout
reference coverage remains zero. Among the 40 labeled scopes with verified
module facts, seventh-route Top5 coverage stays 95.00%. Its aggregate gain
comes from the five labeled empty-fact scopes. Additional criterion coverage
must therefore not be described as better fact-specific interpretation.

All 33 cases have already been observed during development. The next evidence
is independent applicability review, paired judgments with fixed requests, and
evaluation on genuinely unseen cases. No production retrieval default is
automatically replaced by an experimental ranking.

## Native graph replay and retained costs

LightRAG mix and Microsoft GraphRAG Local Search complete all 154 conditions on
the reviewed source inventory. Eight exact unchanged native module indexes and
130 query results are reused with 620 recorded historical model calls. Both
vision indexes are rebuilt over 27 originals and supply 24 new query results.
The new work records 221 actual model calls, including three failed intermediate
calls; final retrieval conditions all complete. Intermediate failures remain
visible and do not become silently successful calls. The three failures exhaust
one exact Microsoft vision entity-extraction request for
`AFTD2022-EXP-a09b64ac70a92828` (PDF 220), without recovery. Its original text is
stored but has no linked entities or relationships. This index is partially
constructed; Microsoft's 64.07%/83.70% is a provisional measurement of that
degraded run, not a clean framework-quality comparison. No fitness judgment
runs in this replay.

The consolidated English report and machine-readable comparisons are at
`outputs/experiments/scope88_optimization_comparison_v2/index.html`. Its v1 remains
immutable history; v2 adds the graph-construction qualification without changing
rankings or scores. All earlier 94-unit results, metadata diagnostics and strategy
controls remain separate.
