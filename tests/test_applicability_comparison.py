"""Test frozen-input, stage-failure and paired-inference contracts without a local model."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from occupational_fitness_rag.evaluation import applicability_comparison as experiment
from occupational_fitness_rag.evaluation import passage_comparison
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json


@pytest.fixture
def frozen(tmp_path):
    root = tmp_path / "retrieval"
    root.mkdir()
    source = {
        "source_id": "fixture-source",
        "module": "vision",
        "pdf_page": 1,
        "printed_page": 1,
        "section": "1.1",
        "source_text": "Synthetic original criterion requires a provisional hold pending review.",
    }
    payload = {
        "licence_context": "commercial",
        "modules": ["vision"],
        "nurse_note": "An observed visual indicator requires review.",
        "verified_patient_facts": {
            "vision.indicator": {"value": True, "patient_quotes": ["observed visual indicator"]}
        },
        "guideline_evidence": [source],
    }
    corpus = {
        "document_sha256": "synthetic-document",
        "units": [
            {**source, "evidence_text": source["source_text"], "licence_context": "commercial"}
        ],
    }
    corpus["corpus_sha256"] = digest(corpus)
    config = yaml.safe_load(Path("configs/experiments/applicability_comparison.yaml").read_text())
    config.update(
        retrieval_dir=str(root),
        output=str(tmp_path / "output"),
        case_ids=["fixture-case"],
        models=["fixture-model"],
        expected_model_digests={"fixture-model": "judge-pin"},
        embedding_model="fixture-embedding",
        embedding_model_digest="embedding-pin",
        repeats=2,
        expected_corpus_sha256=corpus["corpus_sha256"],
    )
    inputs = {
        "fixture-case": {
            "payload": payload,
            "reference_payload": payload,
            "reference_outcome": "temporarily_unfit",
            "rule_result": "never-send-rule-or-label-sentinel",
        }
    }
    sources = {"first_party_source": {"synthetic": "fixture"}}
    upstream_config = {**config, "protocols": ["passage_selection"], "repeats": 1}
    identity_data = {
        "config": upstream_config,
        "config_sha256": digest(upstream_config),
        "sources_sha256": digest(sources),
        "historical_fingerprints": {},
        "environment": {},
        "patient_inputs_sha256": digest(inputs),
        "corpus_sha256": corpus["corpus_sha256"],
        "planned_keys": [],
    }
    identity = digest(identity_data)
    config["expected_retrieval_identity"] = identity
    write_json(root / "manifest.json", {**identity_data, "identity": identity})
    write_json(root / "source_snapshot.json", sources)
    write_json(root / "frozen_inputs.json", inputs)
    write_json(root / "corpus.json", corpus)
    write_json(root / "retrieval.json", {"identity": identity, "records": []})
    write_json(root / "embeddings.json", {"identity": identity, "vectors": []})
    write_json(
        root / "payloads.json",
        {
            "fixture-case": {
                policy: {
                    "status": "completed",
                    "payload": payload,
                    "input_sha256": digest(payload),
                    "selection": {"policy": policy},
                }
                for policy in config["evidence_policies"]
            }
        },
    )
    write_json(
        root / "retrieval_freeze.json",
        {
            "identity": identity,
            "artifacts": {
                name: sha256_bytes((root / name).read_bytes())
                for name in ["retrieval.json", "payloads.json", "embeddings.json"]
            },
        },
    )
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path, config, payload


def get(config):
    def call(endpoint, route):
        if route == "/api/tags":
            return {
                "models": [
                    {"name": "fixture-model", "digest": "judge-pin"},
                    {"name": "fixture-embedding", "digest": "embedding-pin"},
                ]
            }
        return {"version": config["expected_runtime_version"]}

    return call


def post_model(calls):
    def post(endpoint, route, body, timeout):
        assert route == "/api/chat", "Frozen retrieval must not invoke embeddings"
        calls.append(deepcopy(body))
        payload = json.loads(body["messages"][1]["content"])
        source = payload["guideline_evidence"][0]
        check = {
            "module": "vision",
            "passage_id": source["passage_id"],
            "fact_fields": ["vision.indicator"],
            "licence_pathway": "temporary_no_driving",
            "finding": "established_restriction",
            "conclusion": "The observed condition requires review.",
        }
        fields = body["format"]["properties"]
        if "passages" in fields:
            check.update(
                statement_type="restriction",
                applicability="applicable",
                prerequisites=[],
                numeric_application="Not applicable",
            )
            answer = {
                "passages": {
                    "P1": {
                        key: value
                        for key, value in check.items()
                        if key not in {"module", "passage_id"}
                    }
                }
            }
        else:
            answer = {
                "assessment_outcome": "temporarily_unfit",
                "explanation": "The verified observation and original criterion support review.",
            }
            if "decisive_passage_ids" in fields:
                answer["decisive_passage_ids"] = [source["passage_id"]]
            else:
                answer["criterion_checks"] = [check]
        return {
            "done": True,
            "done_reason": "stop",
            "message": {"content": json.dumps(answer)},
            "prompt_eval_count": 100,
            "eval_count": 80,
        }

    return post


def test_resume_keeps_frozen_inputs_and_records_all_stages_without_label_leaks(frozen):
    path, config, _ = frozen
    calls = []
    kwargs = {"post": post_model(calls), "get": get(config)}
    result = experiment.run_comparison(path, max_conditions=2, **kwargs)
    assert result["recorded_conditions"] == 2 and result["execution_status"] == "partial"
    result = experiment.run_comparison(path, resume=True, **kwargs)
    assert result["recorded_conditions"] == result["planned_conditions"] == 8
    assert result["execution_status"] == "completed" and len(calls) == 12
    assert result["model_attempts"] == 12
    assert result["paired_transition_counts"] == {"accepted_both_correct": 4}
    rows = passage_comparison.read_records(Path(config["output"]) / "results.jsonl")
    assert all(row["reference_agreement"] for row in rows)
    for body in calls:
        serialized = json.dumps(body)
        assert "reference_outcome" not in serialized
        assert "never-send-rule-or-label-sentinel" not in serialized
    staged = [row for row in rows if row["protocol"] == "applicability_first"]
    assert all(set(row["stages"]) == {"applicability", "aggregation"} for row in staged)
    assert all(row["model_attempts"] == 2 for row in staged)
    assert all(row["first_pass_status"] == "completed" for row in staged)


def test_hash_tampering_is_detected_before_network_or_output(frozen):
    path, config, _ = frozen
    target = Path(config["retrieval_dir"]) / "payloads.json"
    target.write_bytes(target.read_bytes() + b" ")
    with pytest.raises(ValueError, match="artifact hash changed"):
        experiment.run_comparison(path, get=lambda *_: pytest.fail("Network prohibited"))
    assert not Path(config["output"]).exists()


def test_incomplete_tail_is_never_appended_or_rewritten(frozen):
    path, config, _ = frozen
    output = Path(config["output"])
    output.mkdir()
    (output / "results.jsonl").write_bytes(b'{"unfinished":')
    with pytest.raises(ValueError, match="Incomplete JSONL"):
        experiment.run_comparison(path, get=lambda *_: pytest.fail("Network prohibited"))
    assert (output / "results.jsonl").read_bytes() == b'{"unfinished":'
    assert not (output / "manifest.json").exists()


def test_changed_source_or_config_rejects_resume(frozen, monkeypatch):
    path, config, _ = frozen
    kwargs = {"get": get(config), "post": post_model([])}
    experiment.run_comparison(path, max_conditions=0, **kwargs)
    original = experiment.previous.source_snapshot
    monkeypatch.setattr(
        experiment.previous,
        "source_snapshot",
        lambda text: {
            **original(text),
            "extra_source_change": True,
        },
    )
    with pytest.raises(ValueError, match="identity changed"):
        experiment.run_comparison(path, resume=True, **kwargs)


@pytest.mark.parametrize(
    "raw",
    [
        [],
        {"message": None},
        {"message": {"content": 17}},
        {"done_reason": "length", "message": {"content": "{}"}},
    ],
)
def test_invalid_provider_does_not_run_second_stage_or_repair(frozen, raw):
    _, config, payload = frozen
    calls = []

    def post(*args, **kwargs):
        calls.append(1)
        return raw

    result = experiment.run_applicability(config, "fixture-model", payload, post)
    assert result["status"] == "failed" and calls == [1]
    assert result["model_attempts"] == 1 and "aggregation" not in result["stages"]
    assert result["stages"]["applicability"]["attempts"][0]["raw_response"] == raw
    assert "answer" not in result


def test_stage_provenance_failure_cannot_be_repaired_or_accepted(frozen):
    from occupational_fitness_rag.evaluation import applicability_judgment as protocol

    _, config, payload = frozen

    class BrokenLocations:
        build_applicability_request = staticmethod(protocol.build_applicability_request)
        parse_applicability_response = staticmethod(protocol.parse_applicability_response)

        @staticmethod
        def review_locations(*args):
            raise ValueError("Original source region unavailable")

    calls = []
    result = experiment.run_applicability(
        config, "fixture-model", payload, post_model(calls), BrokenLocations
    )
    assert result["status"] == "failed" and len(calls) == 1
    assert result["stages"]["applicability"]["attempts"][0]["failure_stage"] == "provenance"
    assert "answer" not in result


def test_review_repair_is_visible_and_first_pass_pipeline_remains_failed(frozen):
    _, config, payload = frozen
    calls = []
    valid = post_model(calls)

    def post(*args, **kwargs):
        if not calls:
            calls.append({"invalid": True})
            return {"done": True, "message": {"content": "{}"}}
        return valid(*args, **kwargs)

    result = experiment.run_applicability(config, "fixture-model", payload, post)
    assert result["status"] == "completed" and result["model_attempts"] == 3
    assert result["first_pass_status"] == "failed" and "first_pass_answer" not in result
    assert result["recovered_after_validation_failure"]
    assert len(result["stages"]["applicability"]["attempts"]) == 2
    assert len(result["stages"]["aggregation"]["attempts"]) == 1


def test_over_budget_stage_has_no_network_call(frozen):
    _, config, payload = frozen
    config["request_max_bytes"] = 10
    calls = []
    result = experiment.run_applicability(config, "fixture-model", payload, post_model(calls))
    assert result["status"] == "failed" and calls == []
    assert result["model_attempts"] == 1 and result["model_calls"] == 0
    assert "serialized request" in result["error"]


def test_large_derived_union_completes_both_stages_with_original_source_resolution(frozen):
    _, config, payload = frozen
    fields = ["vision.indicator", *[f"vision.fixture_{i}" for i in range(11)]]
    payload["verified_patient_facts"].update(
        {
            field: {"value": False, "patient_quotes": [f"{field} explicitly absent"]}
            for field in fields[1:]
        }
    )
    calls = []
    provider = post_model(calls)

    def post(*args, **kwargs):
        response = provider(*args, **kwargs)
        if len(calls) == 1:
            answer = json.loads(response["message"]["content"])
            item = answer["passages"]["P1"]
            item["fact_fields"] = fields[:8]
            item["prerequisites"] = [
                {
                    "requirement": "Additional documented fixture prerequisites",
                    "status": "unknown",
                    "fact_fields": fields[8:],
                }
            ]
            response["message"]["content"] = json.dumps(answer)
        return response

    result = experiment.run_applicability(config, "fixture-model", payload, post)
    assert result["status"] == result["first_pass_status"] == "completed"
    assert len(calls) == result["model_calls"] == 2
    stage = result["stages"]["applicability"]
    assert stage["criterion_locations"][0]["check"]["fact_fields"] == fields
    assert (
        stage["criterion_locations"][0]["spans"][0]["original_quote"]
        == payload["guideline_evidence"][0]["source_text"]
    )
    aggregation_wire = json.loads(calls[1]["messages"][1]["content"])
    assert (
        list(aggregation_wire["proposed_applicability_ledger"][0]["referenced_patient_values"])
        == fields
    )


def test_reference_metadata_cannot_enter_any_protocol(frozen):
    _, config, _ = frozen
    root = Path(config["retrieval_dir"])
    path = root / "payloads.json"
    saved = json.loads(path.read_text())
    selected = saved["fixture-case"]["module_query"]
    selected["payload"]["verified_patient_facts"]["vision.indicator"]["expected_outcome"] = (
        "hidden-label"
    )
    selected["input_sha256"] = digest(selected["payload"])
    write_json(path, saved)
    freeze = json.loads((root / "retrieval_freeze.json").read_text())
    freeze["artifacts"]["payloads.json"] = sha256_bytes(path.read_bytes())
    write_json(root / "retrieval_freeze.json", freeze)
    with pytest.raises(ValueError, match="Unexpected verified-fact metadata"):
        experiment.load_retrieval(config)


def test_model_revision_mismatch_blocks_calls(frozen):
    path, config, _ = frozen

    def wrong_pin(endpoint, route):
        value = get(config)(endpoint, route)
        if route == "/api/tags":
            value["models"][0]["digest"] = "changed-model"
        return value

    with pytest.raises(ValueError, match="digest differs"):
        experiment.run_comparison(path, get=wrong_pin, post=lambda *_: pytest.fail("No inference"))
    assert not Path(config["output"]).exists()


def test_review_annotations_survive_resume(frozen):
    path, config, _ = frozen
    kwargs = {"post": post_model([]), "get": get(config)}
    experiment.run_comparison(path, max_conditions=2, **kwargs)
    review_path = Path(config["output"]) / "review.csv"
    original = review_path.read_text(encoding="utf-8-sig")
    review_path.write_text(
        original.replace(",pending,pending,,", ",supported,pending,Reviewer A,", 1),
        encoding="utf-8-sig",
    )
    experiment.run_comparison(path, resume=True, **kwargs)
    assert ",supported,pending,Reviewer A," in review_path.read_text(encoding="utf-8-sig")


def test_changed_accepted_answer_is_rejected_before_resume_calls(frozen):
    path, config, _ = frozen
    kwargs = {"post": post_model([]), "get": get(config)}
    experiment.run_comparison(path, max_conditions=2, **kwargs)
    output = Path(config["output"]) / "results.jsonl"
    rows = passage_comparison.read_records(output)
    rows[0]["answer"]["assessment_outcome"] = "insufficient_information"
    output.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    with pytest.raises(ValueError, match="Saved accepted proposal differs"):
        experiment.run_comparison(
            path, resume=True, post=lambda *_: pytest.fail("No inference"), get=get(config)
        )


def test_failure_classification_counts_as_false_negative():
    rows = [{"status": "failed", "reference_outcome": "temporarily_unfit"}]
    metrics = experiment.classification_metrics(rows, "answer", "status")
    assert metrics["confusion_matrix"]["temporarily_unfit"]["RUN_FAILURE"] == 1
    assert metrics["macro_f1_five_outcomes"] == 0


def test_failed_to_valid_is_not_counted_as_corrected_judgment():
    base = {
        "model": "m",
        "case_id": "c",
        "evidence_policy": "module_query",
        "repeat": 0,
        "input_sha256": "same",
        "model_digest": "same",
        "reference_outcome": "temporarily_unfit",
        "reference_agreement": False,
        "status": "failed",
        "protocol": "passage_selection",
    }
    after = {
        **base,
        "protocol": "applicability_first",
        "status": "completed",
        "reference_agreement": True,
        "answer": {"assessment_outcome": "temporarily_unfit"},
    }
    result = experiment.paired_transitions([base, after])
    assert result["counts"] == {"failed_to_valid": 1}
    after["input_sha256"] = "changed"
    with pytest.raises(ValueError, match="Paired protocols differ"):
        experiment.paired_transitions([base, after])


def test_real_reviewed_retrieval_is_loadable_without_live_calls():
    config = yaml.safe_load(Path("configs/experiments/applicability_comparison.yaml").read_text())
    frozen = experiment.load_retrieval(config)
    assert len(frozen["corpus"]["units"]) == 94
    assert len(frozen["payloads"]) == 8
    assert all(
        item["status"] == "completed"
        for values in frozen["payloads"].values()
        for item in values.values()
    )
