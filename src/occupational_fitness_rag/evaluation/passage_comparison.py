"""Fresh query-policy and passage-contract development comparison, isolated from production."""

import argparse
import csv
import importlib.metadata
import json
import math
import os
import platform
import sys
from collections import Counter, defaultdict
from copy import deepcopy
from html import escape
from itertools import product
from pathlib import Path
from time import perf_counter
from urllib.request import ProxyHandler, build_opener

import yaml

from occupational_fitness_rag.evaluation.evidence_selection import select_documented_evidence
from occupational_fitness_rag.evaluation.judgment_comparison import local_post, make_payload
from occupational_fitness_rag.evaluation.module_queries import build_module_query
from occupational_fitness_rag.indexing.base import StoredDocument
from occupational_fitness_rag.llm import require_local_url
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json
from occupational_fitness_rag.retrieval.bm25 import rank_bm25
from occupational_fitness_rag.retrieval.fusion import reciprocal_rank_fusion

POLICIES = {"mixed_query", "module_query", "reference_evidence"}
PROTOCOLS = {"quote_contract", "passage_selection"}
KEY_FIELDS = ("model", "case_id", "evidence_policy", "protocol", "repeat")


def json_bytes(value):
    """Match the JSON body serialization used by the local HTTP adapter."""
    return json.dumps(value, allow_nan=False).encode("utf-8")


def read_records(path):
    """Never append after an incomplete JSONL tail or silently ignore corruption."""
    if not path.exists():
        return []
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise ValueError(
            "Incomplete JSONL tail; preserve it and use a new output or recover explicitly"
        )
    return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]


def condition_key(row):
    return tuple(row[field] for field in KEY_FIELDS)


def patient_identity(payload):
    return digest({key: value for key, value in payload.items() if key != "guideline_evidence"})


def local_get(endpoint, path):
    with build_opener(ProxyHandler({})).open(
        require_local_url(endpoint) + path, timeout=10
    ) as response:
        return json.load(response)


def pinned_environment(config, get=local_get):
    inventory = {
        model["name"]: model["digest"] for model in get(config["endpoint"], "/api/tags")["models"]
    }
    pins = {
        **config["expected_model_digests"],
        config["embedding_model"]: config["embedding_model_digest"],
    }
    if any(inventory.get(model) != expected for model, expected in pins.items()):
        raise ValueError("Installed local model digest differs from the frozen experiment pin")
    runtime = get(config["endpoint"], "/api/version")
    if runtime.get("version") != config["expected_runtime_version"]:
        raise ValueError("Local model runtime differs from the frozen experiment version")
    return {"model_digests": pins, "runtime": runtime}


def validate_config(config):
    require_local_url(config["endpoint"])
    for field in ["case_ids", "models", "evidence_policies", "protocols"]:
        values = config[field]
        if not isinstance(values, list) or not values or len(set(values)) != len(values):
            raise ValueError("Experiment dimensions must be non-empty unique lists")
    if (
        not set(config["evidence_policies"]) <= POLICIES
        or not set(config["protocols"]) <= PROTOCOLS
    ):
        raise ValueError("Unknown comparison policy or protocol")
    if set(config["expected_model_digests"]) != set(config["models"]):
        raise ValueError("Every judge must have exactly one explicit model digest pin")
    for field in [
        "repeats",
        "top_k",
        "sensitivity_k",
        "embedding_dimensions",
        "context_length",
        "output_tokens",
        "prompt_max_bytes",
        "request_max_bytes",
        "evidence_max_bytes",
    ]:
        if (
            isinstance(config[field], bool)
            or not isinstance(config[field], int)
            or config[field] < 1
        ):
            raise ValueError("Experiment budgets and dimensions must be positive integers")
    if (
        config["top_k"] > config["sensitivity_k"]
        or config["output_tokens"] >= config["context_length"]
    ):
        raise ValueError("Invalid retrieval or model context budget")
    if type(config.get("max_validation_repairs", 0)) is not int or config.get(
        "max_validation_repairs", 0
    ) not in [0, 1]:
        raise ValueError("At most one structural validation repair is permitted")


