"""Export rule-derived field ownership for team integration."""

from occupational_fitness_rag.provenance import write_json


def export_team_contract(root, book):
    fields = {}
    for name, spec in book.field_specs.items():
        owners = [r for r in book.rules if name in r["required_facts"]]
        fields[name] = {
            **spec,
            "modules": sorted({r["module"] for r in owners}),
            "rule_ids": sorted({r["rule_id"] for r in owners}),
            "rag_query_keys": sorted({r["rag_query_key"] for r in owners}),
            "source_ids": sorted({s for r in owners for s in r["source_ids"]}),
            "statuses": ["present", "unknown", "conflicting", "requires_confirmation"],
            "evidence_required_when_present": True,
        }
    path = root / "schemas/team_field_contract.json"
    write_json(
        path,
        {
            "schema_version": "1.0.0",
            "ruleset_sha256": book.sha256,
            "clinical_review_status": "pending",
            "fields": fields,
        },
    )
    return path
