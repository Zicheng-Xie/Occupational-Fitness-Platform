"""Freeze the two complete complex-note folders for a ten-route retrieval study."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "outputs/experiments/complex_234_ten_methods_20261027"
MODULES = ["hypertension", "vision", "hearing", "blackout", "diabetes"]
METHODS = [
    "vector",
    "bm25",
    "hybrid",
    "graph_local",
    "lightrag",
    "graphrag",
    "scope88_prefix_criterion_v6",
    "flag_embedding_rerank",
    "neo4j_frontier_criterion_v3",
    "pageindex_rrf_predicate_navigation",
]


def read(path):
    return json.loads(Path(path).read_bytes())


def rows(path):
    return (
        [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]
        if Path(path).exists()
        else []
    )


def prepare(output=DEFAULT):
    from occupational_fitness_rag.case_intake.model_intake import model_intake
    from occupational_fitness_rag.case_intake.semantic_review import semantic_review
    from occupational_fitness_rag.case_intake.traceable import extract_traceable_text
    from occupational_fitness_rag.pipeline.config import load_workflow_config
    from occupational_fitness_rag.rules.engine import RuleBook

    output = Path(output).resolve()
    if not output.is_relative_to(ROOT / "outputs/experiments"):
        raise ValueError("Keep the experiment in isolated experiment storage")
    output.mkdir(parents=True, exist_ok=True)
    new_manifest = read(ROOT / "data/cases/complex_nurse_notes/long_200_manifest.json")
    old = {r["id"]: r for r in read(ROOT / "data/cases/gold/complex_notes.json")["cases"]}
    new = {r["case_id"]: r for r in new_manifest["cases"]}
    files = sorted(
        p
        for folder in ("complex_nurse_notes", "validation_nurse_notes")
        for p in (ROOT / "data/cases" / folder).glob("*.txt")
    )
    inventory = []
    for p in files:
        cid = p.stem
        # Request scopes are existing dataset metadata; unscoped legacy notes
        # request all five modules. Expected evidence never determines scope.
        mods = new[cid]["modules"] if cid in new else old[cid]["modules"] if cid in old else MODULES
        inventory.append(
            {
                "case_id": cid,
                "input": p.relative_to(ROOT).as_posix(),
                "sha256": sha256_bytes(p.read_bytes()),
                "modules": mods,
                "cohort": "new_200" if cid in new else "original_34",
            }
        )
    if len(files) != 234 or len({r["case_id"] for r in inventory}) != 234:
        raise ValueError("The requested complete 234-note inventory differs")
    frozen = output / "input_inventory.json"
    if frozen.exists() and read(frozen) != inventory:
        raise ValueError("Input files or requested scopes changed")
    write_json(frozen, inventory)
    config, _ = load_workflow_config(ROOT / "configs/workflow.yaml")
    book = RuleBook(ROOT / config.rules)
    (output / "facts").mkdir(exist_ok=True)
    (output / "notes").mkdir(exist_ok=True)
    prior = ROOT / "outputs/evaluation/complex_long_200_20261027"
    for i, item in enumerate(inventory, 1):
        cid, p = item["case_id"], ROOT / item["input"]
        target = output / "facts" / (cid + ".json")
        if target.exists():
            saved = read(target)
            if saved["input_sha256"] != item["sha256"]:
                raise ValueError("Frozen fact input differs")
            continue
        shutil.copyfile(p, output / "notes" / p.name)
        if cid in new:
            candidates = list((prior / "runs" / cid).glob("*/structured_case.json"))
            if len(candidates) != 1:
                raise ValueError("Require one actual accepted upstream snapshot per new note")
            source = candidates[0]
            case = read(source)
            if case["source_text"].strip() != p.read_text(encoding="utf-8").strip():
                raise ValueError("Actual upstream snapshot note differs")
            saved = {
                "input_sha256": item["sha256"],
                "case": case,
                "origin": source.relative_to(ROOT).as_posix(),
                "origin_sha256": sha256_bytes(source.read_bytes()),
                "new_intake_calls": False,
            }
        else:
            case = extract_traceable_text(
                p.read_text(encoding="utf-8"),
                cid,
                p.name,
                book.field_specs,
                modules=item["modules"],
            )
            case, intake = model_intake(case, book.field_specs, config.llm)
            case, review = semantic_review(case, book.field_specs, config.llm)
            saved = {
                "input_sha256": item["sha256"],
                "case": case.model_dump(mode="json"),
                "intake_audit": intake,
                "semantic_review": review,
                "new_intake_calls": True,
                "rules_sha256": book.sha256,
            }
        write_json(target, saved)
        print(f"Frozen intake {i}/234 {cid}", flush=True)
    patients, queries = {}, []
    corpus = read(ROOT / "outputs/experiments/scope88_shared_retrieval_v2/corpus.json")
    for item in inventory:
        cid = item["case_id"]
        case = read(output / "facts" / (cid + ".json"))["case"]
        note = (ROOT / item["input"]).read_text(encoding="utf-8")
        accepted = {}
        for name, fact in case["facts"].items():
            quotes = list(
                dict.fromkeys(
                    e["quote"]
                    for e in fact.get("evidence", [])
                    if e.get("quote") and e["quote"] in note
                )
            )
            if fact["status"] == "present" and fact["value"] is not None and quotes:
                accepted[name] = {"value": fact["value"], "patient_quotes": quotes}
        patients[cid] = {
            "case_id": cid,
            "modules": item["modules"],
            "nurse_note": note,
            "verified_patient_facts": accepted,
        }
        for module in item["modules"]:
            fields = {
                k: v["value"]
                for k, v in accepted.items()
                if ("hypertension" if k.startswith("cardiovascular.") else k.split(".")[0])
                == module
            }
            q = {
                "case_id": cid,
                "module": module,
                "licence_context": "commercial",
                "query": note,
                "corpus_sha256": corpus["corpus_sha256"],
                "cohort": item["cohort"],
                "query_audit": {
                    "query_sha256": digest(note),
                    "field_values": fields,
                    "field_names": sorted(fields),
                    "query_policy": "entire_original_note",
                },
            }
            queries.append({**q, "query_id": digest(q)})
    write_json(output / "patients.json", patients)
    write_json(output / "queries.json", queries)
    write_json(output / "corpus.json", corpus)
    print(
        json.dumps(
            {
                "cases": len(inventory),
                "queries": len(queries),
                "methods": len(METHODS),
                "conditions": len(queries) * len(METHODS),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT)
    prepare(parser.parse_args().output)
