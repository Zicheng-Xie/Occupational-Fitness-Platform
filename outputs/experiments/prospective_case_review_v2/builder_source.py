"""Prepare blinded prospective notes or freeze independently supplied labels.

Preparation reads no existing holdout contents and calls no extraction, retrieval,
judge or network service. Reviewer ZIPs exclude development implementation data.
"""

from __future__ import annotations

import argparse
import json
import shutil
from html import escape
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import fitz
import yaml

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.evaluation.prospective_review import (
    MODULES,
    Adjudication,
    CaseAnnotation,
    ReviewSubmission,
    SourceVerification,
    freeze_execution_amendment,
    freeze_labels,
    prospective_inputs,
    snapshot_paths,
    source_verification_template,
)
from occupational_fitness_rag.provenance import digest, write_json

GUIDELINE_SHA256 = "5811cfbb29c4db2cec704033ec2ee31506e78445ed8108e72d324cbef780500c"
DEFAULT_OUTPUT = "outputs/experiments/prospective_case_review_v2"

INSTRUCTIONS = """# Independent prospective annotation

This packet contains newly authored synthetic notes, not real patient data.
It has no model predictions, retrieval outputs or expected answers. No system
evaluation has been run on these notes. The entire original guideline is supplied
as guideline.pdf; use its commercial-driver or explicitly shared provisions.

Work independently. Do not inspect another reviewer's answers or any model output.
Do not use a language model to supply the labels. Keep relative dates, family
history, historical tests, negation, aiding/correction and missing measurements
separate. Missing or uncertain information is not a normal finding.

1. Copy annotations.json to a separate working location. Keep the case IDs,
   packet_identity and source-note fingerprints unchanged.
2. Enter your stable reviewer ID, role and timezone-aware completion time.
   Clinicians and independent domain reviewers can provide engineering reference
   labels. Declare authorship/development independence and blinded review truthfully.
   A coordinator must verify identity and qualifications separately; a JSON
   declaration is not professional credential verification.
3. Review every note and all five requested modules. Record documented facts with
   exact note quotations, preserving whose history and which time are described.
   Use exact keys/types from field_dictionary.json; cardiovascular keys belong to
   hypertension, and the other field prefixes identify their assessment module.
4. Supply each module outcome and the overall outcome with a substantive rationale.
   For a substantive fitness label, cite original guideline page, section and an
   exact source quotation and provide a documented fact for that module.
   Information-insufficient labels must explain the actual unresolved information.
   Source quotations and note quotations are checked against their original text;
   those checks do not establish clinical entailment.
5. After completing all cases, set status to submitted and return the form to
   the coordinator. Do not replace the original immutable template.

Allowed outcomes: meets_unconditional_standard, may_meet_conditional_standard,
temporarily_unfit, does_not_meet_standard, insufficient_information.

Two different reviewers submit independently. Only case/module disagreements
require a distinct adjudicator, who checks the notes and guideline without model
outputs. The final labels must be frozen before prospective system execution or
scoring. These are engineering reference labels; clinical accuracy remains
unestablished until the required qualified review and validation are completed.
After annotation, a separate coordinator verifies each cited original PDF region,
section, commercial/shared column, footnotes and qualifications. Literal page text
matching alone cannot establish section membership or commercial applicability.
"""


