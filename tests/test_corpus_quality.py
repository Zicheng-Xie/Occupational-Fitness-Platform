"""Reviewed layout exclusions must preserve canonical text and original history."""

from copy import deepcopy

import pytest

from occupational_fitness_rag.evaluation.corpus_quality import apply_quality_review
from occupational_fitness_rag.provenance import digest


def fixture():
    retained = {
        "source_id": "canonical-source",
        "evidence_text": "Complete synthetic original standard.",
        "cross_references": ["fragment-source"],
    }
    excluded = {
        "source_id": "fragment-source",
        "evidence_text": "Truncat... Yes No",
        "cross_references": [],
    }
    corpus = {"document_sha256": "document-pin", "units": [retained, excluded], "exclusions": []}
    corpus["corpus_sha256"] = digest(corpus)
    review = {
        "base_corpus_sha256": corpus["corpus_sha256"],
        "document_sha256": "document-pin",
        "protected_source_ids": ["canonical-source"],
        "exclusions": [
            {
                "source_id": "fragment-source",
                "unit_sha256": digest(excluded),
                "engineering_review_status": "verified_layout_failure",
                "reason": "Synthetic flowchart branch structure was lost.",
            }
        ],
    }
    return corpus, review


def test_quality_revision_preserves_original_and_complete_canonical_text():
    corpus, review = fixture()
    before = deepcopy(corpus)
    result = apply_quality_review(corpus, review)
    assert corpus == before
    assert [unit["source_id"] for unit in result["units"]] == ["canonical-source"]
    assert result["units"][0]["evidence_text"] == corpus["units"][0]["evidence_text"]
    assert result["corpus_sha256"] != corpus["corpus_sha256"]
    assert (
        digest({k: v for k, v in result.items() if k != "corpus_sha256"}) == result["corpus_sha256"]
    )
    assert result["quality_review"]["clinical_review_status"] == "pending"


def test_edges_to_quarantined_sources_remain_visible_as_unresolved():
    corpus, review = fixture()
    result = apply_quality_review(corpus, review)
    assert result["units"][0]["cross_references"] == []
    assert result["units"][0]["quarantined_cross_reference_targets"] == ["fragment-source"]
    assert result["quality_review"]["removed_cross_reference_edges"] == [
        {"from": "canonical-source", "to": "fragment-source"}
    ]


@pytest.mark.parametrize("change", ["corpus", "document", "unit"])
def test_stale_source_or_document_review_is_rejected(change):
    corpus, review = fixture()
    if change == "unit":
        review["exclusions"][0]["unit_sha256"] = "stale-pin"
    else:
        review["base_corpus_sha256" if change == "corpus" else "document_sha256"] = "stale-pin"
    with pytest.raises(ValueError, match="changed|does not match"):
        apply_quality_review(corpus, review)


def test_protected_canonical_source_cannot_be_quarantined():
    corpus, review = fixture()
    review["exclusions"][0]["source_id"] = "canonical-source"
    with pytest.raises(ValueError, match="protected canonical"):
        apply_quality_review(corpus, review)


def test_a_suggested_exclusion_is_not_treated_as_verified_engineering_review():
    corpus, review = fixture()
    review["exclusions"][0]["engineering_review_status"] = "suggested"
    with pytest.raises(ValueError, match="explicit engineering finding"):
        apply_quality_review(corpus, review)
