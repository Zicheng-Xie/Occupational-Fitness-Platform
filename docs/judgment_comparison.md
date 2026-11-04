# Retrieval impact on fitness judgments

This isolated experiment measures how changing original guideline evidence changes a local model's provisional assessment. It does not change production extraction, routing, rules, uploads or reports. Clinical labels and explanation support remain pending clinician review.

## Run and resume

From the project root, with Ollama running:

```powershell
.venv/Scripts/python.exe -m occupational_fitness_rag.commands judgment-comparison --config configs/experiments/judgment_comparison.yaml --resume
```

Use `--stage corpus`, `--stage freeze`, or `--stage retrieval` for preparation alone. `--limit 5 --output outputs/experiments/comparison_pilot` selects a balanced five-condition pilot. Use a new output directory after changing core implementation, configuration, labels, corpus or model digests. Resume refuses incompatible experiment identities; recorded failures are preserved, not silently retried or replaced. Keep the machine awake during local inference.

## Isolated dependencies

The main project environment is unchanged. Workers require Python 3.12 environments at `.runtime/lightrag` and `.runtime/graphrag`. Exact installed versions are recorded in `configs/experiments/lightrag.lock.txt` and `graphrag.lock.txt`. The selected framework releases are LightRAG 1.5.7 and Microsoft GraphRAG 3.2.0. Install lock files with `uv pip install --python <worker-python> -r <lock-file>`. Runtime directories, model caches and generated indexes are excluded from Git. No third-party source checkout is included.

Primary judge: `llama3:8b`; replication judge and graph builder: `qwen3.5:4b-q4_K_M`. Embeddings: `nomic-embed-text`, 768 dimensions. Local model calls use temperature 0 and seed 0. Judge context is 8192 tokens, with a 1536-token output allowance; oversized inputs fail explicitly. Three calls per condition assess repeatability, not three independent patients.

## Frozen inputs and corpus

