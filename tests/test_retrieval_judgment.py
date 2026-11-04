"""Evidence boundaries, quotation integrity and report/API wiring."""

import json

import pytest
from fastapi.testclient import TestClient

from occupational_fitness_rag.evaluation.retrieval_judgment import (
    ReviewOutputError,
    build_payload,
    build_request,
    case_observation,
    parse_review,
    patient_paragraphs,
    reference_audit,
)
from occupational_fitness_rag.provenance import digest, sha256_bytes
from tools.complex_ten_contract import pin, read, write_json
from tools.serve_retrieval_judgments import Condition, ReviewService, create_app, inject


def inputs():
    def unit(sid, section, text, module="blackout", refs=()):
        return {"source_id": sid, "section": section, "evidence_text": text,
                "text_sha256": sha256_bytes(text.encode()), "module": module,
                "licence_context": "commercial", "pdf_page": 10, "printed_page": 9,
                "explicit_section_references": list(refs)}
    a = unit("A", "1.2", "Investigate the cause before deciding fitness. See section 2.3.",
             refs=["2.3", "6.9"])
    b = unit("B", "2.3", "An applicable heart condition requires specialist review.",
             module="hypertension", refs=["1.2"])
    q = {"case_id": "CASE", "module": "blackout", "query_id": "Q",
         "query": "No established cause. Cardiology review is pending."}
    r = {"status": "completed", "query_id": "Q", "case_id": "CASE",
         "method": "hybrid", "source_ids": ["A"],
         "reference_source_ids": ["SECRET_ANSWER"], "rule_outcome": "SECRET_RULE"}
    return q, r, {"A": a, "B": b}


def proposal():
    return {"checks": [{"source_slot": 1, "patient_paragraph": 1,
                        "applicability": "unresolved", "finding": "information_missing",
                        "comment": "The cause-specific evidence and review are needed."}],
            "fitness": "undetermined", "outcome": "insufficient_information",
            "explanation": "A specialist review and the referenced applicable standard are missing.",
            "missing_information": ["Cause-specific review"]}


def completed(value):
    return {"done": True, "done_reason": "stop", "prompt_eval_count": 100,
            "message": {"content": json.dumps(value)}}


def test_strict_topk_and_labels_never_leak():
    q, r, u = inputs()
    p = build_payload(q, r, u)
    assert p["nurse_note"] == q["query"]
    assert p["retrieved_source_ids"] == ["A"]
    assert len(p["guideline_evidence"]) == 1
    assert "SECRET" not in json.dumps(p)
    assert p["assessment_scope"] == ["blackout"]


def test_cross_chapter_target_is_added_independently_of_ranking_and_cycles_stop():
    q, r, u = inputs()
    p = build_payload(q, r, u, evidence_mode="explicit_references")
    assert [s["source_id"] for s in p["guideline_evidence"]] == ["A", "B"]
    assert p["retrieved_source_ids"] == ["A"]
    assert r["source_ids"] == ["A"]
    assert any(link["status"] == "outside_frozen_corpus" for link in p["cross_reference_audit"])


def test_private_reference_and_source_mutation_rejected():
    q, r, u = inputs()
    u["B"]["licence_context"] = "private"
    assert reference_audit(["A"], u)[0]["status"] == "outside_frozen_corpus"
    u["A"]["evidence_text"] += " changed"
    with pytest.raises(ValueError, match="fingerprint"):
        build_payload(q, r, u)


def test_budget_failure_never_truncates():
    q, r, u = inputs()
    p = build_payload(q, r, u)
    before = json.dumps(p)
    with pytest.raises(ValueError, match="No original was truncated"):
        build_request(p, "llama3:8b", 100)
    assert json.dumps(p) == before


def test_all_patient_characters_preserved_in_numbered_paragraphs():
    original = "First long sentence.\n\nSecond sentence.\n \n\nFinal text.\n"
    spans = patient_paragraphs(original)
    assert "".join(p["text"] for p in spans) == original
    for p in spans:
        assert original[p["start"]:p["end"]] == p["text"]


