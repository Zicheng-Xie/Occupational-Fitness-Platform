"""Experimental clause-linked judgments, isolated from production decisions."""

import json
import re
from typing import Literal

from pydantic import Field

from occupational_fitness_rag.evaluation.judgment_comparison import (
    SYSTEM,
    judgment_request,
    validate_answer,
)
from occupational_fitness_rag.evaluation.model_judgment import ExperimentalJudgment
from occupational_fitness_rag.schemas.workflow import Contract

PROTOCOL_SYSTEM = (
    SYSTEM.replace(
        "Return the requested JSON with assessment_outcome, explanation, source_ids and\nfact_fields. Cite only supplied IDs and fields.",
        "Return assessment_outcome, explanation and criterion_checks. Cite only supplied IDs and fields in those checks.",
    )
    + """

Apply the following output-category meanings to the supplied original evidence:
- meets_unconditional_standard: the applicable unconditional requirements are supported;
  do not infer that unknown patient findings are normal.
- may_meet_conditional_standard: the evidence allows a conditional standard and the
  patient facts establish the relevant prerequisites, not just a treatment name.
- temporarily_unfit: an applicable current restriction requires stopping driving
  pending investigation, recovery or stabilisation. Unknown information in another
  module does not erase an already established current restriction.
- does_not_meet_standard: supplied applicable evidence explicitly excludes both
  unconditional AND conditional current eligibility. Failure of an unconditional
  criterion alone does not prove failure of every conditional pathway. This
  category does not itself mean permanent disqualification.
- insufficient_information: no stronger supported restrictive conclusion can be
  established and required facts or applicable guideline evidence are missing.

Record short criterion_checks linking a verified patient finding to a specific
guideline clause. These are auditable findings, not a request for private reasoning.
For every check, copy a SHORT contiguous guideline_quote verbatim from the selected
source_text. Preserve its words, punctuation and qualifications. Use only the
requested modules, supplied source IDs and verified fact fields. A quote describes
a criterion; it does not establish that the patient's criterion is met. Explicitly
distinguish established_restriction, conditional_permission, not_established and
information_missing. Established restrictions require at least one verified fact.
For each check, state whether the clause concerns unconditional licensing,
conditional licensing, both pathways, temporary no-driving, or general information.
Do not apply an undiagnosed-blackout investigation rule when verified facts establish
a diagnosed cause; use the applicable supplied cause-specific evidence or abstain.
The application derives final citation lists from your explicit criterion checks;
do not repeat source_ids or fact_fields as top-level lists. A proposed
conditional permission does not override an independently established restriction.
Do not use unverified original-note claims to fill missing verified facts. Do not
treat the failure to establish a conditional licence as proof of a permanent ban.
Return the same provisional outcome and explanation plus 1 to 5 criterion_checks.
"""
)


class CriterionCheck(Contract):
    module: Literal["hypertension", "vision", "hearing", "blackout", "diabetes"]
    source_id: str
    guideline_quote: str = Field(min_length=12, max_length=800)
    fact_fields: list[str] = Field(max_length=8)
    licence_pathway: Literal[
        "unconditional", "conditional", "both", "temporary_no_driving", "general_information"
    ]
    finding: Literal[
        "established_restriction",
        "conditional_permission",
        "not_established",
        "information_missing",
    ]
    conclusion: str = Field(min_length=1, max_length=500)


class EvidenceJudgment(ExperimentalJudgment):
    criterion_checks: list[CriterionCheck] = Field(min_length=1, max_length=5)


class ClauseJudgment(Contract):
    assessment_outcome: Literal[
        "meets_unconditional_standard",
        "may_meet_conditional_standard",
        "temporarily_unfit",
        "does_not_meet_standard",
        "insufficient_information",
    ]
    explanation: str = Field(min_length=1, max_length=2000)
    criterion_checks: list[CriterionCheck] = Field(min_length=1, max_length=5)


def normalized_quote(value):
    """Permit PDF line wrapping, never changed wording or punctuation."""
    return re.sub(r"\s+", " ", value).strip()


