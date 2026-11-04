"""Independently analyze frozen case-allocation judgments without model calls.

The primary sample size is patients. Repeated actual calls, validation failures,
input-identical variation and clinician-pending explanation support stay separate.
Incomplete observations require an explicitly named partial snapshot.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from collections import Counter
from html import escape
from pathlib import Path

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.evaluation.passage_comparison import patient_identity
from occupational_fitness_rag.provenance import digest, write_json
from tools.run_frozen_retrieval_judgments import accept_completion, prepare_inputs, verify_files

ARMS = (
    "hybrid",
    "seventh_round_robin",
    "seventh_case_coverage",
    "ninth_round_robin",
    "ninth_case_coverage",
)
PAIRS = {
    "retrieval_seventh": ("hybrid", "seventh_round_robin"),
    "retrieval_ninth": ("hybrid", "ninth_round_robin"),
    "allocation_seventh": ("seventh_round_robin", "seventh_case_coverage"),
    "allocation_ninth": ("ninth_round_robin", "ninth_case_coverage"),
    "combined_seventh": ("hybrid", "seventh_case_coverage"),
    "combined_ninth": ("hybrid", "ninth_case_coverage"),
}
OUTCOMES = (
    "meets_unconditional_standard",
    "may_meet_conditional_standard",
    "temporarily_unfit",
    "does_not_meet_standard",
    "insufficient_information",
)
FOCUS_CASES = ("VAL-MIX-02", "VAL-MIX-06")


def condition_key(row):
    return tuple(row[k] for k in ("case_id", "method", "model", "repeat"))


def failure_category(row):
    if row["status"] == "completed":
        return None
    error = row.get("error", "")
    if "requires a supplied source citation" in error:
        return "missing_source_citation"
    if "was not supplied" in error:
        return "invalid_source_or_fact_identifier"
    if "Incomplete or empty" in error:
        return "incomplete_completion"
    if "context budget" in error:
        return "context_budget"
    return "other_recorded_failure"


def audit_observations(config, manifest, payloads, requests, conditions, plan, rows):
    """Verify exact bodies and raw accepted answers before opening outcome labels."""
    if (
        digest({k: v for k, v in plan.items() if k not in {"identity", "production_change"}})
        != plan["identity"]
    ):
        raise ValueError("Actual execution plan self-identity differs")
    if plan["preparation_identity"] != manifest["identity"] or plan["requests_sha256"] != digest(
        requests
    ):
        raise ValueError("Execution binds a different preparation or request inventory")
    expected = {condition_key(c): c for c in conditions}
    actual_plan = {condition_key(c): c for c in plan["conditions"]}
    if len(expected) != len(conditions) or actual_plan != expected:
        raise ValueError("The actual execution condition inventory differs")
    payload_map = {
        (r["case_id"], r["method"]): r["payload"] for r in payloads if r["status"] == "ready"
    }
    patient_ids = {}
    for (case, _), payload in payload_map.items():
        if patient_ids.setdefault(case, patient_identity(payload)) != patient_identity(payload):
            raise ValueError("Evidence arms changed fixed patient facts")
    seen = set()
    for row in rows:
        key = condition_key(row)
        if key in seen or key not in expected:
            raise ValueError("Duplicated or unplanned actual condition")
        seen.add(key)
        condition = expected[key]
        if (
            row["experiment_identity"] != plan["identity"]
            or row["request_identity"] != condition["request_identity"]
            or row["payload_identity"] != condition["payload_identity"]
        ):
            raise ValueError("Actual condition identity differs")
        body = requests[row["request_identity"]]
        if digest(body) != row["request_identity"] or body["model"] != row["model"]:
            raise ValueError("Actual request fingerprint or model differs")
        payload = payload_map[(row["case_id"], row["method"])]
        if json.loads(body["messages"][1]["content"]) != payload:
            raise ValueError("Model-visible patient/evidence payload differs")
        if row["status"] == "completed":
            answer = accept_completion(row["raw_response"], payload, row["method"], config)
            if answer.model_dump(mode="json") != row["answer"]:
                raise ValueError("Accepted answer differs from retained actual completion")
        elif row["status"] != "failed" or not row.get("error"):
            raise ValueError("Unknown or undocumented failure state")
    return payload_map


def method_metrics(rows, labels, conditions):
    """Report call-level denominators; failures are not accepted abstentions."""
    result = []
    groups = sorted({(c["model"], c["method"]) for c in conditions})
    for model, method in groups:
        group = [r for r in rows if r["model"] == model and r["method"] == method]
        accepted = [r for r in group if r["status"] == "completed"]
        expected_count = sum(c["model"] == model and c["method"] == method for c in conditions)
        matrix = {a: {p: 0 for p in (*OUTCOMES, "__failure__")} for a in OUTCOMES}
        for row in group:
            actual = labels[row["case_id"]]["reference_outcome"]
            predicted = (
                row["answer"]["assessment_outcome"]
                if row["status"] == "completed"
                else "__failure__"
            )
            matrix[actual][predicted] += 1
        correct = sum(matrix[label][label] for label in OUTCOMES)
        f1 = []
        for label in OUTCOMES:
            tp = matrix[label][label]
            fp = sum(matrix[a][label] for a in OUTCOMES if a != label)
            fn = sum(matrix[label][p] for p in OUTCOMES if p != label)
            if tp + fp + fn:
                f1.append(2 * tp / (2 * tp + fp + fn))
        insufficient = [
            r for r in accepted if r["answer"]["assessment_outcome"] == "insufficient_information"
        ]
        result.append(
            {
                "model": model,
                "method": method,
                "planned_calls": expected_count,
                "recorded_calls": len(group),
                "pending_calls": expected_count - len(group),
                "accepted": len(accepted),
                "failed": len(group) - len(accepted),
                "correct": correct,
                "agreement_all_recorded": correct / len(group) if group else None,
                "agreement_accepted": correct / len(accepted) if accepted else None,
                "macro_f1_observed_classes_accepted": sum(f1) / len(f1) if f1 else None,
                "accepted_insufficient": len(insufficient),
                "appropriate_insufficient_against_engineering_label": sum(
                    labels[r["case_id"]]["reference_outcome"] == "insufficient_information"
                    for r in insufficient
                ),
                "insufficient_against_other_engineering_label": sum(
                    labels[r["case_id"]]["reference_outcome"] != "insufficient_information"
                    for r in insufficient
                ),
                "failures_by_category": dict(
                    Counter(failure_category(r) for r in group if r["status"] != "completed")
                ),
                "confusion_including_failure_column": matrix,
            }
        )
    return result


def patient_metrics(rows, labels, conditions):
    """Aggregate three repeats within each patient; never inflate patient N."""
    index = {condition_key(r): r for r in rows}
    groups = sorted({(c["case_id"], c["model"], c["method"]) for c in conditions})
    result = []
    for case, model, method in groups:
        expected = [
            c
            for c in conditions
            if c["case_id"] == case and c["model"] == model and c["method"] == method
        ]
        group = [index[condition_key(c)] for c in expected if condition_key(c) in index]
        complete = len(group) == len(expected)
        accepted = [r for r in group if r["status"] == "completed"]
        correct = sum(
            r["answer"]["assessment_outcome"] == labels[case]["reference_outcome"] for r in accepted
        )
        votes = Counter(
            r["answer"]["assessment_outcome"] if r["status"] == "completed" else "__failure__"
            for r in group
        )
        majority = (
            next((outcome for outcome, n in votes.items() if n > len(expected) / 2), None)
            if complete
            else None
        )
        result.append(
            {
                "case_id": case,
                "model": model,
                "method": method,
                "reference_outcome": labels[case]["reference_outcome"],
                "planned_repeats": len(expected),
                "recorded_repeats": len(group),
                "complete_repeat_inventory": complete,
                "correct_repeats": correct,
                "accepted_repeats": len(accepted),
                "failed_repeats": len(group) - len(accepted),
                "mean_repeat_agreement": correct / len(expected) if complete else None,
                "majority_outcome_including_failure_votes": majority,
                "majority_matches_reference": majority == labels[case]["reference_outcome"]
                if complete
                else None,
                "no_strict_majority": complete and majority is None,
                "observed_votes": dict(votes),
            }
        )
    return result


def agreement_component(a, b, expected):
    """Account for agreement changes without calling validation recovery a prediction gain."""
    if a is None or b is None:
        return "pending_pair"
    left_valid, right_valid = (r["status"] == "completed" for r in (a, b))
    before = a.get("answer", {}).get("assessment_outcome")
    after = b.get("answer", {}).get("assessment_outcome")
    if left_valid and right_valid:
        if before == expected and after == expected:
            return "valid_correct_to_valid_correct"
        if before != expected and after == expected:
            return "valid_wrong_to_valid_correct"
        if before == expected:
            return "valid_correct_to_valid_wrong"
        return "valid_wrong_to_valid_wrong"
    if not left_valid and right_valid:
        return "invalid_to_valid_correct" if after == expected else "invalid_to_valid_wrong"
    if left_valid and not right_valid:
        return "valid_correct_to_invalid" if before == expected else "valid_wrong_to_invalid"
    return "both_invalid"


def pair_metrics(rows, labels, conditions, payload_map):
    """Separate evidence interventions from variation of identical requests."""
    index = {condition_key(r): r for r in rows}
    patients = {
        (p["case_id"], p["model"], p["method"]): p
        for p in patient_metrics(rows, labels, conditions)
    }
    cases = sorted({(c["case_id"], c["model"]) for c in conditions})
    repeated, paired_patients = [], []
    for case, model in cases:
        repeats = sorted(
            {c["repeat"] for c in conditions if c["case_id"] == case and c["model"] == model}
        )
        for pair, (left, right) in PAIRS.items():
            before_payload, after_payload = [
                payload_map[(case, method)] for method in (left, right)
            ]
            before_sources, after_sources = [
                {s["source_id"] for s in p["guideline_evidence"]}
                for p in (before_payload, after_payload)
            ]
            for repeat in repeats:
                a, b = [index.get((case, method, model, repeat)) for method in (left, right)]
                before, after = [
                    r.get("answer", {}).get("assessment_outcome") if r else None for r in (a, b)
                ]
                if not a or not b:
                    change = "pending_pair"
                elif a["status"] != "completed" or b["status"] != "completed":
                    change = "run_or_contract_failure"
                elif before == after:
                    change = (
                        "unchanged_correct"
                        if before == labels[case]["reference_outcome"]
                        else "unchanged_wrong"
                    )
                elif after == labels[case]["reference_outcome"]:
                    change = "wrong_to_correct"
                elif before == labels[case]["reference_outcome"]:
                    change = "correct_to_wrong"
                else:
                    change = "wrong_to_different_wrong"
                same_request = bool(a and b and a["request_identity"] == b["request_identity"])
                repeated.append(
                    {
                        "case_id": case,
                        "model": model,
                        "repeat": repeat,
                        "pair": pair,
                        "left": left,
                        "right": right,
                        "before": before,
                        "after": after,
                        "reference_outcome": labels[case]["reference_outcome"],
                        "change": change,
                        "agreement_component": agreement_component(
                            a, b, labels[case]["reference_outcome"]
                        ),
                        "same_request": same_request,
                        "identical_request_outcome_variation": same_request
                        and before is not None
                        and after is not None
                        and before != after,
                        "identical_request_contract_variation": same_request
                        and a["status"] != b["status"],
                        "evidence_changed": before_payload["guideline_evidence"]
                        != after_payload["guideline_evidence"],
                        "source_ids_added": sorted(after_sources - before_sources),
                        "source_ids_removed": sorted(before_sources - after_sources),
                        "before_failure": failure_category(a) if a else None,
                        "after_failure": failure_category(b) if b else None,
                    }
                )
            a, b = [patients[(case, model, method)] for method in (left, right)]
            complete = a["complete_repeat_inventory"] and b["complete_repeat_inventory"]
            delta = b["mean_repeat_agreement"] - a["mean_repeat_agreement"] if complete else None
            paired_patients.append(
                {
                    "case_id": case,
                    "model": model,
                    "pair": pair,
                    "left": left,
                    "right": right,
                    "complete_repeats_on_both_sides": complete,
                    "before_patient_mean_agreement": a["mean_repeat_agreement"],
                    "after_patient_mean_agreement": b["mean_repeat_agreement"],
                    "delta_patient_mean_agreement": delta,
                    "patient_change": "pending_repeats"
                    if delta is None
                    else "improved"
                    if delta > 0
                    else "regressed"
                    if delta < 0
                    else "unchanged",
                    "before_failed_repeats": a["failed_repeats"],
                    "after_failed_repeats": b["failed_repeats"],
                    "before_majority_outcome": a["majority_outcome_including_failure_votes"],
                    "after_majority_outcome": b["majority_outcome_including_failure_votes"],
                    "same_patient_evidence": before_payload["guideline_evidence"]
                    == after_payload["guideline_evidence"],
                }
            )
    return repeated, paired_patients


def support_review_flags(row, payload):
    """Post-hoc literal review cues, not an automatic entailment score."""
    facts = payload["verified_patient_facts"]
    established_blackout = facts.get("blackout.occurred", {}).get("value") is True
    pending_mechanism = (
        facts.get("blackout.mechanism_status", {}).get("value") == "under_investigation"
    )
    answer = row.get("answer", {})
    anchors = []
    for source in payload["guideline_evidence"]:
        normalized = " ".join(source["source_text"].split())
        match = re.search(
            r"[^.!?]*not to drive until[^.!?]*mechanism[^.!?]*[.!?]?", normalized, flags=re.I
        )
        if match:
            anchors.append(
                {
                    "source_id": source["source_id"],
                    "pdf_page": source["pdf_page"],
                    "section": source["section"],
                    "literal_whitespace_normalized_clause": match.group(0).strip(),
                    "cited_by_model": source["source_id"] in answer.get("source_ids", []),
                }
            )
    words = answer.get("explanation", "").lower()
    restriction_mentioned = bool(
        re.search(
            r"not (?:to )?drive|temporar(?:ily|y) unfit|stop driving|refrain from driving|not fit to drive",
            words,
        )
    )
    cues = []
    documented = {
        "hypertension" if field.startswith("cardiovascular.") else field.split(".", 1)[0]
        for field, fact in facts.items()
        if fact.get("value") is not None and fact.get("status", "present") == "present"
    }
    unmeasured = [module for module in payload["modules"] if module not in documented]
    if established_blackout and pending_mechanism and anchors and row["status"] == "completed":
        if answer["assessment_outcome"] == "insufficient_information":
            cues.append(
                "insufficient_outcome_despite_supplied_explicit_pending_mechanism_restriction"
            )
            if unmeasured:
                cues.append("unmeasured_modules_may_mask_supplied_restrictive_clause")
        if not restriction_mentioned:
            cues.append(
                "explicit_stop_driving_clause_not_reflected_in_explanation_by_literal_check"
            )
        if not any(a["cited_by_model"] for a in anchors):
            cues.append("supplied_pending_mechanism_restriction_source_not_cited")
    return {
        "status": "pending_independent_clinical_and_entailment_review",
        "identifier_validity": row["status"] == "completed",
        "fact_presence": {
            "blackout_occurred": established_blackout,
            "mechanism_under_investigation": pending_mechanism,
        },
        "requested_modules_without_verified_values": unmeasured,
        "literal_restriction_anchors": anchors,
        "literal_review_cues": cues,
        "entailment_score": None,
        "literal_check_scope": "Blackout pending-mechanism restriction only; other conditions and exceptions remain unreviewed",
        "interpretation": "Literal cues identify review priorities. They do not prove clinical correctness, contradiction or explanation support.",
    }


def _write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build(root, preparation, run, output, *, allow_partial=False):
    root, preparation, run, output = map(
        lambda p: Path(p).resolve(), (root, preparation, run, output)
    )
    if output.exists() or not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Preserve earlier reports; use a fresh isolated output")
    config, manifest, prep_pins, _, payloads, requests, conditions = prepare_inputs(preparation)
    raw = (run / "results.jsonl").read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise ValueError(
            "Actual JSONL snapshot has an incomplete tail; retry after the actor closes its write"
        )
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    plan = json.loads((run / "plan.json").read_bytes())
    complete = len(rows) == len(conditions)
    if not complete and (not allow_partial or "partial" not in output.name):
        raise ValueError(
            "Incomplete run requires --allow-partial and an explicitly partial output name"
        )
    run_pins = verify_files(run) if complete else None
    payload_map = audit_observations(config, manifest, payloads, requests, conditions, plan, rows)
    labels = json.loads((preparation / "scoring_labels.json").read_bytes())
    metrics = method_metrics(rows, labels, conditions)
    patients = patient_metrics(rows, labels, conditions)
    for patient in patients:
        patient["has_verified_values"] = bool(
            payload_map[(patient["case_id"], patient["method"])]["verified_patient_facts"]
        )
    repeated_pairs, patient_pairs = pair_metrics(rows, labels, conditions, payload_map)
    support = [
        {
            **{k: row[k] for k in ("case_id", "model", "method", "repeat", "status")},
            "review": support_review_flags(row, payload_map[(row["case_id"], row["method"])]),
        }
        for row in rows
    ]
    packet_metrics = json.loads((preparation / "packet_coverage.json").read_bytes())
    focus = []
    for case in FOCUS_CASES:
        if case not in labels:
            continue
        focus_rows = []
        for row in rows:
            if row["case_id"] == case:
                focus_rows.append(
                    {
                        "observation": row,
                        "support_review": support_review_flags(
                            row, payload_map[(case, row["method"])]
                        ),
                    }
                )
        focus.append(
            {
                "case_id": case,
                "engineering_reference": labels[case],
                "fixed_patient": {
                    k: v
                    for k, v in payload_map[(case, "hybrid")].items()
                    if k != "guideline_evidence"
                },
                "actual_evidence_by_arm": {
                    arm: payload_map[(case, arm)]["guideline_evidence"] for arm in ARMS
                },
                "blackout_packet_coverage": [
                    r for r in packet_metrics if r["case_id"] == case and r["module"] == "blackout"
                ],
                "actual_observations": focus_rows,
                "patient_repeat_aggregation": [p for p in patients if p["case_id"] == case],
            }
        )
    pair_summaries = []
    for model in config["models"]:
        for pair in PAIRS:
            calls = [r for r in repeated_pairs if r["model"] == model and r["pair"] == pair]
            people = [r for r in patient_pairs if r["model"] == model and r["pair"] == pair]
            observed = [p for p in people if p["complete_repeats_on_both_sides"]]
            components = Counter(p["agreement_component"] for p in calls)
            classification_net = (
                components["valid_wrong_to_valid_correct"]
                - components["valid_correct_to_valid_wrong"]
            )
            contract_net = (
                components["invalid_to_valid_correct"] - components["valid_correct_to_invalid"]
            )
            pair_summaries.append(
                {
                    "model": model,
                    "pair": pair,
                    "planned_patients": len(people),
                    "patients_with_complete_repeats": len(observed),
                    "patient_change_counts": dict(Counter(p["patient_change"] for p in people)),
                    "mean_patient_agreement_delta": sum(
                        p["delta_patient_mean_agreement"] for p in observed
                    )
                    / len(observed)
                    if observed
                    else None,
                    "repeat_pair_counts": dict(Counter(p["change"] for p in calls)),
                    "agreement_change_decomposition": dict(components),
                    "net_correct_calls_from_valid_classification_changes": classification_net,
                    "net_correct_calls_from_contract_changes": contract_net,
                    "net_correct_call_change_on_recorded_pairs": classification_net + contract_net,
                    "same_request_outcome_variations": sum(
                        p["identical_request_outcome_variation"] for p in calls
                    ),
                    "same_request_contract_variations": sum(
                        p["identical_request_contract_variation"] for p in calls
                    ),
                }
            )
    subgroup_cases = {
        name: {case for case, label in labels.items() if label.get("cohort") == name}
        for name in ("engineering", "complex_validation")
    }
    subgroup_cases["with_verified_values"] = {
        case for case in labels if payload_map[(case, "hybrid")]["verified_patient_facts"]
    }
    subgroup_cases["without_verified_values"] = set(labels) - subgroup_cases["with_verified_values"]
    subgroups = {
        name: {
            "patients": len(cases),
            "methods": method_metrics(
                [r for r in rows if r["case_id"] in cases],
                labels,
                [c for c in conditions if c["case_id"] in cases],
            ),
        }
        for name, cases in subgroup_cases.items()
    }
    summary = {
        "phase": "complete_development_comparison" if complete else "partial_observation_snapshot",
        "planned_actual_calls": len(conditions),
        "recorded_actual_calls": len(rows),
        "accepted": sum(r["status"] == "completed" for r in rows),
        "complete": complete,
        "patient_count": len(labels),
        "repeats_per_condition": config["repeats"],
        "methods": metrics,
        "paired_effects": pair_summaries,
        "subgroups": subgroups,
        "clinical_review": "pending",
        "production_change": False,
        "interpretation": "Engineering reference agreement on observed development cases. Repeats are aggregated within patients. A partial snapshot cannot establish an overall method ranking. Explanation support and clinical applicability remain independently unreviewed.",
    }
    output.mkdir(parents=True)
    for name, value in (
        ("summary.json", summary),
        ("patient_metrics.json", patients),
        ("repeat_pair_metrics.json", repeated_pairs),
        ("patient_pair_metrics.json", patient_pairs),
        ("focus_cases.json", focus),
        ("support_review_queue.json", support),
    ):
        write_json(output / name, value)
    (output / "observed_results.jsonl").write_bytes(raw)
    _write_csv(
        output / "method_metrics.csv",
        metrics,
        [
            k
            for k in metrics[0]
            if k not in {"confusion_including_failure_column", "failures_by_category"}
        ],
    )
    _write_csv(
        output / "patient_metrics.csv", patients, [k for k in patients[0] if k != "observed_votes"]
    )
    _write_csv(output / "patient_pair_metrics.csv", patient_pairs, list(patient_pairs[0]))
    corpus_report = root / config["retrieval_report"]
    shutil.copy2(corpus_report / "evidence_guide.pdf", output / "evidence_guide.pdf")
    _render(output, summary, focus)
    data = {
        "kind": "independent_case_allocation_effect_analysis",
        "preparation_identity": manifest["identity"],
        "preparation_artifacts": prep_pins,
        "actual_plan_sha256": file_hash(run / "plan.json"),
        "actual_observation_file_sha256": file_hash(output / "observed_results.jsonl"),
        "run_identity": plan["identity"],
        "complete_run_artifacts": run_pins,
        "analyzer_sha256": file_hash(__file__),
        "judge_validator_sha256": file_hash(root / "tools/run_frozen_retrieval_judgments.py"),
        "phase": summary["phase"],
        "new_model_calls": 0,
    }
    write_json(
        output / "manifest.json", {**data, "identity": digest(data), "production_change": False}
    )
    (output / "analyzer_source.py").write_bytes(Path(__file__).read_bytes())
    write_json(
        output / "artifacts.json", {p.name: file_hash(p) for p in output.iterdir() if p.is_file()}
    )
    return summary


def _render(output, summary, focus):
    def pct(value):
        return "Pending" if value is None else f"{value:.2%}"

    table = "".join(
        f"<tr><td>{escape(r['model'])}</td><td>{escape(r['method'])}</td><td>{r['recorded_calls']}/{r['planned_calls']}</td><td>{pct(r['agreement_all_recorded'])}</td><td>{r['failed']}</td></tr>"
        for r in summary["methods"]
    )
    html = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Independent paired judgment analysis</title><style>body{font:14px/1.65 Arial,sans-serif;color:#23394a;background:#f4f6f8;margin:30px auto;max-width:1220px;padding:20px}section{background:#fff;border:1px solid #dce4ea;border-radius:8px;padding:24px;margin:18px 0}h1{font-size:28px}h2{font-size:20px}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:10px;border-bottom:1px solid #e1e7ed}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f8fa;padding:14px}summary{padding:8px 0;cursor:pointer}.notice{background:#faf3e6;padding:14px;border-left:4px solid #ad7b29}a{color:#235c82}</style><section><small>OCCUPATIONAL FITNESS PLATFORM · INDEPENDENT ENGINEERING ANALYSIS</small><h1>Retrieval coverage versus actual judgment changes</h1>"""
    html += (
        f'<p>{escape(summary["phase"])} · {summary["recorded_actual_calls"]}/{summary["planned_actual_calls"]} actual calls · {summary["patient_count"]} patients · zero additional model calls.</p><p class="notice">{escape(summary["interpretation"])}</p><table><tr><th>Model</th><th>Evidence arm</th><th>Recorded / planned</th><th>Agreement / recorded</th><th>Failures</th></tr>'
        + table
        + "</table></section>"
    )
    transition_table = ""
    for pair in summary["paired_effects"]:
        counts = pair["agreement_change_decomposition"]
        transition_table += (
            "<tr><td>"
            + escape(pair["model"])
            + "</td><td>"
            + escape(pair["pair"])
            + "</td><td>"
            + str(counts.get("valid_wrong_to_valid_correct", 0))
            + "</td><td>"
            + str(counts.get("valid_correct_to_valid_wrong", 0))
            + "</td><td>"
            + str(counts.get("invalid_to_valid_correct", 0))
            + "</td><td>"
            + str(counts.get("valid_correct_to_invalid", 0))
            + "</td><td>"
            + str(pair["net_correct_calls_from_valid_classification_changes"])
            + "</td><td>"
            + str(pair["net_correct_calls_from_contract_changes"])
            + "</td></tr>"
        )
    html += (
        "<section><h2>Separate classification changes from contract recovery</h2>"
        "<p>Valid wrong-to-correct transitions change an accepted classification. "
        "Invalid-to-valid-correct transitions instead recover an answer that previously "
        "failed its response or citation contract. The reverse transitions are counted "
        "separately. An agreement increase supported only by contract recovery does not "
        "demonstrate better classification from improved retrieval. Identical-request "
        "variation remains a separate control.</p><table><tr><th>Model</th><th>Comparison</th>"
        "<th>Valid wrong → correct</th><th>Valid correct → wrong</th>"
        "<th>Invalid → valid correct</th><th>Valid correct → invalid</th>"
        "<th>Net classification component</th><th>Net contract component</th></tr>"
        + transition_table
        + "</table></section>"
    )
    html += (
        "<section><h2>Patient-level paired effects</h2><p>Each patient contributes the mean of its three repeated calls. Missing repeats remain pending. A strict majority counts failure as a distinct vote and is reported separately. Differences of identical requests cannot be attributed to the evidence allocation.</p><pre>"
        + escape(json.dumps(summary["paired_effects"], indent=2))
        + "</pre></section>"
    )
    for case in focus:
        html += (
            "<section><h2>"
            + escape(case["case_id"])
            + "</h2><p>Engineering reference: "
            + escape(case["engineering_reference"]["reference_outcome"])
            + "; clinical review pending.</p><details><summary>Fixed patient note and verified facts</summary><pre>"
            + escape(json.dumps(case["fixed_patient"], ensure_ascii=False, indent=2))
            + "</pre></details><details><summary>Actual Blackout packet coverage per arm</summary><pre>"
            + escape(json.dumps(case["blackout_packet_coverage"], indent=2))
            + "</pre></details>"
        )
        focus_table = ""
        for observed in case["actual_observations"]:
            row, review = observed["observation"], observed["support_review"]
            anchors = review["literal_restriction_anchors"]
            cited = any(anchor["cited_by_model"] for anchor in anchors)
            outcome = row.get("answer", {}).get("assessment_outcome", "No accepted classification")
            focus_table += (
                "<tr><td>"
                + escape(row["model"])
                + "</td><td>"
                + escape(row["method"])
                + "</td><td>"
                + str(row["repeat"])
                + "</td><td>"
                + escape(row["status"])
                + "</td><td>"
                + escape(outcome)
                + "</td><td>"
                + ("Yes" if anchors else "No")
                + "</td><td>"
                + ("Yes" if cited else "No")
                + "</td></tr>"
            )
        html += (
            "<p>The supplied-clause and cited-clause columns refer only to the literal "
            "Blackout statement advising no driving until the mechanism is ascertained "
            "and the corresponding standard met. They do not certify all qualifications, "
            "exceptions or explanation entailment. Clinical and independent support review "
            "remain pending.</p><table><tr><th>Model</th><th>Arm</th><th>Repeat</th>"
            "<th>Status</th><th>Accepted outcome</th><th>Restriction supplied</th>"
            "<th>Restriction source cited</th></tr>" + focus_table + "</table>"
        )
        for arm, sources in case["actual_evidence_by_arm"].items():
            html += "<details><summary>Original evidence: " + escape(arm) + "</summary>"
            for source in sources:
                html += (
                    "<details><summary>"
                    + escape(source["source_id"])
                    + "</summary><p>Section "
                    + escape(str(source["section"]))
                    + ' · <a href="evidence_guide.pdf#page='
                    + str(source["pdf_page"])
                    + '">PDF '
                    + str(source["pdf_page"])
                    + "</a></p><pre>"
                    + escape(source["source_text"])
                    + "</pre></details>"
                )
            html += "</details>"
        for observed in case["actual_observations"]:
            row = observed["observation"]
            html += (
                "<details><summary>"
                + escape(
                    row["model"]
                    + " · "
                    + row["method"]
                    + " · repeat "
                    + str(row["repeat"])
                    + " · "
                    + row["status"]
                )
                + "</summary><pre>"
                + escape(
                    json.dumps(
                        {
                            "answer": row.get("answer"),
                            "error": row.get("error"),
                            "support_review": observed["support_review"],
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                + "</pre></details>"
            )
        html += "</section>"
    html += '<section><h2>Audit downloads</h2><p><a href="summary.json">Complete metrics</a> · <a href="method_metrics.csv">Method CSV</a> · <a href="patient_metrics.csv">Patient CSV</a> · <a href="patient_pair_metrics.csv">Paired patient CSV</a> · <a href="focus_cases.json">Two focus cases and literal evidence</a> · <a href="support_review_queue.json">Independent support-review queue</a> · <a href="observed_results.jsonl">Exact actual observations</a> · <a href="manifest.json">Provenance</a></p></section></html>'
    (output / "index.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preparation",
        type=Path,
        default=Path("outputs/experiments/case_allocation_judgment_preparation_v1"),
    )
    parser.add_argument(
        "--run", type=Path, default=Path("outputs/experiments/case_allocation_judgment_full_v1")
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    result = build(
        Path.cwd(), args.preparation, args.run, args.output, allow_partial=args.allow_partial
    )
    print(
        json.dumps(
            {
                k: result[k]
                for k in ("phase", "recorded_actual_calls", "planned_actual_calls", "complete")
            },
            indent=2,
        )
    )
