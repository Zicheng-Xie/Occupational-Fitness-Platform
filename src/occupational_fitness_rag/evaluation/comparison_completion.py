"""Audit the completed comparison from immutable calls; never rerun a judge."""

import argparse
import json
import random
from collections import Counter, defaultdict
from itertools import product
from pathlib import Path

from occupational_fitness_rag.evaluation.comparison_error_audit import patient_identity, record_key
from occupational_fitness_rag.evaluation.comparison_snapshot import read_recorded_rows
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json


def correct(row):
    return (
        row["status"] == "completed"
        and row["answer"]["assessment_outcome"] == row["reference_outcome"]
    )


def cohort_metrics(rows):
    """Recalculate reference metrics independently of the running summary helper."""
    groups = defaultdict(list)
    for row in rows:
        groups[row["cohort"], row["model"], row["method"]].append(row)
    result, class_rows = [], []
    for (cohort, model, method), group in sorted(groups.items()):
        classes = sorted({r["reference_outcome"] for r in group})
        recalls, f1s = [], []
        for label in classes:
            relevant = [r for r in group if r["reference_outcome"] == label]
            tp = sum(correct(r) for r in relevant)
            fp = sum(
                r["status"] == "completed"
                and r["answer"]["assessment_outcome"] == label
                and r["reference_outcome"] != label
                for r in group
            )
            fn = len(relevant) - tp
            recalls.append(tp / len(relevant))
            f1s.append(2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0)
            class_rows.append(
                dict(
                    cohort=cohort,
                    model=model,
                    method=method,
                    reference_outcome=label,
                    cases=len({r["case_id"] for r in relevant}),
                    calls=len(relevant),
                    correct=tp,
                    recall=tp / len(relevant),
                    failures=sum(r["status"] != "completed" for r in relevant),
                )
            )
        targets = [r for r in group if r["reference_outcome"] != "insufficient_information"]
        result.append(
            dict(
                cohort=cohort,
                model=model,
                method=method,
                cases=len({r["case_id"] for r in group}),
                calls=len(group),
                correct=sum(correct(r) for r in group),
                agreement=sum(correct(r) for r in group) / len(group),
                balanced_accuracy=sum(recalls) / len(recalls),
                macro_f1=sum(f1s) / len(f1s),
                insufficient_only_baseline=sum(
                    r["reference_outcome"] == "insufficient_information" for r in group
                )
                / len(group),
                non_abstention_reference_calls=len(targets),
                non_abstention_reference_correct=sum(correct(r) for r in targets),
                failures=sum(r["status"] != "completed" for r in group),
            )
        )
    return result, class_rows


def paired_intervals(rows, samples=2000):
    """Case-clustered paired agreement differences; failures count as incorrect."""
    indexed = {record_key(r): r for r in rows}
    groups = defaultdict(list)
    for r in rows:
        if r["method"] != "hybrid":
            groups[r["cohort"], r["model"], r["method"]].append(r)
    result = []
    for (cohort, model, method), group in sorted(groups.items()):
        differences = defaultdict(list)
        both_valid = gain = loss = failure_gain = failure_loss = mismatches = 0
        for r in group:
            b = indexed.get((r["case_id"], model, "hybrid", r["repeat"]))
            if b is None or patient_identity(b) != patient_identity(r):
                mismatches += 1
                continue
            delta = int(correct(r)) - int(correct(b))
            differences[r["case_id"]].append(delta)
            if r["status"] == b["status"] == "completed":
                both_valid += 1
                gain += delta > 0
                loss += delta < 0
            else:
                failure_gain += delta > 0
                failure_loss += delta < 0
        if not differences:
            continue
        means = [sum(v) / len(v) for v in differences.values()]
        rng = random.Random(0)
        distribution = sorted(
            sum(rng.choices(means, k=len(means))) / len(means) for _ in range(samples)
        )
        result.append(
            dict(
                cohort=cohort,
                model=model,
                method=method,
                cases=len(means),
                paired_calls=sum(map(len, differences.values())),
                agreement_delta_vs_hybrid=sum(means) / len(means),
                case_cluster_95ci=[
                    distribution[int(samples * 0.025)],
                    distribution[int(samples * 0.975) - 1],
                ],
                both_valid_pairs=both_valid,
                wrong_to_correct=gain,
                correct_to_wrong=loss,
                gain_with_a_failed_call=failure_gain,
                loss_with_a_failed_call=failure_loss,
                excluded_input_mismatches=mismatches,
            )
        )
    return result


