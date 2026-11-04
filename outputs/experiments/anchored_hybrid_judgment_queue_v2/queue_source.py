"""Run one frozen judgment experiment after its current predecessor finishes.

This is a one-shot continuation of the current experiment, not a recurring job
or scheduler. It never starts Ollama, changes model settings, repairs stale
locks, changes actor code or substitutes missing experiment results.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.evaluation.passage_comparison import read_records
from occupational_fitness_rag.provenance import digest
from tools import run_frozen_retrieval_judgments as actor

DEFAULT_PARENT = "outputs/experiments/seven_method_judgment_full_v1"
DEFAULT_PREPARATION = "outputs/experiments/anchored_hybrid_judgment_preparation_v2"
DEFAULT_OUTPUT = "outputs/experiments/anchored_hybrid_judgment_full_v2"
DEFAULT_QUEUE = "outputs/experiments/anchored_hybrid_judgment_queue_v2"
PARENT_PREPARATION = "outputs/experiments/retrieval_judgment_preparation_v2"
PARENT_ADDITIONAL = "outputs/experiments/planned_hybrid_v1"
SOURCE_NAMES = (
    "tools/run_frozen_retrieval_judgments.py",
    "tools/prepare_retrieval_judgments.py",
    "src/occupational_fitness_rag/evaluation/judgment_comparison.py",
    "src/occupational_fitness_rag/evaluation/model_judgment.py",
    "src/occupational_fitness_rag/evaluation/graph_completion.py",
)


def read_json(path):
    return json.loads(Path(path).read_bytes())


def write_json(path, value):
    """Replace a task-owned status atomically, retaining the append-only log."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def process_identity(pid):
    """Read process liveness without Windows ``os.kill``, which can terminate it."""
    if type(pid) is not int or pid <= 0:
        raise ValueError("A lock must contain a positive process ID")
    if os.name == "nt":
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.GetProcessTimes.argtypes = [
            wintypes.HANDLE,
            *[ctypes.POINTER(wintypes.FILETIME)] * 4,
        ]
        handle = kernel.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION.
        if not handle:
            if ctypes.get_last_error() in {87, 1168}:  # No such process.
                return None
            raise OSError(ctypes.get_last_error(), "Cannot inspect a locked experiment process")
        try:
            code = wintypes.DWORD()
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
                raise OSError(ctypes.get_last_error(), "Cannot inspect process exit status")
            if code.value != 259:  # STILL_ACTIVE.
                return None
            values = [wintypes.FILETIME() for _ in range(4)]
            if not kernel.GetProcessTimes(handle, *[ctypes.byref(v) for v in values]):
                raise OSError(ctypes.get_last_error(), "Cannot inspect process creation time")
            created = values[0].dwLowDateTime | (values[0].dwHighDateTime << 32)
            return {"pid": pid, "creation_time": created}
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return None
    stat = Path(f"/proc/{pid}/stat")
    started = stat.read_text().rsplit(")", 1)[1].split()[19] if stat.exists() else None
    return {"pid": pid, "creation_time": started}


def lock_process(path):
    try:
        text = Path(path).read_text(encoding="ascii").strip()
    except FileNotFoundError:
        return None
    if not text.isdecimal() or int(text) <= 0:
        raise ValueError("Malformed experiment process lock: " + str(path))
    pid = int(text)
    identity = process_identity(pid)
    if identity is None:
        raise ValueError("Locked experiment process has exited; preserve its lock: " + str(path))
    return identity


def verify_artifacts(directory, expected=None):
    directory = Path(directory).resolve()
    pins = read_json(directory / "artifacts.json")
    if not isinstance(pins, dict) or not pins:
        raise ValueError("Missing frozen artifact inventory: " + str(directory))
    if expected is not None and pins != expected:
        raise ValueError("Frozen artifact inventory changed: " + str(directory))
    for name, pin in pins.items():
        path = (directory / name).resolve()
        if not path.is_relative_to(directory) or path == directory or not path.is_file():
            raise ValueError("Artifact path escapes or is absent from its experiment")
        if file_hash(path) != pin:
            raise ValueError("Frozen artifact changed: " + str(path))
    return pins


def _self_identity(plan):
    if (
        digest({k: v for k, v in plan.items() if k not in {"identity", "production_change"}})
        != plan["identity"]
    ):
        raise ValueError("Frozen execution plan self-identity changed")


def _paths(root, parent, preparation, output, queue):
    root = Path(root).resolve()
    paths = [
        Path(p).resolve() if Path(p).is_absolute() else (root / p).resolve()
        for p in (parent, preparation, output, queue)
    ]
    if len(set(paths)) != len(paths) or any(
        not path.is_relative_to(root / "outputs/experiments") for path in paths
    ):
        raise ValueError("Use distinct task directories inside outputs/experiments")
    return paths


