"""Self-contained, offline HTML views. Presentation never changes assessment data."""

from __future__ import annotations

import html
import os
from pathlib import Path
from urllib.parse import quote

from occupational_fitness_rag.provenance import digest
from occupational_fitness_rag.reporting.styles import CSS

OUTCOMES = {
    "meets_unconditional_standard": ("Meets unconditional standard", "clear"),
    "may_meet_conditional_standard": ("May meet conditional standard", "review"),
    "temporarily_unfit": ("Temporarily unfit", "adverse"),
    "does_not_meet_standard": ("Does not meet standard", "adverse"),
    "insufficient_information": ("Insufficient information", "incomplete"),
}
MODULES = {
    "hypertension": "Hypertension",
    "vision": "Vision",
    "hearing": "Hearing",
    "blackout": "Blackout",
    "diabetes": "Diabetes",
}
ROUTES = {
    "fast_path": "Routine review",
    "rag_review": "Evidence review",
    "missing_information": "Review after additional information",
    "human_review": "Refer for human review",
}
FACT_STATUS = {
    "present": "Source-supported",
    "unknown": "Not documented",
    "conflicting": "Conflicting records",
    "requires_confirmation": "Confirmation required",
}
RULE_STATUS = {
    "triggered": "Triggered",
    "unknown": "Unresolved information",
    "not_triggered": "Not triggered",
    "not_applicable": "Not applicable",
}
FIELDS = {
    "cardiovascular.blood_pressure.persistent_systolic": "Persistent systolic blood pressure",
    "cardiovascular.blood_pressure.persistent_diastolic": "Persistent diastolic blood pressure",
    "cardiovascular.blood_pressure.observed_systolic": "Observed systolic blood pressure",
    "cardiovascular.blood_pressure.observed_diastolic": "Observed diastolic blood pressure",
    "cardiovascular.blood_pressure.repeat_available": "Repeat BP reading available",
    "cardiovascular.hypertension.antihypertensive_therapy": "Antihypertensive therapy",
    "cardiovascular.hypertension.controlled_for_4_weeks": "BP controlled for at least four weeks",
    "cardiovascular.hypertension.driving_impairing_medication_side_effects": "Medication side effects affecting driving",
    "cardiovascular.hypertension.target_organ_damage_relevant_to_driving": "Target-organ damage relevant to driving",
    "cardiovascular.hypertension.initial_specialist_information_available": "Initial specialist information available",
    "cardiovascular.myocardial_infarction_history": "History of myocardial infarction",
    "cardiovascular.chest_pain": "Chest pain",
    "cardiovascular.shortness_of_breath": "Shortness of breath",
    "cardiovascular.specialist_report_available": "Cardiovascular specialist report available",
    "vision.normal_statement": "Normal vision explicitly documented",
    "vision.specialist_assessment_available": "Vision specialist assessment available",
    "vision.visual_field.confirmed_defect": "Confirmed visual-field defect",
    "vision.visual_field.reported_defect": "Reported visual-field defect",
    "vision.visual_field.binocular_horizontal_extent_degrees": "Binocular horizontal visual field",
    "vision.visual_field.significant_loss_likely_to_impede_driving": "Significant field loss likely to impair driving",
    "vision.visual_field.static_and_unlikely_to_progress_rapidly": "Visual field stable and unlikely to deteriorate rapidly",
    "vision.visual_field.measured_within_10_degrees_vertical": "Field measured within 10 degrees above and below the horizontal",
    "vision.monocular": "Monocular vision",
    "vision.remaining_eye.snellen": "Remaining-eye acuity",
    "vision.remaining_eye.horizontal_field_degrees": "Remaining-eye horizontal visual field",
    "vision.remaining_eye.other_significant_field_loss": "Other significant field loss in the remaining eye",
    "vision.remaining_eye.field_measured_within_10_degrees_vertical": "Remaining-eye field measured within 10 degrees above and below the horizontal",
    "vision.diplopia.present": "Diplopia",
    "vision.diplopia.physiological": "Physiological diplopia",
    "vision.diplopia.within_20_degrees": "Diplopia within the central 20-degree field",
    "hearing.clinical_assessment": "Clinical hearing assessment",
    "hearing.audiometry.available": "Audiometry available",
    "hearing.average_frequencies_khz": "Frequencies used for the hearing average",
    "hearing.unaided_better_ear_average_db": "Unaided better-ear average hearing threshold",
    "hearing.aided_standard_met": "Aided hearing standard met",
    "hearing.ent_or_audiologist_information_available": "ENT or audiologist information available",
    "hearing.hearing_aid_used": "Hearing aid used",
    "blackout.occurred": "Blackout history",
    "blackout.mechanism_status": "Blackout mechanism investigation status",
    "blackout.diagnosis": "Blackout diagnosis",
    "blackout.provoking_factor_well_defined": "Well-defined provoking factor",
    "blackout.recurrence_while_driving_unlikely": "Recurrence while driving unlikely",
    "blackout.episodes_separated_by_24h_count": "Episodes separated by at least 24 hours",
    "blackout.years_since_last_event": "Years since the last event",
    "blackout.appropriate_specialist_information_available": "Appropriate specialist information available",
    "diabetes.present": "Diabetes documented",
    "diabetes.treatment_category": "Diabetes treatment category",
    "diabetes.driving_relevant_comorbidity_status": "Driving-relevant comorbidity assessment",
    "diabetes.recent_severe_hypoglycaemic_event": "Recent severe hypoglycaemia",
    "diabetes.hypoglycaemia_awareness": "Hypoglycaemia awareness",
    "diabetes.regimen_minimises_hypoglycaemia": "Treatment minimises hypoglycaemia risk",
    "diabetes.driving_relevant_end_organ_effects": "End-organ effects relevant to driving",
    "diabetes.initial_specialist_information_available": "Initial diabetes specialist information available",
    "diabetes.gestational": "Gestational diabetes",
    "diabetes.severe_hypoglycaemic_event.occurred": "Severe hypoglycaemic event documented",
    "diabetes.severe_hypoglycaemic_event.weeks_since_last": "Weeks since the last severe hypoglycaemic event",
    "diabetes.glucose_monitoring_records_months": "Months of glucose-monitoring records",
    "diabetes.specialist_information_available": "Diabetes specialist information available",
    "diabetes.acutely_unwell": "Acutely unwell",
    "diabetes.metabolically_unstable": "Metabolically unstable",
}
for _correction, _label in (("uncorrected", "uncorrected"), ("corrected", "corrected")):
    for _eye, _eye_label in (
        ("right.snellen", "Right eye"),
        ("left.snellen", "Left eye"),
        ("better_eye", "Better eye"),
    ):
        FIELDS[f"vision.{_correction}.{_eye}"] = f"{_eye_label} {_label} acuity"