def quote_locations(quote, original):
    """Return every original character span; repeated quotes remain ambiguous."""
    if not normalized_quote(quote):
        return []
    pattern = re.escape(normalized_quote(quote)).replace(r"\ ", r"\s+")
    return [
        {"char_start": match.start(), "char_end": match.end(), "original_quote": match.group()}
        for match in re.finditer(pattern, original)
    ]


def criterion_locations(answer, payload):
    sources = {source["source_id"]: source for source in payload["guideline_evidence"]}
    return [
        {
            "source_id": check.source_id,
            "pdf_page": sources[check.source_id]["pdf_page"],
            "section": sources[check.source_id]["section"],
            "spans": quote_locations(
                check.guideline_quote, sources[check.source_id]["source_text"]
            ),
            "check": check.model_dump(mode="json"),
            "support_review": "pending_independent_review",
        }
        for check in answer.criterion_checks
    ]


def build_request(config, model, payload, protocol):
    body = judgment_request(config, model, payload)
    if protocol == "baseline":
        return body
    if protocol != "evidence_contract":
        raise ValueError("Unknown judgment protocol")
    sources = [s["source_id"] for s in payload["guideline_evidence"]]
    if not sources:
        raise ValueError("Clause-linked judgment requires original guideline evidence")
    schema = ClauseJudgment.model_json_schema()
    check = schema["$defs"]["CriterionCheck"]["properties"]
    check["module"]["enum"] = payload["modules"]
    check["source_id"]["enum"] = sources
    fields = list(payload["verified_patient_facts"])
    if fields:
        check["fact_fields"]["items"] = {"type": "string", "enum": fields}
        check["fact_fields"]["maxItems"] = min(len(fields), 8)
    else:
        check["fact_fields"]["maxItems"] = 0
    body["format"] = schema
    body["messages"][0]["content"] = PROTOCOL_SYSTEM
    return body


def validate_protocol_answer(answer, payload, protocol):
    validate_answer(answer, payload, "evidence_contract")
    if protocol == "baseline":
        return
    if protocol != "evidence_contract" or not isinstance(answer, EvidenceJudgment):
        raise ValueError("Wrong judgment protocol contract")
    sources = {source["source_id"]: source for source in payload["guideline_evidence"]}
    for check in answer.criterion_checks:
        source = sources.get(check.source_id)
        if check.module not in payload["modules"] or source is None:
            raise ValueError("Criterion check cites an unprovided module or source")
        if check.source_id not in answer.source_ids:
            raise ValueError("Criterion source is absent from the final citation list")
        if not set(check.fact_fields) <= set(answer.fact_fields):
            raise ValueError("Criterion facts are absent from the final fact list")
        if not set(check.fact_fields) <= set(payload["verified_patient_facts"]):
            raise ValueError("Criterion check cites an unverified patient fact")
        if check.finding == "established_restriction" and not check.fact_fields:
            raise ValueError("An established restriction requires a verified patient fact")
        if len(normalized_quote(check.guideline_quote)) < 12 or normalized_quote(
            check.guideline_quote
        ) not in normalized_quote(source["source_text"]):
            raise ValueError("Criterion quote does not match the original guideline passage")
        if any("\u3400" <= c <= "\u9fff" for c in check.conclusion):
            raise ValueError("Criterion conclusion must be in English")


def parse_response(raw, payload, protocol):
    if raw.get("done_reason") == "length" or raw.get("done") is False:
        raise ValueError("Model output was incomplete; partial answers rejected")
    if protocol == "baseline":
        answer = ExperimentalJudgment.model_validate_json(raw["message"]["content"])
    else:
        proposed = ClauseJudgment.model_validate_json(raw["message"]["content"])
        cited_sources = {check.source_id for check in proposed.criterion_checks}
        cited_facts = {field for check in proposed.criterion_checks for field in check.fact_fields}
        answer = EvidenceJudgment.model_validate(
            {
                **proposed.model_dump(mode="json"),
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
    validate_protocol_answer(answer, payload, protocol)
    return answer


def payload_size(payload):
    return len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
