"""Paired retrieval-to-judgment experiment, isolated from production assessments."""

from __future__ import annotations

import csv
import json
import math
import random
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from urllib.request import ProxyHandler, Request, build_opener

import yaml

from occupational_fitness_rag.case_intake.model_intake import model_intake
from occupational_fitness_rag.case_intake.semantic_review import semantic_review
from occupational_fitness_rag.case_intake.traceable import extract_traceable_file
from occupational_fitness_rag.evaluation.comparison_corpus import (
    MODULES,
    build_comparison_corpus,
    verify_corpus,
)
from occupational_fitness_rag.evaluation.model_judgment import ExperimentalJudgment
from occupational_fitness_rag.indexing.base import StoredDocument
from occupational_fitness_rag.ingestion.source_catalogue import SourceCatalogue
from occupational_fitness_rag.llm import require_local_url
from occupational_fitness_rag.pipeline.config import load_workflow_config
from occupational_fitness_rag.provenance import digest, write_json
from occupational_fitness_rag.red_flag import RedFlagEvaluator
from occupational_fitness_rag.retrieval.bm25 import rank_bm25
from occupational_fitness_rag.retrieval.fusion import reciprocal_rank_fusion
from occupational_fitness_rag.retrieval.graph_local import expand_local_graph
from occupational_fitness_rag.rules.engine import RuleBook

METHODS = {
    "vector",
    "bm25",
    "hybrid",
    "graph_local",
    "lightrag",
    "graphrag",
    "no_evidence",
    "reference_evidence",
}
SYSTEM = """You propose an experimental commercial-driver fitness assessment in English.
Use only verified_patient_facts as established facts; nurse_note provides context,
not permission to promote uncertain, negated, historical or other-person findings.
Only keys in verified_patient_facts may be cited as fact_fields. A field mentioned
in nurse_note but absent from verified_patient_facts remains unverified. Do not
assume an unverified negative finding or declare an unassessed module normal.
Use only supplied original guideline_evidence. Do not invent licensing standards.
Missing information is not normal. Do not infer blackout from tiredness alone.
Return the requested JSON with assessment_outcome, explanation, source_ids and
fact_fields. Cite only supplied IDs and fields. A reference to non-insulin treatment
alone does not establish that all conditional licence qualifications are met.
When multiple modules are assessed, distinguish an established restrictive criterion
from an unresolved module; explain both rather than hiding established findings.
With no guideline evidence, abstain if a standard cannot be established; empty source_ids
are allowed only in that control. This proposal is not a clinical licensing decision."""


