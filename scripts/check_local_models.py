"""Opt-in local model integration check; only synthetic input is sent."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from occupational_fitness_rag.llm import OllamaClient
from occupational_fitness_rag.pipeline.config import LLMConfig
from occupational_fitness_rag.provenance import write_json

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="llama3:8b")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()
    client = OllamaClient(LLMConfig(enabled=True, model=args.model, timeout_seconds=args.timeout))
    start = perf_counter()
    report = {
        "model": args.model,
        "timeout_seconds": args.timeout,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "clinical_validation": False,
        "test_scope": "One fixed synthetic structured-extraction request, not a model accuracy benchmark.",
    }
    try:
        result = client.extract(
            "Synthetic demonstration case. No diabetes.", {"diabetes.present": {"type": "boolean"}}
        )
        correct = any(
            p["field"] == "diabetes.present" and p["value"] is False for p in result["proposals"]
        )
        if not correct or result["rejected"]:
            raise ValueError("Local model did not return the expected exact-source proposal")
        report.update(status="passed", extraction_result=result)
    except Exception as exc:
        report.update(status="unavailable_or_failed", error_type=type(exc).__name__)
    report["elapsed_seconds"] = round(perf_counter() - start, 3)
    write_json(ROOT / "outputs/evaluation/local_model_check.json", report)
    print(f"Local structured extraction check: {report['status']}")
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
