"""Replay length-limited graph completions with a larger fixed output budget.

This diagnostic changes no index, ranking, patient fact or clinical judgment.
"""

import argparse
import json
from copy import deepcopy
from html import escape
from pathlib import Path
from time import perf_counter

from occupational_fitness_rag.evaluation.graph_contract import (
    file_hash,
    fingerprint,
    verify_runtime,
)
from occupational_fitness_rag.evaluation.judgment_comparison import local_post
from occupational_fitness_rag.provenance import write_json
from tools.report_six_method_retrieval import completion_quality


def expanded_request(call, output_tokens, context_length):
    original = call["request"]
    prior = json.loads(call["raw_response"])
    if fingerprint(original) != call["request_sha256"] or prior.get("done_reason") != "length":
        raise ValueError("Only a verified native length stop can enter this diagnostic")
    if original.get("stream") is True:
        raise ValueError("Streaming extraction needs a separately validated replay contract")
    if prior.get("prompt_eval_count", context_length) + output_tokens > context_length:
        raise ValueError("The larger output budget would exceed the recorded context capacity")
    new = deepcopy(original)
    before = new.setdefault("options", {}).get("num_predict")
    if not isinstance(before, int) or output_tokens <= before:
        raise ValueError("The diagnostic output budget must strictly increase the native limit")
    new["options"]["num_predict"] = output_tokens
    check = deepcopy(new)
    check["options"]["num_predict"] = before
    if check != original:
        raise ValueError("The diagnostic changed more than the output budget")
    return new


def run(root, graph_dir, output, output_tokens=4096):
    root, graph_dir, output = [Path(p).resolve() for p in (root, graph_dir, output)]
    if not output.is_relative_to(root / "outputs/experiments") or output.exists():
        raise ValueError("Use a new diagnostic output directory")
    summary = json.loads((graph_dir / "summary.json").read_bytes())
    manifest = json.loads((graph_dir / "manifest.json").read_bytes())
    if not summary["complete_inventory"] or file_hash(graph_dir / "model_calls.jsonl") != summary["model_calls_sha256"]:
        raise ValueError("Wait for the frozen complete external execution")
    config = manifest["config"]
    verify_runtime(config)
    calls = [json.loads(line) for line in (graph_dir / "model_calls.jsonl").read_text(encoding="utf-8").splitlines()]
    warnings = completion_quality(calls, [])["warnings"]
    identity = {"parent_identity": manifest["identity"], "parent_calls_sha256": summary["model_calls_sha256"],
                "output_tokens": output_tokens, "source_sha256": file_hash(__file__),
                "scope": "Native extraction completion diagnostic only; no index or retrieval replacement"}
    output.mkdir(parents=True)
    write_json(output / "manifest.json", {**identity, "identity": fingerprint(identity), "production_change": False})
    rows = []
    for warning in warnings:
        started = perf_counter()
        call = calls[warning["call_number"] - 1]
        row = {"original_call_number": warning["call_number"], "phase": call["phase"],
               "original_request": call["request"], "original_raw_response": call["raw_response"],
               "status": "failed", "provider_called": False}
        try:
            request = expanded_request(call, output_tokens, config["graph_context_length"])
            row.update(request=request, request_sha256=fingerprint(request))
            verify_runtime(config)
            row["provider_called"] = True
            raw = local_post(config["endpoint"], call["route"], request, 240)
            row["raw_response"] = raw
            if raw.get("done_reason") != "stop" or not raw.get("done") or not raw.get("message", {}).get("content"):
                raise ValueError("The expanded completion did not finish normally")
            if request.get("format"):
                json.loads(raw["message"]["content"])
            row.update(status="completed", output_tokens=raw.get("eval_count"),
                       semantic_graph_completeness=None,
                       note="Output completion only. Fresh native indexing/retrieval is still required before replacing the affected graph evidence.")
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
        row["seconds"] = perf_counter() - started
        rows.append(row)
        write_json(output / "results.json", rows)
        print(f"Diagnostic {len(rows)}/{len(warnings)}: {row['phase']} {row['status']}", flush=True)
    result = {"conditions": len(rows), "completed": sum(r["status"] == "completed" for r in rows),
              "failed": sum(r["status"] != "completed" for r in rows),
              "actual_model_calls": sum(r["provider_called"] for r in rows),
              "judgment_calls": 0, "indexes_replaced": 0, "rankings_replaced": 0,
              "output_tokens": output_tokens, "production_change": False}
    write_json(output / "summary.json", result)
    cards = ''.join('<article><h3>' + escape(str(r["phase"])) + '</h3><p>' + r["status"] + '</p><details><summary>Native completion</summary><pre>' + escape(json.dumps(r.get("raw_response", r.get("error")), ensure_ascii=False, indent=2)) + '</pre></details></article>' for r in rows)
    html = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Graph output recovery diagnostic</title><style>body{font:15px/1.7 Arial;background:#f4f6f9;color:#213749;max-width:1100px;margin:40px auto}header,article{background:white;padding:24px;border:1px solid #dce3ea;border-radius:10px;margin:20px}pre{white-space:pre-wrap;font:13px/1.6 Consolas}summary{cursor:pointer}</style><header><h1>Graph output recovery diagnostic</h1><p>Native output-limit replay only. No graph index, retrieval ranking or fitness judgment was replaced.</p><pre>' + escape(json.dumps(result, indent=2)) + '</pre><a href="results.json">Original and expanded requests/responses</a></header>' + cards + '</html>'
    (output / "index.html").write_text(html, encoding="utf-8")
    write_json(output / "artifacts.json", {p.name: file_hash(p) for p in output.iterdir() if p.is_file()})
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graphs", default="outputs/experiments/external_graph_retrieval_v2")
    parser.add_argument("--output", default="outputs/experiments/graph_output_recovery_pilot_v1")
    args = parser.parse_args()
    print(json.dumps(run(Path.cwd(), args.graphs, args.output), indent=2))
