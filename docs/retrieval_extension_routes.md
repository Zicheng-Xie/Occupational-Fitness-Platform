# Additional retrieval routes and native framework boundaries

The extension compares new retrieval mechanisms without changing the production
workflow, patient facts or the six existing experimental baselines. The exact
package wheels, reviewed repository revisions and model checkpoint are recorded
in `configs/experiments/extension_sources_v1.json`. Package installation,
index construction and completed query retrieval are different milestones.

## Route 8: original-candidate reranking with a document structure audit

Docling 2.142.0 provides native PDF layout and table extraction through
`DocumentConverter`, `PdfFormatOption` and `PdfPipelineOptions`. For this
text-layer PDF, OCR can be disabled while table structure remains enabled.
This stage checks headings, columns and table structure against the existing
original-source anchors. A structure audit cannot, by itself, be credited with
a ranking improvement on an unchanged corpus.

FlagEmbedding 1.4.2 provides the native `FlagReranker.compute_score` interface.
The candidate checkpoint is `BAAI/bge-reranker-v2-m3`, revision
`953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`. It is a cross-encoder, distinct
from an embedding model. The original query and each actual retrieved passage
are scored together. Token limits, any truncated scoring inputs, precision,
device, pair count and checkpoint fingerprint must be saved. Whole original
passages remain the evidence returned to the judgment stage.

The shared comparison retains all 94 original units. A future Docling-derived
rechunking experiment needs a separate corpus identity and source-containment
audit; it must not be mixed into the fixed-corpus method comparison.

## Route 9: source-bound Neo4j graph retrieval

Neo4j GraphRAG for Python 1.22.0 supplies `HybridCypherRetriever`, combining
native vector/full-text retrieval with a specified Cypher traversal. The
locally observed Java 25 runtime supports the documented Windows installation
route for Neo4j Community 2026.10.0; Docker is not required for the ZIP route.

The intended graph separates original-source nodes, clauses, conditions,
exceptions and explicit cross-references. Relations must point back to original
text and its page/section. Engineering source verification and clinician review
remain separate statuses. No patient reference outcome or per-case expected
source list can create a graph edge or supplement retrieval results.

Each module should have its own source label and vector/full-text indexes so
module and commercial scope apply before candidate ranking. Filtering a shared
Top20 only after retrieval would create a different scope and candidate budget
from the baseline. All returned Neo4j records must resolve to unchanged original
units. A local Python graph is not a substitute for the native Neo4j arm.

## Route 10: native PageIndex tree with bounded local navigation

`tools/pageindex_extension_worker.py` uses the installed PageIndex 0.4.5 native
`pageindex.page_index_md.md_to_tree` function. It organizes the same originals
into five module documents with section, PDF-page and source headings. Exact
original text is fenced to prevent source headings from altering the tree.
Every native leaf must retain its complete original text and match the source
page, section and identity exactly.

Native node summaries, thinning and generated document descriptions are disabled
for this configuration. Native tree construction therefore makes no model calls.
Two bounded first-party local-model stages then select PDF branches and rank
the whole original passages within those branches. The native tree, selected
branches, actual prompts, raw responses, omitted whole passages and final source
mapping are saved. Incomplete completions, context overflow or unknown node IDs
fail explicitly; there is no RRF or reference-label backfill.

This arm is named **PageIndex native Markdown index with first-party navigation**.
It does not claim to run the framework's full chat-agent retrieval. The native
local client does support local indexing and chat backends, but its legacy
`submit_query` and `get_retrieval` methods are cloud-only and deprecated. No
private clinical data is uploaded by this experiment.

The worker accepts a request JSON with exactly `corpus`, `queries`, `output`,
`preparation_identity` and `config`. Its configuration pins the local model and
runtime, PageIndex version, context limit, branch budget and original-text
budget. `--index-only` builds and verifies the native tree without model calls;
`--resume` continues only the same frozen version. Query ranking must wait for
the current local-model workload to finish.

```powershell
.runtime/retrieval_extensions/Scripts/python.exe -m tools.pageindex_extension_worker --request <request.json> --index-only
.runtime/retrieval_extensions/Scripts/python.exe -m tools.pageindex_extension_worker --request <request.json> --resume
```

## Shared interpretation

All arms return original source IDs, guideline version, page, section and text
fingerprint through the same experimental result boundary. Graph summaries,
document summaries and navigation explanations are retrieval aids, not original
evidence. Expected source labels are opened only after rankings are frozen.
Report Top5 and Top10 exact-ID recall, verified original-text coverage, complete
coverage, applicability review, failures and cost separately. The observed 33
cases are development data, not an unseen clinical test set.

## Completed fixed-corpus execution (2026-10-23)

The shared inputs at `outputs/experiments/retrieval_extensions_inputs_v1`
freeze the same 94 original units, 77 queries and 33 patient records. The
English comparison with the later source-scope qualification is
`outputs/experiments/ten_method_retrieval_v3/index.html`. Its measured rankings
remain those of the original frozen 94-unit corpus, not the reviewed subset.

