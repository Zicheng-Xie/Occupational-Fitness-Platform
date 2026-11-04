import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import fitz
import pytest

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.evaluation.prospective_review import (
    MODULES,
    REQUIRED_CONTRACT_SOURCES,
    Adjudication,
    ReviewSubmission,
    SourceVerification,
    freeze_execution_amendment,
    prospective_inputs,
    snapshot_paths,
    source_verification_template,
)
from occupational_fitness_rag.evaluation.prospective_review import (
    freeze_labels as real_freeze_labels,
)
from occupational_fitness_rag.provenance import digest, write_json
from tools.prepare_prospective_review_pack import render


@pytest.fixture
def packet(tmp_path):
    folder = tmp_path / "packet"
    folder.mkdir()
    note = "The driver's measured blood pressure was 180/110 mmHg after rest."
    (folder / "notes").mkdir()
    (folder / "notes/NEW-001.txt").write_bytes((note + "\n").encode("utf-8"))
    with fitz.open() as pdf:
        page = pdf.new_page()
        page.insert_text(
            (60, 80), "Commercial standards require assessment of persistent hypertension."
        )
        pdf.save(folder / "guideline.pdf")
    root = tmp_path / "root"
    for name in REQUIRED_CONTRACT_SOURCES:
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("fixture", encoding="utf-8")
    specs = {
        "cardiovascular.blood_pressure.observed_systolic": {"type": "number"},
        "blackout.occurred": {"type": "boolean"},
        "diabetes.present": {"type": "boolean"},
    }
    write_json(root / "schemas/field_dictionary.json", specs)
    (root / "tools/fixture_base_runner.py").write_text("baseline runner", encoding="utf-8")
    snapshot = {p: file_hash(root / p) for p in snapshot_paths(root)}
    plan_data = {
        "source_sha256": snapshot,
        "runtime_artifacts": {},
        "arms": {"hybrid": ["hybrid", "round_robin"]},
        "expected_model_digests": {"fixture-model": "weights-pin"},
        "expected_runtime_version": "fixture-runtime",
        "endpoint": "http://127.0.0.1:11434",
        "harness_source": "tools/fixture_base_runner.py",
        "harness_integration": "integrated",
    }
    plan = {**plan_data, "identity": digest(plan_data)}
    write_json(folder / "field_dictionary.json", specs)
    write_json(folder / "implementation_snapshot.json", snapshot)
    write_json(folder / "execution_plan.json", plan)
    for name in (
        "gate_source.py",
        "builder_source.py",
        "readiness.json",
        "review.schema.json",
        "source_verification.schema.json",
    ):
        (folder / name).write_text("fixture", encoding="utf-8")
    data = {
        "case_count": 1,
        "requested_modules": list(MODULES),
        "guideline_sha256": file_hash(folder / "guideline.pdf"),
        "guideline_page_count": 1,
        "field_dictionary_identity": digest(specs),
        "development_implementation_identity": digest(snapshot),
        "execution_plan_identity": plan["identity"],
        "cases": [
            {
                "case_id": "NEW-001",
                "note_sha256": file_hash(folder / "notes/NEW-001.txt"),
                "note_path": "notes/NEW-001.txt",
                "nurse_note": note,
            }
        ],
    }
    manifest = {**data, "identity": digest(data)}
    write_json(folder / "manifest.json", manifest)
    write_json(
        folder / "artifacts.json",
        {p.relative_to(folder).as_posix(): file_hash(p) for p in folder.rglob("*") if p.is_file()},
    )
    return folder, manifest


def runtime_probe(endpoint, route):
    return (
        {"version": "fixture-runtime"}
        if route == "/api/version"
        else {"models": [{"name": "fixture-model", "digest": "weights-pin"}]}
    )


def inputs(packet, labels, **kwargs):
    return prospective_inputs(
        packet, labels, root=packet.parent / "root", runtime_probe=runtime_probe, **kwargs
    )


def verified_sources(folder, ap, bp, adjudication_path=None):
    forms = [ReviewSubmission.model_validate_json(p.read_bytes()) for p in (ap, bp)]
    if adjudication_path:
        forms.append(Adjudication.model_validate_json(adjudication_path.read_bytes()))
    packet = json.loads((folder / "manifest.json").read_bytes())
    source = source_verification_template(packet["identity"], forms).model_dump(mode="json")
    source.update(
        status="submitted",
        verifier_id="SOURCE-CHECKER",
        role="domain_reviewer",
        completed_at=datetime.now(timezone.utc).isoformat(),
        independent_of_annotation_and_retrieval=True,
        did_not_view_model_outputs=True,
    )
    for check in source["citations"]:
        check.update(
            bbox=[0, 0, 595, 842],
            inspected_original_region=True,
            section_verified=True,
            commercial_or_shared_column_verified=True,
            footnotes_and_qualifications_checked=True,
        )
    path = folder.parent / "source_check.json"
    write_json(path, source)
    return path


