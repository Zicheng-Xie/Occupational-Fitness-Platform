"""Experimental passage applicability followed by a separate model aggregation.

The ledger is a model proposal, not an authoritative medical interpretation.
Identifier validation and original-text resolution never change its clinical claims.
"""

import json
from copy import deepcopy
from typing import Literal

from pydantic import Field

from occupational_fitness_rag.evaluation.judgment_comparison import judgment_request
from occupational_fitness_rag.evaluation.passage_judgment import (
    FINDINGS,
    PASSAGE_SYSTEM,
    PATHWAYS,
    parse_response,
    passage_catalogue,
    request_payload,
)
from occupational_fitness_rag.evaluation.passage_judgment import (
    build_request as passage_request,
)
from occupational_fitness_rag.provenance import digest
from occupational_fitness_rag.schemas.workflow import Contract

MODULE = Literal["hypertension", "vision", "hearing", "blackout", "diabetes"]

APPLICABILITY_SYSTEM = """You record concise, auditable applicability findings for an experimental
commercial-driver assessment in English. Do not produce an overall fitness outcome
in this stage. Evaluate EVERY supplied passage exactly once. Return the required
passages object with keys P1, P2 and so on. Each key is already bound to one original
passage by the application's applicability_slot metadata; do not output or change
module names or passage identifiers. Evaluate the text assigned to that slot.
These findings are model proposals, not established clinical facts.

Only verified_patient_facts establish patient findings. Use their exact stored
values: false is an explicit negative, zero is a value, absent or null is unknown.
The nurse note gives context only. Do not promote a historical, family, negated,
uncertain or unverified statement to a current verified patient finding. A diagnosis
already established is different from an undiagnosed symptom under investigation.
Do not infer loss of consciousness from tiredness alone.

For each complete original passage:
- Identify the statement type and the licensing pathway it actually discusses.
  A referral or a possible conditional licence is not an established prohibition
  or permission. Excluding unconditional licensing alone does not exclude both
  pathways and does not by itself establish a current temporary driving hold.
- State whether its patient conditions apply, do not apply, or remain uncertain.
  Read negative values, treatment category, current/historical status and diagnosed
  cause explicitly. An applicable passage may still have unmet prerequisites.
- Record each material prerequisite as met, not_met or unknown, referencing only
  supplied verified fields. Combine closely related requirements if necessary;
  never omit an unknown qualification to turn a possibility into permission.
- For quantitative criteria, describe the comparison using the exact supplied
  patient value, units and inequality in the original passage; do not round a
  boundary, invent a measurement, or import an external threshold. If no comparison
  is relevant write 'Not applicable'. If units or measurements are absent say so.
- Distinguish established_restriction, conditional_permission, not_established and
  information_missing. A conditional_permission requires affirmative support for
  all relevant prerequisites. A treatment name alone is insufficient. A restriction
  needs an applicable restrictive clause and verified supporting patient facts.

Select only supplied verified fact fields. Keep each conclusion concise.
Do not copy the passage or provide private reasoning. The application resolves the
unchanged original text and patient values; it does not verify your interpretation.
"""

_CATEGORY_MEANINGS = PASSAGE_SYSTEM[
    PASSAGE_SYSTEM.index("Apply the following output-category meanings") : PASSAGE_SYSTEM.index(
        "Record short criterion_checks"
    )
]

