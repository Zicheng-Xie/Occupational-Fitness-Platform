"""Local-only browser routes with bounded inputs and allowlisted report access."""

import json
import re
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from occupational_fitness_rag.reporting.presentation import local_link
from occupational_fitness_rag.schemas.indicator import IndicatorRequest, Module

ASSETS = Path(__file__).parent / "static"
LIMIT = 8 * 1024 * 1024
CASE_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$"


class TextSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str = Field(pattern=CASE_PATTERN)
    text: str = Field(min_length=1, max_length=100000)
    modules: list[Module] = Field(min_length=1, max_length=5)


def attach_routes(app):
    @app.middleware("http")
    async def local_browser_boundary(request: Request, call_next):
        host = (request.url.hostname or "").lower()
        # testserver is Starlette's in-process test host. Bind the real server to loopback.
        if host not in {"localhost", "127.0.0.1", "::1", "testserver"}:
            return JSONResponse({"detail": "Use the local workspace address."}, status_code=400)
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse(
                {"detail": "Cross-origin requests are not permitted."}, status_code=403
            )
        if request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse(
                {"detail": "Cross-site requests are not permitted."}, status_code=403
            )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        return response

    @app.get("/", response_class=HTMLResponse)
    def workspace():
        return HTMLResponse((ASSETS / "index.html").read_text(encoding="utf-8"))

    @app.get("/docs", response_class=HTMLResponse)
    def api_docs():
        return HTMLResponse((ASSETS / "api.html").read_text(encoding="utf-8"))

    @app.get("/contracts/{name}")
    def contract(name: str):
        if name not in {
            "indicator_request.schema.json",
            "indicator_evidence.schema.json",
            "semantic_review_response.schema.json",
            "field_dictionary.json",
            "team_field_contract.json",
            "structured_case.schema.json",
            "rule_result.schema.json",
            "rag_input.schema.json",
            "evidence_pack.schema.json",
        }:
            raise HTTPException(404)
        path = app.state.workflow.root / "schemas" / name
        if not path.is_file():
            raise HTTPException(404, "Run fitness-rag export-schemas first.")
        return FileResponse(path, media_type="application/json")

    @app.get("/assets/{name}")
    def asset(name: str):
        if name not in {"workspace.css", "workspace.js"}:
            raise HTTPException(404)
        return FileResponse(ASSETS / name)

    @app.get("/workspace/config")
    def workspace_config():
        config = app.state.workflow.config
        return {
            "model": config.llm.model,
            "model_enabled": config.llm.enabled,
            "semantic_review_enabled": config.llm.enabled and config.llm.semantic_review_enabled,
            "retrieval": config.retrieval.mode,
            "max_upload_bytes": LIMIT,
        }

    @app.post("/assessments/text", status_code=202)
    def submit_text(data: TextSubmission):
        if not data.text.strip() or len(set(data.modules)) != len(data.modules):
            raise HTTPException(422, "Enter a note and select each module only once.")
        return enqueue(data.text.encode("utf-8"), data.case_id, ".txt", data.modules)

    def enqueue(content, case_id, suffix, modules):
        try:
            return app.state.jobs.submit(content, case_id, suffix, modules)
        except ValueError as exc:
            raise HTTPException(429, str(exc)) from exc

    @app.post("/assessments/file", status_code=202)
    async def submit_file(request: Request, case_id: str, filename: str, modules: str):
        selected = modules.split(",")
        # Reuse the same module and case-ID validation as text intake.
        try:
            data = TextSubmission(case_id=case_id, text="file", modules=selected)
        except ValueError as exc:
            raise HTTPException(422, "Invalid case ID or assessment modules.") from exc
        if len(set(selected)) != len(selected):
            raise HTTPException(422, "Duplicate assessment module.")
        suffix = Path(filename).suffix.lower()
        if suffix not in {".txt", ".md", ".pdf"}:
            raise HTTPException(415, "Supported formats: UTF-8 TXT, Markdown and text-bearing PDF.")
        content = bytearray()
        async for chunk in request.stream():
            if len(content) + len(chunk) > LIMIT:
                raise HTTPException(413, "File exceeds the 8 MB limit.")
            content.extend(chunk)
        if not content:
            raise HTTPException(422, "The file is empty.")
        if suffix == ".pdf":
            if not content.startswith(b"%PDF-"):
                raise HTTPException(422, "The file is not a PDF document.")
        else:
            try:
                text = content.decode("utf-8-sig")
            except UnicodeError as exc:
                raise HTTPException(422, "Text files must use UTF-8 encoding.") from exc
            if not text.strip() or len(text) > 100000:
                raise HTTPException(422, "Text must contain 1 to 100,000 characters.")
        return enqueue(bytes(content), data.case_id, suffix, selected)

    @app.get("/assessments/jobs/{job_id}")
    def job(job_id: str):
        record = app.state.jobs.get(job_id)
        if record is None:
            raise HTTPException(404, "Job not found. Saved reports remain in Assessment records.")
        return record

    @app.get("/assessments")
    def records():
        rows = []
        for path in app.state.jobs.output_root.glob("*/run-*/run_manifest.json"):
            try:
                manifest = json.loads(path.read_text(encoding="utf-8"))
                result = json.loads((path.parent / "rule_result.json").read_text(encoding="utf-8"))
                case_id, run_id = path.parent.parent.name, path.parent.name
                if not re.fullmatch(CASE_PATTERN, case_id):
                    continue
                rows.append(
                    {
                        "case_id": case_id,
                        "run_id": run_id,
                        "created_at": manifest["created_at"],
                        "outcome": result["assessment_outcome"],
                        "report_url": f"/reports/{case_id}/{run_id}/draft_report.html",
                    }
                )
            except (OSError, ValueError, KeyError):
                continue
        return sorted(rows, key=lambda r: r["created_at"], reverse=True)[:200]

    @app.get("/reports/{case_id}/{run_id}/{filename}")
    def report_file(case_id: str, run_id: str, filename: str):
        if not re.fullmatch(CASE_PATTERN, case_id) or not re.fullmatch(r"run-[a-f0-9]{20}", run_id):
            raise HTTPException(404)
        root = app.state.jobs.output_root.resolve()
        run = (root / case_id / run_id).resolve()
        path = (run / filename).resolve()
        if not run.is_relative_to(root) or path.parent != run or not path.is_file():
            raise HTTPException(404)
        try:
            with app.state.jobs.workflow_lock:
                from occupational_fitness_rag.reporting.archive import verify_saved_report

                verification = verify_saved_report(app.state.workflow, run)
            manifest = json.loads((run / "run_manifest.json").read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            raise HTTPException(409, "Report verification failed.") from exc
        if filename not in manifest["files"] and filename != "run_manifest.json":
            raise HTTPException(404)
        if filename == "draft_report.html":
            text = path.read_text(encoding="utf-8")
            if verification["status"] == "historical_verified":
                notice = (
                    '<aside role="status" class="archive-notice">Historical assessment: '
                    "file integrity and retained source citations verified. This report has "
                    "not been replayed against the current ruleset. Submit the original input "
                    "again to create a current assessment.</aside>"
                )
                text = re.sub(r"(<body\b[^>]*>)", lambda match: match[0] + notice, text, count=1)
                text = text.replace(
                    "</head>",
                    "<style>.archive-notice{margin:16px;padding:16px 20px;"
                    "border:1px solid #d5bd77;border-radius:8px;background:#fff9e8;"
                    "color:#514323;font:14px/1.6 system-ui,sans-serif}</style></head>",
                )
            relative = local_link(app.state.workflow.root, run, "data/knowledge/raw/ap_g56_22.pdf")
            text = text.replace(relative, "/guideline/ap_g56_22.pdf")
            index = local_link(app.state.workflow.root, run, "outputs/index.html")
            text = text.replace(index, "/#records")
            return HTMLResponse(text)
        # Download text/JSON/original input instead of interpreting user content as HTML.
        return FileResponse(path, filename=filename)

    @app.get("/guideline/ap_g56_22.pdf")
    def guideline():
        return FileResponse(
            app.state.workflow.root / "data/knowledge/raw/ap_g56_22.pdf",
            media_type="application/pdf",
        )

    @app.post("/rag/indicators")
    def indicators(request: IndicatorRequest):
        from occupational_fitness_rag.retrieval.indicators import IndicatorRetriever

        with app.state.jobs.workflow_lock:
            if app.state.indicators is None:
                app.state.indicators = IndicatorRetriever(app.state.workflow)
            return app.state.indicators.retrieve(request)
