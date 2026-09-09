from occupational_fitness_rag.evaluation.metrics import evaluate_case
from occupational_fitness_rag.schemas.evidence_pack import (
    EvidenceItem,
    EvidencePack,
    RetrievalStatus,
)


def test_gold_metrics():
    pack = EvidencePack(
        case_id="g",
        status=RetrievalStatus.FOUND,
        filters={},
        evidence=[
            EvidenceItem(
                chunk_id="wrong",
                score=0.9,
                section="1.0",
                pages=[1],
                excerpt="x",
                source_name="s",
                source_version="v",
            ),
            EvidenceItem(
                chunk_id="target",
                score=0.8,
                section="2.0",
                pages=[5],
                excerpt="y",
                source_name="s",
                source_version="v",
            ),
        ],
    )
    m = evaluate_case(pack, ["target"], ["2.0"], [5])
    assert m["recall_at_k"] == 1.0
    assert m["mrr"] == 0.5
    assert m["section_hit"] == 1.0
    assert m["page_citation_hit"] == 1.0
