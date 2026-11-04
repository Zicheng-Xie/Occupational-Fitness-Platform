"""Fact-availability strata must preserve false and zero as verified values."""

import pytest

from tools.audit_scope88_prefix import fact_group


def query(values):
    return {
        "query_audit": {
            "field_names": list(values),
            "field_values": values,
            "no_documented_facts": not values,
        }
    }


@pytest.mark.parametrize("value", [False, 0, "under_investigation"])
def test_verified_false_and_zero_are_not_empty_query_states(value):
    assert fact_group(query({"field": value})) == "verified_module_facts_present"


def test_genuinely_empty_module_query_is_its_own_stratum():
    assert fact_group(query({})) == "no_verified_module_facts"


def test_mismatched_or_null_verified_fields_are_rejected():
    with pytest.raises(ValueError):
        fact_group(query({"field": None}))
    q = query({"field": False})
    q["query_audit"]["no_documented_facts"] = True
    with pytest.raises(ValueError):
        fact_group(q)
