"""Freeze and compare judgment interventions without changing retrieved evidence."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
from collections import Counter
from html import escape
from pathlib import Path
from time import perf_counter

import yaml

from occupational_fitness_rag.evaluation.fitness_judgment import (
    PROTOCOLS,
    build_request,
    parse_completion,
)
from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.evaluation.judgment_comparison import local_post
from occupational_fitness_rag.evaluation.passage_comparison import read_records
from occupational_fitness_rag.provenance import digest, write_json
from tools.run_frozen_retrieval_judgments import prepare_inputs, runtime, scoring
from tools.run_serial_judgment_queue import process_identity, verify_artifacts

ROOT = Path(__file__).resolve().parents[1]
KEYS = ("case_id", "method", "model", "repeat", "protocol")


def key(row):
    return tuple(row[name] for name in KEYS)


def verify_checkpoint(output):
    """Permit verified append-only attempts after the last report checkpoint."""
    pins = json.loads((output / "artifacts.json").read_bytes())
    for name, expected in pins.items():
        path = (output / name).resolve()
        if not path.is_relative_to(output) or not path.is_file():
            raise ValueError("Checkpoint artifact escapes or is missing")
        if name == "results.jsonl" and file_hash(path) != expected:
            state = json.loads((output / "checkpoint_state.json").read_bytes())
            from hashlib import sha256

            with path.open("rb") as stream:
                prefix = stream.read(state["results_bytes"])
            if sha256(prefix).hexdigest() != expected:
                raise ValueError("Previously checkpointed attempts changed")
        elif file_hash(path) != expected:
            raise ValueError("Checkpoint artifact changed: " + name)


def preparation(config_path):
    config_path = Path(config_path).resolve()
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    parent = (ROOT / cfg["preparation"]).resolve()
    output = (ROOT / cfg["output"]).resolve()
    if not all(p.is_relative_to(ROOT / "outputs/experiments") for p in (parent, output)):
        raise ValueError("Use separate workspace experiment directories")
    if output == parent or output.is_relative_to(parent) or parent.is_relative_to(output):
        raise ValueError("Preserve the historical preparation and all its descendants")
    base_config, manifest, pins, _, payloads, old_requests, old_conditions = prepare_inputs(parent)
    for name, expected in manifest["sources"].items():
        if file_hash(ROOT / name) != expected:
            raise ValueError("Historical preparation source drift: " + name)
    if (
        len(set(cfg["case_ids"])) != len(cfg["case_ids"])
        or len(set(cfg["methods"])) != len(cfg["methods"])
        or len(set(cfg["protocols"])) != len(cfg["protocols"])
        or not set(cfg["protocols"]) <= set(PROTOCOLS)
        or type(cfg["repeats"]) is not int
        or cfg["repeats"] != base_config["repeats"]
        or "original" not in cfg["protocols"]
    ):
        raise ValueError("Retain unique conditions, the original control and frozen repeats")
    imported = {(r["case_id"], r["method"]): r for r in payloads if r["status"] == "ready"}
    selected = []
    requests, conditions = {}, []
    old_map = {
        (c["case_id"], c["method"], c["model"]): c["request_identity"] for c in old_conditions
    }
    for case in cfg["case_ids"]:
        common = None
        for method in cfg["methods"]:
            row = imported[(case, method)]
            payload = row["payload"]
            patient = {k: v for k, v in payload.items() if k != "guideline_evidence"}
            if common is not None and common != patient:
                raise ValueError("Evidence arms changed patient facts or nurse-note context")
            common = patient
            evidence_bytes = len(
                json.dumps(payload["guideline_evidence"], ensure_ascii=False).encode()
            )
            if (
                not 1 <= len(payload["guideline_evidence"]) <= 5
                or evidence_bytes > base_config["evidence_max_bytes"]
            ):
                raise ValueError("Whole-original Top-5 evidence budget differs")
            selected.append(row)
            for model in base_config["models"]:
                for protocol in cfg["protocols"]:
                    body = build_request(base_config, model, payload, protocol)
                    if (
                        protocol == "original"
                        and body != old_requests[old_map[(case, method, model)]]
                    ):
                        raise ValueError("Original control request is not byte-content identical")
                    if (
                        len(json.dumps(body, ensure_ascii=False).encode())
                        > base_config["request_max_bytes"]
                    ):
                        raise ValueError("Request exceeds the unchanged byte budget")
                    rid = digest(body)
                    requests[rid] = body
                    for repeat in range(cfg["repeats"]):
                        conditions.append(
                            {
                                "case_id": case,
                                "method": method,
                                "model": model,
                                "repeat": repeat,
                                "protocol": protocol,
                                "payload_identity": row["payload_identity"],
                                "request_identity": rid,
                            }
                        )
    sources = {
        str(p.relative_to(ROOT)): file_hash(p)
        for directory in (ROOT / "src/occupational_fitness_rag", ROOT / "tools")
        for p in sorted(directory.rglob("*.py"))
        if "__pycache__" not in p.parts
    }
    data = {
        "kind": "frozen_evidence_judgment_ablation",
        "config": cfg,
        "config_sha256": file_hash(config_path),
        "judge_config": base_config,
        "preparation_identity": manifest["identity"],
        "preparation_artifacts": pins,
        "sources": sources,
        "runtime": runtime(base_config),
        "payloads_sha256": digest(selected),
        "requests_sha256": digest(requests),
        "conditions": conditions,
        "evidence_changed_between_protocols": False,
        "prior_predictions_imported": False,
        "labels_visible_to_model": False,
        "reference_kind": "engineering_reference_pending_clinical_review",
    }
    return cfg, parent, output, selected, requests, {**data, "identity": digest(data)}


def summarize(rows, labels, plan):
    combined = [{**r, "method": r["method"] + " / " + r["protocol"]} for r in rows]
    metrics = scoring(combined, labels)
    index = {key(r): r for r in rows}
    changes = []
    for row in rows:
        if row["protocol"] == "original":
            continue
        base = index.get((*key(row)[:-1], "original"))
        if base is None:
            continue
        expected = labels[row["case_id"]]["reference_outcome"]
        before = base.get("answer", {}).get("assessment_outcome")
        after = row.get("answer", {}).get("assessment_outcome")
        if base["status"] != "completed" or row["status"] != "completed":
            change = "contract_or_run_status_change"
        elif before == after:
            change = "unchanged"
        elif before != expected and after == expected:
            change = "valid_wrong_to_correct"
        elif before == expected and after != expected:
            change = "valid_correct_to_wrong"
        else:
            change = "valid_wrong_to_different_wrong"
        changes.append(
            {
                **{k: row[k] for k in KEYS},
                "change": change,
                "before": before,
                "after": after,
                "reference": expected,
                "before_status": base["status"],
                "after_status": row["status"],
            }
        )
    cases = []
    for model, method, protocol in sorted({(r["model"], r["method"], r["protocol"]) for r in rows}):
        for case in plan["config"]["case_ids"]:
            group = [
                r
                for r in rows
                if (r["case_id"], r["model"], r["method"], r["protocol"])
                == (case, model, method, protocol)
            ]
            votes = Counter(
                r["answer"]["assessment_outcome"] for r in group if r["status"] == "completed"
            )
            majority = next(
                (label for label, n in votes.items() if n > plan["config"]["repeats"] / 2), None
            )
            cases.append(
                {
                    "case_id": case,
                    "model": model,
                    "method": method,
                    "protocol": protocol,
                    "recorded": len(group),
                    "votes": dict(votes),
                    "majority_outcome": majority,
                    "reference": labels[case]["reference_outcome"],
                    "majority_correct": majority == labels[case]["reference_outcome"],
                    "complete": len(group) == plan["config"]["repeats"],
                }
            )
    summary = {
        "identity": plan["identity"],
        "scope": plan["config"]["scope"],
        "planned": len(plan["conditions"]),
        "recorded": len(rows),
        "accepted": sum(r["status"] == "completed" for r in rows),
        "failed": sum(r["status"] != "completed" for r in rows),
        "complete": len(rows) == len(plan["conditions"]),
        "metrics": metrics,
        "paired_changes": dict(Counter(c["change"] for c in changes)),
        "consistency_flagged_conditions": sum(bool(r.get("consistency_flags")) for r in rows),
        "actual_model_calls": len(rows),
        "observed_attempt_seconds": sum(r["seconds"] for r in rows),
        "prompt_tokens": sum(r.get("raw_response", {}).get("prompt_eval_count", 0) for r in rows),
        "output_tokens": sum(r.get("raw_response", {}).get("eval_count", 0) for r in rows),
        "clinical_explanation_support": "pending_independent_review",
        "production_change": False,
        "independent_patients": len(plan["config"]["case_ids"]),
    }
    return summary, changes, cases


def render(output, rows, payloads, labels, summary):
    pmap = {(r["case_id"], r["method"]): r["payload"] for r in payloads}
    table = "".join(
        f"<tr><td>{escape(r['model'])}</td><td>{escape(r['method'])}</td><td>{r['accepted']}/{r['recorded']}</td><td>{r['correct']}/{r['recorded']}</td><td>{r['engineering_reference_agreement_all_recorded']:.1%}</td><td>{r['insufficient_predictions_against_other_reference']}</td></tr>"
        for r in summary["metrics"]
    )
    filters = "".join(
        f'<label>{name.title()}<select id="{name}"><option value="">All</option>'
        + "".join(f"<option>{escape(str(v))}</option>" for v in sorted({r[field] for r in rows}))
        + "</select></label>"
        for name, field in (
            ("case", "case_id"),
            ("model", "model"),
            ("method", "method"),
            ("protocol", "protocol"),
            ("repeat", "repeat"),
            ("status", "status"),
        )
    )
    cards = []
    for r in rows:
        payload = pmap[(r["case_id"], r["method"])]
        attrs = " ".join(
            f'data-{name}="{escape(str(r[field]), quote=True)}"'
            for name, field in (
                ("case", "case_id"),
                ("model", "model"),
                ("method", "method"),
                ("protocol", "protocol"),
                ("repeat", "repeat"),
                ("status", "status"),
            )
        )
        evidence = "".join(
            f'<details><summary>Source {i}: {escape(s["source_id"])} · {escape(s["module"])} · §{escape(s["section"])} · PDF {s["pdf_page"]}</summary><p><a href="evidence_guide.pdf#page={s["pdf_page"]}">Open original PDF page</a></p><pre>{escape(s["source_text"])}</pre></details>'
            for i, s in enumerate(payload["guideline_evidence"], 1)
        )
        cards.append(
            f'<article {attrs}><p class="eyebrow">{escape(r["method"])} · {escape(r["model"])} · Repeat {r["repeat"] + 1}</p><h2>{escape(r["case_id"])} / {escape(r["protocol"])}</h2>'
            f"<p>Engineering reference: <b>{escape(labels[r['case_id']]['reference_outcome'])}</b></p><p>{escape(r.get('error', r['status']))}</p>"
            f"<pre>{escape(json.dumps(r.get('answer', {}), indent=2))}</pre><details><summary>Criterion checks and consistency flags</summary><pre>{escape(json.dumps({k: r.get(k) for k in ('criterion_checks', 'consistency_flags')}, indent=2))}</pre></details>"
            "<details><summary>Identical frozen patient facts and original note</summary>"
            f"<pre>{escape(json.dumps({k: v for k, v in payload.items() if k != 'guideline_evidence'}, indent=2))}</pre></details>"
            + evidence
            + "</article>"
        )
    html = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fitness judgment comparison | Occupational Fitness Platform</title><style>
*{box-sizing:border-box}body{font:14px/1.6 'Segoe UI',Arial,sans-serif;color:#203448;background:#f5f7fa;margin:0}main{max-width:1440px;margin:auto;padding:40px 32px}.eyebrow{font-size:11px;letter-spacing:.07em;text-transform:uppercase;color:#577087}h1{font-size:32px;margin:8px 0}h2{font-size:17px}section,article{padding:24px;background:white;border:1px solid #dce3eb;border-radius:9px;margin:20px 0}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:10px;border-bottom:1px solid #e3e8ee}th{font-size:12px;color:#61758a}pre{white-space:pre-wrap;overflow-wrap:anywhere;padding:14px;background:#f4f7fa;font:12px/1.7 Consolas,monospace}summary{cursor:pointer;padding:9px 0}a{color:#21618c}label{display:inline-flex;flex-direction:column;margin:6px 14px 6px 0;font-size:12px}select{padding:8px;max-width:250px;border:1px solid #d6dfe8;background:white;border-radius:4px}.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.cards article{margin:0;min-width:0}.notice{border-left:3px solid #b98738;padding:10px 16px;background:#fcf8ef}[hidden]{display:none}@media(max-width:1100px){.cards{grid-template-columns:1fr 1fr}}@media(max-width:750px){main{padding:20px 12px}.cards{grid-template-columns:1fr}section{overflow:auto}}</style><main><p class="eyebrow">Occupational Fitness Platform · Development evaluation</p><h1>Fixed evidence, different judgment protocols</h1>"""
    html += f"<p>{summary['recorded']}/{summary['planned']} actual calls · {summary['accepted']} accepted · {summary['failed']} failed · {summary['independent_patients']} observed development cases.</p>"
    html += '<p class="notice">Engineering reference agreement, not clinical accuracy. Repeated calls are not independent patients. Failures remain in the denominator. Criterion consistency and valid source IDs do not establish that an explanation is medically supported. Production decisions are unchanged.</p>'
    html += (
        "<section><h2>Matched results</h2><table><thead><tr><th>Judge</th><th>Evidence / judgment</th><th>Accepted</th><th>Correct</th><th>Agreement</th><th>Excess insufficiency</th></tr></thead><tbody>"
        + table
        + '</tbody></table><p><a href="summary.json">Metrics and confusion matrices</a> · <a href="paired_changes.json">Valid classification changes versus contract changes</a> · <a href="case_majorities.json">Patient-level repeat votes</a> · <a href="results.jsonl">Raw responses</a> · <a href="requests.json">Exact requests</a> · <a href="plan.json">Frozen protocol</a></p></section><section>'
        + filters
        + '<p id="visible"></p></section><div class="cards">'
        + "".join(cards)
    )
    html += """</div></main><script>const keys=['case','model','method','protocol','repeat','status'];function filter(){let n=0;document.querySelectorAll('article').forEach(a=>{a.hidden=keys.some(k=>document.getElementById(k).value&&a.dataset[k]!==document.getElementById(k).value);if(!a.hidden)n++});document.getElementById('visible').textContent=n+' conditions shown'}keys.forEach(k=>document.getElementById(k).addEventListener('change',filter));['case','model','method','repeat'].forEach(k=>{const s=document.getElementById(k);if(s.options.length>1)s.selectedIndex=1});filter();</script></html>"""
    (output / "index.html").write_text(html, encoding="utf-8")


