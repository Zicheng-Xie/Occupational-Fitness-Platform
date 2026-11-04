"""Audit completed applicability results by reference cohort and evidence policy.

Repeated calls are condition observations, not additional patients. Module slices
use the overall case reference label; they are not disease-specific judgments.
"""

import argparse
import csv
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from html import escape
from pathlib import Path

CLASSES = (
    "meets_unconditional_standard",
    "may_meet_conditional_standard",
    "temporarily_unfit",
    "does_not_meet_standard",
    "insufficient_information",
)
DEVELOPMENT_CASES = {
    "SYN-EXT-002",
    "SYN-EXT-003",
    "SYN-EXT-008",
    "SYN-EXT-020",
    "VAL-MIX-02",
    "VAL-MIX-04",
    "VAL-MIX-06",
    "VAL-MIX-07",
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha256(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    )


def load_renderer():
    spec = importlib.util.spec_from_file_location(
        "applicability_report_reader", Path(__file__).with_name("render_applicability_report.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prediction(row):
    if row["status"] == "completed":
        result = row["answer"]["assessment_outcome"]
        if result not in CLASSES:
            raise ValueError("Unknown accepted outcome")
        return result
    return None


def classification_metrics(rows):
    matrix = {truth: {result: 0 for result in (*CLASSES, "execution_failure")} for truth in CLASSES}
    for row in rows:
        truth = row["reference_outcome"]
        if truth not in CLASSES:
            raise ValueError("Unknown engineering reference")
        matrix[truth][prediction(row) or "execution_failure"] += 1
    per_class = {}
    for label in CLASSES:
        tp = matrix[label][label]
        support = sum(matrix[label].values())
        fp = sum(matrix[truth][label] for truth in CLASSES if truth != label)
        fn = support - tp
        per_class[label] = {
            "reference_conditions": support,
            "true_positive": tp,
            "false_positive": fp,
            "false_negative_including_execution_failure": fn,
            "recall": tp / support if support else 0.0,
            "precision": tp / (tp + fp) if tp + fp else 0.0,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
        }
    correct = sum(matrix[label][label] for label in CLASSES)
    valid = sum(row["status"] == "completed" for row in rows)
    case_rows = defaultdict(list)
    for row in rows:
        case_rows[row["case_id"]].append(row)
    present = [value for value in per_class.values() if value["reference_conditions"]]
    insufficient = "insufficient_information"
    over_insufficient = sum(
        matrix[truth][insufficient] for truth in CLASSES if truth != insufficient
    )
    non_insufficient = sum(
        sum(matrix[truth].values()) for truth in CLASSES if truth != insufficient
    )
    return {
        "condition_count": len(rows),
        "distinct_case_count": len(case_rows),
        "valid_conditions": valid,
        "failed_conditions": len(rows) - valid,
        "correct_conditions": correct,
        "reference_agreement_all_conditions": correct / len(rows) if rows else None,
        "reference_agreement_valid_only": correct / valid if valid else None,
        "distinct_cases_correct_in_every_recorded_repeat": sum(
            all(prediction(row) == row["reference_outcome"] for row in group)
            for group in case_rows.values()
        ),
        "always_insufficient_baseline_agreement": sum(matrix[insufficient].values()) / len(rows)
        if rows
        else None,
        "over_insufficient_conditions": over_insufficient,
        "over_insufficient_rate_non_insufficient_reference": over_insufficient / non_insufficient
        if non_insufficient
        else None,
        "macro_f1_fixed_five_classes": sum(value["f1"] for value in per_class.values())
        / len(CLASSES),
        "macro_f1_present_reference_classes": sum(value["f1"] for value in present) / len(present)
        if present
        else None,
        "balanced_accuracy_present_reference_classes": sum(value["recall"] for value in present)
        / len(present)
        if present
        else None,
        "present_reference_class_count": len(present),
        "per_class": per_class,
        "confusion_matrix": matrix,
        "failure_convention": "Execution failure occupies its own prediction column and counts as a false negative for the reference class; absent-class F1 is zero.",
    }


def transition(before, after):
    left, right = prediction(before), prediction(after)
    if left is None and right is None:
        return "both_failed"
    if left is None:
        return "failed_to_valid"
    if right is None:
        return "valid_to_failed"
    good_left = left == before["reference_outcome"]
    good_right = right == after["reference_outcome"]
    if good_left and good_right:
        return "both_correct"
    if good_left:
        return "accepted_correct_to_wrong"
    if good_right:
        return "accepted_wrong_to_correct"
    return "both_wrong"


def cohorts(labels, upstream):
    names = [label["case_id"] for label in labels]
    if len(set(names)) != len(names):
        raise ValueError("Duplicate engineering reference case")
    all_cases = set(names)
    upstream_cases = {row["case_id"]: row for row in upstream["cases"]}
    if len(upstream_cases) != len(upstream["cases"]) or set(upstream_cases) != all_cases:
        raise ValueError("Upstream audit must cover the original reference cases exactly once")
    if any(row["cohort"] not in {"engineering", "complex"} for row in labels):
        raise ValueError("Unknown engineering cohort")
    if any(
        upstream_cases[row["case_id"]]["reference"] != row["expected_outcome"] for row in labels
    ):
        raise ValueError("Upstream audit reference differs from the original label")
    differences = {
        row["case_id"] for row in upstream["cases"] if row["reference"] != row["frozen_outcome"]
    }
    development = DEVELOPMENT_CASES & all_cases
    remaining = all_cases - development
    return {
        "all_reference_cases": all_cases,
        "engineering_reference_cases": {
            row["case_id"] for row in labels if row["cohort"] == "engineering"
        },
        "complex_validation_cases": {
            row["case_id"] for row in labels if row["cohort"] == "complex"
        },
        "known_error_development_cases": development,
        "remaining_reference_cases": remaining,
        "without_upstream_outcome_discrepancies": all_cases - differences,
        "remaining_without_upstream_outcome_discrepancies": remaining - differences,
        "upstream_outcome_discrepancy_cases": differences,
    }


def analyze(rows, labels, upstream):
    reference = {item["case_id"]: item for item in labels}
    cohort_sets = cohorts(labels, upstream)
    for row in rows:
        if (
            row["case_id"] not in reference
            or row["reference_outcome"] != reference[row["case_id"]]["expected_outcome"]
        ):
            raise ValueError(
                "Recorded reference differs from the pinned original engineering label"
            )
        if digest(row["input_snapshot"]) != row["input_sha256"]:
            raise ValueError("Recorded input payload differs from its fingerprint")
    requested_modules = defaultdict(set)
    for row in rows:
        for module in row["input_snapshot"]["modules"]:
            requested_modules[module].add(row["case_id"])
    slices = {
        **cohort_sets,
        **{"requested_module_" + key: value for key, value in requested_modules.items()},
    }
    groups = defaultdict(list)
    for row in rows:
        for name, case_ids in slices.items():
            if row["case_id"] in case_ids:
                groups[name, row["model"], row["evidence_policy"], row["protocol"]].append(row)
    metrics = [
        {
            "cohort": key[0],
            "model": key[1],
            "evidence_policy": key[2],
            "protocol": key[3],
            **classification_metrics(group),
        }
        for key, group in sorted(groups.items())
    ]
    paired = defaultdict(dict)
    for row in rows:
        key = row["case_id"], row["model"], row["protocol"], row["repeat"]
        paired[key][row["evidence_policy"]] = row
    policy_pairs = []
    for key, group in sorted(paired.items()):
        if set(group) != {"module_query", "reference_evidence"}:
            raise ValueError("Every evidence-policy comparison needs both fixed policies")
        before, after = group["module_query"], group["reference_evidence"]
        left, right = before["input_snapshot"], after["input_snapshot"]
        if digest({k: v for k, v in left.items() if k != "guideline_evidence"}) != digest(
            {k: v for k, v in right.items() if k != "guideline_evidence"}
        ):
            raise ValueError("Evidence policies received different patient facts")
        policy_pairs.append(
            {
                "case_id": key[0],
                "model": key[1],
                "protocol": key[2],
                "repeat": key[3],
                "reference_outcome": before["reference_outcome"],
                "module_query_outcome": prediction(before),
                "reference_evidence_outcome": prediction(after),
                "transition": transition(before, after),
                "both_accepted_prediction_changed": prediction(before) is not None
                and prediction(after) is not None
                and prediction(before) != prediction(after),
                "module_query_sources": left["guideline_evidence"],
                "reference_evidence_sources": right["guideline_evidence"],
                "module_query_input_sha256": before["input_sha256"],
                "reference_evidence_input_sha256": after["input_sha256"],
            }
        )
    pair_groups = defaultdict(list)
    for pair in policy_pairs:
        for name, case_ids in slices.items():
            if pair["case_id"] in case_ids:
                pair_groups[name, pair["model"], pair["protocol"]].append(pair)
    paired_metrics = [
        {
            "cohort": key[0],
            "model": key[1],
            "protocol": key[2],
            "pair_conditions": len(group),
            "distinct_case_count": len({pair["case_id"] for pair in group}),
            "transitions": dict(Counter(pair["transition"] for pair in group)),
            "accepted_changed_prediction_conditions": sum(
                pair["both_accepted_prediction_changed"] for pair in group
            ),
            "failed_to_valid_correct_conditions": sum(
                pair["transition"] == "failed_to_valid"
                and pair["reference_evidence_outcome"] == pair["reference_outcome"]
                for pair in group
            ),
            "valid_to_failed_previously_correct_conditions": sum(
                pair["transition"] == "valid_to_failed"
                and pair["module_query_outcome"] == pair["reference_outcome"]
                for pair in group
            ),
        }
        for key, group in sorted(pair_groups.items())
    ]
    return {
        "metric_name": "Engineering reference agreement",
        "clinical_accuracy": None,
        "production_change": False,
        "clinical_review": "pending",
        "cohort_membership": {name: sorted(ids) for name, ids in slices.items()},
        "cohort_reference_counts": {
            name: dict(Counter(reference[case_id]["expected_outcome"] for case_id in case_ids))
            for name, case_ids in slices.items()
        },
        "cohort_recorded_case_ids": {
            name: sorted(case_ids & {row["case_id"] for row in rows})
            for name, case_ids in slices.items()
        },
        "observed_case_count": len({row["case_id"] for row in rows}),
        "recorded_conditions": len(rows),
        "metrics": metrics,
        "paired_evidence_policy_metrics": paired_metrics,
        "evidence_policy_pairs": policy_pairs,
        "interpretation": "Cohorts overlap and must not be pooled as independent samples. Repeats are independent model calls on the same cases, not additional patients. All 33 reference cases have been observed in earlier experiments; remaining means unused for the recent eight-case protocol development, not unseen validation. Requested-module slices use the overall case reference and cannot establish disease-specific accuracy. Reference evidence is an oracle control, not an alternative production retrieval method. Source validity is distinct from explanation support, which remains pending independent review.",
    }


def export_report(directory, labels_path, upstream_path, expected_results_sha256=None):
    directory, labels_path, upstream_path = map(Path, (directory, labels_path, upstream_path))
    reader = load_renderer()
    manifest, rows, _, provenance = reader.read_completed_snapshot(
        directory, expected_results_sha256
    )
    audit_path = directory / "execution_audit.json"
    if audit_path.exists():
        audit_raw = audit_path.read_bytes()
        if json.loads(audit_raw)["results_sha256"] != provenance["results_sha256"]:
            raise ValueError("Raw results differ from their completion audit")
        provenance["execution_audit_sha256"] = sha256(audit_raw)
    labels_raw, upstream_raw = labels_path.read_bytes(), upstream_path.read_bytes()
    report = analyze(rows, json.loads(labels_raw), json.loads(upstream_raw))
    provenance.update(
        experiment_identity=manifest["identity"],
        labels_sha256=sha256(labels_raw),
        upstream_audit_sha256=sha256(upstream_raw),
        analyzer_sha256=sha256(Path(__file__).read_bytes()),
        snapshot_reader_sha256=sha256(
            Path(__file__).with_name("render_applicability_report.py").read_bytes()
        ),
    )
    report["provenance"] = provenance
    json_path = directory / "cohort_report.json"
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8"
    )
    csv_keys = [key for key, value in report["metrics"][0].items() if not isinstance(value, dict)]
    with (directory / "cohort_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(report["metrics"])

    def pct(value):
        return "—" if value is None else f"{100 * value:.1f}%"

    table = "".join(
        "<tr>"
        + "".join(
            "<td>" + escape(str(value)) + "</td>"
            for value in [
                row["cohort"],
                row["model"],
                row["evidence_policy"],
                row["protocol"],
                row["distinct_case_count"],
                row["condition_count"],
                f"{row['correct_conditions']}/{row['condition_count']}",
                row["failed_conditions"],
                pct(row["reference_agreement_all_conditions"]),
                pct(row["always_insufficient_baseline_agreement"]),
                pct(row["macro_f1_fixed_five_classes"]),
                pct(row["macro_f1_present_reference_classes"]),
                pct(row["balanced_accuracy_present_reference_classes"]),
            ]
        )
        + "</tr>"
        for row in report["metrics"]
    )
    html = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Applicability cohort analysis</title><style>body{font:14px/1.6 Segoe UI,Arial;color:#243244;margin:32px}table{border-collapse:collapse}td,th{padding:10px;border-bottom:1px solid #dce3e9;text-align:left}p{max-width:1100px}.scroll{overflow:auto}</style><h1>Applicability cohort analysis</h1>'
    html += f"<p>{report['observed_case_count']} distinct observed cases · {report['recorded_conditions']} recorded model conditions · Engineering reference agreement; clinical review pending.</p><p>{escape(report['interpretation'])}</p><div class=scroll><table><tr>"
    html += "".join(
        f"<th>{name}</th>"
        for name in [
            "Cohort",
            "Model",
            "Evidence",
            "Protocol",
            "Cases",
            "Conditions",
            "Correct/all",
            "Failures",
            "Agreement",
            "Always insufficient",
            "Macro-F1 five",
            "Macro-F1 present",
            "Balanced recall present",
        ]
    )
    html += (
        "</tr>"
        + table
        + "</table></div><h2>Policy transitions</h2><p>Direction: module-query evidence → reference evidence. Conditions share patient facts, model, protocol, and repeat. Failure recovery is separate from accepted wrong-to-correct changes. A better reference label match does not establish supported reasoning.</p><div class=scroll><table><tr>"
    )
    transition_names = [
        "accepted_wrong_to_correct",
        "accepted_correct_to_wrong",
        "both_correct",
        "both_wrong",
        "failed_to_valid",
        "valid_to_failed",
        "both_failed",
    ]
    html += (
        "".join(
            f"<th>{escape(name)}</th>"
            for name in ["Cohort", "Model", "Protocol", "Cases", "Pairs", *transition_names]
        )
        + "</tr>"
    )
    for row in report["paired_evidence_policy_metrics"]:
        values = [
            row["cohort"],
            row["model"],
            row["protocol"],
            row["distinct_case_count"],
            row["pair_conditions"],
            *[row["transitions"].get(name, 0) for name in transition_names],
        ]
        html += (
            "<tr>" + "".join("<td>" + escape(str(value)) + "</td>" for value in values) + "</tr>"
        )
    html += '</table></div><p><a href="cohort_report.json">Complete confusion matrices, per-class recall and every paired original passage</a> · <a href="cohort_metrics.csv">Metrics CSV</a> · <a href="review.html">Case review report</a></p></html>'
    (directory / "cohort_report.html").write_text(html, encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    parser.add_argument(
        "--labels", default="outputs/experiments/judgment_comparison_v5/labels.json"
    )
    parser.add_argument(
        "--upstream", default="outputs/experiments/judgment_comparison_v5/upstream_audit.json"
    )
    parser.add_argument("--expected-results-sha256")
    args = parser.parse_args()
    result = export_report(args.directory, args.labels, args.upstream, args.expected_results_sha256)
    print(
        json.dumps(
            {
                "observed_cases": result["observed_case_count"],
                "conditions": result["recorded_conditions"],
                "groups": len(result["metrics"]),
                "results_sha256": result["provenance"]["results_sha256"],
            }
        )
    )
