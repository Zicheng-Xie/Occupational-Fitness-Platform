"""Fact-scoped experimental queries without rule decisions or reference labels.

Only frozen verified patient fields and their original quotations form the query.
The original case and the judgment payload are never rewritten by this helper.
"""

import hashlib
import json
import re
from collections.abc import Mapping

from occupational_fitness_rag.evaluation.evidence_selection import MODULES

QUERY_POLICY = "verified_module_facts_v1"


def _field_module(name):
    prefix = name.split(".", 1)[0]
    return "hypertension" if prefix == "cardiovascular" else prefix


def build_module_query(payload, module):
    """Return ``(query, audit)`` for a requested module using documented data only.

    Original quotation strings are retained. Whitespace normalization is used
    solely as a deduplication key, never to rewrite a quote or its negation,
    timing or subject. False and zero values are included. An absent documented
    field yields a generic module query and an explicit audit marker; the helper
    does not fall back to unverified note text or infer normality.
    """
    if module not in MODULES or module not in payload["modules"]:
        raise ValueError("Query module must be a requested assessment module")
    if payload.get("licence_context", "commercial") != "commercial":
        raise ValueError("This experimental query policy requires commercial context")
    facts = {}
    for name, fact in payload["verified_patient_facts"].items():
        if _field_module(name) != module:
            continue
        if not isinstance(fact, Mapping):
            raise ValueError("Verified patient facts must be field records")
        if fact.get("status", "present") != "present" or fact.get("value") is None:
            continue
        facts[name] = fact
    field_names = sorted(facts)
    quotes, seen = [], set()
    for name in field_names:
        raw_quotes = facts[name].get("patient_quotes", [])
        if not isinstance(raw_quotes, list) or any(not isinstance(q, str) for q in raw_quotes):
            raise ValueError("Patient quotations must be a list of original strings")
        for quote in raw_quotes:
            key = re.sub(r"\s+", " ", quote).strip()
            if key and key not in seen:
                seen.add(key)
                quotes.append(quote)
    context = f"{module} commercial driving medical fitness standard"
    fields = [
        re.sub(r"[._]+", " ", name)
        + " = "
        + json.dumps(facts[name]["value"], ensure_ascii=False, allow_nan=False)
        for name in field_names
    ]
    query = " | ".join([context, *fields, *quotes])
    return query, {
        "policy": QUERY_POLICY,
        "module": module,
        "licence_context": "commercial",
        "field_names": field_names,
        "field_values": {name: facts[name]["value"] for name in field_names},
        "patient_quotes": quotes,
        "no_documented_facts": not field_names,
        "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
        "query_utf8_bytes": len(query.encode("utf-8")),
    }