SCRIPT = """
document.documentElement.classList.add('has-js');
function revealAnchor(){
  let id;try{id=decodeURIComponent(location.hash.slice(1))}catch{return}
  const target=document.getElementById(id);if(!target)return;
  let parent=target;while(parent){if(parent.tagName==='DETAILS')parent.open=true;parent=parent.parentElement}
  target.scrollIntoView({block:'start'});
}
window.addEventListener('hashchange',revealAnchor);
document.querySelectorAll('a[href^="#"]').forEach(a=>a.addEventListener('click',()=>{if(a.hash===location.hash)revealAnchor()}));
if(location.hash)revealAnchor();
document.querySelectorAll('[data-expand]').forEach(button=>button.addEventListener('click',()=>{
  document.querySelectorAll('#rules details').forEach(d=>d.open=button.dataset.expand==='all');
}));
document.querySelectorAll('[data-print]').forEach(button=>button.addEventListener('click',()=>window.print()));
let folded=[];window.addEventListener('beforeprint',()=>{folded=[...document.querySelectorAll('details:not([open])')];folded.forEach(d=>d.open=true)});
window.addEventListener('afterprint',()=>{folded.forEach(d=>d.open=false);folded=[]});
const search=document.getElementById('case-search');
if(search){
  const rows=[...document.querySelectorAll('[data-case]')],tabs=[...document.querySelectorAll('[data-source-filter]')];
  const outcome=document.getElementById('outcome-filter');let source='all';
  function filter(){let count=0;const query=search.value.trim().toLowerCase();rows.forEach(row=>{
    const show=(source==='all'||row.dataset.source===source)&&(!outcome.value||row.dataset.outcome===outcome.value)&&row.textContent.toLowerCase().includes(query);
    row.hidden=!show;if(show)count++;
  });document.getElementById('case-count').textContent=count+' / '+rows.length+' reports';document.getElementById('empty-state').hidden=count!==0;}
  tabs.forEach(tab=>tab.addEventListener('click',()=>{source=tab.dataset.sourceFilter;tabs.forEach(t=>t.setAttribute('aria-pressed',String(t===tab)));filter()}));
  search.addEventListener('input',filter);outcome.addEventListener('change',filter);
  document.getElementById('clear-filters').addEventListener('click',()=>{
    search.value='';outcome.value='';source='all';
    tabs.forEach(t=>t.setAttribute('aria-pressed',String(t.dataset.sourceFilter==='all')));
    filter();search.focus();
  });
}
const sectionLinks=[...document.querySelectorAll('.rail nav a[href^="#"]')];
const sections=sectionLinks.map(a=>document.getElementById(a.hash.slice(1))).filter(Boolean);
if(sections.length>1&&'IntersectionObserver' in window){
  const observer=new IntersectionObserver(entries=>{
    const visible=entries.filter(e=>e.isIntersecting).sort((a,b)=>a.boundingClientRect.top-b.boundingClientRect.top);
    if(!visible.length)return;
    sectionLinks.forEach(a=>{
      if(a.hash==='#'+visible[0].target.id)a.setAttribute('aria-current','location');
      else a.removeAttribute('aria-current');
    });
  },{rootMargin:'-5% 0px -65% 0px',threshold:0});
  sections.forEach(section=>observer.observe(section));
}

"""