def load_frozen_inputs(baseline, case_ids, corpus_override=None):
    paths = [
        baseline / name
        for name in ["results.jsonl", "corpus.json", "manifest.json", "model_inventory.json"]
    ]
    fingerprints = {path.name: sha256_bytes(path.read_bytes()) for path in paths}
    corpus = json.loads((baseline / "corpus.json").read_text(encoding="utf-8"))
    original_units = {unit["source_id"]: unit for unit in corpus["units"]}
    if corpus_override is not None:
        selected_path = Path(corpus_override)
        selected = json.loads(selected_path.read_text(encoding="utf-8"))
        if (
            selected.get("quality_review", {}).get("base_corpus_sha256") != corpus["corpus_sha256"]
            or selected["document_sha256"] != corpus["document_sha256"]
            or digest({key: value for key, value in selected.items() if key != "corpus_sha256"})
            != selected["corpus_sha256"]
        ):
            raise ValueError("Reviewed corpus override has an incompatible origin or fingerprint")
        fingerprints["reviewed_corpus.json"] = sha256_bytes(selected_path.read_bytes())
        corpus = selected
    units = {unit["source_id"]: unit for unit in corpus["units"]}
    if len(units) != len(corpus["units"]):
        raise ValueError("Duplicate frozen corpus source identifier")
    if any(unit.get("licence_context") not in {"commercial", "shared"} for unit in units.values()):
        raise ValueError("Frozen corpus includes an inapplicable licence scope")
    old = read_records(baseline / "results.jsonl")
    inputs = {}
    for case_id in case_ids:
        frozen = {}
        references = set()
        for method in ["hybrid", "reference_evidence"]:
            rows = [row for row in old if row["case_id"] == case_id and row["method"] == method]
            if not rows or len({digest(row["input_snapshot"]) for row in rows}) != 1:
                raise ValueError("Missing or inconsistent historical frozen payload")
            references.update(row["reference_outcome"] for row in rows)
            payload = deepcopy(rows[0]["input_snapshot"])
            for source in payload["guideline_evidence"]:
                original = original_units.get(source["source_id"])
                if original is None or source["source_text"] != original["evidence_text"]:
                    raise ValueError("Historical payload does not match its original frozen corpus")
                unit = units.get(source["source_id"])
                if unit is None:
                    if method == "reference_evidence":
                        raise ValueError("Reviewed corpus removed a reference-control source")
                    if source["source_id"] not in corpus.get("quality_review", {}).get(
                        "excluded_source_ids", []
                    ):
                        raise ValueError(
                            "Historical source disappeared without a reviewed exclusion"
                        )
                    source["module"] = original["module"]
                    continue
                if source["source_text"] != unit["evidence_text"]:
                    raise ValueError("Frozen source is not exact original corpus text")
                source["module"] = unit["module"]
            frozen[method] = payload
        if len(references) != 1 or patient_identity(frozen["hybrid"]) != patient_identity(
            frozen["reference_evidence"]
        ):
            raise ValueError("Historical controls disagree on patient inputs or reference label")
        inputs[case_id] = {
            "payload": frozen["hybrid"],
            "reference_payload": frozen["reference_evidence"],
            "reference_outcome": references.pop(),
        }
    return corpus, inputs, fingerprints


def source_snapshot(config_text):
    package = Path(__file__).resolve().parents[1]
    files = {}
    for path in sorted(package.rglob("*.py")):
        raw = path.read_bytes()
        files[str(path.relative_to(package)).replace("\\", "/")] = {
            "sha256": sha256_bytes(raw),
            "content": raw.decode("utf-8"),
        }
    dependencies = sorted(
        {
            (item.metadata["Name"], item.version)
            for item in importlib.metadata.distributions()
            if item.metadata["Name"]
        }
    )
    return {
        "first_party_source": files,
        "config_text": config_text,
        "python": sys.version,
        "platform": platform.platform(),
        "dependencies": dependencies,
    }