def freeze_labels(folder, ap, bp, output, adjudication_path=None):
    return real_freeze_labels(
        folder,
        ap,
        bp,
        output,
        adjudication_path,
        source_verification_path=verified_sources(folder, ap, bp, adjudication_path),
    )


def form(packet, reviewer_id):
    _, manifest = packet
    case = manifest["cases"][0]
    assessment = {
        "outcome": "insufficient_information",
        "rationale": "Some requested information is absent from the synthetic note.",
        "guideline_citations": [],
    }
    return {
        "packet_identity": manifest["identity"],
        "status": "submitted",
        "reviewer": {
            "reviewer_id": reviewer_id,
            "role": "domain_reviewer",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "independent_of_case_authoring": True,
            "independent_of_retrieval_development": True,
            "did_not_view_model_outputs": True,
            "did_not_view_other_reviewer_answers": True,
        },
        "cases": [
            {
                "case_id": "NEW-001",
                "source_note_sha256": case["note_sha256"],
                "documented_facts": [],
                "module_assessments": {m: deepcopy(assessment) for m in MODULES},
                "overall": deepcopy(assessment),
            }
        ],
    }


def submit(tmp_path, a, b):
    paths = [tmp_path / "reviewer_a.json", tmp_path / "reviewer_b.json"]
    for path, value in zip(paths, (a, b), strict=True):
        write_json(path, value)
    return paths


def test_blank_labels_cannot_be_frozen_or_evaluated(packet, tmp_path):
    a, b = form(packet, "A"), form(packet, "B")
    a["status"] = "draft"
    ap, bp = submit(tmp_path, a, b)
    with pytest.raises(ValueError, match="submitted"):
        freeze_labels(packet[0], ap, bp, tmp_path / "labels")
    assert not (tmp_path / "labels").exists()
    with pytest.raises(FileNotFoundError):
        inputs(packet[0], tmp_path / "labels")


def test_two_agreeing_engineering_reviewers_can_freeze_without_clinician_claim(packet, tmp_path):
    ap, bp = submit(tmp_path, form(packet, "A"), form(packet, "B"))
    output = tmp_path / "labels"
    result = freeze_labels(packet[0], ap, bp, output)
    cases, labels = inputs(packet[0], output)
    assert len(cases) == 1 and set(cases[0]) == {"case_id", "nurse_note", "modules"}
    assert labels["NEW-001"]["reference_outcome"] == "insufficient_information"
    assert result["clinical_accuracy_established"] is False and result["adjudicator_id"] is None
    with pytest.raises(ValueError, match="fresh directory"):
        freeze_labels(packet[0], ap, bp, output)


@pytest.mark.parametrize(
    "mutation", ["same_id", "not_independent", "missing_module", "wrong_note", "missing_rationale"]
)
def test_review_provenance_and_case_scope_are_required(packet, tmp_path, mutation):
    a, b = form(packet, "A"), form(packet, "B")
    if mutation == "same_id":
        b["reviewer"]["reviewer_id"] = "A"
    elif mutation == "not_independent":
        b["reviewer"]["did_not_view_model_outputs"] = False
    elif mutation == "missing_module":
        b["cases"][0]["module_assessments"].pop("hearing")
    elif mutation == "wrong_note":
        b["cases"][0]["source_note_sha256"] = "wrong"
    else:
        b["cases"][0]["overall"]["rationale"] = "short"
    ap, bp = submit(tmp_path, a, b)
    with pytest.raises(ValueError):
        freeze_labels(packet[0], ap, bp, tmp_path / "labels")


