# Data contracts

Software 0.4.0 uses `WorkflowRuleResult` 1.3.0 as its sole rule-result contract. Supporting artifacts are independently versioned. Run `fitness-rag export-schemas` to export JSON Schema and the field dictionary. Run `fitness-rag build-knowledge` to rebuild source units and rule associations from the original guideline.

## Facts and model audit

`structured_case.json` stores canonical field keys, typed values, units, status, extraction method and exact source locations.

| Status | Meaning |
|---|---|
| present | Explicit, supported information |
| unknown | Not documented |
| conflicting | Incompatible source statements |
| requires_confirmation | Cannot be accepted automatically |

False requires an explicit negative statement. Model-grounded facts must pass quotation-context, semantic, type and range checks. A single BP reading does not establish persistent BP; a hearing average does not establish its calculation frequencies.

`llm_extraction_audit.json` records the model, weight digest, accepted fields, withheld proposals, call statistics and fallback status. Product-facing summaries use English; original evidence retains its source wording.

## Structured knowledge units

`data/knowledge/processed/knowledge_units.json` contains 28 source units:

| Field | Meaning |
|---|---|
| source_id | Stable source identifier |
| condition / standard / criterion_type | Condition, commercial context and unconditional/conditional/mixed/general criterion |
| section / printed_page / pdf_page | Section and distinct page references |
| table_row | Source table row |
| source_text / bounding_box | Verified quotation and PDF region |
| cross_references | Other sources associated through the same rules |

The aliases `source_text/evidence_text` and `bounding_box/bbox` must agree. Loading verifies the original PDF, quotations, coordinates and cross-references. Printed pages and PDF pages must not be interchanged.

## Rule encoding

`configs/rules/austroads_commercial_v1.yaml` is the authoritative editable rulebook. The generated `rule_knowledge_contract.json` exports 33 rules with `rule_id`, `required_facts`, readable `logic`, `result`, primary `source_id`, complete `source_ids`, executable `predicate`, applicability `gate`, `workflow_outcome` and `rag_query_key`.

Readable logic is for review; execution uses whitelisted structured predicates, never eval. Existing identifiers remain stable. Required facts must match the fields used by gates and predicates. Three-valued logic preserves false AND unknown = false and true OR unknown = true.

## Retrieval and reporting

`WorkflowRuleResult` schema 1.3.0 is the public deterministic-assessment output. It
contains the source/context/ruleset identities, five-class outcome, explicit
`has_red_flag`, `red_flags`, all `triggered_rules`, structured
`missing_information`, warnings and audit traces. The internal `RuleBook`
result is converted to this contract before retrieval. Missing information is
recorded separately and never becomes a Red Flag merely because it is missing.

RAG accepts only the separate immutable `RAGInput` envelope: result identity,
ruleset/guideline fingerprints, route and `rag_requests`. It does not receive
the internal evaluation tree, Red Flag list or missing-information decisions.
The returned evidence pack binds itself to the complete Red Flag result hash.

Rule requests identify their rule, sources, category, subcondition and commercial context. Each evidence item returns complete, partial or no_evidence status, unresolved sources, actual filters, citations and ranking records.

Exact-source scores are not medical confidence estimates. Evidence must match the case, rule version, result fingerprint, request ownership and guideline text. `verify-run` replays rules and checks artifact fingerprints.

The actual hearing example is in `examples/contracts/syn_m2_009/`. Its input records 45 dB without audiometry frequencies, so the four-frequency threshold is not inferred. Use these validated examples and the generated schemas for API integration.
