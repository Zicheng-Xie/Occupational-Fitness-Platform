"""Self-contained, offline HTML views. Presentation never changes assessment data."""

from __future__ import annotations

import html
import os
from pathlib import Path
from urllib.parse import quote

from occupational_fitness_rag.provenance import digest

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

CSS = """
:root{color-scheme:light;--paper:#fff;--ground:#f7f6f3;--ink:#242a29;--muted:#67706b;--line:#e1e4de;--accent:#315c4d;--soft:#eef3ef;--serif:'Noto Serif CJK SC','Source Han Serif SC','Songti SC',SimSun,serif;--mono:ui-monospace,Consolas,monospace}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:28px}body{margin:0;background:var(--paper);color:var(--ink);font:14px/1.7 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}a{color:var(--accent);text-decoration:none;text-underline-offset:4px}a:hover{text-decoration:underline}button,input,select{font:inherit;color:inherit}button,a,input,select,summary{-webkit-tap-highlight-color:transparent}button{cursor:pointer}button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:4px}h1,h2,h3,p{margin:0}h1{font:600 31px/1.4 var(--serif);letter-spacing:.02em}h2{font-size:18px;font-weight:600}h3{font-size:15px;font-weight:600}small{font-size:12px}button{border:1px solid var(--line);background:white;padding:7px 13px;border-radius:3px}button:hover{background:var(--soft)}.skip-link{position:absolute;left:16px;top:-60px;background:white;padding:10px;z-index:10}.skip-link:focus{top:10px}
.shell{min-height:100vh;display:grid;grid-template-columns:218px minmax(0,1fr)}.rail{background:var(--ground);border-right:1px solid var(--line);padding:32px 23px;display:flex;flex-direction:column;gap:34px}.rail-inner{position:sticky;top:30px}.brand{font-size:16px;font-weight:650;letter-spacing:.04em}.brand small{display:block;font-size:11px;color:var(--muted);font-weight:400;letter-spacing:.08em;margin-top:6px}.rail-label{margin:34px 0 10px;color:var(--muted);font-size:11px;letter-spacing:.08em}.rail nav{display:grid;gap:3px}.rail nav a{padding:8px 10px;margin-left:-10px;border-radius:2px;color:#535f58;font-size:13px}.rail nav a:hover,.rail nav a[aria-current]{background:#e8ede7;color:#234b3b;text-decoration:none}.rail-foot{margin-top:40px;padding-top:19px;border-top:1px solid var(--line);font-size:11px;color:var(--muted);line-height:1.9}.content{width:100%;max-width:1220px;margin:0 auto;padding:32px 52px 48px;min-width:0}.topline{display:flex;justify-content:space-between;align-items:center;gap:16px;font-size:12px;color:var(--muted);padding-bottom:23px;border-bottom:1px solid var(--line)}.topline a{color:var(--muted)}.draft{display:inline-flex;align-items:center;gap:8px;white-space:nowrap;font-size:11px;letter-spacing:.05em}.draft:before{content:'';width:5px;height:5px;border-radius:50%;background:#967637}.page-heading{padding:32px 0 26px;display:flex;align-items:flex-start;justify-content:space-between;gap:20px}.eyebrow{color:var(--muted);font-size:11px;letter-spacing:.08em;margin-bottom:9px}.description{max-width:720px;color:var(--muted);margin-top:11px;font-size:13px}.heading-meta{font-family:var(--mono);font-size:12px;color:var(--muted);padding-top:8px;white-space:nowrap}.editor-note{font-size:12px;color:var(--muted);border-top:1px solid var(--line);padding-top:20px;margin-top:34px;line-height:1.9}.number{font-family:var(--mono);font-variant-numeric:tabular-nums}.muted{color:var(--muted)}.badge{font-size:12px;display:inline-flex;align-items:center;gap:7px;white-space:nowrap}.badge:before{content:'';width:5px;height:5px;border-radius:50%;background:currentColor;flex-shrink:0}.badge.clear{color:#315c4d}.badge.incomplete,.badge.review{color:#89632c}.badge.adverse{color:#9a4035}.micro{font:11px/1.6 var(--mono);color:var(--muted);overflow-wrap:anywhere}.section{margin-top:32px;scroll-margin-top:24px}.section-heading{display:flex;justify-content:space-between;align-items:baseline;gap:16px;border-bottom:1px solid var(--ink);padding-bottom:11px;margin-bottom:0}.section-heading small{color:var(--muted)}.section-no{display:inline-block;margin-right:12px;font:12px var(--mono);color:var(--muted)}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;text-align:left}caption{text-align:left;font-weight:600;padding:12px 0}th{font-size:11px;letter-spacing:.02em;color:var(--muted);font-weight:500;padding:12px 12px;border-bottom:1px solid var(--line);white-space:nowrap}td{border-bottom:1px solid var(--line);padding:15px 12px;vertical-align:middle}th:first-child,td:first-child{padding-left:0}th:last-child,td:last-child{padding-right:0}.library-table{min-width:620px}.library-table tr:hover td{background:#fafbf8}.case-link{font:500 13px var(--mono);color:var(--ink)}.case-link:hover{color:var(--accent)}.source-label{font-size:12px;color:var(--muted)}.entry-link{white-space:nowrap;font-size:12px}.controls{padding:17px 0;display:flex;flex-wrap:wrap;align-items:center;gap:12px;border-top:1px solid var(--ink);border-bottom:1px solid var(--line)}.tabs{display:flex;gap:4px;margin-right:auto}.tab{border:0;background:transparent;color:var(--muted);padding:6px 10px;font-size:12px;border-radius:2px}.tab[aria-pressed=true]{background:var(--soft);color:var(--accent);font-weight:600}.search{position:relative}.search input{width:218px;max-width:100%;padding:7px 10px;background:white;border:1px solid var(--line);border-radius:3px;font-size:12px}.filter-select{font-size:12px;padding:7px 8px;border:1px solid var(--line);background:white;border-radius:3px;max-width:100%}.sr-only{position:absolute;width:1px;height:1px;padding:0;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.list-foot{display:flex;justify-content:space-between;gap:18px;color:var(--muted);font-size:12px;padding-top:16px}.empty-state{padding:44px 10px;text-align:center;color:var(--muted);background:var(--ground)}[hidden]{display:none!important}.result-summary{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:24px;border-top:2px solid var(--accent);border-bottom:1px solid var(--line);padding:22px 0}.result-title{font-size:22px;font-family:var(--serif);margin:4px 0 8px}.result-title .badge{font-size:22px;gap:10px}.result-title .badge:before{width:6px;height:6px}.summary-facts{display:flex;gap:26px;align-items:center}.summary-facts div{text-align:right;font-size:11px;color:var(--muted)}.summary-facts strong{display:block;color:var(--ink);font:24px/1.5 var(--mono);font-weight:400}.module-name{font-size:13px;color:var(--ink)}.module-table{min-width:490px}.module-table td{padding-top:12px;padding-bottom:12px;font-size:12px}.review-block{padding:15px 0;border-bottom:1px solid var(--line);display:grid;grid-template-columns:104px minmax(0,1fr);gap:15px}.review-block h3{font-size:13px}.field-list{margin:0;padding:0;list-style:none;display:flex;flex-wrap:wrap;column-gap:23px;row-gap:5px;font-size:13px}.field-list li:before{content:'—';color:#a7aea6;margin-right:8px}.warning-list{margin:16px 0 0;padding:14px 18px 14px 32px;background:#fbf6ed;color:#71562d;font-size:12px;overflow-wrap:anywhere}.source-paper{background:var(--ground);padding:20px 22px;margin-top:17px;border:1px solid #e8e9e3}.source-line{display:grid;grid-template-columns:23px minmax(0,1fr);gap:14px;scroll-margin-top:30px}.line-number{font:11px/1.9 var(--mono);color:#899189;user-select:none}.line-text{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;line-height:1.9}.source-line:target{background:#e7efdf}.source-toolbar{display:flex;justify-content:space-between;gap:14px;font-size:12px;margin-top:12px;color:var(--muted)}details{border-bottom:1px solid var(--line)}summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:13px;padding:17px 0;position:relative}summary::-webkit-details-marker{display:none}summary:before{content:'+';font:16px var(--mono);color:var(--muted);width:12px;flex-shrink:0}details[open]>summary:before{content:'−'}summary .summary-main{flex:1;min-width:0}summary .summary-main strong{font-size:13px;font-weight:500;display:block;overflow-wrap:anywhere}summary .summary-main small{display:block;margin-top:3px}.summary-end{font-size:11px;color:var(--muted);white-space:nowrap}.detail-body{padding:0 0 18px 25px}.rule-group[open]>summary{border-bottom:1px solid var(--line)}.rule-group>.detail-body{padding:0 0 0 24px}.rule-entry:last-child{border-bottom:0}.rule-reason{font-size:13px;line-height:1.8;max-width:760px;margin:0 0 15px;overflow-wrap:anywhere}.fact-item{padding:11px 0;border-top:1px solid #edf0e9}.fact-line{display:flex;justify-content:space-between;align-items:baseline;gap:20px;font-size:12px}.fact-line strong{font-weight:600;overflow-wrap:anywhere}.fact-item .micro{font-size:10px;margin:3px 0}.case-quote{margin:10px 0 0;padding:8px 14px;border-left:2px solid #c6d3c7;color:#4c5650;font-size:12px;line-height:1.8;white-space:pre-wrap;overflow-wrap:anywhere}.case-quote a{display:block;font-size:10px;margin-bottom:4px}.ref-links{display:flex;gap:10px;flex-wrap:wrap;font-size:11px;margin-top:14px}.ref-links a{border-bottom:1px solid #bed0c3}.source-text{margin:12px 0 16px;border-left:2px solid #b8caba;padding:0 18px;font-size:13px;line-height:1.85;white-space:pre-wrap;overflow-wrap:anywhere;max-width:800px}.evidence-info{display:flex;align-items:center;justify-content:space-between;gap:12px;font-size:12px;color:var(--muted);flex-wrap:wrap}.technical{border:0;margin-top:14px}.technical summary{padding:5px 0;font-size:11px;color:var(--muted)}.technical pre{margin:8px 0;background:var(--ground);padding:14px;white-space:pre-wrap;overflow-wrap:anywhere;font:11px/1.7 var(--mono)}.download-list{display:flex;flex-wrap:wrap;gap:12px 22px;padding:17px 0;font-size:12px}.review-list{margin:16px 0;padding-left:20px;color:#4a554e;font-size:13px}.review-list li{padding:4px 0}.rule-tools{margin:13px 0 2px;display:flex;gap:16px}.text-button{font-size:11px;border:0;padding:0;color:var(--accent);background:transparent}.text-button:hover{background:transparent;text-decoration:underline}.page-end{margin-top:40px;padding-top:16px;border-top:1px solid var(--line);display:flex;justify-content:space-between;gap:16px;font-size:11px;color:var(--muted)}.no-js-note{padding:8px;color:var(--muted);font-size:12px}.js-only{display:none}.has-js .js-only{display:flex}.reference-state{font-size:11px;color:var(--muted);margin:9px 0 0}.source-ref{font:11px var(--mono);white-space:nowrap}
:root{--ground:#f3f5f7;--ink:#20313c;--muted:#627582;--line:#dce3e8;--accent:#23657b;--soft:#edf4f7;--serif:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
.rail{background:#182e3a;color:#e8eff3;border-right:0}.brand small,.rail-label,.rail-foot{color:#a6bbc7}.rail .muted{color:#91adbd}.rail nav a{color:#c9d8e2}.rail nav a:hover,.rail nav a[aria-current]{background:#284957;color:#fff}.rail-foot{border-top-color:#35515e}.brand{font-size:17px}h1{font-weight:600;font-size:29px}.page-heading{padding-top:27px}.topline{font-size:12px}.result-summary{border-top-color:#23657b}.section-heading{border-bottom-color:#8397a4}.library-table th{background:#f5f7f9}.library-table th:first-child,.library-table td:first-child{padding-left:12px}.library-table td{padding-top:17px;padding-bottom:17px}.tab[aria-pressed=true]{background:#e7f0f5}.source-paper{background:#f6f8fa;border-color:#e1e7ec}.source-line:target{background:#e2edf3}.ref-links a{border-bottom-color:#b7cdd9}
@media(min-width:1500px){.content{padding:40px 70px 60px}.rail{padding-top:40px}}
@media(max-width:1050px){.shell{grid-template-columns:178px minmax(0,1fr)}.rail{padding:25px 18px}.content{padding:25px 30px 40px}.summary-facts{gap:17px}.controls{gap:10px}.tabs{width:100%}}
@media(max-width:740px){.shell{display:block}.rail{padding:16px 20px;border-right:0;border-bottom:1px solid var(--line)}.rail-inner{position:static}.brand{font-size:13px}.brand small,.rail-label,.rail-foot{display:none}.rail nav{display:flex;gap:12px;overflow-x:auto;margin-top:12px}.rail nav a{font-size:12px;white-space:nowrap;margin:0;padding:5px 0}.rail nav a[aria-current]{background:none;border-bottom:1px solid var(--accent)}.content{padding:20px 20px 32px}.topline{padding-bottom:16px;font-size:11px}h1{font-size:27px}.page-heading{padding:25px 0 22px}.heading-meta{display:none}.result-summary{grid-template-columns:1fr;gap:18px}.summary-facts{justify-content:flex-start;gap:35px}.summary-facts div{text-align:left}.summary-facts strong{font-size:20px}.review-block{grid-template-columns:1fr;gap:8px}.search{flex:1}.search input{width:100%}.filter-select{max-width:160px}.section{margin-top:27px}.section-heading{gap:8px}.section-heading h2{font-size:16px}.section-no{margin-right:8px}.section-heading small{font-size:11px}.source-paper{padding:15px 12px}.source-line{gap:7px;grid-template-columns:17px 1fr}.detail-body{padding-left:18px}.rule-group>.detail-body{padding-left:15px}.summary-end{font-size:10px}.fact-line{display:block}.fact-line strong{display:block;margin-top:4px}.page-end{display:block}.page-end span{display:block}.library-table{min-width:600px}.list-foot{flex-wrap:wrap}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media print{@page{margin:18mm}body{font-size:10pt;background:white}.shell{display:block}.rail,.topline,.js-only,.controls,.rule-tools,.source-toolbar button,.page-end a{display:none!important}.content{max-width:none;padding:0}.page-heading{padding-top:0}h1{font-size:24pt}.section{break-before:auto}.section-heading,summary{break-after:avoid}.result-summary{break-inside:avoid}.table-wrap{overflow:visible}table{min-width:0!important}th,td{padding:9px 7px}a{color:inherit}.source-paper{background:white}.detail-body{padding-bottom:12px}.source-text{font-size:10pt}.rail-foot{display:none}.section-heading{border-bottom:1px solid #666}.editor-note{font-size:9pt}.technical pre{font-size:8pt}.source-line{break-inside:avoid}.page-end{font-size:8pt}}
"""

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


