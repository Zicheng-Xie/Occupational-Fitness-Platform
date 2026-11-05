"""Composition root and auditable artifact lifecycle for the five-module workflow."""

from __future__ import annotations

import importlib.metadata
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

from occupational_fitness_rag.case_intake.model_intake import model_intake, pdf_ranges
from occupational_fitness_rag.case_intake.semantic_review import semantic_review
from occupational_fitness_rag.case_intake.traceable import (
    extract_traceable_file,
    extract_traceable_text,
)
from occupational_fitness_rag.indexing.memory_store import InMemoryVectorStore
from occupational_fitness_rag.ingestion.source_catalogue import SourceCatalogue, build_catalogue
from occupational_fitness_rag.llm import OllamaClient
from occupational_fitness_rag.pipeline.austroads_rag import AustroadsRAGPipeline
from occupational_fitness_rag.pipeline.config import load_workflow_config
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json
from occupational_fitness_rag.red_flag import RedFlagEvaluator
from occupational_fitness_rag.reporting.builder import (
    build_review_note,
    render_reports,
    validate_report_inputs,
)
from occupational_fitness_rag.retrieval.engine import RetrievalEngine
from occupational_fitness_rag.retrieval.indicators import IndicatorRetriever
from occupational_fitness_rag.retrieval.workflow import (
    WorkflowRetriever,
    catalogue_chunks,
)
from occupational_fitness_rag.rules.engine import RuleBook
from occupational_fitness_rag.schemas.red_flag_result import RAGInput, WorkflowRuleResult
from occupational_fitness_rag.schemas.workflow import (
    ClinicalCase,
    ClinicianFormAdvice,
    LocalModelJudgment,
    Outcome,
    WorkflowEvidencePack,
    WorkflowRoute,
)
from occupational_fitness_rag.settings import RetrievalSettings, load_settings


