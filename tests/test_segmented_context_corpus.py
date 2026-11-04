"""A composite original source must retain every exact PDF segment and offset."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from occupational_fitness_rag.evaluation.comparison_corpus import verify_corpus
from occupational_fitness_rag.provenance import digest, sha256_bytes
from tools.build_segmented_context_corpus import compose_unit


@pytest.fixture
def composed():
    root = Path(__file__).resolve().parents[1]
    corpus = json.loads((root / "outputs/experiments/corpus_quality_v1/corpus.json").read_bytes())
    candidate = json.loads((root / "outputs/experiments/source_scope_review_v1/context_candidate.json").read_bytes())
    original = next(unit for unit in corpus["units"] if unit["source_id"] == candidate["target_source_id"])
    segments = []
    for part in candidate["segments"]:
        text = part.get("source_text", part.get("pdf_region_text", "")).strip()
        segments.append({
            "segment_id": part["segment_id"], "role": part["original_layout_role"],
            "source_text": text, "text_sha256": sha256_bytes(text.encode("utf-8")),
            "bbox": part["bbox"], "pdf_page": part["pdf_page"], "printed_page": part["printed_page"],
            "source_document_sha256": corpus["document_sha256"],
        })
    unit = compose_unit(original, segments)
    corpus["schema_version"] = "1.1.0"
    corpus["units"] = [unit if entry["source_id"] == unit["source_id"] else entry for entry in corpus["units"]]
    corpus["corpus_sha256"] = digest({key: value for key, value in corpus.items() if key != "corpus_sha256"})
    return root, corpus, original, unit


def test_composite_retains_the_original_criterion_and_distinct_region_locations(composed):
    root, corpus, original, unit = composed
    verify_corpus(root, corpus)
    assert unit["source_id"] == original["source_id"]
    assert unit["bbox"] == original["bbox"]
    assert unit["source_segments"][-1]["source_text"] == original["evidence_text"]
    assert "gestational" in unit["source_segments"][0]["source_text"]
    for segment in unit["source_segments"]:
        assert unit["evidence_text"][segment["composed_char_start"]:segment["composed_char_end"]] == segment["source_text"]
    assert len(corpus["units"]) == 94


@pytest.mark.parametrize("change", ["text", "rectangle", "offset", "separator", "document"])
def test_rehashed_invalid_composite_cannot_pass_original_pdf_verification(composed, change):
    root, corpus, _, unit = composed
    segment = unit["source_segments"][0]
    if change == "text":
        segment["source_text"] = "A fabricated or private-column original heading."
        segment["text_sha256"] = sha256_bytes(segment["source_text"].encode())
    elif change == "rectangle":
        segment["bbox"] = [210, 178, 295, 252]
    elif change == "offset":
        segment["composed_char_start"] += 1
    elif change == "separator":
        unit["segment_separator"] = "This generated clinical conclusion must not enter original text."
    else:
        segment["source_document_sha256"] = "wrong-original-pdf"
    corpus["corpus_sha256"] = digest({key: value for key, value in corpus.items() if key != "corpus_sha256"})
    with pytest.raises(ValueError, match="segment|composite|Composite|original"):
        verify_corpus(root, corpus)


def test_canonical_criterion_cannot_be_replaced_during_composition(composed):
    _, _, original, unit = composed
    segments = deepcopy(unit["source_segments"])
    segments[-1]["source_text"] += " Added interpretation."
    segments[-1]["text_sha256"] = sha256_bytes(segments[-1]["source_text"].encode())
    with pytest.raises(ValueError, match="canonical criterion"):
        compose_unit(original, segments)