def local_post(endpoint, path, body, timeout=120):
    request = Request(
        require_local_url(endpoint) + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with build_opener(ProxyHandler({})).open(request, timeout=timeout) as response:
        return json.load(response)


def load_labels(root, config, workflow):
    rows = []
    selections = (
        json.loads((root / config["reference_evidence"]).read_text())["cases"]
        if config.get("reference_evidence")
        else {}
    )
    for cohort, filename in config["cohorts"].items():
        fixture = json.loads((root / filename).read_text(encoding="utf-8"))
        if cohort == "engineering":
            entries = fixture["cases"]
        else:
            entries = [
                dict(
                    value,
                    case_id=key,
                    input=f"data/cases/validation_nurse_notes/{key}.txt",
                    module="all",
                    expected_outcome=value["overall_outcome"],
                )
                for key, value in fixture.items()
            ]
        for entry in entries:
            path = (root / entry["input"]).resolve()
            if (
                not path.is_relative_to((root / "data/cases").resolve())
                or "sealed_review" in path.parts
            ):
                raise ValueError(
                    "Experimental case path is outside the permitted non-sealed cohort"
                )
            sources = entry.get(
                "source_ids",
                sorted(
                    {
                        sid
                        for r in workflow.book.rules
                        if r["rule_id"] in entry.get("triggered_rules", [])
                        for sid in r["source_ids"]
                    }
                ),
            )
            sources = selections.get(entry["case_id"], sources)
            if set(sources) - set(workflow.catalogue.units):
                raise ValueError("Reference evidence selection names an unknown canonical source")
            rows.append(
                dict(
                    entry,
                    cohort=cohort,
                    reference_source_ids=sources,
                    label_origin="provisional_engineering_fixture",
                    clinical_review_status="pending",
                )
            )
    if len({x["case_id"] for x in rows}) != len(rows):
        raise ValueError("Duplicate case IDs across comparison cohorts")
    return rows


def freeze_case(workflow, label, directory):
    target = directory / (label["case_id"] + ".json")
    input_path = workflow.root / label["input"]
    identity = digest(
        [
            input_path.read_bytes().hex(),
            workflow.book.sha256,
            workflow.config.llm.model_dump(),
            label["module"],
        ]
    )
    if target.exists():
        record = json.loads(target.read_text(encoding="utf-8"))
        if record["identity"] != identity or digest(record["case"]) != record["case_sha256"]:
            raise ValueError("Frozen case changed; use a new experiment output directory")
        return record
    case = extract_traceable_file(
        input_path,
        workflow.book.field_specs,
        None if label["module"] == "all" else [label["module"]],
    )
    case, intake = model_intake(case, workflow.book.field_specs, workflow.config.llm)
    case = case.model_copy(update={"extraction_metadata": intake})
    case, review = semantic_review(case, workflow.book.field_specs, workflow.config.llm)
    rules = workflow.red_flag.evaluate(case)  # No retrieval or route-model feedback.
    record = {
        "identity": identity,
        "case": case.model_dump(mode="json"),
        "case_sha256": digest(case),
        "intake": intake,
        "semantic_review": review,
        "rule_outcome": rules.assessment_outcome,
    }
    write_json(target, record)
    return record


class CorpusRetriever:
    """Real Ollama dense embeddings, BM25 and the existing graph ranker."""

    def __init__(self, workflow, corpus, config, output):
        self.workflow, self.corpus, self.config = workflow, corpus, config
        self.units = {u["source_id"]: u for u in corpus["units"]}
        self.docs = [
            StoredDocument(
                u["source_id"],
                u["evidence_text"],
                {
                    "module": u["module"],
                    "source_ids_csv": u["source_id"],
                },
            )
            for u in corpus["units"]
        ]
        self.cache = output / "embeddings.json"
        self.vectors = None
        self.catalogue = SimpleNamespace(units=self.units)

    def embed(self, text):
        result = local_post(
            self.config["endpoint"],
            "/api/embed",
            {
                "model": self.config["embedding_model"],
                "input": text,
                "truncate": False,
            },
        )["embeddings"]
        return result

    def ensure_vectors(self):
        if self.vectors is not None:
            return
        identity = digest([self.corpus["corpus_sha256"], self.config["embedding_model"]])
        if self.cache.exists():
            cache = json.loads(self.cache.read_text())
            if cache["identity"] != identity:
                raise ValueError("Embedding cache identity mismatch")
            self.vectors = cache["vectors"]
        else:
            vectors = []
            for start in range(0, len(self.docs), 8):
                vectors.extend(self.embed([d.text for d in self.docs[start : start + 8]]))
            self.vectors = vectors
            write_json(self.cache, {"identity": identity, "vectors": vectors})

    def retrieve(self, query, module, method, k):
        docs = [d for d in self.docs if d.metadata["module"] == module]
        sparse = rank_bm25(query, docs, 30) if method != "vector" else []
        dense = []
        if method != "bm25":
            self.ensure_vectors()
            q = self.embed([query])[0]
            qnorm = math.sqrt(sum(v * v for v in q))
            for doc, vector in zip(self.docs, self.vectors, strict=True):
                if doc.metadata["module"] != module:
                    continue
                norm = math.sqrt(sum(v * v for v in vector))
                score = sum(a * b for a, b in zip(q, vector, strict=True)) / max(
                    qnorm * norm, 1e-12
                )
                dense.append(StoredDocument(doc.chunk_id, doc.text, doc.metadata, score))
            dense.sort(key=lambda d: (-d.vector_score, d.chunk_id))
        if method == "vector":
            return [d.chunk_id for d in dense[:k]]
        hits = reciprocal_rank_fusion(dense[:20], sparse, 60)
        if method == "graph_local":
            hits = expand_local_graph(
                hits, docs, self.workflow.book, self.catalogue, module, query, k
            )
        return [h.doc.chunk_id for h in hits[:k]]


def make_payload(case, units, ids, config):
    facts = {
        name: {"value": fact["value"], "patient_quotes": [s["quote"] for s in fact["evidence"]]}
        for name, fact in case["facts"].items()
        if fact["status"] == "present"
    }
    payload = {
        "licence_context": "commercial",
        "modules": case["modules_requested"],
        "nurse_note": case["source_text"],
        "verified_patient_facts": facts,
        "guideline_evidence": [],
    }
    excluded = []
    for sid in ids:
        u = units[sid]
        passage = {
            "source_id": sid,
            "section": u["section"],
            "pdf_page": u["pdf_page"],
            "printed_page": u["printed_page"],
            "source_text": u["evidence_text"],
        }
        candidate = [*payload["guideline_evidence"], passage]
        if len(json.dumps(candidate).encode()) > config["evidence_max_bytes"]:
            excluded.append(sid)
        else:
            payload["guideline_evidence"] = candidate
    return payload, excluded


def validate_answer(answer, payload, method):
    allowed = {u["source_id"] for u in payload["guideline_evidence"]}
    if set(answer.source_ids) - allowed or set(answer.fact_fields) - set(
        payload["verified_patient_facts"]
    ):
        raise ValueError("Model cited a source or patient fact that was not supplied")
    if method != "no_evidence" and not answer.source_ids:
        raise ValueError("Evidence-grounded judgment requires a supplied source citation")
    if any("\u3400" <= c <= "\u9fff" for c in answer.explanation):
        raise ValueError("Model judgment must be in English")


def bounded_answer_schema(payload):
    """Constrain identifiers, never the predicted clinical outcome or explanation."""
    schema = ExperimentalJudgment.model_json_schema()
    schema["properties"]["explanation"]["maxLength"] = 2000
    for field, values in {
        "source_ids": [u["source_id"] for u in payload["guideline_evidence"]],
        "fact_fields": list(payload["verified_patient_facts"]),
    }.items():
        if values:
            schema["properties"][field]["items"] = {"type": "string", "enum": values}
            schema["properties"][field]["maxItems"] = min(len(values), 30)
        else:
            schema["properties"][field]["maxItems"] = 0
    return schema


def judgment_request(config, model, payload):
    body = {
        "model": model,
        "stream": False,
        "format": bounded_answer_schema(payload),
        "keep_alive": "10m",
        "options": {
            "temperature": 0,
            "seed": 0,
            "num_ctx": config["context_length"],
            "num_predict": config["output_tokens"],
        },
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    }
    if model.startswith("qwen"):
        body["think"] = False
    return body


def support_proxy(answer, payload):
    """A numeric traceability flag, explicitly not an entailment/clinical score."""
    available = (
        json.dumps(payload["verified_patient_facts"])
        + " "
        + " ".join(
            p["source_text"]
            for p in payload["guideline_evidence"]
            if p["source_id"] in answer.source_ids
        )
    )

    def numeric(text):
        return set(re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?(?:/\d+)?", text))

    explanation = re.sub(r"AFTD2022-[A-Za-z0-9-]+", "", answer.explanation)
    return {
        "unsupported_numeric_tokens": sorted(numeric(explanation) - numeric(available)),
        "citation_ids_valid": True,
        "entailment": None,
        "interpretation": "Heuristic review flags only; not a faithfulness score",
    }


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["cohort"], row["model"], row["method"])].append(row)
    metrics = []
    for (cohort, model, method), group in sorted(groups.items()):
        accepted = [r for r in group if r["status"] == "completed"]
        matrix = Counter(
            (r["reference_outcome"], r["answer"]["assessment_outcome"]) for r in accepted
        )
        classes = sorted({r["reference_outcome"] for r in group})
        f1s = []
        for cls in classes:
            tp = matrix[cls, cls]
            fp = sum(v for (a, b), v in matrix.items() if b == cls and a != cls)
            # Failed runs are counted as missed classifications, not removed.
            fn = sum(r["reference_outcome"] == cls for r in group) - tp
            f1s.append(2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0)
        recalls = [
            r["retrieval_recall_at_5"] for r in group if r.get("retrieval_recall_at_5") is not None
        ]
        recalls10 = [
            r["retrieval_recall_at_10"]
            for r in group
            if r.get("retrieval_recall_at_10") is not None
        ]
        patients = defaultdict(list)
        for row in group:
            patients[row["case_id"]].append(float(row.get("reference_agreement", False)))
        values = [sum(v) / len(v) for v in patients.values()]
        rng = random.Random(0)
        samples = sorted(sum(rng.choices(values, k=len(values))) / len(values) for _ in range(1000))
        metrics.append(
            {
                "cohort": cohort,
                "model": model,
                "method": method,
                "runs": len(group),
                "accepted": len(accepted),
                "failures": len(group) - len(accepted),
                "agreement_all_runs": sum(r.get("reference_agreement", False) for r in group)
                / len(group),
                "case_cluster_bootstrap_95ci": [samples[25], samples[974]],
                "macro_f1": sum(f1s) / len(f1s),
                "retrieval_recall_at_5": sum(recalls) / len(recalls) if recalls else None,
                "retrieval_recall_at_10": sum(recalls10) / len(recalls10) if recalls10 else None,
                "complete_evidence_coverage_at_5": sum(value == 1 for value in recalls)
                / len(recalls)
                if recalls
                else None,
                "excess_abstentions": sum(
                    r["answer"]["assessment_outcome"] == "insufficient_information"
                    and r["reference_outcome"] != "insufficient_information"
                    for r in accepted
                ),
                "mean_seconds": sum(r["seconds"] for r in group) / len(group),
                "confusion_matrix": [
                    {"reference": a, "prediction": b, "count": n}
                    for (a, b), n in sorted(matrix.items())
                ],
            }
        )
    paired = []
    by_key = {(r["case_id"], r["model"], r["repeat"], r["method"]): r for r in rows}
    for r in rows:
        base = by_key.get((r["case_id"], r["model"], r["repeat"], "hybrid"))
        if base and r["status"] == base["status"] == "completed" and r["method"] != "hybrid":
            paired.append(
                {
                    "case_id": r["case_id"],
                    "model": r["model"],
                    "repeat": r["repeat"],
                    "method": r["method"],
                    "transition": "wrong_to_correct"
                    if r["reference_agreement"] and not base["reference_agreement"]
                    else "correct_to_wrong"
                    if base["reference_agreement"] and not r["reference_agreement"]
                    else "unchanged_correctness",
                    "hybrid_outcome": base["answer"]["assessment_outcome"],
                    "method_outcome": r["answer"]["assessment_outcome"],
                }
            )
    return {
        "metrics": metrics,
        "paired_transitions": paired,
        "clinical_accuracy": None,
        "reference_status": "provisional engineering labels; no clinician gold",
    }


