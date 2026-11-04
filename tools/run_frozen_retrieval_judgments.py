"""Judge frozen retrieval evidence with identical model request contracts.

Consumes the common six-method preparation and optionally appends the seventh
arm using the same patients and whole-original Top-5 allocation. It never
re-extracts facts, reruns retrieval or sends reference answers to a model.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from collections import Counter
from html import escape
from pathlib import Path
from time import perf_counter

from occupational_fitness_rag.evaluation.evidence_selection import select_documented_evidence
from occupational_fitness_rag.evaluation.graph_completion import require_complete_chat
from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.evaluation.judgment_comparison import (
    judgment_request,
    local_post,
    validate_answer,
)
from occupational_fitness_rag.evaluation.model_judgment import ExperimentalJudgment
from occupational_fitness_rag.evaluation.passage_comparison import (
    local_get,
    patient_identity,
    read_records,
)
from occupational_fitness_rag.provenance import digest, write_json
from tools.prepare_retrieval_judgments import common_evidence

KEYS = ("case_id", "method", "model", "repeat")


def key(condition):
    return tuple(condition[name] for name in KEYS)


def verify_files(directory):
    pins = json.loads((directory / "artifacts.json").read_bytes())
    for name, expected in pins.items():
        if file_hash(directory / name) != expected:
            raise ValueError("Frozen artifact changed: " + str(directory / name))
    return pins


def runtime(config):
    version = local_get(config["endpoint"], "/api/version")
    inventory = {
        m["name"]: m["digest"] for m in local_get(config["endpoint"], "/api/tags")["models"]
    }
    if version.get("version") != config["expected_runtime_version"] or any(
        inventory.get(name) != pin for name, pin in config["expected_model_digests"].items()
    ):
        raise ValueError("Frozen judge runtime or model weights differ")
    return {"version": version, "models": config["expected_model_digests"]}


def accept_completion(raw, payload, method, config):
    try:
        require_complete_chat(json.dumps(raw).encode())
    except ValueError as exc:
        raise ValueError("Incomplete or empty judgment completion") from exc
    count = raw.get("prompt_eval_count")
    if (
        type(count) is not int
        or count < 0
        or count > config["context_length"] - config["output_tokens"]
    ):
        raise ValueError(
            "Prompt consumption exceeds or lacks the reserved generation context budget"
        )
    answer = ExperimentalJudgment.model_validate_json(raw["message"]["content"])
    validate_answer(answer, payload, method)
    return answer


def prepare_inputs(preparation, additional=None):
    pins = verify_files(preparation)
    manifest = json.loads((preparation / "manifest.json").read_bytes())
    if (
        digest(
            {
                k: v
                for k, v in manifest.items()
                if k not in {"identity", "judgment_calls", "production_change"}
            }
        )
        != manifest["identity"]
    ):
        raise ValueError("Prepared judgment manifest self-identity differs")
    summary = json.loads((preparation / "summary.json").read_bytes())
    if not summary["ready_for_final_judgment_run"]:
        raise ValueError(
            "Common retrieval preparation is not ready: preserve unresolved graph or input failures"
        )
    config = manifest["config"]
    payloads, requests, conditions = [
        json.loads((preparation / name).read_bytes())
        for name in ("payloads.json", "requests.json", "conditions.json")
    ]
    if (
        digest(payloads) != manifest["payloads_sha256"]
        or digest(requests) != manifest["requests_sha256"]
        or digest(conditions) != manifest["conditions_sha256"]
    ):
        raise ValueError("Prepared payload/request/condition content differs")
    if any(digest(body) != identity for identity, body in requests.items()):
        raise ValueError("A prepared request identity differs from its exact body")
    evidence = {
        (r["case_id"], r["method"]): r["payload"] for r in payloads if r["status"] == "ready"
    }
    patients = {
        case: payload for (case, method), payload in evidence.items() if method == "no_evidence"
    }
    extra_pins = None
    if additional is not None:
        extra_pins = verify_files(additional)
        extra_manifest = json.loads((additional / "manifest.json").read_bytes())
        extra_summary = json.loads((additional / "summary.json").read_bytes())
        if (
            digest(
                {
                    k: v
                    for k, v in extra_manifest.items()
                    if k not in {"identity", "production_change"}
                }
            )
            != extra_manifest["identity"]
        ):
            raise ValueError("Additional retrieval manifest self-identity differs")
        if extra_summary["failures"] or extra_summary["recorded"] != extra_summary["planned"]:
            raise ValueError("Additional method retrieval has unresolved failures")
        root = Path(__file__).resolve().parents[1]
        prep = root / config["query_preparation"]
        original_patients = json.loads((prep / "patients.json").read_bytes())
        original_manifest = json.loads((prep / "manifest.json").read_bytes())
        if extra_manifest["imported"]["preparation"]["identity"] != original_manifest["identity"]:
            raise ValueError("Additional method used a different fact/query preparation")
        units = {
            u["source_id"]: u
            for u in json.loads((additional / "corpus.json").read_bytes())["units"]
        }
        rankings = read_records(additional / "results.jsonl")
        original_queries = json.loads((prep / "queries.json").read_bytes())
        qmap = {q["query_id"]: q for q in original_queries}
        if (
            len(rankings) != len(qmap)
            or {r["query_id"] for r in rankings} != set(qmap)
            or file_hash(additional / "results.jsonl") != extra_summary["results_sha256"]
        ):
            raise ValueError("Additional arm query inventory differs")
        for row in rankings:
            q = qmap[row["query_id"]]
            if (
                row["method"] != "planned_hybrid"
                or row["experiment_identity"] != extra_manifest["identity"]
                or row["case_id"] != q["case_id"]
                or row["module"] != q["module"]
                or row["status"] != "completed"
                or len(set(row["source_ids"])) != len(row["source_ids"])
                or any(
                    s not in units or units[s]["module"] != q["module"] for s in row["source_ids"]
                )
            ):
                raise ValueError("Additional arm source identity or module differs")
        for case_id, patient in patients.items():
            if {
                k: v for k, v in original_patients[case_id].items() if k != "guideline_evidence"
            } != {k: v for k, v in patient.items() if k != "guideline_evidence"}:
                raise ValueError("New arm changed frozen patient facts")
            selected = [r for r in rankings if r["case_id"] == case_id]
            allocation = select_documented_evidence(patient, selected, 5)
            ids = allocation["source_ids"]
            payload, budget = common_evidence(patient, units, ids, config["evidence_max_bytes"])
            if not payload["guideline_evidence"]:
                raise ValueError(
                    "No original evidence survives the common budget for the additional arm"
                )
            identity = digest({"case_id": case_id, "method": "planned_hybrid", "payload": payload})
            evidence[(case_id, "planned_hybrid")] = payload
            payloads.append(
                {
                    "case_id": case_id,
                    "method": "planned_hybrid",
                    "status": "ready",
                    "payload": payload,
                    "payload_identity": identity,
                    "allocation": allocation,
                    "budget": budget,
                }
            )
            for model in config["models"]:
                body = judgment_request(config, model, payload)
                if len(json.dumps(body, ensure_ascii=False).encode()) > config["request_max_bytes"]:
                    raise ValueError("Additional arm exceeds the unchanged request byte budget")
                rid = digest(body)
                requests[rid] = body
                conditions.extend(
                    {
                        "case_id": case_id,
                        "method": "planned_hybrid",
                        "model": model,
                        "repeat": repeat,
                        "payload_identity": identity,
                        "request_identity": rid,
                    }
                    for repeat in range(config["repeats"])
                )
    if len({key(c) for c in conditions}) != len(conditions):
        raise ValueError(
            "Repeated condition; actual repeated calls still require distinct repeat keys"
        )
    for condition in conditions:
        body = requests[condition["request_identity"]]
        if (
            json.loads(body["messages"][1]["content"])
            != evidence[(condition["case_id"], condition["method"])]
        ):
            raise ValueError("Condition references a different model-visible patient/evidence body")
    return config, manifest, pins, extra_pins, payloads, requests, conditions


def scoring(rows, labels):
    outcomes = [
        "meets_unconditional_standard",
        "may_meet_conditional_standard",
        "temporarily_unfit",
        "does_not_meet_standard",
        "insufficient_information",
    ]
    result = []
    groups = list(dict.fromkeys((r["model"], r["method"]) for r in rows))
    for model, method in groups:
        selected = [r for r in rows if r["model"] == model and r["method"] == method]
        accepted = [r for r in selected if r["status"] == "completed"]
        matrix = {actual: {pred: 0 for pred in outcomes} for actual in outcomes}
        for row in accepted:
            matrix[labels[row["case_id"]]["reference_outcome"]][
                row["answer"]["assessment_outcome"]
            ] += 1
        correct = sum(matrix[label][label] for label in outcomes)
        insufficient = [
            r for r in accepted if r["answer"]["assessment_outcome"] == "insufficient_information"
        ]
        f1s = []
        for label in outcomes:
            tp = matrix[label][label]
            fp = sum(matrix[a][label] for a in outcomes if a != label)
            fn = sum(matrix[label][p] for p in outcomes if p != label)
            if tp + fp + fn:
                f1s.append(2 * tp / (2 * tp + fp + fn))
        result.append(
            {
                "model": model,
                "method": method,
                "recorded": len(selected),
                "accepted": len(accepted),
                "failed": len(selected) - len(accepted),
                "correct": correct,
                "insufficient_predictions": len(insufficient),
                "insufficient_predictions_matching_reference": sum(
                    labels[r["case_id"]]["reference_outcome"] == "insufficient_information"
                    for r in insufficient
                ),
                "insufficient_predictions_against_other_reference": sum(
                    labels[r["case_id"]]["reference_outcome"] != "insufficient_information"
                    for r in insufficient
                ),
                "engineering_reference_agreement_all_recorded": correct / len(selected)
                if selected
                else None,
                "engineering_reference_agreement_accepted": correct / len(accepted)
                if accepted
                else None,
                "macro_f1_over_observed_classes_accepted": sum(f1s) / len(f1s) if f1s else None,
                "confusion_matrix_accepted": matrix,
            }
        )
    return result


def paired_judgments(rows, labels):
    index = {key(r): r for r in rows}
    changes = []
    for row in rows:
        if row["method"] == "hybrid":
            continue
        base = index.get((row["case_id"], "hybrid", row["model"], row["repeat"]))
        if base is None:
            continue
        if base["status"] != "completed" or row["status"] != "completed":
            change = "run_or_contract_failure"
        else:
            expected = labels[row["case_id"]]["reference_outcome"]
            before, after = [r["answer"]["assessment_outcome"] for r in (base, row)]
            change = (
                "unchanged"
                if before == after
                else "wrong_to_correct"
                if before != expected and after == expected
                else "correct_to_wrong"
                if before == expected and after != expected
                else "wrong_to_different_wrong"
            )
        changes.append(
            {
                **{k: row[k] for k in KEYS},
                "baseline": "hybrid",
                "change": change,
                "baseline_outcome": base.get("answer", {}).get("assessment_outcome"),
                "candidate_outcome": row.get("answer", {}).get("assessment_outcome"),
                "reference_outcome": labels[row["case_id"]]["reference_outcome"],
            }
        )
    return changes


def render(output, rows, payloads, summary, labels):
    pmap = {(r["case_id"], r["method"]): r["payload"] for r in payloads}
    table = "".join(
        f"<tr><td>{escape(r['model'])}</td><td>{r['method']}</td><td>{r['accepted']}/{r['recorded']}</td>"
        f"<td>{r['engineering_reference_agreement_all_recorded']:.2%}</td><td>{r['correct']}</td></tr>"
        for r in summary["metrics"]
    )
    cards = []
    for row in rows:
        payload = pmap[(row["case_id"], row["method"])]
        cards.append(
            f'<article data-case="{escape(row["case_id"])}" data-model="{escape(row["model"])}" data-repeat="{row["repeat"] + 1}" data-method="{row["method"]}" data-status="{row["status"]}">'
            f"<h2>{escape(row['case_id'])} · {row['method']} · {escape(row['model'])} · repeat {row['repeat'] + 1}</h2>"
            f"<p>Engineering reference: {escape(labels[row['case_id']]['reference_outcome'])}</p>"
            f"<p>{escape(row.get('error', row['status']))}</p><pre>{escape(json.dumps(row.get('answer', {}), indent=2))}</pre>"
            f"<details><summary>Exact patient facts and original evidence supplied to the judge</summary><pre>{escape(json.dumps(payload, ensure_ascii=False, indent=2))}</pre></details></article>"
        )
    filters = "".join(
        f'<label>{name.title()} <select id="{name}"><option value="">All</option>'
        + "".join(
            f"<option>{escape(str(value))}</option>"
            for value in sorted(
                {
                    r["repeat"] + 1
                    if name == "repeat"
                    else r["case_id" if name == "case" else name]
                    for r in rows
                }
            )
        )
        + "</select></label>"
        for name in ("case", "model", "repeat", "method", "status")
    )
    html = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Frozen retrieval judgments | Occupational Fitness Platform</title>
<style>body{font:14px/1.6 Arial,sans-serif;background:#f4f6f8;color:#233849;margin:0}main{max-width:1200px;margin:36px auto;padding:0 24px}section,article{background:white;border:1px solid #dce4eb;border-radius:8px;padding:24px;margin:18px 0}th,td{text-align:left;padding:12px;border-bottom:1px solid #dce4eb}table{width:100%;border-collapse:collapse}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f6f8fa;padding:14px}label{display:inline-block;margin:10px}select{padding:8px}summary{cursor:pointer}h1{font-size:30px}h2{font-size:17px}[hidden]{display:none}</style><main><section><p>OCCUPATIONAL FITNESS PLATFORM · EXPERIMENTAL JUDGMENT</p><h1>Same patients and judge, different retrieved evidence</h1>"""
    html += f"<p>{summary['recorded']}/{summary['planned']} conditions recorded; {summary['accepted']} accepted; {summary['failed']} failed. Scope: {escape(summary['scope'])}.</p>"
    html += "<p>Engineering reference agreement, not clinical accuracy. Source-ID validity and evidence-supported explanation are separate. No automatic entailment or clinician approval is claimed. All failures remain in the all-recorded agreement denominator.</p>"
    html += (
        "<table><tr><th>Model</th><th>Method</th><th>Accepted</th><th>Agreement / all recorded</th><th>Correct</th></tr>"
        + table
        + '</table><p><a href="summary.json">Full metrics and confusion matrices</a> · <a href="results.jsonl">All raw responses</a> · <a href="paired_changes.json">Case-level judgment changes</a> · <a href="plan.json">Frozen execution plan</a></p></section><section>'
        + filters
        + '</section><div class="cards">'
        + "".join(cards)
    )
    html += """</div></main><style>.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.cards article{margin:0;min-width:0}@media(max-width:850px){.cards{grid-template-columns:1fr}}</style><script>const keys=['case','model','repeat','method','status'];function filter(){document.querySelectorAll('article').forEach(a=>a.hidden=keys.some(k=>document.getElementById(k).value&&a.dataset[k]!==document.getElementById(k).value))}keys.forEach(k=>document.getElementById(k).addEventListener('change',filter));['case','model','repeat'].forEach(k=>{const s=document.getElementById(k);if(s.options.length>1)s.selectedIndex=1});filter();</script></html>"""
    (output / "index.html").write_text(html, encoding="utf-8")