class HybridRetriever:
    """Actual dense/BM25/RRF ranking with a new, pinned corpus embedding cache."""

    def __init__(self, corpus, config, output, identity, post=local_post, get=local_get):
        self.corpus, self.config, self.output = corpus, config, output
        self.identity, self.post, self.get = identity, post, get
        self.docs = [
            StoredDocument(unit["source_id"], unit["evidence_text"], {"module": unit["module"]})
            for unit in corpus["units"]
        ]
        self.vectors = None

    def embed(self, texts):
        pinned_environment(self.config, self.get)
        request = {"model": self.config["embedding_model"], "input": texts, "truncate": False}
        raw = self.post(
            self.config["endpoint"], "/api/embed", request, timeout=self.config["timeout_seconds"]
        )
        vectors = raw.get("embeddings", [])
        self.validate_vectors(vectors, len(texts))
        return vectors, {"request": request, "request_sha256": digest(request), "raw_response": raw}

    def validate_vectors(self, vectors, count):
        if not isinstance(vectors, list) or len(vectors) != count:
            raise ValueError("Embedding response count differs from its input count")
        for vector in vectors:
            if (
                not isinstance(vector, list)
                or len(vector) != self.config["embedding_dimensions"]
                or any(
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                    for value in vector
                )
                or not sum(value * value for value in vector)
            ):
                raise ValueError("Embedding has invalid dimensions or non-finite/zero values")

    def ensure_vectors(self):
        path = self.output / "embeddings.json"
        if self.vectors is not None:
            return
        if path.exists():
            saved = json.loads(path.read_text(encoding="utf-8"))
            if (
                saved["identity"] != self.identity
                or digest(saved["vectors"]) != saved["vectors_sha256"]
            ):
                raise ValueError("Embedding cache identity or content mismatch")
            self.validate_vectors(saved["vectors"], len(self.docs))
            self.vectors = saved["vectors"]
            return
        vectors, calls = [], []
        started = perf_counter()
        for start in range(0, len(self.docs), 8):
            batch, call = self.embed([doc.text for doc in self.docs[start : start + 8]])
            vectors.extend(batch)
            calls.append(call)
        self.vectors = vectors
        write_json(
            path,
            {
                "identity": self.identity,
                "vectors": vectors,
                "vectors_sha256": digest(vectors),
                "calls": calls,
                "seconds": perf_counter() - started,
                "scope": "Fresh embeddings built for this output; no historical vector cache reused",
            },
        )

    def retrieve(self, query, module, k):
        self.ensure_vectors()
        vectors, call = self.embed([query])
        q = vectors[0]
        qnorm = math.sqrt(sum(value * value for value in q))
        docs = [doc for doc in self.docs if doc.metadata["module"] == module]
        if not docs:
            raise ValueError("No frozen corpus documents for requested module")
        sparse = rank_bm25(query, docs, 30)
        dense = []
        for doc, vector in zip(self.docs, self.vectors, strict=True):
            if doc.metadata["module"] != module:
                continue
            norm = math.sqrt(sum(value * value for value in vector))
            score = sum(a * b for a, b in zip(q, vector, strict=True)) / (qnorm * norm)
            dense.append(StoredDocument(doc.chunk_id, doc.text, doc.metadata, score))
        dense.sort(key=lambda doc: (-doc.vector_score, doc.chunk_id))
        hits = reciprocal_rank_fusion(dense[:20], sparse, 60)[:k]
        return {
            "source_ids": [hit.doc.chunk_id for hit in hits],
            "ranked_sources": [
                {
                    "source_id": hit.doc.chunk_id,
                    "rrf_score": hit.score,
                    "vector_score": hit.vector_score,
                    "bm25_score": hit.bm25_score,
                }
                for hit in hits
            ],
            "query_embedding": call,
            "rrf_k": 60,
        }


def build_selected_payload(original, units, rankings, config):
    selection = select_documented_evidence(original, rankings, config["top_k"])
    case = {
        "facts": {
            field: {
                "status": "present",
                "value": fact["value"],
                "evidence": [{"quote": quote} for quote in fact["patient_quotes"]],
            }
            for field, fact in original["verified_patient_facts"].items()
        },
        "modules_requested": original["modules"],
        "source_text": original["nurse_note"],
    }
    payload, excluded = make_payload(case, units, selection["source_ids"], config)
    accepted = []
    for source in payload["guideline_evidence"]:
        source["module"] = units[source["source_id"]]["module"]
        if len(json_bytes([*accepted, source])) > config["evidence_max_bytes"]:
            excluded.append(source["source_id"])
        else:
            accepted.append(source)
    payload["guideline_evidence"] = accepted
    if patient_identity(original) != patient_identity(payload):
        raise ValueError("Evidence selection changed frozen patient inputs")
    if not accepted:
        raise ValueError("Evidence allocation yielded no original passages; no fallback permitted")
    selection["excluded_by_byte_budget"] = excluded
    selection["supplied_source_ids"] = [source["source_id"] for source in accepted]
    return payload, selection


