"""Separate evidence-bundle changes, upstream effects and judgment instability."""

import csv
import json
from collections import Counter, defaultdict
from html import escape
from pathlib import Path

from occupational_fitness_rag.provenance import digest, write_json


def record_key(row):
    return row["case_id"], row["model"], row["method"], row["repeat"]


def patient_identity(row):
    snapshot = row["input_snapshot"]
    return digest(
        {
            key: snapshot.get(key)
            for key in ["licence_context", "modules", "nurse_note", "verified_patient_facts"]
        }
    )


def audit_errors(rows, upstream_case_ids=(), expected_repeats=3):
    indexed = {record_key(row): row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError("Duplicate experimental condition in judgment records")
    pairs = []
    for row in rows:
        if row["method"] == "hybrid":
            continue
        baseline = indexed.get((row["case_id"], row["model"], "hybrid", row["repeat"]))
        if baseline is None:
            continue
        sources = row["input_snapshot"]["guideline_evidence"]
        base_sources = baseline["input_snapshot"]["guideline_evidence"]
        ids = [s["source_id"] for s in sources]
        base_ids = [s["source_id"] for s in base_sources]
        patient_match = patient_identity(row) == patient_identity(baseline)
        accepted = row["status"] == baseline["status"] == "completed"
        prediction = row.get("answer", {}).get("assessment_outcome")
        base_prediction = baseline.get("answer", {}).get("assessment_outcome")
        transition = "not_comparable"
        if accepted and patient_match:
            correct = prediction == row["reference_outcome"]
            base_correct = base_prediction == baseline["reference_outcome"]
            transition = (
                "wrong_to_correct"
                if correct and not base_correct
                else "correct_to_wrong"
                if base_correct and not correct
                else "both_correct"
                if correct
                else "both_wrong"
            )
        evidence_change = (
            "identical_ordered_evidence"
            if digest(sources) == digest(base_sources)
            else "same_passages_different_order"
            if digest(sorted(sources, key=lambda x: x["source_id"]))
            == digest(sorted(base_sources, key=lambda x: x["source_id"]))
            else "changed_evidence_bundle"
        )
        pairs.append(
            {
                "case_id": row["case_id"],
                "cohort": row["cohort"],
                "model": row["model"],
                "method": row["method"],
                "repeat": row["repeat"],
                "reference_outcome": row["reference_outcome"],
                "hybrid_outcome": base_prediction,
                "method_outcome": prediction,
                "hybrid_status": baseline["status"],
                "method_status": row["status"],
                "patient_inputs_identical": patient_match,
                "transition": transition,
                "outcome_changed": accepted and prediction != base_prediction,
                "evidence_change": evidence_change,
                "added_source_ids": sorted(set(ids) - set(base_ids)),
                "removed_source_ids": sorted(set(base_ids) - set(ids)),
                "hybrid_source_ids": base_ids,
                "method_source_ids": ids,
                "upstream_review_difference": row["case_id"] in upstream_case_ids,
                "support_review": "pending_independent_review",
                "interpretation": "Bundle-level association; no single-passage causal attribution",
            }
        )
    repeated = defaultdict(list)
    for row in rows:
        repeated[(row["case_id"], row["model"], row["method"])].append(row)
    stability = []
    for (case_id, model, method), group in sorted(repeated.items()):
        completed = [r for r in group if r["status"] == "completed"]
        outcomes = sorted({r["answer"]["assessment_outcome"] for r in completed})
        eligible = len(group) == expected_repeats and len(completed) == expected_repeats
        identical = len({digest(r["input_snapshot"]) for r in group}) == 1
        stability.append(
            {
                "case_id": case_id,
                "cohort": group[0]["cohort"],
                "model": model,
                "method": method,
                "recorded_calls": len(group),
                "accepted_calls": len(completed),
                "expected_repeats": expected_repeats,
                "complete_condition": eligible,
                "identical_inputs": identical,
                "stability_analysis_eligible": eligible and identical,
                "outcomes": outcomes,
                "stable_outcome": len(outcomes) == 1 if eligible and identical else None,
            }
        )
    counts = Counter((p["cohort"], p["model"], p["method"], p["transition"]) for p in pairs)
    return {
        "recorded_calls": len(rows),
        "paired_conditions": len(pairs),
        "patient_input_mismatches": sum(not p["patient_inputs_identical"] for p in pairs),
        "changed_outcome_with_identical_evidence": sum(
            p["outcome_changed"] and p["evidence_change"] == "identical_ordered_evidence"
            for p in pairs
        ),
        "counts": [
            dict(cohort=c, model=m, method=a, transition=t, case_repeat_pairs=n)
            for (c, m, a, t), n in sorted(counts.items())
        ],
        "pairs": pairs,
        "repeat_stability": stability,
        "clinical_accuracy": None,
        "support_review": "pending_independent_review",
        "notes": [
            "Three repeats are not independent patients.",
            "Both-wrong pairs can have different predicted outcomes.",
            "Changed judgments with identical ordered evidence cannot be attributed to retrieval differences.",
            "Upstream review differences are flags, not proof of their effect on a specific judgment.",
            "Engineering reference agreement does not establish explanation support or clinical correctness.",
        ],
    }


def render_error_audit(audit, rows):
    indexed = {record_key(r): r for r in rows}
    priority = [
        p for p in audit["pairs"] if p["outcome_changed"] or p["transition"] == "not_comparable"
    ]
    priority.sort(
        key=lambda p: (
            p["transition"] not in {"wrong_to_correct", "correct_to_wrong"},
            p["case_id"],
            p["model"],
            p["method"],
            p["repeat"],
        )
    )

    def panel(row):
        answer = row.get("answer", {})
        quoted = "".join(
            f"<details><summary>{escape(s['source_id'])} · section {escape(s['section'])} · "
            f"PDF {s['pdf_page']}</summary><blockquote>{escape(s['source_text'])}</blockquote></details>"
            for s in row["input_snapshot"]["guideline_evidence"]
        )
        return (
            f"<section><h3>{escape(row['method'])}</h3><b>{escape(answer.get('assessment_outcome', 'Unavailable'))}</b>"
            f"<p>{escape(answer.get('explanation', row.get('error', '')))}</p>"
            f"<p>Cited: {escape(', '.join(answer.get('source_ids', [])) or 'None')}</p>{quoted}</section>"
        )

    cards = []
    for pair in priority[:60]:
        row = indexed[(pair["case_id"], pair["model"], pair["method"], pair["repeat"])]
        base = indexed[(pair["case_id"], pair["model"], "hybrid", pair["repeat"])]
        cards.append(
            f"<article><h2>{escape(pair['case_id'])} · {escape(pair['model'])} · repeat {pair['repeat'] + 1}</h2>"
            f"<p>{pair['transition']} · {pair['evidence_change']} · "
            f"Upstream review difference: {pair['upstream_review_difference']}</p>"
            f"<p>Engineering reference: {escape(pair['reference_outcome'])}</p>"
            "<details><summary>Original note and shared frozen facts</summary><pre>"
            + escape(json.dumps(base["input_snapshot"], indent=2))
            + '</pre></details><div class="pair">'
            + panel(base)
            + panel(row)
            + "</div></article>"
        )
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>Judgment error audit</title>'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><style>'
        "body{font:15px/1.65 system-ui;color:#203447;background:#f5f7fa;margin:0;padding:32px}"
        "main{max-width:1280px;margin:auto}article,.intro{background:white;border:1px solid #dce4ec;"
        "border-radius:12px;padding:24px;margin:20px 0}.pair{display:grid;grid-template-columns:1fr 1fr;gap:24px}"
        "pre,blockquote{white-space:pre-wrap;overflow-wrap:anywhere}blockquote{margin:8px 0;background:#f5f8fb;padding:16px}"
        "summary{cursor:pointer;padding:10px 0}h1,h2,h3{line-height:1.3}@media(max-width:800px){.pair{grid-template-columns:1fr}body{padding:12px}}"
        '</style><main><h1>Judgment error audit</h1><div class="intro">'
        f"<p>{audit['recorded_calls']} calls recorded; {audit['paired_conditions']} paired conditions. "
        "This is an evolving error-analysis snapshot, not a completed method ranking.</p>"
        "<p>Compare actual evidence bundles and explanations. Valid identifiers do not establish support. "
        "All explanations remain pending independent review. Repeats are not independent patients.</p>"
        f"<p>Showing {min(len(priority), 60)} of {len(priority)} priority pairs; complete pairs and stability records: "
        '<a href="error_audit.json">JSON</a> · <a href="paired_error_audit.csv">CSV</a>. '
        '<a href="interactive_report.html">Main report</a></p></div>'
        + ("".join(cards) or "<p>No changed outcomes or failed pairs recorded yet.</p>")
        + "</main></html>"
    )


def export_error_audit(output: Path, rows, upstream_case_ids=(), expected_repeats=3):
    audit = audit_errors(rows, upstream_case_ids, expected_repeats)
    write_json(output / "error_audit.json", audit)
    (output / "error_audit.html").write_text(render_error_audit(audit, rows), encoding="utf-8")
    with (output / "paired_error_audit.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        if audit["pairs"]:
            writer = csv.DictWriter(stream, fieldnames=list(audit["pairs"][0]))
            writer.writeheader()
            writer.writerows(
                {k: json.dumps(v) if isinstance(v, list) else v for k, v in p.items()}
                for p in audit["pairs"]
            )
    return audit
