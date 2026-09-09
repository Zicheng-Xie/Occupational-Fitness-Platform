"""Published rule-to-knowledge contracts; executable predicates remain authoritative."""

from occupational_fitness_rag.provenance import write_json


def readable_logic(node):
    for operator, joiner in (("all", " AND "), ("any", " OR ")):
        if operator in node:
            return "(" + joiner.join(readable_logic(child) for child in node[operator]) + ")"
    if "triggered_rule" in node:
        return "TRIGGERED(" + node["triggered_rule"] + ")"
    return f"{node['field']} {node['operator']} {node['value']}"


def export_knowledge_contracts(root, book, catalogue):
    knowledge = list(catalogue.units.values())
    write_json(
        root / "data/knowledge/processed/knowledge_units.json",
        {"schema_version": "1.2.0", "units": knowledge},
    )
    rules = []
    for rule in book.rules:
        rules.append(
            {
                "rule_id": rule["rule_id"],
                "required_facts": rule["required_facts"],
                "logic": readable_logic(rule["condition"]),
                "predicate": rule["condition"],
                "gate": rule.get("gate"),
                "result": "unconditional_standard_not_met"
                if "UNCONDITIONAL" in rule["rule_id"]
                and rule["outcome"]["assessment_outcome"] != "meets_unconditional_standard"
                else rule["outcome"]["assessment_outcome"],
                "workflow_outcome": rule["outcome"],
                "source_id": rule["source_ids"][0],
                "source_ids": rule["source_ids"],
                "category": rule["category"],
                "condition": rule["subcondition"],
                "rag_query_key": rule["rag_query_key"],
                "ruleset_sha256": book.sha256,
            }
        )
    write_json(
        root / "configs/rules/rule_knowledge_contract.json",
        {"schema_version": "1.2.0", "rules": rules},
    )
    return {"knowledge_units": len(knowledge), "linked_rules": len(rules)}
