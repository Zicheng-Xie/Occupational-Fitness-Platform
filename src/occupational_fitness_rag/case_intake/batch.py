from __future__ import annotations

import json
from pathlib import Path

from .adapters import to_condition_map, to_structured_case
from .extractor import extract_case_file
from .models import CaseIntakeResult


def prepare_case_directory(input_dir: str | Path) -> list[CaseIntakeResult]:
    input_dir = Path(input_dir)
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Case input directory not found: {input_dir}")
    paths = sorted(input_dir.glob("*.txt"))
    if not paths:
        raise ValueError(f"No .txt case inputs found: {input_dir}")
    return [extract_case_file(path) for path in paths]


def write_results_jsonl(results: list[CaseIntakeResult], output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(result.model_dump(mode="json"), ensure_ascii=False) + "\n")


def write_workflow_artifacts(
    results: list[CaseIntakeResult],
    structured_output: str | Path,
    condition_output: str | Path,
) -> None:
    structured_output = Path(structured_output)
    condition_output = Path(condition_output)
    structured_output.parent.mkdir(parents=True, exist_ok=True)
    condition_output.parent.mkdir(parents=True, exist_ok=True)
    with (
        structured_output.open("w", encoding="utf-8") as sf,
        condition_output.open("w", encoding="utf-8") as cf,
    ):
        for result in results:
            sf.write(to_structured_case(result).model_dump_json() + "\n")
            cf.write(json.dumps(to_condition_map(result), ensure_ascii=False) + "\n")
