# Established workflow preservation: 0.7.1

The owner's framework is the integration boundary. Collaborator code must adapt to this sequence:

**Original notes → local model extraction and indicator classification → field and source validation → independent local model semantic review → deterministic rules and routing → indicator-scoped guideline retrieval → evidence-backed draft → clinician review.**

The deterministic rule stage was already part of the original platform. The second model pass reviews extracted meaning against the original notes before rules and retrieval. It is not an additional model route classifier. Clinical authorization remains a human responsibility; generated reports remain drafts.

## Restored behavior

| Area | Current default | Implementation |
|---|---|---|
| Additional model routing | Disabled in all shipped profiles and in configuration defaults | `configs/workflow.yaml`, `pipeline/config.py` |
| Deterministic routing | Outcome-based routes from the original workflow; warnings escalate to human review | `rules/engine.py` |
| Retrieval trigger | Fast cases bind exact sources; every request in non-fast cases also ranks with the configured backend | `retrieval/workflow.py` |
| Retrieval method | Chroma vectors and BM25 combined through RRF; indicator-specific queries and strict metadata filters are retained | `retrieval/engine.py`, `retrieval/query_builder.py` |
| Vasovagal exception | Original AND predicate restored; one true condition alone is insufficient to trigger the exception | `configs/rules/austroads_commercial_v1.yaml` |
| Red Flag interface | Public result 1.3.0 and RAGInput 1.1.0 retained as adapters, with legacy 1.0.0 input accepted | `red_flag.py`, `schemas/red_flag_result.py` |

Python paths in this table are relative to `src/occupational_fitness_rag/`.

An explicit `exact` retrieval configuration still skips ranking, as before. The optional route-model code remains available for deliberately enabled experiments and for verifying previously recorded advice. Normal assessment does not invoke it.

`POST /red-flag/evaluate` now returns its RAG input for every route. This preserves the established evidence stage even when the API's summary label is `local_result` or `needs_more_information`. The separate API endpoint stops before retrieval; `/assess` and browser/file assessments execute the complete workflow.

## Regression boundary

`data/cases/gold/framework_routing_expectations.json` captures 30 original synthetic cases from the pre-integration local 0.6.0 snapshot. The comparison checks outcomes, per-module and overall routes, request types, ranking calls and required citations. The restored rulebook fingerprint is `cae808a441f7956628cd772c819097e8c273cf44d56116155082c67a76ad3aaa`.

`tests/test_framework_preservation.py` protects phase order for text and file intake, prohibits the extra route-model call under defaults, and compares the original routing snapshot. `tests/test_red_flag.py` checks AND truth/missing-value boundaries and ranking of triggered as well as unresolved requests. These protect engineering behavior; they are not a new clinical validation study.

The 0.7.1 test run passes **176 tests**, including the 30-case behavior comparison. See `outputs/evaluation/framework_preservation/` for current verification results. The earlier `outputs/evaluation/collaboration/` results remain historical measurements of 0.7.0.

## Report and knowledge consistency

The source catalogue and generated knowledge/field contracts are rebuilt with the restored rulebook fingerprint. Chroma selects the collection corresponding to that index. The 30 distributed examples are regenerated offline with the restored policy; they make no local-model performance claim. Superseded demonstration files are retained in the local restoration backup and Git history. Existing local assessment bundles are preserved unchanged and remain accessible through historical verification when their schema or ruleset differs.

The independent semantic review, source quotes, PDF page/section/bounding-box citations, English report design, browser upload queue and clinician-review boundary are preserved.
