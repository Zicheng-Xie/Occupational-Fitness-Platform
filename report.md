# WorkflowRuleResult schema consolidation

The only active rule-result contract is `WorkflowRuleResult` v1.3.0, defined in `src/occupational_fitness_rag/schemas/red_flag_result.py`.

Red Flag findings are first-class structured result fields: `has_red_flag`, `red_flags`, and `triggered_rules`. `missing_information` remains a separate collection and does not imply or automatically create a Red Flag.

The superseded `WorkflowRuleResult` v1.2.0 model and its flat top-level ruleset fields have been removed from the active code path. The rule engine now emits an unversioned internal `RuleEngineResult`, which `red_flag.py` converts to the canonical public result before RAG runs.

API/Swagger, runtime verification, rule-result schema export, demo generation, delivery building, delivery validation, report reissue, and tests all import or validate the same v1.3.0 model. RAG receives only the immutable `RAGInput` projection containing `rag_requests` and integrity identifiers.

API regression tests pin the OpenAPI component name and version, reject the removed flat ruleset fields, and verify through `/assess` that an insufficient-information result can contain `missing_information` while `has_red_flag` remains false and `red_flags` remains empty.

`AssessmentInput.modules_requested` now scopes rule and Red Flag execution before the `RAGInput` boundary. A hearing-only request therefore emits only hearing assessments, rule evaluations, missing-information records, and RAG requests. Retrieval and evidence-ranking behavior are unchanged.

`POST /red-flag/evaluate` exposes that boundary directly. It returns the structured case, canonical `WorkflowRuleResult`, and immutable `RAGInput` without invoking retrieval or producing an evidence pack or review note. The existing `POST /assess` endpoint remains the complete end-to-end workflow.
