"""Issue English reports from verified runs without repeating clinical extraction."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from shutil import copyfile

from occupational_fitness_rag.llm import LocalNarrative
from occupational_fitness_rag.pipeline.workflow import OccupationalFitnessWorkflow
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json
from occupational_fitness_rag.reporting.builder import build_review_note, render_reports
from occupational_fitness_rag.schemas.workflow import (
    ClinicalCase,
    ReviewNote,
    WorkflowEvidencePack,
)
from occupational_fitness_rag.schemas.red_flag_result import WorkflowRuleResult

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous-outputs", type=Path, required=True)
    args = parser.parse_args()
    previous_outputs = args.previous_outputs.resolve()
    workflow = OccupationalFitnessWorkflow(ROOT / "configs/workflow.offline.yaml")
    previous_entries = json.loads(
        (previous_outputs / "demo_manifest.json").read_text(encoding="utf-8")
    )
    code_hash = digest(
        {
            p.relative_to(ROOT).as_posix(): sha256_bytes(p.read_bytes())
            for p in sorted((ROOT / "src/occupational_fitness_rag").rglob("*.py"))
        }
    )
    entries, checks = [], []
    for entry in previous_entries:
        relative = Path(entry["output"]).relative_to("outputs")
        source = (previous_outputs / relative).resolve()
        if not source.is_relative_to(previous_outputs):
            raise ValueError("Previous run path outside supplied archive")
        workflow.verify_run(source)
        original_manifest = (source / "run_manifest.json").read_bytes()
        manifest = json.loads(original_manifest)
        case = ClinicalCase.model_validate_json(
            (source / "structured_case.json").read_text(encoding="utf-8")
        )
        result = WorkflowRuleResult.model_validate_json(
            (source / "rule_result.json").read_text(encoding="utf-8")
        )
        evidence = WorkflowEvidencePack.model_validate_json(
            (source / "evidence_pack.json").read_text(encoding="utf-8")
        )
        note = ReviewNote.model_validate_json(
            (source / "gp_review_note.json").read_text(encoding="utf-8")
        )
        if note.status != "DRAFT":
            raise ValueError("Signed review records cannot be reissued as drafts")
        if note.llm_commentary:
            LocalNarrative(commentary=note.llm_commentary)
        note = note.model_copy(
            update={"summary": build_review_note(case, result, evidence).summary}
        )
        run_id = "run-" + digest([manifest["run_id"], code_hash, "english_report_reissue_v1"])[:20]
        output = ROOT / "outputs/runs" / case.case_id / run_id
        output.mkdir(parents=True, exist_ok=False)
        for filename in manifest["files"]:
            copyfile(source / filename, output / filename)
        write_json(output / "gp_review_note.json", note)
        for filename, text in render_reports(case, result, evidence, note, ROOT, output).items():
            (output / filename).write_text(text, encoding="utf-8")
        audit_path = output / "audit_events.jsonl"
        events = audit_path.read_text(encoding="utf-8").splitlines()
        event = {
            "sequence": len(events) + 1,
            "stage": "english_report_reissued",
            "case_id": case.case_id,
            "case_sha256": digest(case),
            "rule_result_sha256": digest(result),
            "evidence_pack_sha256": digest(evidence),
            "previous_event_sha256": manifest["audit_head_sha256"],
        }
        event_hash = digest(event)
        events.append(json.dumps({**event, "event_sha256": event_hash}))
        audit_path.write_text("\n".join(events) + "\n", encoding="utf-8")
        manifest.update(
            {
                "run_id": run_id,
                "parent_run_id": manifest["run_id"],
                "parent_run_manifest_sha256": sha256_bytes(original_manifest),
                "presentation": {
                    "language": "en",
                    "implementation_sha256": code_hash,
                    "reissued_at": datetime.now(timezone.utc).isoformat(),
                    "assessment_recomputed": False,
                    "model_calls_reused_from_parent": True,
                },
                "audit_head_sha256": event_hash,
                "files": {
                    p.name: sha256_bytes(p.read_bytes())
                    for p in sorted(output.iterdir())
                    if p.is_file()
                },
            }
        )
        write_json(output / "run_manifest.json", manifest)
        check = workflow.verify_run(output)
        preserved = [
            manifest["input_file"],
            "structured_case.json",
            "condition_map.json",
            "rule_result.json",
            "evidence_pack.json",
            "llm_extraction_audit.json",
        ]
        for filename in preserved:
            if (source / filename).read_bytes() != (output / filename).read_bytes():
                raise ValueError(f"Assessment data changed during reissue: {filename}")
        checks.append(
            {**check, "parent_run_id": manifest["parent_run_id"], "preserved_files": preserved}
        )
        entries.append({**entry, "output": output.relative_to(ROOT).as_posix()})
    write_json(ROOT / "outputs/demo_manifest.json", entries)
    write_json(
        ROOT / "outputs/evaluation/english_reissue.json",
        {
            "status": "passed",
            "runs": len(checks),
            "assessment_recomputed": False,
            "unchanged_files": sum(len(item["preserved_files"]) for item in checks),
            "records": checks,
        },
    )
    print(f"Reissued {len(checks)} English reports with unchanged assessment data")


if __name__ == "__main__":
    main()
