# Six-method retrieval replay readiness

Inspection date: 2026-10-15. This document records implementation readiness. No new six-method retrieval or judgment run was executed for this audit. Production rules, uploads, and report interfaces are unchanged.

## Decision

The historical six-retriever experiment cannot be resumed or relabelled as a contemporary 94-unit, source-literal-facts experiment. Its corpus, graph model weights, queries, judgment prompt, and output contract differ. A separately identified replay adapter and fresh graph indexes are required.

The current 33-case applicability replay and the source-literal sensitivity replay are useful protocol/fact diagnostics. Their frozen retrieval input contains hybrid module-query evidence and a reference-evidence control; these are not completed six-method comparisons.

## Frozen inputs for the next retrieval comparison

| Input | Required identity |
| --- | --- |
| Reviewed corpus | `outputs/experiments/corpus_quality_v1/corpus.json` |
| Corpus semantic SHA-256 | `f4c53ea86f9c6e87a7edfb953a9c5c3305d8a6255116072a30ddf43c001c40cc` |
| Corpus file SHA-256 | `70d853acfc7344cd2dc4b57d9af76b308acf800de0b40cde367c2e75663ff259` |
| Source-literal fact snapshot | `outputs/experiments/source_literal_facts_v1/source_literal_facts.json` |
| Fact snapshot identity | `b156f6ab7f55d03fda9d0c0fb6749f3e0694636cd80392c0bf4567831179e568` |
| Fact snapshot file SHA-256 | `52880f1e4c6da5ff343fb27bc8c90cf363e29ee83d7d5e55de8d62e3696f49ba` |
| Original frozen retrieval identity | `fd91e2fd77b5a739e24d835c94416b00fbdf81006b327e4f52650f6b2bc1f2f4` |
| Held-evidence fact sensitivity input | `outputs/experiments/source_literal_retrieval_v1/derivation.json` explicitly records `retrieval_executed: false` |

The fact snapshot covers all 33 cases. It restores 41 exact typed source literals across 13 cases, leaves three nonliteral changes withheld, and preserves the original semantic review. This is engineering source verification; clinical review remains pending.

Freeze the fact version **before generating any new queries**. All six retrievers must consume the same module query strings built from that version. Preserve query bytes, query hashes, eligible fact fields, case/module scope, and source-literal snapshot identity. Do not use reference source IDs, reference outcomes, triggered rules, or a model judgment to construct the main retrieval query.

The held-evidence sensitivity artifact deliberately retains earlier queries and passages to isolate the effect of patient facts. It must not be described as fresh retrieval from restored facts. A new retrieval artifact must have its own identity and derivation ledger.

## Corpus and index inventory

| Module | Historical units | Reviewed units | Graph workspaces to rebuild |
| --- | ---: | ---: | --- |
| Blackout | 16 | 16 | LightRAG and Microsoft GraphRAG |
| Diabetes | 28 | 28 | LightRAG and Microsoft GraphRAG |
| Hearing | 15 | 13 | LightRAG and Microsoft GraphRAG |
| Hypertension | 4 | 4 | LightRAG and Microsoft GraphRAG |
| Vision | 33 | 33 | LightRAG and Microsoft GraphRAG |
| Total | 96 | 94 | Ten fresh module workspaces |

The inventory found 31 `index_complete.json` files under historical experiment outputs. All are inside the old `e7a9fcc7293a50cb` corpus directory; none binds the reviewed `f4c53ea86f9c6e87` corpus directory. The v5 set contains ten completed module workspaces:

`outputs/experiments/judgment_comparison_v5/indexes/e7a9fcc7293a50cb/{lightrag,graphrag}/{blackout,diabetes,hearing,hypertension,vision}`

Only hearing membership changed in the corpus revision. Nevertheless, all ten graph workspaces need fresh contemporary construction because v5 records graph Qwen weights `2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd`, whereas the current configured Qwen weights are `91fa08b9fedfbbda924cd71febc5f6adbf31503cf7811df817dcf93bd56b08ff`. The old completion sentinels do not independently bind the model digest or complete index configuration. Retain the old indexes as historical evidence.

