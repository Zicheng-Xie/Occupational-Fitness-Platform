"""Blinded prospective labels: require independent submissions before evaluation.

The declarations below are auditable review records, not authentication of a
reviewer's identity or clinical qualifications. No model is called by this module.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import fitz
from pydantic import BaseModel, ConfigDict, Field

from occupational_fitness_rag.case_intake.traceable import valid_value
from occupational_fitness_rag.evaluation.graph_contract import file_hash, local_get
from occupational_fitness_rag.provenance import digest, write_json

MODULES = ("hypertension", "vision", "hearing", "blackout", "diabetes")
Outcome = Literal[
    "meets_unconditional_standard",
    "may_meet_conditional_standard",
    "temporarily_unfit",
    "does_not_meet_standard",
    "insufficient_information",
]


class StrictForm(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GuidelineCitation(StrictForm):
    pdf_page: int = Field(ge=1)
    section: str
    quote: str
    licence_scope: Literal["commercial", "shared"]


class Assessment(StrictForm):
    outcome: Outcome | None = None
    rationale: str | None = None
    guideline_citations: list[GuidelineCitation] = Field(default_factory=list)


class DocumentedFact(StrictForm):
    module: Literal["hypertension", "vision", "hearing", "blackout", "diabetes"]
    field: str
    value: Any
    note_quote: str


class CaseAnnotation(StrictForm):
    case_id: str
    source_note_sha256: str
    documented_facts: list[DocumentedFact] = Field(default_factory=list)
    module_assessments: dict[str, Assessment]
    overall: Assessment


class Reviewer(StrictForm):
    reviewer_id: str | None = None
    role: Literal["clinician", "domain_reviewer"] | None = None
    completed_at: datetime | None = None
    independent_of_case_authoring: bool | None = None
    independent_of_retrieval_development: bool | None = None
    did_not_view_model_outputs: bool | None = None
    did_not_view_other_reviewer_answers: bool | None = None


class ReviewSubmission(StrictForm):
    packet_identity: str
    status: Literal["draft", "submitted"] = "draft"
    reviewer: Reviewer = Field(default_factory=Reviewer)
    cases: list[CaseAnnotation]


class Adjudicator(StrictForm):
    reviewer_id: str | None = None
    role: Literal["clinician", "domain_reviewer"] | None = None
    completed_at: datetime | None = None
    independent_of_retrieval_development: bool | None = None
    did_not_view_model_outputs: bool | None = None
    checked_note_and_guideline_support: bool | None = None


class Adjudication(StrictForm):
    packet_identity: str
    status: Literal["draft", "submitted"] = "draft"
    reviewer_a_id: str | None = None
    reviewer_b_id: str | None = None
    adjudicator: Adjudicator = Field(default_factory=Adjudicator)
    cases: list[CaseAnnotation]


class SourceCheck(StrictForm):
    citation_identity: str
    pdf_page: int
    section: str
    quote: str
    licence_scope: Literal["commercial", "shared"]
    bbox: list[float] | None = None
    inspected_original_region: bool | None = None
    section_verified: bool | None = None
    commercial_or_shared_column_verified: bool | None = None
    footnotes_and_qualifications_checked: bool | None = None


class SourceVerification(StrictForm):
    packet_identity: str
    status: Literal["draft", "submitted"] = "draft"
    verifier_id: str | None = None
    role: Literal["clinician", "domain_reviewer"] | None = None
    completed_at: datetime | None = None
    independent_of_annotation_and_retrieval: bool | None = None
    did_not_view_model_outputs: bool | None = None
    citations: list[SourceCheck] = Field(default_factory=list)


def citation_identity(citation):
    return digest(citation.model_dump(mode="json"))


def source_verification_template(packet_identity, forms):
    citations = {}
    for form in forms:
        for case in form.cases:
            for assessment in [*case.module_assessments.values(), case.overall]:
                for citation in assessment.guideline_citations:
                    citations[citation_identity(citation)] = SourceCheck(
                        citation_identity=citation_identity(citation),
                        **citation.model_dump(),
                    )
    return SourceVerification(packet_identity=packet_identity, citations=list(citations.values()))


REQUIRED_CONTRACT_SOURCES = {
    "src/occupational_fitness_rag/evaluation/prospective_review.py",
    "src/occupational_fitness_rag/evaluation/graph_contract.py",
    "src/occupational_fitness_rag/case_intake/traceable.py",
    "src/occupational_fitness_rag/provenance.py",
    "schemas/field_dictionary.json",
    "tools/prepare_prospective_review_pack.py",
}


def snapshot_paths(root):
    """Conservative dependency closure, including prompts embedded in Python."""
    root = Path(root)
    paths = {p for folder in ("src", "tools") for p in (root / folder).rglob("*.py")}
    paths |= {
        p
        for folder in ("configs", "schemas")
        for p in (root / folder).rglob("*")
        if p.is_file() and p.suffix in {".json", ".yaml", ".yml", ".txt", ".md"}
    }
    paths |= {root / name for name in ("pyproject.toml", "uv.lock") if (root / name).is_file()}
    return sorted(p.relative_to(root).as_posix() for p in paths)


def _packet(directory):
    directory = Path(directory).resolve()
    inventory = verify_inventory(directory)
    packet = json.loads((directory / "manifest.json").read_bytes())
    if digest({k: v for k, v in packet.items() if k != "identity"}) != packet["identity"]:
        raise ValueError("Review packet identity differs")
    cases = packet["cases"]
    if (
        not cases
        or packet["case_count"] != len(cases)
        or len({c["case_id"] for c in cases}) != len(cases)
        or packet["requested_modules"] != list(MODULES)
    ):
        raise ValueError("Review packet case inventory or requested modules differ")
    required = {
        "manifest.json",
        "guideline.pdf",
        "field_dictionary.json",
        "implementation_snapshot.json",
        "execution_plan.json",
        "gate_source.py",
        "builder_source.py",
        "readiness.json",
        "review.schema.json",
        "source_verification.schema.json",
    }
    for case in cases:
        rel = case["note_path"]
        path = (directory / rel).resolve()
        if (
            not path.is_relative_to(directory / "notes")
            or path.name != case["case_id"] + ".txt"
            or not path.is_file()
            or file_hash(path) != case["note_sha256"]
            or path.read_bytes() != (case["nurse_note"] + "\n").encode("utf-8")
        ):
            raise ValueError("Frozen note path, text or SHA differs")
        required.add(rel)
    if not required <= set(inventory):
        raise ValueError("Required frozen packet artifacts are missing")
    if file_hash(directory / "guideline.pdf") != packet["guideline_sha256"]:
        raise ValueError("Frozen original guideline SHA differs")
    with fitz.open(directory / "guideline.pdf") as pdf:
        if len(pdf) != packet["guideline_page_count"]:
            raise ValueError("Frozen original guideline page count differs")
    specs = json.loads((directory / "field_dictionary.json").read_bytes())
    if digest(specs) != packet["field_dictionary_identity"]:
        raise ValueError("Frozen field dictionary differs")
    snapshot = json.loads((directory / "implementation_snapshot.json").read_bytes())
    plan = json.loads((directory / "execution_plan.json").read_bytes())
    if (
        digest(snapshot) != packet["development_implementation_identity"]
        or not REQUIRED_CONTRACT_SOURCES <= set(snapshot)
        or plan["source_sha256"] != snapshot
        or digest({k: v for k, v in plan.items() if k != "identity"}) != plan["identity"]
        or plan["identity"] != packet["execution_plan_identity"]
    ):
        raise ValueError("Frozen execution plan or required contract source binding differs")
    for copy, source in (
        ("gate_source.py", "src/occupational_fitness_rag/evaluation/prospective_review.py"),
        ("builder_source.py", "tools/prepare_prospective_review_pack.py"),
        ("field_dictionary.json", "schemas/field_dictionary.json"),
    ):
        if file_hash(directory / copy) != snapshot[source]:
            raise ValueError("Frozen contract source copy differs from execution snapshot")
    if plan.get("native_index_preflight_required"):
        if (
            "native_index_contract.json" not in inventory
            or digest(json.loads((directory / "native_index_contract.json").read_bytes()))
            != plan["native_index_expected_identity"]
        ):
            raise ValueError("Frozen native index/embedding contract differs")
    return packet, inventory, specs, plan


def normalized(text):
    return " ".join(text.replace("\u00ad", "").split())


def verify_inventory(directory):
    directory = Path(directory).resolve()
    inventory = json.loads((directory / "artifacts.json").read_bytes())
    if not inventory:
        raise ValueError("A frozen packet requires a nonempty artifact inventory")
    for rel, expected in inventory.items():
        path = (directory / rel).resolve()
        if not path.is_relative_to(directory) or not path.is_file() or file_hash(path) != expected:
            raise ValueError("A frozen packet artifact changed: " + rel)
    return inventory


def _require_identity(identifier, role, completed_at):
    if not identifier or identifier != identifier.strip() or role is None:
        raise ValueError("A submitted reviewer requires a nonempty stable identifier and role")
    if completed_at is None or completed_at.tzinfo is None:
        raise ValueError("A submitted review requires a timezone-aware completion time")


def _validate_cases(cases, packet, page_text, specs, expected_case_ids=None):
    expected = {
        c["case_id"]: c
        for c in packet["cases"]
        if expected_case_ids is None or c["case_id"] in expected_case_ids
    }
    if len(cases) != len(expected) or {c.case_id for c in cases} != set(expected):
        raise ValueError("Annotations must cover each frozen case exactly once")
    result = {}
    for case in cases:
        if case.source_note_sha256 != expected[case.case_id]["note_sha256"]:
            raise ValueError("Annotation binds a different source note")
        note = expected[case.case_id]["nurse_note"]
        if set(case.module_assessments) != set(MODULES):
            raise ValueError("Review all five modules; unknown information is not normal")
        for fact in case.documented_facts:
            module = fact.field.split(".")[0]
            module = "hypertension" if module == "cardiovascular" else module
            if fact.module != module or not valid_value(fact.field, fact.value, specs):
                raise ValueError("A review fact violates the frozen field dictionary/module/type")
            if (
                not fact.field.strip()
                or not fact.note_quote.strip()
                or normalized(fact.note_quote) not in normalized(note)
            ):
                raise ValueError("A documented review fact lacks an exact source-note quotation")
        for module, assessment in [*case.module_assessments.items(), ("overall", case.overall)]:
            if (
                assessment.outcome is None
                or not assessment.rationale
                or len(assessment.rationale.strip()) < 20
            ):
                raise ValueError(
                    "Each submitted assessment needs a label and substantive rationale"
                )
            if assessment.outcome != "insufficient_information":
                if not assessment.guideline_citations:
                    raise ValueError(
                        "A substantive fitness label needs original guideline citations"
                    )
                if not any(
                    module == "overall" or f.module == module for f in case.documented_facts
                ):
                    raise ValueError("A substantive module label needs documented patient facts")
            for citation in assessment.guideline_citations:
                if (
                    not citation.section.strip()
                    or citation.pdf_page not in page_text
                    or len(citation.quote.strip()) < 10
                    or normalized(citation.quote) not in normalized(page_text[citation.pdf_page])
                ):
                    raise ValueError(
                        "Guideline quotation is not present on the cited original PDF page"
                    )
        result[case.case_id] = case
    return result


def _outcomes(case):
    return {
        **{m: a.outcome for m, a in case.module_assessments.items()},
        "overall": case.overall.outcome,
    }


def _verify_sources(packet_directory, packet, forms, adjudication, verification, reviewer_ids):
    if verification.packet_identity != packet["identity"] or verification.status != "submitted":
        raise ValueError("Independent source/section/scope verification must be submitted")
    _require_identity(verification.verifier_id, verification.role, verification.completed_at)
    if (
        verification.verifier_id in reviewer_ids
        or verification.independent_of_annotation_and_retrieval is not True
        or verification.did_not_view_model_outputs is not True
    ):
        raise ValueError("A separate independent source verifier is required")
    required = source_verification_template(
        packet["identity"], [*forms, *([adjudication] if adjudication else [])]
    )
    expected = {c.citation_identity: c for c in required.citations}
    if len(verification.citations) != len(expected) or {
        c.citation_identity for c in verification.citations
    } != set(expected):
        raise ValueError("Source verification must cover each submitted citation exactly once")
    with fitz.open(packet_directory / "guideline.pdf") as pdf:
        for check in verification.citations:
            original = expected[check.citation_identity]
            if any(
                getattr(check, k) != getattr(original, k)
                for k in ("pdf_page", "section", "quote", "licence_scope")
            ):
                raise ValueError("Verified citation source/section/scope differs")
            if not all(
                getattr(check, k) is True
                for k in (
                    "inspected_original_region",
                    "section_verified",
                    "commercial_or_shared_column_verified",
                    "footnotes_and_qualifications_checked",
                )
            ):
                raise ValueError("Manual original-region/section/scope verification is incomplete")
            if (
                not check.bbox
                or len(check.bbox) != 4
                or check.pdf_page < 1
                or check.pdf_page > len(pdf)
            ):
                raise ValueError("Source verification requires a valid original page region")
            page = pdf[check.pdf_page - 1]
            rect = fitz.Rect(check.bbox)
            if (
                rect.is_empty
                or rect.is_infinite
                or not page.rect.contains(rect)
                or normalized(check.quote) not in normalized(page.get_text(clip=rect))
            ):
                raise ValueError("Verified citation quote is absent from its inspected PDF region")


def _reviewed_labels(packet_directory, packet, specs, forms, verification, adjudication=None):
    for form in [*forms, *([adjudication] if adjudication else [])]:
        if form.packet_identity != packet["identity"] or form.status != "submitted":
            raise ValueError(
                "All independent reviews and adjudication must be submitted for this packet"
            )
    for form in forms:
        r = form.reviewer
        _require_identity(r.reviewer_id, r.role, r.completed_at)
        if not all(
            getattr(r, k) is True
            for k in (
                "independent_of_case_authoring",
                "independent_of_retrieval_development",
                "did_not_view_model_outputs",
                "did_not_view_other_reviewer_answers",
            )
        ):
            raise ValueError("Independent, blinded human reviewer attestations remain incomplete")
    ids = [form.reviewer.reviewer_id for form in forms]
    if len(set(ids)) != 2:
        raise ValueError("Independent reviews require two distinct reviewer identifiers")
    with fitz.open(packet_directory / "guideline.pdf") as pdf:
        page_text = {i + 1: page.get_text() for i, page in enumerate(pdf)}
    a, b = [_validate_cases(f.cases, packet, page_text, specs) for f in forms]
    disputed_cases = {case for case in a if _outcomes(a[case]) != _outcomes(b[case])}
    final = dict(a)
    adjudicator_id = None
    if disputed_cases:
        if adjudication is None:
            raise ValueError("Disputed independent labels require adjudication before evaluation")
        r = adjudication.adjudicator
        _require_identity(r.reviewer_id, r.role, r.completed_at)
        if (
            len({*ids, r.reviewer_id}) != 3
            or [adjudication.reviewer_a_id, adjudication.reviewer_b_id] != ids
        ):
            raise ValueError(
                "A distinct adjudicator must bind both independent reviewer identifiers"
            )
        if not all(
            getattr(r, k) is True
            for k in (
                "independent_of_retrieval_development",
                "did_not_view_model_outputs",
                "checked_note_and_guideline_support",
            )
        ):
            raise ValueError("Independent source-support adjudication remains incomplete")
        final.update(_validate_cases(adjudication.cases, packet, page_text, specs, disputed_cases))
        adjudicator_id = r.reviewer_id
    elif adjudication is not None:
        raise ValueError("Agreed labels do not require adjudication; omit the unused form")
    _verify_sources(
        packet_directory,
        packet,
        forms,
        adjudication,
        verification,
        [*ids, *([adjudicator_id] if adjudicator_id else [])],
    )
    disagreements = []
    for case in a:
        av, bv, fv = [_outcomes(group[case]) for group in (a, b, final)]
        for module in [*MODULES, "overall"]:
            if av[module] == bv[module] and fv[module] != av[module]:
                raise ValueError(
                    "Adjudication changed an agreed label; resolve it in new independent submissions"
                )
            if av[module] != bv[module]:
                disagreements.append(
                    {
                        "case_id": case,
                        "module": module,
                        "reviewer_a": av[module],
                        "reviewer_b": bv[module],
                        "adjudicated": fv[module],
                    }
                )
    labels = {
        case: {
            "reference_outcome": c.overall.outcome,
            "module_outcomes": {m: x.outcome for m, x in c.module_assessments.items()},
            "rationale": c.overall.rationale,
        }
        for case, c in final.items()
    }
    return labels, disagreements, ids, adjudicator_id


def freeze_labels(
    packet_directory,
    reviewer_a_path,
    reviewer_b_path,
    output,
    adjudication_path=None,
    *,
    source_verification_path=None,
):
    """Create new frozen scoring labels; never fill templates or run a model."""
    packet_directory, output = Path(packet_directory).resolve(), Path(output).resolve()
    if output.exists() or output == packet_directory or packet_directory in output.parents:
        raise ValueError("Freeze labels in a fresh directory outside the immutable review packet")
    packet, packet_pins, specs, _ = _packet(packet_directory)
    if source_verification_path is None:
        raise ValueError(
            "Independent source/section/scope verification is required before freezing"
        )
    verification = SourceVerification.model_validate_json(
        Path(source_verification_path).read_bytes()
    )
    forms = [
        ReviewSubmission.model_validate_json(Path(p).read_bytes())
        for p in (reviewer_a_path, reviewer_b_path)
    ]
    adjudication = (
        Adjudication.model_validate_json(Path(adjudication_path).read_bytes())
        if adjudication_path
        else None
    )
    labels, disagreements, ids, adjudicator_id = _reviewed_labels(
        packet_directory, packet, specs, forms, verification, adjudication
    )
    input_pins = {
        "reviewer_a": file_hash(reviewer_a_path),
        "reviewer_b": file_hash(reviewer_b_path),
        "source_verification": file_hash(source_verification_path),
    }
    if adjudication_path:
        input_pins["adjudication"] = file_hash(adjudication_path)
    data = {
        "kind": "prospective_independent_labels",
        "packet_identity": packet["identity"],
        "packet_artifacts": packet_pins,
        "input_form_sha256": input_pins,
        "labels_sha256": digest(labels),
        "case_count": len(labels),
        "reviewer_ids": ids,
        "adjudicator_id": adjudicator_id,
        "source_verifier_id": verification.verifier_id,
        "execution_plan_identity": packet["execution_plan_identity"],
        "provenance": "declared independent human annotation; identities and qualifications require coordinator verification",
        "clinical_accuracy_established": False,
        "model_calls": 0,
        "production_change": False,
    }
    output.mkdir(parents=True)
    write_json(output / "labels.json", labels)
    write_json(output / "disagreements.json", disagreements)
    write_json(output / "manifest.json", {**data, "identity": digest(data)})
    write_json(
        output / "readiness.json",
        {
            "ready_for_prospective_evaluation": False,
            "independent_labels_frozen": True,
            "reason": "Labels are frozen; execution still requires a pinned harness, live index and runtime preflight",
            "packet_identity": packet["identity"],
            "clinical_accuracy_established": False,
        },
    )
    for name, form in [
        ("reviewer_a.json", forms[0]),
        ("reviewer_b.json", forms[1]),
        ("source_verification.json", verification),
        *([("adjudication.json", adjudication)] if adjudication else []),
    ]:
        write_json(output / name, form.model_dump(mode="json"))
    write_json(
        output / "artifacts.json", {p.name: file_hash(p) for p in output.iterdir() if p.is_file()}
    )
    return data


def prospective_inputs(
    packet_directory,
    frozen_labels_directory,
    *,
    root,
    runtime_probe=local_get,
    execution_amendment_directory=None,
    retrieval_probe=None,
):
    """The prospective harness must call this gate before test execution/scoring.

    The general product upload endpoint is unchanged; this gate controls the new
    prospective evaluation path and cannot prevent manual exploratory uploads.
    """
    packet_directory, frozen_labels_directory = (
        Path(packet_directory),
        Path(frozen_labels_directory),
    )
    packet, packet_pins, specs, execution_plan = _packet(packet_directory)
    verify_inventory(frozen_labels_directory)
    readiness = json.loads((frozen_labels_directory / "readiness.json").read_bytes())
    frozen = json.loads((frozen_labels_directory / "manifest.json").read_bytes())
    if digest({k: v for k, v in frozen.items() if k != "identity"}) != frozen["identity"]:
        raise ValueError("Frozen label manifest identity differs")
    if (
        readiness.get("independent_labels_frozen") is not True
        or readiness["packet_identity"] != packet["identity"]
    ):
        raise ValueError("Independent labels are not frozen and ready for this prospective packet")
    if (
        frozen["packet_identity"] != packet["identity"]
        or frozen["packet_artifacts"] != packet_pins
        or frozen["execution_plan_identity"] != execution_plan["identity"]
    ):
        raise ValueError("Frozen labels bind another packet or source inventory")
    labels = json.loads((frozen_labels_directory / "labels.json").read_bytes())
    if digest(labels) != frozen["labels_sha256"] or set(labels) != {
        c["case_id"] for c in packet["cases"]
    }:
        raise ValueError("Frozen scoring labels differ")
    forms = [
        ReviewSubmission.model_validate_json((frozen_labels_directory / name).read_bytes())
        for name in ("reviewer_a.json", "reviewer_b.json")
    ]
    adj_path = frozen_labels_directory / "adjudication.json"
    adjudication = (
        Adjudication.model_validate_json(adj_path.read_bytes()) if adj_path.exists() else None
    )
    verification = SourceVerification.model_validate_json(
        (frozen_labels_directory / "source_verification.json").read_bytes()
    )
    recomputed, _, ids, adjudicator_id = _reviewed_labels(
        packet_directory, packet, specs, forms, verification, adjudication
    )
    if (
        recomputed != labels
        or frozen["reviewer_ids"] != ids
        or frozen["adjudicator_id"] != adjudicator_id
        or frozen["source_verifier_id"] != verification.verifier_id
    ):
        raise ValueError("Frozen labels differ from the independently submitted review records")
    if execution_amendment_directory:
        execution_plan = _execution_amendment(
            execution_amendment_directory,
            execution_plan,
            packet,
            frozen,
        )
    _verify_execution(execution_plan, root, runtime_probe, retrieval_probe)
    return [
        {"case_id": c["case_id"], "nurse_note": c["nurse_note"], "modules": list(MODULES)}
        for c in packet["cases"]
    ], labels


def _verify_execution(plan, root, runtime_probe, retrieval_probe=None):
    root = Path(root).resolve()
    sources = plan["source_sha256"]
    if plan.get("harness_integration") != "integrated" or plan.get("harness_source") not in sources:
        raise ValueError(
            "Prospective execution is blocked: a pinned inference harness is still pending"
        )
    if snapshot_paths(root) != sorted(sources):
        raise ValueError("Execution source dependency inventory changed; preserve this packet")
    for rel, expected in {**sources, **plan["runtime_artifacts"]}.items():
        path = (root / rel).resolve()
        if not path.is_relative_to(root) or not path.is_file() or file_hash(path) != expected:
            raise ValueError("Execution source/corpus/prompt artifact drift: " + rel)
    if not plan["arms"] or not plan["expected_model_digests"]:
        raise ValueError("Execution plan requires frozen active methods and models")
    if plan.get("native_index_preflight_required"):
        if retrieval_probe is None:
            raise ValueError("Actual live native-index preflight is still pending")
        probe_source = Path(retrieval_probe.__code__.co_filename).resolve()
        if (
            probe_source != (root / plan["harness_source"]).resolve()
            or retrieval_probe(plan) != plan["native_index_expected_identity"]
        ):
            raise ValueError(
                "Native-index contents/configuration differ from the frozen retrieval contract"
            )
    version = runtime_probe(plan["endpoint"], "/api/version")["version"]
    models = {
        m["name"]: m["digest"] for m in runtime_probe(plan["endpoint"], "/api/tags")["models"]
    }
    if version != plan["expected_runtime_version"]:
        raise ValueError("Prospective runtime version drift")
    for name, expected in plan["expected_model_digests"].items():
        if models.get(name) != expected:
            raise ValueError("Prospective live model weight digest drift: " + name)


def _execution_amendment(directory, original, packet, labels):
    directory = Path(directory)
    verify_inventory(directory)
    record = json.loads((directory / "record.json").read_bytes())
    plan = json.loads((directory / "execution_plan.json").read_bytes())
    if (
        digest({k: v for k, v in record.items() if k != "identity"}) != record["identity"]
        or record["packet_identity"] != packet["identity"]
        or record["frozen_label_identity"] != labels["identity"]
        or record["baseline_execution_plan_identity"] != original["identity"]
        or record["zero_prior_prospective_inference_attested"] is not True
        or not record["coordinator_id"].strip()
        or len(record["reason"].strip()) < 20
        or record["execution_plan_identity"] != plan["identity"]
        or digest({k: v for k, v in plan.items() if k != "identity"}) != plan["identity"]
    ):
        raise ValueError("Pre-inference execution amendment binding differs")
    allowed_changes = {"identity", "source_sha256", "harness_source", "harness_integration"}
    if (
        {k: v for k, v in plan.items() if k not in allowed_changes}
        != {k: v for k, v in original.items() if k not in allowed_changes}
        or not REQUIRED_CONTRACT_SOURCES <= set(plan["source_sha256"])
        or plan.get("harness_source") not in plan["source_sha256"]
        or plan.get("harness_integration") != "integrated"
    ):
        raise ValueError(
            "Amendments may integrate a runner; methods/models/corpus/budgets cannot change"
        )
    old_sources, new_sources = original["source_sha256"], plan["source_sha256"]
    if (
        any(new_sources.get(name) != pin for name, pin in old_sources.items())
        or plan["harness_source"] in old_sources
        or set(new_sources) - set(old_sources) != {plan["harness_source"]}
        or record["new_runner_sources"]
        != {plan["harness_source"]: new_sources[plan["harness_source"]]}
    ):
        raise ValueError("Execution amendment changed existing sources or added non-runner sources")
    return plan


def freeze_execution_amendment(
    packet_directory,
    labels_directory,
    output,
    *,
    root,
    coordinator_id,
    runner_source,
    reason,
    zero_prior_inference_attested,
):
    """Keep existing annotations; explicitly pin runner integration before any call.

    This audit record does not prove the declared absence of off-platform calls.
    It permits source integration only, not label-guided retrieval/prompt tuning.
    """
    packet, _, _, original = _packet(packet_directory)
    labels_directory, root, output = Path(labels_directory), Path(root).resolve(), Path(output)
    verify_inventory(labels_directory)
    labels = json.loads((labels_directory / "manifest.json").read_bytes())
    if (
        output.exists()
        or not coordinator_id.strip()
        or len(reason.strip()) < 20
        or zero_prior_inference_attested is not True
        or labels["packet_identity"] != packet["identity"]
        or digest({k: v for k, v in labels.items() if k != "identity"}) != labels["identity"]
    ):
        raise ValueError(
            "A fresh pre-inference amendment needs frozen labels and coordinator provenance"
        )
    paths = snapshot_paths(root)
    if (
        runner_source not in paths
        or runner_source in original["source_sha256"]
        or set(paths) - set(original["source_sha256"]) != {runner_source}
    ):
        raise ValueError("The proposed runner must exist inside the pinned source inventory")
    plan_data = {k: v for k, v in original.items() if k != "identity"}
    plan_data.update(
        source_sha256={p: file_hash(root / p) for p in paths}, harness_source=runner_source
    )
    plan_data["harness_integration"] = "integrated"
    plan = {**plan_data, "identity": digest(plan_data)}
    record_data = {
        "packet_identity": packet["identity"],
        "frozen_label_identity": labels["identity"],
        "baseline_execution_plan_identity": original["identity"],
        "execution_plan_identity": plan["identity"],
        "coordinator_id": coordinator_id,
        "new_runner_sources": {runner_source: plan["source_sha256"][runner_source]},
        "reason": reason,
        "completed_at": datetime.now().astimezone().isoformat(),
        "zero_prior_prospective_inference_attested": True,
        "policy": "runner integration only; no changed methods, weights, prompts, corpus or options; manual change review required",
    }
    # Existing component/prompt sources cannot be retuned under a runner-only amendment.
    for name, old_hash in original["source_sha256"].items():
        if plan["source_sha256"].get(name) != old_hash:
            raise ValueError(
                "Existing frozen component/prompt/config changed; runner-only amendment refused"
            )
    output.mkdir(parents=True)
    write_json(output / "execution_plan.json", plan)
    write_json(output / "record.json", {**record_data, "identity": digest(record_data)})
    write_json(
        output / "artifacts.json", {p.name: file_hash(p) for p in output.iterdir() if p.is_file()}
    )
    return record_data
