"""Consistent English labels for extraction review in reports and checklists."""

STATUS_LABELS = {
    "disabled": "Not performed (disabled)",
    "completed_no_issues": "No issues flagged by the model",
    "requires_confirmation": "Possible extraction issues require confirmation",
    "skipped_context_budget": "Not performed (input exceeds review context budget)",
    "unavailable_or_invalid": "Not completed (model unavailable or response invalid)",
}
REVIEW_LIMIT = (
    "This second-pass model review does not establish clinical accuracy. "
    "A clinician must verify the original record and any flagged information."
)


def review_lines(review):
    lines = [
        "Extraction semantic review: "
        + STATUS_LABELS.get(review["status"], "Review status unavailable"),
        REVIEW_LIMIT,
    ]
    for issue in review.get("issues", []):
        lines.append(f"Confirm {issue['field']} ({issue['kind']}): {issue['explanation']}")
    if review.get("quarantined_fields"):
        lines.append("Fields withheld from rule inputs: " + ", ".join(review["quarantined_fields"]))
    return lines
