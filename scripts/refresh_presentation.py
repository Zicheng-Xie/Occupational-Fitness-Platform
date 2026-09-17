"""Refresh HTML presentation from verified assessments without model calls.

Only report HTML, its manifest and the append-only audit chain are updated.
All input, clinical, narrative and Markdown artifacts must remain byte-identical.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from occupational_fitness_rag.pipeline.workflow import OccupationalFitnessWorkflow
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json
from occupational_fitness_rag.reporting.presentation import render_case_html, render_library
from occupational_fitness_rag.schemas.workflow import (
    ClinicalCase,
    ReviewNote,
    WorkflowEvidencePack,
    WorkflowRuleResult,
)

ROOT = Path(__file__).resolve().parents[1]


def refresh(root: Path):
    root = root.resolve()
    workflow = OccupationalFitnessWorkflow(root / "configs/workflow.offline.yaml")
    manifest_path = root / "outputs/demo/manifest.json"
    if not manifest_path.exists():
        manifest_path = root / "outputs/demo_manifest.json"
    entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    style_hash = digest(
        {
            name: sha256_bytes(
                (root / "src/occupational_fitness_rag/reporting" / name).read_bytes()
            )
            for name in ("presentation.py", "styles.py")
        }
    )
    plans, directory, records = [], [], []
    # Validate every input and render every page before changing any deliverable.
    for entry in entries:
        output = (root / entry["output"]).resolve()
        if not any(
            output.is_relative_to(root / folder) for folder in ("outputs/runs", "outputs/demo")
        ):
            raise ValueError("Assessment path outside the report directory")
        workflow.verify_run(output)
        manifest_bytes = (output / "run_manifest.json").read_bytes()
        manifest = json.loads(manifest_bytes)
        case = ClinicalCase.model_validate_json((output / "structured_case.json").read_bytes())
        result = WorkflowRuleResult.model_validate_json((output / "rule_result.json").read_bytes())
        evidence = WorkflowEvidencePack.model_validate_json(
            (output / "evidence_pack.json").read_bytes()
        )
        note = ReviewNote.model_validate_json((output / "gp_review_note.json").read_bytes())
        if note.status != "DRAFT":
            raise ValueError("Signed reports cannot be refreshed")
        before = {
            name: (output / name).read_bytes()
            for name in ("draft_report.html", "audit_events.jsonl", "run_manifest.json")
        }
        preserved = {
            name: fingerprint
            for name, fingerprint in manifest["files"].items()
            if name not in before
        }
        html_bytes = render_case_html(case, result, evidence, note, root, output).encode("utf-8")
        event = {
            "sequence": len(before["audit_events.jsonl"].splitlines()) + 1,
            "stage": "report_presentation_refreshed",
            "case_id": case.case_id,
            "refreshed_at": datetime.now(timezone.utc).isoformat(),
            "presentation_sha256": style_hash,
            "previous_html_sha256": sha256_bytes(before["draft_report.html"]),
            "html_sha256": sha256_bytes(html_bytes),
            "previous_manifest_sha256": sha256_bytes(manifest_bytes),
            "assessment_recomputed": False,
            "previous_event_sha256": manifest["audit_head_sha256"],
        }
        signature = digest(event)
        audit_bytes = (
            before["audit_events.jsonl"].rstrip(b"\r\n")
            + b"\n"
            + (json.dumps({**event, "event_sha256": signature}) + "\n").encode("utf-8")
        )
        manifest["audit_head_sha256"] = signature
        manifest["presentation"] = {
            **manifest.get("presentation", {}),
            "language": "en",
            "implementation_sha256": style_hash,
            "refreshed_at": event["refreshed_at"],
            "assessment_recomputed": False,
        }
        manifest["files"].update(
            {
                "draft_report.html": sha256_bytes(html_bytes),
                "audit_events.jsonl": sha256_bytes(audit_bytes),
            }
        )
        plans.append((output, before, html_bytes, audit_bytes, manifest, preserved))
        directory.append(
            {
                **entry,
                "relative": output.relative_to(root / "outputs").as_posix(),
                "missing_count": len({key for m in result.modules for key in m.missing_fields}),
            }
        )
    index = root / "outputs/index.html"
    old_index = index.read_bytes()
    new_index = render_library(directory).encode("utf-8")
    changed = []
    try:
        for output, before, html_bytes, audit_bytes, manifest, preserved in plans:
            changed.append((output, before))
            if html_bytes != before["draft_report.html"]:
                (output / "draft_report.html").write_bytes(html_bytes)
                (output / "audit_events.jsonl").write_bytes(audit_bytes)
                write_json(output / "run_manifest.json", manifest)
            for name, fingerprint in preserved.items():
                if sha256_bytes((output / name).read_bytes()) != fingerprint:
                    raise ValueError(f"Assessment artifact changed: {output.name}/{name}")
            records.append(
                {
                    **workflow.verify_run(output),
                    "run_directory": output.relative_to(root).as_posix(),
                    "unchanged_artifacts": preserved,
                    "html_updated": html_bytes != before["draft_report.html"],
                }
            )
        index.write_bytes(new_index)
    except Exception:
        for output, before in reversed(changed):
            for name, data in before.items():
                (output / name).write_bytes(data)
        index.write_bytes(old_index)
        raise
    report = {
        "status": "passed",
        "runs": len(records),
        "assessment_recomputed": False,
        "model_calls": 0,
        "unchanged_artifacts": sum(len(r["unchanged_artifacts"]) for r in records),
        "presentation_sha256": style_hash,
        "records": records,
    }
    write_json(root / "outputs/evaluation/presentation_refresh.json", report)
    print(
        f"Refreshed {len(records)} reports; preserved {report['unchanged_artifacts']} artifacts; no model calls"
    )


if __name__ == "__main__":
    refresh(ROOT)
