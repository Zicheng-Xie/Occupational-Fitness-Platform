"""Run real raw-note assessments; distinguish fact decisions from retrieval activity."""

import argparse
import json
from html import escape
from pathlib import Path

from occupational_fitness_rag.pipeline.workflow import OccupationalFitnessWorkflow
from occupational_fitness_rag.provenance import digest, write_json


def run_batch(workflow, paths, output, expectations=None):
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    workflow.config.llm.narrative_enabled = False
    for path in paths:
        bundle = workflow.run_file(path, output / "runs")

        def read(name):
            return json.loads((bundle / name).read_text(encoding="utf-8"))

        result, evidence = read("rule_result.json"), read("evidence_pack.json")
        case, review = read("structured_case.json"), read("llm_semantic_review.json")
        actual = {x["rule_id"] for x in result["triggered_rules"]}
        expected = (expectations or {}).get(path.stem, {})
        discovery = evidence["retrieval"].get("symptom_discovery", [])
        discovered = {c["source_id"] for d in discovery for c in d["citations"]}
        rule_sources = {
            c["source_id"] for item in evidence["evidence_items"] for c in item["citations"]
        }
        verification = workflow.verify_run(bundle)
        row = {
            "case_id": path.stem,
            "input_sha256": case["text_sha256"],
            "report": (bundle / "draft_report.html").relative_to(output).as_posix(),
            "outcome": result["assessment_outcome"],
            "expected_outcome_matches": result["assessment_outcome"]
            == expected.get("overall_outcome")
            if "overall_outcome" in expected
            else None,
            "modules_requested": case["modules_requested"],
            "module_outcomes": {m["module"]: m["assessment_outcome"] for m in result["modules"]},
            "bundle_verification": verification,
            "route": result["route"],
            "triggered_rules": sorted(actual),
            "present_fields": [k for k, v in case["facts"].items() if v["status"] == "present"],
            "review_status": review["status"],
            "ranking_calls": evidence["retrieval"]["ranking_calls"],
            "ranked_candidates": sum(
                len(x["ranked_candidates"]) for x in evidence["evidence_items"]
            ),
            "discovery_modules": [d["module"] for d in discovery],
            "discovery_sources": sorted(discovered),
            "expected": expected,
            "expected_rules_found": sorted(set(expected.get("required_rules", [])) & actual),
            "missing_expected_rules": sorted(set(expected.get("required_rules", [])) - actual),
            "forbidden_rules_found": sorted(set(expected.get("forbidden_rules", [])) & actual),
            "expected_sources_found": sorted(set(expected.get("source_ids", [])) & discovered),
            "expected_sources_found_in_rule_citations": sorted(
                set(expected.get("source_ids", [])) & rule_sources
            ),
        }
        rows.append(row)
        report = {
            "config": workflow.config.model_dump(mode="json"),
            "ruleset_sha256": workflow.book.sha256,
            "index_sha256": workflow.catalogue.index_sha256,
            "expectations_sha256": digest(expectations or {}),
            "independent_clinical_gold": False,
            "rows": rows,
        }
        write_json(output / "results.json", report)
        render_batch(rows, output)
        print(json.dumps(row), flush=True)
    return rows


def render_batch(rows, output):
    cells = []
    for r in rows:
        check = (
            f"{len(r['expected_rules_found'])}/{len(r['expected'].get('required_rules', []))}"
            if r["expected"].get("required_rules")
            else "Control: " + ("failed" if r["forbidden_rules_found"] else "passed")
            if r["expected"]
            else "Unlabelled"
        )
        cells.append(
            f'<tr><td><a href="{escape(r["report"])}">{escape(r["case_id"])}</a></td>'
            f"<td>{escape(r['outcome'])}</td><td>{len(r['present_fields'])}</td>"
            f"<td>{len(r['triggered_rules'])}</td><td>{r['ranking_calls']}</td>"
            f"<td>{len(r['discovery_sources'])}</td><td>{escape(check)}</td>"
            f"<td>{escape(r['review_status'])}</td><td>{r.get('expected_outcome_matches')}</td></tr>"
        )
    details = "".join(
        f"<details><summary>{escape(r['case_id'])} — audit details</summary>"
        f"<pre>{escape(json.dumps(r, indent=2))}</pre></details>"
        for r in rows
    )
    html = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Note validation | Occupational Fitness Platform</title>
<style>body{font:16px/1.6 system-ui;background:#f4f7fa;color:#193344;margin:0}
main{max-width:1260px;margin:auto;padding:32px}section,details{background:white;border:1px solid #d8e1e8;padding:20px;margin:18px 0;border-radius:8px}
table{border-collapse:collapse;width:100%;font-size:13px}td,th{padding:12px;text-align:left;border-bottom:1px solid #e1e7ec}section{overflow:auto}a{color:#146882}pre{white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer}</style>
<main><p>OCCUPATIONAL FITNESS PLATFORM / VALIDATION</p><h1>Complex note assessment</h1>
<p>All inputs are synthetic. Rule triggers require sufficient verified facts. Missing information does not mean retrieval failed.</p>
<p>Every case uses all five modules. Undocumented modules may keep the overall result insufficient even when another module has triggered rules.</p>
<p>Expected triggers are predefined engineering checks, not clinical diagnostic accuracy. Controls check specified forbidden rules.</p>
<p><a href="results.json">Open machine-readable results</a></p><section><table><tr><th>Case</th><th>Overall outcome</th><th>Accepted facts</th><th>Triggered rules</th><th>Rule ranking calls</th><th>Symptom discovery sources</th><th>Expected triggers</th><th>Source review</th><th>Expected outcome matched</th></tr>"""
    html += "".join(cells) + "</table></section>" + details + "</main></html>"
    (output / "index.html").write_text(html, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/workflow.yaml")
    parser.add_argument("--input-dir", default="data/cases/complex_nurse_notes")
    parser.add_argument("--ids", nargs="+")
    parser.add_argument("--output", required=True)
    parser.add_argument("--expectations")
    args = parser.parse_args()
    paths = (
        [Path(args.input_dir) / (name + ".txt") for name in args.ids]
        if args.ids
        else sorted(Path(args.input_dir).glob("*.txt"))
    )
    expectations = (
        json.loads(Path(args.expectations).read_text(encoding="utf-8"))
        if args.expectations
        else None
    )
    run_batch(OccupationalFitnessWorkflow(args.config), paths, Path(args.output), expectations)


if __name__ == "__main__":
    main()
