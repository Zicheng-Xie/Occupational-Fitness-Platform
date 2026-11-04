# Occupational Fitness Platform

> **Branch identity — `codex/sync-local-integrated` (audit: 2026-11-05).** Integration replay on the research base; audited application source, tests, configs and every other root entry except README/docs match main exactly.
>
> Audited implementation: [`8b52ef91`](https://github.com/Zicheng-Xie/Occupational-Fitness-Platform/tree/8b52ef910e3fe05982178969c565359f077b55b7). This README keeps that branch's own setup and implementation details. For the current integrated application, use [main](https://github.com/Zicheng-Xie/Occupational-Fitness-Platform/tree/main); see the [branch relationship diagram and code matrix](https://github.com/Zicheng-Xie/Occupational-Fitness-Platform/blob/main/docs/branches.md). History counts in that guide are pinned before these documentation-only updates.
>
> At the pinned audit, src/, tests/, configs/ and all other root entries except README/docs were byte-identical by Git tree/blob SHA to main. A unique commit does not imply missing functionality on main.

The isolated [case-evidence allocation comparison](docs/case_evidence_allocation.md)
tests whether seventh- and ninth-route retrieval gains survive the five-original
patient budget and improve actual local-model judgments. It preserves the old
allocator and fixes patient facts, prompts and model versions across five arms.

The [completed 990-condition findings](docs/case_allocation_judgment_findings.md)
separate evidence coverage, valid classification changes and citation recovery.
Open the [completion report](outputs/experiments/case_allocation_completion_v1/index.html)
or [paired viewer](outputs/experiments/case_allocation_judgment_comparison_v1/index.html).
The [prospective review packet](docs/prospective_case_review.md) prepares twelve
new independently annotated cases; prospective execution remains pending.

Start the local browser workspace with `scripts/start_workspace.ps1`, then open `http://127.0.0.1:8000` to upload a clinical record or paste notes. Use `-Offline` for an assessment without model services. See [Team integration](docs/team_integration.md) and [Retrieval experiments](docs/retrieval_experiments.md) for indicator exchange and repeatable comparisons.

See the [aggregation encoding diagnostic](docs/ledger_encoding.md) for the completed main replay reports, the isolated context-budget comparison, and shared six-method query preparation. These experimental artifacts do not change production rule outcomes.

The [source-bound reasoning diagnostic](docs/source_bound_reasoning.md) tests precise numeric support and final source binding against the unchanged baseline, and documents the separately versioned original-table context correction.

The [shared-query retrieval execution](docs/shared_retrieval.md) records 308 completed rankings on the revised corpus for vector, BM25, RRF and local graph-assisted retrieval. External graph methods and downstream judgment comparisons remain separate pending stages.

A traceable assessment platform for occupational health teams and commercial-driver reviews. Software **0.7.1**, rule-result schema **1.3.0**, RAG-input schema **1.2.0** with legacy 1.0/1.1 compatibility, indicator schema **1.0.0**, guideline baseline **AP-G56-22**.

See [Evidence-linked reasoning and RAG comparison](docs/reasoning_and_rag_comparison.md) for the patient-fact-to-guideline audit, local-model reasoning test, five-method retrieval experiment, and prospective clinician-review pack.

See [Complex nurse-note validation](docs/complex_notes.md) for 12 long-form synthetic cases, two negative controls, reproducible live/offline tests and an inspectable retrieval report.

See [Complex-note RAG diagnostics](docs/rag_diagnostics.md) for the mixed-note investigation, source-bound symptom retrieval and ten additional positive/uncertain regression cases. Open [the diagnostic comparison](outputs/evaluation/rag_diagnostics/index.html) for saved live results.

The platform uses local **Qwen 3 14B** to propose structured facts, validates their source quotations, types and meaning, performs a second-pass semantic review, runs deterministic rules, and links each assessment to guideline evidence through **Chroma, nomic-embed-text and BM25/RRF**.

**[Open assessment records](outputs/index.html)** · [Runbook](docs/runbook.md) · [Data contracts](docs/contracts.md) · [Verification](docs/verification.md)

See [Collaboration integration](docs/collaboration_integration.md) for the merged Red Flag boundary, retained local workflow, and compatibility details.

## Getting started

Run `powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1 -Chroma`, or install `python -m pip install -e ".[dev,api,chroma]"` in the project environment. Ollama must have `qwen3:14b` and `nomic-embed-text:latest` installed.

```powershell
.\.venv\Scripts\fitness-rag.exe assess --input data/cases/nurse_notes/SYN-M2-009.txt
.\.venv\Scripts\fitness-rag.exe demo
.\.venv\Scripts\python.exe scripts/build_delivery.py
```

For the full browser workspace, start the local API and open `http://127.0.0.1:8000`.
The compact TXT interface remains available at `http://127.0.0.1:8000/simple` and presents
a concise conclusion with exact case and guideline quotations.

The default configuration enables Qwen3 extraction, semantic review, evidence-mode selection and separate model commentary. See [Extraction semantic review](docs/semantic_review.md) for the review policy and its limitations. `workflow.offline.yaml` provides deterministic operation without model services; `workflow.chroma.yaml` isolates retrieval validation. Model traffic connects directly to loopback endpoints.

## Assessment workflow

1. Read UTF-8 text, Markdown or a PDF with a text layer.
2. Extract and validate facts; retain source locations, conflicts and unknown values.
3. Review extracted meaning against the original note; withhold flagged values for confirmation and map facts to the five modules.
4. Execute deterministic rules and the Red Flag contract adapter using the established outcome-based routing. No additional model route judgment runs by default.
5. Bind required source IDs. Fast cases use exact binding; other cases select exact binding or semantic RAG after deterministic routing. Semantic RAG uses request-scoped facts and metadata filters.
6. Produce an English review report with case quotations, guideline pages, sections and coordinates.

Reports remain **DRAFT / clinical review pending**. Rules retain `pending_clinical_review`; the system does not issue driving licences or employment decisions.

See [Red Flag routing examples](docs/red_flag_cases/README.md) for the missing-evidence,
local fast-path and cross-chapter RAG-review flows.

## Project structure

| Directory | Responsibility |
|---|---|
| `src/occupational_fitness_rag/` | Intake, models, rules, retrieval, reporting and API |
| `configs/` | Workflow settings, executable rules and source anchors |
| `schemas/` | JSON Schema and field dictionary |
| `data/knowledge/` | Original guideline, verified knowledge units and rebuildable indexes |
| `data/cases/` | Supplied synthetic inputs, extension cases and regression expectations |
| `outputs/` | Current assessment records and verification results |
| `scripts/`, `tests/` | Setup, generation, checks and regression tests |

## Included demonstration reports

The repository includes 30 fixed synthetic report bundles in `outputs/demo/`. After cloning or downloading the complete repository, open `outputs/index.html` in a browser; saved reports and evidence links work without Ollama. GitHub itself shows HTML source, so download the repository to use the interface. `outputs/demo/manifest.json` pins this collection; ordinary future runs in `outputs/runs/` remain ignored. See [the demonstration collection](outputs/demo/README.md).

## Deliverables and language

The isolated [retrieval-to-judgment comparison](docs/judgment_comparison.md) freezes patient facts and compares six retrieval methods plus two evidence controls. Run `fitness-rag judgment-comparison --resume` and inspect the experiment's English HTML report, JSONL and CSV audits. Experimental model assessments never replace production rule outcomes.

The completed [evidence-contract diagnostic pilot](docs/judgment_diagnostics.md) replayed those frozen inputs with documented-module evidence allocation, clause-linked judgments and bounded, fully recorded validation recovery. Its v2 outputs and original source snapshot are frozen; a fresh run requires a separate output configuration. The [open-source design review](docs/open_source_design_review.md) records inspected upstream files and adaptation limits.

The subsequent [module-query and immutable-passage comparison](docs/passage_comparison.md) tests disease-scoped verified-fact queries against mixed-note queries, and passage selection against copied quotations. Its completed first pilot is frozen. The reviewed 94-unit corpus and fresh retrieval inputs are preserved separately; their historical source identity must not be rebound after adding new code.

The [applicability-first comparison](docs/applicability_comparison.md) imports those exact reviewed-corpus inputs into a new experiment. Run `fitness-rag applicability-comparison --resume` to compare the contemporary passage-selection control with a two-stage applicability ledger and independent aggregation. First-pass validity, final agreement, paired regressions and all stage costs are reported separately. Experimental outcomes and consistency flags remain separate from production decisions.

Each run includes the original input, structured facts, category facts, rule results, the scoped RAG input, evidence pack, model extraction and semantic-review audits, clinician checklist, HTML/Markdown reports and a fingerprinted run manifest.

Product documentation, labels, accessibility text, generated summaries and model commentary are English. Original evidence is never silently translated or rewritten. The supplied case inputs and guideline are English; historical non-English screenshots and superseded outputs are preserved outside the active project.

All 30 demonstration records are explicitly synthetic. OCR, institutional access controls, formal electronic sign-off and production integration require further implementation; see [deployment boundaries](docs/deployment.md).

The [external graph retrieval execution](docs/external_graph_retrieval.md) adds isolated, pinned LightRAG mix and Microsoft GraphRAG Local Search workers, immutable original-source mappings and a common six-method report. This experimental path preserves the production workflow. Its retrieval results and subsequent judgment comparison have separate completion and clinical-review states.

The additional [Planned Hybrid RRF experiment](docs/planned_hybrid_retrieval.md) adapts selected retrieval and orchestration designs inspected in the owner's WeKnora and DeerFlow forks. It adds bounded, source-literal facet planning, independent channel fusion, keyword follow-up and passage diversity. The original six methods remain independently saved. The common frozen-request judgment runner can append this seventh arm without changing patient facts, judge prompts or production decisions.

The [anchor-aware no-MMR revision](docs/anchored_hybrid_retrieval.md) preserves all earlier experiments and compares predefined query-fusion and original-source coverage policies. Its separate English report records Top5 and Top10 coverage, exact source recall, paired changes and the unchanged judgment evidence budget. Prepared revision requests and serial model execution remain separate from production decisions.

The completed [qualified ten-route retrieval comparison](outputs/experiments/ten_method_retrieval_v3/index.html)
preserves the original six methods and all seventh-method revisions. The preferred
guarded seventh arm reaches 92.59% Top5 and 100.00% Top10 reference-original
coverage on 45 labeled development scopes. Later semantic-score blends reduce
Top5 coverage and remain negative ablations. Three additional, genuinely executed
routes use FlagEmbedding reranking, native Neo4j hybrid graph search, and native
PageIndex indexing with a first-party local navigator. Their boundaries, versions
and independent Docling parsing audit are documented in
[retrieval extension routes](docs/retrieval_extension_routes.md).

A later [source-scope audit](outputs/experiments/commercial_scope_audit_v1/index.html)
identified six private, mixed-scope or incomplete vision passages in that frozen
94-unit experiment corpus. Metadata does not establish commercial-only textual
applicability. A separate [88-unit reviewed subset](outputs/experiments/scope_reviewed_corpus_v2/index.html)
quarantines those sources while retaining all 28 frozen canonical IDs. Historical
94-unit scores remain unchanged. The [reviewed-corpus optimization](docs/scope88_retrieval_optimization.md)
now recomputes all ten routes on the same 88 originals and 77 queries. Retained
sources still need independent layout, applicability and clinical review.

The new criterion-prefix seventh route and native-frontier ninth route each
reach **95.56% Top5 / 100.00% Top10** reference-original coverage across 45 labeled
development scopes. Their actual five-original case packets cover 82.22% and
84.44%, respectively; query ranking and model-input coverage are separate.
The tenth route's best observed, explicitly development-selected RRF/tree
variant reaches **87.04% / 97.78%**, compared with 60.74% / 60.74% for its reviewed
pure-tree control. These are retrieval measurements, not new judgment results.
Open the [qualified current comparison](outputs/experiments/scope88_optimization_comparison_v2/index.html)
for all ten routes and actual input packets. The Microsoft vision graph index
has an unrecovered extraction failure and its scores are explicitly provisional.

The original 1,782 judgment conditions and the retrieval-v2 revision's 198
conditions are complete. The [paired judgment audit](outputs/experiments/anchored_revision_judgment_audit_v1/index.html)
shows that the retrieval-v2 coverage improvement did not improve overall
engineering-reference agreement. The guarded seventh arm and three native routes
still need their own judgment comparisons; retrieval coverage is not clinical
accuracy. Production rules and workflow remain unchanged.
