# Complete complex-note ten-method retrieval comparison

## Frozen cohort and inputs

The study includes every TXT input in `data/cases/complex_nurse_notes` and
`data/cases/validation_nurse_notes`: 224 plus 10, or 234 notes. They comprise
the new 200 long-form notes and the original 34 complex inputs. Original files,
older experiment results, clinical rules and production defaults are preserved.

All methods receive the entire original note as their main query, the same
predeclared requested modules and the same frozen 88-original commercial/shared
corpus. There are 357 case/module scopes and ten methods, for 3,570 conditions.
Existing module metadata supplies the scopes for the new 200 and original 14
labelled stress fixtures. The other 20 notes request all five modules. Scope
selection does not inspect expected evidence IDs or measure disease detection.

The new 200 reuse the actual accepted extraction/provenance/semantic-review
snapshots from their completed workflow study. The original 34 receive one
intake and semantic review through the current unchanged implementation. Every
snapshot is frozen before retrieval and shared across strategies. Method 7 can
form literal facets from accepted source quotations; unconfirmed proposals do
not become retrieval facts. Reference answers are not substituted for rejected
model values. This study does not repair or retest the clinical intake logic.

The new 200 contain 40 authored scenario families and five correlated variants
per family. These are engineering development stress inputs with pending
independent clinical review. They are not independently labelled clinical cases
or a sealed holdout.

## Preserved retrieval strategies

| No. | Implementation | Configuration |
| --- | --- | --- |
| 1 | Vector | Actual Nomic source/query vectors; same-module cosine ranking |
| 2 | BM25 | Existing tokenizer and sparse ranking |
| 3 | Hybrid RRF | Dense Top 20, sparse Top 30, fusion constant 60 |
| 4 | Source graph-assisted | Existing rule/source/section graph over actual RRF seeds |
| 5 | LightRAG mix | Native LightRAG 1.5.7 and actual frozen per-module graphs |
| 6 | Microsoft GraphRAG Local | Native GraphRAG 3.2.0 local context search and actual frozen indexes |
| 7 | Prefix criterion coverage v6 | Existing literal-facet plan, guarded no-MMR selection, exact five-original prefix allocation |
| 8 | FlagEmbedding | Existing pinned BGE reranker revision, 2,048-token scorer limit, actual RRF Top 20 candidates |
| 9 | Neo4j frontier criterion v3 | Actual native vector/fulltext queries and Cypher graph paths, guarded allocation and criterion transfer |
| 10 | PageIndex + RRF predicate navigation | Native PageIndex 0.4.5 tree with the existing first-party two-stage local navigator and predicate instruction |

The native frameworks keep their independent Python 3.12 environments. Model
digests, settings, corpus/vector identities, method source hashes, note hashes
and upstream fact snapshots are pinned in the experiment plan. Source graph,
Neo4j and PageIndex are distinct routes. PageIndex navigation is the existing
first-party adapter over its native tree, not a claim of native hosted chat.

Graph methods return original-source identities. Entity descriptions, graph
summaries and model-written text never replace the guideline originals. No
expected source ID is used as retrieval backfill. Failed and empty retrievals
remain visible. Scorer truncation and native navigation errors are retained in
their original worker traces.

## Integration repair and failure lineage

The first execution exposed two experiment boundary errors: missing
`source_ids_csv` in source graph document metadata, and missing successful
baseline status/module at the method-7 prefix allocator. Those 714 initial
failed records remain unchanged in `local_rankings.jsonl`.

`tools/recover_complex_ten_adapters.py` passes the required existing adapter
fields and reruns the unchanged methods in `adapter_repair/`. It verifies every
matching failed parent condition and reuses only hash-bound actual embedding
responses from the original execution. It makes no model calls, changes no
strategy weights, and sees no patient reference answers. The report explicitly
selects corrected child records for those two methods and preserves all parent
failures. Actual native method failures remain failures, not substitutions.

The first LightRAG batch had two concurrent controllers and produced 363
observations for 357 unique queries. That entire invalid batch is retained,
including one failed observation and all six duplicate observations.
`tools/rerun_complex_lightrag_serial.py` copies unchanged frozen inputs into a
separate execution instance, acquires an exclusive owner lock, and reruns all
357 queries against fresh copies of the unchanged native indexes. Primary
LightRAG scoring uses this complete serial rerun, rather than choosing
favourable duplicates or retrying only failed cases.

## Labels and metrics

The unchanged source references come from `complex_long_200.json`,
`complex_notes.json` and `validation_complex_expectations.json` in
`data/cases/gold`. There are 222 cases with nominated evidence and 273 labelled
module scopes. The twelve unlabelled cases comprise CX-MIX-03 through CX-MIX-12
and the two original CX-CTRL controls. Every case is retrieved, while unlabelled
scopes are excluded from recall denominators and remain visible in the viewer.

