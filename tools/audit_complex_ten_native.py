"""Verify reused native graph files and actual database originals independently."""

from __future__ import annotations

import argparse
from pathlib import Path

from tools.complex_ten_contract import DEFAULT, METHODS, ROOT, pin, read, verify, write_json


def audit(output=DEFAULT):
    from neo4j import GraphDatabase

    output = Path(output).resolve()
    plan = read(output / "plan.json")
    verify(output, plan)
    units = {u["source_id"]: u for u in read(output / "corpus.json")["units"]}
    inventory = read(output / "input_inventory.json")
    duplicates = {}
    for item in inventory:
        duplicates.setdefault(item["sha256"], []).append(item["case_id"])
    receipts = []
    for method in ("lightrag", "graphrag"):
        folder = output / "workers" / method
        if method == "lightrag":
            folder = output / "lightrag_serial_rerun/workers/lightrag"
        if not (folder / "complete.json").exists():
            raise ValueError("Finish native graph queries before final index audit")
        for module in sorted({u["module"] for u in units.values()}):
            parent = (
                ROOT
                / "outputs/experiments"
                / (
                    "scope88_external_graph_v1"
                    if module == "vision"
                    else "external_graph_retrieval_v3"
                )
                / "indexes"
                / method
                / module
            )
            copied = folder / "indexes" / module
            if method == "lightrag":
                originals = read(copied / module / "kv_store_full_docs.json")
                if {s: v["content"] for s, v in originals.items()} != {
                    s: u["evidence_text"] for s, u in units.items() if u["module"] == module
                }:
                    raise ValueError("LightRAG persisted originals differ")
                files = [
                    p
                    for p in (parent / module).iterdir()
                    if p.is_file() and (p.suffix == ".graphml" or p.name.startswith("vdb_"))
                ]
            else:
                files = list((parent / "output").glob("*.parquet"))
            if not files:
                raise ValueError("Native graph has no inspectable construction files")
            checked = []
            for source in files:
                name = source.relative_to(parent)
                target = copied / name
                before, after = pin(source), pin(target)
                same = before == after or (
                    source.suffix == ".json" and read(source) == read(target)
                )
                if not same:
                    raise ValueError("Native graph/vector contents changed: " + str(name))
                checked.append(
                    {"file": name.as_posix(), "parent_sha256": before, "queried_copy_sha256": after}
                )
            receipts.append(
                {
                    "method": method,
                    "module": module,
                    "native_files": checked,
                    "index_completion_sha256": pin(parent / "index_complete.json"),
                }
            )
    credentials = read(ROOT / ".runtime/neo4j/credential.json")
    identity = read(ROOT / "outputs/experiments/scope88_neo4j_strategies_v2/manifest.json")[
        "identity"
    ]
    with GraphDatabase.driver(
        "bolt://127.0.0.1:17687",
        auth=(credentials.get("username", "neo4j"), credentials["password"]),
    ) as driver:
        actual = driver.execute_query(
            "MATCH (n:OFPOriginalSource {experiment_id:$identity}) RETURN n.source_id AS source_id,n.source_text AS source_text",
            {"identity": identity},
            database_=credentials.get("database", "neo4j"),
        ).records
        if {r["source_id"]: r["source_text"] for r in actual} != {
            s: u["evidence_text"] for s, u in units.items()
        }:
            raise ValueError("Actual Neo4j source text differs from frozen guideline originals")
    tree = ROOT / "outputs/experiments/scope88_tree_coverage_v1/native_index"
    checks = {
        "all_234_input_files_unchanged": len(inventory) == 234,
        "upstream_fact_and_code_pins_unchanged": True,
        "actual_native_graph_contents_unchanged": True,
        "actual_neo4j_source_texts_unchanged": True,
        "pageindex_mapping_preserved": read(
            output / "workers" / METHODS[9] / "native_index_receipt.json"
        )["mapping_sha256"]
        == pin(tree / "source_mapping.json"),
    }
    result = {
        "experiment_identity": plan["identity"],
        "checks": checks,
        "all_passed": all(checks.values()),
        "distinct_input_file_hashes": len(duplicates),
        "duplicate_input_files": [v for v in duplicates.values() if len(v) > 1],
        "native_index_receipts": receipts,
        "actual_neo4j_originals_verified": len(actual),
        "source_sha256": pin(__file__),
        "clinical_accuracy": None,
        "production_change": False,
    }
    write_json(output / "native_integrity.json", result)
    print(
        {
            "all_passed": result["all_passed"],
            "native_modules": len(receipts),
            "database_originals": len(actual),
            "distinct_inputs": len(duplicates),
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT)
    audit(parser.parse_args().output)
