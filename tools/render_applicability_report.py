"""Render a completed frozen comparison without changing its experiment records.

Run only after the writer has stopped. Standard-library-only presentation code is
kept outside the experiment package so it cannot change a running source identity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from html import escape
from pathlib import Path

PROTOCOLS = ("passage_selection", "applicability_first")
TITLES = {
    "passage_selection": "Outcome-first control",
    "applicability_first": "Applicability-first",
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def e(value):
    return escape(str(value), quote=True)


def condition_key(row):
    return tuple(
        row[field] for field in ("model", "case_id", "evidence_policy", "protocol", "repeat")
    )


def pair_key(row):
    return row["case_id"], row["model"], row["evidence_policy"], row["repeat"]


def stages(row):
    saved = row.get("stages")
    return saved if saved else {"recorded": {"attempts": row.get("attempts", [])}}


def errors(row):
    messages = [row.get("error")]
    for stage in stages(row).values():
        messages.append(stage.get("error"))
        messages.extend(attempt.get("error") for attempt in stage.get("attempts", []))
    return list(dict.fromkeys(message for message in messages if message))


def first_flags(row):
    return row.get("stages", {}).get("applicability", {}).get("ledger_consistency_flags", [])


def final_flags(row):
    return row.get("output_consistency_flags", [])


def ledger_checks(row):
    return (
        row.get("stages", {}).get("applicability", {}).get("answer", {}).get("passage_checks", [])
    )


def own_check_changes(row):
    earlier = {check["passage_id"]: check for check in ledger_checks(row)}
    changes = []
    for check in row.get("answer", {}).get("criterion_checks", []):
        previous = earlier.get(check.get("passage_id"))
        if previous is None:
            continue
        compared = ("finding", "licence_pathway", "fact_fields", "conclusion")
        changes.append(
            {
                "passage_id": check["passage_id"],
                "stage_one": {field: previous.get(field) for field in compared},
                "final": {field: check.get(field) for field in compared},
                "changed_fields": [
                    field for field in compared if previous.get(field) != check.get(field)
                ],
            }
        )
    return changes


def accepted_outcome(row):
    return row.get("answer", {}).get("assessment_outcome") if row["status"] == "completed" else None


def reference_agreement(row):
    reference = row.get("reference_outcome")
    return accepted_outcome(row) == reference if reference is not None else None


def read_completed_snapshot(directory, expected_results_sha256=None):
    """Read results exactly once and refuse partial or actively written inputs."""
    if (directory / ".run.lock").exists():
        raise ValueError("Experiment still has a run lock; render only after the writer stops")
    manifest_bytes = (directory / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    raw = (directory / "results.jsonl").read_bytes()
    result_hash = sha256(raw)
    if expected_results_sha256 is not None and result_hash != expected_results_sha256:
        raise ValueError("Raw results snapshot SHA-256 differs from the expected value")
    if not raw or not raw.endswith(b"\n"):
        raise ValueError("Completed JSONL must end with a newline; partial snapshots are refused")
    lines = raw.decode("utf-8").splitlines()
    if any(not line.strip() for line in lines):
        raise ValueError("Blank JSONL records are not permitted")
    rows = [json.loads(line) for line in lines]
    planned = [tuple(key) for key in manifest["planned_keys"]]
    if not planned or len(planned) != len(set(planned)):
        raise ValueError("Manifest planned keys are empty or duplicated")
    if any(len(key) != 5 or key[3] not in PROTOCOLS or type(key[4]) is not int for key in planned):
        raise ValueError("Unexpected manifest condition key or protocol")
    keys = [condition_key(row) for row in rows]
    if len(keys) != len(set(keys)) or set(keys) != set(planned):
        raise ValueError("Results must match every manifest planned key exactly once")
    pairs = defaultdict(dict)
    for row in rows:
        if row.get("experiment_identity") != manifest["identity"]:
            raise ValueError("Result identity differs from its manifest")
        if row["status"] not in {"completed", "failed"}:
            raise ValueError("Only terminal completed or failed records can be rendered")
        if row["status"] == "completed" and not accepted_outcome(row):
            raise ValueError("Completed condition is missing its accepted outcome")
        pairs[pair_key(row)][row["protocol"]] = row
    for pair in pairs.values():
        if set(pair) != set(PROTOCOLS):
            raise ValueError("Every case/model/policy/repeat must contain both protocols")
        baseline, proposed = (pair[protocol] for protocol in PROTOCOLS)
        if baseline.get("input_sha256") != proposed.get("input_sha256") or baseline.get(
            "input_snapshot"
        ) != proposed.get("input_snapshot"):
            raise ValueError(
                "Paired protocols received different patient or original-evidence inputs"
            )
    return (
        manifest,
        rows,
        pairs,
        {
            "results_sha256": result_hash,
            "manifest_sha256": sha256(manifest_bytes),
            "results_bytes": len(raw),
            "recorded_conditions": len(rows),
            "planned_conditions": len(planned),
            "complete_newline": True,
            "planned_keys_complete": True,
        },
    )


def repeatability(rows, manifest, snapshot_hash):
    grouped, planned = defaultdict(list), defaultdict(set)
    for key in manifest["planned_keys"]:
        planned[tuple(key[:4])].add(key[4])
    for row in rows:
        grouped[condition_key(row)[:4]].append(row)
    records = []
    for key, group in sorted(grouped.items()):
        outcomes = Counter(
            accepted_outcome(row) for row in group if accepted_outcome(row) is not None
        )
        same_inputs = len({sha256(canonical(row.get("input_snapshot"))) for row in group}) == 1
        complete = len(group) == len(planned[key]) and all(
            row["status"] == "completed" for row in group
        )
        eligible = complete and same_inputs
        records.append(
            {
                **dict(zip(("model", "case_id", "evidence_policy", "protocol"), key, strict=True)),
                "planned_repeats": sorted(planned[key]),
                "recorded_calls": len(group),
                "accepted_calls": sum(row["status"] == "completed" for row in group),
                "failed_calls": sum(row["status"] == "failed" for row in group),
                "outcome_counts": dict(sorted(outcomes.items())),
                "distinct_accepted_outcomes": len(outcomes),
                "identical_patient_and_evidence_inputs": same_inputs,
                "stability_analysis_eligible": eligible,
                "stable_outcome": len(outcomes) == 1 if eligible else None,
            }
        )
    return {
        "results_sha256": snapshot_hash,
        "unit": "Repeated calls for the same frozen case and condition; repeats are not independent patients.",
        "groups": records,
    }


def flags_html(title, flags, *, ledger=False):
    content = (
        "<ul>" + "".join(f"<li>{e(flag)}</li>" for flag in flags) + "</ul>"
        if flags
        else "<p>No structural contradiction flagged. Evidence support remains unverified.</p>"
    )
    return f'<section class="flags {"alert" if flags else "quiet"}" data-flag-stage="{"ledger" if ledger else "final"}"><h4>{e(title)} · {len(flags)}</h4>{content}</section>'


def table(headers, rows):
    return (
        '<div class="table-scroll"><table><thead><tr>'
        + "".join(f"<th>{e(header)}</th>" for header in headers)
        + "</tr></thead><tbody>"
        + "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
        + "</tbody></table></div>"
    )


def source_id_for(check, row):
    if check.get("source_id"):
        return check["source_id"]
    locations = list(row.get("criterion_locations", []))
    for stage in stages(row).values():
        locations.extend(stage.get("criterion_locations", []))
    return next(
        (
            location.get("source_id", "")
            for location in locations
            if location.get("passage_id") == check.get("passage_id")
        ),
        "Unresolved in recorded locations",
    )


def source_anchor(pair_id, source_id):
    return "source-" + pair_id + "-" + sha256(str(source_id).encode("utf-8"))[:16]


def check_html(check, row, pair_id, *, ledger=False):
    source_id = source_id_for(check, row)
    fact_fields = ", ".join(check.get("fact_fields", [])) or "No referenced facts"
    body = f'<div class="check-heading"><a href="#{source_anchor(pair_id, source_id)}">{e(source_id)}</a><span>{e(check.get("module", ""))}</span></div>'
    body += f'<p class="check-meta">{e(check.get("licence_pathway", ""))} · {e(check.get("finding", ""))}</p>'
    if ledger:
        body += f"<p>Applicability: <strong>{e(check.get('applicability', ''))}</strong> · Statement: {e(check.get('statement_type', ''))}</p>"
        requirements = check.get("prerequisites", [])
        body += (
            table(
                ["Reported prerequisite", "Status", "Verified field references"],
                [
                    [
                        e(item.get("requirement", "")),
                        e(item.get("status", "")),
                        e(", ".join(item.get("fact_fields", []))),
                    ]
                    for item in requirements
                ],
            )
            if requirements
            else '<p class="muted">No prerequisites recorded by the model.</p>'
        )
        body += f"<p>Numeric application: {e(check.get('numeric_application', ''))}</p>"
    body += f'<p>{e(check.get("conclusion", ""))}</p><p class="fact-refs">{e(fact_fields)}</p>'
    return '<div class="check">' + body + "</div>"


def protocol_html(row, pair_id, attempts_link):
    answer = row.get("answer", {})
    agreement = reference_agreement(row)
    label = (
        "Matches engineering reference"
        if agreement
        else "Differs from engineering reference"
        if agreement is not None
        else "Reference unavailable"
    )
    if row["status"] != "completed":
        label = "No accepted judgment; execution failure is reported separately."
    outcome = accepted_outcome(row) or "No accepted model outcome"
    content = f'<article class="protocol" data-protocol="{e(row["protocol"])}"><header><h3>{e(TITLES[row["protocol"]])}</h3><span class="status">{e(row["status"])}</span></header><p class="outcome">{e(outcome)}</p><p class="reference">{e(label)}</p>'
    content += f"<p>{e(answer.get('explanation', 'No accepted explanation.'))}</p>"
    if errors(row):
        content += (
            '<details class="errors"><summary>Recorded failures, including repaired attempts</summary><ul>'
            + "".join(f"<li>{e(message)}</li>" for message in errors(row))
            + "</ul></details>"
        )
    if row["protocol"] == "applicability_first":
        if row.get("stages", {}).get("applicability", {}).get("status") == "failed":
            content += '<section class="flags alert"><h4>Stage 1 ledger not accepted</h4><p>Inspect the failed raw attempts; no accepted applicability findings are available.</p></section>'
        else:
            content += flags_html("Stage 1 ledger contradictions", first_flags(row), ledger=True)
        checks = ledger_checks(row)
        content += f'<details class="ledger"><summary>Stage 1 · All {len(checks)} recorded applicability items</summary><p class="muted">Fallible preceding model proposal; these are not the final model checks.</p>'
        content += (
            "".join(check_html(check, row, pair_id, ledger=True) for check in checks) + "</details>"
        )
    if row["status"] == "completed":
        content += flags_html("Final-check contradictions", final_flags(row))
    else:
        content += '<section class="flags alert"><h4>No accepted final checks</h4><p>Absence of a contradiction flag on a failed condition is not a successful check.</p></section>'
    content += (
        '<details class="final-checks" open><summary>Independent final model checks</summary>'
        + "".join(check_html(check, row, pair_id) for check in answer.get("criterion_checks", []))
        + "</details>"
    )
    changes = own_check_changes(row)
    if changes:
        content += (
            "<details><summary>Stage 1 → final check changes</summary>"
            + table(
                ["Passage", "Stage 1 finding / scope", "Final finding / scope", "Changed fields"],
                [
                    [
                        e(change["passage_id"]),
                        e(
                            str(change["stage_one"]["finding"])
                            + " / "
                            + str(change["stage_one"]["licence_pathway"])
                        ),
                        e(
                            str(change["final"]["finding"])
                            + " / "
                            + str(change["final"]["licence_pathway"])
                        ),
                        e(", ".join(change["changed_fields"]) or "None"),
                    ]
                    for change in changes
                ],
            )
            + "</details>"
        )
    calls = sum(len(stage.get("attempts", [])) for stage in stages(row).values())
    content += f'<footer><span>{calls} recorded stage attempts</span><a href="{e(attempts_link)}" download>Download all raw stage attempts</a></footer></article>'
    return content


def evidence_html(payload, pair_id):
    facts = payload.get("verified_patient_facts", {})
    content = '<details class="shared"><summary>Shared original evidence and verified patient facts</summary><h3>Verified patient facts</h3>'
    content += table(
        ["Field", "Stored value", "Patient quotations"],
        [
            [
                f"<code>{e(name)}</code>",
                f"<code>{e(json.dumps(fact.get('value'), ensure_ascii=False))}</code>",
                "<br>".join(e(quote) for quote in fact.get("patient_quotes", [])),
            ]
            for name, fact in facts.items()
        ],
    )
    content += (
        "<details><summary>Original nurse note</summary><pre>"
        + e(payload.get("nurse_note", "No note recorded."))
        + "</pre></details><h3>Supplied original guideline passages</h3>"
    )
    for source in payload.get("guideline_evidence", []):
        content += f'<section class="original" id="{source_anchor(pair_id, source["source_id"])}"><h4>{e(source["source_id"])}</h4><p>Section {e(source.get("section", "Unknown"))} · PDF page {e(source.get("pdf_page", "Unknown"))} · Printed page {e(source.get("printed_page", "Unknown"))}</p><pre>{e(source.get("source_text", ""))}</pre></section>'
    return content + "</details>"


STYLE = """html{scroll-behavior:smooth}*{box-sizing:border-box}body{margin:0;background:#f4f6f8;color:#243244;font:14px/1.55 'Segoe UI',Arial,sans-serif}main{max-width:1520px;margin:auto;padding:28px 36px}a{color:#165581;text-decoration:none}a:hover{text-decoration:underline}.top{display:flex;justify-content:space-between;gap:20px;align-items:center;border-bottom:1px solid #d6dfe6;padding-bottom:18px}.brand{font-weight:650;letter-spacing:.02em;color:#203b50}.kicker{font-size:11px;text-transform:uppercase;letter-spacing:.13em;color:#587084}h1{font-size:30px;font-weight:600;letter-spacing:-.035em;margin:26px 0 6px}h2{font-size:19px;margin:0}h3{font-size:15px;margin:0}h4{font-size:13px;margin:0 0 7px}.muted,.reference,.fact-refs{color:#617184;font-size:12px}.notice{border-left:3px solid #9bafbf;padding:8px 14px;background:#edf2f6}.metrics{display:flex;flex-wrap:wrap;gap:22px;padding:18px 0;border-bottom:1px solid #d6dfe6}.metric strong{font-size:24px;font-weight:600;display:block}.metric span{font-size:12px;color:#617184}.filters{display:flex;flex-wrap:wrap;gap:12px;background:#fff;border:1px solid #d6dfe6;padding:14px 18px;margin:24px 0 12px}.filters label{font-size:11px;font-weight:600;color:#56697b;display:flex;flex-direction:column;gap:5px}.filters select{min-width:125px;max-width:250px;border:1px solid #cad5df;border-radius:3px;padding:7px;color:#243244;background:#fff}button{background:#fff;color:#254b67;border:1px solid #cad5df;border-radius:3px;padding:7px 14px;align-self:flex-end;cursor:pointer}.comparison{border:1px solid #d6dfe6;background:#fff;margin:20px 0 30px;scroll-margin-top:15px}.pair-heading{padding:17px 22px;border-bottom:1px solid #d6dfe6;background:#f9fbfc;display:flex;justify-content:space-between;gap:15px;flex-wrap:wrap}.pair-meta{color:#617184;font-size:12px;margin:5px 0 0}.columns{display:grid;grid-template-columns:1fr 1fr}.protocol{min-width:0;padding:22px}.protocol+.protocol{border-left:1px solid #d6dfe6}.protocol header{display:flex;justify-content:space-between;gap:10px}.status{font-size:11px;letter-spacing:.03em;color:#617184}.outcome{font-size:19px;line-height:1.35;font-weight:600;overflow-wrap:anywhere;margin:14px 0 4px}.protocol footer{font-size:12px;padding-top:15px;margin-top:18px;border-top:1px solid #e1e7ec;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}.flags{padding:12px 14px;margin:18px 0;border-left:3px solid #acb9c6;background:#f4f7f9}.flags p,.flags ul{margin:0;font-size:12px}.flags.alert{border-color:#b97722;background:#fff8e9;color:#6b4b20}.flags li{overflow-wrap:anywhere}.flags ul{padding-left:17px}.check{border-top:1px solid #e1e7ec;padding:13px 0}.check-heading{display:flex;gap:10px;justify-content:space-between;font-size:12px;overflow-wrap:anywhere}.check-meta{font-size:12px;color:#526d83}.check p{margin:7px 0}.shared{border-top:1px solid #d6dfe6;padding:18px 22px}.shared h3{margin:16px 0 8px}.original{padding:15px;background:#f6f8fa;border:1px solid #e1e7ec;margin:12px 0;scroll-margin-top:15px}.original p{margin:0 0 8px;font-size:12px;color:#617184}details{margin:12px 0}summary{cursor:pointer;color:#294f6c;font-size:13px;font-weight:600}pre{font:12px/1.6 Consolas,'Courier New',monospace;white-space:pre-wrap;overflow-wrap:anywhere;margin:10px 0 0}code{overflow-wrap:anywhere;font-size:11px}.table-scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:12px}th,td{padding:8px 10px;border-bottom:1px solid #e1e7ec;vertical-align:top;text-align:left;overflow-wrap:anywhere}th{font-weight:600;color:#52677b;background:#f8fafb}.provenance{margin:30px 0;padding-top:16px;border-top:1px solid #cad5df;font-size:12px}.links{display:flex;flex-wrap:wrap;gap:18px}.hidden{display:none!important}@media(max-width:850px){main{padding:20px 14px}.columns{grid-template-columns:1fr}.protocol+.protocol{border-left:0;border-top:1px solid #d6dfe6}.top{align-items:flex-start}.filters select{min-width:110px}}@media print{.filters,button{display:none}.comparison{break-inside:avoid}main{padding:0}.protocol{padding:14px}.columns{grid-template-columns:1fr 1fr}a{color:inherit}}"""

SCRIPT = """(()=>{const controls=[...document.querySelectorAll('[data-filter]')];const pairs=[...document.querySelectorAll('.comparison')];function apply(){let visible=0;for(const pair of pairs){const show=controls.every(control=>{if(control.value==='all')return true;const key=control.dataset.filter;if(key==='status'||key==='error')return JSON.parse(pair.dataset[key]).includes(control.value);return pair.dataset[key]===control.value});pair.classList.toggle('hidden',!show);if(show)visible++}document.getElementById('visible-count').textContent=visible+' of '+pairs.length+' paired comparisons shown'}controls.forEach(control=>control.addEventListener('change',apply));document.getElementById('reset').addEventListener('click',()=>{controls.forEach(control=>control.value='all');apply()});document.querySelectorAll('a[href^="#source-"]').forEach(link=>link.addEventListener('click',()=>{const target=document.getElementById(link.getAttribute('href').slice(1));if(target){const details=target.closest('details');if(details)details.open=true}}));apply()})();"""


def render_html(manifest, rows, pairs, raw_links, snapshot):
    filters = {
        "case": ("Case", sorted({row["case_id"] for row in rows})),
        "model": ("Model", sorted({row["model"] for row in rows})),
        "policy": ("Evidence policy", sorted({row["evidence_policy"] for row in rows})),
        "repeat": ("Repeat", [str(value) for value in sorted({row["repeat"] for row in rows})]),
        "status": ("Recorded status", sorted({row["status"] for row in rows})),
        "error": (
            "Error type",
            sorted(
                {message.split(":", 1)[0] for row in rows for message in errors(row)} | {"none"}
            ),
        ),
    }
    controls = "".join(
        f'<label>{e(title)}<select data-filter="{key}"><option value="all">All</option>'
        + "".join(f'<option value="{e(value)}">{e(value)}</option>' for value in values)
        + "</select></label>"
        for key, (title, values) in filters.items()
    )
    conditions = len(rows)
    accepted = sum(row["status"] == "completed" for row in rows)
    first_flagged = sum(bool(first_flags(row)) for row in rows)
    final_flagged = sum(bool(final_flags(row)) for row in rows)
    metrics = [
        (conditions, "Recorded conditions"),
        (len({row["case_id"] for row in rows}), "Distinct synthetic cases"),
        (accepted, "Accepted outputs"),
        (conditions - accepted, "Failed conditions"),
        (first_flagged, "Conditions with ledger flags"),
        (final_flagged, "Conditions with final flags"),
    ]
    content = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Applicability comparison | Occupational Fitness</title><style>'
        + STYLE
        + '</style></head><body><main><nav class="top"><span class="brand">Occupational Fitness Platform</span><span class="links"><a href="index.html">Original run audit</a><a href="results.jsonl" download>Raw results</a><a href="presentation_manifest.json">Presentation manifest</a></span></nav><p class="kicker">Engineering assessment · Frozen comparison</p><h1>Evidence applicability review</h1><p>Compare the outcome-first control with the applicability-first proposal for the same case, evidence and repeat.</p><p class="notice">Known-error development cases with provisional engineering references. Accepted format, valid source addresses and consistent fields do not establish clinical correctness. Original experiment records remain unchanged.</p><div class="metrics">'
        + "".join(
            f'<div class="metric"><strong>{value}</strong><span>{e(label)}</span></div>'
            for value, label in metrics
        )
        + '</div><div class="filters">'
        + controls
        + '<button id="reset" type="button">Reset filters</button></div><p class="muted" id="visible-count"></p><p class="muted">Filtering keeps both protocol results together. Repeats are repeated model calls, not independent patients.</p>'
    )
    for key, pair in sorted(pairs.items()):
        case, model, policy, repeat = key
        pair_id = sha256(canonical(key))[:20]
        attributes = {
            "case": case,
            "model": model,
            "policy": policy,
            "repeat": str(repeat),
            "status": json.dumps(sorted({row["status"] for row in pair.values()})),
            "error": json.dumps(
                sorted(
                    {message.split(":", 1)[0] for row in pair.values() for message in errors(row)}
                    | ({"none"} if any(not errors(row) for row in pair.values()) else set())
                )
            ),
        }
        attrs = " ".join(f'data-{name}="{e(value)}"' for name, value in attributes.items())
        reference = pair[PROTOCOLS[0]].get("reference_outcome", "Unavailable")
        content += f'<section class="comparison" id="pair-{pair_id}" {attrs}><header class="pair-heading"><div><h2>{e(case)}</h2><p class="pair-meta">{e(model)} · {e(policy)} · Repeat {repeat}</p></div><div class="pair-meta">Engineering reference: <strong>{e(reference)}</strong></div></header><div class="columns">'
        content += "".join(
            protocol_html(pair[protocol], pair_id, raw_links[condition_key(pair[protocol])])
            for protocol in PROTOCOLS
        )
        content += (
            "</div>"
            + evidence_html(pair[PROTOCOLS[0]].get("input_snapshot", {}), pair_id)
            + "</section>"
        )
    content += (
        '<section class="provenance"><h3>Snapshot and reproducibility</h3><p class="links"><a href="repeatability.json">Repeated-call stability</a><a href="case_findings.json">Per-case findings</a><a href="manifest.json">Experiment manifest</a><a href="presentation_manifest.json">Renderer and input fingerprints</a></p><p>All first attempts, failures and repair attempts are retained in the raw stage downloads. A repaired output remains distinguishable from a first-pass success.</p><p>Experiment identity: <code>'
        + e(manifest["identity"])
        + "</code><br>Results SHA-256: <code>"
        + e(snapshot["results_sha256"])
        + "</code></p></section></main><script>"
        + SCRIPT
        + "</script></body></html>"
    )
    return content


