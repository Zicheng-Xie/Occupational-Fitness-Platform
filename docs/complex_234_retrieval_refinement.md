# Retrieval refinement on the frozen 234-note cohort

Date: 29 October 2026. Status: completed engineering development experiment.

## Scope and reproducibility

The study refines method families 3, 4, 7, 9 and 10 without modifying production
retrieval, the rule engine, input notes, verified patient snapshots, the 88-unit
corpus, earlier method implementations or previous results. All ten original
methods remain preserved in the preceding comparison. Labels are engineering
reference lists awaiting independent clinical review.

The same 234 notes form 357 requested case/module scopes. Of these, 273 scopes
from 222 cases have nominated source references. The remaining scopes are
retrieved and recorded but excluded from reference-recall denominators. The
new 200 notes contain 40 correlated scenario families and are not 200 independent
patients. This cohort has already been used for development; these results do
not constitute unseen validation or clinical accuracy.

The frozen original experiment is
`outputs/experiments/complex_234_ten_methods_20261027`. This experiment is
`outputs/experiments/complex_234_refinement_20261029`. Its `review.html` is the
concise entry point and `index.html` provides the interactive evidence comparison.

## Implemented mechanisms

`evaluation/retrieval_refinement.py` selects up to six complete verbatim
disease-scoped sentences using the existing narrative vocabulary. Negation,
family subject, uncertainty and timing remain in the quoted sentence. These
queries do not become verified patient facts and cannot trigger a clinical rule.
Actual local Nomic sentence embeddings are saved with complete Ollama requests
and responses. Identical sentence/engine views are deduplicated. The original
method receives weight 0.65; all additional views share weight 0.35, splitting
each sentence's contribution between vector and BM25 ranks. The RRF constant
is 60. This prevents long notes from gaining arbitrary weight through more views.

The candidate pool retains the original method's candidates. Method 3 uses its
wider vector/BM25 frontier, method 4 its existing source/rule/section graph
ordering, and method 7 its original fact-planned search channels. Methods 9 and
10 use their previously executed native Neo4j response frontier and actual
PageIndex navigated leaf inventory. Their new facet scores and selection are
explicit first-party post-retrieval refinements over those frozen candidates,
not fresh native graph or tree searches. No new native calls are claimed.

A parent can enter the closure only when it contains a complete retrieved
original on the same PDF page in the same commercial/shared module scope.
Every containment is validated against actual normalized source text. The
allocator maximizes corpus-typed criterion and total original coverage at five
and ten, followed by discounted measured relevance. Every swap/replacement
must preserve the original whole-text footprints at ranks 1, 3, 5 and 10.
It is a bounded local search with a fixed limit of 32 improvements, not a
claim of a globally optimal clinical evidence packet. No final condition hit
that limit. No MMR, expected source backfill, answer labels or rule outcomes
enter the new ranking API.

Two variants per family are retained: protected allocation alone and protected
allocation with literal sentence views. These give 3,570 final primary
conditions, all successfully completed. There are 33 actual new local embedding
calls covering 263 sentence inputs, shared by the variants.

## Paired results

The following are percentages over the original scoring denominators. The
after column uses protected allocation plus literal facets for every case;
there is no per-case choice of a favorable variant.

| Method | Coverage R@5 before | After | Coverage R@10 before | After | Packet coverage before | After |
|---|---:|---:|---:|---:|---:|---:|
| 3 Hybrid RRF | 78.33 | 78.94 | 84.31 | 91.70 | 77.42 | 78.63 |
| 4 Source graph-assisted | 82.36 | 87.24 | 89.74 | 95.18 | 75.05 | 79.93 |
| 7 Criterion coverage v6 | 86.26 | 86.26 | 86.63 | 89.74 | 84.00 | 84.00 |
| 9 Neo4j frontier + criterion coverage v3 | 86.02 | 86.02 | 89.80 | 90.05 | 84.49 | 84.49 |
| 10 PageIndex + RRF predicate navigation | 84.86 | 90.29 | 92.25 | 93.71 | 81.39 | 87.02 |

No labelled query loses covered original evidence at the four protected depths.
This source-coverage property does not guarantee unchanged exact-ID recall,
first-hit order, text size, patient applicability or clinical judgment.

