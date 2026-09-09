from __future__ import annotations

from statistics import mean

from occupational_fitness_rag.schemas.evidence_pack import EvidencePack


def evaluate_case(
    pack: EvidencePack,
    expected_chunk_ids: list[str] | None = None,
    expected_sections: list[str] | None = None,
    expected_pages: list[int] | None = None,
) -> dict[str, float]:
    expected_chunk_ids = expected_chunk_ids or []
    expected_sections = expected_sections or []
    expected_pages = expected_pages or []
    retrieved_ids = [item.chunk_id for item in pack.evidence]

    recall = 0.0
    mrr = 0.0
    if expected_chunk_ids:
        expected = set(expected_chunk_ids)
        hits = [cid for cid in retrieved_ids if cid in expected]
        recall = len(set(hits)) / len(expected)
        ranks = [i + 1 for i, cid in enumerate(retrieved_ids) if cid in expected]
        mrr = 1.0 / min(ranks) if ranks else 0.0

    section_hit = (
        float(bool(set(expected_sections) & {item.section for item in pack.evidence}))
        if expected_sections
        else 0.0
    )
    retrieved_pages = {page for item in pack.evidence for page in item.pages}
    page_hit = float(bool(set(expected_pages) & retrieved_pages)) if expected_pages else 0.0

    return {
        "recall_at_k": recall,
        "mrr": mrr,
        "section_hit": section_hit,
        "page_citation_hit": page_hit,
    }


def aggregate_metrics(rows: list[dict[str, float]]) -> dict[str, float]:
    if not rows:
        return {}
    keys = rows[0].keys()
    return {key: mean(row[key] for row in rows) for key in keys}