def write_artifact(path, content):
    encoded = content.encode("utf-8") if isinstance(content, str) else content
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(encoded)
    temporary.replace(path)
    return sha256(encoded)


def json_artifact(path, value):
    return write_artifact(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def render_report(directory, expected_results_sha256=None):
    directory = Path(directory).resolve()
    manifest, rows, pairs, snapshot = read_completed_snapshot(directory, expected_results_sha256)
    artifacts, links = {}, {}
    for row in rows:
        key = condition_key(row)
        relative = "review_attempts/" + sha256(canonical(key))[:24] + ".json"
        links[key] = relative
        raw = {
            "condition": dict(
                zip(("model", "case_id", "evidence_policy", "protocol", "repeat"), key, strict=True)
            ),
            "results_sha256": snapshot["results_sha256"],
            "status": row["status"],
            "stages": stages(row),
            "support_review": row.get("support_review", "pending_independent_review"),
        }
        artifacts[relative] = json_artifact(directory / relative, raw)
    stability = repeatability(rows, manifest, snapshot["results_sha256"])
    artifacts["repeatability.json"] = json_artifact(directory / "repeatability.json", stability)
    findings = []
    for key, pair in sorted(pairs.items()):
        findings.append(
            {
                **dict(zip(("case_id", "model", "evidence_policy", "repeat"), key, strict=True)),
                "outcome_changed": accepted_outcome(pair[PROTOCOLS[0]])
                != accepted_outcome(pair[PROTOCOLS[1]])
                if all(row["status"] == "completed" for row in pair.values())
                else None,
                "protocols": {
                    protocol: {
                        "status": row["status"],
                        "outcome": accepted_outcome(row),
                        "reference_outcome": row.get("reference_outcome"),
                        "engineering_reference_agreement": reference_agreement(row),
                        "ledger_flags": first_flags(row),
                        "final_flags": final_flags(row),
                        "stage_one_to_final_check_changes": own_check_changes(row),
                        "errors": errors(row),
                        "raw_attempts": links[condition_key(row)],
                    }
                    for protocol, row in pair.items()
                },
            }
        )
    artifacts["case_findings.json"] = json_artifact(
        directory / "case_findings.json",
        {
            "results_sha256": snapshot["results_sha256"],
            "interpretation": "Provisional engineering references; support and clinical review remain separate.",
            "pairs": findings,
        },
    )
    html = render_html(manifest, rows, pairs, links, snapshot)
    artifacts["review.html"] = write_artifact(directory / "review.html", html)
    presentation = {
        "renderer": "tools/render_applicability_report.py",
        "renderer_sha256": sha256(Path(__file__).read_bytes()),
        "experiment_identity": manifest["identity"],
        **snapshot,
        "original_records_modified": False,
        "artifacts_sha256": dict(sorted(artifacts.items())),
    }
    json_artifact(directory / "presentation_manifest.json", presentation)
    return presentation


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment_dir", type=Path)
    parser.add_argument("--expected-results-sha256")
    args = parser.parse_args(argv)
    result = render_report(args.experiment_dir, args.expected_results_sha256)
    print(
        json.dumps(
            {
                key: result[key]
                for key in ("recorded_conditions", "results_sha256", "renderer_sha256")
            }
        )
    )


if __name__ == "__main__":
    main()
