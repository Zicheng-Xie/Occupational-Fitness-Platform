"""Submit and audit a real local-model integration matrix, not an accuracy study."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from urllib.request import Request, urlopen

from tools.complex_ten_contract import write_json
from tools.serve_retrieval_judgments import DEFAULT, MODELS, REPORTS, dataset


def api(path, body=None):
    request = Request("http://127.0.0.1:8781" + path,
                      data=json.dumps(body).encode() if body else None,
                      headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=45) as response:
        return json.load(response)


def conditions():
    v7 = "scope88_prefix_criterion_v6__literal_facets"
    v9 = "neo4j_frontier_criterion_v3__literal_facets"
    data = dataset(REPORTS["refinement"])
    for query in data["queries"].values():
        if query["case_id"] not in {"CX-HTN-01", "CX-VIS-01", "CX-HEAR-01", "CX-BLK-01", "CX-DM-01"}:
            continue
        for model in MODELS:
            for k in (5, 10):
                yield {"dataset": "refinement", "query_id": query["query_id"],
                       "method": v7, "model": model, "top_k": k,
                       "evidence_mode": "strict_topk"}
    for case in ("VAL-MIX-02", "VAL-MIX-06"):
        for method in (v7, v9):
            for model in MODELS:
                for k in (5, 10):
                    yield {"dataset": "refinement", "query_id": "CASE:" + case,
                           "method": method, "model": model, "top_k": k,
                           "evidence_mode": "strict_topk"}
    data = dataset(REPORTS["ten-methods"])
    q = next(q for q in data["queries"].values() if q["case_id"] == "CX-DM-01")
    for method in dict.fromkeys(r["method"] for r in data["rankings"].values()):
        yield {"dataset": "ten-methods", "query_id": q["query_id"], "method": method,
               "model": MODELS[1], "top_k": 5, "evidence_mode": "strict_topk"}
    # Explicit target outside Top K, cross-module hops, cycles and missing chapters.
    for case in ("CX-VIS-01", "CX-HTN-01"):
        q = next(q for q in dataset(REPORTS["refinement"])["queries"].values()
                 if q["case_id"] == case)
        yield {"dataset": "refinement", "query_id": q["query_id"], "method": v7,
               "model": MODELS[1], "top_k": 5, "evidence_mode": "explicit_references"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submit", action="store_true")
    args = parser.parse_args()
    path = DEFAULT / "integration_matrix.json"
    if args.submit:
        planned = list(conditions())
        jobs = []
        for condition in planned:
            record = api("/api/reviews", condition)
            jobs.append({"id": record["id"], "condition": condition})
        write_json(path, {"purpose": "Real-model integration checks; no accuracy claim",
                          "planned": len(planned), "jobs": jobs})
    matrix = json.loads(path.read_bytes())
    records = [api("/api/reviews/" + job["id"]) for job in matrix["jobs"]]
    summary = {
        "planned": matrix["planned"], "status": dict(Counter(r["status"] for r in records)),
        "all_terminal": all(r["status"] not in {"queued", "running"} for r in records),
        "models": dict(Counter(r["condition"]["model"] for r in records)),
        "outcomes": dict(Counter(r.get("result", {}).get("outcome", "no_accepted_result") for r in records)),
        "warning_counts": dict(Counter(w for r in records for w in r.get("result", {}).get("validation_warnings", []))),
        "rows": [{k: r.get(k) for k in ("id", "condition", "case_id", "module", "status", "error", "seconds", "result")}
                 for r in records],
        "accuracy_claim": False,
    }
    write_json(DEFAULT / "integration_summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))


if __name__ == "__main__":
    main()
