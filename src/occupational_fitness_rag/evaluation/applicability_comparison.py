"""Compare outcome-first and applicability-first proposals on immutable retrieval inputs.

This development experiment never writes a production case or changes a rule result.
"""

import argparse
import csv
import json
import os
from collections import Counter, defaultdict
from copy import deepcopy
from html import escape
from itertools import product
from pathlib import Path
from time import perf_counter
from typing import get_args

import yaml

from occupational_fitness_rag.evaluation import passage_comparison as previous
from occupational_fitness_rag.evaluation import passage_judgment
from occupational_fitness_rag.evaluation.judgment_comparison import local_post
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json

PROTOCOLS = {"passage_selection", "applicability_first"}
PHASES = {
    "known_error_development_set",
    "locked_engineering_replay",
    "source_literal_fact_sensitivity",
}
UPSTREAM_IDENTITY_FIELDS = (
    "config",
    "config_sha256",
    "sources_sha256",
    "historical_fingerprints",
    "environment",
    "patient_inputs_sha256",
    "corpus_sha256",
    "planned_keys",
)
PAYLOAD_FIELDS = {
    "licence_context",
    "modules",
    "nurse_note",
    "verified_patient_facts",
    "guideline_evidence",
}


def validate_config(config):
    compatible = {**config, "protocols": ["passage_selection"]}
    previous.validate_config(compatible)
    if config.get("phase", "known_error_development_set") not in PHASES:
        raise ValueError("Unknown experiment phase")
    if config.get("judgment_guidance", "baseline") not in {"baseline", "source_bound_v1"}:
        raise ValueError("Unknown experimental judgment guidance")
    if config.get("aggregation_ledger_mode", "full_values") not in {
        "full_values",
        "field_references",
    }:
        raise ValueError("Unknown aggregation ledger materialization mode")
    if not isinstance(config["protocols"], list) or (
        not config["protocols"]
        or len(set(config["protocols"])) != len(config["protocols"])
        or not set(config["protocols"]) <= PROTOCOLS
    ):
        raise ValueError("Unknown or duplicate applicability protocol")
    if not set(config["evidence_policies"]) <= {"module_query", "reference_evidence"}:
        raise ValueError("Only frozen module-query and reference controls are permitted")
    for field in ["expected_retrieval_identity", "expected_corpus_sha256"]:
        if not isinstance(config.get(field), str) or not config[field]:
            raise ValueError("Explicit upstream retrieval and corpus pins are required")


