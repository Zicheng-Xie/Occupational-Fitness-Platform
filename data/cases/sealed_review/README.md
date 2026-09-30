# Prospective clinician review set

This directory contains ten synthetic nurse notes, two for each pilot module. They were authored after the development and first holdout experiments. **Do not run retrieval, tune prompts, choose RRF weights or compare GraphRAG on these notes before clinicians return the review forms.** The set is sealed by SHA-256 fingerprints in `manifest.json` and has no system-derived labels.

`case_review_template.csv` asks a qualified reviewer to identify relevant guideline source IDs, acceptable alternatives, patient facts, missing facts and a provisional clinical assessment. `source_review_template.csv` asks reviewers to check the 28 existing source anchors against the original guideline, including applicability and cross-references. All reviewer fields are intentionally blank. Reviewers should check the original PDF, not just the excerpt in the CSV.

Verify the seal without running the assessment system:

```powershell
.\.venv\Scripts\python.exe scripts/seal_review_pack.py --verify
```

Once review is complete, keep a copy of the signed forms, resolve disagreements with a second reviewer, record the final label version and only then run the frozen comparison. These authored examples are not patient records or clinical validation by themselves.
