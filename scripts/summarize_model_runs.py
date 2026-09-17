"""Summarize actual local-model calls from the verified demonstration bundles."""

import json
from collections import Counter
from pathlib import Path

from occupational_fitness_rag.provenance import write_json

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest_path = ROOT / "outputs/demo/manifest.json"
    if not manifest_path.exists():
        manifest_path = ROOT / "outputs/demo_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = []
    for entry in manifest:
        directory = ROOT / entry["output"]
        extraction = json.loads(
            (directory / "llm_extraction_audit.json").read_text(encoding="utf-8")
        )
        narrative_path = directory / "llm_narrative_audit.json"
        narrative = (
            json.loads(narrative_path.read_text(encoding="utf-8"))
            if narrative_path.exists()
            else {}
        )
        records.append(
            {
                "case_id": entry["case_id"],
                "model": extraction.get("model"),
                "model_digest": extraction.get("model_digest"),
                "extraction_status": extraction["status"],
                "grounded_fields": len(extraction.get("accepted_fields", [])),
                "withheld_proposals": len(extraction.get("withheld", [])),
                "extraction_seconds": round(
                    sum(c.get("total_duration", 0) or 0 for c in extraction.get("calls", [])) / 1e9,
                    3,
                ),
                "narrative_status": narrative.get("status", "unavailable"),
            }
        )
    success = sum(
        r["extraction_status"].startswith("completed")
        and bool(r["model_digest"])
        and r["narrative_status"] == "completed"
        for r in records
    )
    report = {
        "cases": len(records),
        "completed_extraction_and_narrative": success,
        "extraction_statuses": dict(Counter(r["extraction_status"] for r in records)),
        "grounded_fields": sum(r["grounded_fields"] for r in records),
        "withheld_proposals": sum(r["withheld_proposals"] for r in records),
        "clinical_validation": False,
        "scope": "Actual local-model integration on supplied and authored synthetic inputs. Grounded field counts are not recall or clinical accuracy estimates.",
        "records": records,
    }
    write_json(ROOT / "outputs/evaluation/model_integration.json", report)
    print(json.dumps({k: v for k, v in report.items() if k != "records"}, indent=2))
    if success != len(records):
        raise SystemExit("Some model calls failed; inspect the explicit fallback records")


if __name__ == "__main__":
    main()