def test_case_level_allocation_uses_actual_rankings_and_keeps_assessment_scope():
    q, r, u = inputs()
    q2 = {**q, "query_id": "Q2", "module": "hypertension"}
    r2 = {**r, "query_id": "Q2", "source_ids": ["B"]}
    case, ranked = case_observation("CASE", {"Q": q, "Q2": q2},
                                   {("Q", "hybrid"): r, ("Q2", "hybrid"): r2}, "hybrid")
    payload = build_payload(case, ranked, u)
    assert payload["assessment_scope"] == ["blackout", "hypertension"]
    assert payload["retrieved_source_ids"] == ["A", "B"]
    assert "SECRET" not in json.dumps(payload)
    r2["status"] = "failed"
    with pytest.raises(ValueError, match="every requested module"):
        case_observation("CASE", {"Q": q, "Q2": q2},
                         {("Q", "hybrid"): r, ("Q2", "hybrid"): r2}, "hybrid")


@pytest.mark.parametrize("error", ["patient", "slot", "partial", "context"])
def test_invalid_completion_not_accepted(error):
    q, r, u = inputs()
    p = build_payload(q, r, u)
    body = build_request(p, "qwen3.5:4b-q4_K_M", 32768)
    answer = proposal()
    if error == "patient":
        answer["checks"][0]["patient_paragraph"] = 2
    if error == "slot":
        answer["checks"][0]["source_slot"] = 2
    raw = completed(answer)
    if error == "partial":
        raw["done_reason"] = "length"
    if error == "context":
        raw["prompt_eval_count"] = 32768
    with pytest.raises(ValueError):
        parse_review(raw, p, body)


def test_accepted_review_has_exact_character_spans():
    q, r, u = inputs()
    p = build_payload(q, r, u)
    body = build_request(p, "qwen3.5:4b-q4_K_M", 32768)
    answer = parse_review(completed(proposal()), p, body)
    c = answer["checks"][0]
    assert c["source_id"] == "A"
    assert p["nurse_note"][c["patient_span"]["start"]:c["patient_span"]["end"]] == c["patient_quote"]
    assert answer["fitness"] == "undetermined"
    assert not answer["validation_warnings"]


def test_inconsistent_yes_is_flagged_not_silently_rewritten():
    q, r, u = inputs()
    p = build_payload(q, r, u)
    body = build_request(p, "qwen3.5:4b-q4_K_M", 32768)
    value = proposal()
    value.update(fitness="yes", outcome="meets_unconditional_standard")
    answer = parse_review(completed(value), p, body)
    assert answer["fitness"] == "yes"
    assert len(answer["validation_warnings"]) == 2


def test_api_queue_cache_offline_panel_and_origin_guard(tmp_path, monkeypatch):
    q, r, u = inputs()
    directory = tmp_path / "report"
    directory.mkdir()
    data = {"queries": [q], "rankings": [r], "units": u}
    html = '<html><body><script id="dataset" type="application/json">' + json.dumps(data) + '</script></body></html>'
    (directory / "index.html").write_text(html)
    service = ReviewService(tmp_path / "runs", {"test": directory})
    service.models = {"qwen3.5:4b-q4_K_M": {"digest": "weights", "review_context": 32768}}
    calls = []
    def fake(endpoint, body):
        calls.append(body)
        return completed(proposal())
    monkeypatch.setattr("occupational_fitness_rag.evaluation.retrieval_judgment.call_review", fake)
    c = Condition(dataset="test", query_id="Q", method="hybrid", model="qwen3.5:4b-q4_K_M")
    with TestClient(create_app(service)) as client:
        response = client.post("/api/reviews", json=c.model_dump(), headers={"origin": "http://bad.example"})
        assert response.status_code == 403
        job = client.post("/api/reviews", json=c.model_dump()).json()
        service.pool.shutdown(wait=True)
        record = client.get("/api/reviews/" + job["id"]).json()
        assert record["status"] == "completed"
        assert client.post("/api/reviews", json=c.model_dump()).json()["id"] == job["id"]
        assert len(calls) == 1
        assert 'fitness-review-cache' in inject(html, "test", [record])
        assert client.get('/api/reviews/invalid').status_code == 400
        assert client.get('/api/review-models').json()['service'] == 'occupational-fitness-evidence-review'


