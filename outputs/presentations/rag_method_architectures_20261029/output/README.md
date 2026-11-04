# RAG architecture and logic diagrams

The diagrams use the supplied reference PDF's fourth-page style only. All
architecture content, algorithmic stages and execution boundaries come from
the inspected first-party code. The source framework's application content,
names, components and topology are not reused.

## Files

- `rag_methods_architecture_and_logic.pptx`: 12 editable slides. Text, boxes,
  arrows, support frames and computation groups are native slide objects.
- `rag_methods_architecture_and_logic.pdf`: 12-page searchable vector PDF,
  exported locally through the installed PowerPoint document API.
- `figures/`: one 1920-by-1080 PNG and one vector SVG for each main diagram.
- `source_manifest.json`: diagram-to-code map, source hashes and style reference
  identity. The source PDF is referenced for style, not copied into this pack.
- `source/`: the editable deck authoring script and local PDF export script.

## Page order

| Pages | Method | Diagrams |
|---|---|---|
| 1-2 | 3: Hybrid RRF | Architecture; logic flow |
| 3-4 | 4: Source graph-assisted retrieval | Architecture; logic flow |
| 5-6 | 7: Criterion coverage allocation V6 | Architecture; logic flow |
| 7-8 | 9: Neo4j frontier and criterion transfer | Architecture; logic flow |
| 9-10 | 10: PageIndex and RRF predicate navigation | Architecture; logic flow |
| 11 | Shared current refinement | Protected evidence allocation and packet replay |
| 12 | Implementation map | Python files and principal functions |

The first ten slides can be used directly as the five-method figure set.
The final two slides are supplementary explanations.

## Reading the figures

Dark navy denotes input or original-evidence output. Cyan/blue denotes retrieval
or planning. Teal groups the method's processing stages. Orange emphasizes
fusion, criterion selection or ranking. Thin blue support frames, light grey
data blocks and thick pale grey arrows follow the supplied visual reference.
Calibri bold is used for the main labels; the background and page ratio match
the reference.

The preserved method core and the latest experimental refinement are shown
separately. Methods 9 and 10 originally executed real native retrieval/navigation;
the latest refinement replays their frozen real candidate inventories. It does
not make new native graph/tree calls. The diagrams do not claim that retrieval
criterion coverage proves a patient meets a licensing criterion.

Code references are embedded in each slide's English speaker notes. Within
the implementation-map slide, `retrieval/` and `evaluation/` abbreviate
`src/occupational_fitness_rag/retrieval/` and
`src/occupational_fitness_rag/evaluation/` respectively. Full relative paths
and content fingerprints are in the source manifest.

## Regeneration

Use the authoring script from the project root with the bundled presentation
runtime. Set `RAG_DIAGRAM_STYLE_PDF` to the supplied PDF path and `FINALIZE=1`
to validate a PPTX. `RAG_DIAGRAM_FINAL_PATH` can name a new output for a revision;
the validator intentionally rejects overwriting an existing validated export.
`PROJECT_ROOT`, `CODEX_PRIMARY_RUNTIME` and `PRESENTATIONS_SKILL_DIR` can override
the local paths. The source script does not change any RAG implementation,
workflow setting, rulebook or experiment result.

Run `source/export_pdf.ps1` from the project root to export the validated deck
through the installed PowerPoint API, opening it read-only without a document
window. Exported SVG text remains font-dependent; use the PDF for embedded-font
sharing and the native PPTX for individual component edits.
