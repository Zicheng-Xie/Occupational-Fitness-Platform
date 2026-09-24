# Retrieval and judgment experiments

The indicator study measures discovery independently of exact source binding. Expected source IDs are used only for scoring and are never passed to retrieval.

```powershell
.\.venv\Scripts\fitness-rag.exe export-schemas --config configs/workflow.offline.yaml
.\.venv\Scripts\fitness-rag.exe retrieval-study --config configs/workflow.offline.yaml --backend offline --output outputs/evaluation/indicator_retrieval_offline.json
.\.venv\Scripts\fitness-rag.exe retrieval-study --config configs/workflow.offline.yaml --backend chroma --output outputs/evaluation/indicator_retrieval_chroma.json
.\.venv\Scripts\fitness-rag.exe judgment-study --config configs/workflow.offline.yaml --limit 5 --output outputs/evaluation/model_judgment.json
```

The Chroma study requires local embeddings even with generation disabled. The judgment command explicitly calls the configured LLM regardless of `llm.enabled`; running the experiment is the opt-in. Its offline config keeps fact extraction deterministic.

## Design and limits

The 22 synthetic indicator queries cover all five modules, boundary values, missing data, negation and multiple-section expectations. Labels are source-based engineering expectations pending human review, not independent clinical gold or held-out accuracy data.

Each query compares vector-only, BM25-only and hybrid RRF, with Top 1, 3, 5 and 10 scored from the same Top 10 ranking. Offline vector-only is a lexical cosine surrogate; Chroma uses local `nomic-embed-text`. Explicit reference expansion is excluded from ranked scores.

Three grouping strategies use the same verified anchors: individual units, grouped sections and grouped pages, always within a module. They do not represent newly extracted full PDF chapters. Top K counts chunks; broader grouped chunks return more sources and characters. Compare evidence volume alongside recall.

Reports include source Recall@K, MRR, complete expected-source coverage, label precision, section/page hits, source counts and character counts, by query and module. Unlabelled sources are not necessarily irrelevant. Label precision is limited by draft labels. High page hit rates do not establish correct rule interpretation.

Blackout queries cover undiagnosed mechanisms, provoked syncope, single and recurrent events and referral to a diagnosed condition. Diabetes includes severe hypoglycaemia with multiple sections. The corpus has 28 configured units and does not cover every cardiovascular, seizure or sleep-related referral destination. New destinations require reviewed source anchors. GraphRAG and learned reranking remain future comparisons after a measurable baseline.

## Isolated LLM judgment

Llama 3 8B receives clinical facts and retrieved evidence, without the rule outcome or development label. Its structured answer contains an outcome, explanation and supplied-source IDs. It is saved only in the experiment report and never changes production assessments.

The report includes valid completions, failures, context-budget skips, model fingerprints, timing and rule agreement. Oversized prompts are skipped explicitly. Agreement is not clinical accuracy. Citation identity is checked automatically; whether the evidence supports the explanation remains a human review task.

## Review before changing defaults

Human reviewers should verify category assignment, complete relevant-source sets, acceptable alternate sources, clinical facts and decision labels, then establish a separate frozen holdout set. Review extraction errors separately from retrieval errors. Select grouping and Top K on that reviewed set, including evidence volume and all-required-source coverage.
