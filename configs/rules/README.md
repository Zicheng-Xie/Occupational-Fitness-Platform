# Austroads commercial rules

`austroads_commercial_v1.yaml` is the authoritative editable rulebook for the
five-module commercial-driver prototype: hypertension, vision, hearing,
blackout and diabetes. It is JSON-compatible YAML and currently has
`pending_clinical_review` status.

## Safety behaviour

- Unknown, conflicting or unconfirmed required facts are never coerced to
  `false`; they produce an insufficient-information path where relevant.
- `meets_unconditional_standard` requires an explicit positive screening or
  standard rule. The absence of a triggered restriction is not a pass.
- Conditional eligibility is not a licensing decision. Human clinical and
  licensing-authority review remains required.
- One observed blood-pressure reading is not persistent hypertension.
- The hearing threshold uses `>= 40 dB` from the narrative and licensing
  table. The Figure 11 `> 40 dB` discrepancy remains a warning at the boundary.
- Findings outside the hypertension-only cardiovascular scope use the stable
  warning prefix `OUTSIDE_HYPERTENSION_SCOPE` and route to human review.

## Contracts and provenance

Every rule declares all facts used by its gate and predicate, one or more
`source_ids`, an outcome and a stable `rag_query_key`. Source IDs resolve to
PDF-verified entries in `data/knowledge/processed/knowledge_units.json`.
The generated `rule_knowledge_contract.json` is an export for review; it is not
the executable source of truth.

Outcome precedence is declared in the rulebook and loaded by the engine. The
list must contain each of the five supported outcomes exactly once.

Before clinical use, a reviewer must verify every source quotation, page,
operator, boundary, required fact, outcome and cross-reference, populate the
approval metadata and rerun the complete regression suite.