def select_conditions(payloads, conditions, pilot=False):
    """Select frozen cases independently of optional evidence-control arms.

    A single-method revision can legitimately contain no ``no_evidence`` arm.
    Every ready payload still has to describe the same patient within a case.
    An empty selected inventory is an input failure, never a completed run.
    """
    patients = {}
    for row in payloads:
        if row["status"] != "ready":
            continue
        case_id, payload = row["case_id"], row["payload"]
        if case_id in patients and patient_identity(patients[case_id]) != patient_identity(payload):
            raise ValueError("Ready evidence arms disagree on frozen patient facts")
        patients[case_id] = payload
    if not patients or not conditions:
        raise ValueError("A judgment run requires nonempty ready cases and conditions")
    if {c["case_id"] for c in conditions} != set(patients):
        raise ValueError("Ready case and judgment condition inventories differ")
    case_ids = sorted(patients)
    if pilot:
        case_ids = []
        for module in ("hypertension", "blackout", "diabetes", "hearing", "vision"):
            candidates = [
                case for case in sorted(patients) if patients[case]["modules"] == [module]
            ]
            if not candidates:
                raise ValueError("Pilot requires a single-module case for each disease")
            case_ids.append(candidates[0])
    chosen = [c for c in conditions if c["case_id"] in case_ids]
    if not chosen:
        raise ValueError("The selected judgment condition inventory is empty")
    return chosen


