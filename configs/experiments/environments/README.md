# Native retrieval runtime snapshots

These installed-distribution snapshots describe the separately executed native
retrieval experiments on Windows. They are not the main project's dependency
requirements and do not contain model weights, database files or credentials.

| Snapshot | Interpreter | Role |
| --- | --- | --- |
| `native_extensions_py312.txt` | Python 3.12.14 | Docling, Neo4j SDK, PageIndex and CPU-capable framework dependencies |
| `flag_cuda_py312.txt` | Python 3.12.14 | Native FlagEmbedding cross-encoder scoring with CUDA |

The CUDA environment used PyTorch `2.14.1+cu130`, FP16 and an RTX 3070 Laptop
GPU. The common environment used PyTorch `2.14.1+cpu`. Distribution names and
versions were read from the installed environments using Python metadata.
These files are inventory snapshots, not complete wheel-hash locks or claims
of cross-platform reproducibility. The actual framework versions, model
checkpoint revision, checkpoint file hashes and individual source fingerprints
remain pinned in the corresponding experiment manifests and the reviewed
`extension_sources_v1.json` specification.

The environments remain under ignored `.runtime/` directories. The native
Neo4j server ran separately with Java 25.0.4; its SDK dependency inventory
does not include that server binary. PageIndex navigation used the pinned local
Qwen model; no remote clinical-data upload was performed.
