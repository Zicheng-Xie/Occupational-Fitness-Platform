# Indicator exchange and local assessment workspace

Run `scripts/start_workspace.ps1` and open `http://127.0.0.1:8000`. Ollama must be running with `llama3:8b` and `nomic-embed-text`. Use `scripts/start_workspace.ps1 -Offline` for the UI, rules and report generation without model services. Offline retrieval uses lexical cosine, not semantic embeddings.

The browser accepts UTF-8 `.txt`/`.md` and text-bearing `.pdf` files (8 MB limit), or pasted English notes (100,000 characters). Select the modules to assess. The case reference names the saved input; uploaded file names never become server paths. Scanned pages require OCR first. Model context limits can cause an audited deterministic fallback on long records.

Jobs run one at a time with actual pipeline stage updates. Verified HTML reports link to downloadable JSON, Markdown and the original input. Saved reports survive restart; in-memory job status does not. The list shows the 200 most recent runs in the configured output directory. Fixed demonstration reports remain in `outputs/index.html`. This is a single-user loopback workspace; external hosting and multi-user authentication are not implemented.

## HTTP contracts

| Endpoint | Input | Output |
| --- | --- | --- |
| POST `/assess` | Existing `case_id`, `text` JSON | Existing synchronous assessment JSON |
| POST `/assessments/text` | `case_id`, `text`, `modules` JSON | HTTP 202 job |
| POST `/assessments/file?case_id=...&filename=...&modules=hearing,vision` | Raw file bytes as `application/octet-stream` | HTTP 202 job |
| GET `/assessments/jobs/{job_id}` | Job ID | Real stage, completion link or error category |
| GET `/assessments` | None | Saved report records |
| POST `/rag/retrieve` | Existing `rule_result` | Rule-bound required evidence |
| POST `/rag/indicators` | `schemas/indicator_request.schema.json` | Category-scoped candidates and separate related references |

Local API documentation is available at `/docs`, with the machine-readable specification at `/openapi.json`. File submission uses raw bytes, not multipart. Browser requests must use the same origin.

## Team agreement

Upstream extraction supplies `module`, `source_document`, `source_text` and zero-based Unicode character offsets (`start` inclusive, `end` exclusive). The selected passage must contain 1 to 2,000 characters. Only this passage enters the query. Preserve negations, units and qualifiers. JavaScript producers must convert UTF-16 positions to Unicode code-point offsets for non-BMP characters. The response echoes the offsets and original-text SHA-256; the caller remains responsible for the source and category assignment.

Modules are `hypertension`, `vision`, `hearing`, `blackout` and `diabetes`. The broader rule category `cardiovascular` corresponds to the hypertension pilot module. Do not infer a cause merely from a blackout. Submit separately classified passages when multiple modules are documented.

`schemas/field_dictionary.json` defines field types, units and allowed values. `schemas/team_field_contract.json` adds owning rules, modules, query keys and source IDs. Both are generated from `configs/rules/austroads_commercial_v1.yaml`; edit the rulebook, rebuild knowledge, then export schemas. Extraction-only fields can have empty ownership arrays.

Present facts require a value and source evidence. Unknown, conflicting and unconfirmed facts carry no authoritative value. Missing statements are not negative statements. `source_id` identifies a guideline unit, `chunk_id` its indexed representation, `rule_id` executable logic, and `rag_query_key` a rule-specific retrieval context. Software 0.7.1 uses WorkflowRuleResult 1.3.0 and RAGInput 1.1.0 (also accepts legacy 1.0.0 requests). Supporting assessment artifacts remain at 1.2.0; independent indicator contracts remain at 1.0.0.

## Evidence boundaries

The rule workflow keeps every required source regardless of ranked Top K. Its query uses the current rule's observed facts and quotations. Missing facts become information requirements, never invented observations.

Indicator discovery filters by module, commercial context, guideline version and index fingerprint. It receives no expected source IDs. Default chunks retain complete anchored units. Explicit catalogue cross-references are returned separately and do not consume ranked Top K. These references are not a complete disease graph. `candidates_found` means retrieval produced candidates; no assessment outcome is returned. Review relevance before any downstream decision use.
