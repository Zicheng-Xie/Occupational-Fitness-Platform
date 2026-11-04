# Anchor-aware hybrid retrieval without MMR

This is a separately versioned revision of the seventh experimental method.
The production workflow, default hybrid RRF, original six retrieval methods,
first seventh-arm run and its no-MMR ablation remain unchanged.

## Mechanism and implementation

- `src/occupational_fitness_rag/evaluation/anchored_hybrid.py` implements the
  anchor-aware ranking policies. The original query receives an explicit
  weight. Per-query fusion avoids treating a vector hit from one patient facet
  and a BM25 hit from another as agreement on the same query.
- The primary candidate blends 75% original-query RRF with 25% best-channel
  RRF. Within its first ten candidates, it greedily selects complete original
  units using `0.85 * relevance + 0.15 * incremental_source_coverage / M`, where
  `M` is the largest corpus-defined source footprint in that candidate pool.
  There is no MMR or token-similarity penalty.
- Source footprints come from the existing, verified literal-containment map
  in the frozen corpus. They are independent of the patient's expected answer.
  An expanded paragraph without canonical containment retains its own source
  identity. Complete-clause ablations additionally test full literal text
  containment on the same PDF page before consolidating two narrower passages.
- `tools/run_anchored_hybrid.py` reconstructs all imported channels from actual
  saved embedding requests and responses, freezes the seven predefined
  ablations, and writes rankings without loading reference labels. Duplicate
  serialized refinement channels are verified and imported once.
- `tools/report_anchored_hybrid.py` opens the pinned references after the
  ranking inventory is complete. It reports all variants, case-level changes,
  source text, pages, cohorts, disease groups and evidence-budget effects.
- `tools/prepare_anchored_judgments.py` creates the revision's separate fixed
  judgment requests using the unchanged patient facts, prompt, judge models,
  three independent calls per condition, and 9,000-byte evidence budget.

The policies accept only original ranked channels and corpus metadata. Expected
patient source IDs, engineering outcomes and production rule decisions are not
ranking inputs. Scope remains the frozen disease module and commercial/shared
driving context. Exact source text is never rewritten or truncated.

## Frozen experiment and results

Configuration: `configs/experiments/anchored_hybrid_v2.yaml`.
Run: `outputs/experiments/anchored_hybrid_v2`.
Report: `outputs/experiments/anchored_hybrid_retrieval_v2/index.html`.
Run identity: `72ab42714860c1c3e20266fa3299b02b922a8173ed61e8a121c608c4b22ac007`.

All 539 rankings completed: seven predefined ablations across the same 77
module queries and 33 cases. The run reused the 89 shared embedding calls and
41 facet embedding calls; it made zero new model calls. The original-query
control reproduces all 77 original hybrid ranked lists exactly.

| Configuration | Original-text coverage R@5 | Coverage R@10 |
| --- | ---: | ---: |
| Original hybrid RRF | 91.85% | 98.89% |
| Previous seventh arm without MMR | 87.41% | 98.89% |
| Original-query control | 91.85% | 98.89% |
| Per-query mean, anchor weight 0.75 | 85.19% | 98.89% |
| Per-query mean, anchor weight 0.50 | 85.19% | 100.00% |
| Anchor plus best-channel fusion | 91.85% | 97.78% |
| **Anchor fusion plus source coverage** | **92.59%** | **97.78%** |
| Anchor fusion plus complete-clause consolidation | 91.85% | 97.78% |
| Per-query mean plus complete-clause consolidation | 85.19% | 98.89% |

These are macro averages over the same 45 source-labeled module queries.
The other 32 queries have no source relevance labels and are not treated as
zero recall. Source coverage counts a canonical passage only when it is itself
returned or its original text is verified as contained in a returned unit.
Exact identifier recall is reported separately.

The primary candidate improves Top5 coverage by 5.19 percentage points over
the no-MMR parent and 0.74 points over original RRF. Against original RRF it
improves one labeled scope, leaves 44 unchanged, and regresses none at Top5.
`SYN-EXT-009 / blackout` gains the complete commercial-standards unit on PDF 70,
adding coverage of `AFTD2022-BLK-COM-003`. Another required passage remains
uncovered, so fully covered Top5 scopes remain 40/45 for both methods.

Top10 coverage regresses on `SYN-EXT-012 / diabetes`, from 1.0 to 0.5. Exact
identifier R@5 decreases from 58.52% to 46.67%, reflecting expanded originals
replacing some canonical IDs. Mean module Top5 source text increases from
4,225 to 4,282 UTF-8 bytes. Replaying the unchanged case-level allocator produces
no byte-budget exclusions or blocked cases for any compared method.

Engineering-cohort coverage rises from 90.12% to 91.36%; observed complex-case
coverage remains 94.44%. These 33 cases are observed development fixtures,
including ten previously examined complex cases. They are not a sealed test
set. Corpus-footprint coverage is not an exhaustive relevance or applicability
assessment. This result does not establish better clinical judgments.

