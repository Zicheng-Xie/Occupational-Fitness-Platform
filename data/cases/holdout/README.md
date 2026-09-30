# Synthetic holdout for engineering review

The ten `notes/HOLD-*.txt` files are new, synthetic, uploadable nurse notes spanning the five pilot modules. They contain no patient data. Their wording is separate from the development query fixtures. The holdout was written and its provisional source labels fixed before the retrieval-heading experiment reported below; it has not been used to choose a replacement production method.

`complex_notes.json` contains one labelled retrieval query per note. These source IDs are provisional mapping hypotheses, not clinician-adjudicated truth. `indicator_queries.json` is intentionally empty so the same comparison command can evaluate only the long-note cohort. `reasoning_cases.json` has no expected fitness outcomes: the reasoning audit checks source links and rule trace integrity without pretending to measure clinical accuracy.

The reasoning audit also produces `case_review_queue.csv`. Its provisional outcome and extracted evidence are shown for comparison, while clinician outcome, verified/rejected facts and reviewer fields remain blank. Clinicians should review the original note and guideline rather than copying the provisional result into those columns.

To review source relevance, run the Chroma comparison and open `review_queue.csv` in the output directory. A qualified reviewer should enter the reviewed relevant source IDs, acceptable alternative source IDs, interpretation, name, date and notes. The worksheet is a blank review template; do not fill it with system predictions. Reviewers should also inspect the original PDF at the page and section cited by each proposed source.

```powershell
.\.venv\Scripts\fitness-rag.exe rag-comparison --config configs/workflow.offline.yaml --backend chroma --indicators data/cases/holdout/indicator_queries.json --complex-notes data/cases/holdout/complex_notes.json --output outputs/evaluation/rag_comparison/holdout_baseline
.\.venv\Scripts\fitness-rag.exe reasoning-study --config configs/workflow.offline.yaml --gold data/cases/holdout/reasoning_cases.json --output outputs/evaluation/reasoning_study/holdout
```

The offline reasoning command deliberately disables the local model. It therefore tests deterministic source tracing, not the complete extraction path. For an end-to-end model check, run `assess` with `configs/workflow.yaml` on a note and inspect `llm_extraction_audit.json`, `llm_semantic_review.json`, `rule_result.json` and `evidence_pack.json` together. An `insufficient_information` result can arise before retrieval when facts are withheld; candidate guideline citations do not establish that a rule was triggered.