def test_disagreement_requires_a_distinct_source_bound_adjudicator(packet, tmp_path):
    a, b = form(packet, "A"), form(packet, "B")
    case = b["cases"][0]
    case["overall"] = {
        "outcome": "temporarily_unfit",
        "rationale": "The documented pressure requires a source-supported assessment.",
        "guideline_citations": [
            {
                "pdf_page": 1,
                "section": "2.3",
                "quote": "Commercial standards require assessment of persistent hypertension.",
                "licence_scope": "commercial",
            }
        ],
    }
    case["documented_facts"] = [
        {
            "module": "hypertension",
            "field": "cardiovascular.blood_pressure.observed_systolic",
            "value": 180,
            "note_quote": "measured blood pressure was 180/110 mmHg",
        }
    ]
    ap, bp = submit(tmp_path, a, b)
    with pytest.raises(ValueError, match="require adjudication"):
        freeze_labels(packet[0], ap, bp, tmp_path / "labels")
    adj = {
        "packet_identity": packet[1]["identity"],
        "status": "submitted",
        "reviewer_a_id": "A",
        "reviewer_b_id": "B",
        "adjudicator": {
            "reviewer_id": "C",
            "role": "domain_reviewer",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "independent_of_retrieval_development": True,
            "did_not_view_model_outputs": True,
            "checked_note_and_guideline_support": True,
        },
        "cases": [deepcopy(case)],
    }
    adj_path = tmp_path / "adjudication.json"
    write_json(adj_path, adj)
    frozen = freeze_labels(packet[0], ap, bp, tmp_path / "labels", adj_path)
    assert frozen["adjudicator_id"] == "C"
    assert (
        inputs(packet[0], tmp_path / "labels")[1]["NEW-001"]["reference_outcome"]
        == "temporarily_unfit"
    )


def test_invented_guideline_quote_or_note_quote_is_rejected(packet, tmp_path):
    a, b = form(packet, "A"), form(packet, "B")
    for review in (a, b):
        review["cases"][0]["documented_facts"] = [
            {
                "module": "hypertension",
                "field": "cardiovascular.blood_pressure.observed_systolic",
                "value": 180,
                "note_quote": "not present in the note",
            }
        ]
    ap, bp = submit(tmp_path, a, b)
    with pytest.raises(ValueError, match="source-note quotation"):
        freeze_labels(packet[0], ap, bp, tmp_path / "labels")
    for review in (a, b):
        review["cases"][0]["documented_facts"] = []
        review["cases"][0]["overall"]["guideline_citations"] = [
            {
                "pdf_page": 1,
                "section": "2.3",
                "quote": "An invented rule that does not exist on the page.",
                "licence_scope": "commercial",
            }
        ]
    ap, bp = submit(tmp_path, a, b)
    with pytest.raises(ValueError, match="original PDF page"):
        freeze_labels(packet[0], ap, bp, tmp_path / "labels")


def test_source_notes_have_no_answer_fields_and_rendered_packet_has_no_expected_labels():
    root = Path(__file__).resolve().parents[1]
    source = json.loads((root / "configs/experiments/prospective_notes_v1.json").read_bytes())
    assert len(source["cases"]) == 12 and all(
        len(c["nurse_note"].split()) >= 180 for c in source["cases"]
    )
    assert all(set(c) == {"case_id", "nurse_note"} for c in source["cases"])
    html = render([{**source["cases"][0], "note_path": "notes/PROS-001.txt"}], "annotations.json")
    assert "PROS-001" in html and "annotations.json" in html and "Expected outcome" not in html


def test_form_schemas_keep_drafts_blank_and_reject_extra_predictions():
    assert "cases" in ReviewSubmission.model_json_schema()["properties"]
    assert "cases" in Adjudication.model_json_schema()["properties"]
    with pytest.raises(ValueError):
        ReviewSubmission.model_validate(
            {"packet_identity": "x", "cases": [], "model_prediction": "hidden"}
        )


def test_ready_boolean_does_not_replace_submitted_review_records(packet, tmp_path):
    ap, bp = submit(tmp_path, form(packet, "A"), form(packet, "B"))
    output = tmp_path / "labels"
    freeze_labels(packet[0], ap, bp, output)
    review = json.loads((output / "reviewer_a.json").read_bytes())
    review["status"] = "draft"
    write_json(output / "reviewer_a.json", review)
    write_json(
        output / "artifacts.json",
        {
            p.name: file_hash(p)
            for p in output.iterdir()
            if p.is_file() and p.name != "artifacts.json"
        },
    )
    with pytest.raises(ValueError, match="submitted"):
        inputs(packet[0], output)