BM25 and the curated graph ranker have no persistent learned graph workspace. Recreate their document collections from the frozen 94 units. Dense vectors must be keyed by corpus identity, ordered source/text identities, embedding model **digest**, dimensions, and vector-content hash. The 94-vector cache in `passage_comparison_full_clean/embeddings.json` is available for explicitly verified import; it cannot be copied into the older retriever's different cache schema or credited as a fresh embedding build.

Installed isolated runtimes were inspected without model calls:

- `.runtime/lightrag/Scripts/python.exe`: Python 3.12.14, `lightrag-hku==1.5.7`.
- `.runtime/graphrag/Scripts/python.exe`: Python 3.12.14, `graphrag==3.2.0`.
- Dependency snapshots: `configs/experiments/lightrag.lock.txt` and `configs/experiments/graphrag.lock.txt`.

Installation availability is not a successful contemporary index build or model-connection test.

## What the existing implementation already provides

| File | Existing behavior | Replay implication |
| --- | --- | --- |
| `evaluation/comparison_corpus.py` | Verifies semantic corpus fingerprint, original PDF fingerprint, exact region text/text hash, unique IDs, allowed licence metadata, alternate-region text, and resolved included cross-reference IDs. | Apply verification to the reviewed corpus before any worker request. Exact text addresses do not establish clinical interpretation. |
| `evaluation/judgment_comparison.py` — `CorpusRetriever` | Real dense embeddings; module-filtered BM25; RRF with `k=60`; curated source/rule/section graph reranking. The BM25 branch has no dense list, so its RRF transformation preserves sparse rank order. | Reuse retrieval algorithms through a strict separate input adapter; do not call the legacy end-to-end runner with unsupported override keys. |
| `retrieval/graph_local.py` | Curated graph edges, query/source/rule term matches, same-section and explicit cross-reference propagation within the filtered module. It does not use the patient's rule outcome. | Label it curated graph-assisted retrieval, not LLM entity GraphRAG or a graph diagnostic oracle. Cross-module graph targets are filtered out. |
| `evaluation/graph_worker.py` — LightRAG | Per-module insertion, fixed local Qwen, 4,096-token chunks without overlap, `mix` query, reranking disabled, requested document coverage checks, original source ID mapping. | Generated entities/relationships help ranking; only a mapped original full unit may enter the judge payload. |
| `evaluation/graph_worker.py` — Microsoft | Entity/relationship extraction, communities, embeddings, Local Search context builder; community reports are not generated or supplied, `community_prop=0.0`. | Name the arm **Microsoft GraphRAG source-only Local Search**. It is not Global Search or community-summary answering. |
| Legacy runner failure path | Preserves raw provider output, rejects incomplete output/context reserve failures; failed external workers create failure records; does not replace a failed method with hybrid results. | Preserve and strengthen this behavior in the contemporary adapter. |

Private-only records are excluded by corpus construction and `verify_corpus` rejects units outside `commercial`/`shared`. Graph workers isolate modules, but do not independently run the complete corpus/PDF verifier when invoked directly. Their caller must pin and verify the input first. Mixed/general narrative still needs clinical applicability review: a permitted metadata value is not proof that every clause applies to a commercial driver.

## Required engineering changes before execution

1. **Separate frozen-input replay adapter.** Accept an explicitly pinned reviewed corpus, fact snapshot, query snapshot, model/runtime identity, and evidence-selection policy. Import the existing original cases without re-running extraction or semantic review. Build an exact planned-key manifest, exclusive writer lock, strict JSONL resume validation, complete source/config snapshots, and a retrieval freeze. The legacy runner currently rebuilds its default corpus and freezes patient facts afresh; adding unrecognised `corpus_override` or `fact_snapshot` YAML keys does not implement this behavior.