Report Coverage Recall@1/3/5/10, exact source-ID recall, complete nominated
evidence coverage, hit rate, MRR, case-mean coverage, retained failures, empty
results, incremental ranking latency and original-text bytes. Failure on a
labelled scope contributes zero recall. A pending method has unavailable
metrics, not fabricated zero recall. Coverage requires complete same-page,
same-module literal containment in an actually returned original. Exact-ID
recall is reported separately to make the effect of larger passages visible.

Reference lists are not exhaustive clinical relevance judgements. Their
coverage cannot establish precision over every possible relevant source, the
correct clinical interpretation of an explanation or clinical accuracy.
Hypertension has only four available originals, so its Top-5/10 metrics
saturate. Inspect Top-1/3 and per-disease results as well.

Ranking times exclude common whole-note embeddings, source/index preparation
and upstream intake. Repaired method-7 timings reuse already recorded actual
facet embeddings. Raw initial costs and all actual model responses remain
available. Model/embedding workers can overlap in this execution, so the cost
table is incremental execution evidence rather than isolated hardware speed.

A separate case-level budget replay offers the first five whole originals in
module round-robin order under a 9,000-byte serialized evidence budget. It
records all supplied and excluded originals without truncation or reference
backfill. Packet coverage and complete-case coverage are averaged over the
222 source-labelled cases. This replay makes no decision-model calls.

## Execution and inspection

```powershell
.venv/Scripts/python.exe -X utf8 -m tools.complex_ten_inputs
.venv/Scripts/python.exe -X utf8 -m tools.run_complex_ten_methods
.venv/Scripts/python.exe -X utf8 -m tools.recover_complex_ten_adapters
.venv/Scripts/python.exe -X utf8 -m tools.rerun_complex_lightrag_serial
.venv/Scripts/python.exe -X utf8 -m tools.report_complex_ten_methods
```

Existing completed conditions are preserved. Use the same frozen protocol to
continue unfinished stages; changing notes, implementation or configuration
requires a new experiment identity. Do not reuse old ranks for changed queries.

The project report is
`outputs/experiments/complex_234_ten_methods_20261027/comparison/index.html`.
It provides combined, new-200 and original-34 cohorts, per-disease metrics,
side-by-side same-case evidence, original note text, source page links and raw
ranking/audit downloads. `summary.json` must report `complete: true` before final
comparison claims. HTML, CSV and JSON are English.

This is a retrieval comparison and makes no new fitness-judgment calls. The
previous 33-case judgments and 200-case workflow/judgment results remain
separate. A later judgement experiment must fix patient facts, evidence budget,
decision model and prompt while changing only the supplied ranked evidence.

After every native worker finishes, run the independent index/database check:

```powershell
.runtime/retrieval_extensions/Scripts/python.exe -X utf8 -m tools.audit_complex_ten_native
```

The audit compares frozen native graph/vector files to the queried copies,
verifies all 88 Neo4j original texts against the corpus, preserves the PageIndex
source map, and rechecks the case, fact and implementation fingerprints.

## Completed execution results

All 3,570 final conditions are accounted for, with no failed final conditions.
The 714 initial adapter failures and the complete invalid 363-observation
concurrent LightRAG batch remain separate and unchanged. Primary LightRAG
results come from the fresh exclusive 357-query serial run. Independent checks
verified ten native module indexes, all 88 live database originals, 234
distinct input files and every frozen source/fact fingerprint. The new-200
vector/BM25/RRF Top-5/10 baselines reproduce all six previous values exactly.

| Method | Coverage R@5 | Coverage R@10 | Complete coverage@5 |
| --- | ---: | ---: | ---: |
| 1 · Vector | 63.19% | 84.80% | 58.24% |
| 2 · BM25 | 73.93% | 85.65% | 67.03% |
| 3 · Hybrid RRF | 78.33% | 84.31% | 73.26% |
| 4 · Source graph-assisted | 82.36% | 89.74% | 75.46% |
| 5 · LightRAG mix | 63.19% | 84.80% | 58.24% |
| 6 · Microsoft GraphRAG Local | 63.98% | 84.07% | 55.68% |
| 7 · Prefix criterion coverage v6 | 86.26% | 86.63% | 82.42% |
| 8 · FlagEmbedding reranking | 71.18% | 88.34% | 60.81% |
| 9 · Neo4j frontier + criterion coverage v3 | 86.02% | 89.80% | 82.42% |
| 10 · PageIndex + RRF predicate navigation | 84.86% | 92.25% | 75.46% |

Method 7 has the highest combined Top-5 nominated-original coverage (86.26%),
method 10 the highest Top-10 coverage (92.25%), and method 9 the highest
case-level shared-budget replay coverage (84.49%, versus 77.42% for RRF).
These are different metrics, not conflicting fitness-accuracy estimates. The
Top-5 difference between methods 7 and 9 is small and is not a claim of
statistical superiority. Development family correlation remains material.

The remaining priority is fitness-judgment comparison with fixed facts, model
and evidence budget, plus intake repair and independent clinical reference
review. Vision and diabetes need further retrieval work: method 7 has 70.91%
and 60.91% Top-5 coverage, method 9 has 67.88% and 62.73%, and method 10 has
81.21% and 66.67% in those modules. No production strategy is promoted here.
