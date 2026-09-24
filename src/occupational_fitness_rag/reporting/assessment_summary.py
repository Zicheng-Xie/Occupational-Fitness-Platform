"""Explain assessment completeness without altering clinical decisions."""

from html import escape

from occupational_fitness_rag.case_intake.semantic_review import field_module


def assessment_summary(case, result):
    findings = [r for r in result.rules_evaluated if r.result == "triggered"]
    modules = []
    for module in result.modules:
        facts = [v for k, v in case.facts.items() if field_module(k) == module.module]
        present = sum(f.status == "present" for f in facts)
        unverified = sum(f.status in {"conflicting", "requires_confirmation"} for f in facts)
        status = (
            "No source-supported facts for this requested module"
            if not present
            else "Source-supported facts available"
        )
        if unverified:
            status += "; some facts require confirmation"
        modules.append(
            {
                "module": module.module,
                "present": present,
                "unverified": unverified,
                "status": status,
                "missing": len(module.missing_fields),
            }
        )
    explanation = (
        f"{len(findings)} rules triggered from source-supported facts. "
        "The overall assessment is incomplete; this does not erase the findings below. "
        "Missing facts in any requested module can prevent an overall clearance."
        if result.assessment_outcome == "insufficient_information" and findings
        else "No rule criteria were established from the available verified facts. "
        "This does not establish absence of disease or failure of retrieval."
        if result.assessment_outcome == "insufficient_information"
        else "The provisional outcome reflects the applicable rule priority. "
        "Missing information in other modules remains visible and does not erase an established adverse finding."
    )
    return {"explanation": explanation, "findings": findings, "modules": modules}


def render_assessment_summary(case, result):
    summary = assessment_summary(case, result)
    parts = [
        "<section class='section' id='assessment-findings'><div class='section-heading'>"
        "<h2>Established rule findings</h2><small>Separate from assessment completeness</small>"
        "</div><p>" + escape(summary["explanation"]) + "</p>"
    ]
    for rule in summary["findings"]:
        parts.append(
            f"<div class='review-block'><h3><a href='#rules-{escape(rule.module)}'>"
            f"{escape(rule.module.title())} / {escape(rule.rule_id)}</a></h3>"
            f"<p>{escape(rule.reason)}</p></div>"
        )
    parts.append("<h3>Information coverage by requested module</h3><ul class='review-list'>")
    for m in summary["modules"]:
        parts.append(
            f"<li><strong>{escape(m['module'].title())}:</strong> {escape(m['status'])}; "
            f"{m['present']} supported fields; {m['missing']} unresolved rule fields.</li>"
        )
    parts.append(
        "</ul><p class='reference-state'>Unresolved fields belong to the selected rule branches; "
        "they are not a diagnosis or an instruction to perform every listed test. "
        "Triggered rules can identify missing tests, treatment categories or adverse criteria; "
        "they are not a count of diagnosed diseases.</p></section>"
    )
    return "".join(parts)