def freeze_retrieval(config, corpus, inputs, output, identity, post, get):
    freeze_path = output / "retrieval_freeze.json"
    artifact_names = ["retrieval.json", "payloads.json", "embeddings.json"]
    if freeze_path.exists():
        frozen = json.loads(freeze_path.read_text(encoding="utf-8"))
        observed = {name: sha256_bytes((output / name).read_bytes()) for name in artifact_names}
        if frozen != {"identity": identity, "artifacts": observed}:
            raise ValueError("Frozen retrieval artifact changed; refuse incompatible resume")
        return json.loads((output / "payloads.json").read_text(encoding="utf-8"))
    path = output / "retrieval.json"
    saved = (
        json.loads(path.read_text(encoding="utf-8"))
        if path.exists()
        else {"identity": identity, "records": []}
    )
    if saved["identity"] != identity:
        raise ValueError("Retrieval snapshot identity mismatch")
    queries = []
    for case_id, item in inputs.items():
        for policy in [p for p in config["evidence_policies"] if p != "reference_evidence"]:
            for module in item["payload"]["modules"]:
                if policy == "module_query":
                    query, audit = build_module_query(item["payload"], module)
                else:
                    query = item["payload"]["nurse_note"]
                    audit = {
                        "policy": "historical_full_note_query",
                        "query_sha256": sha256_bytes(query.encode("utf-8")),
                    }
                queries.append(
                    {
                        "case_id": case_id,
                        "evidence_policy": policy,
                        "module": module,
                        "query": query,
                        "query_audit": audit,
                    }
                )
    expected = {(q["case_id"], q["evidence_policy"], q["module"]): q for q in queries}
    records = {(r["case_id"], r["evidence_policy"], r["module"]): r for r in saved["records"]}
    if len(records) != len(saved["records"]) or not records.keys() <= expected.keys():
        raise ValueError("Duplicate or unexpected retrieval condition")
    retriever = HybridRetriever(corpus, config, output, identity, post, get)
    retriever.ensure_vectors()
    for key, query in expected.items():
        if key in records:
            if any(records[key][field] != query[field] for field in query):
                raise ValueError("Saved retrieval query differs from the frozen input")
            continue
        started = perf_counter()
        result = {**query, "status": "failed", "source_ids": []}
        try:
            result.update(
                retriever.retrieve(query["query"], query["module"], config["sensitivity_k"])
            )
            if not result["source_ids"]:
                raise ValueError("Empty retrieval result; no fallback permitted")
            result["status"] = "completed"
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
        result["retrieval_seconds"] = perf_counter() - started
        records[key] = result
        write_json(path, {"identity": identity, "records": list(records.values())})
    if not path.exists():
        write_json(path, {"identity": identity, "records": []})
    units = {unit["source_id"]: unit for unit in corpus["units"]}
    payloads = {}
    for case_id, item in inputs.items():
        payloads[case_id] = {}
        for policy in config["evidence_policies"]:
            try:
                if policy == "reference_evidence":
                    payload = deepcopy(item["reference_payload"])
                    selection = {
                        "policy": "frozen_historical_reference_control",
                        "supplied_source_ids": [
                            s["source_id"] for s in payload["guideline_evidence"]
                        ],
                    }
                    if (
                        len(payload["guideline_evidence"]) > config["top_k"]
                        or len(json_bytes(payload["guideline_evidence"]))
                        > config["evidence_max_bytes"]
                    ):
                        raise ValueError(
                            "Frozen reference control exceeds the common evidence budget"
                        )
                else:
                    ranks = [
                        row
                        for row in records.values()
                        if row["case_id"] == case_id and row["evidence_policy"] == policy
                    ]
                    payload, selection = build_selected_payload(
                        item["payload"], units, ranks, config
                    )
                payloads[case_id][policy] = {
                    "status": "completed",
                    "payload": payload,
                    "input_sha256": digest(payload),
                    "selection": selection,
                }
            except Exception as exc:
                payloads[case_id][policy] = {
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                }
    write_json(output / "payloads.json", payloads)
    write_json(
        freeze_path,
        {
            "identity": identity,
            "artifacts": {
                name: sha256_bytes((output / name).read_bytes()) for name in artifact_names
            },
        },
    )
    return payloads


