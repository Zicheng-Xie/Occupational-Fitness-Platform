"""Self-contained English experiment report with paired source inspection."""

import json
from html import escape


def render_comparison(rows, summary):
    accepted = sum(r["status"] == "completed" for r in rows)
    planned = summary.get("planned_runs", len(rows))
    progress = summary.get("execution_status", "partial")
    cards = []
    for row in rows:
        answer = row.get("answer", {})
        error_type = (
            "failed"
            if row["status"] != "completed"
            else "agreement"
            if row.get("reference_agreement")
            else "excess_abstention"
            if answer.get("assessment_outcome") == "insufficient_information"
            and row["reference_outcome"] != "insufficient_information"
            else "reference_mismatch"
        )
        passages = "".join(
            f"<details><summary>{escape(p['source_id'])} · § {escape(p['section'])} · PDF {p['pdf_page']}</summary>"
            f"<blockquote>{escape(p['source_text'])}</blockquote></details>"
            for p in row["input_snapshot"]["guideline_evidence"]
        )
        facts = escape(json.dumps(row["input_snapshot"]["verified_patient_facts"], indent=2))
        cards.append(
            f'<article data-case="{escape(row["case_id"])}" data-model="{escape(row["model"])}" '
            f'data-method="{row["method"]}" data-module="{row["module"]}" data-status="{row["status"]}" '
            f'data-repeat="{row["repeat"] + 1}" data-error="{error_type}">'
            f"<h3>{escape(row['case_id'])} <small>{row['method']} · repeat {row['repeat'] + 1}</small></h3>"
            f"<p>{escape(row['model'])} · {row['module']} · {row['status']}</p>"
            f"<p>Reference: <b>{row['reference_outcome']}</b><br>Proposal: <b>{answer.get('assessment_outcome', 'Unavailable')}</b></p>"
            f"<p>{escape(answer.get('explanation', row.get('error', '')))}</p>"
            f"<p>Citations: {escape(', '.join(answer.get('source_ids', []))) or 'None'}</p>"
            f"<details><summary>Original note and frozen facts</summary><blockquote>{escape(row['input_snapshot']['nurse_note'])}</blockquote><pre>{facts}</pre></details>"
            f"<h4>Evidence actually supplied to the judge</h4>{passages or '<p>No evidence supplied.</p>'}</article>"
        )
    metrics = "".join(
        f"<tr><td>{m['cohort']}</td><td>{escape(m['model'])}</td><td>{m['method']}</td>"
        f"<td>{m['accepted']}/{m['runs']}</td><td>{m['agreement_all_runs']:.1%}</td><td>{m['macro_f1']:.3f}</td>"
        f"<td>{m['excess_abstentions']}</td><td>{m['mean_seconds']:.1f}s</td></tr>"
        for m in summary["metrics"]
    )

    def select(field, title):
        values = sorted({str(r[field]) for r in rows})
        default = values[0] if values and field in {"case_id", "model"} else ""
        return (
            f'<label>{title}<select data-field="{field}"><option value="">All</option>'
            + "".join(
                f"<option{' selected' if v == default else ''}>{escape(v)}</option>" for v in values
            )
            + "</select></label>"
        )

    return """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Retrieval and judgment comparison | Occupational Fitness Platform</title>
<style>:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#f4f6f8;color:#203142;font:14px/1.6 "Segoe UI",Arial,sans-serif}
header{padding:25px 4vw;background:#203142;color:white}header p{color:#cbd5df;margin:4px 0}h1{font-size:28px;margin:0;letter-spacing:-.6px}main{max-width:1500px;margin:auto;padding:28px 4vw}h2{font-size:20px}a{color:#245d85}table{border-collapse:collapse;width:100%;background:white}td,th{text-align:left;padding:12px;border-bottom:1px solid #dce3e9}th{background:#eaf0f4;font-size:12px}section{margin-bottom:32px}.scroll{overflow:auto}.filters{display:flex;gap:14px;flex-wrap:wrap;margin:20px 0}label{font-size:12px;color:#607183}select{display:block;padding:9px;border:1px solid #ccd6df;border-radius:5px;background:white;max-width:230px}.cases{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}article{padding:22px;background:white;border:1px solid #dce3e9;border-radius:8px;overflow-wrap:anywhere}article h3{margin:0;font-size:18px}small{display:block;font-size:12px;font-weight:400;color:#5e7283}details{border-top:1px solid #e5eaf0;padding:10px 0}summary{cursor:pointer}blockquote,pre{white-space:pre-wrap;margin:12px 0;background:#f4f7fa;padding:13px;border-left:3px solid #a3b9ca;font-size:12px}article[hidden]{display:none}.notice{border-left:3px solid #b68732;padding:12px 18px;background:#fffaf0}@media(max-width:800px){.cases{grid-template-columns:1fr}}</style></head><body>
<header><p>OCCUPATIONAL FITNESS PLATFORM · EXPERIMENTAL EVALUATION</p><h1>How retrieved evidence changes fitness judgments</h1></header><main>""" + (
        f"<section><h2>Executive Summary</h2><p>Execution status: <b>{escape(progress)}</b>. {len(rows)} / {planned} calls recorded.</p><p>{accepted} of {len(rows)} recorded runs passed output and citation validation. "
        "The table reports engineering reference agreement; clinician-reviewed accuracy is unavailable.</p>"
        '<p class="notice">Results may be partial while the experiment is running. Repeated calls are not independent patients. '
        "A valid source ID does not establish that the explanation follows from that source. All explanations await independent review.</p></section>"
        '<section><h2>Method comparison</h2><div class="scroll"><table><thead><tr><th>Cohort</th><th>Judge model</th><th>Retrieval</th><th>Accepted / recorded</th><th>Reference agreement</th><th>Macro-F1</th><th>Excess abstentions</th><th>Mean runtime</th></tr></thead><tbody>'
        + metrics
        + '</tbody></table></div></section><section><h2>Compare a case across methods</h2><p>Select a case and model to inspect evidence and judgments side by side.</p><div class="filters">'
        + "".join(
            select(k, title)
            for k, title in [
                ("case_id", "Case"),
                ("model", "Judge model"),
                ("method", "Retrieval method"),
                ("module", "Disease module"),
                ("status", "Run status"),
            ]
        )
        + '<label>Repeat<select data-field="repeat"><option value="">All</option><option selected>1</option><option>2</option><option>3</option></select></label>'
        + '<label>Error category<select data-field="error"><option value="">All</option><option>failed</option><option>reference_mismatch</option><option>excess_abstention</option><option>agreement</option></select></label>'
        + '</div><div class="cases">'
        + "".join(cards)
        + "</div></section><section><h2>Audit and reproducibility</h2>"
        '<p><a href="summary.json">Metrics and paired transitions</a> · <a href="summary.csv">Summary CSV</a> · '
        '<a href="results.jsonl">Raw judgments</a> · <a href="retrieval.json">Retrieval results</a> · '
        '<a href="label_audit.json">Label audit</a> · '
        '<a href="upstream_audit.json">Upstream fact review audit</a> · '
        '<a href="error_audit.html">Paired errors and repeated-call stability</a> · '
        '<a href="disease_metrics.json">Disease metrics</a> · <a href="costs.json">Cost audit</a> · '
        '<a href="label_consistent_sensitivity.json">Label sensitivity</a> · '
        '<a href="retrieval_review.csv">Evidence review worksheet</a> · '
        '<a href="corpus.json">Frozen source corpus</a> · <a href="labels.json">Provisional labels</a> · '
        '<a href="manifest.json">Configuration manifest</a> · <a href="review_queue.json">Review queue</a></p>'
        "<p>Formal workflow and deterministic rule results are unchanged. Figure reading-order exclusions and unresolved section references are recorded in the corpus.</p></section></main>"
        '<script>function filterCases(){const filters=[...document.querySelectorAll("select")];document.querySelectorAll("article").forEach(a=>{a.hidden=filters.some(f=>f.value&&a.dataset[f.dataset.field==="case_id"?"case":f.dataset.field]!==f.value)})}document.querySelectorAll("select").forEach(s=>s.addEventListener("change",filterCases));filterCases();</script></body></html>'
    )
