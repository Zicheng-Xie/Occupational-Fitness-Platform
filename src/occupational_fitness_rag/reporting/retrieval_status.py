"""Expose retrieval execution independently from clinical rule outcomes."""

from html import escape


def render_retrieval_status(evidence, link):
    audit = evidence.retrieval
    calls = audit.get("ranking_calls", 0)
    groups = audit.get("symptom_discovery", [])
    candidates = sum(len(item.ranked_candidates) for item in evidence.evidence_items)
    discovery_count = sum(len(g["ranked_candidates"]) for g in groups)
    title = "Retrieval completed" if calls or groups else "Exact references only"
    html = (
        "<section class='section' id='symptom-retrieval'><div class='section-heading'>"
        f"<h2>Retrieval activity</h2><strong>{title}</strong></div>"
        f"<p>{calls} rule-scoped ranking calls · {candidates} rule-scoped candidates · "
        f"{len(groups)} symptom searches · {discovery_count} symptom candidates.</p>"
        "<p>Rule triggers count clinical criteria supported by sufficient verified facts. "
        "A zero count does not mean retrieval failed. Rule-linked references are mandatory "
        "citations; symptom candidates are ranked separately across the selected module.</p>"
        "<p>Retrieved passages require clinical interpretation and do not establish a diagnosis.</p>"
    )
    for group in groups:
        html += (
            f"<details class='rule-group' open><summary><strong>{escape(group['module'].title())}"
            f"</strong><span>{len(group['ranked_candidates'])} ranked candidates</span></summary>"
            f"<div class='detail-body'><p><strong>Original symptom query</strong></p>"
            f"<blockquote class='case-quote'>{escape(group['query'])}</blockquote>"
        )
        rank = {sid: r["rank"] for r in group["ranked_candidates"] for sid in r["source_ids"]}
        for citation in group["citations"]:
            url = link(citation["source_path"]) + f"#page={citation['pdf_page']}"
            html += (
                f"<details class='evidence-entry'><summary>Rank {rank[citation['source_id']]} · "
                f"{escape(citation['source_id'])} · Section {escape(citation['section'])} · "
                f"PDF {citation['pdf_page']}</summary><div class='detail-body'>"
                f"<blockquote>{escape(citation['evidence_text'])}</blockquote>"
                f"<a href='{escape(url)}'>Open original guideline page ↗</a></div></details>"
            )
        html += "</div></details>"
    return html + "<a href='evidence_pack.json'>Open retrieval audit ↗</a></section>"
