"""Literal recovery is typed, source bound, uniformly applied and version isolated."""

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest


def tool():
    spec = importlib.util.spec_from_file_location(
        "source_literal_facts",
        Path(__file__).resolve().parents[1] / "tools/build_source_literal_facts.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fixture(root):
    api = tool()
    literal = api.literal_api()
    baseline, audit_dir, retrieval = root / "baseline", root / "audit", root / "retrieval"
    source = root / "data/cases/notes/CASE-1.txt"
    text = "Synthetic é 😀\r\nvision.flag = false\r\nhearing.count = 0\r\nvision.other = true\r\n"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
    changes, facts = [], {}
    for field, value, quote in [
        ("vision.flag", False, "vision.flag = false"),
        ("hearing.count", 0, "hearing.count = 0"),
        ("vision.unstated", False, "Synthetic é 😀"),
    ]:
        start = text.index(quote)
        evidence = [{"start": start, "end": start + len(quote), "quote": quote}]
        before = {"value": value, "status": "present", "evidence": evidence}
        frozen = {"value": None, "status": "requires_confirmation", "evidence": evidence}
        changes.append({"field": field, "before": before, "frozen": frozen})
        facts[field] = deepcopy(frozen)
    payload = {
        "licence_context": "commercial",
        "modules": ["vision", "hearing"],
        "nurse_note": text,
        "verified_patient_facts": {},
        "guideline_evidence": [],
    }
    case = {
        "case_id": "CASE-1",
        "licence_context": "commercial",
        "modules_requested": payload["modules"],
        "source_document": source.name,
        "source_sha256": api.fingerprint(source.read_bytes()),
        "source_text": text,
        "text_sha256": api.fingerprint(text.encode("utf-8")),
        "facts": facts,
    }
    snapshot = {
        "case": case,
        "case_sha256": api.digest(case),
        "semantic_review": {"issues": [{"field": "vision.flag", "kind": "unsupported"}]},
    }
    frozen = {"CASE-1": {"payload": payload, "reference_outcome": "deliberately_unused"}}
    upstream = {
        "cases": [{"case_id": "CASE-1", "changed_fields": changes, "reference": "must_not_be_used"}]
    }
    save(baseline / "upstream_audit.json", upstream)
    save(baseline / "frozen_cases/CASE-1.json", snapshot)
    save(retrieval / "frozen_inputs.json", frozen)
    save(
        retrieval / "manifest.json",
        {"identity": "frozen-retrieval-identity", "patient_inputs_sha256": api.digest(frozen)},
    )
    relative = source.relative_to(root).as_posix()
    audit = {
        "upstream_audit_sha256": api.fingerprint((baseline / "upstream_audit.json").read_bytes()),
        "source_files_sha256": {relative: case["source_sha256"]},
        "cases": [
            {
                "case_id": "CASE-1",
                "source": relative,
                "source_raw_sha256": case["source_sha256"],
                "decoded_text_sha256": case["text_sha256"],
                "fields": [literal.inspect_field(text, changed) for changed in changes],
            }
        ],
    }
    save(audit_dir / "fact_revalidation_audit.json", audit)
    return api, baseline, audit_dir, retrieval, source


def test_typed_literal_snapshot_preserves_quarantine_and_original_version(tmp_path):
    api, baseline, audit, retrieval, source = fixture(tmp_path)
    original = {
        path: path.read_bytes()
        for directory in [baseline, audit, retrieval]
        for path in directory.rglob("*.json")
    }
    result = api.build_snapshot(tmp_path, baseline, audit, retrieval, "sensitivity")
    case = result["cases"]["CASE-1"]
    assert result["metadata"]["restored_field_count"] == 2
    assert result["metadata"]["unrestored_field_count"] == 1
    assert result["metadata"]["reference_outcomes_consulted"] is False
    assert case["original_verified_patient_facts"] == {}
    assert case["sensitivity_verified_patient_facts"]["vision.flag"]["value"] is False
    assert type(case["sensitivity_verified_patient_facts"]["hearing.count"]["value"]) is int
    assert case["sensitivity_verified_patient_facts"]["hearing.count"]["value"] == 0
    assert case["semantic_review_audit"]["semantic_review"]["issues"]
    assert all(change["frozen"]["status"] == "requires_confirmation" for change in case["changes"])
    assert all(change["review_status"] == "pending_clinical_review" for change in case["changes"])
    text = source.read_bytes().decode("utf-8-sig")
    for change in case["changes"]:
        for span in change["literal_spans"]:
            assert text[span["char_start"] : span["char_end"]] == span["quote"]
    assert case["original_patient_identity"] != case["sensitivity_patient_identity"]
    assert all(path.read_bytes() == raw for path, raw in original.items())
    assert api.load_snapshot(tmp_path / "sensitivity", tmp_path) == result
    assert api.build_snapshot(tmp_path, baseline, audit, retrieval, "sensitivity") == result


@pytest.mark.parametrize("mutation", ["source", "span", "type", "snapshot"])
def test_stale_or_rehashed_tampering_is_rejected(tmp_path, mutation):
    api, baseline, audit, retrieval, source = fixture(tmp_path)
    api.build_snapshot(tmp_path, baseline, audit, retrieval, "sensitivity")
    if mutation == "source":
        source.write_bytes(source.read_bytes().replace(b"false", b"true"))
    elif mutation in {"span", "type"}:
        path = audit / "fact_revalidation_audit.json"
        value = json.loads(path.read_bytes())
        field = value["cases"][0]["fields"][0]
        if mutation == "span":
            field["literal_spans"][0]["char_start"] += 1
        else:
            field["literal_spans"][0]["value"] = 0
        save(path, value)
    else:
        path = tmp_path / "sensitivity/source_literal_facts.json"
        value = json.loads(path.read_bytes())
        value["cases"]["CASE-1"]["sensitivity_verified_patient_facts"]["vision.flag"]["value"] = 0
        value["identity"] = api.digest(
            {key: item for key, item in value.items() if key != "identity"}
        )
        save(path, value)
    with pytest.raises(ValueError):
        api.load_snapshot(tmp_path / "sensitivity", tmp_path)


def test_conflicting_duplicate_literals_never_restore(tmp_path):
    api, baseline, audit, retrieval, source = fixture(tmp_path)
    text = source.read_bytes().decode("utf-8-sig") + "vision.flag = true\r\n"
    source.write_bytes(text.encode("utf-8"))
    path = baseline / "frozen_cases/CASE-1.json"
    saved = json.loads(path.read_bytes())
    saved["case"].update(
        source_sha256=api.fingerprint(source.read_bytes()),
        source_text=text,
        text_sha256=api.fingerprint(text.encode("utf-8")),
    )
    saved["case_sha256"] = api.digest(saved["case"])
    save(path, saved)
    path = retrieval / "frozen_inputs.json"
    frozen = json.loads(path.read_bytes())
    frozen["CASE-1"]["payload"]["nurse_note"] = text
    save(path, frozen)
    save(
        retrieval / "manifest.json",
        {"identity": "frozen-retrieval-identity", "patient_inputs_sha256": api.digest(frozen)},
    )
    path = audit / "fact_revalidation_audit.json"
    value = json.loads(path.read_bytes())
    row = value["cases"][0]
    row.update(
        source_raw_sha256=saved["case"]["source_sha256"],
        decoded_text_sha256=saved["case"]["text_sha256"],
    )
    changed = json.loads((baseline / "upstream_audit.json").read_bytes())["cases"][0][
        "changed_fields"
    ]
    row["fields"] = [api.literal_api().inspect_field(text, item) for item in changed]
    value["source_files_sha256"][source.relative_to(tmp_path).as_posix()] = row["source_raw_sha256"]
    save(path, value)
    result = api.build_snapshot(tmp_path, baseline, audit, retrieval, "sensitivity")
    case = result["cases"]["CASE-1"]
    assert "vision.flag" not in case["sensitivity_verified_patient_facts"]
    assert case["unchanged_changed_fields"][0]["status"] == "conflicting_explicit_literals"
    assert result["metadata"]["restored_field_count"] == 1


def test_refuses_output_inside_frozen_inputs(tmp_path):
    api, baseline, audit, retrieval, _ = fixture(tmp_path)
    with pytest.raises(ValueError, match="separate"):
        api.build_snapshot(tmp_path, baseline, audit, retrieval, retrieval / "sensitivity")
