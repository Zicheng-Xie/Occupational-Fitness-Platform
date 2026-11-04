"""Freeze a source-literal engineering sensitivity version without changing production facts.

Only exact JSON literals already present before semantic quarantine are eligible. No
reference outcome is consulted, and the original model review remains attached.
"""

import argparse
import hashlib
import importlib.util
import json
from collections import Counter
from copy import deepcopy
from html import escape
from pathlib import Path

VERSION = "source_literal_facts_v1"
POLICY = "all_changed_fields_exact_typed_unanimous_json_literals_with_verified_prior_spans_v1"
PATIENT_FIELDS = {"licence_context", "modules", "nurse_note", "verified_patient_facts"}


def fingerprint(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return fingerprint(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    )


def literal_api():
    spec = importlib.util.spec_from_file_location(
        "source_literal_audit", Path(__file__).with_name("audit_frozen_fact_literals.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def within(root, path):
    path = (root / path).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Input or output path escapes the project")
    return path


def _prepare(root, baseline, audit_dir, retrieval_dir):
    root = Path(root).resolve()
    baseline, audit_dir, retrieval_dir = [
        within(root, Path(path)) for path in (baseline, audit_dir, retrieval_dir)
    ]
    pins = {}

    def read(path):
        path = within(root, path)
        raw = path.read_bytes()
        pins[path.relative_to(root).as_posix()] = fingerprint(raw)
        return json.loads(raw)

    upstream = read(baseline / "upstream_audit.json")
    audit = read(audit_dir / "fact_revalidation_audit.json")
    frozen = read(retrieval_dir / "frozen_inputs.json")
    manifest = read(retrieval_dir / "manifest.json")
    if digest(frozen) != manifest["patient_inputs_sha256"]:
        raise ValueError("Frozen patient input identity differs")
    if (
        audit["upstream_audit_sha256"]
        != pins[(baseline / "upstream_audit.json").relative_to(root).as_posix()]
    ):
        raise ValueError("The literal audit does not bind the upstream audit")
    upstream_cases = {row["case_id"]: row for row in upstream["cases"]}
    audit_cases = {row["case_id"]: row for row in audit["cases"]}
    if len(upstream_cases) != len(upstream["cases"]) or len(audit_cases) != len(audit["cases"]):
        raise ValueError("Duplicate upstream or audit case")
    if set(upstream_cases) != set(frozen):
        raise ValueError("Frozen and upstream case sets differ")
    expected_audit = {case_id for case_id, row in upstream_cases.items() if row["changed_fields"]}
    if set(audit_cases) != expected_audit:
        raise ValueError("Literal audit must cover every changed case")
    api = literal_api()
    cases = {}
    for case_id, original in frozen.items():
        payload = original["payload"]
        patient = {key: payload[key] for key in PATIENT_FIELDS}
        if any(key not in payload for key in PATIENT_FIELDS):
            raise ValueError("Incomplete original patient payload")
        snapshot_path = baseline / "frozen_cases" / (case_id + ".json")
        snapshot = read(snapshot_path)
        case = snapshot["case"]
        if case["case_id"] != case_id or digest(case) != snapshot["case_sha256"]:
            raise ValueError("Frozen case identity differs")
        expected_facts = {
            field: {
                "value": fact["value"],
                "patient_quotes": [span["quote"] for span in fact["evidence"]],
            }
            for field, fact in case["facts"].items()
            if fact["status"] == "present"
        }
        if (
            digest(expected_facts) != digest(patient["verified_patient_facts"])
            or case["source_text"] != patient["nurse_note"]
            or case["licence_context"] != patient["licence_context"]
            or case["modules_requested"] != patient["modules"]
        ):
            raise ValueError("Original frozen patient facts differ from their case snapshot")
        source_matches = []
        for candidate in (root / "data" / "cases").rglob(case["source_document"]):
            candidate = within(root, candidate)
            if candidate.is_file() and fingerprint(candidate.read_bytes()) == case["source_sha256"]:
                source_matches.append(candidate)
        if len(source_matches) != 1:
            raise ValueError("Original source must resolve to one exact file")
        source_path = source_matches[0]
        source_raw = source_path.read_bytes()
        text = source_raw.decode("utf-8-sig")
        if text != case["source_text"] or fingerprint(text.encode("utf-8")) != case["text_sha256"]:
            raise ValueError("Original source text changed")
        relative = source_path.relative_to(root).as_posix()
        pins[relative] = fingerprint(source_raw)
        prior_audit = audit_cases.get(case_id)
        if prior_audit is not None and (
            prior_audit["source"] != relative
            or prior_audit["source_raw_sha256"] != fingerprint(source_raw)
            or prior_audit["decoded_text_sha256"] != fingerprint(text.encode("utf-8"))
            or audit["source_files_sha256"].get(relative) != fingerprint(source_raw)
        ):
            raise ValueError("Literal audit source pin differs")
        original_facts = deepcopy(patient["verified_patient_facts"])
        sensitivity_facts = deepcopy(original_facts)
        changes, unchanged = [], []
        changed_fields = upstream_cases[case_id]["changed_fields"]
        if len({entry["field"] for entry in changed_fields}) != len(changed_fields):
            raise ValueError("Duplicate changed field")
        audited_fields = (
            {field["field"]: field for field in prior_audit["fields"]} if prior_audit else {}
        )
        if set(audited_fields) != {field["field"] for field in changed_fields}:
            raise ValueError("Literal audit changed-field coverage differs")
        for changed in changed_fields:
            field = changed["field"]
            if field not in case["facts"] or digest(case["facts"][field]) != digest(
                changed["frozen"]
            ):
                raise ValueError("Quarantined field differs from its original frozen record")
            inspected = api.inspect_field(text, changed)
            if digest(inspected) != digest(audited_fields[field]):
                raise ValueError(
                    "Literal audit does not match independently recomputed spans and types"
                )
            entry = {
                "field": field,
                "before": deepcopy(changed["before"]),
                "frozen": deepcopy(changed["frozen"]),
                "literal_spans": inspected["literal_spans"],
                "prior_quoted_spans_verified": inspected["prior_quoted_spans_verified"],
            }
            eligible = (
                inspected["status"] == "explicit_literal_revalidation_candidate"
                and inspected["prior_quoted_spans_verified"]
                and changed["before"].get("status") == "present"
                and changed["frozen"].get("status") == "requires_confirmation"
                and field not in original_facts
            )
            if eligible:
                restored = {
                    "value": deepcopy(inspected["literal_spans"][0]["value"]),
                    "patient_quotes": [span["quote"] for span in inspected["literal_spans"]],
                }
                sensitivity_facts[field] = restored
                changes.append(
                    {
                        **entry,
                        "restored": deepcopy(restored),
                        "review_status": "pending_clinical_review",
                        "reason": POLICY,
                    }
                )
            else:
                unchanged.append({**entry, "status": inspected["status"]})
        sensitivity_patient = {**patient, "verified_patient_facts": sensitivity_facts}
        cases[case_id] = {
            "original_patient_identity": digest(patient),
            "sensitivity_patient_identity": digest(sensitivity_patient),
            "original_verified_patient_facts": original_facts,
            "sensitivity_verified_patient_facts": sensitivity_facts,
            "source": {
                "path": relative,
                "raw_sha256": fingerprint(source_raw),
                "decoded_text_sha256": fingerprint(text.encode("utf-8")),
            },
            "changes": changes,
            "unchanged_changed_fields": unchanged,
            "semantic_review_audit": {
                "original_frozen_case_sha256": pins[snapshot_path.relative_to(root).as_posix()],
                "semantic_review": deepcopy(snapshot["semantic_review"]),
            },
        }
    report = {
        "version": VERSION,
        "metadata": {
            "baseline_dir": baseline.relative_to(root).as_posix(),
            "audit_dir": audit_dir.relative_to(root).as_posix(),
            "retrieval_dir": retrieval_dir.relative_to(root).as_posix(),
            "retrieval_identity": manifest["identity"],
            "input_sha256": pins,
            "builder_sha256": fingerprint(Path(__file__).read_bytes()),
            "literal_audit_tool_sha256": fingerprint(
                Path(__file__).with_name("audit_frozen_fact_literals.py").read_bytes()
            ),
            "eligibility_policy": POLICY,
            "clinical_review": "pending",
            "production_change": False,
            "held_fixed": [
                "nurse_note",
                "modules",
                "licence_context",
                "guideline_evidence",
                "retrieval_queries",
            ],
            "retrieval_interpretation": "Original queries and selected evidence are held fixed; this is a fact sensitivity replay, not fresh retrieval.",
            "case_count": len(cases),
            "changed_case_count": sum(bool(case["changes"]) for case in cases.values()),
            "restored_field_count": sum(len(case["changes"]) for case in cases.values()),
            "unrestored_field_count": sum(
                len(case["unchanged_changed_fields"]) for case in cases.values()
            ),
            "unrestored_status_counts": dict(
                Counter(
                    field["status"]
                    for case in cases.values()
                    for field in case["unchanged_changed_fields"]
                )
            ),
            "offset_representation": "Python Unicode code points after UTF-8 BOM removal; original CRLF/LF preserved",
            "reference_outcomes_consulted": False,
        },
        "cases": cases,
    }
    return {**report, "identity": digest(report)}


def load_snapshot(path, root):
    """Recompute all source-bound decisions and reject modified inputs or artifacts."""
    path, root = Path(path).resolve(), Path(root).resolve()
    if path.is_dir():
        path /= "source_literal_facts.json"
    saved = json.loads(within(root, path).read_bytes())
    if digest({key: value for key, value in saved.items() if key != "identity"}) != saved.get(
        "identity"
    ):
        raise ValueError("Fact snapshot self-identity differs")
    metadata = saved["metadata"]
    expected = _prepare(
        root, metadata["baseline_dir"], metadata["audit_dir"], metadata["retrieval_dir"]
    )
    if saved != expected:
        raise ValueError("Fact snapshot differs from verified source inputs or builder")
    return saved


def build_snapshot(root, baseline, audit_dir, retrieval_dir, output):
    root = Path(root).resolve()
    output = within(root, output)
    if any(
        output == within(root, path) or output.is_relative_to(within(root, path))
        for path in (baseline, audit_dir, retrieval_dir)
    ):
        raise ValueError("Fact sensitivity output must be separate from all frozen inputs")
    report = _prepare(root, baseline, audit_dir, retrieval_dir)
    path = output / "source_literal_facts.json"
    raw = (json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    if path.exists() and path.read_bytes() != raw:
        raise ValueError("Existing fact snapshot differs; preserve it and choose a new version")
    output.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    rows = "".join(
        "<tr>"
        + "".join(
            "<td>" + escape(str(value)) + "</td>"
            for value in [
                case_id,
                change["field"],
                json.dumps(change["frozen"]["value"]),
                json.dumps(change["restored"]["value"]),
                "; ".join(
                    f"Line {span['line']}: {span['quote']}" for span in change["literal_spans"]
                ),
                "Clinical review pending",
            ]
        )
        + "</tr>"
        for case_id, case in report["cases"].items()
        for change in case["changes"]
    )
    metadata = report["metadata"]
    html = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Source literal fact sensitivity</title><style>body{font:14px/1.6 Segoe UI,Arial;margin:36px;color:#243244}table{border-collapse:collapse;width:100%}td,th{padding:12px;border-bottom:1px solid #dce3e9;text-align:left}p{max-width:1050px}</style><h1>Source literal fact sensitivity</h1>'
    html += f"<p>{metadata['case_count']} frozen cases · {metadata['changed_case_count']} changed cases · {metadata['restored_field_count']} exact literal values restored in a separate engineering snapshot · {metadata['unrestored_field_count']} noneligible changes withheld</p>"
    html += "<p>No production fact, rule, label or prior frozen artifact is modified. Original semantic review remains attached. Literal verification confirms documented values and addresses; clinical interpretation and specialist review remain pending. Original queries and selected evidence must be held fixed for the fact sensitivity replay.</p><table><tr>"
    html += "".join(
        f"<th>{name}</th>"
        for name in [
            "Case",
            "Field",
            "Original frozen value",
            "Source literal",
            "Exact source span",
            "Review",
        ]
    )
    html += (
        "</tr>"
        + rows
        + '</table><p><a href="source_literal_facts.json">Complete source pins, original facts, sensitivity facts and preserved semantic review</a></p></html>'
    )
    (output / "index.html").write_text(html, encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default="outputs/experiments/judgment_comparison_v5")
    parser.add_argument("--audit", default="outputs/experiments/fact_revalidation_audit")
    parser.add_argument("--retrieval", default="outputs/experiments/passage_comparison_full_clean")
    parser.add_argument("--output", default="outputs/experiments/source_literal_facts_v1")
    args = parser.parse_args()
    result = build_snapshot(
        Path(__file__).resolve().parents[1], args.baseline, args.audit, args.retrieval, args.output
    )
    print(
        json.dumps(
            {
                "identity": result["identity"],
                **{
                    key: result["metadata"][key]
                    for key in [
                        "case_count",
                        "changed_case_count",
                        "restored_field_count",
                        "unrestored_field_count",
                    ]
                },
            }
        )
    )
