"""Test joint selection on methods seven and nine without altering earlier runs."""

from __future__ import annotations

import argparse
from pathlib import Path
from time import perf_counter

from occupational_fitness_rag.evaluation.retrieval_prefix_search import POLICY, joint_prefix
from tools.complex_ten_contract import ROOT, append, digest, pin, read, rows, write_json
from tools.refine_complex_retrieval import DEFAULT, PARENT, verify


def run(parent=DEFAULT):
    verify(parent, PARENT)
    target = parent / "joint_prefix"
    target.mkdir(exist_ok=True)
    methods = [
        "scope88_prefix_criterion_v6__literal_facets",
        "neo4j_frontier_criterion_v3__literal_facets",
    ]
    manifest = {
        "policy": POLICY,
        "parent_protocol_identity": read(parent / "protocol.json")["identity"],
        "parent_rankings_sha256": pin(parent / "rankings.jsonl"),
        "methods": methods,
        "source_files": {
            n: pin(ROOT / n)
            for n in (
                "tools/refine_complex_prefix.py",
                "src/occupational_fitness_rag/evaluation/retrieval_prefix_search.py",
            )
        },
        "planned_conditions": 714,
        "new_model_or_native_calls": 0,
        "labels_available_to_ranker": False,
        "development_cohort": True,
    }
    manifest["identity"] = digest(manifest)
    if (target / "manifest.json").exists() and read(target / "manifest.json") != manifest:
        raise ValueError("Joint selection protocol or inputs changed")
    write_json(target / "manifest.json", manifest)
    units = {u["source_id"]: u for u in read(parent / "corpus.json")["units"]}
    done = {(r["query_id"], r["method"]) for r in rows(target / "rankings.jsonl")}
    selected = [r for r in rows(parent / "rankings.jsonl") if r["method"] in methods]
    for i, base in enumerate(selected, 1):
        method = base["method"].split("__")[0] + "__joint_prefix"
        if (base["query_id"], method) in done:
            continue
        result = {k: base[k] for k in ("case_id", "query_id", "module", "cohort")}
        result.update(
            method=method,
            baseline_method=base["baseline_method"],
            source_ids=[],
            parent_record_sha256=digest(base),
        )
        begin = perf_counter()
        try:
            scores = {
                sid: sum(p["contribution"] for p in proof)
                for sid, proof in base["ranking_evidence"].items()
            }
            candidates = base["diagnostics"]["candidate_source_ids"]
            for sid in candidates:
                if sid not in scores:
                    scores[sid] = 0.95 * max(
                        (
                            scores.get(s, 0.0)
                            for s in units[sid].get("covers_source_ids", [])
                            if s != sid
                        ),
                        default=0.0,
                    )
            result.update(joint_prefix(base, candidates, units, scores), status="completed")
        except Exception as exc:
            result.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        result["seconds"] = perf_counter() - begin
        result["record_sha256"] = digest(result)
        append(target / "rankings.jsonl", result)
        if i % 50 == 0 or i == len(selected):
            print(f"Joint five-original selection {i}/{len(selected)}", flush=True)
    actual = rows(target / "rankings.jsonl")
    if len(actual) != 714 or len({(r["query_id"], r["method"]) for r in actual}) != 714:
        raise ValueError("Joint selection observation grid differs")
    write_json(
        target / "complete.json",
        {
            "conditions": len(actual),
            "failed": sum(r["status"] != "completed" for r in actual),
            "rankings_sha256": pin(target / "rankings.jsonl"),
            "manifest_identity": manifest["identity"],
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, default=DEFAULT)
    run(parser.parse_args().parent)
