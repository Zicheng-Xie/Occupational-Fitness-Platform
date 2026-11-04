"""Serve preserved retrieval reports with an auditable local-model judgment panel.

Run: python -m tools.serve_retrieval_judgments --port 8781
Batch: python -m tools.serve_retrieval_judgments --batch --case VAL-MIX-02
"""

from __future__ import annotations

import argparse
import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, ConfigDict

from occupational_fitness_rag.evaluation import retrieval_judgment as judge
from occupational_fitness_rag.evaluation.passage_comparison import local_get
from tools.complex_ten_contract import ROOT, digest, pin, read, write_json

DEFAULT = ROOT / "outputs/experiments/retrieval_judgments_20261103"
REPORTS = {
    "ten-methods": ROOT / "outputs/experiments/complex_234_ten_methods_20261027/comparison",
    "refinement": ROOT / "outputs/experiments/complex_234_refinement_20261029",
}
ASSETS = ROOT / "src/occupational_fitness_rag/web/static"
MODELS = ("llama3:8b", "qwen3.5:4b-q4_K_M")
SERVICE_NAME = "occupational-fitness-evidence-review"


class Condition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset: str
    query_id: str
    method: str
    top_k: int = 5
    model: str = MODELS[0]
    evidence_mode: str = "strict_topk"


def dataset(directory):
    """Read the exact embedded, frozen observations displayed by index.html."""
    html = (directory / "index.html").read_text(encoding="utf-8")
    match = re.search(r'<script id="(?:data|dataset)" type="application/json">(.*?)</script>',
                      html, re.S)
    if not match:
        raise ValueError("Unsupported report data contract")
    data = json.loads(match[1])
    source_units = data.get("units", data.get("corpus"))
    units = source_units if isinstance(source_units, dict) else {
        unit["source_id"]: unit for unit in source_units
    }
    queries = {q["query_id"]: q for q in data["queries"]}
    rankings = {(r["query_id"], r["method"]): r for r in data["rankings"]}
    if len(rankings) != len(data["rankings"]) or len(queries) != len(data["queries"]):
        raise ValueError("Duplicate observations in report")
    return {"queries": queries, "rankings": rankings, "units": units,
            "report_sha256": pin(directory / "index.html")}


