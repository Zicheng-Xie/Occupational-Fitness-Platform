# Prospective clinician review set

This directory contains ten synthetic nurse notes, two for each pilot module. They were authored after the development and first holdout experiments. **Do not run retrieval, tune prompts, choose RRF weights or compare GraphRAG on these notes before clinicians return the review forms.** The set is sealed by SHA-256 fingerprints in `manifest.json` and has no system-derived labels.

`case_review_template.csv` asks a qualified reviewer to identify relevant guideline source IDs, acceptable alternatives, patient facts, missing facts and a provisional clinical assessment. `source_review_template.csv` asks reviewers to check the 28 existing source anchors against the original guideline, including applicability and cross-references. All reviewer fields are intentionally blank. Reviewers should check the original PDF, not just the excerpt in the CSV.

Verify the seal without running the assessment system:

```powershell
.\.venv\Scripts\python.exe scripts/seal_review_pack.py --verify
```

Once review is complete, keep a copy of the signed forms, resolve disagreements with a second reviewer, record the final label version and only then run the frozen comparison. These authored examples are not patient records or clinical validation by themselves.

After the reviewer fields are filled, validate their structure and source IDs without changing any clinical label:

```powershell
.\.venv\Scripts\python.exe scripts/validate_review_labels.py --cases path/to/completed_case_review.csv --sources path/to/completed_source_review.csv --output path/to/reviewed_labels_v1.json
```

The validator rejects incomplete rows, changed case fingerprints and out-of-module source IDs. It does not decide whether a clinician's interpretation is medically correct. A `needs_revision` or `rejected` source keeps the result in `reviewed_pending_adjudication` status.