def _sources(root, parent_plan):
    parent = {name.replace("\\", "/"): pin for name, pin in parent_plan["sources"].items()}
    if set(parent) != set(SOURCE_NAMES):
        raise ValueError("Parent uses a different judgment actor source inventory")
    current = {name: file_hash(root / name) for name in SOURCE_NAMES}
    if current != parent:
        raise ValueError("Judgment actor source drift from the original full comparison")
    return current


def build_plan(root, parent, preparation, output, queue):
    root = Path(root).resolve()
    parent, preparation, output, queue = _paths(root, parent, preparation, output, queue)
    parent_plan = read_json(parent / "plan.json")
    _self_identity(parent_plan)
    sources = _sources(root, parent_plan)
    parent_pins = verify_artifacts(root / PARENT_PREPARATION, parent_plan["preparation_artifacts"])
    verify_artifacts(root / PARENT_ADDITIONAL, parent_plan["additional_artifacts"])
    config, manifest, pins, extra, _, requests, conditions = actor.prepare_inputs(preparation)
    verify_artifacts(preparation, pins)
    if extra is not None:
        raise ValueError("The queued arm must use its already frozen preparation only")
    if (
        manifest["parent_preparation_identity"] != parent_plan["preparation_identity"]
        or manifest["parent_preparation_artifacts_sha256"]
        != file_hash(root / PARENT_PREPARATION / "artifacts.json")
        or read_json(root / PARENT_PREPARATION / "manifest.json")["identity"]
        != parent_plan["preparation_identity"]
        or parent_pins != parent_plan["preparation_artifacts"]
    ):
        raise ValueError("Queued arm does not share the original frozen patient preparation")
    env = actor.runtime(config)  # Read-only version and model digest queries.
    if env != parent_plan["runtime"]:
        raise ValueError("Queued judge runtime differs from the original full comparison")
    chosen = sorted(
        conditions,
        key=lambda c: (config["models"].index(c["model"]), c["repeat"], c["case_id"], c["method"]),
    )
    if (
        len(chosen) != 198
        or len({c["case_id"] for c in chosen}) != 33
        or len({c["method"] for c in chosen}) != 1
        or len(config["models"]) != 2
        or config["repeats"] != 3
        or {(c["case_id"], c["model"], c["repeat"]) for c in chosen}
        != {
            (case, model, repeat)
            for case in {c["case_id"] for c in chosen}
            for model in config["models"]
            for repeat in range(3)
        }
    ):
        raise ValueError("Queued arm must retain 33 cases, two models and three independent calls")
    child_data = {
        "preparation_identity": manifest["identity"],
        "preparation_artifacts": pins,
        "additional_artifacts": None,
        "runtime": env,
        "conditions": chosen,
        "requests_sha256": digest(requests),
        "sources": parent_plan["sources"],
        "scope": "complete fixed patient comparison",
    }
    child_plan = {**child_data, "identity": digest(child_data), "production_change": False}
    data = {
        "kind": "one_shot_serial_judgment_continuation",
        "root": str(root),
        "parent": str(parent),
        "preparation": str(preparation),
        "output": str(output),
        "queue": str(queue),
        "parent_plan_sha256": file_hash(parent / "plan.json"),
        "parent_plan_identity": parent_plan["identity"],
        "sources": sources,
        "preparation_artifacts": pins,
        "runtime": env,
        "expected_child_plan": child_plan,
        "queue_source_sha256": file_hash(Path(__file__)),
        "python_executable": str(Path(sys.executable).resolve()),
        "python_version": sys.version,
        "poll_interval_seconds": 10,
    }
    return {**data, "identity": digest(data), "production_change": False}


def verify_live_pins(plan):
    root, parent = Path(plan["root"]), Path(plan["parent"])
    if (
        file_hash(parent / "plan.json") != plan["parent_plan_sha256"]
        or file_hash(Path(__file__)) != plan["queue_source_sha256"]
        or sys.version != plan["python_version"]
        or str(Path(sys.executable).resolve()) != plan["python_executable"]
    ):
        raise ValueError("Serial queue source, interpreter or parent plan changed")
    if _sources(root, read_json(parent / "plan.json")) != plan["sources"]:
        raise ValueError("Frozen actor source changed")
    verify_artifacts(Path(plan["preparation"]), plan["preparation_artifacts"])


