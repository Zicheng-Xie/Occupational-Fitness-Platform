"""Pair actual judgments to distinguish retrieval and case-allocation effects."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter
from html import escape
from pathlib import Path

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.evaluation.passage_comparison import read_records
from occupational_fitness_rag.provenance import digest, write_json
from tools.run_frozen_retrieval_judgments import (
    accept_completion,
    key,
    prepare_inputs,
    scoring,
    verify_files,
)

PAIRS = {
    "retrieval_seventh": ("hybrid", "seventh_round_robin"),
    "retrieval_ninth": ("hybrid", "ninth_round_robin"),
    "allocation_seventh": ("seventh_round_robin", "seventh_case_coverage"),
    "allocation_ninth": ("ninth_round_robin", "ninth_case_coverage"),
    "combined_seventh": ("hybrid", "seventh_case_coverage"),
    "combined_ninth": ("hybrid", "ninth_case_coverage"),
}


def paired_effects(rows, labels):
    index = {key(r): r for r in rows}
    if len(index) != len(rows):
        raise ValueError("A condition cannot have duplicated observations")
    result = []
    for case, model, repeat in sorted({(r["case_id"], r["model"], r["repeat"]) for r in rows}):
        for pair, (left, right) in PAIRS.items():
            a, b = [index.get((case, method, model, repeat)) for method in (left, right)]
            expected = labels[case]["reference_outcome"]
            before, after = [
                r.get("answer", {}).get("assessment_outcome") if r else None for r in (a, b)
            ]
            if a is None or b is None:
                change = "pending_pair"
            elif a["status"] != "completed" or b["status"] != "completed":
                change = "run_or_contract_failure"
            elif before == after:
                change = "unchanged_correct" if before == expected else "unchanged_wrong"
            elif before != expected and after == expected:
                change = "wrong_to_correct"
            elif before == expected:
                change = "correct_to_wrong"
            else:
                change = "wrong_to_different_wrong"
            same = bool(a and b and a["request_identity"] == b["request_identity"])
            result.append(
                {
                    "case_id": case,
                    "model": model,
                    "repeat": repeat,
                    "pair": pair,
                    "left": left,
                    "right": right,
                    "change": change,
                    "before": before,
                    "after": after,
                    "reference_outcome": expected,
                    "same_request": same,
                    "identical_input_variation": same
                    and before is not None
                    and after is not None
                    and before != after,
                }
            )
    return result


def build(root, preparation, run, output):
    root, preparation, run, output = map(
        lambda p: Path(p).resolve(), (root, preparation, run, output)
    )
    if output.exists() or not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Use a fresh report; preserve earlier measurements")
    config, manifest, pins, _, payloads, requests, conditions = prepare_inputs(preparation)
    run_pins = verify_files(run)
    plan = json.loads((run / "plan.json").read_bytes())
    if plan["preparation_identity"] != manifest["identity"]:
        raise ValueError("Run and preparation differ")
    expected = {key(c): c for c in conditions}
    rows = read_records(run / "results.jsonl")
    for row in rows:
        if (
            key(row) not in expected
            or row["experiment_identity"] != plan["identity"]
            or row["request_identity"] != expected[key(row)]["request_identity"]
        ):
            raise ValueError("A retained observation differs from its exact planned request")
        if row["status"] == "completed":
            body = requests[row["request_identity"]]
            answer = accept_completion(
                row["raw_response"],
                json.loads(body["messages"][1]["content"]),
                row["method"],
                config,
            )
            if answer.model_dump(mode="json") != row["answer"]:
                raise ValueError("Accepted answer differs from the actual retained response")
    labels = json.loads((preparation / "scoring_labels.json").read_bytes())
    metrics, pairs = scoring(rows, labels), paired_effects(rows, labels)
    counts = []
    for model in config["models"]:
        for name in PAIRS:
            group = [p for p in pairs if p["pair"] == name and p["model"] == model]
            counts.append(
                {
                    "model": model,
                    "pair": name,
                    "counts": dict(Counter(p["change"] for p in group)),
                    "identical_request_variations": sum(
                        p["identical_input_variation"] for p in group
                    ),
                }
            )
    full = root / "outputs/experiments/case_allocation_judgment_preparation_v1"
    full_pins = verify_files(full)
    allocation = json.loads((full / "summary.json").read_bytes())
    coverage_rows = json.loads((full / "packet_coverage.json").read_bytes())
    coverage_index = {(r["case_id"], r["module"], r["method"]): r for r in coverage_rows}
    allocation_changes = []
    for r in coverage_rows:
        if r["method"].endswith("case_coverage") and r["coverage"] is not None:
            old = coverage_index[
                (r["case_id"], r["module"], r["method"].replace("case_coverage", "round_robin"))
            ]
            if old["coverage"] != r["coverage"]:
                allocation_changes.append(
                    {
                        "case_id": r["case_id"],
                        "module": r["module"],
                        "method": r["method"],
                        "before": old["coverage"],
                        "after": r["coverage"],
                    }
                )
    phase = manifest["phase"]
    summary = {
        "phase": phase,
        "cases": len(labels),
        "planned": len(conditions),
        "recorded": len(rows),
        "complete": len(rows) == len(conditions),
        "metrics": metrics,
        "pairs": counts,
        "allocation_all33": allocation,
        "allocation_coverage_changes_all33": allocation_changes,
        "actual_calls": len(rows),
        "total_seconds": sum(r["seconds"] for r in rows),
        "failure_count": sum(r["status"] != "completed" for r in rows),
        "clinical_review": "pending",
        "production_change": False,
        "interpretation": "Observed engineering references, not clinical accuracy. Mechanism-pilot cases are selected development fixtures, not a generalization estimate.",
    }
    output.mkdir(parents=True)
    for name, value in (
        ("summary.json", summary),
        ("paired_changes.json", pairs),
        ("payloads.json", payloads),
        ("scoring_labels.json", labels),
    ):
        write_json(output / name, value)
    shutil.copy2(run / "results.jsonl", output / "results.jsonl")
    shutil.copy2(
        root / config["retrieval_report"] / "evidence_guide.pdf", output / "evidence_guide.pdf"
    )
    with (output / "metrics.csv").open("w", encoding="utf-8", newline="") as stream:
        fields = [k for k in metrics[0] if k != "confusion_matrix_accepted"] if metrics else []
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(metrics)
    write_json(
        output / "support_review_queue.json",
        [
            {
                **{k: r[k] for k in ("case_id", "model", "method", "repeat", "status")},
                "status_of_explanation_support": "pending_independent_review",
                "source_ids": r.get("answer", {}).get("source_ids", []),
                "fact_fields": r.get("answer", {}).get("fact_fields", []),
            }
            for r in rows
        ],
    )
    render(output, summary, rows, pairs, payloads, labels)
    data = {
        "kind": "paired_case_allocation_judgment_report",
        "preparation_identity": manifest["identity"],
        "preparation_artifacts": pins,
        "run_artifacts": run_pins,
        "run_identity": plan["identity"],
        "full_allocation_artifacts": full_pins,
        "reporter_sha256": file_hash(__file__),
        "reference_labels_never_sent_to_models": True,
    }
    write_json(
        output / "manifest.json", {**data, "identity": digest(data), "production_change": False}
    )
    (output / "reporter_source.py").write_bytes(Path(__file__).read_bytes())
    write_json(
        output / "artifacts.json", {p.name: file_hash(p) for p in output.iterdir() if p.is_file()}
    )
    return summary


def render(output, summary, rows, pairs, payloads, labels):
    table = "".join(
        f"<tr><td>{escape(m['model'])}</td><td>{escape(m['method'])}</td><td>{m['accepted']}/{m['recorded']}</td><td>{m['engineering_reference_agreement_all_recorded']:.2%}</td><td>{m['macro_f1_over_observed_classes_accepted']:.3f}</td><td>{m['insufficient_predictions_against_other_reference']}</td></tr>"
        for m in summary["metrics"]
    )
    allocation = "".join(
        f"<tr><td>{escape(m['method'])}</td><td>{m['packet_coverage']:.2%}</td></tr>"
        for m in summary["allocation_all33"]["metrics"]
    )
    html = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Evidence allocation and judgment | Occupational Fitness Platform</title><style>body{font:14px/1.65 Arial,sans-serif;color:#23394a;background:#f4f6f8;margin:0}main{max-width:1220px;margin:32px auto;padding:0 24px}section{background:white;border:1px solid #dce4ea;border-radius:8px;padding:26px;margin:18px 0}h1{font-size:28px}h2{font-size:19px}th,td{text-align:left;padding:10px;border-bottom:1px solid #e2e8ee}table{width:100%;border-collapse:collapse}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f8fa;padding:12px}select{padding:8px;margin:6px;max-width:95%}.compare{display:grid;grid-template-columns:1fr 1fr;gap:20px}.panel{min-width:0;border:1px solid #dce4ea;padding:18px}summary{cursor:pointer;padding:8px 0}.notice{background:#f9f3e5;padding:14px;border-left:4px solid #af7d27}a{color:#235f89}@media(max-width:850px){.compare{grid-template-columns:1fr}}</style><main><section><small>OCCUPATIONAL FITNESS PLATFORM · EXPERIMENTAL VALIDATION</small><h1>Does better evidence allocation improve judgment?</h1>"""
    html += f"<p>{summary['cases']} cases · {summary['recorded']}/{summary['planned']} actual conditions · Phase: {escape(summary['phase'])}</p>"
    scope = (
        "The mechanism pilot uses five previously observed fixtures selected to test implementation and known allocation problems; it is not the complete 33-case comparison."
        if summary["phase"] == "mechanism_pilot"
        else "The full comparison uses 33 previously observed development cases, two models and three independent calls per arm. Pending calls are not completed comparisons."
    )
    html += (
        '<p class="notice">Engineering reference agreement, not clinical accuracy. '
        + scope
        + " Facts, models, prompt, seed and original evidence budgets are fixed. Identifier validity does not establish explanation support. Retained guideline layout and applicability review remain pending.</p></section>"
    )
    html += (
        "<section><h2>Actual case-packet coverage: all 33 development cases</h2><p>Same 45 labeled module scopes; at most five whole originals and 9,000 evidence bytes. This table measures evidence coverage, separately from the judgment sample below.</p><table><tr><th>Evidence arm</th><th>Packet coverage</th></tr>"
        + allocation
        + "</table><details><summary>Every labeled module coverage change</summary><pre>"
        + escape(json.dumps(summary["allocation_coverage_changes_all33"], indent=2))
        + "</pre></details><p>The two seventh-route packet gains concern VAL-MIX-02 and VAL-MIX-06. They are included in the full comparison, not the five-case mechanism pilot.</p></section>"
    )
    html += (
        "<section><h2>Observed judgment results</h2><p>Failures remain in the agreement denominator. Macro-F1 is calculated over observed classes among accepted answers; three repeated calls are not three independent patients.</p><table><tr><th>Model</th><th>Arm</th><th>Accepted</th><th>Reference agreement</th><th>Macro-F1</th><th>Excess abstentions</th></tr>"
        + table
        + "</table><details><summary>Paired effects and identical-input variation</summary><pre>"
        + escape(json.dumps(summary["pairs"], indent=2))
        + "</pre></details></section>"
    )
    html += '<section><h2>Inspect the same case before and after</h2><label>Case<select id="case"></select></label><label>Model<select id="model"></select></label><label>Repeat<select id="repeat"></select></label><label>Comparison<select id="pair"></select></label><p id="status"></p><div id="comparison"></div></section>'
    html += '<section><h2>Audit files</h2><p><a href="metrics.csv">Metrics CSV</a> · <a href="summary.json">Summary and confusion matrices</a> · <a href="paired_changes.json">Paired changes</a> · <a href="results.jsonl">Actual raw responses</a> · <a href="support_review_queue.json">Explanation-review queue</a> · <a href="manifest.json">Version manifest</a> · <a href="evidence_guide.pdf">Original guideline</a></p></section>'
    data = json.dumps(
        {
            "rows": rows,
            "pairs": pairs,
            "payloads": payloads,
            "labels": labels,
            "comparisons": PAIRS,
        },
        ensure_ascii=False,
        allow_nan=False,
    ).replace("<", "\\u003c")
    html += (
        '<script id="data" type="application/json">'
        + data
        + "</script><script>"
        + r"""
const d=JSON.parse(document.getElementById('data').textContent),$=id=>document.getElementById(id),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function opts(id,values){$(id).innerHTML=values.map(v=>'<option>'+esc(v)+'</option>').join('')}
opts('case',Object.keys(d.labels));opts('model',[...new Set(d.rows.map(r=>r.model))]);opts('repeat',[0,1,2]);opts('pair',Object.keys(d.comparisons));$('pair').value='allocation_seventh';
function render(){const c=$('case').value,m=$('model').value,n=Number($('repeat').value),pair=$('pair').value,p=d.pairs.find(x=>x.case_id===c&&x.model===m&&x.repeat===n&&x.pair===pair);$('status').textContent='Engineering reference: '+d.labels[c].reference_outcome+' · '+(p?p.change:'Pending pair')+(p?.same_request?' · Identical requests: no allocation treatment change':'');$('comparison').innerHTML='<div class="compare">'+d.comparisons[pair].map(arm=>{const r=d.rows.find(x=>x.case_id===c&&x.model===m&&x.repeat===n&&x.method===arm),payload=d.payloads.find(x=>x.case_id===c&&x.method===arm)?.payload;return '<div class="panel"><h3>'+esc(arm)+'</h3><p>'+esc(r?.status||'Pending')+' · '+esc(r?.answer?.assessment_outcome||r?.error||'')+'</p><p>'+esc(r?.answer?.explanation||'No accepted model explanation')+'</p><p>Cited facts: '+esc((r?.answer?.fact_fields||[]).join(', '))+'</p><details><summary>Fixed patient facts and original note</summary><pre>'+esc(JSON.stringify({verified_patient_facts:payload.verified_patient_facts,nurse_note:payload.nurse_note},null,2))+'</pre></details>'+payload.guideline_evidence.map(s=>'<details><summary>'+esc(s.source_id)+(r?.answer?.source_ids?.includes(s.source_id)?' · Cited':' · Supplied')+'</summary><a href="evidence_guide.pdf#page='+Number(s.pdf_page)+'">PDF '+Number(s.pdf_page)+'</a> · Section '+esc(s.section)+'<pre>'+esc(s.source_text)+'</pre></details>').join('')+'</div>'}).join('')+'</div>'}
['case','model','repeat','pair'].forEach(id=>$(id).addEventListener('change',render));render();
"""
        + "</script></main></html>"
    )
    (output / "index.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preparation", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    s = build(Path.cwd(), args.preparation, args.run, args.output)
    print(
        json.dumps(
            {k: s[k] for k in ("phase", "planned", "recorded", "failure_count", "pairs")}, indent=2
        )
    )
