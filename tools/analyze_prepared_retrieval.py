"""Score frozen evidence availability without making fitness judgments."""

import argparse
import json
from collections import defaultdict
from html import escape
from pathlib import Path

from occupational_fitness_rag.provenance import digest, sha256_bytes


def analyze(directory):
    directory = Path(directory)
    if (directory / ".run.lock").exists():
        raise ValueError("Frozen retrieval writer must finish before analysis")
    freeze = json.loads((directory / "retrieval_freeze.json").read_text(encoding="utf-8"))
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if freeze["identity"] != manifest["identity"]:
        raise ValueError("Retrieval identities differ")
    for filename, expected in freeze["artifacts"].items():
        if sha256_bytes((directory / filename).read_bytes()) != expected:
            raise ValueError("Frozen retrieval artifact changed")
    corpus = json.loads((directory / "corpus.json").read_text(encoding="utf-8"))
    if (
        digest({key: value for key, value in corpus.items() if key != "corpus_sha256"})
        != manifest["corpus_sha256"]
    ):
        raise ValueError("Frozen corpus changed")
    inputs = json.loads((directory / "frozen_inputs.json").read_text(encoding="utf-8"))
    if digest(inputs) != manifest["patient_inputs_sha256"]:
        raise ValueError("Frozen patient/reference input changed")
    payloads = json.loads((directory / "payloads.json").read_text(encoding="utf-8"))
    units = {unit["source_id"]: unit for unit in corpus["units"]}
    rows = []
    for case_id, policies in payloads.items():
        expected = {
            source["source_id"]
            for source in inputs[case_id]["reference_payload"]["guideline_evidence"]
        }
        for policy, item in policies.items():
            supplied = [
                source["source_id"]
                for source in item.get("payload", {}).get("guideline_evidence", [])
            ]
            mapped = set(supplied)
            for source_id in supplied:
                mapped.update(units[source_id].get("covers_source_ids", []))
            exact_hit, mapped_hit = expected.intersection(supplied), expected.intersection(mapped)
            rows.append(
                {
                    "case_id": case_id,
                    "cohort": "complex" if case_id.startswith("VAL-") else "engineering",
                    "policy": policy,
                    "status": item["status"],
                    "expected_source_ids": sorted(expected),
                    "supplied_source_ids": supplied,
                    "exact_hits": sorted(exact_hit),
                    "mapped_hits": sorted(mapped_hit),
                    "exact_reference_coverage": len(exact_hit) / len(expected)
                    if expected
                    else None,
                    "mapped_reference_coverage": len(mapped_hit) / len(expected)
                    if expected
                    else None,
                    "complete_exact_coverage": bool(expected) and exact_hit == expected,
                    "complete_mapped_coverage": bool(expected) and mapped_hit == expected,
                }
            )
    groups = defaultdict(list)
    for row in rows:
        groups[row["cohort"], row["policy"]].append(row)
        groups["all", row["policy"]].append(row)
    summary = []
    for (cohort, policy), group in sorted(groups.items()):
        summary.append(
            {
                "cohort": cohort,
                "policy": policy,
                "cases": len(group),
                "successful_payloads": sum(row["status"] == "completed" for row in group),
                "case_macro_exact_coverage": sum(
                    row["exact_reference_coverage"] or 0 for row in group
                )
                / len(group),
                "case_macro_mapped_coverage": sum(
                    row["mapped_reference_coverage"] or 0 for row in group
                )
                / len(group),
                "complete_exact_cases": sum(row["complete_exact_coverage"] for row in group),
                "complete_mapped_cases": sum(row["complete_mapped_coverage"] for row in group),
            }
        )
    report = {
        "retrieval_identity": manifest["identity"],
        "corpus_sha256": manifest["corpus_sha256"],
        "retrieval_freeze_sha256": sha256_bytes((directory / "retrieval_freeze.json").read_bytes()),
        "tool_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "summary": summary,
        "cases": rows,
        "interpretation": "Availability of engineering reference passages in the supplied Top-5 budget. Mapped coverage uses frozen covers_source_ids. Neither metric measures relevance precision, clinical correctness or downstream judgment. Reference evidence is full by construction.",
    }
    (directory / "retrieval_coverage.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    table = "".join(
        "<tr>"
        + "".join(
            "<td>" + escape(str(value)) + "</td>"
            for value in [
                row["cohort"],
                row["policy"],
                row["cases"],
                f"{row['case_macro_exact_coverage']:.1%}",
                f"{row['case_macro_mapped_coverage']:.1%}",
                row["complete_exact_cases"],
                row["complete_mapped_cases"],
            ]
        )
        + "</tr>"
        for row in summary
    )
    html = (
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>Prepared retrieval coverage</title><style>body{font:14px/1.6 Segoe UI,Arial;margin:36px;color:#243244}table{border-collapse:collapse}td,th{padding:12px;border-bottom:1px solid #dce3e9;text-align:left}</style><h1>Prepared retrieval coverage</h1><p>'
        + escape(report["interpretation"])
        + "</p><table><tr><th>Cohort</th><th>Policy</th><th>Cases</th><th>Exact case macro coverage</th><th>Mapped case macro coverage</th><th>Complete exact cases</th><th>Complete mapped cases</th></tr>"
        + table
        + '</table><p><a href="retrieval_coverage.json">Per-case sources and calculations</a></p></html>'
    )
    (directory / "coverage.html").write_text(html, encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    print(json.dumps(analyze(parser.parse_args().directory)["summary"], indent=2))
