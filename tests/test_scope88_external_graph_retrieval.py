"""Native graph reuse requires identical module documents and actual queries."""

from copy import deepcopy

import pytest

from tools.run_scope88_external_graph_retrieval import import_unchanged_modules


def inputs():
    modules = ["blackout", "hypertension", "diabetes", "hearing", "vision"]
    old_units = [{"source_id": m, "module": m, "evidence_text": "Original " + m} for m in modules]
    old_units.append(
        {"source_id": "private-vision", "module": "vision", "evidence_text": "Private fragment"}
    )
    old_corpus = {"units": old_units}
    corpus = {"units": old_units[:-1]}
    old_queries = [
        {
            "query_id": "old-" + m,
            "module": m,
            "query": "Clinical query " + m,
            "corpus_sha256": "old94",
            "query_audit": {"fact": False},
        }
        for m in modules
    ]
    queries = [
        {**q, "query_id": "new-" + q["module"], "corpus_sha256": "new88"} for q in old_queries
    ]
    lineage = {q["query_id"]: {"parent_query_id": "old-" + q["module"]} for q in queries}
    rows = [
        {
            "query_id": q["query_id"],
            "method": method,
            "experiment_identity": "real-old-index",
            "status": "completed",
            "source_ids": [q["module"]],
        }
        for q in old_queries
        for method in ("lightrag", "graphrag")
    ]
    return corpus, queries, lineage, old_corpus, old_queries, rows


def test_unchanged_module_reuse_preserves_original_real_records_and_excludes_vision():
    args = inputs()
    before = deepcopy(args)
    unchanged, originals, mapped = import_unchanged_modules(*args)
    assert set(unchanged) == {"blackout", "hypertension", "diabetes", "hearing"}
    assert len(originals) == len(mapped) == 8
    assert all(r["module"] != "vision" for r in mapped)
    assert all(r["corpus_sha256"] == "new88" and r["actual_new_model_calls"] == 0 for r in mapped)
    assert all(r["parent_experiment_identity"] == "real-old-index" for r in mapped)
    assert args == before


def test_changed_fact_or_literal_query_cannot_reuse_old_native_result():
    args = inputs()
    args[1][0]["query_audit"] = {"fact": True}
    with pytest.raises(ValueError, match="different literal query or fact"):
        import_unchanged_modules(*args)


def test_changed_module_original_requires_native_reconstruction():
    args = inputs()
    args[0]["units"] = deepcopy(args[0]["units"])
    args[0]["units"][0]["evidence_text"] = "Different actual clause"
    with pytest.raises(ValueError, match="exactly four unchanged"):
        import_unchanged_modules(*args)


def test_failed_native_result_is_not_imported_as_a_success():
    args = inputs()
    args[-1][0]["status"] = "retrieval_failed"
    with pytest.raises(ValueError, match="failed native"):
        import_unchanged_modules(*args)
