"""Locate explicit addendum literals without restoring or clinically interpreting facts."""

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from html import escape
from pathlib import Path

LINE = re.compile(r"(?m)^[ \t]*([a-z][a-z0-9_.]+)[ \t]*=[ \t]*(.+?)[ \t]*$")


def fingerprint(raw):
    return hashlib.sha256(raw).hexdigest()


def identical_value(left, right):
    return type(left) is type(right) and left == right


def literals(text, field):
    """Read JSON literals only; no natural-language inference or value coercion."""
    results = []
    for match in LINE.finditer(text):
        if match[1] != field:
            continue
        try:
            value = json.loads(
                match[2], parse_constant=lambda _: (_ for _ in ()).throw(ValueError())
            )
        except (ValueError, json.JSONDecodeError):
            continue
        if value is None or type(value) not in {str, bool, int, float}:
            continue
        if type(value) is float and not math.isfinite(value):
            continue
        results.append(
            {
                "value": value,
                "char_start": match.start(),
                "char_end": match.end(),
                "quote": match.group(),
                "line": text.count("\n", 0, match.start()) + 1,
            }
        )
    return results


def inspect_field(text, changed):
    spans = literals(text, changed["field"])
    target = changed["before"]["value"]
    if not spans:
        status = "no_explicit_literal"
    elif any(not identical_value(item["value"], spans[0]["value"]) for item in spans):
        status = "conflicting_explicit_literals"
    elif not identical_value(spans[0]["value"], target):
        status = "literal_differs_from_prior_extraction"
    else:
        status = "explicit_literal_revalidation_candidate"
    prior = changed["before"].get("evidence", [])
    return {
        "field": changed["field"],
        "prior_extracted_value": target,
        "frozen_value": changed["frozen"].get("value"),
        "frozen_status": changed["frozen"].get("status"),
        "status": status,
        "literal_spans": spans,
        "prior_quoted_spans_verified": bool(prior)
        and all(text[item["start"] : item["end"]] == item["quote"] for item in prior),
        "review_status": "pending_explicit_experimental_refreeze",
    }


