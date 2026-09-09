from __future__ import annotations

import json
from pathlib import Path

from occupational_fitness_rag.pipeline.austroads_rag import AustroadsRAGPipeline
from occupational_fitness_rag.schemas.rule_result import RuleResult

from .metrics import aggregate_metrics, evaluate_case


def run_gold_standard(path: str | Path, pipeline: AustroadsRAGPipeline) -> dict:
    rows = []
    details = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            result = RuleResult.model_validate(item["rule_result"])
            pack = pipeline.run(result)
            metrics = evaluate_case(
                pack,
                item.get("expected_chunk_ids", []),
                item.get("expected_sections", []),
                item.get("expected_pages", []),
            )
            rows.append(metrics)
            details.append({"case_id": result.case_id, **metrics, "status": pack.status.value})
    return {"aggregate": aggregate_metrics(rows), "cases": details}
