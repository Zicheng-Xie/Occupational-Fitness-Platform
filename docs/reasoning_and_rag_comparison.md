# Evidence-linked reasoning and RAG method comparison

This document records engineering experiments on synthetic commercial-driver cases. The results are **not** a clinical validation, fitness certificate, or independent estimate of real-world accuracy. The established production sequence remains: note intake -> grounded fact validation -> semantic review -> deterministic rule evaluation -> source-bound hybrid retrieval -> draft report -> clinician review.

## Evidence-linked reasoning audit

`fitness-rag reasoning-study` runs the rule engine and retrieval on 23 development cases. For each triggered or unresolved rule, the HTML and JSON reports show the original nurse note, verified patient fact quotations, predicate trace, provisional rule result, and matching guideline source text with section and page. Automated checks verify exact note spans, requested source-ID coverage, catalogue/PDF identity, and that retrieval did not modify the rule result. All **23/23** cases passed these engineering checks. The labels were created for development, and the audit does not prove that a guideline passage semantically entails the clinician-facing conclusion.

Open [the reasoning audit](../outputs/evaluation/reasoning_study/index.html) or inspect [its JSON record](../outputs/evaluation/reasoning_study/results.json).

The separate local-model study does **not** receive the rule outcome or expected label in its prompt. It receives the nurse note, verified patient facts with original quotations, and the bound guideline passages. It must return an outcome, explanation, source IDs and fact-field IDs. Source IDs and fact fields are checked against the supplied data; invalid citations are rejected. Explanations still need human entailment review, and the model answer never modifies the assessment.

| Llama 3 8B experiment | Cases | Accepted answers | Agreement with deterministic rules |
|---|---:|---:|---:|
| Initial blind prompt, development cases | 5 | 5 | 1/5 |
| Clarified outcome meanings, same development cases | 5 | 5 | 2/5 |
| Clarified prompt, five other synthetic development cases | 5 | 5 | 1/5 |

The initial and clarified prompts used the same first five cases, so the second row is a prompt-development result, not a held-out gain. The other five cases come from the existing synthetic development suite and are not independent clinical gold. In several cases, the model treated explicit no-driving or disqualifying evidence as merely insufficient information; in others, the revised prompt over-selected temporary unfitness. **The model is not suitable as an autonomous fitness decision-maker on this evidence.**

Inspect [the clarified model trial](../outputs/evaluation/reasoning_study/model_development.html), [the additional-case trial](../outputs/evaluation/reasoning_study/model_additional.html), and [the initial baseline JSON](../outputs/evaluation/reasoning_study/model_baseline.json). Each accepted answer is experimental and unverified even when the cited IDs are valid.

## Retrieval comparison

The new `rag-comparison` command evaluates four ranked methods against exactly the same 40 labelled queries: 22 indicator queries and 18 manually selected paragraphs from complex nurse notes. All methods use the same 28 source-verified guideline anchors, module/commercial/version filters, and Top 1/3/5/10 scoring. Expected source IDs are supplied **only after retrieval** for scoring. Explicit reference expansion is excluded. The graph method starts from the top three hybrid results, then performs one-hop expansion over existing rule-source, cross-reference and section links. It is a **graph-assisted baseline, not full GraphRAG** and does not contain a full-PDF clinical knowledge graph.

| Real Chroma backend, Top 5, 40 queries | Mean source recall | Complete expected-source coverage | MRR |
|---|---:|---:|---:|
| Dense vector (`nomic-embed-text`) | 91.25% | 87.50% | 0.7775 |
| BM25 | 93.75% | 92.50% | 0.7654 |
| Hybrid RRF | **95.00%** | **92.50%** | 0.7579 |
| Graph-assisted expansion | 88.75% | 82.50% | 0.6879 |

On the 18 complex-note paragraphs alone, hybrid RRF reached **94.44%** source recall and **88.89%** complete coverage at Top 5. BM25 reached 91.67% and 88.89%; dense vector reached 80.56% and 72.22%; graph-assisted expansion reached 75.00% and 61.11%. The margin is small and labels need independent review, so this is a development result rather than a universal ranking. Hybrid remains the current production choice; the graph-assisted baseline does not justify replacing it.