def page(title, navigation, body, *, library=False):
    nav_items = []
    for label, url, current in navigation:
        selected = " aria-current='page'" if current else ""
        nav_items.append(f"<a href='{esc(url)}'{selected}>{esc(label)}</a>")
    nav = "".join(nav_items)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} · Occupational Fitness</title><style>{CSS}</style></head>
<body><a class="skip-link" href="#main">Skip to content</a><div class="shell"><aside class="rail"><div class="rail-inner"><div class="brand">OF <span class="muted">/</span> Fitness Review<small>OCCUPATIONAL FITNESS</small></div><p class="rail-label">{"ASSESSMENTS" if library else "THIS REPORT"}</p><nav aria-label="{"Assessment navigation" if library else "Report navigation"}">{nav}</nav><div class="rail-foot">Commercial driving · Occupational health<br>Austroads · AP-G56-22<br>REVIEW PENDING / DRAFT</div></div></aside><main class="content" id="main">{body}</main></div><script type="text/javascript">{SCRIPT}</script></body></html>"""


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
        f"<div class='topline'><a href='{esc(back)}'>← Assessment records</a><span class='draft'>DRAFT / Clinical review pending</span></div><header class='page-heading'><div><p class='eyebrow'>COMMERCIAL DRIVER FITNESS · REVIEW REPORT</p><h1>{esc(case.case_id)}</h1><p class='description'>Review case facts, rule evaluations and linked guideline evidence.</p></div><span class='heading-meta'>AP-G56-22<br>Assessment records</span></header>"
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
        warnings = [warning.message for warning in result.processing_warnings] + [
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
    nav = [
        ("Assessment records", "#main", True),
        ("Project guide", "../README.md", False),
        ("Architecture", "../docs/architecture.md", False),
        ("Verification", "../docs/verification.md", False),
    ]
    body = f"""<div class='topline'><span>Assessments / Assessment records</span><span class='draft'>DRAFT / Review pending</span></div><header class='page-heading'><div><p class='eyebrow'>ASSESSMENT RECORDS</p><h1>Assessment records</h1><p class='description'>{len(entries)} synthetic assessment records covering hypertension, vision, hearing, blackout and diabetes.<br>Select a record to review its provisional outcome, missing information and source evidence.</p></div><span class='heading-meta'>AP-G56-22<br>Commercial driver fitness</span></header><div class='controls js-only'><div class='tabs' role='group' aria-label='Filter by input source'><button class='tab' data-source-filter='all' aria-pressed='true'>All {len(entries)}</button><button class='tab' data-source-filter='original' aria-pressed='false'>Supplied {original}</button><button class='tab' data-source-filter='expansion' aria-pressed='false'>Extension {len(entries) - original}</button></div><label class='search'><span class='sr-only'>Search case ID or outcome</span><input id='case-search' type='search' placeholder='Search case ID or outcome' autocomplete='off'></label><label><span class='sr-only'>Filter by provisional outcome</span><select class='filter-select' id='outcome-filter'><option value=''>All outcomes</option>{options}</select></label></div><noscript><p class='no-js-note'>All records are shown. Open any report to continue.</p></noscript><div class='table-wrap'><table class='library-table'><caption class='sr-only'>Synthetic assessment report directory</caption><thead><tr><th scope='col'>Case ID</th><th scope='col'>Input source</th><th scope='col'>Overall provisional outcome</th><th scope='col'>Missing fields</th><th scope='col'><span class='sr-only'>Open report</span></th></tr></thead><tbody>{"".join(rows)}</tbody></table></div><p class='empty-state' id='empty-state' hidden>No matching records. Adjust the search or filters.</p><div class='list-foot'><span id='case-count' aria-live='polite'>{len(entries)} / {len(entries)} reports</span><span>Case facts → Rule evaluations → Guideline source</span></div><p class='editor-note'>All records are synthetic. Information marked as insufficient remains unverified and does not establish normality or abnormality. All provisional outcomes require clinician review.</p><footer class='page-end'><span>Occupational Fitness Platform</span><a href='evaluation/run_verification.json'>Report integrity checks ↗</a></footer>"""
    return page("Assessment records", nav, body, library=True)