AGGREGATION_SYSTEM = (
    """You propose an experimental commercial-driver fitness assessment in English.
Use only supplied verified_patient_facts and original guideline_evidence. The nurse
note gives context, not permission to promote unverified or negated findings.
Missing information is not normal. This is not a clinical licensing decision.
"""
    + _CATEGORY_MEANINGS
    + """

This is the aggregation stage. An independent preceding call recorded a proposed
applicability ledger for every supplied original passage. Read the SAME original
facts and passages again. The ledger is fallible: never treat its findings as new
patient facts or as a verified clinical authority. Return your own final criterion
checks, outcome and concise explanation. If a ledger interpretation is wrong,
correct your final check against the ORIGINAL passage and explain the disagreement.
The stored preceding ledger remains unchanged for independent review.

Use the exact scope of each applicable original clause. Distinguish failure of an
unconditional criterion, exclusion of both pathways, and an explicit current
no-driving instruction. A mere referral or missing conditional prerequisite does
not create a temporary prohibition. Unknown findings do not establish normality,
and an unresolved unrelated module does not erase an established restriction.
Do not grant a conditional standard from a possibility or a treatment label when
required qualifications remain unknown. Do not apply an investigation-only rule to
an already diagnosed cause. Do not apply a negated condition to this patient.

Return assessment_outcome, explanation and 1 to 5 criterion_checks using supplied
passage_id, module, fact_fields, licence_pathway, finding and conclusion. Cite only
supplied original passages and verified fields. The application resolves the original
text for your FINAL checks. It never converts ledger flags or reference labels into
the outcome. These checks are your own proposal, not a copy asserted to be verified.
"""
)

SOURCE_BOUND_GUIDANCE = """
Apply exact logic, without rounding, from the ORIGINAL applicable clause:
- X OR Y needs at least one true operand; it does not require both. X AND Y
  requires every operand. Keep > distinct from >=, and < distinct from <=.
- source_numeric_relations contains exact decimal arithmetic, not clinical
  criteria. Read the original comparison direction, population, treatment,
  exceptions and prerequisites yourself. Matching units alone is not applicability.
- false is an explicit negative. An absent field is unknown; never invent a
  negated finding in either your explanation or your checks. Stay within modules.
- A conditional pathway may exist even when THIS patient has not met its
  prerequisites. 'May be considered' is not evidence that prerequisites are met.
  If any required prerequisite is unknown or unmet, do not grant conditional fitness.
- Choose does_not_meet_standard when an applicable supported clause excludes
  both licence pathways. This does not mean permanent disqualification. Do not
  replace that category with temporarily_unfit merely because recovery is possible.
- Choose temporarily_unfit for an explicit applicable current no-driving period
  or instruction pending investigation, recovery or stabilisation. A still-unmet
  minimum event-free interval is not satisfied by approaching its boundary.
- If only unconditional eligibility is excluded and conditional eligibility
  remains unestablished, use insufficient_information unless another supported
  clause establishes a stronger restrictive category.
- Choose meets_unconditional_standard when applicable unrestricted requirements
  are established. Do not downgrade an explicit unrestricted treatment category
  solely because a different treatment category has conditional requirements.

Return criterion_checks with passage_slot, fact_fields, licence_pathway, finding
and conclusion. Select only a supplied final_check_slot (P1, P2, ...). The program
binds its unchanged source and module; do not output module or passage_id yourself.
The final outcome is still your proposal. No calculator relation establishes it.
"""


class Prerequisite(Contract):
    requirement: str = Field(min_length=1, max_length=180)
    status: Literal["met", "not_met", "unknown"]
    fact_fields: list[str] = Field(max_length=8)


class ApplicabilityCheck(Contract):
    module: MODULE
    passage_id: str
    # Program-derived union: up to eight direct references plus five prerequisites
    # with eight references each. Model-written component limits remain unchanged.
    fact_fields: list[str] = Field(max_length=48)
    statement_type: Literal[
        "restriction",
        "conditional_opportunity",
        "unconditional_requirement",
        "investigation_advice",
        "background",
        "multiple_clauses",
    ]
    applicability: Literal["applicable", "not_applicable", "uncertain"]
    licence_pathway: PATHWAYS
    prerequisites: list[Prerequisite] = Field(max_length=5)
    numeric_application: str = Field(min_length=1, max_length=240)
    finding: FINDINGS
    conclusion: str = Field(min_length=1, max_length=300)


