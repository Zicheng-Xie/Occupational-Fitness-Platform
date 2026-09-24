# Five-module Red Flag text experiment

These 15 UTF-8 text files are synthetic and contain no real patient data. They cover hypertension, blackout, vision, hearing and diabetes using narrative notes, key-value summaries, questionnaires, referral letters, test reports, dictation, checklists, progress notes, discharge summaries and email-like text.

The experiment uses three display classes:

- `RED_FLAG`: a triggered rule has a `temporarily_unfit` or `does_not_meet_standard` outcome.
- `NEEDS_MORE_INFORMATION`: required information is absent, conflicting or requires confirmation.
- `NO_RED_FLAG`: no Red Flag rule triggered. This can still include `may_meet_conditional_standard` and human review.

Run one case:

```cmd
.venv\Scripts\fitness-rag.exe assess --config configs\workflow.yaml --input data\cases\red_flag_experiment\BLK-REDFLAG-EDNOTE.txt --modules blackout
```

Run the complete manifest:

```cmd
.venv\Scripts\fitness-rag.exe assess-suite --config configs\workflow.yaml --manifest data\cases\red_flag_experiment\manifest.json
```

Each CLI result includes `red_flag_classification`, rule IDs, missing fields and `guideline_references`. Every reference contains the verbatim `source_text`, section, printed page, PDF page and verification flag from `data/knowledge/raw/ap_g56_22.pdf`.

After restarting the FastAPI service, Swagger exposes the same set under the `Red Flag experiment` group:

- `GET /experiment/cases` lists all case texts and expected results.
- `GET /experiment/cases/{case_id}` shows one case.
- `POST /experiment/cases/{case_id}/evaluate` runs it and returns the three-way result, rule IDs, missing fields and verified PDF quotations.
- `POST /experiment/cases/{case_id}/evaluate.txt` displays the final `RAG_INPUT` or `DIRECT_RESULT` inline as UTF-8 text. Swagger shows the body directly and also offers its standard Download button.

The JSON assessment presents seven ordered processing steps, every accepted or contested dictionary fact with its source quotation, the deterministic rule result, the three-way route, verified PDF evidence, and the exact final text payload.

`manifest.json` contains engineering expectations for regression comparison. The ruleset and source entries remain `pending_clinical_review`.