@pytest.mark.parametrize("mutation", ["unknown", "wrong_module", "wrong_type", "range", "enum"])
def test_review_facts_require_real_dictionary_fields_types_and_modules(packet, tmp_path, mutation):
    a, b = form(packet, "A"), form(packet, "B")
    fact = {
        "module": "hypertension",
        "field": "cardiovascular.blood_pressure.observed_systolic",
        "value": 180,
        "note_quote": "measured blood pressure was 180/110 mmHg",
    }
    if mutation == "unknown":
        fact["field"] = "diabetes.invented"
    elif mutation == "wrong_module":
        fact.update(module="diabetes", field="blackout.occurred", value=True)
    elif mutation == "wrong_type":
        fact["value"] = "180"
    elif mutation == "range":
        fact["value"] = 900
    else:
        fact.update(module="blackout", field="blackout.occurred", value="not documented")
    a["cases"][0]["documented_facts"] = [fact]
    ap, bp = submit(tmp_path, a, b)
    with pytest.raises(ValueError, match="dictionary/module/type"):
        freeze_labels(packet[0], ap, bp, tmp_path / "labels")


def test_pdf_page_presence_does_not_replace_independent_section_scope_check(packet, tmp_path):
    a, b = form(packet, "A"), form(packet, "B")
    for review in (a, b):
        review["cases"][0]["overall"]["guideline_citations"] = [
            {
                "pdf_page": 1,
                "section": "invented-section",
                "licence_scope": "commercial",
                "quote": "Commercial standards require assessment of persistent hypertension.",
            }
        ]
    ap, bp = submit(tmp_path, a, b)
    with pytest.raises(ValueError, match="verification is required"):
        real_freeze_labels(packet[0], ap, bp, tmp_path / "labels")
    sp = verified_sources(packet[0], ap, bp)
    data = json.loads(sp.read_bytes())
    data["citations"][0]["section_verified"] = False
    write_json(sp, data)
    with pytest.raises(ValueError, match="verification is incomplete"):
        real_freeze_labels(packet[0], ap, bp, tmp_path / "labels", source_verification_path=sp)
    data["citations"][0].update(section_verified=True, section="2.3")
    write_json(sp, data)
    with pytest.raises(ValueError, match="section/scope differs"):
        real_freeze_labels(packet[0], ap, bp, tmp_path / "labels", source_verification_path=sp)


def repin(folder):
    write_json(
        folder / "artifacts.json",
        {
            p.relative_to(folder).as_posix(): file_hash(p)
            for p in folder.rglob("*")
            if p.is_file() and p.name != "artifacts.json"
        },
    )


@pytest.mark.parametrize(
    "mutation", ["identity", "note_text", "note_sha", "path", "missing_artifact", "contracts"]
)
def test_rehashed_packet_cannot_bypass_case_and_contract_bindings(packet, tmp_path, mutation):
    ap, bp = submit(tmp_path, form(packet, "A"), form(packet, "B"))
    output = tmp_path / "labels"
    freeze_labels(packet[0], ap, bp, output)
    manifest = deepcopy(packet[1])
    if mutation == "identity":
        manifest["case_count"] = 20
    elif mutation == "note_text":
        manifest["cases"][0]["nurse_note"] += " altered"
    elif mutation == "note_sha":
        manifest["cases"][0]["note_sha256"] = "wrong"
    elif mutation == "path":
        manifest["cases"][0]["note_path"] = "../outside.txt"
    elif mutation == "missing_artifact":
        (packet[0] / "gate_source.py").unlink()
    else:
        snapshot = json.loads((packet[0] / "implementation_snapshot.json").read_bytes())
        snapshot.pop("src/occupational_fitness_rag/evaluation/prospective_review.py")
        write_json(packet[0] / "implementation_snapshot.json", snapshot)
        manifest["development_implementation_identity"] = digest(snapshot)
    if mutation != "identity":
        manifest["identity"] = digest({k: v for k, v in manifest.items() if k != "identity"})
    write_json(packet[0] / "manifest.json", manifest)
    repin(packet[0])
    with pytest.raises(ValueError):
        inputs(packet[0], output)


def test_live_code_or_model_drift_blocks_prospective_execution(packet, tmp_path):
    ap, bp = submit(tmp_path, form(packet, "A"), form(packet, "B"))
    output = tmp_path / "labels"
    freeze_labels(packet[0], ap, bp, output)
    root = packet[0].parent / "root"
    with pytest.raises(ValueError, match="model weight digest drift"):
        prospective_inputs(
            packet[0],
            output,
            root=root,
            runtime_probe=lambda endpoint, route: (
                {"version": "fixture-runtime"}
                if route == "/api/version"
                else {"models": [{"name": "fixture-model", "digest": "wrong"}]}
            ),
        )
    (root / "src/occupational_fitness_rag/provenance.py").write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="artifact drift"):
        inputs(packet[0], output)