class ApplicabilityReview(Contract):
    passage_checks: list[ApplicabilityCheck] = Field(min_length=1, max_length=5)


class ApplicabilityEntry(Contract):
    """Only interpretive fields are model-written; the program binds source identity."""

    fact_fields: list[str] = Field(max_length=8)
    statement_type: Literal[
        "restriction",
        "conditional_opportunity",
        "unconditional_requirement",
        "investigation_advice",
        "background",
        "multiple_clauses",
    ]
    applicability: Literal["applicable", "not_applicable", "uncertain"]
    licence_pathway: PATHWAYS
    prerequisites: list[Prerequisite] = Field(max_length=5)
    numeric_application: str = Field(min_length=1, max_length=240)
    finding: FINDINGS
    conclusion: str = Field(min_length=1, max_length=300)


def validate_patient_payload(payload):
    """Reject extra control metadata rather than silently filtering a leaked label."""
    if set(payload) != {
        "licence_context",
        "modules",
        "nurse_note",
        "verified_patient_facts",
        "guideline_evidence",
    }:
        raise ValueError(
            "Unexpected patient payload keys; reference/control metadata is prohibited"
        )
    for fact in payload["verified_patient_facts"].values():
        if set(fact) != {"value", "patient_quotes"}:
            raise ValueError("Unexpected verified-fact metadata")
    for source in payload["guideline_evidence"]:
        if not set(source) <= {
            "source_id",
            "source_text",
            "module",
            "section",
            "pdf_page",
            "printed_page",
        }:
            raise ValueError("Unexpected guideline metadata; reference annotations are prohibited")


def _bound_fields(properties, fields):
    properties["fact_fields"]["maxItems"] = min(8, len(fields))
    if fields:
        properties["fact_fields"]["items"] = {"type": "string", "enum": fields}


def build_applicability_request(config, model, payload):
    validate_patient_payload(payload)
    catalogue = passage_catalogue(payload)
    if len(catalogue) > 5:
        raise ValueError("Applicability experiment permits at most five original passages")
    entry = ApplicabilityEntry.model_json_schema()
    fields = list(payload["verified_patient_facts"])
    _bound_fields(entry["properties"], fields)
    _bound_fields(entry["$defs"]["Prerequisite"]["properties"], fields)
    definitions = entry.pop("$defs")
    definitions["ApplicabilityEntry"] = entry
    slots = {
        f"P{index}": {"$ref": "#/$defs/ApplicabilityEntry"}
        for index in range(1, len(catalogue) + 1)
    }
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "passages": {
                "type": "object",
                "additionalProperties": False,
                "properties": slots,
                "required": list(slots),
            }
        },
        "required": ["passages"],
        "$defs": definitions,
    }
    wire = request_payload(payload)
    for index, source in enumerate(wire["guideline_evidence"], 1):
        source["applicability_slot"] = f"P{index}"
    body = judgment_request(config, model, wire)
    body["messages"][0]["content"] = APPLICABILITY_SYSTEM
    body["format"] = schema
    return body


def _complete(raw):
    if raw.get("done") is False or raw.get("done_reason") == "length":
        raise ValueError("Incomplete model output; partial applicability rejected")
    return raw["message"]["content"]


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key in applicability response")
        result[key] = value
    return result


