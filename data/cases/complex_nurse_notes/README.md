# Complex nurse-note inputs

This folder contains **224 uploadable English UTF-8 text files**: 24 earlier
inputs and 200 new `CX-LONG-001.txt` through `CX-LONG-200.txt` files. The original
24 files are unchanged. The separately stored `validation_nurse_notes` cohort is
not part of this folder's count.

## New 200-case cohort

The notes are authored synthetic software-test records, not real patients or
case histories quoted from the guideline. Their clinical scenarios are grounded
in the existing AP-G56-22 commercial-driving guideline, including its explicitly
referenced general guidance. They cover hypertension, vision, hearing, blackout
and diabetes, with 40 primary-module cases each and 40 multi-module cases.

Each note has 231-312 whitespace-separated English words and at least three
sentences of 35 or more words. Forty scenario families have five correlated
variants each, with different numerical boundaries, documentary context and
mixed-module complications where specified. This is a development stress cohort,
not 200 independently sampled patients or an independently labelled clinical test.

`long_200_manifest.json` and `long_200_input_inventory.csv` identify the recommended
assessment modules, input fingerprints and complexity. For reproduction, select
the listed module or modules before uploading one TXT file. Selecting all five
modules can add legitimate unknowns for conditions not assessed in that note.

Only the TXT file is the clinical input. Do not upload the manifest, CSV, expected
outcomes or source labels. Engineering references and their original PDF locations
are stored separately in `../gold/complex_long_200.json`; clinical review is pending.

## Reproduce the complete evaluation

From the project root, with Ollama, `llama3:8b` and `nomic-embed-text` available:

```powershell
.venv/Scripts/python.exe -X utf8 -m tools.run_complex_long_study --prepare-only
.venv/Scripts/python.exe -X utf8 -m tools.run_complex_long_study --resume
```

The new evaluator preserves production logic and uses a separate index directory.
It performs live intake, semantic review, rules and retrieval, with optional
report-prose generation disabled. Ordinary template reports are still generated.
It also compares vector, BM25 and Hybrid RRF discovery on 88 frozen original
passages, querying with each entire note rather than reference source IDs.
A separate experimental Llama judgment uses the actually accepted facts and
whole Hybrid-retrieved originals; it never changes a production assessment.

Open `outputs/evaluation/complex_long_200_20261027/index.html`. Check completion
counts before quoting metrics. Retrieval coverage, engineering outcome agreement,
fact checks, abstentions and failures are separate measures. Mandatory rule-bound
citations are not treated as successful unconstrained retrieval.

The earlier `evaluation.complex_notes` command still evaluates its original
small fixture. It does not automatically evaluate all 224 files in this folder.
