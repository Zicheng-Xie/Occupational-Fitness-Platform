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

from occupational_fitness_rag.evaluation.graph_contract import file_hash
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


def _validate_cases(cases, packet, page_text, expected_case_ids=None):
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


def _reviewed_labels(packet_directory, packet, forms, adjudication=None):
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
    a, b = [_validate_cases(f.cases, packet, page_text) for f in forms]
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
        final.update(_validate_cases(adjudication.cases, packet, page_text, disputed_cases))
        adjudicator_id = r.reviewer_id
    elif adjudication is not None:
        raise ValueError("Agreed labels do not require adjudication; omit the unused form")
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
    packet_directory, reviewer_a_path, reviewer_b_path, output, adjudication_path=None
):
    """Create new frozen scoring labels; never fill templates or run a model."""
    packet_directory, output = Path(packet_directory).resolve(), Path(output).resolve()
    if output.exists() or output == packet_directory or packet_directory in output.parents:
        raise ValueError("Freeze labels in a fresh directory outside the immutable review packet")
    packet_pins = verify_inventory(packet_directory)
    packet = json.loads((packet_directory / "manifest.json").read_bytes())
    if digest({k: v for k, v in packet.items() if k != "identity"}) != packet["identity"]:
        raise ValueError("Review packet identity differs")
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
        packet_directory, packet, forms, adjudication
    )
    input_pins = {
        "reviewer_a": file_hash(reviewer_a_path),
        "reviewer_b": file_hash(reviewer_b_path),
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
            "ready_for_prospective_evaluation": True,
            "packet_identity": packet["identity"],
            "clinical_accuracy_established": False,
        },
    )
    for name, form in [
        ("reviewer_a.json", forms[0]),
        ("reviewer_b.json", forms[1]),
        *([("adjudication.json", adjudication)] if adjudication else []),
    ]:
        write_json(output / name, form.model_dump(mode="json"))
    write_json(
        output / "artifacts.json", {p.name: file_hash(p) for p in output.iterdir() if p.is_file()}
    )
    return data


def prospective_inputs(packet_directory, frozen_labels_directory):
    """The prospective harness must call this gate before test execution/scoring.

    The general product upload endpoint is unchanged; this gate controls the new
    prospective evaluation path and cannot prevent manual exploratory uploads.
    """
    packet_directory, frozen_labels_directory = (
        Path(packet_directory),
        Path(frozen_labels_directory),
    )
    verify_inventory(packet_directory)
    verify_inventory(frozen_labels_directory)
    packet = json.loads((packet_directory / "manifest.json").read_bytes())
    readiness = json.loads((frozen_labels_directory / "readiness.json").read_bytes())
    frozen = json.loads((frozen_labels_directory / "manifest.json").read_bytes())
    if digest({k: v for k, v in frozen.items() if k != "identity"}) != frozen["identity"]:
        raise ValueError("Frozen label manifest identity differs")
    if (
        readiness.get("ready_for_prospective_evaluation") is not True
        or readiness["packet_identity"] != packet["identity"]
    ):
        raise ValueError("Independent labels are not frozen and ready for this prospective packet")
    if frozen["packet_identity"] != packet["identity"] or frozen["packet_artifacts"] != json.loads(
        (packet_directory / "artifacts.json").read_bytes()
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
    recomputed, _, ids, adjudicator_id = _reviewed_labels(
        packet_directory, packet, forms, adjudication
    )
    if (
        recomputed != labels
        or frozen["reviewer_ids"] != ids
        or frozen["adjudicator_id"] != adjudicator_id
    ):
        raise ValueError("Frozen labels differ from the independently submitted review records")
    return [
        {"case_id": c["case_id"], "nurse_note": c["nurse_note"], "modules": list(MODULES)}
        for c in packet["cases"]
    ], labels