`comparison_corpus.py` retains all 28 canonical source IDs and adds original narrative subsections and commercial table columns. This corpus version contains 96 units across five conditions. Units retain PDF and printed pages, section, original region coordinates, source text and fingerprints. The builder checks region-text equality and printed-page correspondence. Recorded exclusions cover figures, private-only material and unresolved cross-references, but subsequent visual review found two hearing-flowchart column fragments that escaped exclusion. The historical 96-unit corpus and scores remain frozen; the [reviewed quality revision](passage_comparison.md#reviewed-layout-quarantine) quarantines those two units in a separate 94-unit corpus. This version is not a complete transcription or clinical semantic review. Clinician approval remains pending.

`judgment_comparison.py` freezes extraction, source validation, semantic review and facts once per case. All methods use the same frozen facts, original note, disease scope, original corpus and judge instructions. Reference labels, rule outcomes and expected source IDs are absent from the judge prompt and ordinary retrieval queries. Existing reference IDs are used only for scoring and the explicitly named reference-evidence control.

The two cohorts are reported separately: 23 engineering reference cases and 10 complex validation cases. Sealed, unreviewed holdout cases are excluded. `label_audit.json` records discrepancies between existing fixture labels and current frozen rule outputs; neither model answers nor current rules rewrite reference labels.

`comparison_upstream_audit.py` diagnoses these discrepancies without modifying frozen inputs. For the v3 cohort, deterministic extraction and rules agree with all 33 engineering references; eight cases differ after local-model intake/review. Some explicitly documented fields were quarantined by review. These differences must not be called stale labels or retrieval failures. `upstream_audit.json` records changed fields, original quotations and frozen values. The comparison still shares the same frozen facts across methods; its sensitivity subset separates these upstream effects.

Repeated identical text within a disease is indexed once, retaining alternate source regions. LightRAG uses a distinct in-process workspace namespace per disease and verifies that every processed original belongs to that scope. The corrected retrieval artifacts were built in `judgment_comparison_v3` and reused by the current v5 judgment experiment. Earlier development attempts remain separately recorded. Exact-prompt response caches may be reused, but graphs and document-status stores were rebuilt under the corrected namespaces. Cached incremental construction timings are marked explicitly and must not be compared as cold-start costs.

## Retrieval arms

| Arm | Implementation |
|---|---|
| vector | Cosine similarity over actual local Ollama embeddings |
| bm25 | Lexical BM25 baseline |
| hybrid | Rank fusion of vector and BM25 results |
| graph_local | Existing curated source, rule and section relationships |
| lightrag | LightRAG `mix`, actual local entity/relationship graph and vector retrieval |
| graphrag | Microsoft GraphRAG Local context builder, actual entity/relationship graph |
| no_evidence | The same judge receives no guideline evidence |
| reference_evidence | Engineering-selected reference passages, a diagnostic control |

Graph frameworks index independent disease scopes. The Microsoft variant omits community-report generation and sets community context to zero; this is source-only Local retrieval, not Global Search or a comparison of community summaries. LightRAG uses JSON entity extraction with a fixed local model. Both workers map original chunk document IDs to the frozen corpus and reject unmapped sources. Graph descriptions never become judge evidence. Framework errors remain failures; there is no fallback to the native retriever.

Top 5 original passages enter the judge subject to a shared byte budget. Whole passages are skipped rather than silently truncated. Top 10 is a retrieval sensitivity analysis; it is not a second Top-10 judgment experiment. Actual supplied passages and byte counts are recorded. Multi-module candidates are interleaved by within-module rank.

## Outputs and interpretation

Open `outputs/experiments/judgment_comparison_v5/index.html` for the English audit report. It updates every 12 judgments and at completion. Refresh the browser to see new records. An empty or partial table while graph indexes are building is not a completed experiment.

The v3 judgment attempt was stopped after the model cited unprovided fact fields. Its failed records and a raw diagnostic response remain preserved. The v4 interface introduced identifier enums but lacked list length bounds, allowing repeated identifiers until the output budget was exhausted on a sparse-fact case. The v5 experimental interface constrains identifiers to supplied evidence and verified facts and bounds list lengths; it does not constrain the predicted assessment class. Raw responses, request fingerprints and token counts are preserved even when answer validation fails. Identifier validity under this schema is a format guarantee, not evidence of explanation support. A five-disease, two-model pilot plus a sparse-fact boundary case precedes the full matrix. `reuse_manifest.json` records unchanged frozen inputs, original retrieval rankings and graph artifacts reused from v3; v5 construction cost is not a second cold-start measurement. Pilot judgments are separate from the full repeated-call matrix.

`interactive_report.html` is the portable interactive analytical report. Its report refresher rebuilds from actual recorded rows and retains source inspection, model/cohort/case/repeat/error filters, paired changes and confusion matrices. `comparison_snapshot.py` updates the existing report identity; `comparison_report_refresh.py` accepts an existing app directory, bundled Node and Data builder paths, plus optional `--watch` and `--delivery`. It does not run model inference or alter experiment records.

`results.jsonl` stores every call, actual inputs, output, source citations, fact references, timing and failures. `retrieval.json` stores ranked sources and retrieval failures. `summary.json` and `summary.csv` contain agreement, Macro-F1, Recall@5/10, coverage, abstentions, cost and paired changes relative to hybrid. The confusion matrix and case-cluster bootstrap intervals are in JSON. `review_queue.json` retains judgments for independent support review. Corpus, label audit, model inventory and manifest preserve experiment identities.

Recall can credit an expanded original paragraph that contains a complete canonical reference passage; strict source-ID recall is also recorded. These metrics measure reference evidence coverage, not relevance precision or clinical correctness. Automatic numeric support checks are heuristics and do not prove entailment. The report uses **Engineering reference agreement**, never clinical accuracy.

A method recommendation requires completed paired cases: inspect which original evidence changed the assessment, whether it agrees with the fixed reference, and whether the explanation is actually supported. Report wrong-to-correct and correct-to-wrong changes together, alongside failures and costs. Stars on [LightRAG](https://github.com/HKUDS/LightRAG) and [Microsoft GraphRAG](https://github.com/microsoft/graphrag) are project-selection context, not evidence of superiority.

`comparison_analysis.py` exports disease-specific metrics, fixed-label sensitivity, reference class distribution, construction/retrieval/judgment costs and an unfilled evidence-review worksheet. Relevance, condition applicability and explanation entailment require review; blank review fields are not counted as successful checks. `comparison_cost_audit.py` extracts framework-reported request counters with source-log fingerprints and rejects ambiguous duplicate snapshots. Microsoft GraphRAG reports 233 graph-model requests and 121 embedding requests for the completed v3 worker. Exact LightRAG network attempt counts remain unavailable; cache entries are not counted as calls. Local-context budget warnings are recorded separately from retrieval failures.

Disease metrics use the case's reference scope. Multi-disease cases with an overall reference label remain in the `all` scope; they are not presented as independently labelled per-disease assessments.

## Paired error and repeatability audit

`comparison_error_audit.py` compares each recorded method condition with hybrid RRF for the same case, model and repeat. It verifies that patient facts, original note, licence context and disease scope match before crediting a paired change. Duplicate condition keys fail explicitly. `paired_error_audit.csv` and `error_audit.json` preserve both outcomes, reference transitions, ordered source IDs, added and removed sources, upstream review flags and evidence-bundle differences. A changed outcome with identical ordered evidence cannot be attributed to retrieval differences. Changed bundles establish an association, not the causal contribution of one passage.

`error_audit.html` places actual original passages and model explanations side by side for priority pairs. The full pair list remains available in JSON and CSV. The interactive report also shows repeated-call stability: a condition is eligible only when every planned call completed successfully with identical patient inputs and evidence. Failed, incomplete or mismatched conditions do not receive stability credit. Three calls remain repeated observations of one patient case.

The report refresher takes one summary checkpoint for both analytical exports and the interactive snapshot, preventing disagreement caused by new inference rows arriving during export. Failure records remain in the denominator. Filters default to changed correctness and unstable or ineligible conditions; users can expand the complete paired and stability tables.

## Completed matrix and remaining acceptance work

The v5 matrix records all 1,584 conditions: 33 cases, eight evidence conditions, two models and three repeated calls. Of these, 1,548 pass output validation and 36 fail because the model supplies no guideline citation. Failures are retained; completed execution does not mean every call passed. The six retrievers completed all 462 case/module searches without an empty result.

`comparison_completion.py` independently recalculates agreement, Macro-F1, reference-class recall, balanced accuracy and the always-insufficient baseline. It validates condition uniqueness, shared patient inputs, exact original evidence mappings, prompt fingerprints, citation identifiers, evidence budgets and fixed labels. It also estimates paired agreement differences with 2,000 case-cluster bootstrap samples. Run it without model calls:

```powershell
.venv/Scripts/python.exe -m occupational_fitness_rag.evaluation.comparison_completion outputs/experiments/judgment_comparison_v5
```

`completion_audit.json` passes the engineering integrity checks and reconciles all summary metrics. This pass does not approve explanations or reference labels clinically. The corrected refresher now finishes only after building the completed checkpoint; a summary that advances during rendering cannot falsely mark an older export as current.

In the 23-case engineering cohort, hybrid RRF has the highest reference-evidence Recall@5 (93.8%), while Llama judgment agreement is 33.3%, compared with 43.5% for the existing curated graph method. Qwen agrees on 43.5% for hybrid, curated graph and Microsoft GraphRAG. These are repeated-call engineering measurements; all observed paired agreement intervals include zero.

The ten-case complex cohort contains six insufficient-information references and four restrictive references. Every retrieval arm and both controls miss all four restrictive cases with both models. An always-insufficient classifier reaches 60% agreement here. Report balanced accuracy and class-specific results alongside overall agreement; the current model judgment is not ready to replace production rules.

The repeated-call audit contains 528 case/model/method conditions: 508 stable, four unstable, and 16 ineligible because of failed calls. Independent source relevance, licence applicability, explanation support and clinician review remain pending. The eight upstream review discrepancies also require separate inspection. Figure interpretation and unresolved cross-references remain incomplete; two subsequently identified flowchart fragments require the separately versioned quarantine described above. Keep the current production retrieval and deterministic rule workflow until these acceptance items are resolved.
