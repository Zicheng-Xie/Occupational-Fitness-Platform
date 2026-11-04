"""Exercise experiment freeze/resume and failure paths without local model calls."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from occupational_fitness_rag.evaluation import passage_comparison as comparison
from occupational_fitness_rag.evaluation import passage_judgment as protocol
from occupational_fitness_rag.provenance import digest, write_json


@pytest.fixture
def experiment(tmp_path):
    baseline = tmp_path / "baseline"
    baseline.mkdir()
    source = {
        "source_id": "fixture-source",
        "module": "vision",
        "pdf_page": 1,
        "section": "1.1",
        "printed_page": 1,
        "source_text": "Synthetic original criterion requires a provisional hold pending review.",
    }
    payload = {
        "licence_context": "commercial",
        "modules": ["vision"],
        "nurse_note": "An observed visual indicator requires review. Other unrelated context is lengthy.",
        "verified_patient_facts": {
            "vision.indicator": {"value": True, "patient_quotes": ["observed visual indicator"]}
        },
        "guideline_evidence": [{k: v for k, v in source.items() if k != "module"}],
    }
    rows = [
        {
            "case_id": "fixture-case",
            "method": method,
            "input_snapshot": payload,
            "reference_outcome": "temporarily_unfit",
            "rule_result": "never-send-rule-sentinel",
        }
        for method in ["hybrid", "reference_evidence"]
    ]
    (baseline / "results.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    write_json(
        baseline / "corpus.json",
        {
            "corpus_sha256": "fixture-corpus",
            "units": [
                {**source, "evidence_text": source["source_text"], "licence_context": "commercial"}
            ],
        },
    )
    write_json(baseline / "manifest.json", {})
    write_json(baseline / "model_inventory.json", {"fixture-model": "judge-pin"})
    config = yaml.safe_load(
        Path("configs/experiments/passage_comparison.yaml").read_text(encoding="utf-8")
    )
    config.update(
        baseline_dir=str(baseline),
        output=str(tmp_path / "output"),
        case_ids=["fixture-case"],
        models=["fixture-model"],
        expected_model_digests={"fixture-model": "judge-pin"},
        embedding_model="fixture-embedding",
        embedding_model_digest="embedding-pin",
        embedding_dimensions=2,
    )
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path, config, payload


def get(config):
    def call(endpoint, path):
        if path == "/api/tags":
            return {
                "models": [
                    {"name": "fixture-model", "digest": "judge-pin"},
                    {"name": "fixture-embedding", "digest": "embedding-pin"},
                ]
            }
        return {"version": config["expected_runtime_version"]}

    return call


def model_post(calls):
    def post(endpoint, path, body, timeout):
        calls.append(deepcopy((path, body)))
        if path == "/api/embed":
            return {"embeddings": [[1.0, 0.0] for _ in body["input"]]}
        payload = json.loads(body["messages"][1]["content"])
        source = payload["guideline_evidence"][0]
        check = {
            "module": "vision",
            "fact_fields": ["vision.indicator"],
            "licence_pathway": "temporary_no_driving",
            "finding": "established_restriction",
            "conclusion": "The observed condition requires review.",
        }
        if "PassageCheck" in body["format"]["$defs"]:
            check["passage_id"] = source["passage_id"]
        else:
            check.update(source_id=source["source_id"], guideline_quote=source["source_text"])
        result = {
            "assessment_outcome": "temporarily_unfit",
            "explanation": "The synthetic original and recorded finding support a provisional hold.",
            "criterion_checks": [check],
        }
        return {
            "done": True,
            "done_reason": "stop",
            "message": {"content": json.dumps(result)},
            "prompt_eval_count": 100,
            "eval_count": 80,
        }

    return post


def test_fresh_retrieval_freezes_then_resume_records_exact_conditions(experiment):
    path, config, _ = experiment
    calls = []
    kwargs = {"post": model_post(calls), "get": get(config)}
    result = comparison.run_comparison(path, retrieval_only=True, **kwargs)
    assert result["retrieval_frozen"] and result["judgment_conditions"] == 0
    assert not any(route == "/api/chat" for route, _ in calls)
    result = comparison.run_comparison(path, resume=True, max_conditions=2, **kwargs)
    assert result["recorded_conditions"] == 2 and result["execution_status"] == "partial"
    result = comparison.run_comparison(path, resume=True, **kwargs)
    assert result["recorded_conditions"] == result["planned_conditions"] == 6
    assert result["execution_status"] == "completed"
    assert sum(route == "/api/chat" for route, _ in calls) == 6
    rows = comparison.read_records(Path(config["output"]) / "results.jsonl")
    assert len({comparison.condition_key(row) for row in rows}) == 6
    assert all(row["reference_agreement"] for row in rows)
    for route, body in calls:
        if route == "/api/chat":
            text = json.dumps(body)
            assert "never-send-rule-sentinel" not in text and "reference_outcome" not in text
    assert all(m["model_attempts"] == 1 for m in result["metrics"])


def test_truncated_tail_rejects_before_network_and_preserves_bytes(experiment):
    path, config, _ = experiment
    target = Path(config["output"])
    target.mkdir()
    raw = b'{"unfinished":'
    (target / "results.jsonl").write_bytes(raw)

    def prohibited(*args):
        raise AssertionError("No network call is permitted after a detected incomplete tail")

    with pytest.raises(ValueError, match="Incomplete JSONL"):
        comparison.run_comparison(path, resume=True, get=prohibited)
    assert (target / "results.jsonl").read_bytes() == raw
    assert not (target / "manifest.json").exists()


def test_changed_configuration_cannot_reuse_frozen_retrieval(experiment):
    path, config, _ = experiment
    kwargs = {"post": model_post([]), "get": get(config)}
    comparison.run_comparison(path, retrieval_only=True, **kwargs)
    saved = (Path(config["output"]) / "retrieval_freeze.json").read_bytes()
    config["output_tokens"] += 1
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    with pytest.raises(ValueError, match="identity changed"):
        comparison.run_comparison(path, resume=True, **kwargs)
    assert (Path(config["output"]) / "retrieval_freeze.json").read_bytes() == saved


def test_provenance_failure_cannot_be_accepted_or_repaired(experiment):
    _, config, payload = experiment
    payload["guideline_evidence"][0]["module"] = "vision"

    class BrokenLocations:
        build_request = staticmethod(protocol.build_request)
        parse_response = staticmethod(protocol.parse_response)
        output_consistency_flags = staticmethod(protocol.output_consistency_flags)

        @staticmethod
        def criterion_locations(answer, payload):
            raise ValueError("Original location unavailable")

    calls = []
    result = comparison.run_condition(
        config, "fixture-model", payload, "passage_selection", model_post(calls), BrokenLocations
    )
    assert result["status"] == "failed" and len(calls) == 1
    assert result["attempts"][0]["status"] == "failed"
    assert result["attempts"][0]["failure_stage"] == "provenance"
    assert "answer" not in result


@pytest.mark.parametrize("raw", [[], {"message": None}, {"message": {"content": 17}}])
def test_malformed_provider_envelope_is_retained_without_repair(experiment, raw):
    _, config, payload = experiment
    payload["guideline_evidence"][0]["module"] = "vision"
    calls = []

    def post(*args, **kwargs):
        calls.append(1)
        return raw

    result = comparison.run_condition(config, "fixture-model", payload, "passage_selection", post)
    assert result["status"] == "failed" and len(calls) == 1
    assert result["attempts"][0]["raw_response"] == raw
    assert result["attempts"][0]["failure_stage"] == "provider_response"


def test_full_request_budget_applies_before_post_even_when_payload_fits(experiment):
    _, config, payload = experiment
    payload["guideline_evidence"][0]["module"] = "vision"
    config["request_max_bytes"] = len(comparison.json_bytes(payload)) + 10
    calls = []
    result = comparison.run_condition(
        config, "fixture-model", payload, "passage_selection", model_post(calls)
    )
    assert result["status"] == "failed" and calls == []
    assert "serialized request" in result["error"]


def test_changed_model_pin_prevents_any_embedding_or_judgment(experiment):
    path, config, _ = experiment
    config["embedding_model_digest"] = "different-pin"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    calls = []
    with pytest.raises(ValueError, match="digest differs"):
        comparison.run_comparison(path, post=model_post(calls), get=get(config))
    assert calls == []


@pytest.mark.parametrize("vector", [[0.0, 0.0], [1.0], [True, 0.0]])
def test_invalid_cached_vectors_are_rejected_before_ranking(experiment, vector):
    _, config, _ = experiment
    output = Path(config["output"])
    output.mkdir()
    vectors = [vector]
    write_json(
        output / "embeddings.json",
        {"identity": "fixture-cache", "vectors": vectors, "vectors_sha256": digest(vectors)},
    )
    retriever = comparison.HybridRetriever(
        {
            "units": [
                {
                    "source_id": "fixture-source",
                    "evidence_text": "Synthetic original.",
                    "module": "vision",
                }
            ]
        },
        config,
        output,
        "fixture-cache",
    )
    with pytest.raises(ValueError, match="Embedding has invalid"):
        retriever.ensure_vectors()
    assert retriever.vectors is None


def test_reviewed_override_cannot_remove_a_reference_control_source(experiment):
    _, config, _ = experiment
    baseline = Path(config["baseline_dir"])
    original = json.loads((baseline / "corpus.json").read_text(encoding="utf-8"))
    original["document_sha256"] = "fixture-document"
    write_json(baseline / "corpus.json", original)
    revised = {
        **original,
        "units": [],
        "quality_review": {
            "base_corpus_sha256": original["corpus_sha256"],
            "excluded_source_ids": ["fixture-source"],
        },
    }
    revised.pop("corpus_sha256")
    revised["corpus_sha256"] = digest(revised)
    path = baseline.parent / "reviewed-corpus.json"
    write_json(path, revised)
    with pytest.raises(ValueError, match="reference-control source"):
        comparison.load_frozen_inputs(baseline, ["fixture-case"], path)