def load_retrieval(config):
    """Verify historical self-identities without requiring historical code to be current."""
    from occupational_fitness_rag.evaluation.applicability_judgment import validate_patient_payload

    root = Path(config["retrieval_dir"]).resolve()
    names = [
        "manifest.json",
        "retrieval_freeze.json",
        "source_snapshot.json",
        "frozen_inputs.json",
        "corpus.json",
        "retrieval.json",
        "payloads.json",
        "embeddings.json",
    ]
    raw = {name: (root / name).read_bytes() for name in names}
    saved = {name: json.loads(value) for name, value in raw.items()}
    manifest, freeze = saved["manifest.json"], saved["retrieval_freeze.json"]
    identity_data = {field: manifest[field] for field in UPSTREAM_IDENTITY_FIELDS}
    if (
        digest(identity_data) != manifest["identity"]
        or manifest["identity"] != config["expected_retrieval_identity"]
        or freeze["identity"] != manifest["identity"]
        or digest(saved["source_snapshot.json"]) != manifest["sources_sha256"]
        or digest(saved["frozen_inputs.json"]) != manifest["patient_inputs_sha256"]
    ):
        raise ValueError("Frozen retrieval manifest or source identity is invalid")
    artifact_names = {"retrieval.json", "payloads.json", "embeddings.json"}
    if set(freeze["artifacts"]) != artifact_names or any(
        sha256_bytes(raw[name]) != freeze["artifacts"][name] for name in artifact_names
    ):
        raise ValueError("Frozen retrieval artifact hash changed")
    corpus = saved["corpus.json"]
    if (
        corpus["corpus_sha256"] != config["expected_corpus_sha256"]
        or corpus["corpus_sha256"] != manifest["corpus_sha256"]
        or digest({key: value for key, value in corpus.items() if key != "corpus_sha256"})
        != corpus["corpus_sha256"]
    ):
        raise ValueError("Frozen reviewed corpus fingerprint differs")
    units = {unit["source_id"]: unit for unit in corpus["units"]}
    if len(units) != len(corpus["units"]) or any(
        unit.get("licence_context") not in {"commercial", "shared"} for unit in units.values()
    ):
        raise ValueError("Invalid or inapplicable reviewed corpus unit")
    for field in [
        "endpoint",
        "models",
        "expected_model_digests",
        "expected_runtime_version",
        "embedding_model",
        "embedding_model_digest",
        "embedding_dimensions",
        "context_length",
        "output_tokens",
        "prompt_max_bytes",
        "request_max_bytes",
        "evidence_max_bytes",
        "top_k",
        "sensitivity_k",
        "max_validation_repairs",
    ]:
        if config[field] != manifest["config"][field]:
            raise ValueError(
                "Contemporary comparison differs from frozen budget or model: " + field
            )
    selected, labels = {}, {}
    for case_id in config["case_ids"]:
        original = saved["frozen_inputs.json"][case_id]
        labels[case_id] = original["reference_outcome"]
        selected[case_id] = {}
        for policy in config["evidence_policies"]:
            item = deepcopy(saved["payloads.json"][case_id][policy])
            if item["status"] == "completed":
                payload = item["payload"]
                validate_patient_payload(payload)
                if (
                    set(payload) != PAYLOAD_FIELDS
                    or digest(payload) != item["input_sha256"]
                    or previous.patient_identity(payload)
                    != previous.patient_identity(original["payload"])
                    or len(payload["guideline_evidence"]) > config["top_k"]
                    or len(previous.json_bytes(payload)) > config["prompt_max_bytes"]
                    or len(previous.json_bytes(payload["guideline_evidence"]))
                    > config["evidence_max_bytes"]
                ):
                    raise ValueError("Frozen patient or evidence payload differs")
                seen = set()
                for source in payload["guideline_evidence"]:
                    unit = units.get(source["source_id"])
                    if (
                        unit is None
                        or source["source_id"] in seen
                        or any(
                            source[field] != unit[unit_field]
                            for field, unit_field in [
                                ("source_text", "evidence_text"),
                                ("module", "module"),
                                ("pdf_page", "pdf_page"),
                                ("section", "section"),
                                ("printed_page", "printed_page"),
                            ]
                        )
                    ):
                        raise ValueError("Payload source does not match its complete original unit")
                    seen.add(source["source_id"])
                passage_judgment.passage_catalogue(payload)
            selected[case_id][policy] = item
    return {
        "manifest": manifest,
        "payloads": selected,
        "labels": labels,
        "corpus": corpus,
        "fingerprints": {name: sha256_bytes(value) for name, value in raw.items()},
        "upstream_snapshot": saved,
    }


def run_stage(config, body, parse, materialize, post=local_post):
    """One stage, at most one structural repair; no repair of semantic findings."""
    started = perf_counter()
    result = {"status": "failed", "attempts": []}
    for index in range(config["max_validation_repairs"] + 1):
        attempt_started = perf_counter()
        record = {
            "number": index + 1,
            "request": deepcopy(body),
            "request_sha256": digest(body),
            "request_bytes": len(previous.json_bytes(body)),
            "status": "failed",
            "provider_called": False,
        }
        phase, raw = "request", None
        try:
            if record["request_bytes"] > config["request_max_bytes"]:
                raise ValueError("Complete serialized request exceeds the frozen byte limit")
            record["provider_called"] = True
            raw = post(config["endpoint"], "/api/chat", body, timeout=config["timeout_seconds"])
            record["raw_response"] = raw
            phase = "provider_response"
            if (
                not isinstance(raw, dict)
                or not isinstance(raw.get("message"), dict)
                or not isinstance(raw["message"].get("content"), str)
            ):
                raise ValueError("Malformed local model response envelope")
            record["token_counts"] = {
                key: raw.get(key)
                for key in ["prompt_eval_count", "eval_count", "prompt_eval_cached_count"]
            }
            record["context_truncation_status"] = (
                "Token counts alone do not prove the absence of silent truncation"
            )
            if raw.get("done") is False or raw.get("done_reason") == "length":
                raise ValueError("Incomplete model output; no repair for truncation")
            count = raw.get("prompt_eval_count")
            if count is not None and count + config["output_tokens"] >= config["context_length"]:
                raise ValueError("Measured prompt tokens leave insufficient context reserve")
            phase = "structural_validation"
            proposal = parse(raw)
            phase = "provenance"
            derived = materialize(proposal)
            record.update(status="completed", answer=proposal.model_dump(mode="json"), **derived)
            result.update(status="completed", answer=record["answer"], proposal=proposal, **derived)
            result.pop("error", None)
        except Exception as exc:
            record.update(error=f"{type(exc).__name__}: {exc}", failure_stage=phase)
            result["error"] = record["error"]
        record["seconds"] = perf_counter() - attempt_started
        result["attempts"].append(record)
        if record["status"] == "completed":
            break
        if (
            raw is None
            or phase != "structural_validation"
            or index == config["max_validation_repairs"]
        ):
            break
        body = deepcopy(body)
        body["messages"].extend(
            [
                {"role": "assistant", "content": raw["message"]["content"]},
                {
                    "role": "user",
                    "content": (
                        "The output failed structural validation: "
                        + record["error"]
                        + ". Correct only the output contract using the SAME supplied facts and original "
                        "passages. Do not invent facts, quotations or identifiers. This validator provides "
                        "no correct fitness outcome. Semantic consistency flags are not repair instructions."
                    ),
                },
            ]
        )
    result["seconds"] = perf_counter() - started
    return result