An offline comparison is also saved, but its "vector" method is a lexical cosine surrogate rather than a dense embedding. In that run BM25 led at Top 5. Do not combine or rank offline and Chroma results as if they used the same vector model. Open [the real Chroma comparison](../outputs/evaluation/rag_comparison/chroma/index.html) and [the offline comparison](../outputs/evaluation/rag_comparison/offline/index.html).

The Chroma Top 5 result misses some expected sources for insulin-treated diabetes and undiagnosed blackout work-up. Before changing retrieval defaults, clinicians should review the expected source sets, acceptable alternative passages, and the exact query/source wording. A future full GraphRAG experiment needs reviewed entities and cross-condition edges from more of the guideline, then the same frozen query set, evidence-volume accounting, cost/latency measurement, and an independently labelled holdout. The supplied framework presentation also proposes a no-embedding hierarchical search engine; that is a separate future comparator, not the graph baseline implemented here.

## Frozen synthetic holdout and error review

Ten new uploadable nurse notes and their provisional retrieval labels are under `data/cases/holdout/`. They were not copied from the development query fixture. They are **not** independent clinical gold: no clinician has adjudicated source relevance or fitness outcomes. The comparison now writes `error_analysis.json` for every incomplete Top-5 source set and `review_queue.csv` for adjudicating all hybrid queries, including apparent successes. The reasoning audit writes `case_review_queue.csv` for case-level adjudication. Both worksheets have deliberately blank reviewer columns.

With the unchanged Chroma index, hybrid RRF obtained 95% mean provisional-source recall and 90% complete-source coverage at Top 5 on these ten notes. The remaining incomplete query was `HOLD-DM-01-Q1`: the insulin-treated source `AFTD2022-DM-COM-007` ranked eighth despite an explicit current insulin prescription. A trial that prepended catalogue row headings to indexed passages improved development hybrid recall from 95% to 97.5%, but reduced holdout hybrid recall from 95% to 90%. **That trial was reverted**; the production index and method were not changed. The before/after experimental reports remain under `outputs/evaluation/rag_comparison/` for audit.

The unlabeled offline reasoning audit linked the source-verified rule traces for 10/10 holdout notes. All ten provisional results were `insufficient_information` because the notes leave at least one rule-required fact undocumented. This is a source-trace integrity result, not evidence that all ten patients are clinically indeterminate. An initial full `llama3:8b` smoke test on `HOLD-DM-01` exposed a narrower extraction gap: the model proposed current insulin use, but its quotation did not satisfy the strict field-semantic grounder; the semantic-review model also returned invalid source quotations. A bounded deterministic pattern was then added for a patient's historical diet-only treatment explicitly superseded by a **current insulin prescription**. It retains the complete source clause and rejects old prescriptions, family history and negated insulin. In the repeat full workflow run, `diabetes.present` and `diabetes.treatment_category = insulin` were grounded from the note, and the source-bound evidence included `AFTD2022-DM-COM-007`. The result remained `insufficient_information` because gestational status and other rule-required information were undocumented. The abstention is distinct from an RAG retrieval failure; it still needs clinician review.

Do not use these notes to claim a fitness accuracy rate. The next clinical step is to have qualified reviewers adjudicate the worksheet and a separate case-level outcome form against the original guideline, then freeze those labels before evaluating any further retrieval or reasoning changes.

## Reproduce

```powershell
.\.venv\Scripts\fitness-rag.exe reasoning-study --config configs/workflow.offline.yaml --output outputs/evaluation/reasoning_study
.\.venv\Scripts\fitness-rag.exe rag-comparison --config configs/workflow.offline.yaml --backend offline --output outputs/evaluation/rag_comparison/offline
.\.venv\Scripts\fitness-rag.exe rag-comparison --config configs/workflow.offline.yaml --backend chroma --output outputs/evaluation/rag_comparison/chroma
.\.venv\Scripts\fitness-rag.exe judgment-study --config configs/workflow.offline.yaml --case-ids SYN-EXT-002 SYN-EXT-018 SYN-EXT-020 SYN-EXT-003 SYN-EXT-013 --output outputs/evaluation/reasoning_study/model_development.json
.\.venv\Scripts\fitness-rag.exe judgment-study --config configs/workflow.offline.yaml --gold data/cases/gold/reasoning_additional_cases.json --output outputs/evaluation/reasoning_study/model_additional.json
```

The Chroma run requires local Ollama `nomic-embed-text`; the model study requires local `llama3:8b`. The offline reasoning audit does not call a model. All generated reports are English and remain local unless explicitly published.