2. **Strict graph index identity.** Each new completion manifest must bind the full corpus hash; ordered module source IDs/text hashes; graph and embedding model digests; Python/package/lock identities; worker hash; graph/chunk/query settings; and original-source mapping checksum. Validate the recorded document set and underlying mapping/storage files before reuse. An `index_complete.json` file alone is insufficient. Keep partial indexing and cache reuse separately accounted; historical LightRAG v5 timing was explicitly marked as cache reuse and is not a cold build benchmark.

3. **Reject unresolved mappings.** LightRAG rejects returned `file_path` values outside allowed originals. Microsoft rejects a mapped document ID outside its allowed module, but `by_short.get(str(row["id"]), [])` currently silently skips an unknown text-unit short ID. Change that path to a recorded mapping failure. Verify source ID, module, text fingerprint, section, and page against the reviewed corpus after both workers return. Unknown, duplicate, stale, or private-only mappings must not be silently dropped and counted as success.

4. **Exact retrieval completeness.** The legacy resume path skips a method when *any* record for that method exists; it does not require every planned case/module query. A timed-out partial response could therefore leave missing scopes on a later resume. The contemporary adapter must require each planned `(case_id, module, method, query_sha256)` exactly once, reject duplicates/stale records, and record missing scopes as failures. Every external process failure must retain partial records and explicit failure rows for unfinished scopes.

5. **One evidence budget contract.** Apply the same module round-robin merge, deduplication, Top 5 final originals, 9,000-byte evidence ceiling, 24,000-byte patient/evidence payload ceiling, and 48,000-byte complete request ceiling. Record selected rank, full original text, original length, excluded items, actual request bytes, and provider token counts. Do not shorten an original table entry to fit a budget or backfill using a reference source ID. Record Top 10 as a retrieval sensitivity audit; if Top 10 judgments are also required, plan those as a separate factor.

6. **Choose and freeze the judgment contract.** The original six-method config has a single-stage, 1,536-output-token `ExperimentalJudgment` contract. The contemporary applicability protocol uses a program-bound passage ledger followed by a separate aggregation call, 2,048 output tokens, strict passage/fact provenance, and at most one structural repair per stage. Select one common frozen contract for all compared retrieval methods. Never pool old and new contract outcomes as if only retrieval changed. If both outcome-first and applicability-first are compared, declare the protocol as another experimental axis.

7. **Specify the no-evidence control honestly.** The current passage/applicability builders require at least one original passage, so they cannot accept an empty evidence list. Do not insert a fabricated placeholder passage. A no-evidence control needs a documented compatible abstention contract and separate handling; report its structural difference. Alternatively keep the legacy eight-arm experiment separate and run a seven-arm contemporary passage experiment. This choice must precede inference, not be inferred from whichever calls succeed.

8. **Preflight the complete boundary.** Test original-source mapping, exclusion/private filtering, malformed IDs, wrong-module sources, partial worker output, duplicate/missing keys, negative and family-history statements, contradictory literals, empty evidence, and complete-request/context limits before the five-disease pilot. Do not run graph construction while another judgment model is active.

## Workload and fair interpretation

There are 77 case/module scopes across the 33 existing cases. One frozen module-query policy and six retrieval methods imply **462 planned retrieval scope records**. Graph query APIs may make additional internal model calls; record those separately from judgment calls.

| Declared factors | Planned judgment conditions |
| --- | ---: |
| 33 cases × 8 arms × 2 judges × 3 repeats × one fact version × one judgment protocol | 1,584 |
| Same eight arms, two judgment protocols | 3,168 |
| Same eight arms, original and source-literal fact versions, one protocol | 3,168 |
| Both fact versions and both protocols | 6,336 |
| 33 cases × 7 evidence-backed arms × 2 judges × 3 repeats × one contemporary passage protocol | 1,386 |

Eight arms means six retrievers plus no evidence and reference evidence. A two-stage applicability condition makes two initial judge calls, with up to one structural repair per stage. Therefore 1,584 applicability conditions would imply 3,168 initial calls and up to 6,336 calls under that repair policy, **only after defining a valid no-evidence control**. Conditions, model calls, distinct patients, and indexing calls must have different counters.