class ReviewService:
    def __init__(self, output=DEFAULT, reports=None, endpoint="http://127.0.0.1:11434"):
        self.output = Path(output)
        self.reports = reports or REPORTS
        self.datasets = {name: dataset(path) for name, path in self.reports.items()}
        self.endpoint = endpoint
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="local-fitness-review")
        self.lock = threading.Lock()
        self.jobs = {}
        self.models = None
        self.counters = {}
        self.output.mkdir(parents=True, exist_ok=True)
        self.owner = (self.output / "owner.lock").open("a+b")
        self.owner.seek(0)
        if os.name == "nt":
            import msvcrt
            if self.owner.read(1) == b"":
                self.owner.write(b"0")
                self.owner.flush()
            self.owner.seek(0)
            msvcrt.locking(self.owner.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(self.owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest = {
            "protocol": judge.PROTOCOL, "production_change": False,
            "reports": {k: v["report_sha256"] for k, v in self.datasets.items()},
            "implementation": {name: pin(ROOT / name) for name in (
                "src/occupational_fitness_rag/evaluation/retrieval_judgment.py",
                "tools/serve_retrieval_judgments.py",
                "src/occupational_fitness_rag/web/static/retrieval_judgment.js")},
            "label_policy": "No reference label, rule result or retrieval score enters model input",
            "scope": "One case and requested module per exact Top-K condition",
        }
        self.implementation_identity = digest(manifest["implementation"])
        self.engine_sha256 = manifest["implementation"][
            "src/occupational_fitness_rag/evaluation/retrieval_judgment.py"
        ]
        write_json(self.output / "manifests" / (digest(manifest) + ".json"), manifest)
        write_json(self.output / "manifest.json", manifest)

    def inventory(self):
        if self.models is None:
            tags = local_get(self.endpoint, "/api/tags")
            self.models = {m["name"]: m for m in tags["models"] if m["name"] in MODELS}
            for name, model in self.models.items():
                info = judge.local_post(self.endpoint, "/api/show", {"model": name,
                                        "verbose": name.startswith("llama3:")})["model_info"]
                limits = [v for k, v in info.items() if k.endswith(".context_length")]
                if not limits:
                    raise ValueError("Installed model lacks native context metadata")
                model["review_context"] = min(min(limits), 8192 if name.startswith("llama3:")
                                               else 32768)
                if name.startswith("llama3:"):
                    self.counters[name] = judge.llama_token_counter(info)
        return self.models

    def submit(self, condition):
        c = condition.model_dump()
        if c["dataset"] not in self.datasets or c["model"] not in MODELS:
            raise ValueError("Unknown report or model")
        d = self.datasets[c["dataset"]]
        q = d["queries"].get(c["query_id"])
        r = d["rankings"].get((c["query_id"], c["method"]))
        if c["query_id"].startswith("CASE:"):
            q, r = judge.case_observation(c["query_id"][5:], d["queries"], d["rankings"],
                                           c["method"])
        if q is None or r is None:
            raise ValueError("Unknown case/module/method observation")
        payload = judge.build_payload(q, r, d["units"], c["top_k"], c["evidence_mode"])
        model = self.inventory().get(c["model"])
        if model is None:
            raise ValueError("Requested local model is not installed")
        context = model["review_context"]
        request, error = None, None
        try:
            request = judge.build_request(payload, c["model"], context,
                                          count_tokens=self.counters.get(c["model"]))
        except ValueError as exc:
            error = str(exc)
        identity = digest({"condition_identity": judge.condition_identity(
            c, payload, request, model["digest"]), "judge_engine_sha256": self.engine_sha256})
        target = self.output / "records" / (identity + ".json")
        with self.lock:
            if identity in self.jobs:
                return self.jobs[identity]
            if target.exists():
                saved = read(target)
                if saved["status"] in {"completed", "requires_review", "failed", "blocked_context"}:
                    self.jobs[identity] = saved
                    return saved
            # A stylesheet, UI or HTTP-server edit must not hide an identical
            # completed model call. Revalidate its actual response with the current
            # parser, then create a derived record; never rewrite the observation.
            for saved in compatible_records(self.records()):
                if (saved["condition"] == c and saved["payload"] == payload
                    and saved.get("request") == request
                    and saved.get("model_digest") == model["digest"]
                    and saved["status"] in {"completed", "requires_review", "blocked_context"}):
                    restored = {**saved, "id": identity, "origin_record_id": saved["id"],
                                "implementation_identity": self.implementation_identity,
                                "judge_engine_sha256": self.engine_sha256,
                                "cache_note": "Exact request/evidence/weights reused; current parser revalidated"}
                    self.jobs[identity] = restored
                    write_json(target, restored)
                    return restored
            record = {
                "id": identity, "condition": c, "case_id": q["case_id"],
                "module": q["module"], "protocol": judge.PROTOCOL,
                "model_digest": model["digest"], "report_sha256": d["report_sha256"],
                "payload": payload, "payload_sha256": digest(payload), "request": request,
                "implementation_identity": self.implementation_identity,
                "judge_engine_sha256": self.engine_sha256,
                "allocation": r.get("allocation", "Exact per-module ranking prefix"),
                "module_query_ids": r.get("module_query_ids", [q["query_id"]]),
                "status": "blocked_context" if error else "queued", "error": error,
                "validation_note": "Quotation validity is distinct from clinical correctness",
            }
            self.jobs[identity] = record
            write_json(target, record)
            if not error:
                self.pool.submit(self.execute, identity)
            return dict(record)

    def execute(self, identity):
        with self.lock:
            record = self.jobs[identity]
            record["status"] = "running"
            write_json(self.output / "records" / (identity + ".json"), record)
        started = perf_counter()
        try:
            raw = judge.call_review(self.endpoint, record["request"])
            # Preserve actual model output even when validation fails.
            record["raw_response"] = raw
            result = judge.parse_review(raw, record["payload"], record["request"])
            record["result"] = result
            record["status"] = "requires_review" if result["validation_warnings"] else "completed"
        except Exception as exc:
            record["status"] = "failed"
            record["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            record["seconds"] = perf_counter() - started
            with self.lock:
                write_json(self.output / "records" / (identity + ".json"), record)

    def close(self):
        self.pool.shutdown(wait=True)
        self.owner.close()

    def records(self):
        return [read(p) for p in sorted((self.output / "records").glob("*.json"))]


def compatible_records(records):
    """Keep valid saved reviews visible after presentation-only changes."""
    def priority(item):
        return (bool(item.get("result")),
                item.get("raw_response", {}).get("created_at", ""), item["id"])

    selected = {}
    for r in records:
        if r.get("protocol") != judge.PROTOCOL or not r.get("payload"):
            continue
        if r.get("payload_sha256") != digest(r["payload"]):
            continue
        request = r.get("request")
        if request and (request.get("messages", [{}])[0].get("content") != judge.SYSTEM):
            continue
        current = dict(r)
        if r.get("result"):
            try:
                result = judge.parse_review(r["raw_response"], r["payload"], request)
            except (ValueError, KeyError, TypeError):
                continue
            current["result"] = result
            current["status"] = "requires_review" if result["validation_warnings"] else "completed"
        key = digest(r["condition"])
        old = selected.get(key)
        if old is None or priority(current) > priority(old):
            selected[key] = current
    return list(selected.values())


def inject(html, name, records=(), implementation_identity=None,
           live_origin="http://127.0.0.1:8781"):
    current = [r for r in compatible_records(records) if r["condition"]["dataset"] == name]
    embedded = json.dumps(current, ensure_ascii=False).replace("<", "\\u003c")
    addition = (
        '<script id="fitness-review-cache" type="application/json">' + embedded + '</script>'
        '<script>window.fitnessReviewDataset=' + json.dumps(name) + ';</script>'
        '<script>window.fitnessReviewLiveOrigin=' + json.dumps(live_origin) + ';</script>'
        '<script src="/review-assets/retrieval_judgment.js"></script>'
    )
    return html.replace("</body>", addition + "</body>")


def create_app(service):
    @asynccontextmanager
    async def lifespan(app):
        yield
        service.close()

    app = FastAPI(title="Occupational Fitness Evidence Review", lifespan=lifespan)

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        return page("refinement", request)

    @app.get("/{name}/index.html", response_class=HTMLResponse)
    def page(name: str, request: Request):
        if name not in service.reports:
            raise HTTPException(404)
        html = (service.reports[name] / "index.html").read_text(encoding="utf-8")
        # Root-relative links keep the original downloadable artifacts accessible.
        html = html.replace('<head>', '<head><base href="/' + name + '/">', 1)
        return inject(html, name, service.records(), service.implementation_identity,
                      str(request.base_url).rstrip("/"))

    @app.get("/review-assets/retrieval_judgment.js")
    def asset():
        return FileResponse(ASSETS / "retrieval_judgment.js", media_type="text/javascript")

    @app.get("/api/review-models")
    def models():
        try:
            return {"service": SERVICE_NAME, "models": list(service.inventory()),
                    "protocol": judge.PROTOCOL}
        except Exception as exc:
            raise HTTPException(503, detail=str(exc)) from exc

    @app.post("/api/reviews")
    def submit(condition: Condition, request: Request):
        # No remote origins, arbitrary Ollama URLs or client-provided evidence.
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            raise HTTPException(403, detail="Same-origin requests required")
        try:
            return service.submit(condition)
        except ValueError as exc:
            raise HTTPException(400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(503, detail=str(exc)) from exc

    @app.get("/api/reviews/{identity}")
    def status(identity: str):
        if not re.fullmatch(r"[a-f0-9]{64}", identity):
            raise HTTPException(400)
        path = service.output / "records" / (identity + ".json")
        if not path.exists():
            raise HTTPException(404)
        with service.lock:
            return dict(service.jobs[identity]) if identity in service.jobs else read(path)

    @app.get("/{name}/{filename:path}")
    def artifact(name: str, filename: str):
        if name not in service.reports:
            raise HTTPException(404)
        root = service.reports[name].resolve()
        path = (root / filename).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise HTTPException(404)
        return FileResponse(path)

    return app


def export(service, destination):
    """Add an offline snapshot without overwriting either preserved report."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    records = service.records()
    for name, directory in service.reports.items():
        target = destination / name
        target.mkdir(exist_ok=True)
        html = inject((directory / "index.html").read_text(encoding="utf-8"), name, records,
                      service.implementation_identity)
        # Inline the script so the model commentary remains readable offline.
        html = html.replace('<script src="/review-assets/retrieval_judgment.js"></script>',
                            '<script>' + (ASSETS / "retrieval_judgment.js").read_text(
                                encoding="utf-8") + '</script>')
        (target / "index.html").write_text(html, encoding="utf-8")
        import shutil
        for path in directory.iterdir():
            if path.is_file() and path.name != "index.html":
                shutil.copy2(path, target / path.name)
    write_json(destination / "judgments.json", records)
    write_json(destination / "manifest.json", {
        "source_reports": {k: v["report_sha256"] for k, v in service.datasets.items()},
        "records": len(records), "clinical_review_status": "pending",
        "files": {p.relative_to(destination).as_posix(): pin(p)
                  for p in destination.rglob("*") if p.is_file() and p.name != "manifest.json"},
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8781)
    parser.add_argument("--output", type=Path, default=DEFAULT)
    parser.add_argument("--batch", action="store_true")
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--method", action="append", default=[])
    parser.add_argument("--dataset", choices=list(REPORTS), default="refinement")
    parser.add_argument("--model", choices=MODELS, default=MODELS[0])
    parser.add_argument("--top-k", type=int, choices=[5, 10], default=5)
    parser.add_argument("--evidence-mode", choices=["strict_topk", "explicit_references"],
                        default="strict_topk")
    parser.add_argument("--export", type=Path)
    args = parser.parse_args()
    service = ReviewService(args.output)
    if args.batch:
        try:
            for (qid, method), row in service.datasets[args.dataset]["rankings"].items():
                if args.case and row["case_id"] not in args.case:
                    continue
                if args.method and method not in args.method:
                    continue
                job = service.submit(Condition(dataset=args.dataset, query_id=qid,
                    method=method, top_k=args.top_k, model=args.model,
                    evidence_mode=args.evidence_mode))
                print(json.dumps({"id": job["id"], "case": row["case_id"],
                                  "method": method, "status": job["status"]}), flush=True)
            service.pool.shutdown(wait=True)
            if args.export:
                export(service, args.export)
        finally:
            service.close()
    elif args.export:
        try:
            export(service, args.export)
        finally:
            service.close()
    else:
        import uvicorn
        print(f"Evidence review: http://127.0.0.1:{args.port}/refinement/index.html", flush=True)
        uvicorn.run(create_app(service), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
