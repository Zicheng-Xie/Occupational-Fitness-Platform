"""One-time guarded serial continuation after an already running local replay.

This helper never schedules recurring work or runs concurrent model jobs. A failure
stops the pipeline and preserves its logs and experiment outputs for inspection.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_lock(path):
    """A writer may remove its lock between a poll and the next filesystem read."""
    try:
        return path.read_text(encoding="ascii")
    except FileNotFoundError:
        return None


def completed_snapshot(directory, expected_conditions, manifest_sha):
    directory = Path(directory)
    if (directory / ".run.lock").exists():
        raise ValueError("Experiment writer has not stopped")
    if file_sha(directory / "manifest.json") != manifest_sha:
        raise ValueError("First experiment manifest changed after continuation was queued")
    manifest = json.loads((directory / "manifest.json").read_bytes())
    raw = (directory / "results.jsonl").read_bytes()
    if not raw.endswith(b"\n"):
        raise ValueError("Incomplete result tail")
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    fields = ("model", "case_id", "evidence_policy", "protocol", "repeat")
    keys = [tuple(row[field] for field in fields) for row in rows]
    if (
        len(rows) != expected_conditions
        or len(set(keys)) != expected_conditions
        or set(keys) != {tuple(key) for key in manifest["planned_keys"]}
        or any(row["experiment_identity"] != manifest["identity"] for row in rows)
    ):
        raise ValueError("Stopped replay is incomplete or has unexpected condition keys")
    return hashlib.sha256(raw).hexdigest()


def execute(args):
    first, config_path = Path(args.first_directory).resolve(), Path(args.second_config).resolve()
    state_root = Path(args.state_directory).resolve()
    state_root.mkdir(parents=True, exist_ok=True)
    helper_lock = state_root / ".helper.lock"
    with helper_lock.open("x", encoding="ascii") as stream:
        stream.write(str(os.getpid()))
    sequence = 0

    def event(stage, **details):
        nonlocal sequence
        sequence += 1
        value = {
            "sequence": sequence,
            "utc": datetime.now(timezone.utc).isoformat(),
            "helper_pid": os.getpid(),
            "stage": stage,
            **details,
        }
        text = json.dumps(value, indent=2)
        temporary = state_root / "state.pending.json"
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(state_root / "state.json")
        with (state_root / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(value) + "\n")
        print(text, flush=True)

    def run(label, command):
        event("subprocess_started", label=label, command=command)
        with (state_root / (label + ".log")).open("a", encoding="utf-8") as stream:
            process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT)
            event("subprocess_running", label=label, child_pid=process.pid)
            code = process.wait()
        if code:
            raise RuntimeError(f"{label} failed with exit code {code}")
        event("subprocess_completed", label=label, exit_code=code)

    def audit(directory, label):
        command = [sys.executable, "tools/audit_applicability_execution.py", str(directory)]
        if args.tests_at_freeze is not None:
            command.extend(["--tests-at-freeze", str(args.tests_at_freeze)])
        run(label, command)
        result = json.loads((directory / "execution_audit.json").read_bytes())
        pin = result["results_sha256"]
        if file_sha(directory / "results.jsonl") != pin:
            raise ValueError("Result bytes changed after completion audit")
        return pin

    try:
        manifest_sha = file_sha(first / "manifest.json")
        first_manifest = json.loads((first / "manifest.json").read_bytes())
        if first_manifest["planned_conditions"] != args.first_conditions:
            raise ValueError("Unexpected first experiment size")
        config_raw = config_path.read_bytes()
        second_config_sha = hashlib.sha256(config_raw).hexdigest()
        second_config = yaml.safe_load(config_raw)
        second = Path(second_config["output"]).resolve()
        if second == first or first.is_relative_to(second) or second.is_relative_to(first):
            raise ValueError("Serial outputs must be isolated")
        if second.exists() and any(second.iterdir()) and not args.resume_second:
            raise ValueError("Second output already exists; explicit resume is required")
        expected_second = (
            len(second_config["case_ids"])
            * len(second_config["models"])
            * len(second_config["evidence_policies"])
            * len(second_config["protocols"])
            * second_config["repeats"]
        )
        if expected_second != args.second_conditions:
            raise ValueError("Unexpected second experiment size")
        lock = first / ".run.lock"
        original_pid = read_lock(lock)
        event(
            "waiting_for_original_writer",
            original_pid=original_pid,
            first_identity=first_manifest["identity"],
            first_manifest_sha256=manifest_sha,
            second_config_sha256=second_config_sha,
        )
        started = time.monotonic()
        while True:
            owner = read_lock(lock)
            if owner is None:
                break
            if owner != original_pid:
                raise ValueError("Original writer lock changed owner")
            if file_sha(first / "manifest.json") != manifest_sha:
                raise ValueError("Original manifest changed while waiting")
            if time.monotonic() - started > args.wait_timeout_seconds:
                raise TimeoutError("Original writer did not finish within the continuation window")
            time.sleep(5)
        first_pin = completed_snapshot(first, args.first_conditions, manifest_sha)
        if audit(first, "audit_original") != first_pin:
            raise ValueError("Original results changed between snapshot and audit")
        if file_sha(config_path) != second_config_sha:
            raise ValueError("Queued second configuration changed")
        event("original_complete_and_audited", results_sha256=first_pin)
        command = [
            sys.executable,
            "-m",
            "occupational_fitness_rag.evaluation.applicability_comparison",
            "--config",
            str(config_path),
        ]
        if args.resume_second:
            command.append("--resume")
        run("sensitivity_runner", command)
        second_manifest_sha = file_sha(second / "manifest.json")
        second_pin = completed_snapshot(second, args.second_conditions, second_manifest_sha)
        if audit(second, "audit_sensitivity") != second_pin:
            raise ValueError("Sensitivity results changed between snapshot and audit")
        for label, directory, pin in [
            ("original", first, first_pin),
            ("sensitivity", second, second_pin),
        ]:
            run(
                "render_" + label,
                [
                    sys.executable,
                    "tools/render_applicability_report.py",
                    str(directory),
                    "--expected-results-sha256",
                    pin,
                ],
            )
            run(
                "review_packets_" + label,
                [sys.executable, "tools/build_support_review_packets.py", str(directory)],
            )
            run(
                "cohort_analysis_" + label,
                [
                    sys.executable,
                    "tools/analyze_applicability_cohorts.py",
                    str(directory),
                    "--expected-results-sha256",
                    pin,
                ],
            )
            run(
                "cross_stage_audit_" + label,
                [sys.executable, "tools/audit_applicability_disagreements.py", str(directory)],
            )
            if file_sha(directory / "results.jsonl") != pin:
                raise ValueError("Presentation modified original experiment bytes")
        if args.include_fact_analysis:
            run(
                "fact_sensitivity_analysis",
                [
                    sys.executable,
                    "-m",
                    "tools.compare_fact_sensitivity",
                    "--before",
                    str(first),
                    "--after",
                    str(second),
                ],
            )
            if (
                file_sha(first / "results.jsonl") != first_pin
                or file_sha(second / "results.jsonl") != second_pin
            ):
                raise ValueError("Paired analysis modified original experiment bytes")
        event(
            "completed",
            first_results_sha256=first_pin,
            second_results_sha256=second_pin,
            total_conditions=args.first_conditions + args.second_conditions,
            production_change=False,
        )
    except Exception as exc:
        event("failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        helper_lock.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first-directory", required=True)
    parser.add_argument("--second-config", required=True)
    parser.add_argument("--state-directory", required=True)
    parser.add_argument("--first-conditions", type=int, required=True)
    parser.add_argument("--second-conditions", type=int, required=True)
    parser.add_argument("--resume-second", action="store_true")
    parser.add_argument("--include-fact-analysis", action="store_true")
    parser.add_argument("--tests-at-freeze", type=int)
    parser.add_argument("--wait-timeout-seconds", type=int, default=21600)
    execute(parser.parse_args())
