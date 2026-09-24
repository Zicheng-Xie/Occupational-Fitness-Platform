# Collaboration integration: 0.7.1

This integration combines the local indicator retrieval and independent extraction review work with the collaborator's Red Flag changes on GitHub `main`, commit `3da6920067c703c87782ed5f6cfcd61ad2e31498`. The `red-flag` branch changes are already included in that main commit; they should not be merged a second time.

**Current policy:** version 0.7.1 restores the owner's pre-integration framework. The 0.7.0 route-model default, restricted ranking trigger and vasovagal OR rule are superseded. See [Framework preservation](framework_preservation.md).

## Integrated responsibilities

| Area | Integrated behavior | Main files |
|---|---|---|
| Intake | Requested-module dictionary, overlapping note segments, source offsets, subject and certainty checks | `case_intake/model_intake.py`, `llm.py` |
| Independent review | Re-read original notes after fact validation; quarantine concerns before rules | `case_intake/semantic_review.py`, `pipeline/workflow.py` |
| Red Flag | Deterministic result with explicit red flags, missing information and ruleset identity | `red_flag.py`, `schemas/red_flag_result.py` |
| Route advice experiment | Retained for explicit experiments and historical replay; disabled in all shipped profiles | `pipeline/workflow.py`, `llm.py` |
| Retrieval | Required source binding, scoped indicator queries and metadata-filtered hybrid ranking for all non-fast requests | `retrieval/workflow.py`, `retrieval/query_builder.py` |
| Browser | Existing English workspace, upload queue, stage progress and indicator endpoints; new Red Flag API shares the workflow lock | `api.py`, `web/routes.py`, `web/jobs.py` |
| Historical records | Verify original artifacts and retained PDF citations without replaying against newer rules; visibly label historical reports | `reporting/archive.py`, `web/routes.py` |

Paths in the table are relative to `src/occupational_fitness_rag/`.

## Contract adaptation

The public `WorkflowRuleResult` remains **1.3.0**. `RuleBook.evaluate()` returns an internal `RuleEngineResult`; application consumers use `RedFlagEvaluator.evaluate()` and the public contract. Processing warnings are structured objects; report builders read their `message` field.

`RAGInput` **1.1.0** adds `indicator_context`, keyed by request ID. Each entry carries only the requested rule's required fields and their validated source spans. It excludes the full note, diagnosis outcome and rule evaluation tree. The retriever rejects fields outside that rule. Unconfirmed facts have no authoritative value. The legacy **1.0.0** envelope remains accepted without context, using field names and ambiguity reasons for fallback queries. New 1.1.0 payloads require an updated receiver; older strict receivers cannot accept the new field.

`rag_input.json` is saved in new assessment bundles. Evidence continues to bind to the complete public rule-result fingerprint. Verification recomputes the deterministic result and reapplies recorded route advice, without another model call. This verifies reproducibility of the saved handling decision; it does not prove that model advice is correct.

Required citations are always bound. Fast paths skip ranking. Every request in a non-fast case can use metadata-filtered vector/BM25/RRF ranking, including `triggered_rule_evidence`. Independent `/rag/indicators` retrieval keeps its existing hybrid default. No retrieval algorithm or full cross-disease graph was introduced in this integration.

## Model compatibility

The default remains the installed **`llama3:8b`**, with `nomic-embed-text` for Chroma. Qwen remains configurable. Extraction, independent semantic review and report commentary are separate calls and audits. Optional route advice is disabled by default; historical advice remains replayable. An empty route quotation is withheld. Oversized route inputs retain deterministic handling instead of silently truncating notes.

The collaborator's chunking and subject/uncertainty checks are retained. Generic disease-keyword or number matching is not sufficient to authorize a specific field: a blood-pressure number cannot be assigned to the wrong component, and a hearing measurement does not establish that specialist information exists. Unsupported phrasing remains unknown or requires review. Repeated quotations are checked against the selected occurrence's context.

The initial integration included the collaborator's vasovagal OR condition. Version 0.7.1 restores the original AND condition and original rulebook fingerprint, with regenerated knowledge contracts and catalogue. This preserves the owner's existing policy and does not constitute new clinical validation.

## Validation and limits

Run `python -m pytest -q`, `python scripts/verify_demo.py`, and `python scripts/validate_collaboration.py`. The last command optionally accepts `--history-root PATH` to verify retained local run bundles. Export contracts with `fitness-rag export-schemas`.

The historical 0.7.0 integration run completed **165 automated tests**, Ruff lint/format checks, **23/23** original rule regressions, **30/30** fixed report verifications and **34/34** retained local historical report verifications. Two real Llama/Chroma smoke runs generated auditable reports: one clean semantic review and one human-review route. Neither run accepted new model-proposed facts; the results must not be described as successful general language extraction.

Integration checks cover the original 23 development regression cases, all 30 fixed demonstration bundles and the collaborator's 15 varied natural-language fixtures. The latter match expected labels in **6 of 15 offline cases** in both unmodified upstream main and the integrated code; all 15 outcomes are unchanged. The nine remaining label mismatches are existing offline extraction coverage limitations, not successful assessments. See `outputs/evaluation/collaboration/` for the baseline, individual results and fingerprints.

Real local-model smoke checks exercise complete report production and the audited human-review fallback. They are integration checks, not held-out clinical accuracy measurements. Previous retrieval and semantic-review experiment outputs retain their original versions and must not be read as measurements of this merged release.

Historical reports are preserved byte for byte. Their browser notice distinguishes artifact/PDF verification from current-rule replay. Creating a current assessment requires a new run from the original input. The fixed demonstration collection is regenerated under the restored workflow in 0.7.1. Superseded snapshots are retained in the local restoration backup; previous versions also remain available in Git history.
