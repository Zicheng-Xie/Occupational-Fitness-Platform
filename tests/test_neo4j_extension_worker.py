from copy import deepcopy

import pytest

from tools import neo4j_extension_worker as worker


def unit(
    sid="one",
    module="blackout",
    text="Commercial standard.\nIf symptoms recur, obtain review.\nUnless a specialist confirms otherwise.",
):
    return {
        "source_id": sid,
        "module": module,
        "licence_context": "commercial",
        "evidence_text": text,
        "text_sha256": worker.text_sha(text),
        "pdf_page": 70,
        "cross_references": [],
        "covers_source_ids": [],
    }


def request():
    return {
        "experiment_identity": "a" * 64,
        "corpus": {"units": [unit()]},
        "corpus_vectors": [[0.2, 0.3]],
        "queries": [
            {
                "query_id": "q",
                "case_id": "case",
                "module": "blackout",
                "licence_context": "commercial",
                "query": "No blackout reported: false | 0 episodes.",
            }
        ],
        "query_vectors": {"q": [0.4, 0.5]},
        "config": {"embedding_dimensions": 2},
    }


def test_literal_condition_and_exception_anchors_have_exact_source_bounds():
    source = unit()
    anchors, edges = worker.source_relations([source])
    assert [a["kind"] for a in anchors] == ["condition", "exception"]
    assert not edges
    for anchor in anchors:
        assert source["evidence_text"][anchor["char_start"] : anchor["char_end"]] == anchor["text"]
        assert source["evidence_text"].splitlines()[anchor["line_start"] - 1] == anchor["text"]
        assert anchor["review_status"] == "engineering_anchor_pending_clinical_review"


def test_shared_literal_anchors_are_module_scoped_and_originals_unchanged():
    sources = [unit(), unit("two"), unit("different", "diabetes")]
    before = deepcopy(sources)
    anchors, _ = worker.source_relations(sources)
    by_source = {
        sid: [a["anchor_id"] for a in anchors if a["source_id"] == sid]
        for sid in ("one", "two", "different")
    }
    assert by_source["one"] == by_source["two"]
    assert set(by_source["one"]).isdisjoint(by_source["different"])
    assert sources == before


def test_containment_requires_complete_literal_source_text_and_same_page():
    child = unit("child", text="If symptoms recur, obtain review.")
    parent = unit("parent")
    parent["covers_source_ids"] = ["child"]
    _, edges = worker.source_relations([child, parent])
    assert edges == [
        {"source_id": "parent", "target_id": "child", "relationship": "CONTAINS_ORIGINAL"}
    ]
    child["pdf_page"] = 71
    with pytest.raises(ValueError, match="complete original text"):
        worker.source_relations([child, parent])


def test_curated_related_metadata_does_not_become_an_explicit_reference():
    source = unit("source", text="If the person has had one blackout.")
    target = {**unit("target"), "section": "1.3"}
    source.update(cross_references=["target"], explicit_section_references=[], section="1.2")
    assert worker.source_relations([source, target])[1] == []
    source["explicit_section_references"] = ["1.3"]
    assert worker.source_relations([source, target])[1] == []
    source["evidence_text"] += " Refer to section 1.3."
    assert worker.source_relations([source, target])[1] == [
        {"source_id": "source", "target_id": "target", "relationship": "EXPLICIT_SECTION_REFERENCE"}
    ]


@pytest.mark.parametrize("change", ["scope", "sha", "vector", "query_inventory"])
def test_invalid_frozen_input_is_rejected_before_native_indexing(change):
    data = request()
    if change == "scope":
        data["corpus"]["units"][0]["licence_context"] = "private"
    elif change == "sha":
        data["corpus"]["units"][0]["evidence_text"] += " changed"
    elif change == "vector":
        data["query_vectors"]["q"] = [True, 0.3]
    else:
        data["query_vectors"]["extra"] = [0.2, 0.4]
    with pytest.raises(ValueError):
        worker.validate_input(data)


def test_lucene_backend_tokens_preserve_negation_and_numeric_zero():
    data = request()
    worker.validate_input(data)
    text = data["queries"][0]["query"]
    assert worker.lexical_query(text) == "no blackout reported false 0 episodes"
    assert data["queries"][0]["query"] == text


def test_native_source_mapping_does_not_substitute_or_expand_scope():
    sources = {u["source_id"]: u for u in [unit(), unit("other", "diabetes")]}
    row = {
        "source_id": "one",
        "seed_source_id": "one",
        "text_sha256": sources["one"]["text_sha256"],
        "score": 0.8,
        "graph_path": "native_hybrid_seed",
    }
    result = worker.aggregate([row, {**row, "score": 0.7}], sources, "blackout")
    assert len(result) == 1 and result[0]["score"] == 0.8
    with pytest.raises(ValueError, match="out-of-scope"):
        worker.aggregate([{**row, "seed_source_id": "other"}], sources, "blackout")
    with pytest.raises(ValueError, match="no original evidence"):
        worker.aggregate([], sources, "blackout")


def test_graph_namespaces_use_full_experiment_identity():
    first = worker.graph_namespace("a" * 64, "blackout")
    second = worker.graph_namespace("a" * 63 + "b", "blackout")
    assert first != second
    with pytest.raises(ValueError, match="Unsafe"):
        worker.graph_namespace("a" * 64, "blackout` MATCH (n) DELETE n")
