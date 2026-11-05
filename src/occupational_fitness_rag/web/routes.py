"""Local-only browser routes with bounded inputs and allowlisted report access."""

import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

from occupational_fitness_rag.reporting.presentation import local_link
from occupational_fitness_rag.schemas.indicator import IndicatorRequest, Module
from occupational_fitness_rag.web.clinical_record import extract_clinical_record, extract_note

ASSETS = Path(__file__).parent / "static"
LIMIT = 8 * 1024 * 1024
CASE_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$"


class TextSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str = Field(pattern=CASE_PATTERN)
    text: str = Field(min_length=1, max_length=100000)
    modules: list[Module] = Field(min_length=1, max_length=5)


class FormSubmission(TextSubmission):
    surname: str = Field(min_length=1, max_length=100)
    given_names: str = Field(min_length=1, max_length=150)
    address: str = Field(default="", max_length=300)
    date_of_birth: str = Field(default="", max_length=30)
    phone: str = Field(default="", max_length=50)
    licence_number: str = Field(default="", max_length=80)
    licence_state: str = Field(default="", max_length=50)
    employer: str = Field(default="", max_length=150)
    employer_contact: str = Field(default="", max_length=150)
    employer_address: str = Field(default="", max_length=300)
    employer_phone: str = Field(default="", max_length=50)
    employer_email: str = Field(default="", max_length=150)
    driving_duties: str = Field(default="", max_length=500)
    history_known: bool
    licence_sighted: bool
    report_type: str = Field(pattern=r"^(interim|final)$")
    practitioner_surname: str = Field(default="", max_length=100)
    practitioner_given_names: str = Field(default="", max_length=150)
    practice_address: str = Field(default="", max_length=300)
    practitioner_phone: str = Field(default="", max_length=50)
    facsimile: str = Field(default="", max_length=50)
    assessment_date: str = Field(default="", max_length=30)
    other_comments: str = Field(default="", max_length=1000)
    assessment_opinion: str = Field(
        default="system",
        pattern=r"^(system|unconditional|conditional|temporary|permanent|blank)$",
    )
    corrective_lenses: bool = False
    hearing_aid: bool = False
    other_aid: bool = False
    local_doctor_referral: bool = False
    specialist_referral: bool = False
    drug_test: bool = False
    practical_driver_test: bool = False
    other_management: bool = False
    management_details: str = Field(default="", max_length=1000)
    review_plan: str = Field(default="schedule", pattern=r"^(schedule|frequent|not_selected)$")
    review_interval: str = Field(default="", pattern=r"^(|1 month|3 months|6 months|1 year)$")

    @model_validator(mode="after")
    def require_management_details(self):
        if any(
            (
                self.local_doctor_referral,
                self.specialist_referral,
                self.drug_test,
                self.practical_driver_test,
                self.other_management,
            )
        ) and not self.management_details.strip():
            raise ValueError("Recommended management details are required for selected actions")
        return self


class FinalizeSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assessment_opinion: str = Field(
        pattern=r"^(unconditional|conditional|temporary|permanent|blank)$"
    )
    corrective_lenses: bool
    hearing_aid: bool
    other_aid: bool
    local_doctor_referral: bool
    specialist_referral: bool
    drug_test: bool
    practical_driver_test: bool
    other_management: bool
    management_details: str = Field(default="", max_length=1000)
    review_plan: str = Field(pattern=r"^(schedule|frequent|not_selected)$")
    review_interval: str = Field(pattern=r"^(|1 month|3 months|6 months|1 year)$")
    other_comments: str = Field(max_length=1000)

    @model_validator(mode="after")
    def require_management_details(self):
        if any(
            (
                self.local_doctor_referral,
                self.specialist_referral,
                self.drug_test,
                self.practical_driver_test,
                self.other_management,
            )
        ) and not self.management_details.strip():
            raise ValueError("Recommended management details are required for selected actions")
        return self


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
        return FileResponse(ASSETS / name, headers={"Cache-Control": "no-store"})

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

    async def bounded_upload(request: Request) -> bytes:
        content = bytearray()
        async for chunk in request.stream():
            if len(content) + len(chunk) > LIMIT:
                raise HTTPException(413, "File exceeds the 8 MB limit.")
            content.extend(chunk)
        if not content:
            raise HTTPException(422, "The file is empty.")
        return bytes(content)

    @app.post("/clinical-record/extract")
    async def clinical_record(request: Request):
        content = await bounded_upload(request)
        if not content.startswith(b"%PDF-"):
            raise HTTPException(422, "Upload the AFTD Clinical Record as a PDF.")
        try:
            with TemporaryDirectory(prefix="clinical-record-") as folder:
                path = Path(folder) / "clinical-record.pdf"
                path.write_bytes(content)
                return extract_clinical_record(path)
        except (OSError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/nurse-note/extract")
    async def nurse_note(request: Request, filename: str):
        suffix = Path(filename).suffix.lower()
        if suffix not in {".txt", ".md", ".pdf"}:
            raise HTTPException(415, "Supported nurse note formats: TXT, Markdown and PDF.")
        content = await bounded_upload(request)
        if suffix == ".pdf" and not content.startswith(b"%PDF-"):
            raise HTTPException(422, "The nurse note is not a PDF document.")
        try:
            with TemporaryDirectory(prefix="nurse-note-") as folder:
                path = Path(folder) / ("nurse-note" + suffix)
                path.write_bytes(content)
                text = extract_note(path)
            if not text:
                raise ValueError("The nurse note is empty.")
            if len(text) > 90000:
                raise ValueError("The nurse note exceeds the 90,000 character limit.")
            return {"text": text, "characters": len(text)}
        except (OSError, UnicodeError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/assessments/text", status_code=202)
    def submit_text(data: TextSubmission):
        if not data.text.strip() or len(set(data.modules)) != len(data.modules):
            raise HTTPException(422, "Enter a note and select each module only once.")
        return enqueue(data.text.encode("utf-8"), data.case_id, ".txt", data.modules)

    @app.post("/assessments/form", status_code=202)
    def submit_form(data: FormSubmission):
        if not data.text.strip() or len(set(data.modules)) != len(data.modules):
            raise HTTPException(422, "Enter clinical notes and select each module only once.")
        form_data = data.model_dump(exclude={"case_id", "text", "modules"})
        return enqueue(
            data.text.encode("utf-8"), data.case_id, ".txt", data.modules, form_data
        )

    def enqueue(content, case_id, suffix, modules, form_data=None):
        try:
            return app.state.jobs.submit(content, case_id, suffix, modules, form_data)
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

    @app.post("/assessments/jobs/{job_id}/completed-form")
    def finalize_completed_form(job_id: str, decisions: FinalizeSubmission):
        record = app.state.jobs.get(job_id)
        if record is None or record.get("status") != "completed":
            raise HTTPException(409, "The assessment must complete before the form is finalised.")
        run = app.state.jobs.output_root / record["case_id"] / record["run_id"]
        data_path = run / "fitness_to_drive_form.json"
        if not data_path.is_file():
            raise HTTPException(404, "The assessment form data was not found.")
        data = json.loads(data_path.read_text(encoding="utf-8"))
        data.update(decisions.model_dump())
        filename = f"{record['case_id']}_Fitness_to_Drive_Report.pdf"
        from occupational_fitness_rag.web.fitness_form import add_completed_form_to_run

        with app.state.jobs.workflow_lock:
            add_completed_form_to_run(
                app.state.workflow.root, run, data, record["outcome"], filename
            )
        url = f"/reports/{record['case_id']}/{record['run_id']}/{filename}"
        app.state.jobs._update(job_id, completed_form_url=url)
        return {"completed_form_url": url, "filename": filename}

    @app.get("/assessments")
    def records():
        rows = []
        for path in app.state.jobs.output_root.glob("*/run-*/run_manifest.json"):
            try:
                manifest = json.loads(path.read_text(encoding="utf-8"))
                result = json.loads((path.parent / "rule_result.json").read_text(encoding="utf-8"))
                case_id, run_id = path.parent.parent.name, path.parent.name
                final_forms = sorted(
                    name
                    for name in manifest["files"]
                    if name.endswith("_Fitness_to_Drive_Report.pdf")
                )
                completed_form = (
                    final_forms[-1]
                    if final_forms
                    else (
                        "completed_fitness_to_drive_report.pdf"
                        if "completed_fitness_to_drive_report.pdf" in manifest["files"]
                        else None
                    )
                )
                if not re.fullmatch(CASE_PATTERN, case_id):
                    continue
                rows.append(
                    {
                        "case_id": case_id,
                        "run_id": run_id,
                        "created_at": manifest["created_at"],
                        "outcome": result["assessment_outcome"],
                        "report_url": f"/reports/{case_id}/{run_id}/draft_report.html",
                        "completed_form_url": (
                            f"/reports/{case_id}/{run_id}/{completed_form}"
                            if completed_form
                            else None
                        ),
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

    @app.get("/guideline/highlight/{source_id}.pdf")
    def highlighted_guideline(source_id: str):
        if not re.fullmatch(r"[A-Z0-9-]{1,80}", source_id):
            raise HTTPException(404)
        citation = app.state.workflow.catalogue.citation(source_id)
        if not citation:
            raise HTTPException(404)
        path = app.state.workflow.root / "data/knowledge/raw/ap_g56_22.pdf"
        with pymupdf.open(path) as document, pymupdf.open() as highlighted:
            highlighted.insert_pdf(
                document,
                from_page=citation.pdf_page - 1,
                to_page=citation.pdf_page - 1,
            )
            page = highlighted[0]
            annotation = page.add_rect_annot(pymupdf.Rect(citation.bbox))
            annotation.set_colors(stroke=(1, 0.72, 0), fill=(1, 0.92, 0.3))
            annotation.set_border(width=1)
            annotation.set_opacity(0.22)
            annotation.set_info(
                title="Occupational Fitness Platform",
                content=f"Highlighted source: {source_id}",
            )
            annotation.update()
            content = highlighted.tobytes(garbage=4, deflate=True)
        return Response(
            content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{source_id}-highlighted.pdf"',
                "Cache-Control": "private, max-age=3600",
            },
        )

    @app.post("/rag/indicators")
    def indicators(request: IndicatorRequest):
        from occupational_fitness_rag.retrieval.indicators import IndicatorRetriever

        with app.state.jobs.workflow_lock:
            if app.state.indicators is None:
                app.state.indicators = IndicatorRetriever(app.state.workflow)
            return app.state.indicators.retrieve(request)