def run_comparison(config_path, output=None, resume=False, stage="all", limit=None):
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    if not set(config["methods"]) <= METHODS or config["repeats"] < 1:
        raise ValueError("Invalid experimental methods or repeats")
    require_local_url(config["endpoint"])
    workflow_config, project_root = load_workflow_config(config["workflow_config"])
    book = RuleBook(project_root / workflow_config.rules)
    catalogue = SourceCatalogue(project_root, project_root / workflow_config.catalogue)
    if catalogue.ruleset_sha256 != book.sha256:
        raise ValueError("Production rule and source catalogue versions disagree")
    workflow = SimpleNamespace(
        root=project_root,
        config=workflow_config,
        book=book,
        catalogue=catalogue,
        red_flag=RedFlagEvaluator(book),
    )
    root = workflow.root
    output = Path(output or root / config["output"]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if not resume and (output / "results.jsonl").exists():
        raise ValueError("Output already contains judgments; use --resume or a new directory")
    corpus_path = output / "corpus.json"
    corpus = (
        json.loads(corpus_path.read_text(encoding="utf-8"))
        if resume and corpus_path.exists()
        else build_comparison_corpus(workflow, corpus_path)
    )
    verify_corpus(root, corpus)
    labels = load_labels(root, config, workflow)
    if limit:
        # Pilot: deterministic selection covering the five conditions first.
        selected = []
        for module in MODULES:
            selected.extend(next(([x] for x in labels if x["module"] == module), []))
        selected.extend(x for x in labels if x not in selected)
        labels = selected[:limit]
    manifest = {
        "config": config,
        "corpus_sha256": corpus["corpus_sha256"],
        "label_sha256": digest(labels),
        "system_sha256": digest(SYSTEM),
        "seed": 0,
        "planned_runs": len(labels)
        * len(config["models"])
        * len(config["methods"])
        * config["repeats"],
        "code_sha256": digest(
            {
                p.name: p.read_text(encoding="utf-8")
                for p in Path(__file__).parent.glob("*comparison*.py")
            }
        ),
        "clinical_review_status": "pending",
        "production_mutation": False,
    }
    manifest["code_sha256"] = digest(
        {
            p.name: p.read_text(encoding="utf-8")
            for p in Path(__file__).parent.glob("*.py")
            if p.name
            in {
                "comparison_corpus.py",
                "judgment_comparison.py",
                "graph_worker.py",
                "model_judgment.py",
            }
        }
    )
    manifest_path = output / "manifest.json"
    if resume and manifest_path.exists():
        previous = json.loads(manifest_path.read_text())
        if any(
            previous.get(key) != manifest[key]
            for key in ["config", "label_sha256", "corpus_sha256", "system_sha256", "code_sha256"]
        ):
            raise ValueError("Experiment inputs changed; use a separate output directory")
    write_json(manifest_path, manifest)
    write_json(output / "labels.json", labels)
    if stage == "corpus":
        return {"corpus": str(corpus_path), "units": len(corpus["units"]), "cases": len(labels)}
    with build_opener(ProxyHandler({})).open(
        config["endpoint"] + "/api/tags", timeout=10
    ) as response:
        installed = json.load(response)["models"]
    required_models = set(config["models"]) | {
        config["graph_model"],
        config["embedding_model"],
        workflow.config.llm.model,
    }
    inventory = {}
    for name in sorted(required_models):
        full_name = name if ":" in name else name + ":latest"
        match = next((m for m in installed if m["name"] == full_name), None)
        if match is None:
            raise ValueError(f"Required experiment model is not installed: {full_name}")
        inventory[name] = match["digest"]
    inventory_path = output / "model_inventory.json"
    if resume and inventory_path.exists() and json.loads(inventory_path.read_text()) != inventory:
        raise ValueError("Installed model weights changed; use a new experiment directory")
    write_json(inventory_path, inventory)
    frozen = {x["case_id"]: freeze_case(workflow, x, output / "frozen_cases") for x in labels}
    write_json(
        output / "label_audit.json",
        [
            {
                "case_id": label["case_id"],
                "cohort": label["cohort"],
                "fixture_outcome": label["expected_outcome"],
                "frozen_rule_outcome": frozen[label["case_id"]]["rule_outcome"],
                "matches_current_rules": label["expected_outcome"]
                == frozen[label["case_id"]]["rule_outcome"],
                "policy": "Mismatch is reported; labels are never rewritten from rules or model outputs",
            }
            for label in labels
        ],
    )
    if stage == "freeze":
        return {"frozen_cases": len(frozen), "output": str(output)}
    queries = [
        {
            "case_id": label["case_id"],
            "module": module,
            "query": frozen[label["case_id"]]["case"]["source_text"],
        }
        for label in labels
        for module in frozen[label["case_id"]]["case"]["modules_requested"]
    ]
    # No label, rule result or expected source enters a retrieval worker request.
    retrieval_file = output / "retrieval.json"
    retrieval = (
        json.loads(retrieval_file.read_text(encoding="utf-8"))
        if resume and retrieval_file.exists()
        else []
    )
    retriever = CorpusRetriever(workflow, corpus, config, output)
    for method in config["methods"]:
        if method in {"no_evidence", "reference_evidence"}:
            continue
        if any(r["method"] == method for r in retrieval):
            continue
        if method in {"lightrag", "graphrag"}:
            request = {
                "config": config,
                "corpus": str(corpus_path),
                "workspace": str(output / "indexes" / corpus["corpus_sha256"][:16] / method),
                "queries": queries,
                "top_k": config["sensitivity_k"],
            }
            request_path, response = (
                output / f"{method}_request.json",
                output / f"{method}_response.json",
            )
            write_json(request_path, request)
            worker = root / "src/occupational_fitness_rag/evaluation/graph_worker.py"
            python = root / f".runtime/{method}/Scripts/python.exe"
            try:
                with (output / f"{method}.log").open("w", encoding="utf-8") as log:
                    subprocess.run(
                        [
                            str(python),
                            str(worker),
                            "--method",
                            method,
                            "--request",
                            str(request_path),
                            "--response",
                            str(response),
                        ],
                        stdout=log,
                        stderr=log,
                        timeout=config["external_timeout_seconds"],
                        check=True,
                    )
                external = json.loads(response.read_text(encoding="utf-8"))
            except Exception as exc:
                external = (
                    json.loads(response.read_text(encoding="utf-8")) if response.exists() else []
                )
                done = {(r["case_id"], r["module"]) for r in external}
                external.extend(
                    dict(
                        q,
                        status="worker_failed",
                        source_ids=[],
                        error=f"{type(exc).__name__}: {exc}",
                    )
                    for q in queries
                    if (q["case_id"], q["module"]) not in done
                )
            retrieval.extend(dict(r, method=method) for r in external)
        else:
            for q in queries:
                started = perf_counter()
                try:
                    ids = retriever.retrieve(
                        q["query"], q["module"], method, config["sensitivity_k"]
                    )
                    retrieval.append(
                        dict(
                            q,
                            method=method,
                            status="completed",
                            source_ids=ids,
                            retrieval_seconds=perf_counter() - started,
                        )
                    )
                except Exception as exc:
                    retrieval.append(
                        dict(
                            q,
                            method=method,
                            status="retrieval_failed",
                            source_ids=[],
                            error=f"{type(exc).__name__}: {exc}",
                        )
                    )
        write_json(retrieval_file, retrieval)
    if stage == "retrieval":
        return {
            "queries": len(retrieval),
            "failures": sum(r["status"] != "completed" for r in retrieval),
        }
    results_path = output / "results.jsonl"
    rows = (
        [json.loads(line) for line in results_path.read_text(encoding="utf-8").splitlines()]
        if resume and results_path.exists()
        else []
    )
    done = {(r["case_id"], r["model"], r["method"], r["repeat"]) for r in rows}
    units = retriever.units
    for model in config["models"]:
        for label in labels:
            frozen_case = frozen[label["case_id"]]
            for method in config["methods"]:
                candidates = [
                    r
                    for r in retrieval
                    if r["case_id"] == label["case_id"] and r["method"] == method
                ]
                ids = []
                # Round-robin rank positions gives every requested module equal opportunity.
                for rank in range(config["sensitivity_k"]):
                    for r in candidates:
                        if rank < len(r["source_ids"]) and r["source_ids"][rank] not in ids:
                            ids.append(r["source_ids"][rank])
                if method == "reference_evidence":
                    ids = label["reference_source_ids"]
                payload, excluded = make_payload(
                    frozen_case["case"], units, ids[: config["top_k"]], config
                )
                supplied = {u["source_id"] for u in payload["guideline_evidence"]}
                covered = {
                    sid for uid in supplied for sid in units[uid].get("covers_source_ids", [uid])
                }
                covered10 = {
                    sid for uid in ids[:10] for sid in units[uid].get("covers_source_ids", [uid])
                }
                expected = set(label["reference_source_ids"])
                for repeat in range(config["repeats"]):
                    key = (label["case_id"], model, method, repeat)
                    if key in done:
                        continue
                    started = perf_counter()
                    row = {
                        "case_id": label["case_id"],
                        "cohort": label["cohort"],
                        "module": label["module"],
                        "model": model,
                        "method": method,
                        "repeat": repeat,
                        "case_sha256": frozen_case["case_sha256"],
                        "prompt_sha256": digest(payload),
                        "input_snapshot": payload,
                        "excluded_source_ids": excluded,
                        "reference_outcome": label["expected_outcome"],
                        "rule_outcome": frozen_case["rule_outcome"],
                        "retrieval_recall_at_5": len(expected & covered) / len(expected)
                        if expected
                        else None,
                        "retrieval_recall_at_10": len(expected & covered10) / len(expected)
                        if expected
                        else None,
                        "strict_source_id_recall_at_5": len(expected & supplied) / len(expected)
                        if expected
                        else None,
                        "support_review": "pending_human_review",
                        "status": "pending",
                    }
                    try:
                        if any(r["status"] != "completed" for r in candidates):
                            raise RuntimeError(
                                "One or more module retrievals failed; no fallback permitted"
                            )
                        if method != "no_evidence" and not supplied:
                            raise ValueError(
                                "No source evidence available for this experimental arm"
                            )
                        encoded = len(json.dumps(payload).encode())
                        if encoded > config["prompt_max_bytes"]:
                            raise ValueError(
                                "Input exceeds the explicit experiment byte budget; no truncation"
                            )
                        request = judgment_request(config, model, payload)
                        row["request_sha256"] = digest(request)
                        raw = local_post(
                            config["endpoint"],
                            "/api/chat",
                            request,
                            timeout=workflow.config.llm.timeout_seconds,
                        )
                        # Preserve the response even when parsing or citation validation fails.
                        row["raw_response"] = raw
                        call = {
                            key: raw.get(key)
                            for key in (
                                "model",
                                "done_reason",
                                "prompt_eval_count",
                                "eval_count",
                                "total_duration",
                            )
                        }
                        row["call"] = call
                        if raw.get("done_reason") == "length" or raw.get("done") is False:
                            raise ValueError(
                                "Model output was incomplete; partial answers rejected"
                            )
                        answer = ExperimentalJudgment.model_validate_json(raw["message"]["content"])
                        if (call.get("prompt_eval_count") or 0) + config["output_tokens"] >= config[
                            "context_length"
                        ]:
                            raise ValueError(
                                "Measured prompt tokens leave insufficient context reserve"
                            )
                        validate_answer(answer, payload, method)
                        row.update(
                            status="completed",
                            answer=answer.model_dump(mode="json"),
                            reference_agreement=answer.assessment_outcome
                            == label["expected_outcome"],
                            model_digest=inventory[model],
                            call=call,
                            support_proxy=support_proxy(answer, payload),
                        )
                    except Exception as exc:
                        row.update(status="failed", error=f"{type(exc).__name__}: {exc}")
                    row["seconds"] = perf_counter() - started
                    rows.append(row)
                    with results_path.open("a", encoding="utf-8") as stream:
                        stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                    # Update a readable report throughout long experiments.
                    if len(rows) % 12 == 0:
                        write_outputs(output, rows)
    return write_outputs(output, rows)


def write_outputs(output, rows):
    from occupational_fitness_rag.evaluation.comparison_report import render_comparison

    summary = summarize(rows)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    summary["planned_runs"] = manifest["planned_runs"]
    summary["recorded_runs"] = len(rows)
    summary["execution_status"] = (
        "completed" if len(rows) == manifest["planned_runs"] else "running"
    )
    write_json(output / "summary.json", summary)
    with (output / "summary.csv").open("w", encoding="utf-8", newline="") as stream:
        metrics = [
            {k: v for k, v in row.items() if k != "confusion_matrix"} for row in summary["metrics"]
        ]
        if metrics:
            writer = csv.DictWriter(stream, fieldnames=list(metrics[0]))
            writer.writeheader()
            writer.writerows(metrics)
    write_json(
        output / "review_queue.json",
        [
            {
                "case_id": r["case_id"],
                "model": r["model"],
                "method": r["method"],
                "repeat": r["repeat"],
                "reason": r.get(
                    "error",
                    "Explanation entailment and provisional outcome require independent review",
                ),
            }
            for r in rows
        ],
    )
    (output / "index.html").write_text(render_comparison(rows, summary), encoding="utf-8")
    return {
        "output": str(output),
        "runs": len(rows),
        "completed": sum(r["status"] == "completed" for r in rows),
        "summary": summary,
    }
