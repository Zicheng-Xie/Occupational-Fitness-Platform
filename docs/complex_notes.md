# Complex nurse-note validation

The platform accepts long-form nurse notes as ordinary UTF-8 `.txt` input. The new
synthetic set contains 12 complex cases and two short negative controls. It covers
hypertension, vision, hearing, blackout and diabetes, including two cases involving
multiple modules. These are engineering fixtures, not real patient records or an
independently reviewed clinical benchmark.

## Inputs and expected behavior

Upload files from `data/cases/complex_nurse_notes/`, or paste their content into the
workspace. Select the modules listed for each case in
`data/cases/gold/complex_notes.json`. The evaluator explicitly selects those modules;
requesting additional modules in the UI can introduce additional missing information.

| Cases | Challenges |
|---|---|
| CX-HTN-01 / 02 | Changing BP, historical readings, treatment timing, family history |
| CX-VIS-01 / 02 | Intermittent double vision, correction status, unreliable fields |
| CX-HEAR-01 / 02 | Aided versus unaided testing, missing frequencies, disputed records |
| CX-BLK-01 / 02 | Blank spells, witness disagreement, uncertain cause and event counts |
| CX-DM-01 / 02 | Treatment changes, possible hypoglycaemia, symptoms without diagnosis |
| CX-MIX-01 / 02 | Blackout with diabetes; hypertension with visual and hearing symptoms |
| CX-CTRL-01 / 02 | Explicit absence of diabetes or blackouts; fast-path controls |

Complexity alone does not select RAG. Deterministic rule outcomes and missing or
disputed facts control routing after model extraction and semantic review. Clear
abnormal inputs can still need RAG, while clear sufficient negative inputs can use
the fast path. The approved clinical rules and thresholds are unchanged.

## Changes

- `case_intake/traceable.py` rejects positive-report matches containing negation,
  withholds historical or explicitly unverified measurements, and retains units
  on uncertain/conflicting numeric facts. Qualified absence such as no diplopia
  at rest does not establish absence in all driving conditions.
- `case_intake/model_intake.py` preserves units and provenance dependencies when
  model values conflict with baseline measurements.
- `llm.py` explicitly distinguishes definite negative statements from uncertain
  statements in the extraction instructions.
- `case_intake/semantic_review.py` retains uncertain source observations even when
  baseline extraction missed the field. Invalid reviews record their validation
  reason; the bounded retry receives that reason. Failed reviews require a human.
- `case_intake/narrative_context.py` selects verbatim module-related sentences with
  common symptom vocabulary. It preserves negation and temporal context, excludes
  structured addendum lines and caps each module at 2,000 characters. Sentences
  longer than the remaining budget are skipped, not cut into misleading fragments.
- `red_flag.py`, `schemas/red_flag_result.py` and `retrieval/query_builder.py` carry
  these passages through RAGInput 1.2.0 and label them as unverified narrative.
  They cannot change an authoritative fact or rule outcome.
- `retrieval/workflow.py` exposes the context mode and request count in its audit.
  Required exact citations, existing filters and hybrid ranking remain in place.
- `pipeline/workflow.py` verifies older saved bundles using their original
  projection, while accepting normalized legacy RAGInput defaults.
- `evaluation/complex_notes.py` runs raw-note assessment and a separate retrieval
  comparison, saving per-case reports, model audits, rankings and an English HTML
  overview. `tests/test_complex_notes.py` protects the reproduced failures.

## Run the checks

From the project root, with Ollama running and `llama3:8b` and `nomic-embed-text`
installed:

```powershell
.\.venv\Scripts\python.exe -m occupational_fitness_rag.evaluation.complex_notes --output outputs/evaluation/complex_notes/my_live_run --profile live
```

The evaluator uses the normal extraction, semantic review, rules and retrieval
pipeline. It disables only optional report prose generation, which is unrelated
to this test. Each case still receives an ordinary template-based draft report.

For repeatable checks without model services:

```powershell
.\.venv\Scripts\python.exe -m occupational_fitness_rag.evaluation.complex_notes --config configs/workflow.offline.yaml --output outputs/evaluation/complex_notes/my_offline_run --profile offline
.\.venv\Scripts\python.exe -m pytest tests/test_complex_notes.py -q
```

Use `--only CX-MIX-01` for a single case and `--no-discovery` to skip the separate
retrieval comparison. Keep separate output directories for different experiments.

## Inspect the output

Open `outputs/evaluation/complex_notes/validated_live/index.html`. Each case links
to `draft_report.html`; the associated directory contains `structured_case.json`,
`llm_extraction_audit.json`, `llm_semantic_review.json`, `rule_result.json`,
`rag_input.json` and `evidence_pack.json`. In the evidence pack, inspect
`retrieval.ranking_calls`, `semantic_query`, `metadata_filters` and
`ranked_candidates`. A report existing does not prove retrieval occurred.

The second part of the HTML compares vector, BM25 and hybrid RRF on 18 manually
selected original paragraphs at Top 1, 3 and 5. Expected sources are passed only
to scoring. This broader module-level discovery test isolates ranking quality;
it is not the tightly rule-filtered production query, nor a measure of automatic
passage-selection accuracy. Report its source Recall@K as retrieval coverage,
not patient-level accuracy. The offline vector branch is a lexical surrogate.

## Boundaries

The vocabulary selector cannot understand every clinical paraphrase; mixed
sentences may legitimately contribute to multiple modules. Passing an abstention
check means an unsupported value stayed unconfirmed, not that the model correctly
extracted all facts. Model output can still fail schema, coverage or exact-quote
validation; those cases are explicitly routed for human review. Rules still use
the existing verified source catalogue rather than a complete cross-disease graph.
Do not infer that hybrid RRF is superior merely because it is the default.
