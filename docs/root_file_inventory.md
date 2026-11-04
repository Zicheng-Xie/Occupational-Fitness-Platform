# Root-file inventory and cleanup

Reviewed on 2026-11-05 against [main before cleanup](https://github.com/Zicheng-Xie/Occupational-Fitness-Platform/tree/fefea009f937376fac119f6a4311ff1c917b8f76). Scope: GitHub main only; local workspace files and other branch heads are unchanged.

| File | Decision | Reason |
|---|---|---|
| `.env.example` | Keep at root | Documents the workflow configuration environment variable; contains example settings. |
| `.gitattributes` | Keep at root | Preserves byte-level experiment and evidence formatting across Git checkouts. |
| `.gitignore` | Keep at root | Excludes local environments, caches, secrets and generated runs. |
| `AFTD2022_Clinical_Record.pdf` | Keep at root | Supplied five-page clinical assessment form; the browser's clinical-record adapter reads its completed fields. |
| `AFTD2022_Fitness_to_Drive_Report-December-2022.pdf` | Keep at root | Direct template dependency of `web/fitness_form.py::add_completed_form_to_run`; moving it requires a coordinated code change. |
| `Makefile` | Keep at root | Entry points for tests, demo, lint, knowledge rebuild and benchmarks. |
| `README.md` | Keep at root | Repository landing page, architecture, setup and navigation. |
| `THIRD_PARTY_NOTES.md` | Keep at root | Guideline and dependency attribution, licensing and adaptation notices. |
| `pyproject.toml` | Keep at root | Python package metadata, dependencies, CLI entry point and tool settings. |
| `rag_methods_architecture_and_logic.pdf` | Remove from current main | Presentation export of retrieval-method explanations; no execution/build dependency found in the inspected source/configuration/tooling/documentation files. Current architecture and method documents remain under docs. |
| `rag_methods_architecture_and_logic.pptx` | Remove from current main | Editable slide counterpart of the same explanatory material; no execution/build dependency found. |
| `report.md` | Move without content changes | Schema-consolidation implementation notes belong in [red_flag_contract.md](red_flag_contract.md), rather than the repository root. |
| `data/knowledge/raw/ap_g56_22.pdf` | Preserve in place | Actual guideline source used by `configs/source_anchors.json`; retained unchanged together with source anchors, corpus and rule configuration. |

## Evidence and validation

- Inspected all twelve top-level files shown in the cleanup request. The actual guideline PDF is separate from the two AFTD form PDFs and the RAG presentation.
- Checked 476 tracked text files under src, tests, scripts, tools, docs, configs, examples, schemas, .github, .vscode and requirements at the pinned GitHub commit. Local copies were used only when their Git blob hashes matched GitHub; all 39 differing or missing text files were read from that pinned remote commit. Root README and configuration files were inspected separately.
- The presentation filenames and old report path appear in the frozen branch-audit inventory. Those entries describe historical commits, so they are retained unchanged. No active execution dependency on the removed presentation files was found in the inspected files.
- The local PDF and PPTX inspected for classification exactly match their GitHub blob SHAs (`04f6fcffaf17d2dd75fa116f435e86ed57ea75ab`, `a3a24cd0df2ab9c7ee03f2153e2c1e39b97817f0`). They contain presentation material, not the rule-source PDF.
- The moved schema notes reuse the original blob (`81571229069f0a880bf61c909585109f2eb766cc`), preserving the contents.
- Cleanup changes only presentation placement and documentation. Source, tests, configurations, data, supplied form PDFs and saved experiment outputs retain their original Git object identities. No clinical or runtime test result is inferred from this file audit.

Removed files remain recoverable from the linked pre-cleanup commit and Git history. See [project architecture](architecture.md), [retrieval methods](retrieval_extension_routes.md), [branch guide](branches.md) and [third-party notices](../THIRD_PARTY_NOTES.md).
