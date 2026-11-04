"""Deduplicate identical evidence claims into review packets without reference labels."""

import argparse
import csv
import json
from collections import Counter
from html import escape
from pathlib import Path

from occupational_fitness_rag.provenance import digest, sha256_bytes

ANNOTATIONS = ["source_support", "patient_applicability", "licence_scope", "reviewer", "notes"]


def collect_packets(rows):
    packets = {}
    for row in rows:
        facts = row.get("input_snapshot", {}).get("verified_patient_facts", {})
        for stage_name, stage in row.get("stages", {}).items():
            for attempt in stage.get("attempts", []):
                ledger = {
                    check["passage_id"]: check
                    for check in attempt.get("answer", {}).get("passage_checks", [])
                }
                for location in attempt.get("criterion_locations", []):
                    claim = ledger.get(location.get("passage_id"), location["check"])
                    datum = {
                        "case_id": row["case_id"],
                        "stage_class": "applicability"
                        if stage_name == "applicability"
                        else "final_check",
                        "verified_patient_facts": facts,
                        "source_location": {
                            key: value
                            for key, value in location.items()
                            if key not in {"check", "support_review", "check_origin"}
                        },
                        "model_claim": claim,
                    }
                    key = digest(datum)
                    if key not in packets:
                        packets[key] = {
                            "packet_id": key,
                            **datum,
                            "occurrences": [],
                            "structural_flagged_occurrences": 0,
                        }
                    packets[key]["occurrences"].append(
                        {
                            "model": row["model"],
                            "evidence_policy": row["evidence_policy"],
                            "protocol": row["protocol"],
                            "repeat": row["repeat"],
                            "stage": stage_name,
                            "attempt": attempt["number"],
                        }
                    )
                    packets[key]["structural_flagged_occurrences"] += bool(
                        attempt.get("ledger_consistency_flags")
                        or attempt.get("output_consistency_flags")
                    )
    return list(packets.values())


def build(directory):
    directory = Path(directory).resolve()
    if (directory / ".run.lock").exists():
        raise ValueError("Review packets require a stopped writer")
    raw = (directory / "results.jsonl").read_bytes()
    completed_audit = directory / "execution_audit.json"
    if completed_audit.exists() and json.loads(completed_audit.read_text(encoding="utf-8"))[
        "results_sha256"
    ] != sha256_bytes(raw):
        raise ValueError("Results changed since the completion audit")
    if not raw or not raw.endswith(b"\n"):
        raise ValueError("Incomplete result snapshot")
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    keys = [
        tuple(row[key] for key in ("model", "case_id", "evidence_policy", "protocol", "repeat"))
        for row in rows
    ]
    if (
        len(keys) != len(set(keys))
        or set(keys) != {tuple(key) for key in manifest["planned_keys"]}
        or any(row["experiment_identity"] != manifest["identity"] for row in rows)
    ):
        raise ValueError("Review snapshot differs from the complete planned experiment")
    packets = collect_packets(rows)
    output = directory / "support_review"
    output.mkdir(exist_ok=True)
    path = output / "review.csv"
    existing = {}
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as stream:
            previous = list(csv.DictReader(stream))
        existing = {row["packet_id"]: row for row in previous}
        if len(existing) != len(previous) or not set(existing) <= {
            packet["packet_id"] for packet in packets
        }:
            raise ValueError("Previously annotated review packets changed or disappeared")
    records = []
    for packet in packets:
        record = {
            "packet_id": packet["packet_id"],
            "case_id": packet["case_id"],
            "stage_class": packet["stage_class"],
            "occurrence_count": len(packet["occurrences"]),
        }
        for field in ANNOTATIONS:
            record[field] = existing.get(packet["packet_id"], {}).get(
                field, "pending" if field not in {"reviewer", "notes"} else ""
            )
        records.append(record)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    report = {
        "experiment_identity": manifest["identity"],
        "results_sha256": sha256_bytes(raw),
        "tool_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "original_claim_occurrences": sum(len(packet["occurrences"]) for packet in packets),
        "unique_review_packets": len(packets),
        "stage_counts": dict(Counter(packet["stage_class"] for packet in packets)),
        "expected_labels_disclosed": False,
        "interpretation": "Exact duplicate claims only are grouped. Stage-one proposals and final checks remain separate. Source addresses and patient facts are supplied; engineering reference labels and the overall assessment field are withheld from this worksheet. The claim text remains unedited. This does not perform human review or establish clinical accuracy.",
        "packets": packets,
    }
    (output / "packets.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    html = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Independent evidence support review</title><style>body{font:14px/1.6 Segoe UI,Arial;margin:32px;color:#243244}details{border-top:1px solid #d6dfe6;padding:14px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}summary{cursor:pointer}p{max-width:1100px}</style><h1>Independent evidence support review</h1>'
    html += f'<p>{report["original_claim_occurrences"]} recorded claim occurrences · {len(packets)} unique exact-claim packets</p><p>{escape(report["interpretation"])}</p><p><a href="review.csv">Editable review worksheet</a> · <a href="packets.json">Exact locations and occurrences</a></p>'
    html += "<p>For each packet: verify the original passage and patient quotations; check applicability to the current patient and investigation status; distinguish restriction triggers from permission prerequisites; verify numeric comparisons and licence pathways. In review.csv, enter source_support as supported/unsupported/uncertain, patient_applicability as applicable/not_applicable/uncertain, and licence_scope from the original clause. Add reviewer identity and a concise rationale. Pending fields are never counted as reviewed. These annotations do not establish the overall clinical outcome.</p>"
    for packet in sorted(
        packets,
        key=lambda item: (
            -item["structural_flagged_occurrences"],
            item["case_id"],
            item["packet_id"],
        ),
    ):
        content = {
            key: value
            for key, value in packet.items()
            if key not in {"occurrences", "structural_flagged_occurrences"}
        }
        html += (
            "<details><summary>"
            + escape(
                f"{packet['case_id']} · {packet['stage_class']} · {packet['packet_id'][:12]} · {len(packet['occurrences'])} occurrences"
            )
            + "</summary><p>Judge source support, patient applicability and licence scope independently; do not infer correctness from a valid address.</p><pre>"
            + escape(json.dumps(content, ensure_ascii=False, indent=2))
            + "</pre></details>"
        )
    (output / "index.html").write_text(html + "</html>", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    report = build(parser.parse_args().directory)
    print(
        json.dumps(
            {
                key: report[key]
                for key in [
                    "original_claim_occurrences",
                    "unique_review_packets",
                    "stage_counts",
                    "expected_labels_disclosed",
                ]
            }
        )
    )