def run_applicability(config, model, payload, post=local_post, api=None):
    if api is None:
        from occupational_fitness_rag.evaluation import applicability_judgment as api
    started = perf_counter()
    result = {
        "status": "failed",
        "stages": {},
        "attempts": [],
        "input_snapshot": deepcopy(payload),
        "support_review": "pending_independent_review",
        "first_pass_status": "failed",
        "recovered_after_validation_failure": False,
        "model_attempts": 0,
        "model_calls": 0,
    }
    if len(previous.json_bytes(payload)) > config["prompt_max_bytes"]:
        return {**result, "error": "Payload exceeds frozen byte limit", "seconds": 0.0}
    try:
        review = run_stage(
            config,
            api.build_applicability_request(config, model, payload),
            lambda raw: api.parse_applicability_response(raw, payload),
            lambda value: {
                "criterion_locations": api.review_locations(value, payload),
                "ledger_consistency_flags": api.ledger_consistency_flags(value),
            },
            post,
        )
        proposal = review.pop("proposal", None)
        result["stages"]["applicability"] = review
        if review["status"] != "completed":
            raise ValueError("Applicability stage failed: " + review["error"])
        aggregation = run_stage(
            config,
            api.build_aggregation_request(config, model, payload, proposal),
            lambda raw: (
                api.parse_aggregation_response(raw, payload, proposal, config=config)
                if config.get("judgment_guidance", "baseline") != "baseline"
                else api.parse_aggregation_response(raw, payload, proposal)
            ),
            lambda value: {
                "criterion_locations": passage_judgment.criterion_locations(value, payload),
                "output_consistency_flags": passage_judgment.output_consistency_flags(
                    value, payload
                ),
            },
            post,
        )
        aggregation.pop("proposal", None)
        result["stages"]["aggregation"] = aggregation
        result["attempts"] = aggregation["attempts"]
        if aggregation["status"] != "completed":
            raise ValueError("Aggregation stage failed: " + aggregation["error"])
        for field in ["answer", "criterion_locations", "output_consistency_flags"]:
            result[field] = aggregation[field]
        result["status"] = "completed"
        if all(stage["attempts"][0]["status"] == "completed" for stage in [review, aggregation]):
            result["first_pass_status"] = "completed"
            result["first_pass_answer"] = aggregation["attempts"][0]["answer"]
        result["recovered_after_validation_failure"] = any(
            len(stage["attempts"]) > 1 for stage in [review, aggregation]
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    result["model_attempts"] = sum(len(stage["attempts"]) for stage in result["stages"].values())
    result["model_calls"] = sum(
        attempt["provider_called"]
        for stage in result["stages"].values()
        for attempt in stage["attempts"]
    )
    result["seconds"] = perf_counter() - started
    return result


def normalize_baseline(result, posted_requests=None):
    result = deepcopy(result)
    result["first_pass_status"] = "failed"
    if result["attempts"] and result["attempts"][0]["status"] == "completed":
        result["first_pass_status"] = "completed"
        result["first_pass_answer"] = result["attempts"][0]["answer"]
    result["model_attempts"] = len(result["attempts"])
    posted = Counter(posted_requests or [])
    for attempt in result["attempts"]:
        request_hash = attempt["request_sha256"]
        attempt["provider_called"] = posted[request_hash] > 0
        if attempt["provider_called"]:
            posted[request_hash] -= 1
    result["model_calls"] = sum(attempt["provider_called"] for attempt in result["attempts"])
    result["stages"] = {
        "outcome_first": {
            key: value
            for key, value in result.items()
            if key in {"status", "attempts", "answer", "error", "seconds"}
        }
    }
    return result


def run_baseline(config, model, payload, post):
    calls = []

    def counted_post(endpoint, route, body, timeout):
        calls.append(digest(body))
        return post(endpoint, route, body, timeout=timeout)

    return normalize_baseline(
        previous.run_condition(config, model, payload, "passage_selection", counted_post), calls
    )


def cost_totals(rows):
    """All stages and failed/repaired calls count; unknown token counts remain unknown."""
    attempts = [
        attempt
        for row in rows
        for stage in row.get("stages", {}).values()
        for attempt in stage["attempts"]
    ]
    calls = [attempt for attempt in attempts if attempt.get("provider_called")]
    result = {"request_attempts": len(attempts), "model_calls": len(calls)}
    for token in ["prompt_eval_count", "eval_count", "prompt_eval_cached_count"]:
        observed = [a.get("token_counts", {}).get(token) for a in calls]
        valid = [value for value in observed if type(value) is int and value >= 0]
        result[token + "_known_sum"] = sum(valid)
        result[token + "_unknown_calls"] = len(calls) - len(valid)
    result["seconds"] = sum(row["seconds"] for row in rows)
    return result


def classification_metrics(rows, answer_field, status_field):
    """Five fixed outcome classes, with failed calls retained as missed reference labels."""
    labels = list(get_args(passage_judgment.OUTCOMES))
    confusion = {
        truth: {prediction: 0 for prediction in [*labels, "RUN_FAILURE"]} for truth in labels
    }
    for row in rows:
        prediction = (
            row[answer_field]["assessment_outcome"]
            if row[status_field] == "completed"
            else "RUN_FAILURE"
        )
        confusion[row["reference_outcome"]][prediction] += 1
    per_class = {}
    for label in labels:
        true_positive = confusion[label][label]
        false_negative = sum(confusion[label].values()) - true_positive
        false_positive = sum(confusion[truth][label] for truth in labels if truth != label)
        denominator = 2 * true_positive + false_negative + false_positive
        per_class[label] = {
            "reference_count": sum(confusion[label].values()),
            "f1": 2 * true_positive / denominator if denominator else 0.0,
        }
    return {
        "macro_f1_five_outcomes": sum(item["f1"] for item in per_class.values()) / len(labels),
        "class_definition": "Five fixed outcomes; zero-division F1 is zero; failures count as false negatives",
        "confusion_matrix": confusion,
        "per_class": per_class,
    }


def paired_transitions(rows):
    groups = defaultdict(dict)
    for row in rows:
        key = (row["model"], row["case_id"], row["evidence_policy"], row["repeat"])
        if row["protocol"] in groups[key]:
            raise ValueError("Duplicate paired protocol condition")
        groups[key][row["protocol"]] = row
    pairs = []
    for key, arms in groups.items():
        if set(arms) != PROTOCOLS:
            continue
        before, after = arms["passage_selection"], arms["applicability_first"]
        if (
            before["input_sha256"] != after["input_sha256"]
            or before["model_digest"] != after["model_digest"]
            or before["reference_outcome"] != after["reference_outcome"]
        ):
            raise ValueError("Paired protocols differ in patient, evidence, model or reference")
        before_valid, after_valid = before["status"] == "completed", after["status"] == "completed"
        if before_valid and after_valid:
            correctness = (before["reference_agreement"], after["reference_agreement"])
            transition = {
                (False, True): "accepted_wrong_to_correct",
                (True, False): "accepted_correct_to_wrong",
                (True, True): "accepted_both_correct",
                (False, False): "accepted_both_wrong",
            }[correctness]
        else:
            transition = {
                (False, True): "failed_to_valid",
                (True, False): "valid_to_failed",
                (False, False): "both_failed",
            }[before_valid, after_valid]
        pairs.append(
            {
                "model": key[0],
                "case_id": key[1],
                "evidence_policy": key[2],
                "repeat": key[3],
                "input_sha256": before["input_sha256"],
                "transition": transition,
                "baseline_outcome": before.get("answer", {}).get("assessment_outcome"),
                "applicability_outcome": after.get("answer", {}).get("assessment_outcome"),
                "engineering_reference": before["reference_outcome"],
            }
        )
    return {"pairs": pairs, "counts": dict(Counter(row["transition"] for row in pairs))}


def write_review(output, rows):
    """Keep human annotations while extending the immutable attempt-level worksheet."""
    path = output / "review.csv"
    existing = {}
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as stream:
            old = list(csv.DictReader(stream))
        existing = {row["item_id"]: row for row in old}
        if len(existing) != len(old):
            raise ValueError("Duplicate manual-review item")
    items = []
    for row in rows:
        for stage_name, stage in row.get("stages", {}).items():
            for attempt in stage["attempts"]:
                for index, location in enumerate(attempt.get("criterion_locations", [])):
                    immutable = {
                        "condition": list(previous.condition_key(row)),
                        "stage": stage_name,
                        "attempt": attempt["number"],
                        "check_index": index,
                        "location": location,
                    }
                    item = {
                        "item_id": digest({k: v for k, v in immutable.items() if k != "location"}),
                        "immutable_sha256": digest(immutable),
                        "case_id": row["case_id"],
                        "model": row["model"],
                        "policy": row["evidence_policy"],
                        "protocol": row["protocol"],
                        "repeat": row["repeat"],
                        "stage": stage_name,
                        "attempt": attempt["number"],
                        "attempt_status": attempt["status"],
                        "original_location_json": json.dumps(location, ensure_ascii=False),
                        "support_review": "pending",
                        "applicability_review": "pending",
                        "reviewer": "",
                        "notes": "",
                    }
                    if item["item_id"] in existing:
                        old = existing[item["item_id"]]
                        if old["immutable_sha256"] != item["immutable_sha256"]:
                            raise ValueError("Annotated criterion source changed")
                        for field in [
                            "support_review",
                            "applicability_review",
                            "reviewer",
                            "notes",
                        ]:
                            item[field] = old[field]
                    items.append(item)
    if not set(existing) <= {item["item_id"] for item in items}:
        raise ValueError("Manual-review items disappeared")
    if items:
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(items[0]))
            writer.writeheader()
            writer.writerows(items)
    return len(items)


