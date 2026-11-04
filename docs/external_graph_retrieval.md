# External graph retrieval on frozen shared queries

This experiment connects LightRAG `mix` and Microsoft GraphRAG Local Search to the same reviewed 94-unit corpus and 77 case/module queries as the completed four-method retrieval execution. It does not change production extraction, semantic review, rules, uploads or assessment reports. Graph-generated entity descriptions and relations guide retrieval; only mapped original guideline passages may enter a judgment request.

## Runtime and identity

Both frameworks run in separate Python 3.12 environments: `lightrag-hku==1.5.7` and `graphrag==3.2.0`. Their installed dependency versions are checked against the existing lock files. Index construction uses the pinned local `qwen3.5:4b-q4_K_M`; embedding uses the pinned 768-dimensional `nomic-embed-text:latest`. Ollama 0.40.6 and both weight digests are checked before execution and model requests. The five module workspaces per framework enforce disease and commercial/shared scope.

The local tokenizer vocabularies are downloaded from the URLs specified by the installed tiktoken package. Both official SHA-256 values are checked before use. No third-party repository source directory is copied into the project.

Each index binds the full corpus fingerprint, ordered original-source/text identities, model settings, runtime, dependencies, worker source, mapping file and persisted index files. An old `index_complete.json` alone cannot authorize reuse. Query/LLM response caches and logs are explicitly separate from frozen index content; their growth cannot silently authorize changes to graph or original-document stores. Stored original documents and every returned text-unit mapping are checked. Unknown IDs, missing original mappings and cross-module sources become explicit failures, including invalid entries below the Top-k cutoff.

`graph_contract.py` is a standard-library contract module, importable from both isolated environments. `graph_worker.py` invokes the actual framework APIs. `tools/run_external_graph_retrieval.py` verifies inputs, serializes framework/module execution and records every forwarded local model request/response through a loopback audit proxy. The proxy is transport infrastructure; it does not rewrite prompts or answers. Query inventories use exact query identities. Partial responses remain resumable only with identical frozen inputs, code and environments. Failed conditions are retained and never replaced by hybrid rankings.

## Commands

```powershell
.venv/Scripts/python.exe -X utf8 -m tools.run_external_graph_retrieval --config configs/experiments/external_graph_retrieval_v3.yaml --modules hypertension --methods lightrag
.venv/Scripts/python.exe -X utf8 -m tools.run_external_graph_retrieval --config configs/experiments/external_graph_retrieval_v3.yaml --resume
```

The full external inventory is 154 records: 77 queries for each framework. `responses/`, `results.jsonl`, `model_calls.jsonl`, `logs/`, module source mappings and index manifests retain the execution evidence. The driver summary is refreshed after each module; an active module's partial response is more recent than that summary.

The first diagnostic attempt, `external_graph_retrieval_v1`, retains 14 LightRAG tokenizer-initialization failures and 14 successful GraphRAG hypertension queries. It is not pooled into the main v2 result matrix. The v2 run uses a separately identified configuration with explicit verified tokenizer files. Its exact executed worker, contract and runner sources are copied into its own output directory.

The v2 construction profile uses an 8,192-token context and a 2,048-token output ceiling. A successful native framework call can still contain a length-stopped, partial entity extraction. `graph_completion_quality.json` checks raw completion reasons separately from HTTP success and original-source mapping. It records every observed truncation and its affected module; such a configuration is not evidence of a complete knowledge graph. `tools/check_graph_output_recovery.py` can replay exactly those requests with a fixed 4,096-token output allowance while preserving all other request fields and refusing context overflow. This diagnostic does not rebuild or replace any index or ranking. A new graph index revision and evidence freeze remain necessary before the final judgment experiment.

The completed v2 run contains 154/154 external ranking records, ten module indexes, 905 actual framework model/embedding calls, no empty ranking and two length-stopped construction calls. They affect LightRAG vision and GraphRAG diabetes. The larger-output diagnostic completed both original requests normally with the 4,096-token ceiling. That confirms output completion for those two requests, not semantic completeness of a rebuilt graph. The new v3 configuration sets that larger budget and strict completion validation; its indexes and rankings have not yet been rebuilt. The proxy retains the original native response and rejects incomplete output before it can be ingested. Do not resume v2 using edited worker code; preserve its executed source snapshots and use the separately identified v3 output.

After all six ranking inventories are fixed:

```powershell
.venv/Scripts/python.exe -X utf8 -m tools.report_six_method_retrieval --external outputs/experiments/external_graph_retrieval_v3 --output outputs/experiments/six_method_retrieval_v2
```

This report imports the 308 previous baseline rankings by their audited hashes; it does not count them as new retrieval or embedding calls. It verifies complete case/module/method keys and external index manifests before opening the reference labels. The English HTML, per-scope JSON, summary CSV and raw model logs distinguish exact source-ID recall from verified full-original-text coverage. The 23 engineering fixtures and 10 complex validation fixtures are reported separately. Source labels exist for only 45 of 77 module scopes; no recall values are fabricated for the others. Additional candidates are not automatically irrelevant because the engineering reference lists are not exhaustive relevance judgments.

The first completed six-method report is `outputs/experiments/six_method_retrieval_v1/index.html`, with 462 ranking records. Observed Top-5 original-text coverage recall is vector 85.19%, BM25 82.59%, hybrid RRF 91.85%, local graph-assisted 78.52%, LightRAG mix 85.19%, and Microsoft GraphRAG Local Search 67.41%. These are results for the frozen budgeted configuration and source-reference labels, not clinical classification accuracy or a universal framework ranking. The graph length-stop warnings remain visible in that report.

In this scoped corpus, LightRAG's returned Top-5 originals match the pure-vector sequence in all 77 queries, although the actual native `mix` pipeline ran and constructed entity/relationship graphs. Native query metadata and model logs confirm graph retrieval; the result does not establish a graph contribution to the supplied Top-5 text. The installed implementation merges vector/entity/relation chunks and can select their overlapping originals in the same order. Chunk selection and reranking sensitivity remain separate follow-up questions. Do not rename this native result or invent a retrieval gain.

## Judgment preparation and limits

`tools/prepare_retrieval_judgments.py` prepares the next isolated experiment without model calls. It uses frozen patient facts, one common single-stage source-ID judgment prompt, the six retrieval methods and explicit no-evidence/reference-evidence controls. The original source IDs in the reference control are resolved against the same revised corpus. Reference outcomes remain in a separate scoring file and never enter a model request.

The preparation includes an English input-review page. Structurally valid payloads and readiness for the final judgment experiment are separate fields. Any recorded graph construction truncation keeps `ready_for_final_judgment_run` false; a successful larger-output diagnostic alone does not clear the old index's flag.

Evidence is allocated by documented modules, preserving within-module rank order. Only Top-5 originals are eligible; a common UTF-8 byte budget excludes whole passages and records each exclusion. It never cuts away a footnote or backfills from an expected source. Patient identities are checked after allocation. Blocked retrieval or empty non-control evidence is retained as blocked, rather than silently changing into the no-evidence control. Prepared request bodies and all repeated condition keys are fingerprinted.

Retrieval completion does not establish improved fitness judgments. The next gate is the common paired model experiment, with Llama 3 8B and Qwen 3.5 4B, three independent calls per condition, separate cohort analysis, invalid citation/failure accounting and source-support review. Top-10 rankings currently provide retrieval sensitivity analysis; they are not silently supplied to the Top-5 judge. Clinical review and unseen natural-note validation remain pending. The historical 69 unexecuted fact-sensitivity conditions also remain distinct from this new experiment.