def parse_applicability_response(raw, payload):
    proposed = json.loads(_complete(raw), object_pairs_hook=_unique_json_object)
    catalogue = passage_catalogue(payload)
    slots = {f"P{index}": anchor for index, anchor in enumerate(catalogue.values(), 1)}
    if (
        not isinstance(proposed, dict)
        or set(proposed) != {"passages"}
        or not isinstance(proposed["passages"], dict)
        or set(proposed["passages"]) != set(slots)
    ):
        raise ValueError("Ledger must cover each supplied passage slot exactly once")
    checks = []
    for slot, anchor in slots.items():
        entry = ApplicabilityEntry.model_validate(proposed["passages"][slot])
        # Both direct and prerequisite references are explicit model-written IDs.
        # Derive their union instead of requiring a redundant second model copy.
        references = list(
            dict.fromkeys(
                [
                    *entry.fact_fields,
                    *(
                        field
                        for prerequisite in entry.prerequisites
                        for field in prerequisite.fact_fields
                    ),
                ]
            )
        )
        checks.append(
            {
                **entry.model_dump(mode="json"),
                "fact_fields": references,
                "passage_id": anchor["passage_id"],
                "module": anchor["module"],
            }
        )
    review = ApplicabilityReview.model_validate({"passage_checks": checks})
    fields = set(payload["verified_patient_facts"])
    for check in review.passage_checks:
        if check.module != catalogue[check.passage_id]["module"]:
            raise ValueError("Applicability module differs from the original passage")
        references = set(check.fact_fields)
        for prerequisite in check.prerequisites:
            references.update(prerequisite.fact_fields)
        if not references <= fields:
            raise ValueError("Applicability ledger cites an unverified patient fact")
        if (
            check.finding in {"established_restriction", "conditional_permission"}
            and not references
        ):
            raise ValueError("Established findings require a verified patient fact reference")
        prose = [check.conclusion, check.numeric_application]
        prose.extend(prerequisite.requirement for prerequisite in check.prerequisites)
        if any("\u3400" <= char <= "\u9fff" for item in prose for char in item):
            raise ValueError("Applicability findings must be in English")
    return review


def ledger_payload(review, payload):
    """Values come from frozen facts, never a model-written numeric duplicate."""
    catalogue = passage_catalogue(payload)
    return [
        {
            **check.model_dump(mode="json"),
            "source_id": catalogue[check.passage_id]["source_id"],
            "referenced_patient_values": {
                field: deepcopy(payload["verified_patient_facts"][field])
                for field in check.fact_fields
            },
            "interpretation_status": "unverified_model_proposal",
        }
        for check in review.passage_checks
    ]


def build_aggregation_request(config, model, payload, review):
    validate_patient_payload(payload)
    wire = request_payload(payload)
    mode = config.get("aggregation_ledger_mode", "full_values")
    if mode not in {"full_values", "field_references"}:
        raise ValueError("Unknown aggregation ledger materialization mode")
    ledger = ledger_payload(review, payload)
    if mode == "field_references":
        # Original values and source quotations remain intact in the patient table.
        # Only their repeated per-passage copies are omitted from this new protocol.
        ledger = [
            {key: value for key, value in check.items() if key != "referenced_patient_values"}
            for check in ledger
        ]
        wire["ledger_fact_reference_contract"] = (
            "Resolve each ledger fact_fields reference against verified_patient_facts. "
            "That table contains the unchanged values and original patient quotations. "
            "The ledger remains an unverified model proposal, not a new fact source."
        )
    wire["proposed_applicability_ledger"] = ledger
    wire["ledger_sha256"] = digest(review.model_dump(mode="json"))
    body = passage_request(config, model, payload, "passage_selection")
    body["messages"][1]["content"] = json.dumps(wire, ensure_ascii=False)
    body["messages"][0]["content"] = AGGREGATION_SYSTEM
    guidance = config.get("judgment_guidance", "baseline")
    if guidance not in {"baseline", "source_bound_v1"}:
        raise ValueError("Unknown experimental judgment guidance")
    if guidance == "source_bound_v1":
        from occupational_fitness_rag.evaluation.numeric_support import numeric_relations

        wire["source_numeric_relations"] = numeric_relations(payload)
        wire["numeric_support_status"] = "Exact arithmetic only; clinical applicability is unverified"
        for index, source in enumerate(wire["guideline_evidence"], 1):
            source["final_check_slot"] = f"P{index}"
        body["messages"][1]["content"] = json.dumps(wire, ensure_ascii=False)
        body["messages"][0]["content"] += SOURCE_BOUND_GUIDANCE
        schema = body["format"]["$defs"]["PassageCheck"]
        for field in ("module", "passage_id"):
            schema["properties"].pop(field)
            schema["required"].remove(field)
        schema["properties"]["passage_slot"] = {
            "type": "string", "enum": [f"P{i}" for i in range(1, len(wire["guideline_evidence"]) + 1)],
        }
        schema["required"].insert(0, "passage_slot")
    return body


