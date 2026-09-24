# Data contracts

Software 0.7.1 uses WorkflowRuleResult 1.3.0 and RAGInput 1.2.0 (also accepts legacy 1.0.0/1.1.0 requests). Requests without narrative context continue to emit 1.1.0. Supporting assessment artifacts remain at 1.2.0; independent indicator contracts remain at 1.0.0. Run `fitness-rag export-schemas` to export nine JSON Schemas, the field dictionary and the team field contract. Run `fitness-rag build-knowledge` to rebuild source units and rule associations from the original guideline. See [Team integration](team_integration.md) for the indicator and browser endpoints.

RAGInput 1.2.0 adds optional `narrative_context` (request ID to verbatim `TextSpan` list) and `narrative_source_text_sha256`. These module-scoped symptom passages are unverified retrieval context, never rule facts. Each request is limited to 2,000 quote characters. The intake adapter selects exact source offsets; receivers validate request IDs, hash format, quote lengths and the declared version. A hash identifies the source but is not proof that an external caller supplied an authentic note. See [Complex nurse-note validation](complex_notes.md).

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

The model input is UTF-8 case text plus only the requested modules' entries from
`field_dictionary.json`. Model output is a strict `proposals` JSON object. Each
proposal contains an exact dictionary field name, typed value, verbatim quote,
patient/other subject, explicit/uncertain certainty and temporality. Only facts
that pass deterministic validation enter `ClinicalCase.facts`.

Example input:

```text
The patient denies a history of diabetes mellitus.
```

Model proposal contract:

```json
{
  "proposals": [
    {
      "field": "diabetes.present",
      "value": false,
      "quote": "The patient denies a history of diabetes mellitus.",
      "subject": "patient",
      "certainty": "explicit",
      "temporality": "history"
    }
  ]
}
```

After validation the canonical output remains dictionary keyed:

```json
{
  "facts": {
    "diabetes.present": {
      "value": false,
      "status": "present",
      "unit": null,
      "evidence": [
        {
          "start": 0,
          "end": 50,
          "quote": "The patient denies a history of diabetes mellitus.",
          "line_start": 1,
          "line_end": 1,
          "pdf_page": null
        }
      ],
      "method": "llm_grounded",
      "derived_from": []
    }
  }
}
```

Runtime `present` facts always contain an exact source span.

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
ruleset/guideline fingerprints, route, `rag_requests` and request-scoped
`indicator_context` in version 1.1.0. Context contains only each rule's required
fields, their validated values/statuses and source spans. It does not receive
the internal evaluation tree, Red Flag list or missing-information decisions.
The returned evidence pack binds itself to the complete Red Flag result hash.
Legacy RAGInput 1.0.0 remains accepted without indicator context and uses field
names and ambiguity reasons as its query fallback. Exported 1.1.0 payloads need
the updated schema; older strict clients should omit context and send 1.0.0.
New file assessments save `rag_input.json` alongside the public rule result.
`POST /red-flag/evaluate` returns this projection for every route: fast paths
need source binding and non-fast paths also use ranked evidence. The optional
three-way API route label does not override the deterministic workflow route.

Rule requests identify their rule, sources, category, subcondition and commercial context. Each evidence item returns complete, partial or no_evidence status, unresolved sources, actual filters, citations and ranking records.
For an unresolved rule, the request also carries dictionary-keyed `fact_context`
and bounded `ambiguity_reasons`; it never carries an unverified model value as a
patient fact.

Exact-source scores are not medical confidence estimates. Evidence must match the case, rule version, result fingerprint, request ownership and guideline text. `verify-run` replays rules and checks artifact fingerprints.

The actual hearing example is in `examples/contracts/syn_m2_009/`. Its input records 45 dB without audiometry frequencies, so the four-frequency threshold is not inferred. Use these validated examples and the generated schemas for API integration.

## Extraction review audit

`llm_semantic_review.json` records the second-pass status, prompt and model fingerprints, bounded retry attempts, checked fields, source-bound concerns, original quarantined facts and final fact hashes. The same audit is embedded in the structured case. `semantic_review_response.schema.json` defines independent source observations from the model; the runtime additionally verifies field scope, complete checked-field coverage and verbatim source quotations. Independent observation values remain in the audit and cannot replace case facts. See [Extraction semantic review](semantic_review.md).
