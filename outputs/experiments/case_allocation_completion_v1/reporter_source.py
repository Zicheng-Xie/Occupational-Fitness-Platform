"""Build a readable completion report from independently audited frozen results.

This report makes no model calls and never modifies the measured experiment.
"""

from __future__ import annotations

import argparse
import json
import shutil
from html import escape
from pathlib import Path

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.provenance import digest, write_json
from tools.run_frozen_retrieval_judgments import verify_files

ARMS = {
    "hybrid": "Hybrid RRF / original allocation",
    "seventh_round_robin": "Method 7 / original allocation",
    "seventh_case_coverage": "Method 7 / case allocation",
    "ninth_round_robin": "Method 9 / original allocation",
    "ninth_case_coverage": "Method 9 / case allocation",
}
PAIRS = {
    "retrieval_seventh": "Method 7 retrieval versus RRF",
    "retrieval_ninth": "Method 9 retrieval versus RRF",
    "allocation_seventh": "Method 7: new versus original allocation",
    "allocation_ninth": "Method 9: new versus original allocation",
    "combined_seventh": "Method 7 plus allocation versus RRF",
    "combined_ninth": "Method 9 plus allocation versus RRF",
}


def read(path):
    return json.loads(path.read_bytes())


def pct(value):
    return f"{value:.2%}"


def render(summary, focus, checks, allocation):
    if not summary["complete"] or summary["recorded_actual_calls"] != 990:
        raise ValueError("A completion report requires all 990 actual conditions")
    if not checks["complete"] or checks["observed_conditions"] != 990:
        raise ValueError("Independent completion audit is required")
    if (
        summary["patient_count"] != 33
        or len(summary["methods"]) != 10
        or any(r["recorded_calls"] != 99 for r in summary["methods"])
        or sum(r["accepted"] for r in summary["methods"]) != summary["accepted"]
    ):
        raise ValueError("The fixed 33-case, two-model, five-arm inventory differs")
    metric_rows = "".join(
        f"<tr><td>{escape(r['model'])}</td><td>{ARMS[r['method']]}</td>"
        f"<td>{r['correct']}/99 ({pct(r['agreement_all_recorded'])})</td>"
        f"<td>{r['accepted']}/99</td><td>{r['failed']}</td>"
        f"<td>{r['insufficient_against_other_engineering_label']}</td></tr>"
        for r in summary["methods"]
    )
    pairs = "".join(
        f"<tr><td>{escape(p['model'])}</td><td>{PAIRS[p['pair']]}</td>"
        f"<td>{p['mean_patient_agreement_delta'] * 100:+.2f} pp</td>"
        f"<td>{p['net_correct_calls_from_valid_classification_changes']:+d}</td>"
        f"<td>{p['net_correct_calls_from_contract_changes']:+d}</td>"
        f"<td>{p['same_request_outcome_variations']} / {p['same_request_contract_variations']}</td></tr>"
        for p in summary["paired_effects"]
    )
    coverage = "".join(
        f"<tr><td>{ARMS[r['method']]}</td><td>{pct(r['packet_coverage'])}</td></tr>"
        for r in allocation["metrics"]
    )
    focus_html = ""
    for case in focus:
        groups = {}
        for item in case["actual_observations"]:
            r = item["observation"]
            key = (r["model"], r["method"])
            groups.setdefault(key, []).append(r)
        rows = ""
        for (model, arm), observations in sorted(groups.items()):
            by_repeat = sorted(observations, key=lambda r: r["repeat"])
            outcomes = [
                r["answer"]["assessment_outcome"]
                if r["status"] == "completed"
                else "FAILED: " + r.get("error", "unknown")
                for r in by_repeat
            ]
            cited = sum(
                "AFTD2022-EXP-05643c50d6cf5973" in r.get("answer", {}).get("source_ids", [])
                for r in observations
            )
            rows += (
                f"<tr><td>{escape(model)}</td><td>{ARMS[arm]}</td><td>"
                + "<br>".join(escape(v) for v in outcomes)
                + f"</td><td>{cited}/3</td></tr>"
            )
        focus_html += (
            f"<section><h2>{escape(case['case_id'])}</h2><p>Engineering reference: "
            f"<strong>{escape(case['engineering_reference']['reference_outcome'])}</strong>. "
            "The verified record documents a Blackout and an unresolved mechanism. "
            "Clinical review remains pending.</p><div class='scroll'><table><thead><tr>"
            "<th>Model</th><th>Evidence arm</th><th>Actual outcomes: repeats 0 / 1 / 2</th>"
            "<th>Restriction passage cited</th></tr></thead><tbody>"
            + rows
            + "</tbody></table></div><p>The seventh route's new packet contains the added "
            "Blackout work-up passage. A supplied or validly cited passage does not establish "
            "that its restriction was correctly applied. See the paired viewer for every "
            "explanation and every supplied original.</p></section>"
        )
    accepted = summary["accepted"]
    html = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Completed judgment comparison | Occupational Fitness Platform</title><style>
