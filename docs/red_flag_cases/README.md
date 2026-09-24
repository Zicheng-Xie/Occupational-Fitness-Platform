# Red Flag boundary under the established workflow

The Red Flag module adapts deterministic rule results to `WorkflowRuleResult` 1.3.0. It does not replace the owner's workflow or add a model decision stage. Local-model extraction, field/source validation and independent semantic review precede rule evaluation. Additional model route advice is disabled by default.

`POST /red-flag/evaluate` stops before retrieval and returns the structured case, public rule result, source locators and `RAGInput` for every route. The complete `/assess` and browser/file workflows then retrieve evidence and produce drafts.

| Example | Outcome and route | Evidence behavior in the complete workflow |
|---|---|---|
| Reduced hearing with incomplete audiometry | Insufficient information; `missing_information` | Bind required sources and rank every emitted request |
| Supported four-frequency audiometry below the rule threshold, without other outstanding findings | Meets unconditional standard; `fast_path` | Bind exact required sources; skip ranking |
| Documented diagnosed blackout requiring interpretation outside the blackout-only scope | Insufficient information; `missing_information` under the original outcome-based routing policy | Bind referral evidence and rank the emitted triggered-rule request |

The last example may have an empty `missing_information` collection: its insufficiency concerns assessment scope rather than an absent blackout field. The retained legacy route name is not itself a missing-field claim. Existing referral sources do not constitute a complete cross-disease knowledge graph.

Request types retain their original meanings: a triggered rule emits `triggered_rule_evidence`; an unresolved rule emits `missing_information_guidance`. Both types rank in a non-fast case when a ranking backend is configured. `has_red_flag` is based on triggered Red Flag outcomes, not on missing information alone.

Implementation: `src/occupational_fitness_rag/rules/engine.py` preserves routing; `red_flag.py` converts the internal result; `retrieval/workflow.py` binds and ranks sources. `tests/test_red_flag.py` and `tests/test_framework_preservation.py` protect these boundaries.

See [framework preservation](../framework_preservation.md) for the fixed sequence and [contracts](../contracts.md) for API schemas.