def test_source_verifier_cannot_be_an_annotator(packet, tmp_path):
    ap, bp = submit(tmp_path, form(packet, "A"), form(packet, "B"))
    sp = verified_sources(packet[0], ap, bp)
    data = json.loads(sp.read_bytes())
    data["verifier_id"] = "A"
    write_json(sp, data)
    with pytest.raises(ValueError, match="separate independent source verifier"):
        real_freeze_labels(packet[0], ap, bp, tmp_path / "labels", source_verification_path=sp)


def test_source_schema_keeps_manual_scope_attestations_blank():
    form = SourceVerification(packet_identity="fixture").model_dump()
    assert form["status"] == "draft" and form["verifier_id"] is None


def test_explicit_runner_addition_preserves_labels_and_methods(packet, tmp_path):
    ap, bp = submit(tmp_path, form(packet, "A"), form(packet, "B"))
    labels = tmp_path / "labels"
    freeze_labels(packet[0], ap, bp, labels)
    label_pin = file_hash(labels / "labels.json")
    root = packet[0].parent / "root"
    (root / "tools/new_prospective_runner.py").write_text("fixture runner", encoding="utf-8")
    with pytest.raises(ValueError, match="dependency inventory changed"):
        inputs(packet[0], labels)
    amendment = tmp_path / "amendment"
    freeze_execution_amendment(
        packet[0],
        labels,
        amendment,
        root=root,
        coordinator_id="coordinator",
        runner_source="tools/new_prospective_runner.py",
        reason="Integrate the new runner without changing any frozen strategy.",
        zero_prior_inference_attested=True,
    )
    cases, _ = inputs(packet[0], labels, execution_amendment_directory=amendment)
    assert len(cases) == 1 and file_hash(labels / "labels.json") == label_pin
    # Consumption must reject a retuned component even when every editable hash is recomputed.
    changed = "src/occupational_fitness_rag/provenance.py"
    (root / changed).write_text("retuned prompt or strategy", encoding="utf-8")
    plan = json.loads((amendment / "execution_plan.json").read_bytes())
    plan["source_sha256"][changed] = file_hash(root / changed)
    plan["identity"] = digest({k: v for k, v in plan.items() if k != "identity"})
    write_json(amendment / "execution_plan.json", plan)
    record = json.loads((amendment / "record.json").read_bytes())
    record["execution_plan_identity"] = plan["identity"]
    record["identity"] = digest({k: v for k, v in record.items() if k != "identity"})
    write_json(amendment / "record.json", record)
    repin(amendment)
    with pytest.raises(ValueError, match="changed existing sources"):
        inputs(packet[0], labels, execution_amendment_directory=amendment)


def test_runner_amendment_rejects_existing_prompt_or_strategy_changes(packet, tmp_path):
    ap, bp = submit(tmp_path, form(packet, "A"), form(packet, "B"))
    labels = tmp_path / "labels"
    freeze_labels(packet[0], ap, bp, labels)
    root = packet[0].parent / "root"
    (root / "tools/new_runner.py").write_text("fixture runner", encoding="utf-8")
    (root / "src/occupational_fitness_rag/provenance.py").write_text("retuned", encoding="utf-8")
    with pytest.raises(ValueError, match="runner-only amendment refused"):
        freeze_execution_amendment(
            packet[0],
            labels,
            tmp_path / "amendment",
            root=root,
            coordinator_id="coordinator",
            runner_source="tools/new_runner.py",
            reason="Attempt to modify an existing experimental component.",
            zero_prior_inference_attested=True,
        )
    assert not (tmp_path / "amendment").exists()


def test_pending_harness_and_native_index_cannot_report_execution_ready(packet, tmp_path):
    from occupational_fitness_rag.evaluation.prospective_review import _verify_execution

    root = packet[0].parent / "root"
    plan = json.loads((packet[0] / "execution_plan.json").read_bytes())
    plan["harness_integration"] = "pending"
    with pytest.raises(ValueError, match="harness is still pending"):
        _verify_execution(plan, root, runtime_probe)
    plan["harness_integration"] = "integrated"
    plan["native_index_preflight_required"] = True
    with pytest.raises(ValueError, match="native-index preflight is still pending"):
        _verify_execution(plan, root, runtime_probe)