These 33 cases are previously observed engineering fixtures, not an unseen holdout. Labels remain provisional. Report **Engineering reference agreement**, fixed-five-class Macro-F1, per-class recall with failures retained, evidence-policy transitions, and independent source-support review. A reference-evidence advantage measures a retrieval headroom control; it does not make the reference arm a deployable retriever. A fact-version effect must not be attributed to a retrieval-method change.

## Commands and their present status

The following checks are supported now and do not start graph or judgment models:

```powershell
& .venv/Scripts/python.exe -c "import importlib.util,pathlib; p=pathlib.Path('tools/build_source_literal_facts.py'); s=importlib.util.spec_from_file_location('facts',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); d=m.load_snapshot('outputs/experiments/source_literal_facts_v1',pathlib.Path.cwd()); print(d['identity'])"
& .runtime/lightrag/Scripts/python.exe -c "import sys,importlib.metadata as m; print(sys.version); print(m.version('lightrag-hku'))"
& .runtime/graphrag/Scripts/python.exe -c "import sys,importlib.metadata as m; print(sys.version); print(m.version('graphrag'))"
```

Existing diagnostic commands, after their manifests and source identities have been frozen, are:

```powershell
& .venv/Scripts/fitness-rag.exe applicability-comparison --config configs/experiments/applicability_comparison_full33_original.yaml --resume
& .venv/Scripts/fitness-rag.exe applicability-comparison --config configs/experiments/applicability_fact_sensitivity.yaml --resume
```

Those commands do not implement fresh six-method retrieval. Do not launch both at once.

`fitness-rag judgment-comparison --config configs/experiments/judgment_comparison.yaml` is a **legacy protocol entry point** whose configured output is the historical v5 directory. Do not execute it against that directory for this replay. The adapter and new contemporary six-method configuration do not yet exist at inspection time; no executable command is claimed for them. Reserve a new output, such as `outputs/experiments/six_method_source_literal_v1`, only when its complete contract is implemented and validated.

The direct external worker syntax already exists:

```powershell
& .runtime/lightrag/Scripts/python.exe src/occupational_fitness_rag/evaluation/graph_worker.py --method lightrag --request NEW_PINNED_REQUEST.json --response NEW_RESPONSE.json
& .runtime/graphrag/Scripts/python.exe src/occupational_fitness_rag/evaluation/graph_worker.py --method graphrag --request NEW_PINNED_REQUEST.json --response NEW_RESPONSE.json
```

The uppercase file names are placeholders, not prepared requests. Do not run these commands until the caller has verified the corpus/fact/query pins and the worker identity/mapping gaps above have been addressed. Fresh graph construction must remain in independent output directories and must not reuse the old completion sentinels.

## Inspection fingerprints

These identify code/configuration inspected for this audit; later edits require a new audit rather than changing historical results.

| File | SHA-256 |
| --- | --- |
| `evaluation/judgment_comparison.py` | `e39362dd31aec0923c4ad33d9cbc02cc56eae6afbb76c0f8819646e26b5d4822` |
| `evaluation/graph_worker.py` | `543610697cd74e998d0f44a12069a514f1dcb00db5a5598b5605126f6130bc21` |
| `configs/experiments/judgment_comparison.yaml` | `1aa99dd36a3a680fccb8b76b7564b6292bf582cad6d0d7934a694eaf51ef4fb8` |
| `configs/experiments/lightrag.lock.txt` | `920d6103307fa03aa23aaf6664b630a66ce0cd4e7fdf26d38ec1577b949b408f` |
| `configs/experiments/graphrag.lock.txt` | `45cc57dbefae8d7d3367c72cbef50a7a07de6b539064095dfd0f8d39c738f823` |

Next gate: implement and test the frozen-input six-method adapter plus strict graph manifest/mapping validation; rebuild the ten graph module workspaces with pinned current weights; run a five-disease pilot; then execute the declared complete comparison and retain all failures and independent review items.
