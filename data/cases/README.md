# Case inputs

`nurse_notes/` contains ten supplied synthetic notes, preserved verbatim. `manifest.json` records their original fingerprints and categories. They mainly cover BP, cardiovascular history, vision and hearing. Unmentioned blackout or diabetes history cannot be assumed negative.

`synthetic_expansion/` contains twenty separately authored synthetic validation inputs covering all five modules, boundaries, waiting periods, missing information and special branches. Structured additions are test data, not proof of general free-text extraction accuracy.

`red_flag_experiment/` contains fifteen varied-format free-text cases for the Ollama intake experiment. Its manifest covers all five modules and the three displayed Red Flag classes: `RED_FLAG`, `NEEDS_MORE_INFORMATION` and `NO_RED_FLAG`.

The generator is `scripts/build_synthetic_cases.py`. Independent rule expectations are in `gold/workflow_expectations.json`; see [validation scope](../../docs/validation.md).