def render(cases, annotation_link=None):
    links = '<a href="guideline.pdf">Original guideline</a>'
    if annotation_link:
        links += (
            ' · <a href="' + escape(annotation_link, quote=True) + '">Blank annotation form</a>'
        )
    else:
        links += ' · <a href="reviewer_a.zip">Reviewer A packet</a> · <a href="reviewer_b.zip">Reviewer B packet</a>'
    links += ' · <a href="instructions.md">Independent-review instructions</a>'
    body = "".join(
        "<article><h2>"
        + escape(c["case_id"])
        + '</h2><p><a href="'
        + escape(c["note_path"], quote=True)
        + '">Original TXT note</a></p><pre>'
        + escape(c["nurse_note"])
        + "</pre></article>"
        for c in cases
    )
    return (
        """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Independent prospective review | Occupational Fitness Platform</title><style>body{font:15px/1.65 Arial,sans-serif;background:#f4f6f8;color:#23394a;max-width:1120px;margin:32px auto;padding:24px}header,article{background:white;border:1px solid #dce4eb;border-radius:8px;padding:26px;margin:18px 0}h1{font-size:28px}h2{font-size:18px}pre{font:14px/1.75 Arial,sans-serif;white-space:pre-wrap;overflow-wrap:anywhere}a{color:#235b82}.notice{border-left:4px solid #b17b27;padding:14px;background:#faf3e5}</style><header><small>OCCUPATIONAL FITNESS PLATFORM · INDEPENDENT ANNOTATION</small><h1>Prospective nurse-note review</h1><p class="notice">12 synthetic notes · No system predictions · Independent labels pending · Prospective evaluation not started. These cases have not been used by the evaluated retrieval or judgment models.</p><p>"""
        + links
        + "</p></header>"
        + body
        + "</html>"
    )


