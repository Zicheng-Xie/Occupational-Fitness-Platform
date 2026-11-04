"""Submit one exact retrieval condition and inspect its persisted local review.

First start scripts/start_retrieval_review.ps1. No patient text or answer key is
sent by this client: the server resolves the frozen report observation itself.
"""

import json
from urllib.request import Request, urlopen


def submit(query_id, method, dataset="refinement", top_k=5, model="llama3:8b"):
    condition = {"dataset": dataset, "query_id": query_id, "method": method,
                 "top_k": top_k, "model": model, "evidence_mode": "strict_topk"}
    request = Request("http://127.0.0.1:8781/api/reviews",
                      data=json.dumps(condition).encode(),
                      headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def inspect(identity):
    with urlopen("http://127.0.0.1:8781/api/reviews/" + identity, timeout=10) as response:
        return json.load(response)


if __name__ == "__main__":
    job = submit("CASE:VAL-MIX-02", "scope88_prefix_criterion_v6__literal_facets")
    print(json.dumps({"id": job["id"], "status": job["status"]}, indent=2))
    print("Use inspect(job_id) to poll. Complete evidence and model output are persisted.")
