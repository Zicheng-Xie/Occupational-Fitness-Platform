"""Retain the invalid concurrent batch and rerun LightRAG with one exclusive owner."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

from tools.complex_ten_contract import DEFAULT, ROOT, digest, pin, read, rows, verify, write_json
from tools.run_external_graph_retrieval import AuditProxy


def rerun(parent=DEFAULT):
    parent = Path(parent).resolve()
    plan = read(parent / "plan.json")
    verify(parent, plan)
    previous = parent / "workers/lightrag"
    observations = rows(previous / "results.jsonl")
    target = parent / "lightrag_serial_rerun"
    target.mkdir(exist_ok=True)
    manifest = {
        "kind": "exclusive_serial_lightrag_rerun",
        "parent_protocol_identity": plan["identity"],
        "invalid_parent_rankings_sha256": pin(previous / "results.jsonl"),
        "invalid_parent_model_calls_sha256": pin(previous / "model_calls.jsonl"),
        "invalid_parent_observations": len(observations),
        "invalid_parent_distinct_queries": len({r["query_id"] for r in observations}),
        "reason": "Concurrent controllers created duplicate observations; exclude the complete invalid batch from primary scoring and retain every raw record.",
        "selection_by_expected_answer": False,
        "method_configuration_changed": False,
        "source_sha256": pin(__file__),
    }
    manifest["identity"] = digest(manifest)
    if (target / "manifest.json").exists() and read(target / "manifest.json") != manifest:
        raise ValueError("Serial rerun source or frozen parent changed")
    write_json(target / "manifest.json", manifest)
    lock = target / ".owner.lock"
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(descriptor, str(os.getpid()).encode())
    os.close(descriptor)
    try:
        for name in ["plan.json", *plan["prepared_files"]]:
            destination = target / name
            if destination.exists() and pin(destination) != pin(parent / name):
                raise ValueError("Copied frozen input differs")
            shutil.copyfile(parent / name, destination)
        (target / "facts").mkdir(exist_ok=True)
        for name in plan["fact_files"]:
            shutil.copyfile(parent / "facts" / name, target / "facts" / name)
        folder = target / "workers/lightrag"
        folder.mkdir(parents=True, exist_ok=True)
        if not (folder / "complete.json").exists():
            context = AuditProxy(plan["external_config"], folder)
            context.job = folder
            env = {
                **os.environ,
                "PYTHONPATH": str(ROOT / "src") + os.pathsep + str(ROOT),
                "PYTHONUTF8": "1",
                "TIKTOKEN_CACHE_DIR": str(ROOT / ".runtime/tokenizers"),
            }
            command = [
                str(ROOT / ".runtime/lightrag/Scripts/python.exe"),
                "-X",
                "utf8",
                "-m",
                "tools.complex_native_worker",
                "--output",
                str(target),
                "--method",
                "lightrag",
            ]
            with context, (folder / "stdout.log").open("a", encoding="utf-8") as log:
                response = subprocess.run(
                    command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT
                )
            if response.returncode:
                raise RuntimeError("Serial native worker failed; original records retained")
        receipt = read(folder / "complete.json")
        if receipt["recorded"] != 357 or receipt["results_sha256"] != pin(folder / "results.jsonl"):
            raise ValueError("Serial native condition inventory differs")
        verify(parent, plan)
        write_json(
            target / "complete.json",
            {
                "parent_protocol_identity": plan["identity"],
                "serial_manifest_identity": manifest["identity"],
                "native_receipt": receipt,
                "parent_invalid_batch_retained": True,
                "completed": True,
            },
        )
        print("Exclusive LightRAG rerun completed: 357 actual unique conditions", flush=True)
    finally:
        lock.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, default=DEFAULT)
    rerun(parser.parse_args().parent)
