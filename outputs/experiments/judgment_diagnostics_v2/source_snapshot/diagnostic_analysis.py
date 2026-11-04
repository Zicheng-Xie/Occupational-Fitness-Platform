"""Post-hoc paired analysis and human review export for diagnostic development pilots."""

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from occupational_fitness_rag.evaluation.evidence_judgment import quote_locations
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json

STAGES = ("first_attempt", "final_with_repair")
CONDITION_FIELDS = ("case_id", "model", "evidence_policy", "protocol", "repeat")
OUTCOMES = {
    "meets_unconditional_standard",
    "may_meet_conditional_standard",
    "temporarily_unfit",
    "does_not_meet_standard",
    "insufficient_information",
}
MANUAL_DEFAULTS = {
    "support_status": "pending",
    "applicability_status": "pending",
    "patient_fact_interpretation_status": "pending",
    "clinical_review_status": "pending",
    "review_status": "pending",
    "reviewer": "",
    "reviewed_at": "",
    "comments": "",
}


def condition_key(row):
    return tuple(row[field] for field in CONDITION_FIELDS)


def patient_identity(payload):
    """Retain all payload fields except the evidence being varied."""
    return digest({key: value for key, value in payload.items() if key != "guideline_evidence"})


def answer_at(row, stage):
    if stage not in STAGES:
        raise ValueError("Unknown analysis stage")
    value = (row.get("attempts") or [{}])[0] if stage == "first_attempt" else row
    answer = value.get("answer") or {}
    accepted = value.get("status") == "completed" and answer.get("assessment_outcome") in OUTCOMES
    return {
        "status": "completed" if accepted else "failed",
        "outcome": answer.get("assessment_outcome") if accepted else None,
        "error": value.get("error") if not accepted else None,
    }


def evidence_difference(before, after):
    old = before.get("guideline_evidence", [])
    new = after.get("guideline_evidence", [])
    old_ids = [source["source_id"] for source in old]
    new_ids = [source["source_id"] for source in new]
    old_by_id = {source["source_id"]: source for source in old}
    new_by_id = {source["source_id"]: source for source in new}
    if len(old_by_id) != len(old) or len(new_by_id) != len(new):
        raise ValueError("Duplicate source identifier in a supplied evidence bundle")
    change = (
        "identical_ordered_evidence"
        if old == new
        else "same_passages_different_order"
        if old_by_id == new_by_id
        else "changed_evidence_bundle"
    )
    return {
        "evidence_change": change,
        "baseline_ordered_source_ids": old_ids,
        "intervention_ordered_source_ids": new_ids,
        "added_source_ids": [source for source in new_ids if source not in old_by_id],
        "removed_source_ids": [source for source in old_ids if source not in new_by_id],
        "changed_source_ids": [
            source
            for source in old_ids
            if source in new_by_id and old_by_id[source] != new_by_id[source]
        ],
        "baseline_evidence_sha256": digest(old),
        "intervention_evidence_sha256": digest(new),
    }


def pair_conditions(before, after, axis, stage):
    """Compare accepted predictions only after verifying the controlled inputs."""
    if axis not in {"protocol", "evidence_policy"}:
        raise ValueError("Unknown comparison axis")
    old = before["input_snapshot"]
    new = after["input_snapshot"]
    excluded = []
    if patient_identity(old) != patient_identity(new):
        excluded.append("patient_input_mismatch")
    if axis == "protocol" and digest(old) != digest(new):
        excluded.append("protocol_payload_mismatch")
    if not before.get("model_digest") or before.get("model_digest") != after.get("model_digest"):
        excluded.append("model_digest_missing_or_mismatched")
    if not before.get("reference_outcome") or before.get("reference_outcome") != after.get(
        "reference_outcome"
    ):
        excluded.append("reference_mismatch")
    for label, row in [("baseline", before), ("intervention", after)]:
        if row.get("input_sha256") and row["input_sha256"] != digest(row["input_snapshot"]):
            excluded.append(label + "_input_fingerprint_mismatch")
    first = answer_at(before, stage)
    second = answer_at(after, stage)
    both_valid = first["status"] == second["status"] == "completed"
    reference = after["reference_outcome"]
    transition = "excluded_identity_mismatch" if excluded else "failure_separate"
    if not excluded and both_valid:
        correct_before = first["outcome"] == reference
        correct_after = second["outcome"] == reference
        transition = (
            "wrong_to_correct"
            if not correct_before and correct_after
            else "correct_to_wrong"
            if correct_before and not correct_after
            else "both_correct"
            if correct_before
            else "both_wrong"
        )
    return {
        "axis": axis,
        "stage": stage,
        "case_id": after["case_id"],
        "model": after["model"],
        "model_digest": after.get("model_digest"),
        "repeat": after["repeat"],
        "baseline_policy": before["evidence_policy"],
        "intervention_policy": after["evidence_policy"],
        "baseline_protocol": before["protocol"],
        "intervention_protocol": after["protocol"],
        "reference_outcome": reference,
        "baseline": first,
        "intervention": second,
        "identity_eligible": not excluded,
        "exclusion_reasons": excluded,
        "both_valid": both_valid,
        "transition": transition,
        "outcome_changed": first["outcome"] != second["outcome"] if both_valid else None,
        "patient_input_sha256": patient_identity(new),
        **evidence_difference(old, new),
        "support_review": "pending_independent_review",
    }


