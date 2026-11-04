# Shared-query retrieval execution

`tools/run_shared_retrieval.py` executes dense vector retrieval, BM25, hybrid RRF and the existing source/rule/section graph-assisted retriever on one frozen corpus and query preparation. This stage does not implement or substitute for LightRAG `mix` or Microsoft GraphRAG Local Search. Those two methods remain pending.

## Frozen inputs and execution

The completed `outputs/experiments/shared_retrieval_v1` run uses the 94-unit original-table context revision, 33 source-literal patient inputs and 77 identical case/module queries from `six_method_query_preparation_v2`. Its corpus fingerprint is `e81da5c99682bd8ee7ff4df7a1dbd778fbf5437e51f030870237c6d86ec7b6ab`.

The run records 308/308 case/module/method rankings, with zero failures. The pinned local runtime is Ollama 0.40.6 and the embedding model is `nomic-embed-text:latest`, pinned by its recorded weight digest and 768 dimensions. There are 89 actual embedding calls: 12 corpus batches and 77 query calls. Corpus and query embeddings are shared across the vector-based methods; they are not billed repeatedly as new calls. No judgment calls are executed in this stage.

Candidate sources are filtered by the requested module before ranking. Commercial/shared original units use the same frozen corpus for every method. Vector ranking uses cosine similarity; BM25 uses its direct keyword score; hybrid uses RRF with constant 60, vector Top 20 and sparse Top 30. The local graph arm expands actual source, rule-source and section associations; it does not use case-specific expected source IDs or triggered rule outcomes.

Original source IDs, scores, graph paths, query fingerprints and per-query embedding status are retained. An embedding failure cannot become a silent lexical fallback. Before completion, every saved ranking is reconstructed deterministically from the frozen queries and vectors. Runtime/model pins, tool/source identities and original PDF text are checked. Reference inputs are opened for scoring only after all rankings are fixed.

## Engineering reference-source results

There are 45 case/module scopes with reference-source labels among the 77 queried scopes. The other 32 are not assigned an invented recall value. Recall below is a macro average over those 45 labeled scopes. It is not patient-level judgment accuracy.

| Method | Exact canonical ID Recall@5 | Original-text coverage Recall@5 | Coverage Recall@10 | Fully covered scopes at Top 5 |
| --- | ---: | ---: | ---: | ---: |
| Vector | 48.89% | 85.19% | 94.81% | 37/45 |
| BM25 | 59.26% | 82.59% | 97.04% | 36/45 |
| Hybrid RRF | 58.52% | 91.85% | 98.89% | 40/45 |
| Local graph-assisted | 59.26% | 78.52% | 96.67% | 34/45 |

Exact recall requires the canonical source ID itself. Coverage recall also credits an original expanded unit that contains the complete required canonical text under the verified coverage mapping. The corrected diabetes row context matters: a commercial-column crop missing the condition title no longer counts as the complete revised canonical source. A fully covered scope requires every reference source in that scope; 91.85% coverage recall and 40/45 fully covered scopes are different statistics.

Hybrid RRF has the highest Top-5 coverage recall in this four-method execution. BM25 and the local graph arm have slightly higher direct canonical-ID recall at Top 5. These metrics do not establish a universally best RAG system. Additional candidates are not automatically irrelevant, the reference lists are engineering references rather than exhaustive clinician relevance judgments, and these previously observed cases include structured field literals. Generalization to unseen natural clinical notes remains untested.

## Reports and continuation

Open `outputs/experiments/shared_retrieval_v1/index.html` to filter by case and method and inspect Top-5 original passages. `results.jsonl` includes Top-10 rankings, `retrieval_metrics.json` records reference-source scoring, and `embedding_calls.jsonl` preserves actual requests/responses and observed costs. `execution_audit.json` binds completed artifacts by hash. Ranking timings exclude shared embedding time; observed workstation costs are not an isolated latency benchmark.

`configs/experiments/shared_retrieval_v1.yaml` records the execution configuration. The exact executed standalone source is preserved as `runner_source.py` and in the frozen manifest. Later source formatting changes invalidate a strict resume identity; use a separately identified output for a new run and retain the historical source if exact reconstruction is required.

The next gate is to bind the external graph indexes to corpus/model/settings/storage identities, build ten new module workspaces, validate their complete original-source mappings and query inventories, and join their results with this frozen ranking matrix. Then allocate a common Top-5 evidence payload and run the same judgment/control contract across methods. This stage has not measured the effect of these four retrieval methods on final fitness judgments and has not completed the six-method comparison. Production routing and rules remain unchanged.
