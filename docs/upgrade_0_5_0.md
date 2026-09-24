# Version 0.5.0 meeting follow-up

This version adds a working local browser intake, independent indicator retrieval, team contracts and reproducible retrieval and model-judgment comparisons. All interface text and new documentation are English. The authoritative rulebook, guideline anchors and existing fixed demonstration bundles are preserved.

## Implemented

- Local upload and pasted-note assessment, selectable five-module scope, bounded background queue, real processing stages and verified report access.
- TXT, Markdown and text-bearing PDF intake, with explicit encoding, size, empty-input and scan rejection. PDF intake is limited to 200 pages and 100,000 extracted characters.
- Per-rule queries built from the relevant observed fields and their source quotations, with existing required evidence preserved independently of Top K.
- `/rag/indicators` for upstream-classified passages with exact text offsets, module filtering, independent candidate ranking and separate catalogue-reference expansion.
- Unit-based retrieval with module and chapter metadata; experimental section/page grouping over the same anchors.
- Seven exported schemas and a generated team field contract linking fields to rules, query keys and sources.
- A 22-query development fixture and a repeatable 3-method by 3-grouping by 4-Top-K study, plus an isolated Llama 3 8B judgment study.

## Verification on 17 September 2026

- 116 automated tests passed, including 13 new workspace, input, citation, query-boundary and experiment checks.
- All 23 existing deterministic rule regression cases passed. Rulebook and knowledge-index fingerprints remain unchanged.
- Headless browser checks completed pasted-note and file submission, opened the report, checked the guideline URL, and found no JavaScript errors or mobile viewport overflow. Desktop and mobile layouts were visually inspected.
- Offline and actual Chroma studies each produced 792 observations from 22 development queries. In the unit strategy, Chroma vector-only source Recall@3 was 1.0; hybrid Recall@3 was 0.9545. The draft labels and small anchored corpus prevent claims about general clinical accuracy.
- The isolated Llama study attempted 23 cases: 22 valid responses, one explicit context-budget skip, and 8 of 22 responses agreeing with deterministic rule outcomes (36.36%). This is an experimental agreement measure, not a clinical accuracy estimate. Explanation correctness still requires human review.
- A live SYN-M2-009 hearing assessment completed local Llama extraction and commentary, Chroma retrieval, draft generation and source verification; its result remained insufficient information.

Machine-readable results: `outputs/evaluation/indicator_retrieval_offline.json`, `indicator_retrieval_chroma.json`, `model_judgment.json` and `upgrade_workflow_regression.json`.

## Remaining work

Independent clinical review of labels and explanations, a frozen holdout set, additional source coverage for diagnosed blackout referrals, and OCR integration remain open. GraphRAG and learned reranking are future measured comparisons. Existing catalogue cross-references are not a complete cross-disease graph. The browser workspace is for local single-user use; external hosting, authentication and clinician electronic sign-off are not included.

## Start and inspect

Run `scripts/start_workspace.ps1` and open `http://127.0.0.1:8000`. Use `-Offline` if local model services are unavailable. The local API page at `/docs` links to the field dictionary and integration schemas. See `docs/team_integration.md` and `docs/retrieval_experiments.md` for contracts and experiment commands.