def audit_completion(output: Path):
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    config = manifest["config"]
    labels = json.loads((output / "labels.json").read_text(encoding="utf-8"))
    corpus = json.loads((output / "corpus.json").read_text(encoding="utf-8"))
    units = {u["source_id"]: u for u in corpus["units"]}
    rows = read_recorded_rows(output / "results.jsonl")
    expected = set(
        product(
            [label["case_id"] for label in labels],
            config["models"],
            config["methods"],
            range(config["repeats"]),
        )
    )
    counts = Counter(record_key(r) for r in rows)
    issues = []
    for description, count in [
        ("missing_condition", len(expected - counts.keys())),
        ("unexpected_condition", len(counts.keys() - expected)),
        ("duplicate_condition", sum(n - 1 for n in counts.values())),
        ("planned_count_mismatch", int(manifest["planned_runs"] != len(expected))),
    ]:
        if count:
            issues.append(dict(check=description, count=count))
    expected_labels = {label["case_id"]: label for label in labels}
    checks = Counter()
    identities, payloads = defaultdict(set), defaultdict(set)
    failures = Counter()
    for row in rows:
        case_id = row["case_id"]
        payload = row["input_snapshot"]
        identities[case_id].add(patient_identity(row))
        payloads[case_id, row["method"]].add(digest(payload))
        checks["prompt_fingerprint_mismatch"] += digest(payload) != row["prompt_sha256"]
        label = expected_labels.get(case_id)
        checks["reference_label_mismatch"] += (
            label is None or row["reference_outcome"] != label["expected_outcome"]
        )
        evidence = payload["guideline_evidence"]
        supplied = {s["source_id"] for s in evidence}
        checks["evidence_budget_violation"] += (
            len(json.dumps(evidence).encode()) > config["evidence_max_bytes"]
            or len(evidence) > config["top_k"]
        )
        checks["reference_fields_in_judge_input"] += bool(
            {"reference_outcome", "expected_outcome", "rule_outcome", "reference_source_ids"}
            & payload.keys()
        )
        checks["control_contains_evidence"] += row["method"] == "no_evidence" and bool(evidence)
        for source in evidence:
            unit = units.get(source["source_id"])
            checks["original_source_mapping_mismatch"] += unit is None or any(
                source.get(key) != unit.get(key if key != "source_text" else "evidence_text")
                for key in ["source_text", "section", "pdf_page", "printed_page"]
            )
        if row["status"] == "completed":
            answer = row["answer"]
            checks["invalid_accepted_source"] += bool(set(answer["source_ids"]) - supplied)
            checks["invalid_accepted_fact"] += bool(
                set(answer["fact_fields"]) - payload["verified_patient_facts"].keys()
            )
            checks["accepted_without_required_citation"] += (
                row["method"] != "no_evidence" and not answer["source_ids"]
            )
            checks["agreement_flag_mismatch"] += bool(row["reference_agreement"]) != correct(row)
        else:
            failures[row.get("error", "Unspecified failure")] += 1
            checks["failed_without_raw_response"] += "raw_response" not in row
    checks["patient_input_mismatches"] = sum(len(v) != 1 for v in identities.values())
    checks["evidence_changed_between_models_or_repeats"] = sum(
        len(v) != 1 for v in payloads.values()
    )
    issues.extend(dict(check=k, count=v) for k, v in checks.items() if v)
    metrics, classes = cohort_metrics(rows)
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    indexed = {(m["cohort"], m["model"], m["method"]): m for m in summary["metrics"]}
    reconciled = True
    for m in metrics:
        prior = indexed.get((m["cohort"], m["model"], m["method"]))
        if prior is None or any(
            abs(m[a] - prior[b]) > 1e-10
            for a, b in [
                ("agreement", "agreement_all_runs"),
                ("macro_f1", "macro_f1"),
                ("failures", "failures"),
                ("calls", "runs"),
            ]
        ):
            reconciled = False
    if not reconciled:
        issues.append(dict(check="summary_reconciliation_failed", count=1))
    evidence_review = output / "retrieval_review.csv"
    result = dict(
        status="passed" if not issues else "needs_revision",
        planned_calls=manifest["planned_runs"],
        recorded_calls=len(rows),
        matrix_complete=set(counts) == expected and len(rows) == len(expected),
        accepted_calls=sum(r["status"] == "completed" for r in rows),
        failed_calls=sum(failures.values()),
        failure_reasons=dict(failures),
        checks=dict(checks),
        issues=issues,
        summary_reconciled=reconciled,
        metrics=metrics,
        class_metrics=classes,
        paired_differences=paired_intervals(rows),
        source_fingerprints={
            name: sha256_bytes((output / name).read_bytes())
            for name in ["results.jsonl", "manifest.json", "corpus.json", "labels.json"]
        },
        evidence_review_worksheet=evidence_review.name,
        explanation_support="pending_independent_review",
        clinical_accuracy=None,
        production_change=False,
        decision="Keep production retrieval unchanged; prioritize judgment and upstream review diagnostics.",
        interpretation=[
            "Completed execution includes recorded failures; it does not mean all calls passed.",
            "Balanced accuracy averages recall over reference classes present in each cohort.",
            "Insufficient-only baseline uses fixed reference labels, not model outputs.",
            "Paired confidence intervals resample cases, not individual repeated calls.",
            "This audit validates engineering records and calculations, not clinical accuracy or entailment.",
        ],
    )
    write_json(output / "completion_audit.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    result = audit_completion(parser.parse_args().output)
    print(
        json.dumps({k: result[k] for k in ["status", "recorded_calls", "failed_calls", "issues"]})
    )