def analyze_diagnostics(rows, manifest):
    indexed = {condition_key(row): row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError("Duplicate diagnostic condition")
    groups = defaultdict(list)
    for row in rows:
        groups[
            row["model"], row.get("model_digest"), row["evidence_policy"], row["protocol"]
        ].append(row)
    metrics = []
    for (model, revision, policy, protocol), group in sorted(
        groups.items(), key=lambda item: str(item[0])
    ):
        for stage in STAGES:
            answers = [answer_at(row, stage) for row in group]
            valid = sum(answer["status"] == "completed" for answer in answers)
            correct = sum(
                answer["status"] == "completed" and answer["outcome"] == row["reference_outcome"]
                for row, answer in zip(group, answers, strict=True)
            )
            metrics.append(
                {
                    "model": model,
                    "model_digest": revision,
                    "evidence_policy": policy,
                    "protocol": protocol,
                    "stage": stage,
                    "recorded_conditions": len(group),
                    "valid": valid,
                    "failures": len(group) - valid,
                    "correct": correct,
                    "engineering_reference_agreement_all_conditions": correct / len(group),
                    "agreement_valid_only": correct / valid if valid else None,
                    "recoveries": sum(
                        answer_at(row, "first_attempt")["status"] != "completed"
                        and answer_at(row, "final_with_repair")["status"] == "completed"
                        for row in group
                    ),
                    "recorded_model_attempts": sum(
                        bool(row.get("attempts"))
                        if stage == "first_attempt"
                        else len(row.get("attempts", []))
                        for row in group
                    ),
                    "stage_seconds": sum(
                        (row.get("attempts") or [{}])[0].get("seconds", 0)
                        if stage == "first_attempt"
                        else row.get("seconds", 0)
                        for row in group
                    ),
                }
            )
    pairs = []
    missing = []
    for row in rows:
        comparisons = []
        if row["protocol"] == "evidence_contract":
            comparisons.append(("protocol", {**row, "protocol": "baseline"}))
        if row["evidence_policy"] == "documented_modules":
            comparisons.append(("evidence_policy", {**row, "evidence_policy": "hybrid_fixed"}))
        for axis, comparator in comparisons:
            baseline = indexed.get(condition_key(comparator))
            if baseline is None:
                missing.append(
                    {
                        "axis": axis,
                        "condition": list(condition_key(row)),
                        "missing_comparator": list(condition_key(comparator)),
                    }
                )
            else:
                pairs.extend(pair_conditions(baseline, row, axis, stage) for stage in STAGES)
    pair_groups = defaultdict(list)
    for pair in pairs:
        pair_groups[
            pair["axis"],
            pair["stage"],
            pair["model"],
            pair["model_digest"],
            pair["baseline_policy"],
            pair["intervention_policy"],
            pair["baseline_protocol"],
            pair["intervention_protocol"],
        ].append(pair)
    paired_metrics = []
    for key, group in sorted(pair_groups.items(), key=lambda item: str(item[0])):
        names = (
            "axis",
            "stage",
            "model",
            "model_digest",
            "baseline_policy",
            "intervention_policy",
            "baseline_protocol",
            "intervention_protocol",
        )
        paired_metrics.append(
            {
                **dict(zip(names, key, strict=True)),
                "recorded_pairs": len(group),
                "eligible_accepted_pairs": sum(
                    pair["identity_eligible"] and pair["both_valid"] for pair in group
                ),
                "transitions": dict(Counter(pair["transition"] for pair in group)),
            }
        )
    planned = manifest.get("planned_conditions")
    return {
        "phase": manifest.get("phase", "targeted_diagnostic_development_set"),
        "evaluation_scope": "Known-error diagnostic development pilot; not independent validation",
        "recorded_conditions": len(rows),
        "planned_conditions": planned,
        "execution_status": "completed" if planned == len(rows) else "partial",
        "metrics": metrics,
        "paired_metrics": paired_metrics,
        "pairs": pairs,
        "missing_comparators": missing,
        "failures": [
            {
                **{field: row[field] for field in CONDITION_FIELDS},
                "stage": stage,
                "error": answer_at(row, stage)["error"],
            }
            for row in rows
            for stage in STAGES
            if answer_at(row, stage)["status"] != "completed"
        ],
        "model_revision_changes": manifest.get("model_revision_changes", {}),
        "model_revision_warning": "Only contemporaneous conditions with identical model digests are paired. Do not attribute differences from historical model revisions to this intervention.",
        "clinical_accuracy": None,
        "production_change": False,
        "interpretation": "Paired changes describe an association for this development pilot, not single-passage causality. Protocol changes include instructions and output schema. Failures are separate from accepted wrong predictions. Quote presence establishes provenance, not entailment or clinical correctness.",
    }


def criterion_review_rows(rows):
    """Recheck original quote spans without assigning semantic or clinical support."""
    review = []
    for row in rows:
        payload = row["input_snapshot"]
        sources = {source["source_id"]: source for source in payload["guideline_evidence"]}
        if len(sources) != len(payload["guideline_evidence"]):
            raise ValueError("Duplicate source identifier in a supplied evidence bundle")
        facts = payload["verified_patient_facts"]
        for attempt in row.get("attempts", []):
            proposed = attempt.get("answer")
            if not isinstance(proposed, dict):
                try:
                    proposed = json.loads(
                        attempt.get("raw_response", {}).get("message", {}).get("content", "")
                    )
                except (ValueError, TypeError):
                    continue
            if not isinstance(proposed, dict):
                continue
            checks = proposed.get("criterion_checks", [])
            if not isinstance(checks, list):
                continue
            for index, check in enumerate(checks):
                if not isinstance(check, dict):
                    continue
                source_id = check.get("source_id")
                source = sources.get(source_id) if isinstance(source_id, str) else None
                quote = check.get("guideline_quote")
                spans = (
                    quote_locations(quote, source["source_text"])
                    if source and isinstance(quote, str)
                    else []
                )
                fields = check.get("fact_fields", [])
                if not isinstance(fields, list) or any(
                    not isinstance(field, str) for field in fields
                ):
                    fields = []
                item = {
                    "review_id": digest(
                        {
                            "condition": condition_key(row),
                            "attempt": attempt["number"],
                            "criterion": index,
                        }
                    ),
                    **{field: row[field] for field in CONDITION_FIELDS},
                    "model_digest": row.get("model_digest", ""),
                    "attempt_number": attempt["number"],
                    "attempt_status": attempt.get("status", "failed"),
                    "condition_status": row["status"],
                    "criterion_index": index,
                    "attempt_outcome": proposed.get("assessment_outcome", ""),
                    "final_outcome": answer_at(row, "final_with_repair")["outcome"] or "",
                    "reference_outcome": row["reference_outcome"],
                    "module": check.get("module", ""),
                    "licence_pathway": check.get("licence_pathway", ""),
                    "finding": check.get("finding", ""),
                    "criterion_conclusion": check.get("conclusion", ""),
                    "source_id": source_id if isinstance(source_id, str) else "",
                    "proposed_criterion_json": json.dumps(
                        check, ensure_ascii=False, sort_keys=True
                    ),
                    "pdf_page": source.get("pdf_page", "") if source else "",
                    "section": source.get("section", "") if source else "",
                    "source_text": source["source_text"] if source else "",
                    "proposed_guideline_quote": quote or "",
                    "original_quote_spans_json": json.dumps(
                        spans, ensure_ascii=False, sort_keys=True
                    ),
                    "quote_provenance": "unprovided_source"
                    if source is None
                    else "absent_quote"
                    if not spans
                    else "ambiguous_quote"
                    if len(spans) > 1
                    else "matched_original_quote",
                    "verified_fact_fields_json": json.dumps(
                        {field: facts[field] for field in fields if field in facts},
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    "unverified_fact_fields_json": json.dumps(
                        [field for field in fields if field not in facts]
                    ),
                    "patient_input_sha256": patient_identity(payload),
                    "supplied_evidence_sha256": digest(payload["guideline_evidence"]),
                }
                item["immutable_row_sha256"] = digest(item)
                review.append({**item, **MANUAL_DEFAULTS})
    return review


def write_review(path, rows):
    """Preserve reviewer entries; refuse to attach them to changed source material."""
    values = {row["review_id"]: row.copy() for row in rows}
    if len(values) != len(rows):
        raise ValueError("Duplicate criterion review identity")
    fields = list(rows[0]) if rows else ["review_id", "immutable_row_sha256", *MANUAL_DEFAULTS]
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as stream:
            previous = list(csv.DictReader(stream))
        seen = set()
        for old in previous:
            key = old["review_id"]
            if key in seen:
                raise ValueError("Duplicate existing review identity")
            seen.add(key)
            new = values.get(key)
            if new is None or old.get("immutable_row_sha256") != new["immutable_row_sha256"]:
                raise ValueError("Review source material changed; preserve the existing worksheet")
            for field, value in old.items():
                if field in MANUAL_DEFAULTS or field not in new:
                    new[field] = value
                    if field not in fields:
                        fields.append(field)
                elif ("" if new[field] is None else str(new[field])) != value:
                    raise ValueError(
                        "Immutable review column changed; preserve the existing worksheet"
                    )
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(values.values())
    temporary.replace(path)


def load_snapshot(path):
    raw = path.read_bytes()
    end = raw.rfind(b"\n") + 1
    complete = raw[:end]
    rows = [json.loads(line) for line in complete.decode("utf-8").splitlines() if line.strip()]
    return rows, {
        "path": str(path.resolve()),
        "completed_prefix_sha256": sha256_bytes(complete),
        "completed_prefix_bytes": len(complete),
        "uncommitted_tail_bytes": len(raw) - len(complete),
    }


def export_diagnostic_analysis(output):
    output = Path(output)
    manifest_path = output / "manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    rows, snapshot = load_snapshot(output / "results.jsonl")
    analysis = analyze_diagnostics(rows, manifest)
    code = {}
    for name in [
        "diagnostic_analysis.py",
        "evidence_judgment.py",
        "evidence_selection.py",
        "judgment_diagnostics.py",
    ]:
        path = Path(__file__).parent / name
        code[name] = sha256_bytes(path.read_bytes())
    runtime_code = {
        name: (Path(__file__).parent / name).read_text(encoding="utf-8")
        for name in ["evidence_judgment.py", "evidence_selection.py", "judgment_diagnostics.py"]
    }
    analysis["provenance"] = {
        "results_snapshot": snapshot,
        "manifest_path": str(manifest_path.resolve()),
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "run_code_sha256": manifest.get("code_sha256"),
        "observed_code_sha256": code,
        "observed_runtime_code_matches_manifest": digest(runtime_code)
        == manifest.get("code_sha256"),
        "baseline_fingerprints": manifest.get("baseline_fingerprints", {}),
    }
    review = criterion_review_rows(rows)
    write_review(output / "review.csv", review)
    analysis["criterion_review_items"] = len(review)
    analysis["review_status"] = (
        "Pending human review; worksheet entries are not automatically approved"
    )
    write_json(output / "diagnostic_analysis.json", analysis)
    return {
        "recorded_conditions": len(rows),
        "planned_conditions": analysis["planned_conditions"],
        "paired_stage_records": len(analysis["pairs"]),
        "criterion_review_items": len(review),
        "execution_status": analysis["execution_status"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    print(json.dumps(export_diagnostic_analysis(parser.parse_args().output), indent=2))