class OccupationalFitnessWorkflow:
    def __init__(self, config_path="configs/workflow.yaml", *, build_missing=True):
        self.config, self.root = load_workflow_config(config_path)
        self.book = RuleBook(self.root / self.config.rules)
        self.red_flag = RedFlagEvaluator(self.book)
        target = self.root / self.config.catalogue
        if not target.exists() and build_missing:
            build_catalogue(self.root, self.root / self.config.anchors, target)
        self.catalogue = SourceCatalogue(self.root, target)
        if self.catalogue.ruleset_sha256 != self.book.sha256:
            raise ValueError("Rules changed; rebuild the structured knowledge catalogue")
        anchors = json.loads((self.root / self.config.anchors).read_text(encoding="utf-8"))
        if digest(anchors) != self.catalogue.anchors_sha256:
            raise ValueError(
                "Source anchor configuration changed; rebuild and verify the knowledge catalogue"
            )
        ret = self.config.retrieval
        engine = None
        if ret.mode != "exact":
            chunks = catalogue_chunks(self.book, self.catalogue)
            if ret.mode == "hybrid_local":
                store = InMemoryVectorStore(chunks)
            else:
                from occupational_fitness_rag.indexing.local_chroma import build_local_chroma

                store = build_local_chroma(self.root, ret, self.catalogue.index_sha256)
                store.add(chunks)
            engine = RetrievalEngine(
                store, RetrievalSettings(candidate_k=ret.candidate_k, top_k=ret.top_k)
            )
        original_rag = (
            AustroadsRAGPipeline(engine, load_settings(self.root / "configs/rag.yaml"))
            if engine is not None
            else None
        )
        self.retriever = WorkflowRetriever(
            self.catalogue,
            self.book,
            engine,
            ret.mode,
            ret.embedding_model,
            discovery_factory=(lambda: IndicatorRetriever(self)) if engine else None,
            original_rag=original_rag,
        )

    def assess(self, case: ClinicalCase, progress=None):
        progress = progress or (lambda stage: None)
        progress("rules")
        result = self.evaluate_red_flag(case)
        evidence = self._evidence_after_routing(result, progress)
        note = build_review_note(case, result, evidence)
        return result, evidence, note

    def from_text(self, text, case_id, modules=None):
        case, result = self.red_flag_from_text(text, case_id, modules)
        evidence = self._evidence_after_routing(result)
        note = build_review_note(case, result, evidence)
        return case, result, evidence, note

    def _evidence_after_routing(self, result: WorkflowRuleResult, progress=None):
        """Use the evidence mode chosen after deterministic clinical routing."""

        progress = progress or (lambda stage: None)
        if result.route == WorkflowRoute.FAST:
            progress("exact_source_binding")
            return self.retriever.bind_exact(result)
        if result.internal_metadata.get("evidence_mode") == "semantic_rag":
            progress("retrieval")
            return self.retriever.run(result.rag_input())
        progress("exact_source_binding")
        return self.retriever.bind_exact(result)

    def _model_judgment_payload(
        self,
        case: ClinicalCase,
        result: WorkflowRuleResult,
        evidence: WorkflowEvidencePack,
    ):
        facts = {
            name: {
                "value": fact.value,
                "patient_quotes": [span.quote for span in fact.evidence],
            }
            for name, fact in case.facts.items()
            if fact.status == "present"
            and any(
                name.startswith("cardiovascular." if module == "hypertension" else module + ".")
                for module in case.modules_requested
            )
        }
        triggered = {rule.rule_id for rule in result.triggered_rules}
        ordered_items = sorted(
            evidence.evidence_items,
            key=lambda item: (item.rule_id not in triggered, item.rule_id),
        )
        sources_by_module = {}
        for item in ordered_items:
            module = item.rule_id.split("-", 1)[0]
            sources_by_module.setdefault(module, [])
            for source_id in [citation.source_id for citation in item.citations] + [
                candidate.get("source_id")
                for candidate in item.ranked_candidates
                if candidate.get("source_id")
            ]:
                if source_id not in sources_by_module[module]:
                    sources_by_module[module].append(source_id)
        item_sources = list(sources_by_module.values())
        source_ids = []
        max_candidates = max((len(sources) for sources in item_sources), default=0)
        for rank in range(max_candidates):
            for sources in item_sources:
                if rank >= len(sources):
                    continue
                source_id = sources[rank]
                if source_id and source_id not in source_ids and source_id in self.catalogue.units:
                    source_ids.append(source_id)
                    if len(source_ids) >= self.config.retrieval.top_k:
                        break
            if len(source_ids) >= self.config.retrieval.top_k:
                break
        if not source_ids:
            source_ids = list(
                dict.fromkeys(
                    citation.source_id
                    for item in evidence.evidence_items
                    for citation in item.citations
                )
            )[: self.config.retrieval.top_k]
        guideline_evidence = []
        for source_id in source_ids:
            citation = self.catalogue.citation(source_id)
            if citation:
                guideline_evidence.append(
                    {
                        "source_id": citation.source_id,
                        "section": citation.section,
                        "pdf_page": citation.pdf_page,
                        "source_text": citation.evidence_text,
                    }
                )
        return {
            "case_id": case.case_id,
            "modules": case.modules_requested,
            "nurse_note": case.source_text[:4000],
            "verified_patient_facts": facts,
            "required_missing_fields": sorted({item.field for item in result.missing_information}),
            "guideline_evidence": guideline_evidence,
        }

    @staticmethod
    def _validate_model_judgment(judgment: LocalModelJudgment, payload: dict) -> LocalModelJudgment:
        sources = {item["source_id"] for item in payload["guideline_evidence"]}
        facts = set(payload["verified_patient_facts"]) | set(
            payload.get("required_missing_fields", [])
        )
        if set(judgment.source_ids) - sources or set(judgment.fact_fields) - facts:
            raise ValueError("Local-model judgment cites unavailable evidence or facts")
        missing_by_module = {}
        for field in payload.get("required_missing_fields", []):
            missing_by_module.setdefault(field.split(".", 1)[0], []).append(field)
        source_by_module = {
            source["source_id"].split("-")[1]: source["source_id"]
            for source in payload["guideline_evidence"]
        }
        advice_templates = {
            "cardiovascular": (
                "HTN",
                ["local_doctor_referral", "specialist_referral", "management_details"],
                "Confirm repeated or persistent blood-pressure findings and relevant treatment information before recording referral or management decisions.",
                "Review the documented persistent blood-pressure findings and treatment against the cited commercial standard before confirming referral or management decisions.",
            ),
            "vision": (
                "VIS",
                ["corrective_lenses", "specialist_referral", "management_details"],
                "Document the required visual acuity, visual-field, diplopia and monocular-vision findings before confirming corrective-lens or specialist-review requirements.",
                "Review the documented visual acuity, visual-field, diplopia and monocular-vision findings against the cited commercial standard before confirming corrective-lens or specialist-review requirements.",
            ),
            "hearing": (
                "HEAR",
                ["hearing_aid", "specialist_referral", "management_details"],
                "Confirm four-frequency audiometry and any ENT or audiologist information before deciding whether a hearing aid or specialist review is required.",
                "Review the documented clinical hearing assessment and any audiometry against the cited commercial hearing criterion before confirming whether a hearing aid or specialist review is required.",
            ),
            "blackout": (
                "BLK",
                ["assessment_opinion", "specialist_referral", "management_details"],
                "Confirm whether any blackout occurred and document its mechanism or investigation status before recording the assessment opinion; seek specialist review if it remains unexplained.",
                "Review the documented blackout history, investigation status and event-free period against the cited commercial criterion before confirming the assessment opinion and any specialist review.",
            ),
            "diabetes": (
                "DM",
                ["local_doctor_referral", "specialist_referral", "management_details"],
                "Confirm whether diabetes, including gestational diabetes, is present and document relevant treatment before deciding referral or management.",
                "Review the documented diabetes history and treatment status against the cited commercial criterion before confirming referral or management decisions.",
            ),
        }
        generated_advice = []
        verified_by_module = {}
        for field in payload["verified_patient_facts"]:
            verified_by_module.setdefault(field.split(".", 1)[0], []).append(field)
        for module in dict.fromkeys([*missing_by_module, *verified_by_module]):
            if module not in advice_templates:
                continue
            missing_fields = missing_by_module.get(module, [])
            fact_fields = missing_fields or verified_by_module.get(module, [])
            source_module, form_fields, missing_text, verified_text = advice_templates[module]
            source_id = source_by_module.get(source_module)
            if source_id and fact_fields:
                generated_advice.append(
                    ClinicianFormAdvice(
                        form_fields=form_fields,
                        advice=missing_text if missing_fields else verified_text,
                        source_ids=[source_id],
                        fact_fields=fact_fields,
                    )
                )
        form_advice = (
            generated_advice
            if missing_by_module or not judgment.form_advice
            else judgment.form_advice
        )
        judgment = judgment.model_copy(update={"form_advice": form_advice})
        if not judgment.form_advice:
            raise ValueError("Local-model judgment did not bind advice to review fields")
        judgment = judgment.model_copy(
            update={
                "form_advice": [
                    advice.model_copy(
                        update={"form_fields": list(dict.fromkeys(advice.form_fields))}
                    )
                    for advice in judgment.form_advice
                ]
            }
        )
        safe_advice = []
        for advice in judgment.form_advice:
            if set(advice.source_ids) - sources or set(advice.fact_fields) - facts:
                continue
            if not advice.fact_fields:
                continue
            module_codes = {
                "cardiovascular": "HTN",
                "vision": "VIS",
                "hearing": "HEAR",
                "blackout": "BLK",
                "diabetes": "DM",
            }
            if any(field.split(".", 1)[0] not in module_codes for field in advice.fact_fields):
                continue
            fact_modules = {
                module_codes[field.split(".", 1)[0]] for field in advice.fact_fields
            }
            source_modules = {source_id.split("-")[1] for source_id in advice.source_ids}
            if not source_modules <= fact_modules:
                continue
            allowed_fields = set().union(
                *(
                    {
                        "HTN": {
                            "assessment_opinion",
                            "local_doctor_referral",
                            "specialist_referral",
                            "other_management",
                            "management_details",
                            "review_plan",
                            "other_comments",
                        },
                        "VIS": {
                            "corrective_lenses",
                            "other_aid",
                            "specialist_referral",
                            "practical_driver_test",
                            "management_details",
                            "review_plan",
                            "other_comments",
                        },
                        "HEAR": {
                            "hearing_aid",
                            "other_aid",
                            "specialist_referral",
                            "management_details",
                            "review_plan",
                            "other_comments",
                        },
                        "BLK": {
                            "assessment_opinion",
                            "local_doctor_referral",
                            "specialist_referral",
                            "practical_driver_test",
                            "other_management",
                            "management_details",
                            "review_plan",
                            "review_interval",
                            "other_comments",
                        },
                        "DM": {
                            "local_doctor_referral",
                            "specialist_referral",
                            "drug_test",
                            "other_management",
                            "management_details",
                            "review_plan",
                            "other_comments",
                        },
                    }[module]
                    for module in fact_modules
                )
            )
            if not set(advice.form_fields) <= allowed_fields:
                continue
            safe_advice.append(advice)
        if not safe_advice:
            raise ValueError("Local-model advice was not grounded to matching fields and sources")
        judgment = judgment.model_copy(
            update={
                "form_advice": safe_advice,
                "recommended_actions": list(
                    dict.fromkeys(item.advice for item in safe_advice)
                )[:6],
            }
        )
        if (
            payload.get("required_missing_fields")
            and judgment.assessment_outcome != Outcome.INSUFFICIENT
        ):
            raise ValueError("Local-model judgment ignored required missing information")
        return judgment

    def red_flag_from_text(self, text, case_id, modules=None):
        """Build the canonical Red Flag result without invoking retrieval."""

        case = extract_traceable_text(
            text, case_id, "api_input.txt", self.book.field_specs, modules=modules
        )
        case, intake = model_intake(case, self.book.field_specs, self.config.llm)
        case = case.model_copy(update={"extraction_metadata": intake})
        case, _ = semantic_review(case, self.book.field_specs, self.config.llm)
        return case, self.evaluate_red_flag(case)

    def evaluate_red_flag(self, case: ClinicalCase):
        result = self.red_flag.evaluate(case)
        if self.config.llm.enabled and self.config.llm.route_classification_enabled:
            client = OllamaClient(self.config.llm)
            try:
                suggestion = client.classify_route(
                    case.source_text,
                    {
                        "route": result.route,
                        "assessment_outcome": result.assessment_outcome,
                        "has_red_flag": result.has_red_flag,
                        "missing_fields": sorted(
                            {item.field for item in result.missing_information}
                        ),
                        "triggered_rules": [item.rule_id for item in result.triggered_rules],
                    },
                )
            except Exception as exc:
                suggestion = {
                    "status": "unavailable",
                    "route": None,
                    "reason": "Local route model unavailable; deterministic route retained.",
                    "evidence_quotes": [],
                    "model": self.config.llm.model,
                    "error_type": type(exc).__name__,
                }
            result = self.red_flag.apply_route_suggestion(result, suggestion)
        if result.route == WorkflowRoute.FAST:
            result = result.model_copy(
                update={
                    "internal_metadata": {
                        **result.internal_metadata,
                        "evidence_mode": "exact_source",
                        "evidence_mode_decision": {
                            "status": "deterministic",
                            "mode": "exact_source",
                            "reason": "Fast-path rules bind their authoritative PDF sources without semantic retrieval.",
                            "model": None,
                        },
                    }
                }
            )
        else:
            result = self._select_evidence_mode(case, result)
        return result

    def _select_evidence_mode(
        self, case: ClinicalCase, result: WorkflowRuleResult
    ) -> WorkflowRuleResult:
        """Select exact binding or semantic RAG without changing clinical routing."""

        fallback = self._fallback_evidence_mode(result)
        decision = {
            "status": "deterministic_fallback",
            "mode": fallback,
            "reason": "Evidence mode selected from validated fact provenance and ambiguity.",
            "model": None,
        }
        if self.config.llm.enabled and self.config.llm.evidence_classification_enabled:
            client = OllamaClient(self.config.llm)
            try:
                proposed = client.classify_evidence_mode(
                    case.source_text,
                    {
                        "route": result.route,
                        "assessment_outcome": result.assessment_outcome,
                        "has_red_flag": result.has_red_flag,
                        "missing_fields": sorted(
                            {item.field for item in result.missing_information}
                        ),
                        "triggered_rules": [item.rule_id for item in result.triggered_rules],
                        "structured_fact_fields": self._structured_fact_fields(result),
                    },
                )
                if proposed.get("status") == "grounded":
                    decision = proposed
                else:
                    decision = {**proposed, "mode": fallback, "fallback_mode": fallback}
            except Exception as exc:
                decision = {
                    "status": "unavailable",
                    "mode": fallback,
                    "fallback_mode": fallback,
                    "reason": "Local evidence-mode model unavailable; deterministic fallback used.",
                    "model": self.config.llm.model,
                    "error_type": type(exc).__name__,
                }
        return result.model_copy(
            update={
                "internal_metadata": {
                    **result.internal_metadata,
                    "evidence_mode": decision["mode"],
                    "evidence_mode_decision": decision,
                }
            }
        )

    @staticmethod
    def _structured_fact_fields(result: WorkflowRuleResult) -> list[str]:
        fields = set()
        for evaluation in result.rules_evaluated:
            for name, fact in evaluation.observed_facts.items():
                if fact.status == "present" and any(
                    span.quote.lstrip().startswith(name + " =") for span in fact.evidence
                ):
                    fields.add(name)
        return sorted(fields)

    @classmethod
    def _fallback_evidence_mode(cls, result: WorkflowRuleResult) -> str:
        """Use exact sources for clear structured triggers; reserve RAG for narrative ambiguity."""

        evaluations = {item.rule_id: item for item in result.rules_evaluated}
        triggered = [
            request
            for request in result.rag_requests
            if request.request_type == "triggered_rule_evidence"
        ]
        for request in triggered:
            evaluation = evaluations.get(request.rule_id)
            substantive_ambiguity = set(request.ambiguity_reasons) - {"cross_chapter_condition"}
            if substantive_ambiguity or evaluation is None or evaluation.missing_fields:
                return "semantic_rag"
            present = [
                fact for fact in evaluation.observed_facts.values() if fact.status == "present"
            ]
            if not present or any(
                not any(" = " in span.quote for span in fact.evidence) for fact in present
            ):
                return "semantic_rag"
        if triggered:
            return "exact_source"
        return (
            "semantic_rag" if result.internal_metadata.get("narrative_context") else "exact_source"
        )

    def run_file(self, input_path, output_root=None, modules=None, progress=None):
        progress = progress or (lambda stage: None)
        progress("parsing")
        case = extract_traceable_file(input_path, self.book.field_specs, modules)
        progress("extraction")
        page_ranges = pdf_ranges(Path(input_path))
        case, intake = model_intake(case, self.book.field_specs, self.config.llm, page_ranges)
        case = case.model_copy(update={"extraction_metadata": intake})
        progress("semantic_review")
        case, review = semantic_review(case, self.book.field_specs, self.config.llm, page_ranges)
        result, evidence, note = self.assess(case, progress)
        code_files = sorted((self.root / "src/occupational_fitness_rag").rglob("*.py"))
        code_hash = digest(
            {p.relative_to(self.root).as_posix(): sha256_bytes(p.read_bytes()) for p in code_files}
        )
        run_id = (
            "run-"
            + digest(
                [
                    digest(case),
                    self.book.sha256,
                    self.catalogue.index_sha256,
                    self.config.model_dump(),
                    code_hash,
                ]
            )[:20]
        )
        output = Path(output_root) if output_root else self.root / self.config.output_directory
        output = output / case.case_id / run_id
        # A run is immutable. Repeated execution returns a verified existing bundle.
        if output.exists():
            if (output / "run_manifest.json").exists():
                self.verify_run(output)
                return output
            raise FileExistsError(f"Incomplete output directory exists: {output}")
        output.mkdir(parents=True)
        input_copy = "source_input" + Path(input_path).suffix.lower()
        (output / input_copy).write_bytes(Path(input_path).read_bytes())
        llm_status = intake["status"]
        write_json(output / "llm_extraction_audit.json", intake)
        write_json(output / "llm_semantic_review.json", review)
        client = OllamaClient(self.config.llm) if self.config.llm.enabled else None
        judgment_status = "disabled"
        if client:
            try:
                judgment_payload = self._model_judgment_payload(case, result, evidence)
                if not judgment_payload["guideline_evidence"]:
                    raise ValueError("No retrieved guideline evidence is available for judgment")
                judgment = self._validate_model_judgment(
                    client.judgment(judgment_payload), judgment_payload
                )
                note = note.model_copy(update={"llm_judgment": judgment})
                write_json(output / "llm_judgment.json", judgment)
                write_json(
                    output / "llm_judgment_audit.json",
                    {
                        "status": "completed",
                        "model": self.config.llm.model,
                        "model_digest": client.resolved_digest,
                        "input_source_ids": [
                            item["source_id"] for item in judgment_payload["guideline_evidence"]
                        ],
                        "input_fact_fields": sorted(judgment_payload["verified_patient_facts"]),
                        "authoritative_rule_result_modified": False,
                    },
                )
                judgment_status = "completed"
            except Exception as exc:
                judgment_status = "unavailable_fallback_to_rules"
                write_json(
                    output / "llm_judgment_audit.json",
                    {
                        "status": judgment_status,
                        "error_type": type(exc).__name__,
                        "reason": str(exc)[:300],
                    },
                )
        if client and self.config.llm.narrative_enabled:
            try:
                commentary = client.narrative(
                    {
                        "case_id": case.case_id,
                        "assessment_outcome": result.assessment_outcome,
                        "modules": [m.model_dump(mode="json") for m in result.modules],
                        "semantic_review": {
                            "status": review["status"],
                            "quarantined_fields": review["quarantined_fields"],
                            "manual_review_required": review["manual_review_required"],
                        },
                        "case_note": case.source_text[:4000],
                        "evidence": [
                            {
                                "source_id": c.source_id,
                                "pdf_page": c.pdf_page,
                                "quote": c.evidence_text[:600],
                            }
                            for c in list(
                                {
                                    c.source_id: c
                                    for item in evidence.evidence_items
                                    for c in item.citations
                                }.values()
                            )[:6]
                        ],
                    }
                )
                note = note.model_copy(update={"llm_commentary": commentary})
                write_json(
                    output / "llm_narrative_audit.json",
                    {
                        "status": "completed",
                        "model": self.config.llm.model,
                        "model_digest": client.resolved_digest,
                        "calls": client.calls,
                        "authoritative_facts_modified": False,
                    },
                )
                llm_status = (
                    "completed"
                    if intake["status"].startswith("completed")
                    else "narrative_completed_extraction_fallback"
                )
            except Exception as exc:
                # Record a bounded error without sending the case to another provider.
                llm_status = "unavailable_fallback_to_template"
                write_json(
                    output / "llm_status.json",
                    {"status": llm_status, "error_type": type(exc).__name__},
                )
        progress("report")
        artifacts = {
            "structured_case.json": case,
            "condition_map.json": {
                "case_id": case.case_id,
                "input_file": input_copy,
                "modules_requested": case.modules_requested,
                "categories": {
                    m: ("cardiovascular" if m == "hypertension" else m)
                    for m in case.modules_requested
                },
                "category_facts": {
                    m: {
                        key: fact.model_dump(mode="json")
                        for key, fact in case.facts.items()
                        if key.startswith("cardiovascular." if m == "hypertension" else m + ".")
                    }
                    for m in case.modules_requested
                },
            },
            "rule_result.json": result,
            "rag_input.json": result.rag_input(),
            "evidence_pack.json": evidence,
            "gp_review_note.json": note,
        }
        for name, value in artifacts.items():
            write_json(output / name, value)
        for name, text in render_reports(case, result, evidence, note, self.root, output).items():
            (output / name).write_text(text, encoding="utf-8")
        stages = [
            "case_loaded",
            "local_model_extraction_completed_or_fallback",
            "facts_validated",
            "semantic_review_" + review["status"],
            "categories_mapped",
            "rules_evaluated",
            "evidence_bound",
            "draft_rendered",
            "awaiting_clinician_review",
        ]
        audit = []
        previous = "0" * 64
        for number, stage in enumerate(stages, 1):
            record = {
                "sequence": number,
                "stage": stage,
                "case_id": case.case_id,
                "case_sha256": digest(case),
                "rule_result_sha256": digest(result),
                "evidence_pack_sha256": digest(evidence),
                "previous_event_sha256": previous,
            }
            previous = digest(record)
            audit.append({**record, "event_sha256": previous})
        (output / "audit_events.jsonl").write_text(
            "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in audit), encoding="utf-8"
        )
        write_json(
            output / "run_manifest.json",
            {
                "schema_version": "1.2.0",
                "run_id": run_id,
                "case_id": case.case_id,
                "input_file": input_copy,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "runtime": {
                    "python": platform.python_version(),
                    "pydantic": importlib.metadata.version("pydantic"),
                    "pymupdf": importlib.metadata.version("PyMuPDF"),
                },
                "config": self.config.model_dump(),
                "implementation_sha256": code_hash,
                "ruleset_sha256": self.book.sha256,
                "index_sha256": self.catalogue.index_sha256,
                "llm_status": llm_status,
                "llm_judgment_status": judgment_status,
                "semantic_review_status": review["status"],
                "files": {
                    p.name: sha256_bytes(p.read_bytes())
                    for p in sorted(output.iterdir())
                    if p.is_file()
                },
                "audit_head_sha256": previous,
                "review_status": "pending",
            },
        )
        progress("verification")
        self.verify_run(output)
        return output

    def verify_run(self, output: Path):
        output = Path(output)
        manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
        required = {
            "structured_case.json",
            "condition_map.json",
            "rule_result.json",
            "evidence_pack.json",
            "gp_review_note.json",
            "draft_report.md",
            "draft_report.html",
            "audit_events.jsonl",
        }
        if not required <= set(manifest["files"]):
            raise ValueError("Run manifest omits a required artifact")
        if (
            manifest["ruleset_sha256"] != self.book.sha256
            or manifest["index_sha256"] != self.catalogue.index_sha256
        ):
            raise ValueError("Run manifest belongs to a different ruleset or source index")
        for name, expected in manifest["files"].items():
            path = (output / name).resolve()
            if path.parent != output.resolve() or sha256_bytes(path.read_bytes()) != expected:
                raise ValueError(f"Run artifact fingerprint mismatch: {name}")
        case = ClinicalCase.model_validate_json(
            (output / "structured_case.json").read_text(encoding="utf-8")
        )
        review = case.extraction_metadata.get("semantic_review")
        if review is not None:
            if "llm_semantic_review.json" not in manifest["files"]:
                raise ValueError("Run manifest omits its semantic review audit")
            saved_review = json.loads(
                (output / "llm_semantic_review.json").read_text(encoding="utf-8")
            )
            if saved_review != review or review["output_facts_sha256"] != digest(case.facts):
                raise ValueError("Semantic review does not match the saved facts")
            if manifest.get("semantic_review_status") != review["status"]:
                raise ValueError("Semantic review status differs from the manifest")
        input_copy = manifest.get("input_file")
        if not input_copy or input_copy not in manifest["files"]:
            raise ValueError("Run manifest omits its original case input")
        if sha256_bytes((output / input_copy).read_bytes()) != case.source_sha256:
            raise ValueError("Case input differs from its recorded original source")
        result = WorkflowRuleResult.model_validate_json(
            (output / "rule_result.json").read_text(encoding="utf-8")
        )
        evidence = WorkflowEvidencePack.model_validate_json(
            (output / "evidence_pack.json").read_text(encoding="utf-8")
        )
        validate_report_inputs(case, result, evidence)
        context_version = result.internal_metadata.get("narrative_context_version", 1)
        replayed = (
            self.red_flag.evaluate(case)
            if context_version == 2
            else self.red_flag.evaluate(case, context_version=context_version)
        )
        # Historical bundles predate bounded narrative context. Reproduce their
        # original projection rather than rewriting immutable saved artifacts.
        if "narrative_context" not in result.internal_metadata:
            replayed = replayed.model_copy(
                update={
                    "internal_metadata": {
                        key: value
                        for key, value in replayed.internal_metadata.items()
                        if key not in {"narrative_context", "narrative_source_text_sha256"}
                    }
                }
            )
        suggestion = result.internal_metadata.get("llm_route")
        if suggestion is not None:
            if suggestion.get("status") == "grounded" and not (
                suggestion.get("evidence_quotes")
                and all(
                    isinstance(quote, str) and quote.strip() and quote in case.source_text
                    for quote in suggestion["evidence_quotes"]
                )
            ):
                raise ValueError("Saved route suggestion lacks source evidence")
            replayed = self.red_flag.apply_route_suggestion(replayed, suggestion)
        evidence_decision = result.internal_metadata.get("evidence_mode_decision")
        if evidence_decision is not None:
            if result.internal_metadata.get("evidence_mode") not in {
                "exact_source",
                "semantic_rag",
            }:
                raise ValueError("Saved evidence mode is invalid")
            quotes = evidence_decision.get("evidence_quotes", [])
            if evidence_decision.get("status") == "grounded" and not (
                quotes
                and all(
                    isinstance(quote, str) and quote.strip() and quote in case.source_text
                    for quote in quotes
                )
            ):
                raise ValueError("Saved evidence-mode decision lacks source evidence")
            replayed = replayed.model_copy(
                update={
                    "internal_metadata": {
                        **replayed.internal_metadata,
                        "evidence_mode": result.internal_metadata["evidence_mode"],
                        "evidence_mode_decision": evidence_decision,
                    }
                }
            )
        if digest(replayed) != digest(result):
            raise ValueError("Rules do not replay to the saved result")
        if "rag_input.json" in manifest["files"]:
            saved_input = json.loads((output / "rag_input.json").read_text(encoding="utf-8"))
            if RAGInput.model_validate(saved_input) != result.rag_input():
                raise ValueError("Saved RAG input differs from the Red Flag projection")
        self.catalogue.verify()
        for item in evidence.retrieval.get("symptom_discovery", []):
            if item["source_text_sha256"] != case.text_sha256:
                raise ValueError("Symptom retrieval input fingerprint mismatch")
            for span in item["source_passages"]:
                if case.source_text[span["start"] : span["end"]] != span["quote"]:
                    raise ValueError("Symptom retrieval source passage mismatch")
            for citation in item["citations"]:
                expected = self.catalogue.citation(
                    citation["source_id"], citation["retrieval_score"], citation["score_type"]
                ).model_dump(mode="json")
                if citation != expected:
                    raise ValueError("Symptom citation differs from the verified source catalogue")
        for item in evidence.evidence_items:
            for citation in item.citations:
                if citation != self.catalogue.citation(
                    citation.source_id, citation.retrieval_score, citation.score_type
                ):
                    raise ValueError("Saved citation differs from the verified source catalogue")
        previous = "0" * 64
        for sequence, line in enumerate(
            (output / "audit_events.jsonl").read_text(encoding="utf-8").splitlines(), 1
        ):
            event = json.loads(line)
            signature = event.pop("event_sha256")
            if (
                event["sequence"] != sequence
                or event["previous_event_sha256"] != previous
                or digest(event) != signature
            ):
                raise ValueError("Audit event chain mismatch")
            previous = signature
        if previous != manifest["audit_head_sha256"]:
            raise ValueError("Audit head mismatch")
        return {
            "status": "verified",
            "case_id": case.case_id,
            "files": len(manifest["files"]),
            "rules_replayed": True,
            "source_citations_verified": True,
        }
