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

    def submit(self, content, case_id, suffix, modules, form_data=None):
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
                self._run, job_id, content, case_id, suffix, modules, form_data
            )
            return dict(self.records[job_id])

    def _update(self, job_id, **values):
        with self.lock:
            self.records[job_id].update(values)

    def get(self, job_id):
        with self.lock:
            return dict(self.records[job_id]) if job_id in self.records else None

    def _run(self, job_id, content, case_id, suffix, modules, form_data=None):
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
            evidence = json.loads((run / "evidence_pack.json").read_text(encoding="utf-8"))
            evidence_by_rule = {
                item["rule_id"]: item for item in evidence.get("evidence_items", [])
            }
            decision_basis = []
            unresolved = {}
            for rule in result.get("triggered_rules", []):
                item = evidence_by_rule.get(rule["rule_id"], {})
                sources = []
                for citation in item.get("citations", []):
                    pdf_page = citation.get("pdf_page")
                    sources.append(
                        {
                            "source_id": citation.get("source_id"),
                            "section": citation.get("section"),
                            "printed_page": citation.get("printed_page"),
                            "pdf_page": pdf_page,
                            "table_row": citation.get("table_row"),
                            "quote": citation.get("source_text")
                            or citation.get("evidence_text"),
                            "url": "/guideline/ap_g56_22.pdf"
                            + (f"#page={pdf_page}" if pdf_page else ""),
                        }
                    )
                decision_basis.append(
                    {
                        "rule_id": rule["rule_id"],
                        "category": rule.get("category", "clinical").title(),
                        "subcondition": rule.get("subcondition", "Assessment criterion"),
                        "outcome": rule.get("assessment_outcome"),
                        "reason": rule.get("reason", "The documented facts triggered this rule."),
                        "case_quotes": rule.get("source_evidence", []),
                        "guideline_sources": sources,
                    }
                )
            seen = set()
            for item in result.get("missing_information", []):
                quote = next(iter(item.get("source_evidence", [])), "")
                key = (item.get("field"), quote)
                if key in seen:
                    continue
                seen.add(key)
                category = item.get("category", "clinical").title()
                rule_evidence = evidence_by_rule.get(item.get("required_by_rule_id"), {})
                group = unresolved.setdefault(
                    category, {"fields": [], "guideline_sources": {}}
                )
                group["fields"].append(item.get("field", "unknown field"))
                for citation in rule_evidence.get("citations", []):
                    pdf_page = citation.get("pdf_page")
                    group["guideline_sources"][citation["source_id"]] = {
                        "source_id": citation["source_id"],
                        "section": citation.get("section"),
                        "printed_page": citation.get("printed_page"),
                        "pdf_page": pdf_page,
                        "quote": citation.get("source_text")
                        or citation.get("evidence_text"),
                        "url": "/guideline/ap_g56_22.pdf"
                        + (f"#page={pdf_page}" if pdf_page else ""),
                    }
            missing_summary = [
                {
                    "category": category,
                    "fields": sorted(set(group["fields"])),
                    "guideline_sources": list(group["guideline_sources"].values()),
                }
                for category, group in sorted(unresolved.items())
            ]
            completed_form = None
            if form_data:
                from occupational_fitness_rag.web.fitness_form import add_completed_form_to_run

                completed_form = add_completed_form_to_run(
                    self.workflow.root, run, form_data, result["assessment_outcome"]
                )
            manifest = json.loads((run / "run_manifest.json").read_text(encoding="utf-8"))
            outcome = result["assessment_outcome"]
            form_suggestions = {
                "assessment_opinion": {
                    "meets_unconditional_standard": "unconditional",
                    "may_meet_conditional_standard": "conditional",
                    "temporarily_unfit": "temporary",
                    "does_not_meet_standard": "permanent",
                    "insufficient_information": "blank",
                }[outcome],
                "local_doctor_referral": outcome == "insufficient_information",
                "review_plan": (
                    "frequent"
                    if outcome
                    in {
                        "may_meet_conditional_standard",
                        "temporarily_unfit",
                        "insufficient_information",
                    }
                    else "schedule"
                ),
                "other_comments": (
                    "Further clinical information is required before a final fitness opinion can be made."
                    if outcome == "insufficient_information"
                    else ""
                ),
            }
            self._update(
                job_id,
                status="completed",
                stage="completed",
                run_id=run.name,
                outcome=outcome,
                route=result["route"],
                form_suggestions=form_suggestions,
                llm_status=manifest["llm_status"],
                semantic_review_status=manifest.get("semantic_review_status", "not_recorded"),
                decision_basis=decision_basis,
                missing_summary=missing_summary,
                source_url=f"/reports/{case_id}/{run.name}/{manifest['input_file']}",
                source_is_pdf=manifest["input_file"].lower().endswith(".pdf"),
                report_url=f"/reports/{case_id}/{run.name}/draft_report.html",
                completed_form_url=(
                    f"/reports/{case_id}/{run.name}/{completed_form}" if completed_form else None
                ),
                artifact_urls={
                    Path(name).stem: f"/reports/{case_id}/{run.name}/{name}"
                    for name in manifest["files"]
                },
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
