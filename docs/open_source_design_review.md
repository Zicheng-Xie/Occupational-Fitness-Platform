# Open-source designs for traceable retrieval and judgment

Reviewed on **15 October 2026** using the connected GitHub service. This review inspects implementation and test files, rather than treating project descriptions or star counts as effectiveness evidence. Only public, generic queries were sent to GitHub. No patient notes, experiment records or local clinical content were sent to external services. No third-party checkout or source file was copied into this project.

## Selection and provenance

| Repository | Stars observed | License reported by GitHub | Inspected commit |
|---|---:|---|---|
| [deepset-ai/haystack](https://github.com/deepset-ai/haystack) | 26,741 | Apache-2.0 | `122a617bd661de20cbf882f00010627b0ed7278f` |
| [run-llama/llama_index](https://github.com/run-llama/llama_index) | 52,495 | MIT | `619d74664e8404612038bc15a1a40c686037277c` |
| [vibrantlabsai/ragas](https://github.com/vibrantlabsai/ragas) | 16,024 | Apache-2.0 | `298b68274234c060deacab3cf5fb52aa3a20e885` |
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | 43,267 | MIT | `e5b422455d9304e8a655c90d46133cf78ec25fa1` |

The older `explodinggradients/ragas` repository address resolved to `vibrantlabsai/ragas`. These are pinned source-review snapshots of the default branches, not dependency upgrades or a claim that these are the latest published packages. GitHub metadata reported all four repositories as public and not archived. Latest push timestamps observed were 14 October 2026 for Haystack, LlamaIndex and LangGraph, and 24 February 2026 for Ragas. Stars and activity are selection context; they do not establish retrieval quality or clinical suitability. License metadata does not replace a future dependency and distribution review if library code is adopted.

## 1. Haystack: explicit output contracts and bounded recovery

Inspected source:

- [AnswerBuilder implementation](https://github.com/deepset-ai/haystack/blob/122a617bd661de20cbf882f00010627b0ed7278f/haystack/components/builders/answer_builder.py)
- [AnswerBuilder tests](https://github.com/deepset-ai/haystack/blob/122a617bd661de20cbf882f00010627b0ed7278f/test/components/builders/test_answer_builder.py)
- [JsonSchemaValidator implementation](https://github.com/deepset-ai/haystack/blob/122a617bd661de20cbf882f00010627b0ed7278f/haystack/components/validators/json_schema.py)
- [JsonSchemaValidator tests](https://github.com/deepset-ai/haystack/blob/122a617bd661de20cbf882f00010627b0ed7278f/test/components/validators/test_json_schema.py)

`AnswerBuilder` maps generated references to supplied documents, preserves source order and adds reference metadata to document copies. Its bounds checks reject zero and out-of-range references, avoiding Python negative-index behavior. Range expansion is capped at the supplied document count. These are useful tests for any local citation adapter, even when the project uses stable source identifiers instead of numbered references.

`JsonSchemaValidator` exposes separate validated and validation-error branches. Recovery information identifies the invalid output, error path and schema path. This makes output repair a visible workflow event. Schema validity alone does not prove that a judgment follows from evidence; AnswerBuilder reference resolution also does not establish entailment.

**Project-aligned adaptation:** keep a strict first-attempt result, and evaluate a separately versioned, bounded recovery condition for missing or malformed citations. Recovery receives only the unchanged case, supplied original evidence and validation errors. Save both attempts, request fingerprints, errors and costs. Never silently insert a citation, supply the expected outcome, change evidence to make an answer pass, or rewrite the completed comparison records. A repaired answer is a distinct observation. The existing Pydantic contracts can implement this behavior without installing Haystack.

**Acceptance checks:** invalid source identifier; missing citation; duplicate references; oversized arrays; malformed JSON; recovery exhausted; valid identifiers with an unsupported explanation. The last case must remain a support-review concern despite schema success.

## 2. LlamaIndex: separate retrieval units from citation units

Inspected source:

- [CitationQueryEngine implementation](https://github.com/run-llama/llama_index/blob/619d74664e8404612038bc15a1a40c686037277c/llama-index-core/llama_index/core/query_engine/citation_query_engine.py)
- [CitationQueryEngine tests](https://github.com/run-llama/llama_index/blob/619d74664e8404612038bc15a1a40c686037277c/llama-index-core/tests/query_engine/test_citation_query_engine.py)

The engine first retrieves and post-processes nodes, then creates finer citation nodes with local source labels before synthesis. The inspected implementation deliberately removes inherited node IDs and character offsets after splitting: the original offsets no longer describe a smaller citation chunk. Tests cover unique chunk IDs, cleared offsets and preserved, independent metadata. This is directly relevant to reports that link explanations back to original PDF regions.

**Project-aligned adaptation:** retain the frozen guideline unit, canonical source identifier, PDF page and region fingerprint. Allow a judgment to identify a short quotation within a supplied unit, then resolve it deterministically against that exact original text. Store the parent source ID and matched character span separately from any display label. Reject absent quotations and retain all candidate spans when a quotation occurs more than once; require ambiguity resolution before claiming one precise location. Do not invent precise coordinates for a generated summary. Keep complete table criteria, qualifiers and footnotes together. Do not automatically replace the audited medical corpus with the framework's default sentence splitting.

**Acceptance checks:** quotation not present in the source; repeated ambiguous quotation; correct text but wrong source ID; invalid inherited offsets after a split; table qualifier omitted; source order changed. Valid quote matching proves provenance, while clinical applicability and explanatory support still require separate checks.

## 3. Ragas: evaluate claims against evidence independently

Inspected source:

- [Faithfulness metric](https://github.com/vibrantlabsai/ragas/blob/298b68274234c060deacab3cf5fb52aa3a20e885/src/ragas/metrics/collections/faithfulness/metric.py)
- [Statement and inference contracts](https://github.com/vibrantlabsai/ragas/blob/298b68274234c060deacab3cf5fb52aa3a20e885/src/ragas/metrics/collections/faithfulness/util.py)
- [Metric edge-case tests](https://github.com/vibrantlabsai/ragas/blob/298b68274234c060deacab3cf5fb52aa3a20e885/tests/e2e/metrics_migration/test_faithfulness_migration.py)

The implementation decomposes a response into atomic statements, checks those statements against retrieved context and computes the supported-statement ratio. Verdict contracts retain the statement and a reason. Missing question, response or retrieved contexts are rejected; an empty statement set yields an undefined score rather than full credit. This provides a useful design for separating a valid citation identifier from an explanation that is actually supported.

**Project-aligned adaptation:** create a separate support-review record for each material judgment claim. Record the fact references, original guideline source, exact supporting quotation, applicability conditions, support verdict and review provenance. Distinguish patient-fact claims from guideline claims and the final application of a criterion to the patient. An auxiliary local-model review may prioritize cases, but its verdict remains automated and unverified. Preserve a human-review field and do not count blank reviews as passed. Missing evidence must be a recorded unavailable/failed check, not support score 1.

**Limits:** a statement can faithfully repeat the wrong commercial/private condition, and a cautious response can be faithful yet classify fitness incorrectly. Report provenance validity, automated support, independent review and engineering reference agreement separately. A model's support judgment is not a clinician label, and using the same model for generation and review does not create an independent clinical reference.

## 4. LangGraph: durable state and explicit review boundaries

Inspected source:

- [Interrupt, command and durability contracts](https://github.com/langchain-ai/langgraph/blob/e5b422455d9304e8a655c90d46133cf78ec25fa1/libs/langgraph/langgraph/types.py)
- [Checkpoint saver contract](https://github.com/langchain-ai/langgraph/blob/e5b422455d9304e8a655c90d46133cf78ec25fa1/libs/checkpoint/langgraph/checkpoint/base/__init__.py)

The contracts separate persisted state, intermediate writes, task identities and resumable human input. `interrupt` requires a checkpointer and resumes from the beginning of the interrupted node, re-executing that node's logic. Consequently, wrapping an existing sequence in a graph does not by itself make model calls or file writes exactly-once operations.

**Project-aligned adaptation:** preserve the established notes-to-extraction-to-validation-to-semantic-review-to-retrieval-to-draft-to-human-review sequence. Improve checkpoint identities and atomic completion records around existing stages, rather than replacing the framework immediately. Each result should be bound to case, corpus, configuration, model, prompt and attempt identity. Resume must refuse incompatible identities and avoid duplicate side effects. A future workflow migration should have a demonstrated operational need and an equivalence test against the existing stages.

**Acceptance checks:** process interruption during append; duplicate condition; stale configuration; partial JSON record; resumed model call with a changed corpus; a review pause that must not imply clinical approval. Existing local checkpoint code already covers part of this design; the inspection supports hardening it, not claiming LangGraph has been integrated.

## Recommended implementation order

1. Add an evidence-linked judgment contract and explicit citation/quotation validation in an isolated experiment. Keep restrictive conclusions distinct from missing-information flags so that one unresolved module does not erase an already supported restriction in another module.
2. Evaluate bounded contract recovery as a new condition, preserving every first-attempt failure and reporting both raw and recovered results.
3. Extend the support-review queue to material claims and applicability conditions. Use automated checks to triage; retain independent human review status.
4. Strengthen checkpoint and duplicate protections where a concrete gap is demonstrated. Defer a full orchestration-framework replacement.

These recommendations are design inferences from inspected source and this project's traceability requirements. They are not measured improvements. Any implemented variant must use a new experiment identity, preserve the completed baseline and be compared on unchanged cases, facts, evidence budgets and model settings. Retain the current production workflow until engineering acceptance and the required clinical review are complete.

## 5. Docling: preserve layout provenance before expanding the corpus

Reviewed through GitHub on **15 October 2026**: [docling-project/docling](https://github.com/docling-project/docling), **68,879 stars**, MIT, public and not archived; latest observed push **14 October 2026**. Inspected commit: `6fadbae317b09c4dd4051c0f1fc1746c6baf04bc`.

Inspected implementation and tests:

- [Reading-order and document assembly](https://github.com/docling-project/docling/blob/6fadbae317b09c4dd4051c0f1fc1746c6baf04bc/docling/models/stages/reading_order/readingorder_model.py)
- [Table structure and coordinate conversion](https://github.com/docling-project/docling/blob/6fadbae317b09c4dd4051c0f1fc1746c6baf04bc/docling/models/stages/table_structure/table_structure_model.py)
- [Table orientation and nested-picture tests](https://github.com/docling-project/docling/blob/6fadbae317b09c4dd4051c0f1fc1746c6baf04bc/tests/test_readingorder_table_orientation.py)
- [Hyphenated-merge tests](https://github.com/docling-project/docling/blob/6fadbae317b09c4dd4051c0f1fc1746c6baf04bc/tests/test_readingorder_hyphenated_merges.py)

The assembly code binds the document to its binary hash and items to page, bounding box and character span. It explicitly orders siblings within containers and associates captions and footnotes with tables and pictures. Table cells retain row/column offsets and orientation. Coordinate conversion records the origin; picture/table spans can be `(0, 0)`, so an image region must not masquerade as a verified text quotation. These are concrete provenance designs, not evidence of extraction accuracy on this guideline.

**Useful for the next corpus version:** store item/parent IDs, reading-order positions, coordinate origin and page size, table row/column spans, caption/footnote links, raw versus normalized text, and extraction-version fingerprints alongside existing source IDs. Recheck offsets after dehyphenation or merging. Verify commercial/private column assignment, complete qualifiers, rotation and the rendered PDF crop before accepting a unit. Keep unresolved figure and cross-reference links explicit; extracted picture descriptions do not establish decision-tree meaning or resolve a medical cross-reference automatically.

**Can wait:** installing Docling or rebuilding the frozen corpus. First prepare a small, separately versioned ingestion comparison on problematic table/figure pages with region-level review. Existing exclusion records remain valid until verified replacements exist; the completed judgment comparison must retain its original corpus and results. No package installation, source copying or corpus replacement was performed for this review.