def completed_run(directory, expected_plan=None):
    """Require a complete, consistently counted run and verify every pinned file."""
    directory = Path(directory)
    plan = read_json(directory / "plan.json")
    _self_identity(plan)
    if expected_plan is not None and plan != expected_plan:
        raise ValueError("Completed child execution plan differs from the queue")
    summary = read_json(directory / "summary.json")
    if summary.get("complete") is not True:
        raise ValueError("A predecessor or child run is incomplete")
    pins = verify_artifacts(directory)
    if not {"plan.json", "summary.json", "results.jsonl", "requests.json", "payloads.json"} <= set(
        pins
    ):
        raise ValueError("Completed run omits required auditable artifacts")
    rows = read_records(directory / "results.jsonl")
    planned = {actor.key(c): c for c in plan["conditions"]}
    if (
        len(planned) != len(plan["conditions"])
        or len(rows) != len(planned)
        or {actor.key(r) for r in rows} != set(planned)
        or any(
            r["experiment_identity"] != plan["identity"]
            or r["request_identity"] != planned[actor.key(r)]["request_identity"]
            or r["status"] not in {"completed", "failed"}
            for r in rows
        )
        or summary.get("identity") != plan["identity"]
        or summary.get("planned") != len(planned)
        or summary.get("recorded") != len(rows)
        or summary.get("accepted") != sum(r["status"] == "completed" for r in rows)
        or summary.get("failed") != sum(r["status"] == "failed" for r in rows)
        or summary.get("actual_judgment_calls") != len(rows)
    ):
        raise ValueError("Completed run counters or recorded condition identities differ")
    return {
        "identity": plan["identity"],
        "planned": summary["planned"],
        "recorded": summary["recorded"],
        "accepted": summary["accepted"],
        "failed": summary["failed"],
        "artifacts_sha256": file_hash(directory / "artifacts.json"),
        "summary_sha256": file_hash(directory / "summary.json"),
    }


def predecessor_status(plan, previous_identity=None):
    parent = Path(plan["parent"])
    identity = lock_process(parent / ".run.lock")
    if identity is not None:
        if previous_identity is not None and identity != previous_identity:
            raise ValueError("Predecessor process identity changed; do not dispatch")
        return {"ready": False, "parent_process": identity}
    # An exited process is acceptable only after its successful finalization and
    # lock release. Missing/incomplete artifacts never trigger the next run.
    completion = completed_run(parent)
    return {"ready": True, "parent_completion": completion}


def require_no_other_active_jobs(plan):
    excluded = {Path(plan["queue"]) / ".run.lock"}
    for marker in (Path(plan["root"]) / "outputs/experiments").rglob(".run.lock"):
        if marker in excluded:
            continue
        try:
            text = marker.read_text(encoding="ascii").strip()
            identity = process_identity(int(text)) if text.isdecimal() else None
        except FileNotFoundError:
            continue
        if identity is not None:
            raise ValueError(
                "Another experiment process is active; preserve serial GPU use: " + str(marker)
            )


