"""Audit a completed retrieval-v2 judgment revision against original hybrid RRF.

This is read-only postprocessing. Dispatch version v3 does not mean that the
later guarded retrieval-v3/v4 methods have been judged. Raw output validation,
engineering reference agreement and independent clinical support stay separate.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import Counter
from copy import deepcopy
from html import escape
from pathlib import Path

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.provenance import digest, write_json
from tools import run_frozen_retrieval_judgments as actor
from tools.audit_completed_judgments import function_ast, verify_completed
from tools.report_anchored_hybrid import write_csv
from tools.report_judgment_evidence_changes import compare_evidence, render

REVISION = "planned_hybrid_v2_containment"
ACTOR_SOURCES = frozenset(
    {
        "tools/run_frozen_retrieval_judgments.py",
        "tools/prepare_retrieval_judgments.py",
        "src/occupational_fitness_rag/evaluation/judgment_comparison.py",
        "src/occupational_fitness_rag/evaluation/model_judgment.py",
        "src/occupational_fitness_rag/evaluation/graph_completion.py",
    }
)


def failure_category(row):
    if row["status"] == "completed":
        return None
    if re.search(r"source_ids|cit(?:e|ation)|supplied source", row.get("error", ""), re.I):
        return "citation_contract_failure"
    return "other_run_or_contract_failure"


def validate_evidence(payload, units):
    sources = payload["guideline_evidence"]
    if len(sources) > 5 or len({s["source_id"] for s in sources}) != len(sources):
        raise ValueError("Evidence exceeds the fixed five-original budget or repeats a source")
    for source in sources:
        unit = units.get(source["source_id"])
        if (
            unit is None
            or unit["licence_context"] not in {"commercial", "shared"}
            or unit["module"] not in payload["modules"]
            or source["source_text"] != unit["evidence_text"]
            or any(source[k] != unit[k] for k in ("module", "section", "pdf_page", "printed_page"))
        ):
            raise ValueError(
                "Judgment evidence differs from a frozen in-scope original and locator"
            )


def pair_runs(baseline, candidate, first_requests, second_requests, labels):
    first = {(r["case_id"], r["model"], r["repeat"]): r for r in baseline}
    second = {(r["case_id"], r["model"], r["repeat"]): r for r in candidate}
    if (
        len(first) != len(baseline)
        or len(second) != len(candidate)
        or first.keys() != second.keys()
    ):
        raise ValueError("The paired case/model/repeat inventory is incomplete or repeated")
    pairs, payloads = [], {}
    for key in sorted(first):
        before, after = first[key], second[key]
        if before["method"] != "hybrid" or after["method"] != REVISION:
            raise ValueError("Compare the original hybrid with retrieval-v2 only")
        bodies = [
            requests[row["request_identity"]]
            for requests, row in ((first_requests, before), (second_requests, after))
        ]
        inputs = [json.loads(body["messages"][1]["content"]) for body in bodies]
        comparison_bodies = deepcopy(bodies)
        for body, payload in zip(comparison_bodies, inputs, strict=True):
            source_schema = body.get("format", {}).get("properties", {}).get("source_ids")
            if source_schema is not None:
                source_enum = source_schema["items"]["enum"]
                if source_enum != [s["source_id"] for s in payload["guideline_evidence"]]:
                    raise ValueError("Output citation enumeration differs from supplied evidence")
                source_schema["items"]["enum"] = ["<supplied-original-source-ids>"]
        if (
            any(len(body["messages"]) != 2 for body in bodies)
            or bodies[0]["messages"][0] != bodies[1]["messages"][0]
            or {k: v for k, v in comparison_bodies[0].items() if k != "messages"}
            != {k: v for k, v in comparison_bodies[1].items() if k != "messages"}
            or bodies[0]["model"] != before["model"]
            or bodies[1]["model"] != after["model"]
        ):
            raise ValueError("Judge prompt, model, schema or inference options changed")
        evidence = compare_evidence(*inputs)
        for method, payload in zip(("hybrid", REVISION), inputs, strict=True):
            identity = (key[0], method)
            if identity in payloads and digest(payloads[identity]) != digest(payload):
                raise ValueError("Patient or evidence changed across independent calls")
            payloads[identity] = payload
        reference = labels[key[0]]["reference_outcome"]
        left = before.get("answer", {}).get("assessment_outcome")
        right = after.get("answer", {}).get("assessment_outcome")
        if before["status"] != "completed" or after["status"] != "completed":
            change = "run_or_contract_failure"
        else:
            change = (
                "unchanged"
                if left == right
                else "wrong_to_correct"
                if left != reference and right == reference
                else "correct_to_wrong"
                if left == reference and right != reference
                else "wrong_to_different_wrong"
            )
        pairs.append(
            {
                "case_id": key[0],
                "model": key[1],
                "repeat": key[2],
                "method": REVISION,
                "cohort": labels[key[0]]["cohort"],
                "reference_outcome": reference,
                "change": change,
                **evidence,
                "baseline_outcome": left,
                "candidate_outcome": right,
                "baseline_request_identity": before["request_identity"],
                "candidate_request_identity": after["request_identity"],
                "baseline_status": before["status"],
                "candidate_status": after["status"],
                "baseline_answer": before.get("answer"),
                "candidate_answer": after.get("answer"),
                "baseline_failure": before.get("error"),
                "candidate_failure": after.get("error"),
                "baseline_failure_category": failure_category(before),
                "candidate_failure_category": failure_category(after),
                "candidate_insufficient_against_other_engineering_reference": after["status"]
                == "completed"
                and right == "insufficient_information"
                and right != reference,
                "candidate_insufficient_matching_engineering_reference": after["status"]
                == "completed"
                and right == "insufficient_information"
                and right == reference,
                "unaccepted_candidate_content": after.get("raw_response", {})
                .get("message", {})
                .get("content")
                if after["status"] != "completed"
                else None,
                "independent_support_review": "pending",
            }
        )
    return pairs, payloads


def _changes(pairs):
    return {
        "pairs": len(pairs),
        "cases": len({r["case_id"] for r in pairs}),
        "changes": dict(Counter(r["change"] for r in pairs)),
        "baseline_failures": dict(
            Counter(r["baseline_failure_category"] for r in pairs if r["baseline_failure_category"])
        ),
        "candidate_failures": dict(
            Counter(
                r["candidate_failure_category"] for r in pairs if r["candidate_failure_category"]
            )
        ),
    }


def build(root, parent, revision, parent_preparation, revision_preparation, retrieval, output):
    root = Path(root).resolve()
    parent, revision, parent_preparation, revision_preparation, retrieval, output = [
        (root / Path(p)).resolve()
        for p in (parent, revision, parent_preparation, revision_preparation, retrieval, output)
    ]
    if output.exists() or not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Use a fresh independent audit directory")
    for directory in (parent_preparation, revision_preparation, retrieval):
        actor.verify_files(directory)
    prep = [
        json.loads((d / "manifest.json").read_bytes())
        for d in (parent_preparation, revision_preparation)
    ]
    labels_path = parent_preparation / "scoring_labels.json"
    labels = json.loads(labels_path.read_bytes())
    if (
        prep[0]["config"] != prep[1]["config"]
        or digest(labels) != prep[0]["labels_sha256"]
        or digest(labels) != prep[1]["labels_sha256"]
        or json.loads((revision_preparation / "scoring_labels.json").read_bytes()) != labels
        or prep[1]["method"] != REVISION
        or prep[1]["retrieval_identity"]
        != json.loads((retrieval / "manifest.json").read_bytes())["identity"]
        or prep[1]["retrieval_artifacts_sha256"] != file_hash(retrieval / "artifacts.json")
    ):
        raise ValueError("Preparation labels, judge settings or retrieval-v2 identity differ")
    plans = [json.loads((d / "plan.json").read_bytes()) for d in (parent, revision)]
    current_sources = {name.replace("\\", "/"): pin for name, pin in plans[1]["sources"].items()}
    if set(current_sources) != ACTOR_SOURCES or any(
        file_hash(root / name) != pin for name, pin in current_sources.items()
    ):
        raise ValueError("Current actor sources differ from the completed revision pins")
    snapshots = json.loads((parent / "source_files.json").read_bytes())
    for name, record in snapshots.items():
        if (
            file_hash(parent / record["file"]) != record["sha256"]
            or plans[0]["sources"][name] != record["sha256"]
        ):
            raise ValueError("Parent archived actor source differs from its original plan")
    archived = next(
        parent / record["file"]
        for name, record in snapshots.items()
        if name.replace("\\", "/") == "tools/run_frozen_retrieval_judgments.py"
    )
    contract_functions = ("key", "accept_completion", "scoring", "paired_judgments")
    if any(
        function_ast(archived, name)
        != function_ast(root / "tools/run_frozen_retrieval_judgments.py", name)
        for name in contract_functions
    ):
        raise ValueError("The original output-validation or scoring contract changed")
    verified = [
        verify_completed(directory, labels, prep[0]["config"]) for directory in (parent, revision)
    ]
    for index, (plan, rows, requests, _) in enumerate(verified):
        if (
            plan["preparation_identity"] != prep[index]["identity"]
            or plan["preparation_artifacts"]["scoring_labels.json"] != file_hash(labels_path)
            or plan["runtime"] != plans[0]["runtime"]
            or (index == 1 and len(rows) != 198)
        ):
            raise ValueError(
                "Completed run differs from the common preparation/runtime/198-call protocol"
            )
        for row in rows:
            if row["status"] == "failed" and "raw_response" in row:
                payload = json.loads(requests[row["request_identity"]]["messages"][1]["content"])
                try:
                    actor.accept_completion(
                        row["raw_response"], payload, row["method"], prep[0]["config"]
                    )
                except Exception:
                    pass
                else:
                    raise ValueError(
                        "A retained failed raw completion now passes the frozen contract"
                    )
    baseline = [row for row in verified[0][1] if row["method"] == "hybrid"]
    candidates = verified[1][1]
    if len(baseline) != 198 or {r["method"] for r in candidates} != {REVISION}:
        raise ValueError("Require all 198 original-hybrid and retrieval-v2 conditions")
    pairs, payloads = pair_runs(baseline, candidates, verified[0][2], verified[1][2], labels)
    corpus = json.loads((retrieval / "corpus.json").read_bytes())
    units = {unit["source_id"]: unit for unit in corpus["units"]}
    for payload in payloads.values():
        validate_evidence(payload, units)
    all_rows = [*baseline, *candidates]
    metrics = actor.scoring(all_rows, labels)
    summary = {
        "retrieval_revision": "v2_containment",
        "execution_revision_directory": revision.name,
        "newer_guarded_v3_v4_and_external_routes_not_judged_here": True,
        "pairs": len(pairs),
        "cases": len(labels),
        "metrics": metrics,
        **_changes(pairs),
        "by_model": {
            model: _changes([r for r in pairs if r["model"] == model])
            for model in prep[0]["config"]["models"]
        },
        "by_cohort": {
            cohort: {
                **_changes([r for r in pairs if r["cohort"] == cohort]),
                "metrics": actor.scoring(
                    [r for r in all_rows if labels[r["case_id"]]["cohort"] == cohort], labels
                ),
            }
            for cohort in ("engineering", "complex_validation")
        },
        "by_model_and_cohort": {
            model: {
                cohort: _changes(
                    [r for r in pairs if r["model"] == model and r["cohort"] == cohort]
                )
                for cohort in ("engineering", "complex_validation")
            }
            for model in prep[0]["config"]["models"]
        },
        "original_judgment_calls_imported": len(verified[0][1]),
        "revision_judgment_calls_imported": len(candidates),
        "new_model_calls": 0,
        "clinical_review": "pending",
        "production_change": False,
        "interpretation": "Engineering reference agreement across 33 observed development cases; not clinical accuracy. Three independent calls are repeated conditions, not additional patients. Source identifier validity is distinct from explanation support. Evidence bundles and order differ; this does not isolate one passage's causal effect. The completed judgment revision uses retrieval-v2, not the later guarded retrieval revisions.",
    }
    data = {
        "parent_identity": plans[0]["identity"],
        "revision_identity": plans[1]["identity"],
        "input_artifacts_sha256": {
            str(d.relative_to(root)): file_hash(d / "artifacts.json")
            for d in (parent, revision, parent_preparation, revision_preparation, retrieval)
        },
        "actor_sources_verified_against_revision_plan": current_sources,
        "parent_contract_ast_unchanged": list(contract_functions),
        "reporter_sha256": file_hash(__file__),
        "completion_validator_sha256": file_hash(root / "tools/audit_completed_judgments.py"),
        "pair_renderer_sha256": file_hash(root / "tools/report_judgment_evidence_changes.py"),
        "labels_sha256": file_hash(labels_path),
        "new_model_calls": 0,
    }
    output.mkdir(parents=True)
    source_inventory = {}
    for name, pin in current_sources.items():
        target = output / "sources" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, target)
        if file_hash(target) != pin:
            raise ValueError("Archived current actor source changed during copying")
        source_inventory[name] = {
            "file": str(target.relative_to(output)).replace("\\", "/"),
            "sha256": pin,
        }
    write_json(output / "source_files.json", source_inventory)
    write_json(
        output / "manifest.json", {**data, "identity": digest(data), "production_change": False}
    )
    write_json(output / "summary.json", summary)
    write_json(output / "pairs.json", pairs)
    write_json(
        output / "payloads.json",
        [
            {"case_id": case, "method": method, "payload": payload}
            for (case, method), payload in payloads.items()
        ],
    )
    review = [
        {
            "case_id": r["case_id"],
            "model": r["model"],
            "repeat": r["repeat"],
            "change": r["change"],
            "priority": "contract_failure"
            if r["change"] == "run_or_contract_failure"
            else "engineering_reference_disagreement"
            if r["candidate_outcome"] != r["reference_outcome"]
            else "support_unreviewed",
            "candidate_source_ids": r["candidate_source_ids"],
            "independent_support_review": "pending",
        }
        for r in pairs
    ]
    write_json(output / "support_review_queue.json", review)
    write_json(
        output / "failures.json", [r for r in pairs if r["change"] == "run_or_contract_failure"]
    )
    write_csv(
        output / "summary.csv",
        [{k: v for k, v in row.items() if k != "confusion_matrix_accepted"} for row in metrics],
    )
    write_csv(
        output / "paired_changes.csv",
        [
            {
                k: r[k]
                for k in (
                    "case_id",
                    "model",
                    "repeat",
                    "cohort",
                    "change",
                    "reference_outcome",
                    "baseline_outcome",
                    "candidate_outcome",
                    "baseline_status",
                    "candidate_status",
                )
            }
            for r in pairs
        ],
    )
    guide = root / corpus["source_path"]
    if file_hash(guide) != corpus["document_sha256"]:
        raise ValueError("Guideline PDF changed")
    shutil.copyfile(guide, output / "evidence_guide.pdf")
    render(output, pairs, payloads)
    decorate(output, summary)
    shutil.copyfile(__file__, output / "reporter_source.py")
    write_json(
        output / "artifacts.json",
        {
            str(p.relative_to(output)).replace("\\", "/"): file_hash(p)
            for p in output.rglob("*")
            if p.is_file() and p.name != "artifacts.json"
        },
    )
    return summary


def decorate(output, summary):
    def table(metrics):
        header = "<table><tr><th>Judge</th><th>Method</th><th>Recorded</th><th>Accepted</th><th>Failed</th><th>Reference agreement, all recorded</th><th>Macro-F1, accepted observed classes</th><th>Insufficient vs other reference</th></tr>"
        for row in metrics:
            header += "<tr>" + "".join(
                "<td>" + escape(str(row[k])) + "</td>"
                for k in ("model", "method", "recorded", "accepted", "failed")
            )
            header += f"<td>{row['engineering_reference_agreement_all_recorded']:.2%}</td><td>{row['macro_f1_over_observed_classes_accepted']:.4f}</td><td>{row['insufficient_predictions_against_other_reference']}</td></tr>"
        return header + "</table>"

    detail = (
        "<section><h2>Completed retrieval-v2 judgment revision</h2><p>"
        + escape(summary["interpretation"])
        + "</p><p>198 paired conditions: 33 cases × 2 judges × 3 independent calls. Validation failures stay in the all-recorded agreement denominator. Macro-F1 is computed on accepted outputs and observed classes, with failures listed separately.</p>"
        + table(summary["metrics"])
    )
    for cohort, values in summary["by_cohort"].items():
        detail += (
            "<details><summary>Cohort: "
            + escape(cohort)
            + "</summary>"
            + table(values["metrics"])
            + "</details>"
        )
    detail += (
        "<h3>Paired judgment changes</h3><pre>"
        + escape(json.dumps(summary["by_model"], indent=2))
        + '</pre><p>“Insufficient vs other reference” denotes disagreement with the engineering label, not a clinical finding that more information was unnecessary. Citation-contract failures are separate from substantive explanation support; every pair remains pending independent support review.</p><p><a href="summary.json">Verified metrics and cohort changes</a> · <a href="summary.csv">Metrics CSV</a> · <a href="paired_changes.csv">Paired CSV</a> · <a href="failures.json">Citation and other contract failures</a> · <a href="support_review_queue.json">Independent support review queue</a> · <a href="source_files.json">Archived actor source hashes</a></p></section>'
    )
    page = output / "index.html"
    html = page.read_text(encoding="utf-8").replace("</header>", "</header>" + detail, 1)
    html = html.replace(
        "document.getElementById('method').value='planned_hybrid';",
        f"document.getElementById('method').value='{REVISION}';",
    )
    html = html.replace(
        "</style>",
        "table{border-collapse:collapse;width:100%;font-size:12px}td,th{padding:8px;border-bottom:1px solid #dce3ea;text-align:left}section{overflow-x:auto}</style>",
        1,
    )
    page.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", default="outputs/experiments/seven_method_judgment_full_v1")
    parser.add_argument(
        "--revision", default="outputs/experiments/anchored_hybrid_judgment_full_v3"
    )
    parser.add_argument(
        "--parent-preparation", default="outputs/experiments/retrieval_judgment_preparation_v2"
    )
    parser.add_argument(
        "--revision-preparation",
        default="outputs/experiments/anchored_hybrid_judgment_preparation_v2",
    )
    parser.add_argument("--retrieval", default="outputs/experiments/anchored_hybrid_v2")
    parser.add_argument(
        "--output", default="outputs/experiments/anchored_revision_judgment_audit_v1"
    )
    args = parser.parse_args()
    result = build(
        Path.cwd(),
        args.parent,
        args.revision,
        args.parent_preparation,
        args.revision_preparation,
        args.retrieval,
        args.output,
    )
    print(
        json.dumps(
            {k: result[k] for k in ("pairs", "cases", "metrics", "by_model", "new_model_calls")},
            indent=2,
        )
    )