def esc(value):
    return html.escape(str(value))


def local_link(root: Path, output: Path, relative: str):
    try:
        return quote(Path(os.path.relpath(root / relative, output)).as_posix(), safe="/.-_")
    except ValueError:
        return (root / relative).resolve().as_uri()


def badge(outcome):
    label, style = OUTCOMES[outcome]
    return f"<span class='badge {style}'>{label}</span>"


def field_label(key):
    return FIELDS.get(key, key)


def fact_value(fact):
    if fact.status != "present":
        return FACT_STATUS[fact.status]
    value = "Yes" if fact.value is True else "No" if fact.value is False else str(fact.value)
    return value + (" " + fact.unit if fact.unit else "")


def icon(kind):
    """Small original line symbols; no external fonts or icon dependencies."""
    paths = {
        "grid": "<rect x='3' y='3' width='7' height='7' rx='1.5'/><rect x='14' y='3' width='7' height='7' rx='1.5'/><rect x='3' y='14' width='7' height='7' rx='1.5'/><rect x='14' y='14' width='7' height='7' rx='1.5'/>",
        "file": "<path d='M14 3H6a1 1 0 0 0-1 1v16h14V8zM14 3v5h5M8 12h8M8 16h5'/>",
        "check": "<rect x='4' y='3' width='16' height='18' rx='3'/><path d='m8 12 3 3 5-6'/>",
        "source": "<path d='m8 5-6 7 6 7m8-14 6 7-6 7m-3-15-2 16'/>",
        "search": "<circle cx='10.5' cy='10.5' r='6.5'/><path d='m16 16 5 5'/>",
        "print": "<path d='M7 8V3h10v5M7 17H3V9h18v8h-4M7 14h10v7H7zM17 11h1'/>",
    }
    return f"<svg class='icon' viewBox='0 0 24 24' aria-hidden='true'>{paths[kind]}</svg>"