def parse_aggregation_response(raw, payload, review, config=None):
    _complete(raw)
    guidance = (config or {}).get("judgment_guidance", "baseline")
    if guidance not in {"baseline", "source_bound_v1"}:
        raise ValueError("Unknown experimental judgment guidance")
    if guidance == "source_bound_v1":
        proposed = json.loads(_complete(raw), object_pairs_hook=_unique_json_object)
        slots = {f"P{i}": anchor for i, anchor in enumerate(passage_catalogue(payload).values(), 1)}
        if not isinstance(proposed, dict) or not isinstance(proposed.get("criterion_checks"), list):
            raise ValueError("Expected final criterion_checks with bound passage slots")
        for check in proposed["criterion_checks"]:
            if not isinstance(check, dict) or "module" in check or "passage_id" in check:
                raise ValueError("Final source and module must be program-bound")
            slot = check.pop("passage_slot", None)
            if not isinstance(slot, str) or slot not in slots:
                raise ValueError("Final passage slot is not in the original bundle")
            check.update(module=slots[slot]["module"], passage_id=slots[slot]["passage_id"])
        raw = deepcopy(raw)
        raw["message"]["content"] = json.dumps(proposed, ensure_ascii=False)
    answer = parse_response(raw, payload, "passage_selection")
    ids = [check.passage_id for check in answer.criterion_checks]
    checks = {check.passage_id: check for check in review.passage_checks}
    if not set(ids) <= checks.keys():
        raise ValueError("Aggregation selected a passage absent from its original ledger")
    return answer


def review_locations(review, payload):
    """Resolve internal unions directly, outside the model-written proposal contract."""
    catalogue = passage_catalogue(payload)
    common_fields = (
        "module",
        "passage_id",
        "fact_fields",
        "licence_pathway",
        "finding",
        "conclusion",
    )
    result = []
    for check in review.passage_checks:
        anchor = catalogue.get(check.passage_id)
        if anchor is None or check.module != anchor["module"]:
            raise ValueError("Ledger passage differs from its immutable original source")
        references = set(check.fact_fields)
        for prerequisite in check.prerequisites:
            references.update(prerequisite.fact_fields)
        if not references <= payload["verified_patient_facts"].keys():
            raise ValueError("Ledger location cites an unverified patient fact")
        resolved = {field: deepcopy(getattr(check, field)) for field in common_fields}
        resolved.update(source_id=anchor["source_id"], guideline_quote=anchor["original_quote"])
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
                "check": resolved,
                "support_review": "pending_independent_review",
                "check_origin": "unverified_stage_one_model_proposal",
            }
        )
    return result


def ledger_consistency_flags(review):
    """Internal contradictions are flags, not entailment scores or repair prompts."""
    flags = []
    for check in review.passage_checks:
        prefix = check.passage_id + ":"
        if check.applicability != "applicable" and check.finding in {
            "established_restriction",
            "conditional_permission",
        }:
            flags.append(prefix + "established_finding_without_reported_applicability")
        if check.finding == "conditional_permission" and any(
            requirement.status != "met" for requirement in check.prerequisites
        ):
            flags.append(prefix + "conditional_permission_with_unestablished_prerequisite")
        if check.finding == "conditional_permission" and not check.prerequisites:
            flags.append(prefix + "conditional_permission_without_reported_prerequisites")
        if (
            check.finding == "established_restriction"
            and check.licence_pathway == "general_information"
        ):
            flags.append(prefix + "restriction_classified_as_general_information")
    return flags
