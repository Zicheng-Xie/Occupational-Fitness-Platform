"""Extract framework-reported request counters without inferring calls from caches."""

import argparse
import json
import re
from pathlib import Path

from occupational_fitness_rag.provenance import sha256_bytes, write_json


def audit_costs(output: Path):
    reports = []
    warnings = 0
    for path in sorted((output / "indexes").rglob("indexing-engine.log")):
        text = path.read_text(encoding="utf-8")
        warnings += text.count("Reached token limit - reverting to previous context state")
        for match in re.finditer(r"Metrics for ([^\n]+?): (\{.*?\n\})", text, re.DOTALL):
            metrics = json.loads(match.group(2))
            reports.append(
                {
                    "provider_model": match.group(1),
                    "metrics": metrics,
                    "log_path": str(path.relative_to(output)),
                    "log_sha256": sha256_bytes(path.read_bytes()),
                    "scope": "Framework provider counters emitted at worker shutdown",
                }
            )
    # One worker process emits cumulative provider metrics. Summing duplicate
    # snapshots would inflate request counts, so refuse ambiguous logs.
    names = [r["provider_model"] for r in reports]
    unambiguous = len(names) == len(set(names))
    chat = [r for r in reports if r["provider_model"].startswith("ollama_chat/")]
    result = {
        "graphrag": {
            "reports": reports,
            "attempted_graph_model_requests": sum(
                r["metrics"]["attempted_request_count"] for r in chat
            )
            if reports and unambiguous
            else None,
            "status": "framework_reported"
            if reports and unambiguous
            else "unavailable_or_ambiguous",
            "context_budget_warnings": warnings,
            "warning_interpretation": "Local graph context was budget-limited; this is not a failed source mapping or silent fallback",
        },
        "lightrag": {
            "attempted_graph_model_requests": None,
            "status": "Exact network attempts unavailable; cache entries are not request counters",
        },
    }
    write_json(output / "framework_cost_audit.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    print(json.dumps(audit_costs(parser.parse_args().output), indent=2))