:root{color-scheme:light;font:15px/1.65 Arial,sans-serif;color:#26394a;background:#f4f6f8}body{margin:0}main{max-width:1240px;margin:32px auto;padding:0 24px}header,section{background:#fff;border:1px solid #dce4eb;border-radius:8px;margin:18px 0;padding:26px}h1{font-size:30px;line-height:1.25;margin:12px 0}h2{font-size:20px;margin:0 0 12px}small{letter-spacing:.09em;color:#567187}p{max-width:1100px}.notice{background:#faf3e7;border-left:4px solid #ab7a27;padding:14px}.stats{display:flex;gap:36px;flex-wrap:wrap;padding:12px 0}.stats strong{font-size:27px;display:block}.stats span{color:#596b7a;font-size:13px}.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;border-bottom:1px solid #e0e7ed;padding:10px;vertical-align:top}th{color:#527083;background:#f7f9fb}a{color:#205e88}li{margin:8px 0}code{overflow-wrap:anywhere}figure{margin:16px 0}img{max-width:100%;border:1px solid #dce4eb}figcaption{font-size:13px;color:#596b7a}details{padding:10px 0}summary{cursor:pointer}footer{padding:18px 0;color:#596b7a;font-size:13px}</style></head><body><main><header><small>OCCUPATIONAL FITNESS PLATFORM · COMPLETED DEVELOPMENT COMPARISON</small><h1>Does better retrieval improve fitness judgment?</h1>"""
    html += (
        f"<div class='stats'><div><strong>990 / 990</strong><span>Actual conditions completed</span></div>"
        f"<div><strong>33</strong><span>Previously observed development cases</span></div>"
        f"<div><strong>{accepted}</strong><span>Accepted responses</span></div>"
        f"<div><strong>{990 - accepted}</strong><span>Retained failures</span></div></div>"
        "<p class='notice'>Engineering reference agreement, not clinical accuracy. Each model/arm "
        "has 33 cases and three calls per case. Repeats are aggregated within patients. The "
        "production workflow, rules and default retrieval remain unchanged.</p></header>"
        "<section><h2>Evidence delivered to the judge</h2><p>Coverage over the same 45 labeled "
        "module scopes. At most five whole original passages and 9,000 evidence bytes; this is "
        "case-packet coverage, separate from module-level Top-5 recall.</p><table><tr>"
        "<th>Evidence arm</th><th>Original-text packet coverage</th></tr>"
        + coverage
        + "</table></section><section><h2>Actual judgments</h2><p>Failures remain in the agreement "
        "denominator. Abstentions against other labels are accepted insufficient-information "
        "answers against a different engineering reference. They require case review, rather "
        "than automatically establishing inappropriate clinical abstention. VAL-MIX-09 and "
        "VAL-MIX-10 have no verified fact values and both have an insufficient-information "
        "engineering reference. The independent analysis reports that subgroup separately.</p>"
        "<div class='scroll'><table><thead><tr><th>Model</th>"
        "<th>Evidence arm</th><th>Correct / recorded</th><th>Accepted</th><th>Failed</th>"
        "<th>Abstentions vs other labels</th></tr></thead><tbody>"
        + metric_rows
        + "</tbody></table></div></section><section><h2>Paired effects: classification and contract</h2>"
        "<p>Net classification = valid wrong-to-correct minus valid correct-to-wrong. Net "
        "contract = failed-to-correct minus correct-to-failed. Both contribute to all-call "
        "agreement, but only the first describes a change between valid classifications. "
        "Variation between identical requests cannot be attributed to evidence allocation.</p>"
        "<div class='scroll'><table><thead><tr><th>Model</th><th>Comparison</th>"
        "<th>Mean patient agreement change</th><th>Net classification calls</th>"
        "<th>Net contract calls</th><th>Identical-request outcome / contract variations</th>"
        "</tr></thead><tbody>"
        + pairs
        + "</tbody></table></div></section>"
        + focus_html
        + "<section><h2>Original restriction and engineering consistency check</h2>"
        "<p>The added passage is source <code>AFTD2022-EXP-05643c50d6cf5973</code>, "
        "section 1.2.1, PDF page 68, printed page 57. Native PDF text and the cited rectangle "
        "match the frozen passage. The neighboring vasovagal qualification still requires "
        "case-specific assessment. This source check is not independent clinical adjudication.</p>"
        "<figure><img src='../blackout_source_visual_review_v1/source_region.png' "
        "alt='Original Blackout work-up passage from PDF page 68'><figcaption>"
        "Native PDF region; no rewritten or generated guideline text.</figcaption></figure>"
        "<p><a href='../case_allocation_judgment_comparison_v1/evidence_guide.pdf#page=68'>"
        "Open original PDF page 68</a></p></section>"
        "<section><h2>Inspect and reproduce</h2><ul>"
        "<li><a href='../case_allocation_judgment_comparison_v1/index.html'>"
        "Interactive paired viewer: case, model, repeat and evidence arm</a></li>"
        "<li><a href='../case_allocation_effect_analysis_v1/index.html'>"
        "Independent analysis, patient aggregates and focus-case explanations</a></li>"
        "<li><a href='../case_allocation_focus_support_review_v1/index.html'>"
        "Independent human support-review worksheet for the two focus cases</a></li>"
        "<li><a href='../case_allocation_full_integrity_v1/checks.json'>"
        "Independent integrity audit: exact conditions, requests and actual responses</a></li>"
        "<li><a href='../case_allocation_judgment_full_v1/results.jsonl'>"
        "All 990 original responses, including failed responses</a></li>"
        "<li><a href='../scope88_optimization_comparison_v2/index.html'>"
        "Preserved ten-route retrieval comparison</a></li>"
        "<li><a href='../prospective_case_review_v2/index.html'>"
        "Twelve new prospective cases: independent annotation and readiness gate</a></li>"
        "<li><a href='summary.json'>Completion summary and provenance</a></li></ul></section>"
        "<section><h2>What remains</h2><ol><li>Independent human review of explanation support "
        "and guideline applicability, including the two Blackout cases.</li>"
        "<li>Two independent reviewers label the twelve new cases; adjudicate disagreements "
        "and freeze reference labels before any model test or strategy tuning.</li>"
        "<li>Integrate the prospective runner and live native-index preflight under an "
        "explicit pre-inference plan. Then run the frozen strategies on that unseen cohort, "
        "retain failures and compare patient-level results before a production change.</li>"
        "<li>Resolve remaining corpus layout and applicability issues; clinical approval "
        "remains separate from engineering validation.</li></ol></section>"
        "<footer>All previous methods, experiments and pilot results are preserved. "
        "No production method has been replaced.</footer></main></body></html>"
    )
    return html


def build(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists() or not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Use a fresh output inside outputs/experiments")
    experiments = root / "outputs/experiments"
    inputs = [
        "case_allocation_effect_analysis_v1",
        "case_allocation_full_integrity_v1",
        "case_allocation_focus_support_review_v1",
        "case_allocation_judgment_preparation_v1",
        "blackout_source_visual_review_v1",
        "prospective_case_review_v2",
    ]
    pins = {name: verify_files(experiments / name) for name in inputs}
    analysis = experiments / inputs[0]
    summary = read(analysis / "summary.json")
    focus = read(analysis / "focus_cases.json")
    checks = read(experiments / inputs[1] / "checks.json")
    if read(analysis / "manifest.json")["run_identity"] != checks["run_identity"]:
        raise ValueError("Independent analysis and audit bind different actual runs")
    allocation = read(experiments / "case_allocation_judgment_preparation_v1/summary.json")
    html = render(summary, focus, checks, allocation)
    data = {
        "complete": True,
        "actual_conditions": summary["recorded_actual_calls"],
        "accepted": summary["accepted"],
        "failed": summary["recorded_actual_calls"] - summary["accepted"],
        "patients": summary["patient_count"],
        "metrics": summary["methods"],
        "paired_effects": summary["paired_effects"],
        "input_inventories": pins,
        "reporter_sha256": file_hash(__file__),
        "clinical_review": "pending",
        "production_change": False,
    }
    output.mkdir(parents=True)
    (output / "index.html").write_text(html, encoding="utf-8")
    write_json(output / "summary.json", data)
    write_json(output / "manifest.json", {"identity": digest(data), **data})
    shutil.copy2(__file__, output / "reporter_source.py")
    write_json(
        output / "artifacts.json", {p.name: file_hash(p) for p in output.iterdir() if p.is_file()}
    )
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/experiments/case_allocation_completion_v1")
    )
    arguments = parser.parse_args()
    result = build(Path.cwd(), arguments.output)
    print(json.dumps({k: result[k] for k in ("actual_conditions", "accepted", "failed")}))
