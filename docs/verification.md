# Engineering verification

Software 0.4.0 / schema 1.2.0 uses the supplied AP-G56-22 guideline. Current machine-readable results are in `outputs/evaluation/`; open the [assessment records](../outputs/index.html) to inspect reports.

| Check | Scope | Record |
|---|---|---|
| Automated tests | Facts, negation, quotation context, conflicts, rules, sources, local transport, API and language policy | `pytest.xml` |
| Offline regression | 23 engineering expectations | `workflow_metrics.json` |
| Chroma and local embeddings | The same 23 expectations with actual retrieval | `chroma_metrics.json` |
| Llama 3 8B | Actual extraction and commentary, model digests, accepted/withheld fields and fallback states | `model_integration.json` |
| Run integrity | 30 reports: replayed rules, file fingerprints and original PDF citations | `run_verification.json` |
| HTML and contracts | File links, anchors, UTF-8, draft markers and four current JSON examples | `artifact_checks.json` |
| English delivery | Active text files, PDF text and interface language | `english_language_check.json` |
| Repository | File inventory, naming policy and original-source fingerprints | `repository_audit.json` |

The exchange contracts contain 33 rules and 28 knowledge units, including source wording, condition, standard, criterion type, section, printed/PDF pages, table row, coordinates and cross-references. Five JSON Schemas are reproducible from code.

Llama proposals precede rule execution and must pass source-context and field validation. Quotes that omit negation or family-history context are withheld. Single readings do not establish persistent BP; audiometry frequencies are never fabricated. Commentary remains separate from authoritative rule outcomes.

Reports use an enterprise layout with a dark navigation rail, compact tables, English labels and expandable evidence. Static link and content checks are automated. A connected browser has not been available for screenshot-level visual acceptance.

These are integration and synthetic-regression results, not clinical accuracy estimates. Rules remain pending clinical review. Deployment dependencies are listed in [deployment boundaries](deployment.md). The previous environment emitted two third-party deprecation warnings; dependency consistency passed. Remote CI has not run.

## English report reissue

The English release passed 103 automated tests. All 30 existing assessments were reissued as new report bundles: 180 input, fact, category, rule, evidence and extraction-audit files were byte-identical to their parents. Local-model call records are retained from those verified parent runs; clinical extraction was not repeated for localisation. Each manifest records its parent fingerprint, presentation code fingerprint and an additional audit event. See `outputs/evaluation/english_reissue.json`.
