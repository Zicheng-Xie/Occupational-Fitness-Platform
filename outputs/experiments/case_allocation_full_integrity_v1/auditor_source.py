"""Independently audit frozen paired judgments without model or network calls.

Default execution requires the completed 990-condition run. A requested partial
snapshot records only the captured newline-complete prefix and is never scored
as a completed comparison. Existing inputs and observations are read only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.evaluation.judgment_comparison import SYSTEM
from occupational_fitness_rag.evaluation.model_judgment import ExperimentalJudgment
from occupational_fitness_rag.evaluation.passage_comparison import patient_identity
from occupational_fitness_rag.provenance import digest, write_json

PREPARATION = "case_allocation_judgment_preparation_v1"
RUN = "case_allocation_judgment_full_v1"
PILOT = "case_allocation_judgment_pilot_v1"
SERIES = "case_allocation_series_v2"
ARMS = (
    "hybrid",
    "seventh_round_robin",
    "seventh_case_coverage",
    "ninth_round_robin",
    "ninth_case_coverage",
)
OUTCOMES = (
    "meets_unconditional_standard",
    "may_meet_conditional_standard",
    "temporarily_unfit",
    "does_not_meet_standard",
    "insufficient_information",
)
BODY_KEYS = {
    "licence_context",
    "modules",
    "nurse_note",
    "verified_patient_facts",
    "guideline_evidence",
}
PAIRS = {
    "retrieval_seventh": ("hybrid", "seventh_round_robin"),
    "retrieval_ninth": ("hybrid", "ninth_round_robin"),
    "allocation_seventh": ("seventh_round_robin", "seventh_case_coverage"),
    "allocation_ninth": ("ninth_round_robin", "ninth_case_coverage"),
    "combined_seventh": ("hybrid", "seventh_case_coverage"),
    "combined_ninth": ("hybrid", "ninth_case_coverage"),
}


def read(path):
    return json.loads(Path(path).read_bytes())


def identity(value):
    return digest({k: v for k, v in value.items() if k not in {"identity", "production_change"}})


def verify_inventory(directory):
    directory = Path(directory).resolve()
    pins = read(directory / "artifacts.json")
    if not isinstance(pins, dict) or not pins:
        raise ValueError("An immutable inventory is missing or empty")
    for rel, expected in pins.items():
        path = (directory / rel).resolve()
        if not path.is_relative_to(directory) or file_hash(path) != expected:
            raise ValueError("Immutable artifact differs: " + str(path))
    return pins


def record_key(row):
    return tuple(row[k] for k in ("case_id", "method", "model", "repeat"))


def read_prefix(path):
    """Capture complete records without changing or repairing the live file."""
    raw = Path(path).read_bytes()
    tail_bytes = 0
    if raw and not raw.endswith(b"\n"):
        complete, separator, tail = raw.rpartition(b"\n")
        raw, tail_bytes = complete + separator, len(tail)
    records = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    return records, raw, tail_bytes


def validate_raw(row, payload, config):
    """Apply the public output contract independently of the dispatch runner."""
    raw = row.get("raw_response")
    if not isinstance(raw, dict):
        return None, "provider_response_missing"
    if raw.get("model") != row["model"]:
        return None, "provider_model_differs"
    if raw.get("done") is not True or raw.get("done_reason") != "stop":
        return None, "incomplete_provider_completion"
    count = raw.get("prompt_eval_count")
    if (
        type(count) is not int
        or not 0 <= count <= config["context_length"] - config["output_tokens"]
    ):
        return None, "context_reservation_failed"
    try:
        answer = ExperimentalJudgment.model_validate_json(raw["message"]["content"])
    except (ValueError, KeyError, TypeError):
        return None, "response_schema_failed"
    if set(answer.source_ids) - {s["source_id"] for s in payload["guideline_evidence"]}:
        return None, "unavailable_source_citation"
    if not answer.source_ids:
        return None, "empty_source_citations"
    if set(answer.fact_fields) - set(payload["verified_patient_facts"]):
        return None, "unavailable_fact_citation"
    if any("\u3400" <= c <= "\u9fff" for c in answer.explanation):
        return None, "non_english_explanation"
    return answer.model_dump(mode="json"), None


def independently_score(rows, labels):
    metrics, patients = [], []
    groups = defaultdict(list)
    for row in rows:
        groups[(row["model"], row["method"])].append(row)
    for (model, arm), group in sorted(groups.items()):
        matrix = {a: {b: 0 for b in OUTCOMES} for a in OUTCOMES}
        accepted = [r for r in group if r["status"] == "completed"]
        for row in accepted:
            matrix[labels[row["case_id"]]["reference_outcome"]][
                row["answer"]["assessment_outcome"]
            ] += 1
        correct = sum(matrix[x][x] for x in OUTCOMES)
        f1s = []
        for outcome in OUTCOMES:
            tp = matrix[outcome][outcome]
            fp = sum(matrix[a][outcome] for a in OUTCOMES if a != outcome)
            fn = sum(matrix[outcome][b] for b in OUTCOMES if b != outcome)
            if tp + fp + fn:
                f1s.append(2 * tp / (2 * tp + fp + fn))
        insufficient = [
            r for r in accepted if r["answer"]["assessment_outcome"] == "insufficient_information"
        ]
        metrics.append(
            {
                "model": model,
                "method": arm,
                "recorded": len(group),
                "accepted": len(accepted),
                "failed": len(group) - len(accepted),
                "correct": correct,
                "engineering_reference_agreement_all_recorded": correct / len(group),
                "engineering_reference_agreement_accepted": correct / len(accepted)
                if accepted
                else None,
                "macro_f1_over_observed_classes_accepted": sum(f1s) / len(f1s) if f1s else None,
                "insufficient_predictions": len(insufficient),
                "insufficient_predictions_matching_reference": sum(
                    labels[r["case_id"]]["reference_outcome"] == "insufficient_information"
                    for r in insufficient
                ),
                "insufficient_predictions_against_other_reference": sum(
                    labels[r["case_id"]]["reference_outcome"] != "insufficient_information"
                    for r in insufficient
                ),
                "confusion_matrix_accepted": matrix,
            }
        )
        by_case = defaultdict(list)
        for row in group:
            by_case[row["case_id"]].append(row)
        for case, observations in sorted(by_case.items()):
            valid = [r for r in observations if r["status"] == "completed"]
            votes = Counter(r["answer"]["assessment_outcome"] for r in valid)
            majority = next((label for label, n in votes.items() if n >= 2), None)
            patients.append(
                {
                    "case_id": case,
                    "model": model,
                    "method": arm,
                    "recorded_repeats": len(observations),
                    "expected_repeats": 3,
                    "complete_repeated_condition": len(observations) == 3,
                    "accepted_repeats": len(valid),
                    "votes": dict(votes),
                    "reference_outcome": labels[case]["reference_outcome"],
                    "majority_outcome": majority,
                    "majority_correct": majority == labels[case]["reference_outcome"]
                    if len(observations) == 3
                    else None,
                    "correct_repeats": sum(
                        r["answer"]["assessment_outcome"] == labels[case]["reference_outcome"]
                        for r in valid
                    ),
                    "unit_of_independence": "patient, not repeated call",
                }
            )
    return metrics, patients


def paired_decomposition(rows, labels):
    """Explain all-recorded correctness changes without calling failures answers."""
    index = {record_key(r): r for r in rows}
    if len(index) != len(rows):
        raise ValueError("Duplicate actual conditions")
    result = []
    groups = sorted({(r["model"], r["case_id"], r["repeat"]) for r in rows})
    for model in sorted({r["model"] for r in rows}):
        for name, (left, right) in PAIRS.items():
            counts = Counter()
            identical_variations = 0
            same_delta, changed_delta = 0, 0
            for observed_model, case, repeat in groups:
                if observed_model != model:
                    continue
                a, b = [index.get((case, method, model, repeat)) for method in (left, right)]
                if a is None or b is None:
                    counts["pending_pair"] += 1
                    continue
                expected = labels[case]["reference_outcome"]
                valid_a, valid_b = [r["status"] == "completed" for r in (a, b)]
                before, after = [r.get("answer", {}).get("assessment_outcome") for r in (a, b)]
                correct_a, correct_b = valid_a and before == expected, valid_b and after == expected
                same = a["request_identity"] == b["request_identity"]
                delta = int(correct_b) - int(correct_a)
                if same:
                    same_delta += delta
                    identical_variations += (valid_a != valid_b) or (
                        valid_a and valid_b and before != after
                    )
                else:
                    changed_delta += delta
                if valid_a and valid_b:
                    change = (
                        "valid_wrong_to_correct"
                        if not correct_a and correct_b
                        else "valid_correct_to_wrong"
                        if correct_a and not correct_b
                        else "valid_unchanged_correct"
                        if correct_a and correct_b
                        else "valid_wrong_to_wrong"
                    )
                elif not valid_a and valid_b:
                    change = (
                        "contract_recovery_to_correct"
                        if correct_b
                        else "contract_recovery_to_wrong"
                    )
                elif valid_a and not valid_b:
                    change = (
                        "correct_to_contract_failure" if correct_a else "wrong_to_contract_failure"
                    )
                else:
                    change = "both_contract_failures"
                counts[change] += 1
            valid_delta = counts["valid_wrong_to_correct"] - counts["valid_correct_to_wrong"]
            contract_delta = (
                counts["contract_recovery_to_correct"] - counts["correct_to_contract_failure"]
            )
            if valid_delta + contract_delta != same_delta + changed_delta:
                raise ValueError("Paired correctness decomposition does not reconcile")
            result.append(
                {
                    "model": model,
                    "pair": name,
                    "counts": dict(counts),
                    "valid_prediction_net_correct": valid_delta,
                    "contract_net_correct": contract_delta,
                    "all_recorded_net_correct": valid_delta + contract_delta,
                    "same_request_net_correct": same_delta,
                    "changed_request_net_correct": changed_delta,
                    "identical_request_outcome_or_contract_variations": identical_variations,
                }
            )
    return result


def audit(root, output, allow_partial=False, check_only=False):
    root, output = Path(root).resolve(), Path(output).resolve()
    experiments = root / "outputs/experiments"
    if output.exists() or not output.is_relative_to(experiments):
        raise ValueError("Use a fresh isolated audit output")
    prep, run, pilot, series = [experiments / name for name in (PREPARATION, RUN, PILOT, SERIES)]
    prep_pins, pilot_pins = verify_inventory(prep), verify_inventory(pilot)
    manifest, plan, serial = (
        read(prep / "manifest.json"),
        read(run / "plan.json"),
        read(series / "plan.json"),
    )
    if (
        identity(manifest) != manifest["identity"]
        or identity(plan) != plan["identity"]
        or digest({k: v for k, v in serial.items() if k != "identity"}) != serial["identity"]
    ):
        raise ValueError("Manifest self identity differs")
    config = manifest["config"]
    if (
        plan["runtime"]["models"] != config["expected_model_digests"]
        or plan["runtime"]["version"].get("version") != config["expected_runtime_version"]
        or serial["models_serial"] != config["models"]
    ):
        raise ValueError("Frozen runtime/model identity or serial staging differs")
    if (
        plan["preparation_identity"] != manifest["identity"]
        or plan["preparation_artifacts"] != prep_pins
        or serial["preparation_artifacts"] != prep_pins
    ):
        raise ValueError("Actual run or serial preparation differs")
    if serial["pilot_calls_imported"] != 0 or serial["pilot_artifacts_sha256"] != file_hash(
        pilot / "artifacts.json"
    ):
        raise ValueError("Pilot import/call lineage differs")
    for source, expected in {**manifest["sources"], **plan["sources"], **serial["sources"]}.items():
        if file_hash(root / source) != expected:
            raise ValueError("An executing or preparation source changed")
    payloads, requests, conditions = [
        read(prep / name) for name in ("payloads.json", "requests.json", "conditions.json")
    ]
    run_requests, run_payloads = read(run / "requests.json"), read(run / "payloads.json")
    if (
        run_requests != requests
        or run_payloads != payloads
        or digest(requests) != plan["requests_sha256"]
    ):
        raise ValueError("Actor request or payload snapshot differs")
    labels = read(prep / "scoring_labels.json")
    for field, value in (
        ("payloads_sha256", payloads),
        ("requests_sha256", requests),
        ("conditions_sha256", conditions),
        ("labels_sha256", labels),
    ):
        if manifest[field] != digest(value):
            raise ValueError("Prepared semantic content identity differs: " + field)
    expected = {
        (case, arm, model, repeat)
        for case in labels
        for arm in ARMS
        for model in config["models"]
        for repeat in range(3)
    }
    if (
        len(labels) != 33
        or len(config["models"]) != 2
        or len(conditions) != 990
        or {record_key(c) for c in conditions} != expected
    ):
        raise ValueError("The fixed 33 x 5 x 2 x 3 inventory differs")
    if {record_key(c): c for c in conditions} != {record_key(c): c for c in plan["conditions"]}:
        raise ValueError("Actual condition inventory differs")
    pmap = {(r["case_id"], r["method"]): r for r in payloads}
    patient_ids = {}
    for row in payloads:
        payload, case = row["payload"], row["case_id"]
        if set(payload) != BODY_KEYS:
            raise ValueError("Model-visible payload contains additional scoring metadata")
        patient_ids.setdefault(case, patient_identity(payload))
        if patient_ids[case] != patient_identity(payload):
            raise ValueError("Patient facts differ across evidence arms")
    for c in conditions:
        body = requests[c["request_identity"]]
        if digest(body) != c["request_identity"] or body != run_requests[c["request_identity"]]:
            raise ValueError("Exact model request differs")
        if (
            body["messages"][0] != {"role": "system", "content": SYSTEM}
            or len(body["messages"]) != 2
        ):
            raise ValueError("Fixed system instructions differ")
        if (
            json.loads(body["messages"][1]["content"])
            != pmap[(c["case_id"], c["method"])]["payload"]
        ):
            raise ValueError("Condition body differs from its fixed case/evidence payload")
        if body["model"] != c["model"] or body["options"] != {
            "temperature": 0,
            "seed": 0,
            "num_ctx": config["context_length"],
            "num_predict": config["output_tokens"],
        }:
            raise ValueError("Model or generation options differ")
        if set(body["format"]["properties"]["assessment_outcome"]["enum"]) != set(OUTCOMES):
            raise ValueError("Model output outcomes have been narrowed using an answer label")
    rows, prefix, tail_bytes = read_prefix(run / "results.jsonl")
    ordered = sorted(
        conditions,
        key=lambda c: (config["models"].index(c["model"]), c["repeat"], c["case_id"], c["method"]),
    )
    if len(rows) > 990 or [record_key(r) for r in rows] != [
        record_key(c) for c in ordered[: len(rows)]
    ]:
        raise ValueError("Actual calls are repeated, skipped or out of serial protocol order")
    complete = len(rows) == 990 and tail_bytes == 0
    if not allow_partial and (
        not complete or (series / ".run.lock").exists() or (run / ".run.lock").exists()
    ):
        raise ValueError("Wait for the completed run; partial prefixes are not full comparisons")
    pilot_rows, _, pilot_tail = read_prefix(pilot / "results.jsonl")
    if len(pilot_rows) != 150 or pilot_tail:
        raise ValueError("Completed mechanism-pilot inventory differs")
    pilot_raw_ids = {digest(r["raw_response"]) for r in pilot_rows if "raw_response" in r}
    actual_plan = {record_key(c): c for c in conditions}
    nonces, failures, costs = set(), Counter(), defaultdict(list)
    for row in rows:
        c = actual_plan[record_key(row)]
        if (
            row["request_identity"] != c["request_identity"]
            or row["payload_identity"] != c["payload_identity"]
            or row["experiment_identity"] != plan["identity"]
        ):
            raise ValueError("Observed call is bound to a different planned request")
        if (
            row["status"] not in {"completed", "failed"}
            or type(row["seconds"]) not in {int, float}
            or row["seconds"] < 0
        ):
            raise ValueError("Invalid actual attempt status or timing")
        answer, reason = validate_raw(row, pmap[(row["case_id"], row["method"])]["payload"], config)
        if row["status"] == "completed":
            if reason is not None or row["answer"] != answer:
                raise ValueError("Accepted answer differs from its actual provider completion")
        else:
            if reason is None:
                raise ValueError("A failed row actually satisfies the output contract")
            failures[reason] += 1
        raw = row.get("raw_response")
        if raw is not None:
            if digest(raw) in pilot_raw_ids:
                raise ValueError("A full-run response was copied from the mechanism pilot")
            nonce = (raw.get("model"), raw.get("created_at"))
            if not nonce[1] or nonce in nonces:
                raise ValueError("Raw provider response identity is absent or duplicated")
            nonces.add(nonce)
        costs[(row["model"], row["method"])].append(row)
    metrics, patient_aggregates = independently_score(rows, labels)
    checked_summary = None
    if complete and not (run / ".run.lock").exists():
        run_pins = verify_inventory(run)
        summary = read(run / "summary.json")
        if (
            not summary["complete"]
            or summary["recorded"] != 990
            or summary["actual_judgment_calls"] != 990
        ):
            raise ValueError("Completed actor summary inventory differs")
        by_group = {(m["model"], m["method"]): m for m in summary["metrics"]}
        for m in metrics:
            actual = by_group[(m["model"], m["method"])]
            if any(actual[k] != v for k, v in m.items()):
                raise ValueError("Independent scoring differs from the actor summary")
        if summary["failed"] != sum(failures.values()) or summary["accepted"] != 990 - sum(
            failures.values()
        ):
            raise ValueError("Completed accepted/failed counts differ")
        checked_summary = file_hash(run / "summary.json")
    else:
        run_pins = None
    cost_rows = []
    for (model, arm), group in sorted(costs.items()):
        raw = [r["raw_response"] for r in group if "raw_response" in r]
        cost_rows.append(
            {
                "model": model,
                "method": arm,
                "actual_attempts": len(group),
                "provider_responses": len(raw),
                "attempt_seconds": sum(r["seconds"] for r in group),
                "provider_total_seconds": sum(r.get("total_duration", 0) for r in raw) / 1e9,
                "generated_tokens": sum(r.get("eval_count", 0) for r in raw),
                "prompt_tokens": sum(r.get("prompt_eval_count", 0) for r in raw),
                "maximum_prompt_tokens": max(
                    (r.get("prompt_eval_count", 0) for r in raw), default=0
                ),
            }
        )
    decomposition = paired_decomposition(rows, labels)
    snapshot = {
        "prefix_bytes": len(prefix),
        "prefix_sha256": hashlib.sha256(prefix).hexdigest(),
        "unfinished_tail_bytes": tail_bytes,
    }
    if not (run / "results.jsonl").read_bytes().startswith(prefix):
        raise ValueError("Captured raw prefix changed during its independent audit")
    data = {
        "kind": "independent_case_allocation_judgment_integrity",
        "complete": complete,
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "planned_conditions": 990,
        "observed_conditions": len(rows),
        "planned_patients": 33,
        "actual_provider_responses": len(nonces),
        "failures_by_contract": dict(failures),
        "all_failed_calls_excluded_from_normal_abstentions": True,
        "patient_facts_identical_across_arms": True,
        "fixed_system_prompt": True,
        "no_model_visible_scoring_metadata": True,
        "pilot_responses_imported": 0,
        "pilot_actual_attempts_separate_from_full": len(pilot_rows),
        "pilot_attempt_seconds_separate_from_full": sum(r["seconds"] for r in pilot_rows),
        "total_actual_attempts_including_pilot": len(rows) + len(pilot_rows),
        "repeated_calls_are_independent_patients": False,
        "clinical_explanation_support_audited": False,
        "clinical_review": "pending",
        "production_change": False,
        "prepared_identity": manifest["identity"],
        "run_identity": plan["identity"],
        "preparation_artifacts": prep_pins,
        "pilot_artifacts": pilot_pins,
        "completed_run_artifacts": run_pins,
        "completed_summary_sha256": checked_summary,
        "snapshot": snapshot,
        "auditor_sha256": file_hash(__file__),
        "interpretation": "Engineering protocol and artifact integrity, not clinical accuracy or an independent clinician assessment.",
    }
    if check_only:
        return data
    output.mkdir(parents=True)
    for filename, value in (
        ("checks.json", data),
        ("independent_metrics.json", metrics),
        ("patient_aggregates.json", patient_aggregates),
        ("costs.json", cost_rows),
        ("paired_decomposition.json", decomposition),
    ):
        write_json(output / filename, value)
    write_json(output / "manifest.json", {**data, "identity": digest(data)})
    (output / "auditor_source.py").write_bytes(Path(__file__).read_bytes())
    write_json(
        output / "artifacts.json", {p.name: file_hash(p) for p in output.iterdir() if p.is_file()}
    )
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/experiments/case_allocation_full_integrity_v1")
    )
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument(
        "--check-only", action="store_true", help="Read and validate without writing any files"
    )
    args = parser.parse_args()
    result = audit(
        Path.cwd(), args.output, allow_partial=args.allow_partial, check_only=args.check_only
    )
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "complete",
                    "planned_conditions",
                    "observed_conditions",
                    "actual_provider_responses",
                    "failures_by_contract",
                )
            },
            indent=2,
        )
    )