def test_presentation_changes_keep_saved_model_decision_visible(tmp_path, monkeypatch):
    q, r, u = inputs()
    directory = tmp_path / "report"
    directory.mkdir()
    (directory / "index.html").write_text('<html><body><script id="dataset" type="application/json">'
        + json.dumps({"queries": [q], "rankings": [r], "units": u}) + '</script></body></html>')
    service = ReviewService(tmp_path / "runs", {"test": directory})
    service.models = {"qwen3.5:4b-q4_K_M": {"digest": "weights", "review_context": 32768}}
    monkeypatch.setattr("occupational_fitness_rag.evaluation.retrieval_judgment.call_review",
                        lambda *args: completed(proposal()))
    c = Condition(dataset="test", query_id="Q", method="hybrid", model="qwen3.5:4b-q4_K_M")
    job = service.submit(c)
    service.pool.shutdown(wait=True)
    record = service.records()[0]
    service.implementation_identity = "A new UI and HTTP implementation"
    assert service.submit(c)["id"] == job["id"]
    page = inject('<body></body>', 'test', [record], "another UI version")
    assert proposal()["explanation"] in page
    service.close()


def test_legacy_response_is_revalidated_without_recalling_model(tmp_path, monkeypatch):
    q, r, u = inputs()
    directory = tmp_path / "report"
    directory.mkdir()
    (directory / "index.html").write_text('<html><body><script id="dataset" type="application/json">'
        + json.dumps({"queries": [q], "rankings": [r], "units": u}) + '</script></body></html>')
    service = ReviewService(tmp_path / "runs", {"test": directory})
    service.models = {"qwen3.5:4b-q4_K_M": {"digest": "weights", "review_context": 32768}}
    c = Condition(dataset="test", query_id="Q", method="hybrid", model="qwen3.5:4b-q4_K_M")
    payload = build_payload(q, r, u)
    request = build_request(payload, c.model, 32768)
    raw = completed(proposal())
    old = {"id": "a" * 64, "case_id": "CASE", "module": "blackout", "condition": c.model_dump(),
           "protocol": "original_note_topk_review_v2", "model_digest": "weights",
           "implementation_identity": "old UI", "payload": payload, "payload_sha256": digest(payload),
           "request": request, "raw_response": raw, "result": parse_review(raw, payload, request),
           "status": "completed"}
    source = service.output / "records" / (old["id"] + ".json")
    write_json(source, old)
    before = pin(source)
    calls = []
    monkeypatch.setattr("occupational_fitness_rag.evaluation.retrieval_judgment.call_review",
                        lambda *args: calls.append(args))
    restored = service.submit(c)
    service.pool.shutdown(wait=True)
    assert restored["origin_record_id"] == old["id"]
    assert restored["result"]["explanation"] == proposal()["explanation"]
    assert not calls
    assert pin(source) == before
    service.close()


def make_service(tmp_path):
    q, r, u = inputs()
    directory = tmp_path / "report"
    directory.mkdir()
    (directory / "index.html").write_text('<html><body><script id="dataset" type="application/json">'
        + json.dumps({"queries": [q], "rankings": [r], "units": u}) + '</script></body></html>')
    service = ReviewService(tmp_path / "runs", {"test": directory})
    service.models = {"qwen3.5:4b-q4_K_M": {"digest": "weights", "review_context": 32768}}
    condition = Condition(dataset="test", query_id="Q", method="hybrid", model="qwen3.5:4b-q4_K_M")
    return service, condition


def bad_patient_reference():
    value = proposal()
    value["checks"][0].update(patient_paragraph=0, applicability="established")
    return completed(value)


def test_decoder_contract_disallows_established_without_a_patient_paragraph():
    q, r, u = inputs()
    payload = build_payload(q, r, u)
    request = build_request(payload, "llama3:8b", 32768)
    branches = request["format"]["$defs"]["Check"]["anyOf"]
    for branch in branches:
        props = branch["properties"]
        value = props["applicability"]["enum"][0]
        assert props["patient_paragraph"]["minimum"] == (0 if value == "unresolved" else 1)
    with pytest.raises(ReviewOutputError) as exc:
        parse_review(bad_patient_reference(), payload, request)
    assert exc.value.code == "missing_patient_reference"