Exact-ID R@5 declines: method 3 from 38.52 to 30.04, method 4 from 75.58 to
43.04, method 7 from 36.63 to 32.84, method 9 from 36.45 to 33.21, and method
10 from 64.59 to 53.91. A complete parent often replaces directly returned
child identifiers. The parent text is actually returned and fully charged;
source-ID performance is not relabelled as an improvement. Mean Top5 original
text size increases by about 36, 602, 14, 10 and 380 UTF-8 bytes respectively.

The unchanged packet replay offers the first five whole originals in requested
module round-robin order, within 9,000 serialized UTF-8 evidence bytes. It never
truncates a passage or backfills an excluded passage with rank six. No byte
exclusions occurred. Higher module-level R@10 therefore does not necessarily
improve the five-original case packet, as seen in methods 7 and 9.

## Joint-prefix follow-up

`evaluation/retrieval_prefix_search.py` adds exhaustive five-source subset
selection with protected prefix ordering and a constructive old-tail completion.
It was applied to both methods 7 and 9 across every requested scope: 714
conditions and 26,410,318 five-source combinations. All conditions completed;
no ranking changed from the literal-facet variant. The raw observations and
fixed protocol are retained under `joint_prefix/`.

This verifies a limited conclusion: replacing the local search with exhaustive
five-source subset selection does not improve the current typed/all-original
coverage objective under the same pools and preservation constraints. It is
not a global limit on RAG, relevance ranking or fitness decision accuracy.

## Audit and retained implementation defect

The initial allocator had a tuple-swap error that duplicated a replacement ID.
Source validation rejected 1,164 of the first 3,570 observations. All initial
records, reports, protocol and exact implementation snapshots are retained in
`initial_attempt/`. The swap was corrected and all 3,570 conditions rerun;
earlier successful rows were not selectively substituted. A regression test
specifically covers moving an already present parent source. All 4,284 final
conditions completed with zero execution failures and 17,136 nested source
coverage checks passed. The initial 3,570 observations are additional retained
implementation evidence, not final successful conditions.

Raw model receipts, source identifiers, PDF page/section geometry, per-query
rankings, paired changes, failed initial rows, exact-ID metrics, packet replay,
byte counts and per-disease/cohort results are downloadable. Optimization
seconds exclude reused native navigation, previous embeddings and intake.
They are not comparable to total platform latency or proof of a speedup.

## Commands and files

Use the project environment from the repository root:

```powershell
python -m tools.refine_complex_retrieval prepare
python -m tools.refine_complex_retrieval run
python -m tools.refine_complex_retrieval report
python -m tools.refine_complex_prefix
python -m tools.export_complex_refinement
```

The protocol pins implementation and input hashes; an incompatible resume is
rejected. The original implementation attempt is intentionally retained with
its snapshots. Portable exports include the necessary source snapshots and
raw records, but no model weights, third-party source checkout or credentials.

| File | Responsibility |
|---|---|
| `src/occupational_fitness_rag/evaluation/retrieval_refinement.py` | Literal sentence views, bounded RRF weighting, verified parent closure and protected allocation |
| `src/occupational_fitness_rag/evaluation/retrieval_prefix_search.py` | Joint five-source subset search with nested coverage constraints |
| `tools/refine_complex_retrieval.py` | Frozen inputs, actual sentence embeddings, resumable paired 3,570-condition execution |
| `tools/report_complex_refinement.py` | Independent lineage and coverage audit, metrics, packet replay and English interactive report |
| `tools/refine_complex_prefix.py` | Complete two-method, 714-condition joint-selection follow-up |
| `tools/export_complex_refinement.py` | Final review, retained-attempt verification and hash-checked portable delivery |
| `tests/test_retrieval_refinement.py` | Critical contracts for literal grounding, valid swaps, deduplication, protected prefixes and joint selection |

## Decision

Keep production unchanged. Method 10 is a useful candidate for the next fixed
facts/model/prompt fitness-judgment comparison because its finite-budget case
coverage improved. Method 4 gives the strongest R@10 in this refinement, with
a substantial direct-ID tradeoff. Methods 7 and 9 need patient-specific condition
and exception relevance work rather than further maximization of corpus
criterion counts. Independent relevance annotation and unseen validation remain
necessary before making precision, deployment-superiority or clinical claims.
