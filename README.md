# Occupational Fitness Platform

Start the local browser workspace with `scripts/start_workspace.ps1`, then open `http://127.0.0.1:8000` to upload a clinical record or paste notes. Use `-Offline` for an assessment without model services. See [Team integration](docs/team_integration.md) and [Retrieval experiments](docs/retrieval_experiments.md) for indicator exchange and repeatable comparisons.

A traceable assessment platform for occupational health teams and commercial-driver reviews. Software **0.7.1**, rule-result schema **1.3.0**, RAG-input schema **1.2.0** with legacy 1.0/1.1 compatibility, indicator schema **1.0.0**, guideline baseline **AP-G56-22**.

See [Complex nurse-note validation](docs/complex_notes.md) for 12 long-form synthetic cases, two negative controls, reproducible live/offline tests and an inspectable retrieval report.

See [Complex-note RAG diagnostics](docs/rag_diagnostics.md) for the mixed-note investigation, source-bound symptom retrieval and ten additional positive/uncertain regression cases. Open [the diagnostic comparison](outputs/evaluation/rag_diagnostics/index.html) for saved live results.

The platform uses local **Llama 3 8B** to propose structured facts, validates their source quotations, types and meaning, performs a second-pass semantic review, runs deterministic rules, and links each assessment to guideline evidence through **Chroma, nomic-embed-text and BM25/RRF**.

**[Open assessment records](outputs/index.html)** · [Runbook](docs/runbook.md) · [Data contracts](docs/contracts.md) · [Verification](docs/verification.md)

See [Collaboration integration](docs/collaboration_integration.md) for the merged Red Flag boundary, retained local workflow, and compatibility details.

## Getting started

Run `powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1 -Chroma`, or install `python -m pip install -e ".[dev,api,chroma]"` in the project environment. Ollama must have `llama3:8b` and `nomic-embed-text:latest` installed.

```powershell
.\.venv\Scripts\fitness-rag.exe assess --input data/cases/nurse_notes/SYN-M2-009.txt
.\.venv\Scripts\fitness-rag.exe demo
.\.venv\Scripts\python.exe scripts/build_delivery.py
```

For the full browser workspace, start the local API and open `http://127.0.0.1:8000`.
The compact TXT interface remains available at `http://127.0.0.1:8000/simple` and presents
a concise conclusion with exact case and guideline quotations.

The default configuration enables Llama extraction, semantic review and separate model commentary. See [Extraction semantic review](docs/semantic_review.md) for the review policy and its limitations. `workflow.offline.yaml` provides deterministic operation without model services; `workflow.chroma.yaml` isolates retrieval validation. Model traffic connects directly to loopback endpoints.

## Assessment workflow

1. Read UTF-8 text, Markdown or a PDF with a text layer.
2. Extract and validate facts; retain source locations, conflicts and unknown values.
3. Review extracted meaning against the original note; withhold flagged values for confirmation and map facts to the five modules.
4. Execute deterministic rules and the Red Flag contract adapter using the established outcome-based routing. No additional model route judgment runs by default.
5. Bind required source IDs. Non-fast cases rank every request using indicator-scoped hybrid retrieval, filtered by category, condition, commercial standard and version.
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

Each run includes the original input, structured facts, category facts, rule results, the scoped RAG input, evidence pack, model extraction and semantic-review audits, clinician checklist, HTML/Markdown reports and a fingerprinted run manifest.

Product documentation, labels, accessibility text, generated summaries and model commentary are English. Original evidence is never silently translated or rewritten. The supplied case inputs and guideline are English; historical non-English screenshots and superseded outputs are preserved outside the active project.

All 30 demonstration records are explicitly synthetic. OCR, institutional access controls, formal electronic sign-off and production integration require further implementation; see [deployment boundaries](docs/deployment.md).
