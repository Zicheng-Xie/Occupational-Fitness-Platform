# Complex nurse-note validation inputs

Upload one UTF-8 `.txt` file through the local workspace at `http://127.0.0.1:8000`.
Select all five modules to reproduce the saved batch configuration. Use a new case
reference for each test and wait for **Assessment complete** before opening its report.

- `VAL-MIX-01`–`VAL-MIX-08`: explicit positive facts embedded in complex narratives.
- `VAL-MIX-09`–`VAL-MIX-10`: uncertainty controls; unsupported clinical rules must not trigger.

Start with `VAL-MIX-04` to inspect insulin treatment and confirmed diplopia, then
`VAL-MIX-09` to compare an uncertain input. In each report, inspect **Retrieval activity**
separately from **Triggered rules**. Unknown information in other requested modules can
keep an overall result insufficient even when a documented module triggers a rule.

Scoring expectations are in `../gold/validation_complex_expectations.json`. They are
never part of the upload and are not provided to the model. These synthetic cases
were used during debugging and are regression data, not independent clinical gold.

The saved comparison is `outputs/evaluation/rag_diagnostics/index.html` from the project
root. See `docs/rag_diagnostics.md` for implementation details and reproduction commands.
