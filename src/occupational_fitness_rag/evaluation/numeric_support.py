"""Source-bound decimal relations, never clinical criteria or rule decisions."""

import re
from decimal import Decimal

from occupational_fitness_rag.evaluation.passage_judgment import passage_catalogue

NUMBER = r"(?<![\w.+-])(?P<number>[+-]?\d+(?:\.\d+)?)"
# These bindings identify quantities, not medical cutoffs or eligibility rules.
# Threshold numbers are read exclusively from the supplied original passages.
QUANTITIES = (
    ("cardiovascular.blood_pressure.persistent_systolic", "hypertension", "mmHg", NUMBER + r"\s+systolic\b"),
    ("cardiovascular.blood_pressure.persistent_diastolic", "hypertension", "mmHg", NUMBER + r"\s+diastolic\b"),
    ("hearing.unaided_better_ear_average_db", "hearing", "dB", NUMBER + r"\s*dB\b"),
    ("blackout.years_since_last_event", "blackout", "years", NUMBER + r"\s+years?\b"),
    ("diabetes.severe_hypoglycaemic_event.weeks_since_last", "diabetes", "weeks", NUMBER + r"\s+weeks?\b"),
)


def numeric_relations(payload):
    """Compare explicit scalar facts to quantity literals without applying a rule.

    A matching unit does not establish clinical applicability, treatment category,
    prerequisite satisfaction or the direction of a licensing requirement. No
    missing fact is filled and no OR/AND expression or outcome is generated.
    """
    catalogue = passage_catalogue(payload)
    facts = payload["verified_patient_facts"]
    result = []
    for field, module, unit, pattern in QUANTITIES:
        if field not in facts or facts[field]["value"] is None:
            continue
        value = facts[field]["value"]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Arithmetic support requires a numeric scalar, not a boolean or string")
        patient = Decimal(str(value))
        if not patient.is_finite():
            raise ValueError("Arithmetic support rejects a non-finite patient value")
        for anchor in catalogue.values():
            if anchor["module"] != module:
                continue
            text = anchor["original_quote"]
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                literal = match.group("number")
                original = Decimal(literal)
                relation = "equal_to" if patient == original else (
                    "less_than" if patient < original else "greater_than"
                )
                result.append({
                    "fact_field": field, "patient_value": value,
                    "source_number_literal": literal, "quantity_unit": unit,
                    "relation": relation, "exact_difference": str(patient - original),
                    "passage_id": anchor["passage_id"], "source_id": anchor["source_id"],
                    "source_text_sha256": anchor["text_sha256"],
                    "char_start": match.start(), "char_end": match.end(),
                    "original_quote": match.group(),
                    "offset_unit": "python_unicode_code_points",
                })
    return result