def run_condition(config, model, payload, protocol, post=local_post, api=None):
    if api is None:
        from occupational_fitness_rag.evaluation import passage_judgment as api
    require_local_url(config["endpoint"])
    started = perf_counter()
    result = {
        "status": "failed",
        "attempts": [],
        "input_snapshot": deepcopy(payload),
        "support_review": "pending_independent_review",
        "recovered_after_validation_failure": False,
    }
    if len(json_bytes(payload)) > config["prompt_max_bytes"]:
        return {**result, "error": "Payload exceeds the frozen byte limit", "seconds": 0.0}
    try:
        body = api.build_request(config, model, payload, protocol)
    except Exception as exc:
        return {
            **result,
            "error": f"{type(exc).__name__}: {exc}",
            "seconds": perf_counter() - started,
        }
    for index in range(config["max_validation_repairs"] + 1):
        attempt_started = perf_counter()
        record = {
            "number": index + 1,
            "request": deepcopy(body),
            "request_sha256": digest(body),
            "request_bytes": len(json_bytes(body)),
            "status": "failed",
        }
        raw, phase = None, "request"
        try:
            if record["request_bytes"] > config["request_max_bytes"]:
                raise ValueError("Complete serialized request exceeds the frozen byte limit")
            raw = post(config["endpoint"], "/api/chat", body, timeout=config["timeout_seconds"])
            record["raw_response"] = raw
            phase = "provider_response"
            if (
                not isinstance(raw, dict)
                or not isinstance(raw.get("message"), dict)
                or not isinstance(raw["message"].get("content"), str)
            ):
                raise ValueError("Malformed local model response envelope")
            record["token_counts"] = {
                key: raw.get(key)
                for key in ["prompt_eval_count", "eval_count", "prompt_eval_cached_count"]
            }
            record["context_truncation_status"] = (
                "Token counts alone do not prove the absence of silent truncation"
            )
            if raw.get("done") is False or raw.get("done_reason") == "length":
                raise ValueError("Incomplete model output; no repair for truncation")
            if (
                raw.get("prompt_eval_count") is not None
                and raw["prompt_eval_count"] + config["output_tokens"] >= config["context_length"]
            ):
                raise ValueError("Measured prompt tokens leave insufficient context reserve")
            phase = "structural_validation"
            answer = api.parse_response(raw, payload, protocol)
            phase = "provenance"
            locations = api.criterion_locations(answer, payload)
            phase = "consistency_flags"
            flags = api.output_consistency_flags(answer, payload)
            record.update(
                status="completed",
                answer=answer.model_dump(mode="json"),
                criterion_locations=locations,
                output_consistency_flags=flags,
            )
            result.update(
                status="completed",
                answer=record["answer"],
                criterion_locations=locations,
                output_consistency_flags=flags,
            )
            result.pop("error", None)
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
            record["failure_stage"] = phase
            result["error"] = record["error"]
        record["seconds"] = perf_counter() - attempt_started
        result["attempts"].append(record)
        if record["status"] == "completed":
            break
        if (
            raw is None
            or phase != "structural_validation"
            or index == config["max_validation_repairs"]
        ):
            break
        body = deepcopy(body)
        body["messages"].extend(
            [
                {"role": "assistant", "content": raw.get("message", {}).get("content", "")},
                {
                    "role": "user",
                    "content": "The previous output failed structural validation: "
                    + record["error"]
                    + ". Correct only the output contract using the SAME original patient facts and evidence. Do not invent a source, passage, quotation or fact. The validator supplies no correct outcome. No semantic consistency flag is a repair instruction.",
                },
            ]
        )
    result["seconds"] = perf_counter() - started
    result["recovered_after_validation_failure"] = (
        result["status"] == "completed" and len(result["attempts"]) > 1
    )
    return result