def checkpoint(output, rows, payloads, parent, plan):
    # Labels are opened only after immutable requests and actual attempts exist.
    labels = json.loads((parent / "scoring_labels.json").read_bytes())
    summary, changes, cases = summarize(rows, labels, plan)
    write_json(output / "summary.json", summary)
    write_json(output / "paired_changes.json", changes)
    write_json(output / "case_majorities.json", cases)
    write_json(
        output / "support_review_queue.json",
        [
            {
                **{k: r[k] for k in KEYS},
                "status": "pending_independent_review",
                "reference_agreement": r.get("answer", {}).get("assessment_outcome")
                == labels[r["case_id"]]["reference_outcome"],
                "consistency_flags": r.get("consistency_flags", []),
            }
            for r in rows
        ],
    )
    with (output / "summary.csv").open("w", encoding="utf-8", newline="") as stream:
        fields = (
            [k for k in summary["metrics"][0] if k != "confusion_matrix_accepted"] if rows else []
        )
        writer = csv.DictWriter(stream, fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(summary["metrics"])
    render(output, rows, payloads, labels, summary)
    write_json(
        output / "checkpoint_state.json",
        {"results_bytes": (output / "results.jsonl").stat().st_size},
    )
    write_json(
        output / "artifacts.json",
        {
            p.name: file_hash(p)
            for p in output.iterdir()
            if p.is_file() and p.name not in {"artifacts.json", ".run.lock"}
        },
    )
    return summary


def run(config_path, resume=False, prepare_only=False, max_new_calls=None):
    if max_new_calls is not None and (type(max_new_calls) is not int or max_new_calls < 1):
        raise ValueError("Call limit must be positive")
    cfg, parent, output, payloads, requests, plan = preparation(config_path)
    # Do not compete with another owned model job. Preserve exited legacy locks.
    for lock in (ROOT / "outputs/experiments").glob("*/.run.lock"):
        text = lock.read_text(encoding="ascii").strip()
        pid = int(text) if text.isdecimal() else json.loads(text)["pid"]
        if process_identity(pid) is not None:
            raise ValueError("Another experiment process is active: " + str(lock))
    output.mkdir(parents=True, exist_ok=True)
    lock = output / ".run.lock"
    with lock.open("x", encoding="ascii") as stream:
        stream.write(str(os.getpid()))
    try:
        if (output / "plan.json").exists():
            if not resume or json.loads((output / "plan.json").read_bytes()) != plan:
                raise ValueError(
                    "Resume requires an identical source, runtime, input and request plan"
                )
            if (output / "artifacts.json").exists():
                verify_checkpoint(output)
        elif any(p.name != ".run.lock" for p in output.iterdir()):
            raise ValueError("Preserve unowned experiment files")
        else:
            write_json(output / "plan.json", plan)
            write_json(output / "payloads.json", payloads)
            write_json(output / "requests.json", requests)
            shutil.copyfile(config_path, output / "config.yaml")
            shutil.copyfile(
                ROOT / "data/knowledge/raw/ap_g56_22.pdf", output / "evidence_guide.pdf"
            )
        rows = read_records(output / "results.jsonl")
        planned = {key(c): c for c in plan["conditions"]}
        done = {key(r) for r in rows}
        if len(done) != len(rows) or not done <= planned.keys():
            raise ValueError("Duplicate or foreign saved conditions")
        pmap = {(r["case_id"], r["method"]): r["payload"] for r in payloads}
        for row in rows:
            if row["experiment_identity"] != plan["identity"] or any(
                row[k] != planned[key(row)][k] for k in ("request_identity", "payload_identity")
            ):
                raise ValueError("Saved attempt identity differs")
            if row["status"] == "completed" and parse_completion(
                row["raw_response"],
                pmap[(row["case_id"], row["method"])],
                row["protocol"],
                plan["judge_config"],
            ) != {
                k: row[k]
                for k in (
                    "answer",
                    "criterion_checks",
                    "consistency_flags",
                    "clinical_explanation_support",
                )
            }:
                raise ValueError("Saved answer differs from its raw completion")
        if prepare_only:
            write_json(
                output / "artifacts.json",
                {
                    p.name: file_hash(p)
                    for p in output.iterdir()
                    if p.is_file() and p.name not in {"artifacts.json", ".run.lock"}
                },
            )
            return {"planned": len(planned), "recorded": len(rows), "prepared_only": True}
        chosen = sorted(
            plan["conditions"],
            key=lambda c: (
                plan["judge_config"]["models"].index(c["model"]),
                c["repeat"],
                c["case_id"],
                c["method"],
                cfg["protocols"].index(c["protocol"]),
            ),
        )
        calls = 0
        for condition in chosen:
            if key(condition) in done:
                continue
            if max_new_calls is not None and calls >= max_new_calls:
                break
            if runtime(plan["judge_config"]) != plan["runtime"]:
                raise ValueError("Judge runtime drift")
            started = perf_counter()
            row = {**condition, "experiment_identity": plan["identity"]}
            try:
                raw = local_post(
                    plan["judge_config"]["endpoint"],
                    "/api/chat",
                    requests[condition["request_identity"]],
                    180,
                )
                row["raw_response"] = raw
                row.update(
                    parse_completion(
                        raw,
                        pmap[(row["case_id"], row["method"])],
                        row["protocol"],
                        plan["judge_config"],
                    ),
                    status="completed",
                )
            except Exception as exc:
                row.update(status="failed", error=f"{type(exc).__name__}: {exc}")
            row["seconds"] = perf_counter() - started
            with (output / "results.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
            rows.append(row)
            done.add(key(row))
            calls += 1
            print(
                f"Judgments {len(rows)}/{len(planned)} {row['model']} {row['case_id']} {row['method']} {row['protocol']} {row['status']}",
                flush=True,
            )
            if calls % 12 == 0:
                checkpoint(output, rows, payloads, parent, plan)
        verify_artifacts(parent, plan["preparation_artifacts"])
        if (
            any(file_hash(ROOT / name) != pin for name, pin in plan["sources"].items())
            or runtime(plan["judge_config"]) != plan["runtime"]
        ):
            raise ValueError("Frozen execution sources or runtime changed")
        return checkpoint(output, rows, payloads, parent, plan)
    finally:
        lock.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--max-new-calls", type=int)
    args = parser.parse_args()
    result = run(args.config, args.resume, args.prepare_only, args.max_new_calls)
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k in {"planned", "recorded", "accepted", "failed", "complete", "prepared_only"}
            },
            indent=2,
        )
    )