def build_audit(root, baseline, output):
    root, baseline, output = Path(root).resolve(), Path(baseline).resolve(), Path(output).resolve()
    if output == baseline or output.is_relative_to(baseline) or not output.is_relative_to(root):
        raise ValueError("Audit output must be a separate project directory")
    upstream_raw = (baseline / "upstream_audit.json").read_bytes()
    labels_raw = (baseline / "labels.json").read_bytes()
    labels = {item["case_id"]: item for item in json.loads(labels_raw)}
    cases, pins = [], {}
    for row in json.loads(upstream_raw)["cases"]:
        if not row["changed_fields"]:
            continue
        source = (root / labels[row["case_id"]]["input"]).resolve()
        if not source.is_relative_to(root):
            raise ValueError("Source path escapes the project")
        raw = source.read_bytes()
        # Existing traceable intake uses decoded file bytes and preserves CRLF.
        text = raw.decode("utf-8-sig")
        relative = source.relative_to(root).as_posix()
        pins[relative] = fingerprint(raw)
        cases.append(
            {
                "case_id": row["case_id"],
                "source": relative,
                "source_raw_sha256": fingerprint(raw),
                "decoded_text_sha256": fingerprint(text.encode("utf-8")),
                "upstream_outcome_discrepancy": row["reference"] != row["frozen_outcome"],
                "fields": [inspect_field(text, changed) for changed in row["changed_fields"]],
                "interpretation_note": (
                    "Recent-event status and weeks-since-event are distinct documented fields; their "
                    "clinical relationship requires guideline and specialist review."
                    if row["case_id"] == "SYN-EXT-014"
                    else "Literal recovery is not clinical adjudication."
                ),
            }
        )
    fields = [field for case in cases for field in case["fields"]]
    discrepancy_fields = [
        field for case in cases if case["upstream_outcome_discrepancy"] for field in case["fields"]
    ]
    report = {
        "upstream_audit_sha256": fingerprint(upstream_raw),
        "label_file_sha256": fingerprint(labels_raw),
        "source_files_sha256": pins,
        "tool_sha256": fingerprint(Path(__file__).read_bytes()),
        "case_count": len(cases),
        "field_occurrences": len(fields),
        "outcome_discrepancy_case_count": sum(
            case["upstream_outcome_discrepancy"] for case in cases
        ),
        "outcome_discrepancy_field_occurrences": len(discrepancy_fields),
        "outcome_discrepancy_status_counts": dict(
            Counter(field["status"] for field in discrepancy_fields)
        ),
        "status_counts": dict(Counter(field["status"] for field in fields)),
        "prior_span_verified_count": sum(field["prior_quoted_spans_verified"] for field in fields),
        "offset_representation": "Python Unicode code points after UTF-8 BOM removal; original CRLF/LF preserved",
        "facts_restored": 0,
        "clinical_review": "pending",
        "production_change": False,
        "interpretation": "Source-literal revalidation candidates only; no facts, labels, rules or frozen inputs are changed.",
        "cases": cases,
    }
    output.mkdir(parents=True, exist_ok=True)
    path = output / "fact_revalidation_audit.json"
    if path.exists():
        previous = json.loads(path.read_text(encoding="utf-8"))
        for key in ("upstream_audit_sha256", "label_file_sha256", "source_files_sha256"):
            if previous[key] != report[key]:
                raise ValueError("Pinned audit inputs changed; preserve existing output")
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rows = "".join(
        "<tr>"
        + "".join(
            "<td>" + escape(str(value)) + "</td>"
            for value in (
                case["case_id"],
                field["field"],
                json.dumps(field["frozen_value"]),
                json.dumps(field["prior_extracted_value"]),
                field["status"],
                "; ".join(
                    f"Line {span['line']}: {span['quote']}" for span in field["literal_spans"]
                ),
                field["prior_quoted_spans_verified"],
            )
        )
        + "</tr>"
        for case in cases
        for field in case["fields"]
    )
    html = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Fact literal revalidation audit</title><style>body{font:14px/1.6 Segoe UI,Arial;margin:36px;color:#243244}table{border-collapse:collapse;width:100%}td,th{padding:12px;border-bottom:1px solid #dce3e9;text-align:left}p{max-width:1050px}</style><h1>Fact literal revalidation audit</h1>'
    html += f"<p>{len(cases)} cases · {len(fields)} field occurrences · 0 facts restored</p>"
    html += "<p>Explicit source values were withheld during upstream review. This audit verifies literal addresses and types; it does not resolve clinical meaning or promote values into production facts. Existing experimental inputs remain unchanged. Independent revalidation and a separately pinned fact version are required before a sensitivity replay.</p><p>Source offsets use decoded Unicode text with original newlines preserved. Eight cases change the aggregate rule outcome; other field changes may not change that outcome.</p><table><tr>"
    html += "".join(
        f"<th>{name}</th>"
        for name in [
            "Case",
            "Field",
            "Frozen value",
            "Prior extraction",
            "Audit status",
            "Original literal",
            "Prior span verified",
        ]
    )
    html += (
        "</tr>"
        + rows
        + '</table><p><a href="fact_revalidation_audit.json">Source hashes and exact spans</a></p></html>'
    )
    (output / "index.html").write_text(html, encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default="outputs/experiments/judgment_comparison_v5")
    parser.add_argument("--output", default="outputs/experiments/fact_revalidation_audit")
    args = parser.parse_args()
    result = build_audit(Path(__file__).resolve().parents[1], args.baseline, args.output)
    print(
        json.dumps(
            {
                key: result[key]
                for key in [
                    "case_count",
                    "field_occurrences",
                    "status_counts",
                    "prior_span_verified_count",
                    "facts_restored",
                ]
            }
        )
    )