def write_report(output, rows, planned_keys):
    keys = {condition_key(row) for row in rows}
    if len(keys) != len(rows) or not keys <= planned_keys:
        raise ValueError("Duplicate or unexpected judgment condition")
    groups = defaultdict(list)
    for row in rows:
        groups[row["model"], row["evidence_policy"], row["protocol"]].append(row)
    metrics = []
    for (model, policy, protocol), group in sorted(groups.items()):
        for stage in ["first_attempt", "final_with_repair"]:
            answers = [
                (row.get("attempts") or [{}])[0] if stage == "first_attempt" else row
                for row in group
            ]
            valid = [answer.get("status") == "completed" for answer in answers]
            correct = sum(
                ok and answer["answer"]["assessment_outcome"] == row["reference_outcome"]
                for row, answer, ok in zip(group, answers, valid, strict=True)
            )
            metrics.append(
                {
                    "model": model,
                    "evidence_policy": policy,
                    "protocol": protocol,
                    "stage": stage,
                    "conditions": len(group),
                    "valid": sum(valid),
                    "failures": len(group) - sum(valid),
                    "correct": correct,
                    "engineering_reference_agreement": correct / len(group),
                    "recoveries": sum(
                        row.get("recovered_after_validation_failure", False) for row in group
                    )
                    if stage == "final_with_repair"
                    else 0,
                    "model_attempts": sum(
                        len(row.get("attempts", []))
                        if stage == "final_with_repair"
                        else bool(row.get("attempts"))
                        for row in group
                    ),
                    "consistency_flagged_conditions": sum(
                        bool(answer.get("output_consistency_flags")) for answer in answers
                    ),
                }
            )
    summary = {
        "phase": "targeted_diagnostic_development_set",
        "recorded_conditions": len(rows),
        "planned_conditions": len(planned_keys),
        "execution_status": "completed" if keys == planned_keys else "partial",
        "metrics": metrics,
        "failures": dict(
            Counter(
                row.get("error", "Unspecified failure")
                for row in rows
                if row["status"] != "completed"
            )
        ),
        "clinical_accuracy": None,
        "production_change": False,
        "warning": "Known-error development pilot; not independent validation. Exact source provenance and output consistency flags do not establish clinical support. First attempts and bounded structural repairs are reported separately.",
    }
    write_json(output / "summary.json", summary)
    if metrics:
        with (output / "summary.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(metrics[0]))
            writer.writeheader()
            writer.writerows(metrics)
    selectors = "".join(
        "<label>"
        + label
        + '<select data-field="'
        + field
        + '">'
        + "".join(
            "<option>" + escape(value) + "</option>" for value in sorted({row[key] for row in rows})
        )
        + "</select></label>"
        for field, label, key in [("case", "Case", "case_id"), ("model", "Model", "model")]
    )
    table = "".join(
        f"<tr><td>{escape(m['model'])}</td><td>{m['evidence_policy']}</td><td>{m['protocol']}</td><td>{m['stage']}</td><td>{m['valid']}/{m['conditions']}</td><td>{m['engineering_reference_agreement']:.1%}</td><td>{m['consistency_flagged_conditions']}</td></tr>"
        for m in metrics
    )
    cards = []
    for row in rows:
        answer = row.get("answer", {})
        evidence = row.get("input_snapshot", {}).get("guideline_evidence", [])
        passages = "".join(
            f"<details><summary>{escape(source['source_id'])} · {escape(source['module'])} · Section {escape(source['section'])} · PDF {source['pdf_page']}</summary><blockquote>{escape(source['source_text'])}</blockquote></details>"
            for source in evidence
        )
        cards.append(
            f'<article data-case="{escape(row["case_id"])}" data-model="{escape(row["model"])}"><h3>{row["evidence_policy"]} / {row["protocol"]}</h3><p>{escape(row["case_id"])} · {escape(row["model"])} · {row["status"]}</p><p>Proposal: {escape(answer.get("assessment_outcome", "Unavailable"))}<br>Engineering reference: {escape(row["reference_outcome"])}</p><p>{escape(answer.get("explanation", row.get("error", "")))}</p><p>Output consistency flags (not clinical verdicts): {escape(json.dumps(row.get("output_consistency_flags", [])))}</p><details><summary>Criterion checks and original locations</summary><pre>{escape(json.dumps(row.get("criterion_locations", []), indent=2))}</pre></details><details><summary>Frozen patient inputs and selection audit</summary><pre>{escape(json.dumps({"patient": {k: v for k, v in row.get("input_snapshot", {}).items() if k != "guideline_evidence"}, "selection": row.get("selection")}, indent=2))}</pre></details>'
            + passages
            + f"<details><summary>All requests, raw responses and failed attempts</summary><pre>{escape(json.dumps(row.get('attempts', []), indent=2))}</pre></details></article>"
        )
    html = (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Passage judgment comparison | Occupational Fitness Platform</title><style>body{font:14px/1.65 system-ui;background:#f4f6f8;color:#233647;margin:0}header{background:#233647;color:white;padding:26px 4vw}main{max-width:1500px;margin:auto;padding:26px}.scroll{overflow:auto}table{border-collapse:collapse;background:white;width:100%}th,td{padding:12px;border-bottom:1px solid #dce3e9;text-align:left}.cards{display:grid;grid-template-columns:1fr 1fr;gap:20px}article{border:1px solid #dce3e9;background:white;padding:22px;border-radius:8px}article[hidden]{display:none}pre,blockquote{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f7fa;padding:14px}summary{cursor:pointer;padding:8px 0}label{display:inline-block;margin:20px}select{display:block;padding:8px}.notice{background:#fff7e9;padding:18px}@media(max-width:850px){.cards{grid-template-columns:1fr}main{padding:12px}}</style><header>OCCUPATIONAL FITNESS PLATFORM<h1>Passage judgment comparison</h1></header><main>'
        + f'<p>{len(rows)}/{len(planned_keys)} conditions · {summary["execution_status"]}</p><p class="notice">{escape(summary["warning"])}</p><p>Fresh, pinned embeddings and hybrid RRF. Top 10 rankings retained; Top 5 shared documented-module allocation and common byte limits supply judgment evidence. Reference evidence is a separate diagnostic control.</p><div class="scroll"><table><thead><tr><th>Model</th><th>Query policy</th><th>Protocol</th><th>Stage</th><th>Valid</th><th>Engineering reference agreement</th><th>Flagged</th></tr></thead><tbody>'
        + table
        + "</tbody></table></div>"
        + selectors
        + '<div class="cards">'
        + "".join(cards)
        + '</div><p><a href="results.jsonl">Original calls</a> · <a href="retrieval.json">Rankings and queries</a> · <a href="summary.json">Metrics</a> · <a href="manifest.json">Manifest</a> · <a href="source_snapshot.json">Code and dependency snapshot</a> · <a href="retrieval_freeze.json">Evidence fingerprints</a> · <a href="paired_analysis.json">Paired analysis (after export)</a> · <a href="review.csv">Review worksheet (after export)</a></p><script>function f(){const s=[...document.querySelectorAll("select")];document.querySelectorAll("article").forEach(a=>a.hidden=s.some(x=>a.dataset[x.dataset.field]!==x.value))}document.querySelectorAll("select").forEach(s=>s.addEventListener("change",f));f();</script></main></html>'
    )
    (output / "index.html").write_text(html, encoding="utf-8")
    return summary


def run_comparison(
    config_path,
    resume=False,
    max_conditions=None,
    retrieval_only=False,
    post=local_post,
    get=local_get,
    api=None,
):
    if max_conditions is not None and (isinstance(max_conditions, bool) or max_conditions < 0):
        raise ValueError("max_conditions must be non-negative")
    config_path = Path(config_path)
    config_text = config_path.read_text(encoding="utf-8")
    config = yaml.safe_load(config_text)
    validate_config(config)
    baseline, output = Path(config["baseline_dir"]).resolve(), Path(config["output"]).resolve()
    if output == baseline or output.is_relative_to(baseline) or baseline.is_relative_to(output):
        raise ValueError("Experiment output must be isolated from historical baseline files")
    # Validate appendability before network calls, manifests or derived reports change.
    read_records(output / "results.jsonl")
    corpus, inputs, fingerprints = load_frozen_inputs(
        baseline, config["case_ids"], config.get("corpus_override")
    )
    environment = pinned_environment(config, get)
    sources = source_snapshot(config_text)
    planned = list(
        product(
            config["models"],
            config["case_ids"],
            config["evidence_policies"],
            config["protocols"],
            range(config["repeats"]),
        )
    )
    identity_data = {
        "config": config,
        "config_sha256": sha256_bytes(config_text.encode("utf-8")),
        "sources_sha256": digest(sources),
        "historical_fingerprints": fingerprints,
        "environment": environment,
        "patient_inputs_sha256": digest(inputs),
        "corpus_sha256": corpus["corpus_sha256"],
        "planned_keys": planned,
    }
    manifest = {
        **identity_data,
        "identity": digest(identity_data),
        "planned_conditions": len(planned),
        "phase": "targeted_diagnostic_development_set",
        "production_change": False,
        "clinical_review": "pending",
        "historical_model_digests": json.loads(
            (baseline / "model_inventory.json").read_text(encoding="utf-8")
        ),
        "model_revision_warning": "Judge revisions are pinned for contemporaneous controls; historical judgment agreement must not be attributed solely to this intervention.",
    }
    output.mkdir(parents=True, exist_ok=True)
    lock = output / ".run.lock"
    try:
        with lock.open("x", encoding="ascii") as stream:
            stream.write(str(os.getpid()))
    except FileExistsError as exc:
        raise ValueError("Another run or an unreviewed stale run lock exists") from exc
    try:
        manifest_path = output / "manifest.json"
        if manifest_path.exists():
            if not resume:
                raise ValueError("Existing experiment requires --resume or a new output")
            if json.loads(manifest_path.read_text(encoding="utf-8")) != json.loads(
                json.dumps(manifest)
            ):
                raise ValueError(
                    "Experiment identity changed; preserve existing output and use a new directory"
                )
            if json.loads(
                (output / "source_snapshot.json").read_text(encoding="utf-8")
            ) != json.loads(json.dumps(sources)):
                raise ValueError("First-party source or dependency snapshot changed")
            if json.loads((output / "frozen_inputs.json").read_text(encoding="utf-8")) != inputs:
                raise ValueError("Frozen patient source snapshot changed")
            if json.loads((output / "corpus.json").read_text(encoding="utf-8")) != corpus:
                raise ValueError("Frozen corpus snapshot changed")
        else:
            if any(path.name != ".run.lock" for path in output.iterdir()):
                raise ValueError("Non-empty output lacks a manifest; refuse to overwrite artifacts")
            write_json(manifest_path, manifest)
            write_json(output / "source_snapshot.json", sources)
            write_json(output / "frozen_inputs.json", inputs)
            write_json(output / "corpus.json", corpus)
        rows = read_records(output / "results.jsonl")
        planned_keys = set(planned)
        write_report(output, rows, planned_keys)
        payloads = freeze_retrieval(config, corpus, inputs, output, manifest["identity"], post, get)
        if retrieval_only:
            return {
                "retrieval_frozen": True,
                "judgment_conditions": len(rows),
                "planned_conditions": len(planned),
                "output": str(output),
            }
        done = {condition_key(row) for row in rows}
        added = 0
        for model, case_id, policy, protocol, repeat in planned:
            key = (model, case_id, policy, protocol, repeat)
            if key in done:
                continue
            if max_conditions is not None and added >= max_conditions:
                break
            pinned_environment(config, get)
            selected = payloads[case_id][policy]
            row = {
                "model": model,
                "model_digest": environment["model_digests"][model],
                "case_id": case_id,
                "evidence_policy": policy,
                "protocol": protocol,
                "repeat": repeat,
                "experiment_identity": manifest["identity"],
            }
            if selected["status"] != "completed":
                row.update(
                    status="failed",
                    error="Retrieval preparation failed: " + selected["error"],
                    attempts=[],
                    seconds=0.0,
                )
            else:
                row.update(selection=selected["selection"], input_sha256=selected["input_sha256"])
                row.update(run_condition(config, model, selected["payload"], protocol, post, api))
            row["reference_outcome"] = inputs[case_id]["reference_outcome"]
            row["reference_agreement"] = (
                row["status"] == "completed"
                and row["answer"]["assessment_outcome"] == row["reference_outcome"]
            )
            # Re-read before append: a partial line must never be concatenated or ignored.
            observed = read_records(output / "results.jsonl")
            if observed != rows:
                raise ValueError("Judgment records changed during this exclusive run")
            with (output / "results.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
            rows.append(row)
            done.add(key)
            added += 1
            write_report(output, rows, planned_keys)
            print(
                f"Recorded {len(rows)}/{len(planned)}: {case_id} {model} {policy} {protocol} {row['status']}",
                flush=True,
            )
        return write_report(output, rows, planned_keys)
    finally:
        lock.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/experiments/passage_comparison_clean.yaml")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-conditions", type=int)
    parser.add_argument("--retrieval-only", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            run_comparison(args.config, args.resume, args.max_conditions, args.retrieval_only),
            indent=2,
        )
    )