| Route | Completed queries | Coverage R@5 | Coverage R@10 |
| --- | ---: | ---: | ---: |
| Original hybrid RRF | 77/77 | 91.85% | 98.89% |
| Preferred seventh method, guarded v3 | 77/77 | 92.59% | 100.00% |
| Native FlagEmbedding reranking | 77/77 | 79.26% | 92.22% |
| Native Neo4j hybrid clause graph | 77/77 | 89.63% | 94.81% |
| PageIndex tree with strict available-count navigation, v4 | 77/77 | 65.19% | 65.19% |

Coverage is a macro average over 45 source-labeled query scopes. The other
32 have no source relevance labels. Completion means an actual successful
query execution, not perfect recall, a full ten-item answer or a correct
fitness judgment. Negative results are retained without replacing production.

FlagEmbedding ran 77 native scoring calls over 1,139 real query/passage pairs
on CUDA, using FP16 and the pinned checkpoint. No scoring pair was truncated;
the maximum was 719 tokens against a 2,048-token limit. Native scoring took
16.19 seconds excluding model loading. Whole original text was returned.

Neo4j ran 77 native `HybridCypherRetriever` searches against module-specific
vector and full-text indexes. The graph has 94 originals, 94 clauses and
131 unique literal condition/exception anchors. It includes 25 verified
containment edges and 50 literal explicit-reference edges. Curated links
without a literal source mention were excluded from traversal. Index building
took 6.25 seconds; the local server was stopped after result freezing.

PageIndex v1 completed 44 queries and failed 33 when leaf IDs were returned
where branch IDs were required. The separate enum-constrained v2 completed
69 and failed eight duplicate valid branch selections. The explicit v3 recovery
preserves those earlier runs and reuses 69 successful results and all 146
actual parent calls. Stable deduplication of the eight valid branch lists
allowed eight missing final-ranking calls, for 77 completed queries and
154 actual lineage calls. It did not rerun or overwrite the parent answers,
infer unknown nodes or supplement results from reference labels.

The additional strict-cardinality v4 ablation preserves those actual selected
branches and original candidate pools. It imports 34 already-full rankings and
makes 43 actual new ranking calls, requiring exactly `min(10, available)` unique
native leaf IDs. All 43 succeed with no inferred refill or duplicate recovery.
Underfilled answers fall from 43 to zero; every branch pool still contains
fewer than ten originals. Coverage rises only to 65.19% at both cutoffs, so
narrow branch selection remains a limitation. The current lineage has 197
actual calls; the separate v1 development run adds another 121, for 318 across
the complete saved PageIndex development history. The 43 new calls take
140.02 seconds; these are stage costs, not end-to-end speedup measurements.

Docling independently parsed 34 guideline pages in 57.1 seconds, preserving
94 anchors, ten tables and 90 table cells. Of the source alignments, 31 are
literal, 60 have high token overlap and three remain partial for review.
These are lexical/geometry audit results, not retrieval recall or confirmed
column/footnote correctness. No production chunk or source text was replaced.

The native frameworks use a separate Python 3.12 environment; FlagEmbedding
uses its own CUDA environment. The main Python environment was not modified.
Raw requests, model responses, paths, original source hashes, failures,
software versions and immutable artifact inventories remain in the experiment
directories. The completed original and retrieval-v2 judgment comparisons are
separate from these new retrieval-only results.

## Later textual scope findings and reviewed subset

`outputs/experiments/commercial_scope_audit_v1` reviews all 94 source metadata
records and records exact source exposure in each method. Six vision originals
require quarantine or segmentation: two flattened private/commercial flowchart
regions on PDF 214; mixed-licence conditions on PDF 216, 217 and 218; and an
orphan private-clause continuation on PDF 219. A private subject cannot become
commercial evidence because a clipped commercial word occurs elsewhere.
Shared prose explicitly applying to both classes is not excluded merely for
mentioning private drivers.

The separate `scope_reviewed_corpus_v2` retains 88 unchanged originals and all
28 frozen canonical IDs. The edge audit confirms that no retained reference
points to a quarantined unit; no retained edge required editing. The remaining sources are not certified fully
applicable, and clinical review remains pending. Production knowledge files
and the historical 94-unit experiment artifacts are unchanged.

The fresh `ten_method_retrieval_v3` report adds this qualification to a copy of
the frozen v2 comparison; it does not alter scores or pretend to rerank the
88-unit subset. Every method needs a shared rebuilt-corpus replay. The future
`comparison_corpus.py` builder now rejects private-headed regions and flattened
standalone Yes/No chart answers before keyword scope inference. These guards
catch structural failures; they do not replace review of mixed predicates or
continuation subjects. This scope correction is a prerequisite to interpreting
commercial-only retrieval or subsequent judgment comparisons.
