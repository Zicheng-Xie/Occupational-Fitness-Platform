"""Standard-library contract usable by every isolated native dependency environment."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def pin(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "outputs/experiments/complex_234_ten_methods_20261027"
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


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    temp.replace(path)


def append(path, value):
    with Path(path).open("ab") as stream:
        stream.write((json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n").encode())


def verify(output, plan):
    if plan["identity"] != digest({k: v for k, v in plan.items() if k != "identity"}):
        raise ValueError("Plan self identity differs")
    for name, expected in plan["sources"].items():
        if pin(ROOT / name) != expected:
            raise ValueError("Frozen source changed: " + name)
    for name, expected in plan["prepared_files"].items():
        if pin(output / name) != expected:
            raise ValueError("Frozen query/corpus changed")
    for name, expected in plan["fact_files"].items():
        if pin(output / "facts" / name) != expected:
            raise ValueError("Frozen intake changed")
