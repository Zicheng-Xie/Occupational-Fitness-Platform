"""Run frozen, resumable live evaluation of 200 complex synthetic nurse notes."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
from pathlib import Path
from time import perf_counter

import yaml

from occupational_fitness_rag.evaluation.judgment_comparison import judgment_request, local_post
from occupational_fitness_rag.evaluation.long_note_study import fact_checks, render, summarize
from occupational_fitness_rag.evaluation.passage_comparison import read_records
from occupational_fitness_rag.indexing.local_chroma import build_local_chroma
from occupational_fitness_rag.ingestion.models import GuidelineChunk
from occupational_fitness_rag.pipeline.workflow import OccupationalFitnessWorkflow
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json
from occupational_fitness_rag.retrieval.engine import RetrievalEngine
from occupational_fitness_rag.settings import RetrievalSettings
from tools.run_frozen_retrieval_judgments import accept_completion, runtime
from tools.run_serial_judgment_queue import process_identity, verify_artifacts

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_bytes())


def append(path, row):
    value = {**row, "record_sha256": digest(row)}
    with Path(path).open("ab") as stream:
        stream.write((json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n").encode())
    return value


def records(path, identity):
    rows = read_records(Path(path))
    for row in rows:
        if row["experiment_identity"] != identity or row["record_sha256"] != digest(
            {k: v for k, v in row.items() if k != "record_sha256"}
        ):
            raise ValueError("A saved observation differs from its experiment or digest")
    return rows


def verify_notes(plan):
    for r in plan["inputs"]:
        path = (ROOT / r["input"]).resolve()
        if (
            not path.is_relative_to(ROOT / "data/cases/complex_nurse_notes")
            or sha256_bytes(path.read_bytes()) != r["sha256"]
        ):
            raise ValueError("Input path or content changed")
    for name, pin in plan["old_notes"].items():
        if sha256_bytes((ROOT / "data/cases/complex_nurse_notes" / name).read_bytes()) != pin:
            raise ValueError("An original note changed")


def freeze(config):
    path = Path(config).resolve()
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    manifest = read(ROOT / cfg["manifest"])
    if digest({k: v for k, v in manifest.items() if k != "identity"}) != manifest["identity"]:
        raise ValueError("Dataset manifest identity differs")
    corpus = read(ROOT / cfg["corpus"])
    verify_artifacts((ROOT / cfg["corpus"]).parent)
    if len(manifest["cases"]) != 200 or len(corpus["units"]) != 88:
        raise ValueError("This protocol requires the complete 200-case/88-original datasets")
    units = {u["source_id"]: u for u in corpus["units"]}
    for u in units.values():
        if u["licence_context"] not in {"commercial", "shared"}:
            raise ValueError("Private-only original in commercial/shared discovery corpus")
        for sid in u.get("covers_source_ids", []):
            child = units[sid]
            if (
                child["module"] != u["module"]
                or child["pdf_page"] != u["pdf_page"]
                or " ".join(child["evidence_text"].split())
                not in " ".join(u["evidence_text"].split())
            ):
                raise ValueError("Coverage mapping lacks same-module/page literal proof")
    base = yaml.safe_load((ROOT / cfg["workflow"]).read_text(encoding="utf-8"))
    profile = json.loads(json.dumps(base))
    profile["project_root"] = "../../.."
    profile["llm"]["narrative_enabled"] = False
    profile["llm"]["model_digest"] = cfg["expected_model_digests"][cfg["judge_model"]]
    profile["retrieval"]["persist_directory"] = ".runtime/complex_long_200/production_chroma"
    output = (ROOT / cfg["output"]).resolve()
    if not output.is_relative_to(ROOT / "outputs/evaluation"):
        raise ValueError("Use an isolated evaluation directory")
    pyfiles = list((ROOT / "src/occupational_fitness_rag").rglob("*.py"))
    pyfiles += [
        ROOT / n
        for n in [
            "tools/run_complex_long_study.py",
            "tools/build_complex_long_cases.py",
            "tools/run_frozen_retrieval_judgments.py",
            "tools/run_serial_judgment_queue.py",
            "tools/prepare_retrieval_judgments.py",
        ]
    ]
    sources = {
        p.relative_to(ROOT).as_posix(): sha256_bytes(p.read_bytes()) for p in sorted(pyfiles)
    }
    data = {
        "kind": "complex_long_200_live_study",
        "config": cfg,
        "config_sha256": sha256_bytes(path.read_bytes()),
        "runtime": runtime(cfg),
        "sources": sources,
        "dataset_identity": manifest["identity"],
        "inputs": manifest["cases"],
        "old_notes": manifest["preexisting_notes_sha256"],
        "gold_sha256": sha256_bytes((ROOT / cfg["gold"]).read_bytes()),
        "gold_value_sha256": manifest["gold_sha256"],
        "corpus_file_sha256": sha256_bytes((ROOT / cfg["corpus"]).read_bytes()),
        "corpus_identity": corpus["corpus_sha256"],
        "workflow_profile": profile,
        "base_workflow_sha256": sha256_bytes((ROOT / cfg["workflow"]).read_bytes()),
        "rules_sha256": sha256_bytes((ROOT / base["rules"]).read_bytes()),
        "catalogue_sha256": sha256_bytes((ROOT / base["catalogue"]).read_bytes()),
        "guideline_sha256": sha256_bytes((ROOT / "data/knowledge/raw/ap_g56_22.pdf").read_bytes()),
        "query_policy": "entire_original_note_no_reference_source_ids",
        "judge_policy": "original_frozen_prompt_actual_intake_facts_round_robin_whole_hybrid_top5",
        "production_change": False,
    }
    plan = {**data, "identity": digest(data)}
    verify_notes(plan)
    return cfg, output, units, plan


def corpus_chunks(units, identity):
    return [
        GuidelineChunk(
            chunk_id="LONG-" + digest([identity, sid])[:24],
            text=u["evidence_text"],
            section=u["section"],
            title=u.get("table_row") or u["section"],
            pages=[u["pdf_page"]],
            metadata={
                "source_id": sid,
                "module": u["module"],
                "licence_context": u["licence_context"],
                "licence_scope": "commercial_compatible",
                "source_version": "AP-G56-22",
                "corpus_sha256": identity,
            },
        )
        for sid, u in units.items()
    ]


def ranked_search(store, note, module, method, identity):
    """This boundary has no label, rule-result or expected-source argument."""
    filters = {
        "module": module,
        "licence_scope": "commercial_compatible",
        "source_version": "AP-G56-22",
        "corpus_sha256": identity,
    }
    engine = RetrievalEngine(
        store,
        RetrievalSettings(
            candidate_k=20,
            bm25_k=30,
            top_k=10,
            use_vector=method != "bm25",
            use_bm25=method != "vector",
        ),
    )
    hits = engine.retrieve(note, filters)
    for h in hits:
        if any(str(h.doc.metadata.get(k)) != v for k, v in filters.items()):
            raise ValueError("Discovery crossed its frozen scope")
    return {
        "source_ids": [h.doc.metadata["source_id"] for h in hits],
        "ranked_candidates": [
            {
                "source_id": h.doc.metadata["source_id"],
                "score": h.score,
                "vector_score": h.vector_score,
                "bm25_score": h.bm25_score,
            }
            for h in hits
        ],
        "filters": filters,
    }


def judgment_payload(case, modules, note, hybrid, units, limit):
    # Rank order and requested modules only. No reference labels or source IDs.
    ordered = []
    for i in range(5):
        for module in modules:
            r = hybrid[(case["case_id"], module)]
            if r["status"] != "completed":
                raise ValueError("A required Hybrid retrieval attempt failed")
            if i < len(r["source_ids"]):
                ordered.append(r["source_ids"][i])
    sources = []
    skipped = []
    for sid in ordered[:5]:
        u = units[sid]
        source = {
            "source_id": sid,
            "module": u["module"],
            "section": u["section"],
            "pdf_page": u["pdf_page"],
            "printed_page": u["printed_page"],
            "source_text": u["evidence_text"],
        }
        if len(json.dumps([*sources, source], ensure_ascii=False).encode()) <= limit:
            sources.append(source)
        else:
            skipped.append(sid)
    if not sources:
        raise ValueError("No whole original survives the common evidence budget")
    prefixes = tuple("cardiovascular." if m == "hypertension" else m + "." for m in modules)
    facts = {
        name: {"value": f["value"], "patient_quotes": [s["quote"] for s in f["evidence"]]}
        for name, f in case["facts"].items()
        if f["status"] == "present" and name.startswith(prefixes)
    }
    return {
        "licence_context": "commercial",
        "modules": modules,
        "nurse_note": note,
        "verified_patient_facts": facts,
        "guideline_evidence": sources,
    }, {
        "selected_before_budget": ordered[:5],
        "skipped_by_budget": skipped,
        "actual_bytes": len(json.dumps(sources, ensure_ascii=False).encode()),
        "policy": "whole_original_top5_no_reference_backfill",
    }


def load_journals(output, plan):
    collections = [
        records(output / name, plan["identity"])
        for name in ("retrieval.jsonl", "workflow.jsonl", "judgments.jsonl")
    ]
    for rows, keys in zip(
        collections, [("case_id", "module", "method"), ("case_id",), ("case_id",)]
    ):
        if len({tuple(r[k] for k in keys) for r in rows}) != len(rows):
            raise ValueError("Duplicate observed conditions")
    allowed = {i["case_id"] for i in plan["inputs"]}
    if any(r["case_id"] not in allowed for rows in collections for r in rows):
        raise ValueError("Foreign case in an observation journal")
    return collections


def checkpoint(output, plan, units):
    retrieval, workflow, judgments = load_journals(output, plan)
    # Open scoring labels after requests/attempts are saved. They never go to
    # ranked_search(), run_file(), judgment_payload() or the model transport.
    gold = read(ROOT / plan["config"]["gold"])
    if digest(gold) != plan["gold_value_sha256"]:
        raise ValueError("Frozen engineering references changed")
    labels = {c["case_id"]: c for c in gold["cases"]}
    for row in workflow:
        if row["status"] == "completed":
            case = read(output / row["bundle"] / "structured_case.json")
            row["fact_checks"] = fact_checks(case["facts"], labels[row["case_id"]]["fact_checks"])
    summary = summarize(retrieval, workflow, judgments, labels, units, plan)
    summary["available_originals_per_module"] = {
        m: sum(u["module"] == m for u in units.values())
        for m in {u["module"] for u in units.values()}
    }
    summary["retrieval_topk_saturation_note"] = (
        "Hypertension has four corpus originals: R@5/10 cannot test fine ranking in that module; inspect Top1/3 and per-module metrics."
    )
    summary["workflow_profile_changes"] = [
        "Optional narrative generation disabled; original template reports retained",
        "Separate Chroma persistence directory; original corpus and retrieval settings retained",
    ]
    write_json(output / "summary.json", summary)
    write_json(output / "scoring_labels.json", gold)
    write_json(output / "workflow_scored.json", workflow)
    with (output / "retrieval_metrics.csv").open("w", encoding="utf-8", newline="") as stream:
        fields = list(summary["retrieval_metrics"][0]) if retrieval else []
        w = csv.DictWriter(stream, fields)
        w.writeheader()
        w.writerows(summary["retrieval_metrics"])
    with (output / "review_queue.csv").open("w", encoding="utf-8", newline="") as stream:
        w = csv.DictWriter(
            stream,
            [
                "case_id",
                "engineering_reference",
                "workflow_outcome",
                "model_outcome",
                "reviewer",
                "clinical_outcome",
                "explanation_supported",
                "notes",
            ],
        )
        w.writeheader()
        wm = {r["case_id"]: r for r in workflow}
        jm = {r["case_id"]: r for r in judgments}
        for case, label in labels.items():
            w.writerow(
                {
                    "case_id": case,
                    "engineering_reference": label["expected_outcome"],
                    "workflow_outcome": wm.get(case, {}).get("assessment_outcome", ""),
                    "model_outcome": jm.get(case, {})
                    .get("answer", {})
                    .get("assessment_outcome", ""),
                }
            )
    notes = {i["case_id"]: (ROOT / i["input"]).read_text(encoding="utf-8") for i in plan["inputs"]}
    render(output, summary, workflow, judgments, retrieval, labels, notes, units)
    write_json(
        output / "checkpoint.json",
        {
            "journals": {
                name: {
                    "bytes": (output / name).stat().st_size,
                    "sha256": sha256_bytes((output / name).read_bytes()),
                }
                for name in ("retrieval.jsonl", "workflow.jsonl", "judgments.jsonl")
                if (output / name).exists()
            }
        },
    )
    write_json(
        output / "artifacts.json",
        {
            p.name: sha256_bytes(p.read_bytes())
            for p in output.iterdir()
            if p.is_file() and p.name not in {"artifacts.json", ".run.lock"}
        },
    )
    return summary


def verify_checkpoint(output):
    pins = read(output / "artifacts.json")
    sizes = (
        read(output / "checkpoint.json")["journals"]
        if (output / "checkpoint.json").exists()
        else {}
    )
    for name, pin in pins.items():
        path = (output / name).resolve()
        if not path.is_relative_to(output) or not path.is_file():
            raise ValueError("Checkpoint file missing or outside its directory")
        with path.open("rb") as stream:
            data = stream.read(sizes[name]["bytes"]) if name in sizes else stream.read()
        if sha256_bytes(data) != pin:
            raise ValueError("Previously recorded checkpoint changed: " + name)


def run(config, resume=False, prepare_only=False):
    cfg, output, units, plan = freeze(config)
    output.mkdir(parents=True, exist_ok=True)
    if (output / "plan.json").exists():
        if not resume or read(output / "plan.json") != plan:
            raise ValueError(
                "Resume requires identical source, input, configuration and model pins"
            )
        verify_checkpoint(output)
    elif any(output.iterdir()):
        raise ValueError("Preserve an unowned evaluation directory")
    else:
        write_json(output / "plan.json", plan)
        (output / "workflow.yaml").write_text(
            yaml.safe_dump(plan["workflow_profile"], sort_keys=False), encoding="utf-8"
        )
        write_json(
            output / "corpus.json",
            {"corpus_sha256": plan["corpus_identity"], "units": list(units.values())},
        )
        shutil.copyfile(ROOT / "data/knowledge/raw/ap_g56_22.pdf", output / "evidence_guide.pdf")
        (output / "notes").mkdir()
        for i in plan["inputs"]:
            shutil.copyfile(ROOT / i["input"], output / "notes" / (i["case_id"] + ".txt"))
        write_json(
            output / "artifacts.json",
            {p.name: sha256_bytes(p.read_bytes()) for p in output.iterdir() if p.is_file()},
        )
    if prepare_only:
        return {"prepared_cases": len(plan["inputs"]), "dataset_identity": plan["dataset_identity"]}
    lock = output / ".run.lock"
    if lock.exists():
        pid = int(lock.read_text(encoding="ascii"))
        if process_identity(pid) is not None:
            raise ValueError("This study has a live owner")
        write_json(
            output / ("exited_owner_" + str(pid) + ".json"),
            {"pid": pid, "lock_sha256": sha256_bytes(lock.read_bytes())},
        )
        lock.unlink()
    for other in (ROOT / "outputs").glob("*/*/.run.lock"):
        if other == lock:
            continue
        raw = other.read_text(encoding="ascii").strip()
        if raw.isdecimal() and process_identity(int(raw)) is not None:
            raise ValueError("Another owned experiment is using local models: " + str(other))
    lock.write_text(str(os.getpid()), encoding="ascii")
    try:
        retrieval, workflow, judgments = load_journals(output, plan)
        done = {(r["case_id"], r["module"], r["method"]) for r in retrieval}
        notes = {
            i["case_id"]: (ROOT / i["input"]).read_text(encoding="utf-8") for i in plan["inputs"]
        }
        if len(done) < sum(len(i["modules"]) for i in plan["inputs"]) * 3:
            # A normal production workflow is initialized after broad discovery,
            # keeping embedding-heavy and generator-heavy stages serial.
            from occupational_fitness_rag.pipeline.config import load_workflow_config

            wfconfig, _ = load_workflow_config(ROOT / cfg["workflow"])
            ret = wfconfig.retrieval.model_copy(
                update={
                    "collection_name": "complex_long200_scope88",
                    "persist_directory": ".runtime/complex_long_200/discovery_chroma",
                }
            )
            store = build_local_chroma(ROOT, ret, plan["corpus_identity"])
            chunks = corpus_chunks(units, plan["corpus_identity"])
            store.add(chunks)
            native = store.collection.get(include=["documents", "metadatas", "embeddings"])
            native["embeddings"] = native["embeddings"].tolist()
            write_json(
                output / "discovery_index.json",
                {
                    "collection": store.collection.name,
                    "count": store.collection.count(),
                    "content_sha256": digest(native),
                    "embedding_model_digest": cfg["expected_model_digests"][
                        "nomic-embed-text:latest"
                    ],
                },
            )
            for i in plan["inputs"]:
                for module in i["modules"]:
                    for method in cfg["methods"]:
                        key = (i["case_id"], module, method)
                        if key in done:
                            continue
                        row = {
                            "experiment_identity": plan["identity"],
                            "case_id": i["case_id"],
                            "module": module,
                            "method": method,
                            "query_sha256": sha256_bytes(notes[i["case_id"]].encode()),
                            "input_sha256": i["sha256"],
                        }
                        started = perf_counter()
                        try:
                            row.update(
                                ranked_search(
                                    store,
                                    notes[i["case_id"]],
                                    module,
                                    method,
                                    plan["corpus_identity"],
                                ),
                                status="completed",
                            )
                        except Exception as exc:
                            row.update(
                                status="failed", source_ids=[], error=f"{type(exc).__name__}: {exc}"
                            )
                        row["seconds"] = perf_counter() - started
                        append(output / "retrieval.jsonl", row)
                        done.add(key)
                if len(done) % 30 == 0:
                    checkpoint(output, plan, units)
                    print(f"Discovery {len(done)}/720 ranked conditions", flush=True)
            checkpoint(output, plan, units)
        # No labels or expectations are passed to the normal workflow.
        engine = OccupationalFitnessWorkflow(output / "workflow.yaml", build_missing=False)
        retrieval, workflow, judgments = load_journals(output, plan)
        done = {r["case_id"] for r in workflow}
        (output / "attempt_starts").mkdir(exist_ok=True)
        for i in plan["inputs"]:
            if i["case_id"] in done:
                continue
            row = {
                "experiment_identity": plan["identity"],
                "case_id": i["case_id"],
                "input_sha256": i["sha256"],
            }
            start_file = output / "attempt_starts" / (i["case_id"] + ".json")
            started = perf_counter()
            if start_file.exists():
                row.update(
                    status="failed",
                    error="Prior workflow attempt was interrupted before a journal record; no silent retry.",
                )
            else:
                write_json(start_file, row)
                try:
                    runtime(cfg)
                    bundle = engine.run_file(
                        ROOT / i["input"], output / "runs", modules=i["modules"]
                    )
                    engine.verify_run(bundle)
                    rule, evidence = (
                        read(bundle / "rule_result.json"),
                        read(bundle / "evidence_pack.json"),
                    )
                    intake, review = (
                        read(bundle / "llm_extraction_audit.json"),
                        read(bundle / "llm_semantic_review.json"),
                    )
                    row.update(
                        status="completed",
                        bundle=bundle.relative_to(output).as_posix(),
                        bundle_manifest_sha256=sha256_bytes(
                            (bundle / "run_manifest.json").read_bytes()
                        ),
                        assessment_outcome=rule["assessment_outcome"],
                        route=rule["route"],
                        modules=rule["modules"],
                        triggered_rule_ids=[r["rule_id"] for r in rule["triggered_rules"]],
                        ranking_calls=evidence["retrieval"]["ranking_calls"],
                        symptom_discovery_calls=evidence["retrieval"]["symptom_discovery_calls"],
                        extraction_status=intake["status"],
                        semantic_review_status=review["status"],
                        captured_extraction_generation_records=len(intake.get("calls", [])),
                        captured_review_generation_records=len(review.get("calls", [])),
                        all_citations_verified_against_pdf=evidence["integrity"][
                            "all_citations_verified_against_pdf"
                        ],
                    )
                except Exception as exc:
                    row.update(status="failed", error=f"{type(exc).__name__}: {exc}")
            row["seconds"] = perf_counter() - started
            append(output / "workflow.jsonl", row)
            done.add(i["case_id"])
            print(
                f"Workflow {len(done)}/200 {i['case_id']} {row['status']} {row.get('assessment_outcome', '')}",
                flush=True,
            )
            if len(done) % 5 == 0:
                checkpoint(output, plan, units)
        retrieval, workflow, judgments = load_journals(output, plan)
        hybrid = {(r["case_id"], r["module"]): r for r in retrieval if r["method"] == "hybrid"}
        wm = {r["case_id"]: r for r in workflow}
        done = {r["case_id"] for r in judgments}
        for i in plan["inputs"]:
            case_id = i["case_id"]
            if case_id in done:
                continue
            row = {
                "experiment_identity": plan["identity"],
                "case_id": case_id,
                "model": cfg["judge_model"],
                "actual_judge_attempts": 0,
            }
            started = perf_counter()
            start_file = output / "attempt_starts" / (case_id + "_judgment.json")
            try:
                if wm[case_id]["status"] != "completed":
                    raise ValueError("Upstream workflow failed; no imaginary judgment call")
                if start_file.exists():
                    raise ValueError(
                        "Prior judgment attempt was interrupted; preserve it without silent retry"
                    )
                case = read(output / wm[case_id]["bundle"] / "structured_case.json")
                payload, budget = judgment_payload(
                    case, i["modules"], notes[case_id], hybrid, units, cfg["evidence_max_bytes"]
                )
                body = judgment_request(cfg, cfg["judge_model"], payload)
                row.update(
                    input_payload=payload,
                    evidence_budget=budget,
                    request=body,
                    request_sha256=digest(body),
                )
                write_json(
                    start_file,
                    {
                        "experiment_identity": plan["identity"],
                        "request_sha256": row["request_sha256"],
                    },
                )
                runtime(cfg)
                row["actual_judge_attempts"] = 1
                raw = local_post(cfg["endpoint"], "/api/chat", body, 180)
                row["raw_response"] = raw
                answer = accept_completion(raw, payload, "hybrid", cfg)
                row.update(
                    status="completed",
                    answer=answer.model_dump(mode="json"),
                    clinical_explanation_support="pending_independent_review",
                )
            except Exception as exc:
                row.update(status="failed", error=f"{type(exc).__name__}: {exc}")
            row["seconds"] = perf_counter() - started
            append(output / "judgments.jsonl", row)
            done.add(case_id)
            print(f"Judgment {len(done)}/200 {case_id} {row['status']}", flush=True)
            if len(done) % 5 == 0:
                checkpoint(output, plan, units)
        verify_notes(plan)
        if (
            any(
                sha256_bytes((ROOT / name).read_bytes()) != pin
                for name, pin in plan["sources"].items()
            )
            or runtime(cfg) != plan["runtime"]
        ):
            raise ValueError("Source or runtime drift during the evaluation")
        summary = checkpoint(output, plan, units)
        print(
            json.dumps(
                {
                    k: summary[k]
                    for k in ("complete", "stages", "workflow_metrics", "judgment_metrics")
                },
                indent=2,
            ),
            flush=True,
        )
        return summary
    finally:
        lock.unlink()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", default="configs/experiments/complex_long_200.yaml")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--prepare-only", action="store_true")
    a = p.parse_args()
    run(a.config, a.resume, a.prepare_only)