def _status(queue, plan, state, **fields):
    value = {
        "queue_identity": plan["identity"],
        "state": state,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **fields,
    }
    write_json(queue / "status.json", value)
    with (queue / "events.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps(value, ensure_ascii=False), flush=True)
    return value


def run(
    root,
    parent=DEFAULT_PARENT,
    preparation=DEFAULT_PREPARATION,
    output=DEFAULT_OUTPUT,
    queue=DEFAULT_QUEUE,
    resume=False,
    once=False,
):
    plan = build_plan(root, parent, preparation, output, queue)
    queue = Path(plan["queue"])
    parent, output = Path(plan["parent"]), Path(plan["output"])
    if queue.exists():
        if not resume or read_json(queue / "plan.json") != plan:
            raise ValueError("Resume requires the identical serial queue plan")
    else:
        if resume:
            raise ValueError("There is no serial queue to resume")
        if output.exists() and any(output.iterdir()):
            raise ValueError("Preserve unowned judgment output; use a new queue/output")
        queue.mkdir(parents=True)
        write_json(queue / "plan.json", plan)
        (queue / "queue_source.py").write_bytes(Path(__file__).read_bytes())
    lock = queue / ".run.lock"
    with lock.open("x", encoding="ascii") as stream:
        stream.write(str(os.getpid()))
    previous = read_json(queue / "status.json") if (queue / "status.json").exists() else {}
    parent_process = previous.get("parent_process")
    try:
        if previous.get("state") == "complete":
            completion = completed_run(output, plan["expected_child_plan"])
            if completion != previous["child_completion"]:
                raise ValueError("Completed queued run artifacts changed after finalization")
            return previous
        while True:
            verify_live_pins(plan)
            ready = predecessor_status(plan, parent_process)
            if ready["ready"]:
                if previous.get("parent_completion") is not None and (
                    previous["parent_completion"] != ready["parent_completion"]
                ):
                    raise ValueError("Frozen predecessor completion changed")
                break
            parent_process = ready["parent_process"]
            if (
                previous.get("state") != "waiting_for_predecessor"
                or previous.get("parent_process") != parent_process
            ):
                previous = _status(
                    queue, plan, "waiting_for_predecessor", parent_process=parent_process
                )
            if once:
                return previous
            time.sleep(plan["poll_interval_seconds"])
        completion = ready["parent_completion"]
        if once:
            return _status(queue, plan, "ready_without_dispatch", parent_completion=completion)
        config = read_json(Path(plan["preparation"]) / "manifest.json")["config"]
        if actor.runtime(config) != plan["runtime"]:
            raise ValueError("Frozen judge runtime changed before serial dispatch")
        verify_artifacts(
            Path(plan["root"]) / PARENT_PREPARATION,
            read_json(parent / "plan.json")["preparation_artifacts"],
        )
        verify_artifacts(
            Path(plan["root"]) / PARENT_ADDITIONAL,
            read_json(parent / "plan.json")["additional_artifacts"],
        )
        verify_live_pins(plan)
        child_marker = output / ".run.lock"
        child_plan_path = output / "plan.json"
        if child_plan_path.exists() and read_json(child_plan_path) != plan["expected_child_plan"]:
            raise ValueError("Existing queued child has a different execution plan")
        if (
            not child_marker.exists()
            and (output / "summary.json").exists()
            and read_json(output / "summary.json").get("complete")
        ):
            child = completed_run(output, plan["expected_child_plan"])
            return _status(
                queue, plan, "complete", parent_completion=completion, child_completion=child
            )
        process = None
        if child_marker.exists():
            identity = lock_process(child_marker)
            if not resume or previous.get("child_process") != identity:
                raise ValueError("Unowned or changed live child process; do not dispatch another")
            previous = _status(
                queue,
                plan,
                "running_child",
                parent_completion=completion,
                child_process=identity,
                reattached=True,
            )
        else:
            if previous.get("state") == "running_child":
                raise ValueError("Child process ended without verified complete artifacts")
            require_no_other_active_jobs(plan)
            args = [
                sys.executable,
                "-X",
                "utf8",
                "-m",
                "tools.run_frozen_retrieval_judgments",
                "--preparation",
                plan["preparation"],
                "--output",
                str(output),
            ]
            if child_plan_path.exists():
                args.append("--resume")
            previous = _status(
                queue, plan, "dispatching_child", parent_completion=completion, command=args
            )
            with (queue / "child.log").open("ab", buffering=0) as log:
                process = subprocess.Popen(
                    args, cwd=plan["root"], stdout=log, stderr=subprocess.STDOUT
                )
            identity = process_identity(process.pid)
            if identity is None:
                raise ValueError(
                    "Queued child exited before its process identity could be recorded"
                )
            previous = _status(
                queue, plan, "running_child", parent_completion=completion, child_process=identity
            )
        while True:
            verify_live_pins(plan)
            if process is not None:
                code = process.poll()
                if code is not None:
                    if code != 0:
                        raise ValueError(f"Queued child exited with code {code}; inspect child.log")
                    break
            elif process_identity(identity["pid"]) != identity:
                break
            time.sleep(plan["poll_interval_seconds"])
        if child_marker.exists():
            raise ValueError("Queued child left its process lock; preserve it for diagnosis")
        child = completed_run(output, plan["expected_child_plan"])
        verify_live_pins(plan)
        if actor.runtime(config) != plan["runtime"]:
            raise ValueError("Frozen judge runtime changed during queued judgment")
        return _status(
            queue, plan, "complete", parent_completion=completion, child_completion=child
        )
    except BaseException as exc:
        _status(
            queue,
            plan,
            "failed",
            error=f"{type(exc).__name__}: {exc}",
            parent_process=parent_process,
            parent_completion=previous.get("parent_completion"),
            child_process=previous.get("child_process"),
        )
        raise
    finally:
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", default=DEFAULT_PARENT)
    parser.add_argument("--preparation", default=DEFAULT_PREPARATION)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--queue-dir", default=DEFAULT_QUEUE)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--once", action="store_true", help="Preflight/status only; never dispatch")
    args = parser.parse_args()
    run(
        Path(__file__).resolve().parents[1],
        args.parent,
        args.preparation,
        args.output,
        args.queue_dir,
        args.resume,
        args.once,
    )


if __name__ == "__main__":
    main()
