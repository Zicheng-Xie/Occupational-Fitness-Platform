"""Read historical bundles without replaying them against a different ruleset."""

import json
from pathlib import Path

from occupational_fitness_rag.provenance import digest, sha256_bytes
from occupational_fitness_rag.schemas.workflow import Citation, ClinicalCase


def verify_saved_report(workflow, output: Path):
    output = Path(output).resolve()
    manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
    result_version = json.loads((output / "rule_result.json").read_text(encoding="utf-8")).get(
        "schema_version"
    )
    if (
        manifest["ruleset_sha256"] == workflow.book.sha256
        and manifest["index_sha256"] == workflow.catalogue.index_sha256
        and result_version == "1.3.0"
    ):
        return workflow.verify_run(output)
    required = {
        "structured_case.json",
        "condition_map.json",
        "rule_result.json",
        "evidence_pack.json",
        "gp_review_note.json",
        "draft_report.md",
        "draft_report.html",
        "audit_events.jsonl",
    }
    if not required <= set(manifest["files"]):
        raise ValueError("Historical manifest omits a required artifact")
    for name, expected in manifest["files"].items():
        path = (output / name).resolve()
        if path.parent != output or sha256_bytes(path.read_bytes()) != expected:
            raise ValueError(f"Historical artifact fingerprint mismatch: {name}")

    def read(name):
        return json.loads((output / name).read_text(encoding="utf-8"))

    case_data = read("structured_case.json")
    case = ClinicalCase.model_validate(case_data)
    input_file = manifest.get("input_file")
    if input_file not in manifest["files"]:
        raise ValueError("Historical manifest omits its original input")
    if sha256_bytes((output / input_file).read_bytes()) != case.source_sha256:
        raise ValueError("Historical input fingerprint mismatch")
    result, evidence, note = (
        read(name) for name in ("rule_result.json", "evidence_pack.json", "gp_review_note.json")
    )
    if result.get("schema_version") not in {"1.2.0", "1.3.0"}:
        raise ValueError("Unsupported historical rule result contract")
    ruleset = result.get("ruleset", result)
    if (
        ruleset["ruleset_sha256"] != manifest["ruleset_sha256"]
        or evidence["index_sha256"] != manifest["index_sha256"]
        or any(item["case_id"] != case.case_id for item in (result, evidence, note, manifest))
        or result["case_sha256"] != digest(case_data)
        or evidence["result_id"] != result["result_id"]
        or evidence["rule_result_sha256"] != digest(result)
        or note["rule_result_sha256"] != digest(result)
        or note["evidence_pack_sha256"] != digest(evidence)
    ):
        raise ValueError("Historical artifact references disagree")
    review = case.extraction_metadata.get("semantic_review")
    if review is not None and (
        "llm_semantic_review.json" not in manifest["files"]
        or read("llm_semantic_review.json") != review
        or review["output_facts_sha256"] != digest(case.facts)
    ):
        raise ValueError("Historical semantic review disagrees with saved facts")
    workflow.catalogue.verify()
    for item in evidence["evidence_items"]:
        for data in item["citations"]:
            citation = Citation.model_validate(data)
            if citation != workflow.catalogue.citation(
                citation.source_id, citation.retrieval_score, citation.score_type
            ):
                raise ValueError("Historical citation cannot be verified against the retained PDF")
    previous = "0" * 64
    for sequence, line in enumerate(
        (output / "audit_events.jsonl").read_text(encoding="utf-8").splitlines(), 1
    ):
        event = json.loads(line)
        signature = event.pop("event_sha256")
        if (
            event["sequence"] != sequence
            or event["previous_event_sha256"] != previous
            or digest(event) != signature
        ):
            raise ValueError("Historical audit chain mismatch")
        previous = signature
    if previous != manifest["audit_head_sha256"]:
        raise ValueError("Historical audit head mismatch")
    return {
        "status": "historical_verified",
        "case_id": case.case_id,
        "files": len(manifest["files"]),
        "rules_replayed": False,
        "source_citations_verified": True,
    }
