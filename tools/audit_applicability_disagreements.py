"""Expose cross-stage permission disagreements for independent source review.

This post-processing tool never calls a model, changes a judgment, or treats the
first-stage ledger as authoritative. It reads one completed experiment snapshot.
"""

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from html import escape
from pathlib import Path

KEY_FIELDS = ("model", "case_id", "evidence_policy", "protocol", "repeat")
ANNOTATIONS = ("review_status", "reviewer", "notes")
REVIEW_STATUSES = {
    "pending",
    "stage_one_supported",
    "final_supported",
    "both_unsupported",
    "uncertain",
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha256(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    )


def source_location(row, check):
    """Validate the saved location against the unchanged original payload."""
    matches = [
        item
        for item in row.get("criterion_locations", [])
        if item.get("passage_id") == check["passage_id"]
        and all(item.get("check", {}).get(key) == value for key, value in check.items())
    ]
    if not matches:
        raise ValueError("A flagged final claim has no matching saved source location")
    location = matches[0]
    sources = [
        item
        for item in row["input_snapshot"]["guideline_evidence"]
        if item["source_id"] == location["source_id"]
        and item["module"] == check["module"]
        and all(item[key] == location[key] for key in ("section", "pdf_page", "printed_page"))
    ]
    if len(sources) != 1:
        raise ValueError("A flagged source address differs from the frozen input")
    text = sources[0]["source_text"]
    if sha256(text.encode("utf-8")) != location["text_sha256"]:
        raise ValueError("A flagged original passage has an invalid text fingerprint")
    spans = location.get("spans", [])
    if not spans or any(
        not (0 <= span["char_start"] <= span["char_end"] <= len(text))
        or text[span["char_start"] : span["char_end"]] != span["original_quote"]
        for span in spans
    ):
        raise ValueError("A flagged original quotation does not match its saved span")
    return {
        key: value
        for key, value in location.items()
        if key not in {"check", "support_review", "check_origin"}
    }


def collect_disagreements(rows):
    """Select explicit structured disagreements; do not infer clinical support."""
    events = []
    for row in rows:
        if row["protocol"] != "applicability_first" or row["status"] != "completed":
            continue
        payload = row["input_snapshot"]
        if digest(payload) != row["input_sha256"]:
            raise ValueError("Saved patient and evidence payload fingerprint changed")
        original = row["stages"]["applicability"]["answer"]["passage_checks"]
        ledger = {item["passage_id"]: item for item in original}
        if len(ledger) != len(original):
            raise ValueError("Duplicate first-stage passage binding")
        for ordinal, check in enumerate(row["answer"]["criterion_checks"]):
            if check["finding"] != "conditional_permission":
                continue
            if check["passage_id"] not in ledger:
                raise ValueError("Final passage absent from its first-stage ledger")
            first = ledger[check["passage_id"]]
            reasons = []
            if first["applicability"] != "applicable":
                reasons.append("final_permission_despite_stage_one_non_applicability")
            if any(item["status"] != "met" for item in first["prerequisites"]):
                reasons.append("final_permission_despite_stage_one_unestablished_prerequisite")
            if not reasons:
                continue
            datum = {
                **{key: row[key] for key in KEY_FIELDS},
                "input_sha256": row["input_sha256"],
                "final_check_ordinal": ordinal,
                "reasons": reasons,
                "stage_one_proposal": first,
                "final_proposal": check,
                "original_passage": source_location(row, check),
                "patient_context": {
                    key: payload[key]
                    for key in (
                        "licence_context",
                        "modules",
                        "nurse_note",
                        "verified_patient_facts",
                    )
                },
            }
            events.append({"event_id": digest(datum), **datum})
    return events


def completed_snapshot(directory):
    directory = Path(directory).resolve()
    if (directory / ".run.lock").exists():
        raise ValueError("Cross-stage audit requires a stopped experiment writer")
    raw = (directory / "results.jsonl").read_bytes()
    if not raw or not raw.endswith(b"\n"):
        raise ValueError("Incomplete result snapshot")
    manifest_raw = (directory / "manifest.json").read_bytes()
    audit_raw = (directory / "execution_audit.json").read_bytes()
    manifest, audit = json.loads(manifest_raw), json.loads(audit_raw)
    if audit["results_sha256"] != sha256(raw):
        raise ValueError("Results changed after the completion audit")
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    keys = [tuple(row[key] for key in KEY_FIELDS) for row in rows]
    planned = [tuple(key) for key in manifest["planned_keys"]]
    if (
        len(keys) != len(set(keys))
        or len(planned) != len(set(planned))
        or set(keys) != set(planned)
        or any(row["experiment_identity"] != manifest["identity"] for row in rows)
    ):
        raise ValueError("Audit snapshot differs from the complete planned experiment")
    return rows, {
        "experiment_identity": manifest["identity"],
        "results_sha256": sha256(raw),
        "manifest_sha256": sha256(manifest_raw),
        "execution_audit_sha256": sha256(audit_raw),
    }


def review_records(output, events):
    existing = {}
    path = output / "review.csv"
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as stream:
            previous = list(csv.DictReader(stream))
        existing = {row["event_id"]: row for row in previous}
        if len(existing) != len(previous) or not set(existing) <= {e["event_id"] for e in events}:
            raise ValueError("Previously annotated disagreement events changed or disappeared")
        if any(row.get("review_status") not in REVIEW_STATUSES for row in previous):
            raise ValueError("Unknown review status; retain the existing worksheet for correction")
    records = []
    for event in events:
        record = {
            key: event[key] for key in ("event_id", "case_id", "model", "evidence_policy", "repeat")
        }
        record.update(
            passage_id=event["final_proposal"]["passage_id"], reasons="; ".join(event["reasons"])
        )
        for field in ANNOTATIONS:
            record[field] = existing.get(event["event_id"], {}).get(
                field, "pending" if field == "review_status" else ""
            )
        records.append(record)
    return records


def write_atomic(path, raw):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(raw)
    temporary.replace(path)


def build(directory):
    directory = Path(directory).resolve()
    rows, identity = completed_snapshot(directory)
    events = collect_disagreements(rows)
    output = directory / "cross_stage_review"
    previous_report = output / "disagreements.json"
    if previous_report.exists():
        previous = json.loads(previous_report.read_text(encoding="utf-8"))
        if any(previous[key] != value for key, value in identity.items()):
            raise ValueError("Preserve the prior audit: completed source identity changed")
    records = review_records(output, events)
    conditions = {tuple(event[key] for key in KEY_FIELDS) for event in events}
    report = {
        **identity,
        "tool_sha256": sha256(Path(__file__).read_bytes()),
        "condition_count": len(rows),
        "completed_applicability_conditions": sum(
            row["protocol"] == "applicability_first" and row["status"] == "completed"
            for row in rows
        ),
        "flagged_claim_occurrences": len(events),
        "flagged_condition_count": len(conditions),
        "reason_counts": dict(Counter(reason for event in events for reason in event["reasons"])),
        "case_claim_counts": dict(Counter(event["case_id"] for event in events)),
        "expected_labels_disclosed": False,
        "overall_model_assessments_disclosed": False,
        "judgments_changed": 0,
        "clinical_review_status": "pending",
        "interpretation": (
            "A final conditional-permission claim disagrees with the same-passage first-stage "
            "applicability or prerequisite proposal. Both proposals are fallible. A disagreement "
            "is a source-review priority, not proof that either stage is correct or a clinical "
            "error rate. Saved judgments, source inputs and production behavior are unchanged. "
            "Reference labels and overall model outcomes are withheld from these review packets."
        ),
        "events": events,
    }
    fields = [
        "event_id",
        "case_id",
        "model",
        "evidence_policy",
        "repeat",
        "passage_id",
        "reasons",
        *ANNOTATIONS,
    ]
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    writer.writerows(records)
    html = [
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>Cross-stage permission review</title>',
        "<style>body{font:14px/1.6 Segoe UI,Arial;margin:36px;color:#243244;max-width:1300px}details{border:1px solid #dce3e9;border-radius:8px;margin:12px 0;padding:14px}summary{cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.6 Consolas,monospace}.filter{padding:10px;width:min(700px,90%)}a{color:#255b83}.muted{color:#576577}</style>",
        "<h1>Cross-stage permission review</h1>",
        f"<p>{len(events)} claim occurrences across {len(conditions)} conditions require independent review.</p>",
        "<p>" + escape(report["interpretation"]) + "</p>",
        '<p><a href="review.csv">Review worksheet</a> · <a href="disagreements.json">Exact source packets and identity</a></p>',
        '<p class="muted">Review status: pending, stage_one_supported, final_supported, both_unsupported or uncertain. Record reviewer and rationale in the worksheet. Pending is never counted as reviewed. Do not treat this computer-generated audit as human or clinical review.</p>',
        '<label>Filter case, model, query policy or reason <input class="filter" id="filter" type="search"></label>',
    ]
    if (directory / "review.html").exists():
        html.append(
            '<p><a href="../review.html">Return to the complete experimental report</a></p>'
        )
    for event in events:
        label = f"{event['case_id']} · {event['model']} · {event['evidence_policy']} · Repeat {event['repeat'] + 1} · {event['event_id'][:12]}"
        html.extend(
            [
                '<details data-search="'
                + escape(label + " " + " ".join(event["reasons"]), quote=True)
                + '"><summary>'
                + escape(label)
                + "</summary>",
                "<p>" + escape("; ".join(event["reasons"])) + "</p><pre>",
                escape(json.dumps(event, ensure_ascii=False, indent=2)),
                "</pre></details>",
            ]
        )
    html.append(
        '<script>document.getElementById("filter").addEventListener("input",function(){let q=this.value.toLowerCase();document.querySelectorAll("details").forEach(d=>d.hidden=!d.dataset.search.toLowerCase().includes(q));});</script></html>'
    )
    # All validation and annotation checks precede any output replacement.
    output.mkdir(exist_ok=True)
    write_atomic(output / "review.csv", buffer.getvalue().encode("utf-8-sig"))
    write_atomic(
        previous_report, (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
    write_atomic(output / "index.html", "".join(html).encode("utf-8"))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    result = build(parser.parse_args().directory)
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "condition_count",
                    "flagged_claim_occurrences",
                    "flagged_condition_count",
                    "judgments_changed",
                )
            }
        )
    )