def run(preparation, output, additional=None, pilot=False, resume=False, max_new_calls=None):
    if max_new_calls is not None and (type(max_new_calls) is not int or max_new_calls <= 0):
        raise ValueError("The optional per-invocation call budget must be positive")
    root = Path(__file__).resolve().parents[1]
    preparation, output = Path(preparation).resolve(), Path(output).resolve()
    additional = Path(additional).resolve() if additional else None
    config, prep_manifest, pins, extra_pins, payloads, requests, conditions = prepare_inputs(
        preparation, additional
    )
    chosen = select_conditions(payloads, conditions, pilot)
    chosen.sort(
        key=lambda c: (config["models"].index(c["model"]), c["repeat"], c["case_id"], c["method"])
    )
    source_paths = [
        Path(__file__),
        root / "tools/prepare_retrieval_judgments.py",
        root / "src/occupational_fitness_rag/evaluation/judgment_comparison.py",
        root / "src/occupational_fitness_rag/evaluation/model_judgment.py",
        root / "src/occupational_fitness_rag/evaluation/graph_completion.py",
    ]
    env = runtime(config)
    data = {
        "preparation_identity": prep_manifest["identity"],
        "preparation_artifacts": pins,
        "additional_artifacts": extra_pins,
        "runtime": env,
        "conditions": chosen,
        "requests_sha256": digest(requests),
        "sources": {str(p.relative_to(root)): file_hash(p) for p in source_paths},
        "scope": "five-disease pilot, three independent calls per condition"
        if pilot
        else "complete fixed patient comparison",
    }
    plan = {**data, "identity": digest(data), "production_change": False}
    if not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Judgment output must remain in a separate experiment directory")
    output.mkdir(parents=True, exist_ok=True)
    lock = output / ".run.lock"
    with lock.open("x", encoding="ascii") as stream:
        stream.write(str(os.getpid()))
    try:
        if (output / "plan.json").exists():
            if not resume or json.loads((output / "plan.json").read_bytes()) != plan:
                raise ValueError("Resume requires an identical judgment execution plan")
            if (output / "artifacts.json").exists():
                verify_files(output)
        elif any(p.name != ".run.lock" for p in output.iterdir()):
            raise ValueError("Preserve unowned experiment files")
        else:
            write_json(output / "plan.json", plan)
            write_json(output / "payloads.json", payloads)
            write_json(output / "requests.json", requests)
        rows = read_records(output / "results.jsonl")
        planned = {key(c): c for c in chosen}
        done = {key(r) for r in rows}
        if (
            len(done) != len(rows)
            or not done <= set(planned)
            or any(
                r["experiment_identity"] != plan["identity"]
                or r["request_identity"] != planned[key(r)]["request_identity"]
                for r in rows
            )
        ):
            raise ValueError("Saved judgment conditions differ or are repeated")
        for row in rows:
            if row["status"] == "completed":
                payload = json.loads(requests[row["request_identity"]]["messages"][1]["content"])
                answer = accept_completion(row["raw_response"], payload, row["method"], config)
                if row["answer"] != answer.model_dump(mode="json"):
                    raise ValueError(
                        "Saved judgment answer differs from its retained raw completion"
                    )
        new_calls = 0
        for condition in chosen:
            if key(condition) in done:
                continue
            if max_new_calls is not None and new_calls >= max_new_calls:
                break
            runtime(config)
            body = requests[condition["request_identity"]]
            row = {**condition, "experiment_identity": plan["identity"]}
            started = perf_counter()
            try:
                raw = local_post(config["endpoint"], "/api/chat", body, 180)
                row["raw_response"] = raw
                payload = json.loads(body["messages"][1]["content"])
                answer = accept_completion(raw, payload, condition["method"], config)
                row.update(status="completed", answer=answer.model_dump(mode="json"))
            except Exception as exc:
                row.update(status="failed", error=f"{type(exc).__name__}: {exc}")
            row["seconds"] = perf_counter() - started
            with (output / "results.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
            rows.append(row)
            done.add(key(condition))
            new_calls += 1
            print(
                f"Judgments {len(rows)}/{len(chosen)} {condition['model']} {condition['case_id']} {condition['method']} {row['status']}",
                flush=True,
            )
        if (
            runtime(config) != env
            or {str(p.relative_to(root)): file_hash(p) for p in source_paths} != data["sources"]
        ):
            raise ValueError("Frozen judgment source or runtime changed")
        if verify_files(preparation) != pins or (
            additional is not None and verify_files(additional) != extra_pins
        ):
            raise ValueError("Input artifacts changed during judging")
        # Open labels only after immutable request bodies and observed attempts
        # have been saved. They never enter the transport body or recovery path.
        labels = json.loads((preparation / "scoring_labels.json").read_bytes())
        metrics = scoring(rows, labels)
        changes = paired_judgments(rows, labels)
        summary = {
            "identity": plan["identity"],
            "scope": data["scope"],
            "planned": len(chosen),
            "recorded": len(rows),
            "accepted": sum(r["status"] == "completed" for r in rows),
            "failed": sum(r["status"] != "completed" for r in rows),
            "complete": done == set(planned),
            "actual_judgment_calls": len(rows),
            "metrics": metrics,
            "paired_change_counts": dict(Counter(r["change"] for r in changes)),
            "cohorts": {
                name: scoring([r for r in rows if labels[r["case_id"]]["cohort"] == name], labels)
                for name in ("engineering", "complex_validation")
            },
            "clinical_review": "pending",
            "production_change": False,
            "citation_validity_does_not_prove_explanation_support": True,
        }
        write_json(output / "summary.json", summary)
        write_json(output / "paired_changes.json", changes)
        write_json(
            output / "support_review_queue.json",
            [
                {
                    **{key: row[key] for key in KEYS},
                    "status": "pending_independent_review",
                    "priority": "contract_failure"
                    if row["status"] != "completed"
                    else "engineering_reference_disagreement"
                    if row["answer"]["assessment_outcome"]
                    != labels[row["case_id"]]["reference_outcome"]
                    else "support_unreviewed",
                    "cited_source_ids": row.get("answer", {}).get("source_ids", []),
                    "cited_fact_fields": row.get("answer", {}).get("fact_fields", []),
                    "note": "Identifier validity is not clinical explanation support; review original evidence and applicability.",
                }
                for row in rows
            ],
        )
        with (output / "summary.csv").open("w", encoding="utf-8", newline="") as stream:
            fields = [k for k in metrics[0] if k != "confusion_matrix_accepted"] if metrics else []
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(metrics)
        render(output, rows, payloads, summary, labels)
        write_json(
            output / "artifacts.json",
            {
                p.name: file_hash(p)
                for p in output.iterdir()
                if p.is_file() and p.name not in {"artifacts.json", ".run.lock"}
            },
        )
        return summary
    finally:
        lock.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preparation", required=True)
    parser.add_argument("--additional")
    parser.add_argument("--output", required=True)
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-new-calls", type=int)
    args = parser.parse_args()
    result = run(
        args.preparation, args.output, args.additional, args.pilot, args.resume, args.max_new_calls
    )
    print(
        json.dumps(
            {k: result[k] for k in ("planned", "recorded", "accepted", "failed", "complete")},
            indent=2,
        )
    )
