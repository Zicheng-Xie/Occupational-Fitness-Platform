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
from occupational_fitness_rag.retrieval.workflow import WorkflowRetriever, catalogue_chunks
from occupational_fitness_rag.rules.engine import RuleBook
from occupational_fitness_rag.schemas.red_flag_result import RAGInput, WorkflowRuleResult
from occupational_fitness_rag.schemas.workflow import (
    ClinicalCase,
    WorkflowEvidencePack,
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
        progress("retrieval")
        evidence = self.retriever.run(result.rag_input())
        note = build_review_note(case, result, evidence)
        return result, evidence, note

    def from_text(self, text, case_id, modules=None):
        case, result = self.red_flag_from_text(text, case_id, modules)
        evidence = self.retriever.run(result.rag_input())
        note = build_review_note(case, result, evidence)
        return case, result, evidence, note

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
        return result

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
        if self.config.llm.enabled and self.config.llm.narrative_enabled:
            client = OllamaClient(self.config.llm)
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