def page(title, navigation, body, *, library=False):
    nav_items = []
    for number, (label, url, current) in enumerate(navigation):
        selected = " aria-current='page'" if current else ""
        symbol = ("grid", "check", "file", "source", "file", "source")[number % 6]
        nav_items.append(
            f"<a href='{esc(url)}'{selected}>{icon(symbol)}<span>{esc(label)}</span></a>"
        )
    nav = "".join(nav_items)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} | Occupational Fitness Platform</title><style>{CSS}</style></head>
<body><a class="skip-link" href="#main">Skip to content</a><div class="shell"><aside class="rail"><div class="rail-inner"><div class="brand"><span class="brand-mark">{icon("grid")}</span><span>Occupational Fitness<small>Platform</small></span></div><p class="rail-label">{"WORKSPACE" if library else "REPORT CONTENTS"}</p><nav aria-label="{"Assessment navigation" if library else "Report navigation"}">{nav}</nav><div class="rail-foot"><strong>Commercial driver fitness</strong>Austroads / AP-G56-22<br>Assessment drafts for clinical review</div></div></aside><main class="content" id="main">{body}</main></div><script type="text/javascript">{SCRIPT}</script></body></html>"""


def render_case_html(case, result, evidence, note, root: Path, output: Path):
    citations = {c.source_id: c for item in evidence.evidence_items for c in item.citations}
    refs = {sid: f"{n:02}" for n, sid in enumerate(citations, 1)}
    missing = sorted({key for m in result.modules for key in m.missing_fields})
    triggered = sum(r.result == "triggered" for r in result.rules_evaluated)
    nav = [
        ("Overview", "#overview", False),
        ("Information and review", "#review", False),
        ("Case source", "#case-source", False),
        ("Rule evaluations", "#rules", False),
        ("Guideline evidence", "#evidence", False),
        ("Files and audit", "#files", False),
    ]
    back = local_link(root, output, "outputs/index.html")
    body = [
        f"<div class='topline'><a href='{esc(back)}'>← Assessment records</a><div class='top-actions'><span class='draft'>DRAFT / Clinical review pending</span><button class='print-button js-only' data-print>{icon('print')}Print report</button></div></div><header class='page-heading'><div><p class='eyebrow'>COMMERCIAL DRIVER FITNESS · REVIEW REPORT</p><h1>{esc(case.case_id)}</h1><p class='description'>Review case facts, rule evaluations and linked guideline evidence.</p></div><span class='heading-meta'>AP-G56-22<br>Assessment records</span></header>"
    ]
    extraction = case.extraction_metadata
    if extraction.get("model"):
        accepted = len(extraction.get("accepted_fields", []))
        state = (
            "Extraction validated"
            if extraction.get("status", "").startswith("completed")
            else "Model unavailable; deterministic extraction applied"
        )
        body.append(
            f"<p class='reference-state'>Local model {esc(extraction['model'])} · {state} · {accepted} model-extracted fields accepted</p>"
        )
    body.append(
        f"<section id='overview'><div class='result-summary'><div><p class='eyebrow'>Overall provisional outcome</p><div class='result-title'>{badge(result.assessment_outcome)}</div><p class='muted'>{ROUTES[result.route]}. These outcomes cover only the {len(result.modules)} requested modules.</p></div><div class='summary-facts'><div><strong>{len(missing):02}</strong>Missing fields</div><div><strong>{triggered:02}</strong>Triggered rules</div><div><strong>{len(citations):02}</strong>Guideline citations</div></div></div><div class='table-wrap'><table class='module-table'><caption class='sr-only'>Provisional outcomes by module</caption><thead><tr><th scope='col'>Module</th><th scope='col'>Provisional outcome</th><th scope='col'>Next step</th><th scope='col'>Missing fields</th></tr></thead><tbody>"
    )
    for module in result.modules:
        body.append(
            f"<tr><td><a class='module-name' href='#rules-{esc(module.module)}'>{MODULES[module.module]}</a></td><td>{badge(module.assessment_outcome)}</td><td class='muted'>{ROUTES[module.route]}</td><td class='number'>{len(module.missing_fields) or '—'}</td></tr>"
        )
    body.append(
        "</tbody></table></div><p class='reference-state'>Undocumented information remains unknown. Clinical review is pending; this report is not a final fitness or licensing decision.</p></section>"
    )
    body.append(
        "<section class='section' id='review'><div class='section-heading'><h2><span class='section-no'>01</span>Information and review</h2><small>Grouped by module</small></div>"
    )
    for module in result.modules:
        if module.missing_fields:
            fields = "".join(
                f"<li title='{esc(key)}'>{esc(field_label(key))}</li>"
                for key in module.missing_fields
            )
            body.append(
                f"<div class='review-block'><h3>{MODULES[module.module]}</h3><ul class='field-list'>{fields}</ul></div>"
            )
    if not missing:
        body.append(
            "<p class='description'>No required fields are missing for these rules. A clinician must still verify the information and rule applicability.</p>"
        )
    if result.processing_warnings or evidence.unresolved_requests:
        warnings = result.processing_warnings + [
            f"Unresolved guideline evidence: {key}" for key in evidence.unresolved_requests
        ]
        body.append(
            "<ul class='warning-list'>" + "".join(f"<li>{esc(x)}</li>" for x in warnings) + "</ul>"
        )
    body.append(
        "<ol class='review-list'><li>Verify source quotations, rule applicability and each provisional module outcome.</li><li>Confirm the commercial driving task and review conditions outside the requested modules.</li></ol><details class='technical'><summary>Full review checklist</summary><ul class='review-list'>"
        + "".join(f"<li>{esc(x)}</li>" for x in note.review_checklist)
        + "</ul></details></section>"
    )
    input_link = "source_input" + Path(case.source_document).suffix.lower()
    body.append(
        "<section class='section' id='case-source'><div class='section-heading'><h2><span class='section-no'>02</span>Case source</h2><small>Original wording</small></div><div class='source-paper'>"
    )
    for number, line in enumerate(case.source_text.splitlines(), 1):
        body.append(
            f"<div class='source-line' id='case-line-{number}'><span class='line-number'>{number:02}</span><span class='line-text'>{esc(line) or '&nbsp;'}</span></div>"
        )
    body.append(
        f"</div><div class='source-toolbar'><span>{esc(case.source_document)}</span><a href='{esc(input_link)}'>Open original input ↗</a></div></section>"
    )
    body.append(
        "<section class='section' id='rules'><div class='section-heading'><h2><span class='section-no'>03</span>Rule evaluations</h2><small>Expand a module to review</small></div><div class='rule-tools js-only'><button class='text-button' data-expand='all'>Expand all rules</button><button class='text-button' data-expand='none'>Collapse all rules</button></div>"
    )
    for module in result.modules:
        items = [r for r in result.rules_evaluated if r.module == module.module]
        relevant = sum(r.result in {"triggered", "unknown"} for r in items)
        body.append(
            f"<details class='rule-group' id='rules-{esc(module.module)}'><summary><span class='summary-main'><strong>{MODULES[module.module]}</strong></span><span class='summary-end'>{relevant} triggered or unresolved / {len(items)} rules</span></summary><div class='detail-body'>"
        )
        for item in items:
            body.append(
                f"<details class='rule-entry'><summary><span class='summary-main'><strong>{esc(item.subcondition.replace('_', ' '))}</strong><small class='micro'>{esc(item.rule_id)}</small></span><span class='summary-end'>{RULE_STATUS[item.result]}</span></summary><div class='detail-body'><p class='rule-reason'>{esc(item.reason)}</p>"
            )
            for key, fact in item.observed_facts.items():
                body.append(
                    f"<div class='fact-item'><div class='fact-line'><span>{esc(field_label(key))}</span><strong>{esc(fact_value(fact))}</strong></div><p class='micro'>{esc(key)} · {FACT_STATUS[fact.status]}</p>"
                )
                for span in fact.evidence:
                    locator = (
                        f"Source lines {span.line_start}–{span.line_end} · characters {span.start}:{span.end}"
                        + (f" · PDF page {span.pdf_page}" if span.pdf_page else "")
                    )
                    body.append(
                        f"<blockquote class='case-quote'><a href='#case-line-{span.line_start}'>{esc(locator)}</a>{esc(span.quote)}</blockquote>"
                    )
                body.append("</div>")
            links = "".join(
                f"<a href='#{esc(sid)}' title='{esc(sid)}'>Source {refs[sid]} ↗</a>"
                for sid in item.source_ids
                if sid in refs
            )
            if links:
                body.append(f"<div class='ref-links'>{links}</div>")
            else:
                body.append(
                    "<p class='reference-state'>This rule was not included in the current evidence requests. Its source IDs remain available in the rule result.</p>"
                )
            body.append("</div></details>")
        body.append("</div></details>")
    body.append(
        "</section><section class='section' id='evidence'><div class='section-heading'><h2><span class='section-no'>04</span>Guideline evidence</h2><small>Austroads · AP-G56-22</small></div>"
    )
    for sid, citation in citations.items():
        link = local_link(root, output, citation.source_path) + f"#page={citation.pdf_page}"
        metadata = f"Source ID: {sid}\nPDF region: {citation.bbox}\nText SHA-256: {citation.text_sha256}\nDocument SHA-256: {citation.document_sha256}"
        body.append(
            f"<details class='evidence-entry' id='{esc(sid)}'><summary><span class='source-ref'>{refs[sid]}</span><span class='summary-main'><strong>{esc(citation.table_row or citation.section)}</strong><small>Section {esc(citation.section)} · Printed page {citation.printed_page}</small></span><span class='summary-end'>PDF {citation.pdf_page}</span></summary><div class='detail-body'><div class='evidence-info'><span>{'Commercial driving standard' if citation.applicability == 'commercial_table' else 'Shared guidance'}</span><a href='{esc(link)}'>Open source PDF page {citation.pdf_page} ↗</a></div><blockquote class='source-text'>{esc(citation.evidence_text)}</blockquote><p class='reference-state'>Source text verified. Clinical interpretation remains subject to review.</p><details class='technical'><summary>Source location and fingerprints</summary><pre>{esc(metadata)}</pre></details></div></details>"
        )
    body.append("</section>")
    if note.llm_commentary:
        body.append(
            f"<section class='section'><div class='section-heading'><h2>Local-model commentary</h2><small>Unverified</small></div><p class='source-text'>{esc(note.llm_commentary)}</p></section>"
        )
    body.append(
        "<section class='section' id='files'><div class='section-heading'><h2><span class='section-no'>05</span>Files and audit</h2><small>Complete review record</small></div><div class='download-list'>"
    )
    for label, name in (
        ("Markdown report", "draft_report.md"),
        ("Structured case", "structured_case.json"),
        ("Rule result", "rule_result.json"),
        ("Evidence pack", "evidence_pack.json"),
        ("Clinician checklist", "gp_review_note.json"),
        ("Run manifest", "run_manifest.json"),
        ("Extraction audit", "llm_extraction_audit.json"),
        ("Category facts", "condition_map.json"),
    ):
        body.append(f"<a href='{name}'>{label} ↗</a>")
    body.append(
        f"</div><details class='technical'><summary>Input and result fingerprints</summary><pre>Input SHA-256: {esc(case.source_sha256)}\nRule-result SHA-256: {digest(result)}\nEvidence-pack SHA-256: {digest(evidence)}</pre></details></section><footer class='page-end'><span>{esc(case.case_id)} · Assessment draft · Clinical sign-off pending</span><a href='#main'>Back to top ↑</a></footer>"
    )
    return page(f"{case.case_id} · Review report", nav, "".join(body))


def render_library(entries):
    """entries contain already verified report paths and presentation-only counts."""
    rows = []
    for entry in entries:
        source = "original" if entry["case_id"].startswith("SYN-M2") else "expansion"
        source_label = (
            "Supplied synthetic input" if source == "original" else "Extension synthetic input"
        )
        path = quote(entry["relative"], safe="/.-_") + "/draft_report.html"
        rows.append(
            f"<tr data-case='{esc(entry['case_id'])}' data-source='{source}' data-outcome='{esc(entry['assessment_outcome'])}'><td><a class='case-link' href='{path}'>{esc(entry['case_id'])}</a></td><td class='source-label'>{source_label}</td><td>{badge(entry['assessment_outcome'])}</td><td class='number'>{entry['missing_count'] or '—'}</td><td><a class='entry-link' href='{path}' aria-label='Open report for {esc(entry['case_id'])}'>View report ↗</a></td></tr>"
        )
    options = "".join(
        f"<option value='{key}'>{label}</option>" for key, (label, _) in OUTCOMES.items()
    )
    original = sum(e["case_id"].startswith("SYN-M2") for e in entries)
    incomplete = sum(e["missing_count"] > 0 for e in entries)
    metrics = f"""<div class='metric-grid'><div class='metric'><span class='metric-label'>Assessment reports{icon("file")}</span><strong>{len(entries):02}</strong><small>Available for clinical review</small></div><div class='metric'><span class='metric-label'>Missing information{icon("check")}</span><strong>{incomplete:02}</strong><small>Reports with undocumented fields</small></div><div class='metric'><span class='metric-label'>Input collection{icon("grid")}</span><strong>{original:02} / {len(entries) - original:02}</strong><small>Supplied / extension cases</small></div></div>"""
    nav = [
        ("Assessment records", "#main", True),
        ("Project guide", "../README.md", False),
        ("Architecture", "../docs/architecture.md", False),
        ("Verification", "../docs/verification.md", False),
    ]
    body = f"""<div class='topline'><span>Assessments / Assessment records</span><span class='draft'>DRAFT / Review pending</span></div><header class='page-heading'><div><p class='eyebrow'>ASSESSMENT RECORDS</p><h1>Assessment records</h1><p class='description'>{len(entries)} synthetic assessment records covering hypertension, vision, hearing, blackout and diabetes.<br>Select a record to review its provisional outcome, missing information and source evidence.</p></div><span class='heading-meta'>AP-G56-22<br>Commercial driver fitness</span></header>{metrics}<section class='library-panel' aria-label='Assessment report directory'><div class='panel-heading'><h2>Report directory</h2><small>All records are synthetic</small></div><div class='controls js-only'><div class='tabs' role='group' aria-label='Filter by input source'><button class='tab' data-source-filter='all' aria-pressed='true'>All {len(entries)}</button><button class='tab' data-source-filter='original' aria-pressed='false'>Supplied {original}</button><button class='tab' data-source-filter='expansion' aria-pressed='false'>Extension {len(entries) - original}</button></div><label class='search'>{icon("search")}<span class='sr-only'>Search case ID or outcome</span><input id='case-search' type='search' placeholder='Search case ID or outcome' autocomplete='off'></label><label><span class='sr-only'>Filter by provisional outcome</span><select class='filter-select' id='outcome-filter'><option value=''>All outcomes</option>{options}</select></label></div><noscript><p class='no-js-note'>All records are shown. Open any report to continue.</p></noscript><div class='table-wrap'><table class='library-table'><caption class='sr-only'>Synthetic assessment report directory</caption><thead><tr><th scope='col'>Case ID</th><th scope='col'>Input source</th><th scope='col'>Overall provisional outcome</th><th scope='col'>Missing fields</th><th scope='col'><span class='sr-only'>Open report</span></th></tr></thead><tbody>{"".join(rows)}</tbody></table></div><div class='empty-state' id='empty-state' hidden><p>No matching records. Adjust the search or filters.</p><button id='clear-filters'>Clear filters</button></div><div class='list-foot'><span id='case-count' aria-live='polite'>{len(entries)} / {len(entries)} reports</span><span>Case facts → Rule evaluations → Guideline source</span></div></section><p class='editor-note'>All records are synthetic. Information marked as insufficient remains unverified and does not establish normality or abnormality. All provisional outcomes require clinician review.</p><footer class='page-end'><span>Occupational Fitness Platform</span><a href='evaluation/run_verification.json'>Report integrity checks ↗</a></footer>"""
    return page("Assessment records", nav, body, library=True)