def prepare(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists() or not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Use a fresh isolated prospective packet directory")
    source = root / "configs/experiments/prospective_notes_v1.json"
    definition = json.loads(source.read_bytes())
    cases = definition["cases"]
    if (
        len(cases) != 12
        or len({c["case_id"] for c in cases}) != 12
        or any(
            set(c) != {"case_id", "nurse_note"} or len(c["nurse_note"].split()) < 180 for c in cases
        )
    ):
        raise ValueError(
            "The packet requires twelve unique long-form notes and no embedded answer fields"
        )
    guide = root / "data/knowledge/raw/ap_g56_22.pdf"
    if file_hash(guide) != GUIDELINE_SHA256:
        raise ValueError("The original guideline identity differs")
    snapshot = {name: file_hash(root / name) for name in snapshot_paths(root)}
    config_path = root / "configs/experiments/case_allocation_judgments_v1.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    preparation = json.loads(
        (
            root / "outputs/experiments/case_allocation_judgment_preparation_v1/manifest.json"
        ).read_bytes()
    )
    corpus_path = "outputs/experiments/scope88_optimization_comparison_v2/corpus.json"
    vector_path = "outputs/experiments/scope88_shared_retrieval_v2/corpus_vectors.json"
    native_path = "outputs/experiments/scope88_neo4j_strategies_v2/native_input.json"
    native = json.loads((root / native_path).read_bytes())
    native_contract = {key: native[key] for key in ("corpus", "corpus_vectors", "config")}
    retrieval_config = yaml.safe_load(
        (root / "configs/experiments/planned_hybrid_v1.yaml").read_text(encoding="utf-8")
    )
    plan_data = {
        "kind": "prospective_execution_plan_v2",
        "status": "frozen_before_first_inference",
        "arms": preparation["arms"],
        "expected_model_digests": {
            **config["expected_model_digests"],
            retrieval_config["embedding_model"]: retrieval_config["embedding_model_digest"],
        },
        "expected_runtime_version": config["expected_runtime_version"],
        "endpoint": config["endpoint"],
        "options": {
            key: config[key]
            for key in (
                "repeats",
                "context_length",
                "output_tokens",
                "evidence_max_bytes",
                "request_max_bytes",
            )
        },
        "temperature": 0,
        "seed": 0,
        "source_sha256": snapshot,
        "runtime_artifacts": {
            name: file_hash(root / name) for name in (corpus_path, vector_path, native_path)
        },
        "native_index_expected_identity": digest(native_contract),
        "native_index_preflight_required": True,
        "reference_labels_are_model_inputs": False,
        "harness_integration": "pending",
    }
    plan = {**plan_data, "identity": digest(plan_data)}
    specs = json.loads((root / "schemas/field_dictionary.json").read_bytes())
    with fitz.open(guide) as pdf:
        pages = len(pdf)
    records = [
        {
            **c,
            "note_path": "notes/" + c["case_id"] + ".txt",
            "note_sha256": digest(c["nurse_note"].encode("utf-8").hex()),
            "note_file_sha256": None,
        }
        for c in cases
    ]
    output.mkdir(parents=True)
    (output / "notes").mkdir()
    for case in records:
        path = output / case["note_path"]
        path.write_bytes((case["nurse_note"] + "\n").encode("utf-8"))
        case["note_sha256"] = file_hash(path)
        case.pop("note_file_sha256")
    data = {
        "kind": "prospective_blinded_review_packet",
        "cases": records,
        "case_count": 12,
        "requested_modules": list(MODULES),
        "guideline_sha256": GUIDELINE_SHA256,
        "guideline_page_count": pages,
        "development_implementation_identity": digest(snapshot),
        "execution_plan_identity": plan["identity"],
        "field_dictionary_identity": digest(specs),
        "source_definition_sha256": file_hash(source),
        "case_authorship": "AI-assisted synthetic fixture authoring; independent labels are not generated",
        "independent_annotation_status": "pending",
        "system_evaluation_status": "not_started",
        "existing_holdout_contents_opened": False,
        "production_change": False,
    }
    manifest = {**data, "identity": digest(data)}
    write_json(output / "manifest.json", manifest)
    write_json(output / "implementation_snapshot.json", snapshot)
    write_json(output / "execution_plan.json", plan)
    write_json(output / "native_index_contract.json", native_contract)
    shutil.copy2(root / "schemas/field_dictionary.json", output / "field_dictionary.json")
    shutil.copy2(guide, output / "guideline.pdf")
    annotations = [
        CaseAnnotation(
            case_id=c["case_id"],
            source_note_sha256=c["note_sha256"],
            module_assessments={m: {} for m in MODULES},
            overall={},
        )
        for c in records
    ]
    template = ReviewSubmission(packet_identity=manifest["identity"], cases=annotations).model_dump(
        mode="json"
    )
    for name in ("reviewer_a.template.json", "reviewer_b.template.json"):
        write_json(output / name, template)
    write_json(
        output / "adjudication.template.json",
        Adjudication(packet_identity=manifest["identity"], cases=[]).model_dump(mode="json"),
    )
    write_json(output / "review.schema.json", ReviewSubmission.model_json_schema())
    write_json(output / "adjudication.schema.json", Adjudication.model_json_schema())
    write_json(output / "source_verification.schema.json", SourceVerification.model_json_schema())
    write_json(
        output / "source_verification.template.json",
        SourceVerification(packet_identity=manifest["identity"]).model_dump(mode="json"),
    )
    (output / "instructions.md").write_text(INSTRUCTIONS, encoding="utf-8")
    (output / "index.html").write_text(render(records), encoding="utf-8")
    for role in ("a", "b"):
        with ZipFile(output / f"reviewer_{role}.zip", "x", compression=ZIP_DEFLATED) as bundle:
            for c in records:
                bundle.write(output / c["note_path"], c["note_path"])
            bundle.write(output / "guideline.pdf", "guideline.pdf")
            bundle.write(output / "instructions.md", "instructions.md")
            bundle.write(output / "review.schema.json", "review.schema.json")
            bundle.write(output / "field_dictionary.json", "field_dictionary.json")
            bundle.write(output / "manifest.json", "manifest.json")
            bundle.writestr("index.html", render(records, "annotations.json"))
            bundle.writestr(
                "annotations.json", json.dumps(template, ensure_ascii=False, indent=2) + "\n"
            )
    write_json(
        output / "readiness.json",
        {
            "ready_for_prospective_evaluation": False,
            "reason": "Independent annotations, any disputed-label adjudication, and separate source/section/scope verification remain pending; harness integration is not yet implemented",
            "labels_generated_by_ai": False,
            "system_calls": 0,
            "clinical_accuracy_established": False,
        },
    )
    (output / "builder_source.py").write_bytes(Path(__file__).read_bytes())
    (output / "gate_source.py").write_bytes(
        (root / "src/occupational_fitness_rag/evaluation/prospective_review.py").read_bytes()
    )
    write_json(
        output / "artifacts.json",
        {p.relative_to(output).as_posix(): file_hash(p) for p in output.rglob("*") if p.is_file()},
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--output", type=Path, default=Path(DEFAULT_OUTPUT))
    p = sub.add_parser("freeze-labels")
    p.add_argument("--packet", type=Path, default=Path(DEFAULT_OUTPUT))
    p.add_argument("--reviewer-a", type=Path, required=True)
    p.add_argument("--reviewer-b", type=Path, required=True)
    p.add_argument("--adjudication", type=Path)
    p.add_argument("--source-verification", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("check-ready")
    p.add_argument("--packet", type=Path, default=Path(DEFAULT_OUTPUT))
    p.add_argument("--labels", type=Path, required=True)
    p.add_argument("--root", type=Path, default=Path.cwd())
    p.add_argument("--execution-amendment", type=Path)
    p = sub.add_parser("freeze-execution-amendment")
    p.add_argument("--packet", type=Path, default=Path(DEFAULT_OUTPUT))
    p.add_argument("--labels", type=Path, required=True)
    p.add_argument("--root", type=Path, default=Path.cwd())
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--coordinator-id", required=True)
    p.add_argument("--runner-source", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--attest-zero-prior-inference", action="store_true", required=True)
    p = sub.add_parser("source-check-template")
    p.add_argument("--packet", type=Path, default=Path(DEFAULT_OUTPUT))
    p.add_argument("--reviewer-a", type=Path, required=True)
    p.add_argument("--reviewer-b", type=Path, required=True)
    p.add_argument("--adjudication", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(Path.cwd(), args.output)
        print(
            json.dumps(
                {
                    k: result[k]
                    for k in (
                        "identity",
                        "case_count",
                        "independent_annotation_status",
                        "system_evaluation_status",
                    )
                },
                indent=2,
            )
        )
    elif args.command == "freeze-labels":
        result = freeze_labels(
            args.packet,
            args.reviewer_a,
            args.reviewer_b,
            args.output,
            args.adjudication,
            source_verification_path=args.source_verification,
        )
        print(
            json.dumps(
                {
                    k: result[k]
                    for k in (
                        "case_count",
                        "reviewer_ids",
                        "adjudicator_id",
                        "clinical_accuracy_established",
                    )
                },
                indent=2,
            )
        )
    elif args.command == "freeze-execution-amendment":
        result = freeze_execution_amendment(
            args.packet,
            args.labels,
            args.output,
            root=args.root,
            coordinator_id=args.coordinator_id,
            runner_source=args.runner_source,
            reason=args.reason,
            zero_prior_inference_attested=args.attest_zero_prior_inference,
        )
        print(json.dumps(result, indent=2))
    elif args.command == "source-check-template":
        if args.output.exists():
            raise ValueError("Keep existing human review records; choose a fresh output file")
        forms = [
            ReviewSubmission.model_validate_json(p.read_bytes())
            for p in (args.reviewer_a, args.reviewer_b)
        ]
        if args.adjudication:
            forms.append(Adjudication.model_validate_json(args.adjudication.read_bytes()))
        packet = json.loads((args.packet / "manifest.json").read_bytes())
        write_json(
            args.output,
            source_verification_template(packet["identity"], forms).model_dump(mode="json"),
        )
        print(
            "Blank independent source checks written; no scope verification or inference performed"
        )
    else:
        cases, _ = prospective_inputs(
            args.packet,
            args.labels,
            root=args.root,
            execution_amendment_directory=args.execution_amendment,
        )
        print(
            json.dumps(
                {"ready_for_prospective_evaluation": True, "cases": len(cases), "system_calls": 0}
            )
        )
