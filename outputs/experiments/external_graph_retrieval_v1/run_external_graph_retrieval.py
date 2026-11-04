"""Run isolated LightRAG mix / GraphRAG Local Search on frozen shared queries.

The four completed baseline rankings are imported by hash, never counted as
new calls. No judgment, reference label, production workflow or rule is changed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import threading
from collections import Counter
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from time import perf_counter
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request, build_opener

import yaml

from occupational_fitness_rag.evaluation.comparison_corpus import verify_corpus
from occupational_fitness_rag.evaluation.graph_contract import (
    file_hash,
    fingerprint,
    validate_records,
    verify_index,
    verify_runtime,
)
from occupational_fitness_rag.provenance import write_json

METHODS = ("lightrag", "graphrag")


def runtime_environment(python, method, root):
    code = ("import json,sys,importlib.metadata as m; "
            "print(json.dumps({'python':sys.version,'dependencies':"
            "sorted((d.metadata['Name'].lower().replace('_','-'), d.version) for d in m.distributions())}))")
    env = json.loads(subprocess.check_output([str(python), "-X", "utf8", "-c", code], text=True))
    actual = {re.sub(r"[-_.]+", "-", name): version for name, version in env["dependencies"]}
    expected_version = {"lightrag": ("lightrag-hku", "1.5.7"), "graphrag": ("graphrag", "3.2.0")}
    package, version = expected_version[method]
    if actual.get(package) != version or not env["python"].startswith("3.12."):
        raise ValueError("External framework package/Python version differs")
    lock = root / f"configs/experiments/{method}.lock.txt"
    for line in lock.read_text(encoding="utf-8").splitlines():
        if "==" in line and not line.startswith("#"):
            name, expected = line.split("==", 1)
            if actual.get(re.sub(r"[-_.]+", "-", name.lower())) != expected:
                raise ValueError("Installed external dependency differs from lock: " + name)
    return {**env, "lock_sha256": file_hash(lock)}


class AuditProxy:
    """Record real framework model calls without patching third-party code.

    Only the selected local model and embedder can be forwarded. Buffering a
    streaming response changes transport timing, not its content or tokens.
    """

    def __init__(self, config, output):
        self.config, self.output, self.job = config, output, None
        self.lock = threading.Lock()
        proxy = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def log_message(self, *args):
                pass

            def do_POST(self):
                started = perf_counter()
                body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                data = json.loads(body)
                if self.path not in {"/api/chat", "/api/embed", "/api/embeddings", "/v1/embeddings", "/v1/chat/completions"}:
                    self.send_error(403, "Route is outside the local model contract")
                    return
                if data.get("model") not in {config["graph_model"], config["embedding_model"]}:
                    self.send_error(403, "Model is outside the frozen graph contract")
                    return
                phase_path = proxy.job / "phase.json"
                phase = json.loads(phase_path.read_bytes()) if phase_path.exists() else {}
                record = {"utc": datetime.now(timezone.utc).isoformat(), "phase": phase,
                          "route": self.path, "request": data, "request_sha256": fingerprint(data)}
                try:
                    verify_runtime(config)
                    request = Request(config["endpoint"] + self.path, data=body,
                                      headers={"Content-Type": "application/json"})
                    with build_opener(ProxyHandler({})).open(request, timeout=config["call_timeout_seconds"]) as response:
                        raw, status, content_type = response.read(), response.status, response.headers.get("Content-Type")
                except HTTPError as exc:
                    raw, status, content_type = exc.read(), exc.code, "application/json"
                except Exception as exc:
                    raw = json.dumps({"error": f"{type(exc).__name__}: {exc}"}).encode()
                    status, content_type = 502, "application/json"
                record.update(http_status=status, status="completed" if status == 200 else "failed",
                              seconds=perf_counter() - started, raw_response=raw.decode("utf-8"))
                with proxy.lock, (output / "model_calls.jsonl").open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
                self.send_response(status)
                self.send_header("Content-Type", content_type or "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                try:
                    self.wfile.write(raw)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        url = urlparse(config["audit_endpoint"])
        if url.hostname != "127.0.0.1" or not url.port:
            raise ValueError("The audit endpoint must be a fixed local IPv4 port")
        self.server = ThreadingHTTPServer((url.hostname, url.port), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


def load_inputs(root, config):
    prep = root / config["preparation_dir"]
    pins = json.loads((prep / "artifacts.json").read_bytes())
    if pins["identity"] != config["expected_preparation_identity"]:
        raise ValueError("Unexpected frozen query preparation")
    for name, expected in pins["artifacts"].items():
        if file_hash(prep / name) != expected:
            raise ValueError("Prepared artifact drift: " + name)
    manifest = json.loads((prep / "manifest.json").read_bytes())
    if fingerprint({k: v for k, v in manifest.items() if k != "identity"}) != pins["identity"]:
        raise ValueError("Preparation self-identity differs")
    corpus, queries = [json.loads((prep / name).read_bytes()) for name in ("corpus.json", "queries.json")]
    verify_corpus(root, corpus)
    baseline = root / config["baseline_dir"]
    audit = json.loads((baseline / "execution_audit.json").read_bytes())
    for name, key in (("results.jsonl", "results_sha256"), ("manifest.json", "manifest_sha256"),
                      ("embedding_calls.jsonl", "embedding_calls_sha256")):
        if file_hash(baseline / name) != audit[key]:
            raise ValueError("Completed baseline artifact drift: " + name)
    if (not audit["planned_keys_complete"] or audit["records"] != len(queries) * 4
            or file_hash(baseline / "queries.json") != file_hash(prep / "queries.json")
            or json.loads((baseline / "corpus.json").read_bytes()) != corpus):
        raise ValueError("Baseline and graph queries/corpus differ")
    return prep, pins, corpus, queries, audit


def run(config_path, resume=False, selected_modules=None, selected_methods=None):
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    prep, pins, corpus, queries, baseline = load_inputs(root, config)
    verify_runtime(config)
    worker = root / "src/occupational_fitness_rag/evaluation/graph_worker.py"
    contract_source = worker.with_name("graph_contract.py")
    environments = {method: runtime_environment(root / f".runtime/{method}/Scripts/python.exe", method, root)
                    for method in METHODS}
    data = {"config": config, "preparation": pins, "baseline_audit": baseline,
            "worker_sha256": file_hash(worker), "contract_sha256": file_hash(contract_source),
            "runner_sha256": file_hash(__file__), "environments": environments,
            "planned": [{"query_id": q["query_id"], "method": m} for m in METHODS for q in queries]}
    manifest = {**data, "identity": fingerprint(data), "production_change": False}
    output = (root / config["output"]).resolve()
    if not output.is_relative_to(root / "outputs/experiments") or output == prep or output.is_relative_to(prep):
        raise ValueError("External outputs must have a separate experiment directory")
    output.mkdir(parents=True, exist_ok=True)
    lock = output / ".run.lock"
    with lock.open("x", encoding="ascii") as stream:
        stream.write(str(os.getpid()))
    try:
        target = output / "manifest.json"
        if target.exists():
            if not resume or json.loads(target.read_bytes()) != manifest:
                raise ValueError("Resume requires identical graph inputs/source/runtime/dependencies")
        else:
            if any(p.name != ".run.lock" for p in output.iterdir()):
                raise ValueError("Preserve unowned experiment files")
            write_json(target, manifest)
            for path in (worker, contract_source, Path(__file__)):
                (output / path.name).write_bytes(path.read_bytes())
        for name in ("requests", "responses", "logs", "indexes"):
            (output / name).mkdir(exist_ok=True)
        modules = sorted({q["module"] for q in queries}, key=lambda m: (m != "hypertension", m))
        with AuditProxy(config, output) as proxy:
            for method in METHODS:
                if selected_methods and method not in selected_methods:
                    continue
                for module in modules:
                    if selected_modules and module not in selected_modules:
                        continue
                    selected = [q for q in queries if q["module"] == module]
                    workspace = output / "indexes" / method
                    proxy.job = workspace
                    units = [u for u in corpus["units"] if u["module"] == module]
                    contract = {"method": method, "module": module, "corpus_sha256": corpus["corpus_sha256"],
                                "documents": [{"source_id": u["source_id"], "text_sha256": fingerprint(u["evidence_text"])} for u in units],
                                "config": config, "environment": environments[method],
                                "worker_sha256": data["worker_sha256"], "contract_sha256": data["contract_sha256"]}
                    request = {"method": method, "config": config, "corpus": str(prep / "corpus.json"),
                               "corpus_file_sha256": file_hash(prep / "corpus.json"), "corpus_sha256": corpus["corpus_sha256"],
                               "workspace": str(workspace), "top_k": 10, "queries": selected,
                               "experiment_identity": manifest["identity"], "index_contracts": {module: contract},
                               "worker_sha256": data["worker_sha256"], "contract_sha256": data["contract_sha256"]}
                    request["request_identity"] = fingerprint(request)
                    request_path, response_path = output / "requests" / f"{method}-{module}.json", output / "responses" / f"{method}-{module}.json"
                    if request_path.exists() and json.loads(request_path.read_bytes()) != request:
                        raise ValueError("Saved graph request differs")
                    write_json(request_path, request)
                    prior = json.loads(response_path.read_bytes()) if response_path.exists() else []
                    done = validate_records(prior, selected, method, corpus["units"], manifest["identity"])
                    if len(done) == len(selected):
                        if any(r["status"] == "completed" for r in prior):
                            verify_index(workspace / module, method, contract)
                        continue
                    print(f"Starting {method}/{module}: {len(units)} originals, {len(selected)} queries", flush=True)
                    failure = None
                    started = perf_counter()
                    try:
                        with (output / "logs" / f"{method}-{module}.log").open("a", encoding="utf-8") as log:
                            subprocess.run([str(root / f".runtime/{method}/Scripts/python.exe"), "-X", "utf8", str(worker),
                                            "--method", method, "--request", str(request_path), "--response", str(response_path)],
                                           stdout=log, stderr=log, check=True, timeout=config["worker_timeout_seconds"])
                    except Exception as exc:
                        failure = f"{type(exc).__name__}: {exc}"
                    rows = json.loads(response_path.read_bytes()) if response_path.exists() else []
                    done = validate_records(rows, selected, method, corpus["units"], manifest["identity"])
                    for q in selected:
                        if q["query_id"] not in done:
                            rows.append({**q, "method": method, "experiment_identity": manifest["identity"],
                                         "query_sha256": q["query_audit"]["query_sha256"], "status": "worker_failed",
                                         "source_ids": [], "error": failure or "Worker returned an incomplete query inventory"})
                    validate_records(rows, selected, method, corpus["units"], manifest["identity"])
                    write_json(response_path, rows)
                    write_json(output / "logs" / f"{method}-{module}-execution.json", {
                        "seconds": perf_counter() - started, "error": failure,
                        "status_counts": dict(Counter(r["status"] for r in rows))})
                    print(f"Finished {method}/{module}: {dict(Counter(r['status'] for r in rows))}", flush=True)
                    summarize(output, manifest, queries, corpus)
        verify_runtime(config)
        if file_hash(worker) != data["worker_sha256"] or file_hash(contract_source) != data["contract_sha256"] or file_hash(__file__) != data["runner_sha256"]:
            raise ValueError("Graph worker or runner changed during execution")
        return summarize(output, manifest, queries, corpus)
    finally:
        lock.unlink()


def summarize(output, manifest, queries, corpus):
    rows = []
    for method in METHODS:
        selected = []
        for path in sorted((output / "responses").glob(method + "-*.json")):
            selected.extend(json.loads(path.read_bytes()))
        validate_records(selected, queries, method, corpus["units"], manifest["identity"])
        rows.extend(selected)
    (output / "results.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False, allow_nan=False) + "\n" for r in rows), encoding="utf-8")
    calls = [json.loads(line) for line in (output / "model_calls.jsonl").read_text(encoding="utf-8").splitlines()] if (output / "model_calls.jsonl").exists() else []
    summary = {"identity": manifest["identity"], "planned": len(queries) * 2, "recorded": len(rows),
               "status_counts": dict(Counter(r["status"] for r in rows)),
               "methods": {m: dict(Counter(r["status"] for r in rows if r["method"] == m)) for m in METHODS},
               "index_count": len(list((output / "indexes").glob("*/*/index_manifest.json"))),
               "actual_model_calls": len(calls), "failed_model_calls": sum(r["status"] != "completed" for r in calls),
               "complete_inventory": len(rows) == len(queries) * 2,
               "judgment_calls": 0, "production_change": False,
               "results_sha256": file_hash(output / "results.jsonl"),
               "model_calls_sha256": file_hash(output / "model_calls.jsonl") if calls else None}
    write_json(output / "summary.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--modules", nargs="+")
    parser.add_argument("--methods", nargs="+", choices=METHODS)
    args = parser.parse_args()
    print(json.dumps(run(args.config, args.resume, args.modules, args.methods), indent=2))
