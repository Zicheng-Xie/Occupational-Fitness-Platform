import pytest

from occupational_fitness_rag.schemas.evidence_pack import (
    EvidenceItem,
    EvidencePack,
    RetrievalStatus,
)


def test_evidence_pack_is_frozen():
    pack = EvidencePack(
        case_id="x",
        status=RetrievalStatus.FOUND,
        filters={"category": "vision"},
        evidence=[
            EvidenceItem(
                chunk_id="c",
                score=1.0,
                section="2.1",
                pages=[20],
                excerpt="evidence",
                source_name="source",
                source_version="v1",
            )
        ],
    )
    with pytest.raises(Exception):
        pack.status = RetrievalStatus.NO_EVIDENCE
