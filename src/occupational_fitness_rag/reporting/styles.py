"""Shared visual tokens and responsive styles for offline assessment views."""

CSS = """
:root {
  color-scheme: light;
  --paper: #fff;
  --ground: #f7f8fa;
  --ink: #20252d;
  --muted: #626b78;
  --line: #e5e8ed;
  --accent: #275e83;
  --soft: #edf4f8;
  --mono: ui-monospace, 'Cascadia Code', Consolas, monospace;
  --shadow: 0 2px 5px #18263904, 0 12px 30px #18263903;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; scroll-padding-top: 28px; }
body { margin: 0; background: var(--ground); color: var(--ink); font: 14px/1.65 -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; -webkit-font-smoothing: antialiased; }
a { color: var(--accent); text-decoration: none; text-underline-offset: 4px; }
a:hover { text-decoration: underline; }
button, input, select { font: inherit; color: inherit; }
button, a, input, select, summary { -webkit-tap-highlight-color: transparent; }
button { cursor: pointer; border: 1px solid var(--line); background: white; padding: 8px 13px; border-radius: 8px; }
button:hover { background: var(--ground); border-color: #b9c4d0; }
:where(button, a, input, select, summary):focus-visible { outline: 3px solid #6295b6; outline-offset: 3px; }
h1, h2, h3, p { margin: 0; }
h1 { font-size: 32px; font-weight: 650; line-height: 1.25; letter-spacing: -.9px; }
h2 { font-size: 17px; font-weight: 650; letter-spacing: -.25px; }
h3 { font-size: 14px; font-weight: 600; }
small { font-size: 12px; }
[hidden] { display: none !important; }
.icon { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 1.6; stroke-linecap: round; stroke-linejoin: round; flex-shrink: 0; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
.skip-link { position: absolute; left: 16px; top: -70px; background: white; padding: 10px; z-index: 20; }
.skip-link:focus { top: 10px; }
.shell { min-height: 100vh; display: grid; grid-template-columns: 248px minmax(0,1fr); }
.rail { background: #fff; border-right: 1px solid var(--line); padding: 28px 18px; }
.rail-inner { position: sticky; top: 28px; display: flex; flex-direction: column; min-height: calc(100vh - 56px); }
.brand { display: flex; align-items: center; gap: 11px; padding: 0 8px; font-size: 14px; font-weight: 650; line-height: 1.4; }
.brand-mark { display: grid; place-items: center; width: 36px; height: 36px; border-radius: 10px; background: #253747; color: white; flex-shrink: 0; }
.brand small { display: block; font-size: 11px; color: var(--muted); font-weight: 400; margin-top: 2px; }
.rail-label { margin: 38px 12px 12px; color: #767f8b; font-size: 10px; font-weight: 600; letter-spacing: 1.1px; }
.rail nav { display: grid; gap: 5px; }
.rail nav a { display: flex; align-items: center; gap: 11px; padding: 11px 12px; border-radius: 9px; color: #5a6572; font-size: 12px; transition: background .15s, color .15s; }
.rail nav a:hover { background: var(--ground); color: var(--ink); text-decoration: none; }
.rail nav a[aria-current] { background: #edf2f6; color: #244b69; font-weight: 600; }
.rail-foot { margin-top: auto; padding: 48px 10px 4px; font-size: 11px; color: var(--muted); line-height: 1.9; }
.rail-foot strong { display: block; color: var(--ink); font-weight: 500; margin-bottom: 3px; }
.content { width: 100%; max-width: 1320px; margin: 0 auto; padding: 25px 44px 40px; min-width: 0; }
.topline { display: flex; justify-content: space-between; align-items: center; gap: 16px; font-size: 12px; color: var(--muted); padding-bottom: 22px; border-bottom: 1px solid var(--line); }
.topline a { color: var(--muted); }
.top-actions { display: flex; align-items: center; gap: 14px; }
.print-button { display: inline-flex; align-items: center; gap: 8px; font-size: 12px; padding: 7px 11px; }
.draft { display: inline-flex; align-items: center; gap: 7px; font-size: 10px; white-space: nowrap; }
.draft:before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: #a47830; }
.page-heading { padding: 32px 0 27px; display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; }
.eyebrow { color: var(--muted); font-size: 10px; font-weight: 600; letter-spacing: 1px; margin-bottom: 10px; }
.description { max-width: 640px; color: var(--muted); margin-top: 12px; font-size: 13px; }
.heading-meta { font-size: 11px; color: var(--muted); text-align: right; padding-top: 8px; white-space: nowrap; }
.number { font-family: var(--mono); font-variant-numeric: tabular-nums; }
.muted { color: var(--muted); }
.micro { font: 11px/1.7 var(--mono); color: var(--muted); overflow-wrap: anywhere; }
.metric-grid { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 16px; margin-bottom: 26px; }
.metric { background: white; border: 1px solid var(--line); border-radius: 12px; padding: 18px 22px; box-shadow: var(--shadow); }
.metric-label { display: flex; justify-content: space-between; align-items: center; color: var(--muted); font-size: 12px; }
.metric strong { display: block; font-size: 28px; letter-spacing: -.8px; line-height: 1.3; margin: 9px 0 4px; font-weight: 600; font-variant-numeric: tabular-nums; }
.metric small { color: var(--muted); font-size: 11px; }
.library-panel { background: white; border: 1px solid var(--line); border-radius: 13px; box-shadow: var(--shadow); overflow: hidden; }
.panel-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 20px 22px 0; }
.panel-heading small { color: var(--muted); font-size: 11px; }
.controls { padding: 17px 22px; display: flex; flex-wrap: wrap; align-items: center; gap: 12px; border-bottom: 1px solid var(--line); }
.tabs { display: flex; padding: 3px; gap: 2px; background: #f2f4f7; border-radius: 9px; margin-right: auto; }
.tab { border: 1px solid transparent; background: transparent; color: var(--muted); padding: 5px 11px; font-size: 12px; border-radius: 7px; }
.tab[aria-pressed=true] { border-color: #e0e4e9; background: white; color: var(--ink); box-shadow: 0 1px 3px #1526380a; font-weight: 600; }
.search { position: relative; display: flex; align-items: center; }
.search .icon { position: absolute; left: 11px; width: 15px; height: 15px; color: var(--muted); pointer-events: none; }
.search input { width: 230px; max-width: 100%; padding: 8px 10px 8px 34px; background: white; border: 1px solid var(--line); border-radius: 8px; font-size: 12px; }
.filter-select { font-size: 12px; padding: 8px 10px; border: 1px solid var(--line); background: white; border-radius: 8px; max-width: 210px; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; text-align: left; }
caption { text-align: left; font-weight: 600; padding: 12px 0; }
th { font-size: 11px; color: var(--muted); font-weight: 500; padding: 12px 18px; border-bottom: 1px solid var(--line); white-space: nowrap; background: #fafbfc; }
td { border-bottom: 1px solid var(--line); padding: 17px 18px; vertical-align: middle; font-size: 12px; }
tr:last-child td { border-bottom: 0; }
th:first-child, td:first-child { padding-left: 22px; }
th:last-child, td:last-child { padding-right: 22px; }
.library-table { min-width: 680px; }
.library-table tr:hover td { background: #f8fafc; }
.case-link { font: 600 12px var(--mono); color: var(--ink); }
.case-link:hover { color: var(--accent); }
.source-label { font-size: 11px; color: var(--muted); }
.entry-link { display: inline-flex; white-space: nowrap; font-size: 11px; padding: 5px 9px; border: 1px solid var(--line); border-radius: 6px; color: #4b5866; background: white; }
.entry-link:hover { color: var(--accent); border-color: #b7c7d4; text-decoration: none; }
.badge { font-size: 11px; display: inline-flex; align-items: center; gap: 7px; border-radius: 6px; padding: 4px 8px; line-height: 1.45; background: #f2f4f7; }
.badge:before { content: ''; width: 5px; height: 5px; border-radius: 50%; background: currentColor; flex-shrink: 0; }
.badge.clear { color: #25634a; background: #edf6f0; }
.badge.review { color: #795b22; background: #fcf5e7; }
.badge.incomplete { color: #596575; background: #f0f2f5; }
.badge.adverse { color: #a34540; background: #fcefee; }
.list-foot { display: flex; justify-content: space-between; gap: 18px; color: var(--muted); font-size: 11px; padding: 15px 22px; border-top: 1px solid var(--line); }
.empty-state { padding: 44px 16px; text-align: center; color: var(--muted); }
.empty-state button { margin-top: 12px; }
.editor-note { font-size: 11px; color: var(--muted); padding: 0 2px; margin-top: 22px; line-height: 1.9; max-width: 900px; }
#overview { margin-top: 20px; padding: 0; background: white; border: 1px solid var(--line); border-radius: 13px; box-shadow: var(--shadow); overflow: hidden; }
#overview>.reference-state { padding: 13px 22px; margin: 0; border-top: 1px solid var(--line); background: #fbfcfd; }
.result-summary { display: grid; grid-template-columns: minmax(0,1fr) auto; align-items: center; gap: 28px; padding: 24px; border-bottom: 1px solid var(--line); }
.result-title { margin: 4px 0 10px; }
.result-title .badge { font-size: 21px; font-weight: 600; letter-spacing: -.4px; background: none; padding: 0; }
.result-title .badge:before { width: 7px; height: 7px; }
.result-summary .muted { font-size: 12px; max-width: 470px; }
.summary-facts { display: flex; gap: 20px; align-items: center; }
.summary-facts div { text-align: center; font-size: 10px; color: var(--muted); padding-left: 20px; border-left: 1px solid var(--line); }
.summary-facts strong { display: block; color: var(--ink); font-size: 26px; font-weight: 500; line-height: 1.5; font-variant-numeric: tabular-nums; }
.module-table { min-width: 550px; }
.module-name { font-size: 12px; font-weight: 600; color: var(--ink); }
.section { margin-top: 24px; padding: 22px 24px; background: white; border: 1px solid var(--line); border-radius: 13px; scroll-margin-top: 24px; box-shadow: var(--shadow); }
.section-heading { display: flex; justify-content: space-between; align-items: baseline; gap: 16px; padding-bottom: 17px; border-bottom: 1px solid var(--line); }
.section-heading small { color: var(--muted); font-size: 11px; }
.section-no { display: inline-grid; place-items: center; margin-right: 10px; width: 25px; height: 25px; background: #f2f5f8; border-radius: 6px; font: 10px var(--mono); color: var(--muted); vertical-align: middle; }
.review-block { padding: 18px 0; border-bottom: 1px solid var(--line); display: grid; grid-template-columns: 116px minmax(0,1fr); gap: 16px; }
.review-block h3 { font-size: 12px; padding-top: 4px; }
.field-list { margin: 0; padding: 0; list-style: none; display: flex; flex-wrap: wrap; gap: 7px; font-size: 12px; }
.field-list li { background: #f7f8fa; border: 1px solid #edf0f3; padding: 3px 9px; border-radius: 6px; }
.warning-list { margin: 17px 0; padding: 14px 18px 14px 32px; background: #fcf6eb; color: #76571f; border-radius: 8px; font-size: 12px; overflow-wrap: anywhere; }
.review-list { margin: 16px 0; padding-left: 20px; color: #56616e; font-size: 12px; }
.review-list li { padding: 4px 0; }
.source-paper { background: #fafbfc; padding: 20px; margin-top: 18px; border: 1px solid var(--line); border-radius: 9px; }
.source-line { display: grid; grid-template-columns: 25px minmax(0,1fr); gap: 14px; scroll-margin-top: 30px; border-radius: 3px; }
.line-number { font: 11px/1.95 var(--mono); color: #747f8c; user-select: none; }
.line-text { white-space: pre-wrap; overflow-wrap: anywhere; font: 12px/1.8 var(--mono); }
.source-line:target { background: #e5f0f8; outline: 2px solid #b0cfdf; }
.source-toolbar { display: flex; justify-content: space-between; gap: 14px; font-size: 11px; margin-top: 12px; color: var(--muted); overflow-wrap: anywhere; }
details { border-bottom: 1px solid var(--line); }
summary { list-style: none; cursor: pointer; display: flex; align-items: center; gap: 13px; padding: 17px 0; position: relative; }
summary::-webkit-details-marker { display: none; }
summary:before { content: ''; width: 6px; height: 6px; border-right: 1.5px solid #75808c; border-bottom: 1.5px solid #75808c; transform: rotate(-45deg); margin: 0 3px; flex-shrink: 0; transition: transform .15s; }
details[open]>summary:before { transform: rotate(45deg); }
summary:hover .summary-main strong { color: var(--accent); }
.summary-main { flex: 1; min-width: 0; }
.summary-main strong { font-size: 13px; font-weight: 500; display: block; overflow-wrap: anywhere; }
.summary-main small { display: block; margin-top: 3px; }
.summary-end { font-size: 10px; color: var(--muted); flex-shrink: 0; max-width: 40%; text-align: right; }
.detail-body { padding: 0 0 18px 25px; }
.rule-group { border: 1px solid var(--line); border-radius: 9px; margin-top: 10px; }
.rule-group>summary { padding: 15px; }
.rule-group[open]>summary { background: #f8fafc; border-radius: 9px 9px 0 0; border-bottom: 1px solid var(--line); }
.rule-group>.detail-body { padding: 0 18px; }
.rule-entry:last-child { border-bottom: 0; }
.rule-reason { font-size: 13px; line-height: 1.8; margin: 12px 0 15px; overflow-wrap: anywhere; }
.fact-item { padding: 13px 0; border-top: 1px solid var(--line); }
.fact-line { display: flex; justify-content: space-between; align-items: baseline; gap: 20px; font-size: 12px; }
.fact-line strong { font-weight: 600; overflow-wrap: anywhere; }
.fact-item .micro { font-size: 10px; margin: 3px 0; }
.case-quote { margin: 10px 0 0; padding: 10px 14px; border-left: 2px solid #b4ccdd; background: #f7fafd; color: #505f6c; font-size: 12px; line-height: 1.8; white-space: pre-wrap; overflow-wrap: anywhere; border-radius: 0 6px 6px 0; }
.case-quote a { display: block; font-size: 10px; margin-bottom: 5px; }
.ref-links { display: flex; gap: 8px; flex-wrap: wrap; font-size: 11px; margin-top: 14px; }
.ref-links a { background: var(--soft); padding: 4px 9px; border-radius: 5px; }
.source-text { margin: 15px 0; border-left: 2px solid #b4ccdd; padding: 2px 18px; font-size: 13px; line-height: 1.85; white-space: pre-wrap; overflow-wrap: anywhere; }
.evidence-info { display: flex; align-items: center; justify-content: space-between; gap: 12px; font-size: 11px; color: var(--muted); flex-wrap: wrap; }
.source-ref { display: grid; place-items: center; font: 11px var(--mono); background: var(--soft); color: var(--accent); width: 28px; height: 28px; border-radius: 7px; flex-shrink: 0; }
.technical { border: 0; margin-top: 14px; }
.technical summary { padding: 6px 0; font-size: 11px; color: var(--muted); }
.technical pre { margin: 8px 0; background: var(--ground); padding: 14px; border-radius: 8px; white-space: pre-wrap; overflow-wrap: anywhere; font: 11px/1.7 var(--mono); }
.download-list { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 10px; padding-top: 18px; font-size: 12px; }
.download-list a { padding: 12px; border: 1px solid var(--line); border-radius: 8px; color: #4a5b6b; }
.download-list a:hover { background: var(--soft); border-color: #b8cddd; text-decoration: none; }
.rule-tools { margin: 14px 0; display: flex; gap: 8px; }
.text-button { font-size: 11px; padding: 5px 10px; color: var(--muted); }
.page-end { margin-top: 30px; padding-top: 18px; border-top: 1px solid var(--line); display: flex; justify-content: space-between; gap: 16px; font-size: 11px; color: var(--muted); }
.no-js-note { padding: 12px 22px; color: var(--muted); font-size: 12px; }
.js-only { display: none; }
.has-js .js-only { display: flex; }
.reference-state { font-size: 11px; color: var(--muted); margin-top: 10px; }
@media (min-width: 1600px) { .content { padding: 30px 56px 48px; } }
@media (max-width: 1200px) {
  .shell { grid-template-columns: 215px minmax(0,1fr); }
  .content { padding: 24px 28px 36px; }
  .result-summary { grid-template-columns: 1fr; }
  .summary-facts { justify-content: flex-start; }
  .summary-facts div { text-align: left; }
  .summary-facts div:first-child { padding-left: 0; border: 0; }
  .tabs { width: 100%; margin-right: 0; }
  .download-list { grid-template-columns: repeat(2,minmax(0,1fr)); }
}
@media (max-width: 760px) {
  .shell { display: block; }
  .rail { padding: 16px; border-right: 0; border-bottom: 1px solid var(--line); }
  .rail-inner { position: static; min-height: 0; }
  .brand { font-size: 13px; }
  .brand-mark { width: 30px; height: 30px; border-radius: 8px; }
  .brand small, .rail-label, .rail-foot { display: none; }
  .rail nav { display: flex; gap: 5px; overflow-x: auto; margin-top: 14px; }
  .rail nav a { font-size: 11px; white-space: nowrap; padding: 8px 10px; gap: 7px; }
  .rail nav .icon { width: 15px; height: 15px; }
  .content { padding: 18px 16px 28px; }
  .topline { font-size: 11px; padding-bottom: 16px; flex-wrap: wrap; gap: 10px; }
  .top-actions { gap: 10px; }
  .draft { font-size: 9px; }
  h1 { font-size: 27px; }
  .page-heading { padding: 24px 0; }
  .heading-meta { display: none; }
  .metric-grid { gap: 8px; margin-bottom: 18px; }
  .metric { padding: 12px; }
  .metric-label { font-size: 10px; }
  .metric-label .icon { display: none; }
  .metric strong { font-size: 24px; }
  .metric small { font-size: 10px; line-height: 1.5; display: block; }
  .panel-heading { padding: 16px 14px 0; }
  .panel-heading small { display: none; }
  .controls { padding: 14px; gap: 10px; }
  .search, .search input { width: 100%; }
  .filter-select { max-width: 100%; }
  .result-summary { padding: 18px; gap: 18px; }
  .result-title .badge { font-size: 19px; }
  .summary-facts { gap: 12px; }
  .summary-facts div { padding-left: 12px; font-size: 9px; }
  .summary-facts strong { font-size: 22px; }
  .section { padding: 18px 16px; margin-top: 18px; }
  .section-heading { gap: 8px; flex-wrap: wrap; }
  .section-heading h2 { font-size: 15px; }
  .section-heading small { font-size: 10px; }
  .review-block { grid-template-columns: 1fr; gap: 10px; }
  .source-paper { padding: 12px 10px; }
  .source-line { gap: 8px; grid-template-columns: 18px minmax(0,1fr); }
  .line-text { font-size: 11px; }
  .source-toolbar, .fact-line { display: block; }
  .source-toolbar a { display: block; margin-top: 5px; }
  .fact-line strong { display: block; margin-top: 5px; }
  .rule-group>.detail-body { padding: 0 10px; }
  .detail-body { padding-left: 12px; }
  .summary-end { font-size: 9px; max-width: 34%; }
  .list-foot, .page-end { flex-wrap: wrap; font-size: 10px; }
  .list-foot { padding: 14px; gap: 8px; }
  .download-list { gap: 8px; font-size: 11px; }
}
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  *, *:before, *:after { transition: none !important; }
}
@media print {
  @page { margin: 17mm; }
  body { background: white; font-size: 10pt; color: #222; }
  .shell { display: block; }
  .rail, .topline, .js-only, .controls, .rule-tools, .page-end a { display: none !important; }
  .content { max-width: none; padding: 0; }
  .page-heading { padding-top: 0; }
  h1 { font-size: 24pt; }
  .section, #overview, .library-panel, .metric { box-shadow: none; border-radius: 0; }
  .section { padding: 14px 0; border: 0; margin-top: 18px; }
  .section-heading, summary { break-after: avoid; }
  .result-summary, .metric, .source-line { break-inside: avoid; }
  .result-summary { grid-template-columns: 1fr; }
  .table-wrap { overflow: visible; }
  table { min-width: 0 !important; table-layout: fixed; }
  th, td { padding: 9px 7px !important; font-size: 9pt; overflow-wrap: anywhere; white-space: normal; }
  a { color: inherit; }
  .source-paper, .case-quote { background: white; }
  .source-text { font-size: 10pt; }
  .technical pre { font-size: 8pt; }
  .page-end, .editor-note { font-size: 8pt; }
}
"""
