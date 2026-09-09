# Operations runbook

Run commands from the project root. Case data is sent only to the configured loopback Ollama service.

```powershell
ollama list
.\.venv\Scripts\fitness-rag.exe build-knowledge
.\.venv\Scripts\fitness-rag.exe export-schemas
.\.venv\Scripts\fitness-rag.exe assess --input data/cases/nurse_notes/SYN-M2-009.txt
.\.venv\Scripts\fitness-rag.exe demo
.\.venv\Scripts\python.exe scripts/build_delivery.py
.\.venv\Scripts\python.exe scripts/validate_delivery.py
.\.venv\Scripts\python.exe scripts/check_english.py
```

The default configuration uses `llama3:8b` for extraction and separate English commentary, with `nomic-embed-text` for Chroma guideline vectors. Only case evidence can establish patient facts. Unsupported proposals are withheld; supported deterministic extraction fills gaps in model coverage.

`workflow.offline.yaml` disables model and vector services. `workflow.chroma.yaml` isolates retrieval; its alternative Qwen setting is disabled by default. Use `llm.model_digest` to pin model weights. A mismatch, timeout, malformed response or unsupported quotation cannot silently become a successful fact.

```powershell
.\.venv\Scripts\fitness-rag.exe benchmark --config configs/workflow.offline.yaml
.\.venv\Scripts\fitness-rag.exe benchmark --config configs/workflow.chroma.yaml --output outputs/evaluation/chroma_metrics.json
.\.venv\Scripts\python.exe -m ruff check src tests scripts examples
.\.venv\Scripts\python.exe -m ruff format --check src tests scripts examples
.\.venv\Scripts\fitness-rag.exe verify-run --run-dir outputs/runs/CASE-ID/RUN-ID
```

To avoid a shared Windows temporary-directory ownership conflict, create a fresh test location:

```powershell
New-Item -ItemType Directory -Path tmp -Force | Out-Null
$testRun = Join-Path (Get-Location) ('tmp/test-' + [Guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe -m pytest -q --basetemp $testRun
```

Extraction runs before rules. Model output and runtime metadata can produce a new immutable run on repeated execution. Rule regression scores measure deterministic behaviour and evidence binding, not model extraction accuracy.

## Local API

```powershell
.\.venv\Scripts\python.exe -m uvicorn occupational_fitness_rag.api:app --host 127.0.0.1 --port 8000
```

`GET /health` reports source identity. `POST /assess` accepts `case_id` and `text`, then runs configured extraction and assessment. `POST /rag/retrieve` processes rule evidence requests. Select a configuration through `FITNESS_WORKFLOW_CONFIG`. The CLI persists HTML reports and model commentary; the API returns structured assessment and review data.

The field dictionary is in `schemas/field_dictionary.json`. Explicitly reviewed additions can use one `field = JSON` entry per line. Missing history remains unknown. Text-free scanned PDFs require an OCR integration.

Documentation and generated interface text are English. Case and guideline quotations remain exact source evidence. Current supplied inputs are English; a future non-English intake requires an explicit translation design rather than silent changes to source evidence.

Interface references: [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs), [Ollama chat API](https://docs.ollama.com/api/chat).
