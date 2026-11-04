"""Select immutable original passages without asking a model to copy source text.

An anchor covers one supplied, complete knowledge unit. It is a mechanical text
address, not a claim that an isolated sentence is a complete clinical criterion.
"""

import json
from copy import deepcopy
from typing import Literal

from pydantic import Field

from occupational_fitness_rag.evaluation.evidence_judgment import (
    PROTOCOL_SYSTEM,
)
from occupational_fitness_rag.evaluation.evidence_judgment import (
    build_request as quote_request,
)
from occupational_fitness_rag.evaluation.evidence_judgment import (
    criterion_locations as quote_criterion_locations,
)
from occupational_fitness_rag.evaluation.evidence_judgment import (
    parse_response as parse_quote_response,
)
from occupational_fitness_rag.evaluation.judgment_comparison import (
    judgment_request,
    validate_answer,
)
from occupational_fitness_rag.evaluation.model_judgment import ExperimentalJudgment
from occupational_fitness_rag.provenance import digest, sha256_bytes
from occupational_fitness_rag.schemas.workflow import Contract

MODULES = {"hypertension", "vision", "hearing", "blackout", "diabetes"}
OUTCOMES = Literal[
    "meets_unconditional_standard",
    "may_meet_conditional_standard",
    "temporarily_unfit",
    "does_not_meet_standard",
    "insufficient_information",
]
PATHWAYS = Literal[
    "unconditional", "conditional", "both", "temporary_no_driving", "general_information"
]
FINDINGS = Literal[
    "established_restriction", "conditional_permission", "not_established", "information_missing"
]

PASSAGE_SYSTEM = (
    PROTOCOL_SYSTEM.replace(
        "For every check, copy a SHORT contiguous guideline_quote verbatim from the selected\n"
        "source_text. Preserve its words, punctuation and qualifications. Use only the\n"
        "requested modules, supplied source IDs and verified fact fields.",
        "For every check, select one supplied passage_id. The application retrieves its\n"
        "complete original source_text and text location without model transcription.\n"
        "The full passage, including qualifications, remains the basis for the check.\n"
        "Use only requested modules, supplied passage IDs and verified fact fields.",
    )
    .replace(
        "Return assessment_outcome, explanation and criterion_checks. Cite only supplied IDs and fields in those checks.",
        "Return assessment_outcome, explanation and criterion_checks. Cite only supplied passage IDs and verified fields in those checks.",
    )
    .replace(
        "A quote describes\na criterion; it does not establish that the patient's criterion is met.",
        "A selected passage describes a criterion; selecting it does not establish that\n"
        "the patient's criterion is met.",
    )
    .replace(
        "The application derives final citation lists from your explicit criterion checks;",
        "The application resolves passage_id to source_id and derives citation lists from explicit checks;",
    )
)


class PassageCheck(Contract):
    module: Literal["hypertension", "vision", "hearing", "blackout", "diabetes"]
    passage_id: str
    fact_fields: list[str] = Field(max_length=8)
    licence_pathway: PATHWAYS
    finding: FINDINGS
    conclusion: str = Field(min_length=1, max_length=500)


class PassageProposal(Contract):
    assessment_outcome: OUTCOMES
    explanation: str = Field(min_length=1, max_length=2000)
    criterion_checks: list[PassageCheck] = Field(min_length=1, max_length=5)


class ResolvedPassageCheck(PassageCheck):
    source_id: str
    guideline_quote: str = Field(min_length=12)


class PassageJudgment(ExperimentalJudgment):
    criterion_checks: list[ResolvedPassageCheck] = Field(min_length=1, max_length=5)


def passage_catalogue(payload):
    """Content-address full units; offsets are half-open Python Unicode positions."""
    if payload.get("licence_context") != "commercial":
        raise ValueError("This experiment requires the commercial licence context")
    modules = payload.get("modules", [])
    if not modules or len(set(modules)) != len(modules) or not set(modules) <= MODULES:
        raise ValueError("Invalid requested module set")
    catalogue = {}
    seen_sources = set()
    for source in payload.get("guideline_evidence", []):
        sid = source["source_id"]
        text = source["source_text"]
        module = source["module"]
        page = source["pdf_page"]
        if not isinstance(sid, str) or not sid or sid in seen_sources:
            raise ValueError("Missing or duplicate original source identifier")
        if not isinstance(text, str) or len(text.strip()) < 12:
            raise ValueError("A complete original passage is required")
        if module not in modules:
            raise ValueError("Original source module is outside the requested scope")
        if type(page) is not int or page < 1 or not source["section"]:
            raise ValueError("Original passage lacks valid PDF page and section metadata")
        seen_sources.add(sid)
        anchor = {
            "source_id": sid,
            "module": module,
            "pdf_page": page,
            "printed_page": source.get("printed_page"),
            "section": source["section"],
            "char_start": 0,
            "char_end": len(text),
            "text_sha256": sha256_bytes(text.encode("utf-8")),
        }
        pid = "PASS-" + digest(anchor)[:24]
        if pid in catalogue:
            raise ValueError("Passage identifier collision")
        catalogue[pid] = {"passage_id": pid, **anchor, "original_quote": text}
    if not catalogue:
        raise ValueError("Passage judgment requires original guideline evidence")
    return catalogue


def request_payload(payload):
    """Both arms receive the same text and anchor metadata, exactly once."""
    catalogue = passage_catalogue(payload)
    anchors = {anchor["source_id"]: anchor for anchor in catalogue.values()}
    wire = deepcopy(payload)
    for source in wire["guideline_evidence"]:
        anchor = anchors[source["source_id"]]
        source.update(
            passage_id=anchor["passage_id"],
            text_sha256=anchor["text_sha256"],
            char_start=anchor["char_start"],
            char_end=anchor["char_end"],
        )
    return wire