def write_report(output, rows, planned_keys):
    manifest_path = output / "manifest.json"
    phase = (
        json.loads(manifest_path.read_text(encoding="utf-8")).get(
            "phase", "known_error_development_set"
        )
        if manifest_path.exists()
        else "known_error_development_set"
    )
    keys = {previous.condition_key(row) for row in rows}
    if len(keys) != len(rows) or not keys <= planned_keys:
        raise ValueError("Duplicate or unexpected experiment condition")
    metrics = []
    groups = defaultdict(list)
    for row in rows:
        groups[row["model"], row["evidence_policy"], row["protocol"]].append(row)
    for (model, policy, protocol), group in sorted(groups.items()):
        for stage in ["first_pass_without_repairs", "final_with_structural_repairs"]:
            valid = [
                row
                for row in group
                if row["first_pass_status" if stage == "first_pass_without_repairs" else "status"]
                == "completed"
            ]
            answer_field = (
                "first_pass_answer" if stage == "first_pass_without_repairs" else "answer"
            )
            correct = sum(
                row[answer_field]["assessment_outcome"] == row["reference_outcome"] for row in valid
            )
            metrics.append(
                {
                    "model": model,
                    "evidence_policy": policy,
                    "protocol": protocol,
                    "stage": stage,
                    "conditions": len(group),
                    "valid": len(valid),
                    "failures": len(group) - len(valid),
                    "correct": correct,
                    "engineering_reference_agreement": correct / len(group),
                    "model_attempts": sum(row["model_attempts"] for row in group),
                    "model_calls": sum(row["model_calls"] for row in group),
                    "seconds": sum(row["seconds"] for row in group),
                    "flagged_conditions": sum(
                        bool(row.get("output_consistency_flags")) for row in valid
                    ),
                    "ledger_flagged_conditions": sum(
                        bool(
                            row.get("stages", {})
                            .get("applicability", {})
                            .get("ledger_consistency_flags")
                        )
                        for row in group
                    ),
                    "macro_f1_five_outcomes": classification_metrics(
                        group,
                        answer_field,
                        "first_pass_status" if stage == "first_pass_without_repairs" else "status",
                    )["macro_f1_five_outcomes"],
                }
            )
    classifications = [
        {
            "model": model,
            "evidence_policy": policy,
            "protocol": protocol,
            **classification_metrics(group, "answer", "status"),
        }
        for (model, policy, protocol), group in sorted(groups.items())
    ]
    write_json(output / "classification.json", classifications)
    paired = paired_transitions(rows)
    write_json(output / "paired_analysis.json", paired)
    review_items = write_review(output, rows)
    summary = {
        "phase": phase,
        "recorded_conditions": len(rows),
        "planned_conditions": len(planned_keys),
        "execution_status": "completed" if keys == planned_keys else "partial",
        "metrics": metrics,
        "model_attempts": sum(row["model_attempts"] for row in rows),
        "review_items": review_items,
        "cost": cost_totals(rows),
        "paired_transition_counts": paired["counts"],
        "clinical_accuracy": None,
        "failures": dict(
            Counter(
                row.get("error", "Unspecified failure")
                for row in rows
                if row["status"] != "completed"
            )
        ),
        "production_change": False,
        "warning": (
            "Existing engineering cases; not independent clinical validation. Engineering reference "
            "agreement is not clinical accuracy. Original-source resolution does not establish semantic "
            "support. The applicability ledger is a fallible model proposal. Stage costs include both "
            "calls and all bounded structural repairs. No outcome is automatically corrected."
        ),
    }
    write_json(output / "summary.json", summary)
    if metrics:
        with (output / "summary.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(metrics[0]))
            writer.writeheader()
            writer.writerows(metrics)
    table = "".join(
        "<tr>"
        + "".join(
            f"<td>{escape(str(metric[field]))}</td>"
            for field in [
                "model",
                "evidence_policy",
                "protocol",
                "stage",
                "valid",
                "conditions",
                "correct",
                "model_calls",
                "flagged_conditions",
            ]
        )
        + "</tr>"
        for metric in metrics
    )
    selectors = "".join(
        f'<label>{label}<select data-field="{field}">'
        + "".join(f"<option>{escape(value)}</option>" for value in sorted({r[field] for r in rows}))
        + "</select></label>"
        for field, label in [("case_id", "Case"), ("model", "Model")]
    )
    cards = []
    for row in rows:
        answer = row.get("answer", {})
        sources = "".join(
            f"<details><summary>{escape(source['source_id'])} · {escape(source['module'])} · "
            f"Section {escape(source['section'])} · PDF {source['pdf_page']} · "
            f"Printed {source['printed_page']}</summary><blockquote>{escape(source['source_text'])}"
            "</blockquote></details>"
            for source in row.get("input_snapshot", {}).get("guideline_evidence", [])
        )
        cards.append(
            f'<article data-case_id="{escape(row["case_id"])}" data-model="{escape(row["model"])}">'
            f"<h2>{escape(row['evidence_policy'])} / {escape(row['protocol'])} · Repeat {row['repeat'] + 1}</h2>"
            f"<p>{escape(row['case_id'])} · {escape(row['model'])} · {row['status']}</p>"
            f"<p>Proposal: <strong>{escape(answer.get('assessment_outcome', 'Unavailable'))}</strong>"
            f"<br>Engineering reference: {escape(row['reference_outcome'])}</p>"
            f"<p>{escape(answer.get('explanation', row.get('error', '')))}</p>"
            f"<p>Model calls: {row['model_calls']} · Request attempts: {row['model_attempts']} · First pass: {row['first_pass_status']}</p>"
            f"<details><summary>Criterion checks and original locations</summary><pre>{escape(json.dumps(row.get('criterion_locations', []), indent=2))}</pre></details>"
            f"<details><summary>Applicability ledger and all stage attempts</summary><pre>{escape(json.dumps(row.get('stages', {}), indent=2))}</pre></details>"
            f"<details><summary>Frozen patient inputs</summary><pre>{escape(json.dumps({k: v for k, v in row.get('input_snapshot', {}).items() if k != 'guideline_evidence'}, indent=2))}</pre></details>"
            + sources
            + "</article>"
        )
    html = (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Applicability comparison | Occupational Fitness Platform</title><style>"
        "body{font:14px/1.6 system-ui;background:#f4f6f8;color:#233647;margin:0}header{background:#233647;color:white;padding:28px 4vw}"
        "main{max-width:1500px;margin:auto;padding:24px}.notice{background:#fff4df;padding:18px}.scroll{overflow:auto}"
        "table{width:100%;border-collapse:collapse;background:white}td,th{padding:10px;border-bottom:1px solid #dce3e9;text-align:left}"
        ".cards{display:grid;grid-template-columns:1fr 1fr;gap:18px}article{background:white;padding:22px;border:1px solid #dce3e9;border-radius:8px}"
        "article[hidden]{display:none}h2{font-size:17px}pre,blockquote{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f7fa;padding:12px}"
        "summary{cursor:pointer;padding:8px 0}select{display:block;padding:8px}label{display:inline-block;margin:18px}@media(max-width:850px){.cards{grid-template-columns:1fr}}</style>"
        "<header>OCCUPATIONAL FITNESS PLATFORM<h1>Applicability and judgment comparison</h1></header><main>"
        f'<p>{len(rows)}/{len(planned_keys)} conditions · {summary["execution_status"]}</p><p class="notice">{escape(summary["warning"])}</p>'
        "<p>Identical frozen patient facts, complete original passages, judge revisions, temperature and seed. Reference evidence is a separate diagnostic control.</p>"
        '<div class="scroll"><table><thead><tr><th>Model</th><th>Evidence policy</th><th>Protocol</th><th>Stage</th><th>Valid</th><th>Total</th><th>Agree</th><th>Calls (all stages)</th><th>Flagged</th></tr></thead><tbody>'
        + table
        + "</tbody></table></div><h2>Paired transitions</h2><pre>"
        + escape(json.dumps(paired["counts"], indent=2))
        + "</pre>"
        + selectors
        + '<div class="cards">'
        + "".join(cards)
        + '</div><p><a href="results.jsonl">Raw results</a> · '
        '<a href="summary.json">Metrics</a> · <a href="paired_analysis.json">Paired cases</a> · <a href="review.csv">Review worksheet</a> · '
        '<a href="manifest.json">Manifest</a> · <a href="source_snapshot.json">Code snapshot</a> · <a href="retrieval_inputs.json">Frozen retrieval inputs</a></p>'
        '<script>function f(){const s=[...document.querySelectorAll("select")];document.querySelectorAll("article").forEach(a=>a.hidden=s.some(x=>a.dataset[x.dataset.field]!==x.value))}document.querySelectorAll("select").forEach(s=>s.addEventListener("change",f));f();</script></main></html>'
    )
    (output / "index.html").write_text(html, encoding="utf-8")
    return summary


def validate_saved_rows(rows, manifest, frozen):
    """Do not resume from edited condition identities, labels or accepted stage records."""
    planned = {tuple(key) for key in manifest["planned_keys"]}
    keys = [previous.condition_key(row) for row in rows]
    if len(keys) != len(set(keys)) or not set(keys) <= planned:
        raise ValueError("Duplicate or unexpected saved condition")
    for row in rows:
        selected = frozen["payloads"][row["case_id"]][row["evidence_policy"]]
        if (
            row["experiment_identity"] != manifest["identity"]
            or row["model_digest"] != manifest["environment"]["model_digests"][row["model"]]
            or row["reference_outcome"] != frozen["labels"][row["case_id"]]
            or row["input_sha256"] != selected.get("input_sha256", digest(selected))
            or row["status"] not in {"completed", "failed"}
        ):
            raise ValueError("Saved condition identity, input or reference changed")
        if selected["status"] == "completed" and row.get("input_snapshot") != selected["payload"]:
            raise ValueError("Saved patient input snapshot changed")
        stages = row.get("stages", {})
        for stage in stages.values():
            for attempt in stage["attempts"]:
                if attempt["request_sha256"] != digest(attempt["request"]) or attempt[
                    "request_bytes"
                ] != len(previous.json_bytes(attempt["request"])):
                    raise ValueError("Saved stage request fingerprint changed")
                if attempt["status"] == "completed" and "error" in attempt:
                    raise ValueError("Accepted stage attempt carries a failure")
        if row["model_attempts"] != sum(len(stage["attempts"]) for stage in stages.values()):
            raise ValueError("Saved stage cost differs from its attempts")
        if row["model_calls"] != sum(
            bool(attempt.get("provider_called"))
            for stage in stages.values()
            for attempt in stage["attempts"]
        ):
            raise ValueError("Saved provider-call cost differs from its stage records")
        if row["status"] == "completed":
            final = stages[
                "outcome_first" if row["protocol"] == "passage_selection" else "aggregation"
            ]
            if (
                final["status"] != "completed"
                or row["answer"] != final["answer"]
                or row["attempts"] != final["attempts"]
                or "error" in row
                or not row["reference_agreement"]
                == (row["answer"]["assessment_outcome"] == row["reference_outcome"])
            ):
                raise ValueError("Saved accepted proposal differs from its final stage")
        elif row["reference_agreement"]:
            raise ValueError("A failed condition cannot agree with a reference")


def run_comparison(
    config_path,
    resume=False,
    max_conditions=None,
    post=local_post,
    get=previous.local_get,
    api=None,
):
    if max_conditions is not None and (type(max_conditions) is not int or max_conditions < 0):
        raise ValueError("max_conditions must be a non-negative integer")
    config_path = Path(config_path)
    config_text = config_path.read_text(encoding="utf-8")
    config = yaml.safe_load(config_text)
    validate_config(config)
    output, upstream = Path(config["output"]).resolve(), Path(config["retrieval_dir"]).resolve()
    if output == upstream or output.is_relative_to(upstream) or upstream.is_relative_to(output):
        raise ValueError("New experiment output must be isolated from frozen retrieval")
    previous.read_records(output / "results.jsonl")
    frozen = load_retrieval(config)
    environment = previous.pinned_environment(config, get)
    sources = previous.source_snapshot(config_text)
    planned = list(
        product(
            config["models"],
            config["case_ids"],
            config["evidence_policies"],
            config["protocols"],
            range(config["repeats"]),
        )
    )
    identity_data = {
        "config": config,
        "config_sha256": sha256_bytes(config_text.encode("utf-8")),
        "sources_sha256": digest(sources),
        "upstream_fingerprints": frozen["fingerprints"],
        "environment": environment,
        "planned_keys": planned,
    }
    manifest = {
        **identity_data,
        "identity": digest(identity_data),
        "planned_conditions": len(planned),
        "corpus_sha256": config["expected_corpus_sha256"],
        "phase": config.get("phase", "known_error_development_set"),
        "clinical_review": "pending",
        "production_change": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    lock = output / ".run.lock"
    try:
        with lock.open("x", encoding="ascii") as stream:
            stream.write(str(os.getpid()))
    except FileExistsError as exc:
        raise ValueError("Another run or an unreviewed stale run lock exists") from exc
    try:
        path = output / "manifest.json"
        artifacts = {
            "source_snapshot.json": sources,
            "retrieval_inputs.json": frozen["payloads"],
            "corpus.json": frozen["corpus"],
            "reference_labels.json": frozen["labels"],
            "upstream_manifest.json": frozen["manifest"],
        }
        if path.exists():
            if not resume:
                raise ValueError("Existing experiment requires --resume or a new output")
            if json.loads(path.read_text(encoding="utf-8")) != json.loads(json.dumps(manifest)):
                raise ValueError(
                    "Experiment identity changed; preserve output and use a new directory"
                )
            for name, value in artifacts.items():
                if json.loads((output / name).read_text(encoding="utf-8")) != json.loads(
                    json.dumps(value)
                ):
                    raise ValueError("Saved experiment artifact changed: " + name)
        else:
            if any(item.name != ".run.lock" for item in output.iterdir()):
                raise ValueError("Non-empty output lacks a manifest")
            write_json(path, manifest)
            for name, value in artifacts.items():
                write_json(output / name, value)
        rows = previous.read_records(output / "results.jsonl")
        validate_saved_rows(rows, manifest, frozen)
        planned_keys = set(planned)
        write_report(output, rows, planned_keys)
        done = {previous.condition_key(row) for row in rows}
        added = 0
        for model, case_id, policy, protocol, repeat in planned:
            key = (model, case_id, policy, protocol, repeat)
            if key in done:
                continue
            if max_conditions is not None and added >= max_conditions:
                break
            previous.pinned_environment(config, get)
            selected = frozen["payloads"][case_id][policy]
            row = {
                "model": model,
                "model_digest": environment["model_digests"][model],
                "case_id": case_id,
                "evidence_policy": policy,
                "protocol": protocol,
                "repeat": repeat,
                "experiment_identity": manifest["identity"],
                "input_sha256": selected.get("input_sha256", digest(selected)),
            }
            if selected["status"] != "completed":
                row.update(
                    status="failed",
                    error="Frozen retrieval failed: " + selected["error"],
                    attempts=[],
                    stages={},
                    model_attempts=0,
                    model_calls=0,
                    seconds=0.0,
                    first_pass_status="failed",
                )
            else:
                row["selection"] = deepcopy(selected["selection"])
                if protocol == "passage_selection":
                    row.update(run_baseline(config, model, selected["payload"], post))
                else:
                    row.update(run_applicability(config, model, selected["payload"], post, api))
            # Labels are attached only after all model stages finish.
            row["reference_outcome"] = frozen["labels"][case_id]
            row["reference_agreement"] = row["status"] == "completed" and (
                row["answer"]["assessment_outcome"] == row["reference_outcome"]
            )
            if previous.read_records(output / "results.jsonl") != rows:
                raise ValueError("Records changed during the exclusive experiment")
            with (output / "results.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
            rows.append(row)
            done.add(key)
            added += 1
            write_report(output, rows, planned_keys)
            print(
                f"Recorded {len(rows)}/{len(planned)}: {case_id} {model} {policy} {protocol} {row['status']}",
                flush=True,
            )
        return write_report(output, rows, planned_keys)
    finally:
        lock.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", default="configs/experiments/applicability_comparison_bound.yaml"
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-conditions", type=int)
    args = parser.parse_args()
    print(json.dumps(run_comparison(args.config, args.resume, args.max_conditions), indent=2))
