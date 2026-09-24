"""Bounded local assessment queue; completed run bundles survive server restarts."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
from uuid import uuid4


class AssessmentJobs:
    def __init__(self, workflow, output_root=None):
        self.workflow = workflow
        self.output_root = Path(output_root or workflow.root / workflow.config.output_directory)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="assessment")
        self.lock = Lock()
        self.workflow_lock = Lock()
        self.records = {}
        self.futures = {}

    def submit(self, content, case_id, suffix, modules):
        with self.lock:
            if sum(r["status"] in {"queued", "running"} for r in self.records.values()) >= 8:
                raise ValueError("The assessment queue is full. Please try again shortly.")
            # Keep status memory bounded without deleting any saved report bundles.
            if len(self.records) >= 200:
                for key in list(self.records):
                    if self.records[key]["status"] in {"completed", "failed"}:
                        self.records.pop(key)
                        self.futures.pop(key, None)
                        break
            job_id = uuid4().hex
            self.records[job_id] = {
                "job_id": job_id,
                "case_id": case_id,
                "status": "queued",
                "stage": "queued",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self.futures[job_id] = self.executor.submit(
                self._run, job_id, content, case_id, suffix, modules
            )
            return dict(self.records[job_id])

    def _update(self, job_id, **values):
        with self.lock:
            self.records[job_id].update(values)

    def get(self, job_id):
        with self.lock:
            return dict(self.records[job_id]) if job_id in self.records else None

    def _run(self, job_id, content, case_id, suffix, modules):
        try:
            self._update(job_id, status="running")
            with self.workflow_lock, TemporaryDirectory(prefix="fitness-intake-") as folder:
                path = Path(folder) / (case_id + suffix)
                path.write_bytes(content)
                run = self.workflow.run_file(
                    path,
                    self.output_root,
                    modules,
                    progress=lambda stage: self._update(job_id, stage=stage),
                )
            result = json.loads((run / "rule_result.json").read_text(encoding="utf-8"))
            manifest = json.loads((run / "run_manifest.json").read_text(encoding="utf-8"))
            self._update(
                job_id,
                status="completed",
                stage="completed",
                run_id=run.name,
                outcome=result["assessment_outcome"],
                llm_status=manifest["llm_status"],
                semantic_review_status=manifest.get("semantic_review_status", "not_recorded"),
                report_url=f"/reports/{case_id}/{run.name}/draft_report.html",
            )
        except Exception as exc:
            # Raw exceptions may contain private paths or input text; expose actionable categories.
            message = "Assessment failed. Check the input and local service configuration."
            if "OCR" in str(exc):
                message = "This PDF contains a page without extractable text. OCR and verification are required."
            elif isinstance(exc, UnicodeError):
                message = "Save the text file using UTF-8 encoding and try again."
            self._update(
                job_id,
                status="failed",
                stage="failed",
                error=message,
                error_type=type(exc).__name__,
            )

    def close(self):
        self.executor.shutdown(wait=True)