def test_one_reference_repair_keeps_the_exact_note_evidence_and_model(tmp_path, monkeypatch):
    service, condition = make_service(tmp_path)
    calls = []
    def fake(endpoint, request):
        calls.append(request)
        return bad_patient_reference() if len(calls) == 1 else completed(proposal())
    monkeypatch.setattr("occupational_fitness_rag.evaluation.retrieval_judgment.call_review", fake)
    try:
        job = service.submit(condition)
        service.pool.submit(lambda: None).result(timeout=5)
        record = read(service.output / "records" / (job["id"] + ".json"))
        assert record["status"] == "completed"
        assert record["model_calls"] == 2
        assert [a["status"] for a in record["attempts"]] == ["rejected", "accepted"]
        assert calls[0]["messages"][1] == calls[1]["messages"][1]
        assert calls[0]["model"] == calls[1]["model"]
        assert calls[0]["format"] == calls[1]["format"]
        assert "Validation repair" in calls[1]["messages"][0]["content"]
        assert record["attempts"][0]["raw_response"] == bad_patient_reference()
    finally:
        service.close()


def test_repair_is_bounded_and_manual_retry_retains_the_failed_observation(tmp_path, monkeypatch):
    service, condition = make_service(tmp_path)
    calls = []
    def fake(endpoint, request):
        calls.append(request)
        return bad_patient_reference() if len(calls) <= 2 else completed(proposal())
    monkeypatch.setattr("occupational_fitness_rag.evaluation.retrieval_judgment.call_review", fake)
    try:
        job = service.submit(condition)
        service.pool.submit(lambda: None).result(timeout=5)
        failed = service.output / "records" / (job["id"] + ".json")
        before = pin(failed)
        assert read(failed)["status"] == "failed"
        assert len(calls) == 2
        assert service.submit(condition)["id"] == job["id"]
        retried = service.retry(job["id"])
        service.pool.submit(lambda: None).result(timeout=5)
        fresh = read(service.output / "records" / (retried["id"] + ".json"))
        assert fresh["status"] == "completed"
        assert fresh["retry_of"] == job["id"]
        assert retried["id"] != job["id"]
        assert pin(failed) == before
        assert service.submit(condition)["id"] == retried["id"]
        assert len(calls) == 3
    finally:
        service.close()


def test_partial_completion_is_not_repaired_or_accepted(tmp_path, monkeypatch):
    service, condition = make_service(tmp_path)
    calls = []
    def fake(endpoint, request):
        calls.append(request)
        return {**completed(proposal()), "done_reason": "length"}
    monkeypatch.setattr("occupational_fitness_rag.evaluation.retrieval_judgment.call_review", fake)
    try:
        job = service.submit(condition)
        service.pool.submit(lambda: None).result(timeout=5)
        record = read(service.output / "records" / (job["id"] + ".json"))
        assert record["status"] == "failed"
        assert not record.get("result")
        assert len(calls) == 1
    finally:
        service.close()


def test_retry_api_preserves_origin_guard_and_returns_new_record(tmp_path, monkeypatch):
    service, condition = make_service(tmp_path)
    calls = []
    def fake(endpoint, request):
        calls.append(request)
        return bad_patient_reference() if len(calls) <= 2 else completed(proposal())
    monkeypatch.setattr("occupational_fitness_rag.evaluation.retrieval_judgment.call_review", fake)
    with TestClient(create_app(service)) as client:
        job = client.post('/api/reviews', json=condition.model_dump()).json()
        service.pool.submit(lambda: None).result(timeout=5)
        path = '/api/reviews/' + job['id'] + '/retry'
        assert client.post(path, headers={'origin': 'https://bad.example'}).status_code == 403
        response = client.post(path)
        assert response.status_code == 200
        service.pool.submit(lambda: None).result(timeout=5)
        retried = client.get('/api/reviews/' + response.json()['id']).json()
        assert retried['status'] == 'completed'
        assert retried['retry_of'] == job['id']
        assert client.get('/api/reviews/' + job['id']).json()['status'] == 'failed'
