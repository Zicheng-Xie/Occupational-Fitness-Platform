"""Independent paired analysis and review export for the passage comparison."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from occupational_fitness_rag.evaluation.diagnostic_analysis import (
    MANUAL_DEFAULTS,
    STAGES,
    pair_conditions,
    write_review,
)
from occupational_fitness_rag.evaluation.evidence_judgment import quote_locations
from occupational_fitness_rag.evaluation.passage_comparison import condition_key
from occupational_fitness_rag.evaluation.passage_judgment import passage_catalogue
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json


def analyze(rows, manifest):
    expected = {tuple(key) for key in manifest["planned_keys"]}
    indexed = {condition_key(row): row for row in rows}
    if len(expected) != manifest["planned_conditions"]:
        raise ValueError("Manifest planned keys and count disagree")
    if len(indexed) != len(rows) or not indexed.keys() <= expected:
        raise ValueError("Duplicate or unexpected passage comparison condition")
    for row in rows:
        if row["experiment_identity"] != manifest["identity"]:
            raise ValueError("Recorded result has a different experiment identity")
        pin = manifest["environment"]["model_digests"].get(row["model"])
        if not pin or row["model_digest"] != pin:
            raise ValueError("Recorded model digest differs from the experiment pin")
        if "input_snapshot" in row and digest(row["input_snapshot"]) != row["input_sha256"]:
            raise ValueError("Recorded patient/evidence payload fingerprint changed")
        for attempt in row.get("attempts", []):
            if digest(attempt["request"]) != attempt["request_sha256"]:
                raise ValueError("Original model request fingerprint changed")
            if attempt["status"] == "completed" and attempt.get("error"):
                raise ValueError("An accepted attempt also carries a failure")
    pairs, missing = [], []
    for row in rows:
        controls = []
        if row["protocol"] == "passage_selection":
            controls.append(("protocol", {**row, "protocol": "quote_contract"}))
        if row["evidence_policy"] == "module_query":
            controls.append(("evidence_policy", {**row, "evidence_policy": "mixed_query"}))
        for axis, control in controls:
            before = indexed.get(condition_key(control))
            if before is None:
                missing.append({"axis": axis, "condition": list(condition_key(row))})
                continue
            if "input_snapshot" not in before or "input_snapshot" not in row:
                missing.append(
                    {
                        "axis": axis,
                        "condition": list(condition_key(row)),
                        "reason": "retrieval_failed",
                    }
                )
                continue
            pairs.extend(pair_conditions(before, row, axis, stage) for stage in STAGES)
    groups = defaultdict(list)
    for pair in pairs:
        groups[
            pair["axis"],
            pair["stage"],
            pair["model"],
            pair["baseline_policy"],
            pair["intervention_policy"],
            pair["baseline_protocol"],
            pair["intervention_protocol"],
        ].append(pair)
    fields = [
        "axis",
        "stage",
        "model",
        "baseline_policy",
        "intervention_policy",
        "baseline_protocol",
        "intervention_protocol",
    ]
    metrics = [
        {
            **dict(zip(fields, key, strict=True)),
            "pairs": len(group),
            "accepted_identity_matched_pairs": sum(
                p["both_valid"] and p["identity_eligible"] for p in group
            ),
            "transitions": dict(Counter(p["transition"] for p in group)),
        }
        for key, group in sorted(groups.items())
    ]
    return {
        "phase": manifest["phase"],
        "planned_conditions": len(expected),
        "recorded_conditions": len(rows),
        "execution_status": "completed" if set(indexed) == expected else "partial",
        "missing_conditions": [list(key) for key in sorted(expected - indexed.keys())],
        "paired_metrics": metrics,
        "pairs": pairs,
        "missing_comparators": missing,
        "clinical_accuracy": None,
        "production_change": False,
        "support_review": "pending_independent_review",
        "interpretation": "Query and protocol changes are evaluated separately on a known-error development set. A valid passage ID establishes provenance, not clinical applicability or explanation support. Failures are separate from accepted incorrect classifications.",
    }


def review_rows(rows):
    """Preserve proposed IDs and resolve raw attempts without accepting predictions."""
    review = []
    for row in rows:
        payload = row.get("input_snapshot")
        if payload is None:
            continue
        sources = {source["source_id"]: source for source in payload["guideline_evidence"]}
        catalogue = passage_catalogue(payload)
        for attempt in row.get("attempts", []):
            try:
                proposed = json.loads(
                    attempt.get("raw_response", {}).get("message", {}).get("content", "")
                )
            except (ValueError, TypeError, AttributeError):
                continue
            if not isinstance(proposed, dict) or not isinstance(
                proposed.get("criterion_checks"), list
            ):
                continue
            for index, check in enumerate(proposed["criterion_checks"]):
                if not isinstance(check, dict):
                    continue
                selected = row["protocol"] == "passage_selection"
                pid = check.get("passage_id")
                anchor = catalogue.get(pid) if selected and isinstance(pid, str) else None
                sid = (
                    anchor["source_id"] if anchor else None if selected else check.get("source_id")
                )
                source = sources.get(sid) if isinstance(sid, str) else None
                quote = (
                    anchor["original_quote"]
                    if anchor
                    else ""
                    if selected
                    else check.get("guideline_quote", "")
                )
                spans = (
                    [{key: anchor[key] for key in ("char_start", "char_end", "original_quote")}]
                    if anchor
                    else quote_locations(quote, source["source_text"])
                    if source and isinstance(quote, str)
                    else []
                )
                explicit_fields = check.get("fact_fields", [])
                if not isinstance(explicit_fields, list):
                    explicit_fields = []
                facts = {
                    field: payload["verified_patient_facts"][field]
                    for field in explicit_fields
                    if isinstance(field, str) and field in payload["verified_patient_facts"]
                }
                identity = [list(condition_key(row)), attempt["number"], index]
                material = {
                    "review_id": digest(identity),
                    **{
                        field: row[field]
                        for field in (
                            "case_id",
                            "model",
                            "model_digest",
                            "evidence_policy",
                            "protocol",
                            "repeat",
                        )
                    },
                    "attempt_number": attempt["number"],
                    "criterion_index": index,
                    "attempt_status": attempt["status"],
                    "condition_status": row["status"],
                    "attempt_outcome": proposed.get("assessment_outcome"),
                    "final_outcome": row.get("answer", {}).get("assessment_outcome"),
                    "reference_outcome": row["reference_outcome"],
                    "proposed_check_json": json.dumps(check, ensure_ascii=False),
                    "passage_id": check.get("passage_id"),
                    "resolved_source_id": sid,
                    "pdf_page": source.get("pdf_page") if source else None,
                    "section": source.get("section") if source else None,
                    "original_source_text": source["source_text"] if source else "",
                    "resolved_original_quote": quote if isinstance(quote, str) else "",
                    "original_quote_spans_json": json.dumps(spans, ensure_ascii=False),
                    "mechanical_provenance": "program_resolved_full_passage"
                    if anchor
                    else "matched_model_quote"
                    if spans
                    else "unresolved",
                    "offset_unit": "python_unicode_code_points",
                    "verified_patient_facts_json": json.dumps(facts, ensure_ascii=False),
                    "output_consistency_flags_json": json.dumps(
                        attempt.get("output_consistency_flags", [])
                    ),
                    "patient_input_sha256": row["input_sha256"],
                }
                review.append(
                    {**material, "immutable_row_sha256": digest(material), **MANUAL_DEFAULTS}
                )
    return review


def export_analysis(output):
    output = Path(output)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    raw = (output / "results.jsonl").read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise ValueError("Incomplete JSONL tail; preserve it before exporting analysis")
    # Analyze exactly the bytes being fingerprinted, even if inference appends later.
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    result = analyze(rows, manifest)
    frozen = json.loads((output / "retrieval_freeze.json").read_text(encoding="utf-8"))
    if frozen["identity"] != manifest["identity"]:
        raise ValueError("Retrieval snapshot experiment identity changed")
    for name, fingerprint in frozen["artifacts"].items():
        if sha256_bytes((output / name).read_bytes()) != fingerprint:
            raise ValueError("Frozen retrieval evidence changed")
    snapshot = json.loads((output / "source_snapshot.json").read_text(encoding="utf-8"))
    if digest(snapshot) != manifest["sources_sha256"]:
        raise ValueError("Original code snapshot fingerprint changed")
    review = review_rows(rows)
    write_review(output / "review.csv", review)
    result["criterion_review_items"] = len(review)
    result["provenance"] = {
        "experiment_identity": manifest["identity"],
        "results_sha256": sha256_bytes(raw),
        "results_bytes": len(raw),
        "manifest_sha256": sha256_bytes((output / "manifest.json").read_bytes()),
        "retrieval_artifacts_verified": True,
        "recorded_source_snapshot_verified": True,
    }
    write_json(output / "paired_analysis.json", result)
    return {
        key: result[key]
        for key in (
            "recorded_conditions",
            "planned_conditions",
            "execution_status",
            "criterion_review_items",
        )
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    print(json.dumps(export_analysis(parser.parse_args().output), indent=2))