def build_request(config, model, payload, protocol):
    wire = request_payload(payload)
    if protocol == "quote_contract":
        return quote_request(config, model, wire, "evidence_contract")
    if protocol != "passage_selection":
        raise ValueError("Unknown passage comparison protocol")
    catalogue = passage_catalogue(payload)
    schema = PassageProposal.model_json_schema()
    props = schema["$defs"]["PassageCheck"]["properties"]
    props["passage_id"]["enum"] = list(catalogue)
    props["module"]["enum"] = payload["modules"]
    fields = list(payload["verified_patient_facts"])
    if fields:
        props["fact_fields"]["items"] = {"type": "string", "enum": fields}
    props["fact_fields"]["maxItems"] = min(8, len(fields))
    body = judgment_request(config, model, wire)
    body["format"] = schema
    body["messages"][0]["content"] = PASSAGE_SYSTEM
    return body


def parse_response(raw, payload, protocol):
    catalogue = passage_catalogue(payload)
    if protocol == "quote_contract":
        answer = parse_quote_response(raw, payload, "evidence_contract")
    elif protocol == "passage_selection":
        if raw.get("done_reason") == "length" or raw.get("done") is False:
            raise ValueError("Model output was incomplete; partial answers rejected")
        proposed = PassageProposal.model_validate_json(raw["message"]["content"])
        checks = []
        for check in proposed.criterion_checks:
            anchor = catalogue.get(check.passage_id)
            if anchor is None:
                raise ValueError("Selected passage ID is not in this evidence bundle")
            checks.append(
                {
                    **check.model_dump(mode="json"),
                    "source_id": anchor["source_id"],
                    "guideline_quote": anchor["original_quote"],
                }
            )
        cited_sources = {check["source_id"] for check in checks}
        cited_facts = {field for check in checks for field in check["fact_fields"]}
        answer = PassageJudgment.model_validate(
            {
                **proposed.model_dump(mode="json"),
                "criterion_checks": checks,
                "source_ids": [
                    source["source_id"]
                    for source in payload["guideline_evidence"]
                    if source["source_id"] in cited_sources
                ],
                "fact_fields": [
                    field for field in payload["verified_patient_facts"] if field in cited_facts
                ],
            }
        )
        # Check original explicit field references before canonicalization can omit them.
        for check in checks:
            if not set(check["fact_fields"]) <= set(payload["verified_patient_facts"]):
                raise ValueError("Criterion check cites an unverified patient fact")
        validate_answer(answer, payload, "passage_selection")
    else:
        raise ValueError("Unknown passage comparison protocol")
    sources = {source["source_id"]: source for source in payload["guideline_evidence"]}
    for check in answer.criterion_checks:
        if check.module != sources[check.source_id]["module"]:
            raise ValueError("Criterion module differs from the selected original source")
        if (
            check.finding in {"established_restriction", "conditional_permission"}
            and not check.fact_fields
        ):
            raise ValueError("Established findings require a verified patient fact reference")
        if any("\u3400" <= char <= "\u9fff" for char in check.conclusion):
            raise ValueError("Criterion conclusion must be in English")
    return answer


def criterion_locations(answer, payload):
    catalogue = passage_catalogue(payload)
    if not isinstance(answer, PassageJudgment):
        return quote_criterion_locations(answer, payload)
    result = []
    for check in answer.criterion_checks:
        anchor = catalogue[check.passage_id]
        if (
            check.source_id != anchor["source_id"]
            or check.guideline_quote != anchor["original_quote"]
        ):
            raise ValueError("Resolved passage differs from its immutable original")
        result.append(
            {
                "passage_id": check.passage_id,
                "source_id": anchor["source_id"],
                "pdf_page": anchor["pdf_page"],
                "printed_page": anchor["printed_page"],
                "section": anchor["section"],
                "text_sha256": anchor["text_sha256"],
                "offset_unit": "python_unicode_code_points",
                "anchor_scope": "complete_original_knowledge_unit",
                "spans": [
                    {key: anchor[key] for key in ("char_start", "char_end", "original_quote")}
                ],
                "check": check.model_dump(mode="json"),
                "support_review": "pending_independent_review",
            }
        )
    return result


def output_consistency_flags(answer, payload):
    """Flag contradictions in model-reported categories, never decide eligibility.

    This checks relationships between structured assertions. It does not establish
    that an assertion is supported by the patient facts or the selected guideline.
    """
    del payload
    checks = answer.criterion_checks
    established = [check for check in checks if check.finding == "established_restriction"]
    both = any(check.licence_pathway == "both" for check in established)
    temporary = any(check.licence_pathway == "temporary_no_driving" for check in established)
    conditional = any(
        check.finding == "conditional_permission"
        and check.licence_pathway in {"conditional", "both"}
        for check in checks
    )
    outcome = answer.assessment_outcome
    flags = []
    if outcome == "meets_unconditional_standard" and established:
        flags.append("unconditional_permission_conflicts_with_reported_restriction")
    if outcome in {"insufficient_information", "may_meet_conditional_standard"} and (
        both or temporary
    ):
        flags.append("reported_restriction_not_reflected_in_outcome")
    if outcome == "does_not_meet_standard" and not both:
        flags.append("both_pathways_exclusion_not_established_in_checks")
    if outcome == "temporarily_unfit" and not temporary:
        flags.append("temporary_restriction_not_established_in_checks")
    if outcome == "may_meet_conditional_standard" and not conditional:
        flags.append("conditional_prerequisites_not_established_in_checks")
    return flags


def serialized_request_bytes(body):
    """Full HTTP JSON size, distinct from patient payload or measured token count."""
    return len(json.dumps(body, ensure_ascii=True).encode("utf-8"))
