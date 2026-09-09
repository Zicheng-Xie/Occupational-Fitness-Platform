from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            name = f"{prefix}.{key}" if prefix else key
            out.update(_flatten(child, name))
    else:
        out[prefix] = value
    return out


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def exact_field_accuracy(
    predictions: list[dict[str, Any]], gold: list[dict[str, Any]]
) -> dict[str, Any]:
    gold_by_id = {x["case_id"]: x for x in gold}
    predictions_by_id = {x["case_id"]: x for x in predictions}
    if len(gold_by_id) != len(gold) or len(predictions_by_id) != len(predictions):
        raise ValueError("Duplicate case IDs in predictions or gold labels")
    correct = 0
    total = 0
    case_scores: dict[str, float] = {}
    for case_id in gold_by_id:
        pred = predictions_by_id.get(case_id, {})
        p = _flatten(pred.get("structured_facts", {}))
        g = _flatten(gold_by_id[case_id].get("structured_facts", {}))
        case_correct = 0
        case_total = 0
        for key, expected in g.items():
            if expected is None:
                continue
            case_total += 1
            total += 1
            if key in p and type(p[key]) is type(expected) and p[key] == expected:
                case_correct += 1
                correct += 1
        case_scores[case_id] = (case_correct / case_total) if case_total else 1.0
    return {
        "field_accuracy": (correct / total) if total else 0.0,
        "correct_fields": correct,
        "evaluated_fields": total,
        "case_scores": case_scores,
        "case_coverage": len(set(predictions_by_id) & set(gold_by_id)) / len(gold_by_id)
        if gold_by_id
        else 0.0,
        "missing_case_ids": sorted(set(gold_by_id) - set(predictions_by_id)),
        "unexpected_case_ids": sorted(set(predictions_by_id) - set(gold_by_id)),
    }
