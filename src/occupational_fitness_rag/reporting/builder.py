from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

from occupational_fitness_rag.provenance import digest
from occupational_fitness_rag.reporting.presentation import render_case_html
from occupational_fitness_rag.schemas.red_flag_result import WorkflowRuleResult
from occupational_fitness_rag.schemas.workflow import (
    ClinicalCase,
    ReviewNote,
    WorkflowEvidencePack,
)

LABELS = {
    "meets_unconditional_standard": "Meets unconditional standard",
    "may_meet_conditional_standard": "May meet conditional standard",
    "temporarily_unfit": "Temporarily unfit",
    "does_not_meet_standard": "Does not meet standard",
    "insufficient_information": "Insufficient information",
}
MODULE_LABELS = {
    "hypertension": "Hypertension",
    "vision": "Vision",
    "hearing": "Hearing",
    "blackout": "Blackout",
    "diabetes": "Diabetes",
}


def validate_report_inputs(case, result, evidence):
    if case.case_id != result.case_id or result.case_id != evidence.case_id:
        raise ValueError("Case ID mismatch across workflow stages")
    if (
        digest(case) != result.case_sha256
        or digest(result) != evidence.rule_result_sha256
        or result.result_id != evidence.result_id
    ):
        raise ValueError("Workflow artifact identity mismatch")
    requests = {r.request_id: r for r in result.rag_requests}
    if len(evidence.evidence_items) != len(requests) or {
        x.request_id for x in evidence.evidence_items
    } != set(requests):
        raise ValueError("Evidence request accounting mismatch")
    for item in evidence.evidence_items:
        request = requests[item.request_id]
        if item.rule_id != request.rule_id or item.requested_source_ids != request.source_ids:
            raise ValueError("Evidence rule/source ownership mismatch")
        if {c.source_id for c in item.citations} | set(item.unresolved_source_ids) != set(
            request.source_ids
        ):
            raise ValueError("Unaccounted evidence source IDs")
        if any(c.source_id not in request.source_ids for c in item.citations):
            raise ValueError("Unrequested evidence source")


def build_review_note(
    case: ClinicalCase, result: WorkflowRuleResult, evidence: WorkflowEvidencePack
) -> ReviewNote:
    validate_report_inputs(case, result, evidence)
    missing = sorted({key for m in result.modules for key in m.missing_fields})
    checklist = [
        "Clinician: review source facts, rule applicability and every provisional conclusion.",
        "Confirm the commercial driving task and assess conditions outside the five-module scope.",
    ]
    checklist += [f"Confirm missing/unverified case fact: {key}" for key in missing]
    checklist += [warning.message for warning in result.processing_warnings]
    checklist += [
        f"Unresolved guideline evidence request: {key}" for key in evidence.unresolved_requests
    ]
    return ReviewNote(
        case_id=case.case_id,
        assessment_outcome=result.assessment_outcome,
        modules=result.modules,
        rule_result_sha256=digest(result),
        evidence_pack_sha256=digest(evidence),
        summary=f"{case.case_id}: {LABELS[result.assessment_outcome]}. {len(result.modules)} requested modules; {len(missing)} unresolved fact fields. This draft is occupational fitness decision support. The result is limited to the implemented criteria and is not a licensing or employment decision.",
        review_checklist=checklist,
    )


def _relative_link(root: Path, output: Path, path: str, page=None):
    try:
        target = quote(Path(os.path.relpath(root / path, output)).as_posix(), safe="/.-_")
    except ValueError:
        target = (root / path).resolve().as_uri()
    return target + (f"#page={page}" if page else "")


def render_reports(case, result, evidence, note, root: Path, output: Path) -> dict[str, str]:
    validate_report_inputs(case, result, evidence)
    citations = {c.source_id: c for item in evidence.evidence_items for c in item.citations}
    md = [
        f"# Clinical review draft — {case.case_id}",
        "",
        note.summary,
        "",
        "**DRAFT · pending_clinical_review · Clinical sign-off pending**",
        "",
        "| Module | Provisional outcome | Route | Missing fields |",
        "|---|---|---|---|",
    ]
    for module in result.modules:
        md.append(
            f"| {module.module} | {LABELS[module.assessment_outcome]} | {module.route} | {len(module.missing_fields)} |"
        )
    input_link = "source_input" + Path(case.source_document).suffix.lower()
    md += ["", f"[Original case input]({input_link})", ""]
    md += ["", "## Rule-to-source trace", ""]
    for item in result.rules_evaluated:
        if item.result not in {"triggered", "unknown"}:
            continue
        md += [f"### {item.rule_id} — {item.result}", "", item.reason, ""]
        for key, fact in item.observed_facts.items():
            value = str(fact.value) if fact.status == "present" else "UNKNOWN"
            md.append(f"- `{key}` = {value} ({fact.status})")
            for span in fact.evidence:
                locator = (
                    f"lines {span.line_start}–{span.line_end}; chars {span.start}:{span.end}"
                    + (f"; PDF page {span.pdf_page}" if span.pdf_page else "")
                )
                md += [f"  - Source {locator}: {span.quote.replace(chr(10), ' ')}"]
        md += [
            "",
            "Guideline sources: "
            + ", ".join(f"[{sid}](#{sid.lower()})" for sid in item.source_ids),
            "",
        ]
    md += ["## Guideline evidence", ""]
    for sid, citation in citations.items():
        link = _relative_link(root, output, citation.source_path, citation.pdf_page)
        locator = f"§{citation.section} · printed {citation.printed_page} / PDF {citation.pdf_page}"
        md += [
            f"### {sid}",
            "",
            f"[{locator}]({link})",
            "",
            f"Table/context: {citation.table_row}",
            "",
            "> " + citation.evidence_text.replace("\n", "\n> "),
            "",
            f"PDF region: {citation.bbox}; text SHA-256: `{citation.text_sha256}`.",
            "",
        ]
    md += [
        "## Clinician checklist",
        "",
        *["- [ ] " + x for x in note.review_checklist],
        "",
        "## Case source",
        "",
        "```text",
        case.source_text,
        "```",
        "",
        f"Input SHA-256: `{case.source_sha256}`",
        f"Rule-result SHA-256: `{digest(result)}`",
        f"Evidence-pack SHA-256: `{digest(evidence)}`",
        "",
    ]
    if note.llm_commentary:
        md += ["## Unverified local-model commentary", "", note.llm_commentary, ""]
    rendered = render_case_html(case, result, evidence, note, root, output)
    return {"draft_report.md": "\n".join(md), "draft_report.html": rendered}