The initial import attempt is retained separately at
`outputs/experiments/anchored_hybrid_v2_import_failure`: duplicated serialized
follow-up channels caused 231 explicit failures. The import adapter was fixed
and tested before any reference scoring; ranking policies and weights stayed
unchanged. The successful run uses a new identity and does not replace that
diagnostic history.

## Top10-preserving revisions

The separate `guarded_hybrid_v3` experiment widens the real candidate pool and
protects the original RRF Top10 source footprint with an exact bounded set-cover
check. It never reads per-patient expected source IDs while ranking. Its primary
`planned_hybrid_v3_guarded_30` completes all 77 queries with **92.59% Top5** and
**100.00% Top10** original-text coverage. The report is
`outputs/experiments/guarded_hybrid_retrieval_v3/index.html`. The wider-pool
control achieves the same aggregate coverage; the gain cannot be attributed
to the guard alone. No model calls or case-budget exclusions were added.

The separately frozen `guarded_hybrid_v4` tests coverage weights 0.35 and 0.50.
Both retain 92.59%/100.00% coverage but reduce exact-ID Top5 recall to 31.85%.
These are negative ablations, not further improvements. Historical v2 rankings,
including their Top10 regression, remain unchanged.

The `semantic_guarded_hybrid_v5` ablation reuses the actual native FlagEmbedding
query/passage scores. Its candidate union contains real guarded-v3 Top10 and
original-RRF Top20 candidates. Both predeclared semantic weights, 0.25 and
0.50, protect the entire actual v3 Top10 source footprint. They complete
154/154 rankings with no guard violations and no new model calls, but Top5
coverage falls to **83.70%** and **81.48%** while Top10 remains **100.00%**.
The scores are not evidence of clinical correctness. These negative results
are retained at `outputs/experiments/semantic_guarded_retrieval_v5/index.html`;
v3 remains the preferred experimental seventh method. All policy choices were
frozen before reference scoring; no post-score weight search was performed.

## Completed judgment comparison and remaining work

The original common comparison at
`outputs/experiments/seven_method_judgment_full_v1` completed **1,782/1,782**
conditions: 1,765 accepted responses and 17 citation-contract failures. It
includes the six original methods, the seventh **v1**, and two evidence controls.
It does not evaluate the Top10-preserving revisions.

The revision's prepared requests are at
`outputs/experiments/anchored_hybrid_judgment_preparation_v2`: 33 ready payloads
and 198 planned calls, with no model calls made during preparation. The models
run serially to avoid competing for GPU memory.

The old `anchored_hybrid_judgment_full_v2` contains zero calls and is retained
as an invalid dispatch diagnostic. The runner originally selected case IDs only
from a `no_evidence` arm that was absent from this revision. The generic payload
selector and nonempty-plan checks now reject this condition. The original
judge prompt, output schema, model options and scoring contract were preserved.

The fresh `anchored_hybrid_judgment_full_v3` completed **198/198** conditions,
with 186 accepted and 12 citation-contract failures. Despite the job suffix,
it evaluates **retrieval v2 containment**, not guarded retrieval v3. The paired
audit is `outputs/experiments/anchored_revision_judgment_audit_v1/index.html`.
Llama engineering-reference agreement changes from 44/99 to 36/99, and Qwen
from 46/99 to 45/99; failures change from 1 to 9 and 0 to 3 respectively.
Qwen has three wrong-to-correct and one correct-to-wrong accepted transitions.
Improved retrieval coverage therefore has not established improved judgment.

The guarded and semantic revisions need their own frozen judgment comparison,
independent explanation/applicability review and genuinely unseen notes.
Production workflow, rules and method selection are unchanged.

The later `commercial_scope_audit_v1` found six private/mixed/incomplete vision
units in the shared frozen 94-unit corpus. Consequently these historical
recall numbers describe fixed-corpus reference coverage, not verified
commercial-only retrieval. The separate 88-unit `scope_reviewed_corpus_v2`
preserves the frozen canonical IDs but has not been reranked. Guarded v3 and
every baseline must be compared again on that same reviewed corpus before
commercial-scope or production-replacement conclusions.

```powershell
.venv/Scripts/python.exe -m tools.run_anchored_hybrid --config configs/experiments/anchored_hybrid_v2.yaml
.venv/Scripts/python.exe -m tools.prepare_anchored_judgments --common outputs/experiments/retrieval_judgment_preparation_v2 --retrieval outputs/experiments/anchored_hybrid_v2 --method planned_hybrid_v2_containment --output outputs/experiments/anchored_hybrid_judgment_preparation_v2
```

Commands require fresh output directories and preserve earlier runs. Use the
completed HTML and saved manifests to inspect existing results instead of
rerunning into those directories.
