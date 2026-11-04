"""Do not publish partial observations as a completed comparison."""

import pytest

from tools.report_case_allocation_completion import render


def test_incomplete_model_inventory_cannot_be_published_as_complete():
    with pytest.raises(ValueError, match="990 actual"):
        render({"complete": False, "recorded_actual_calls": 989}, [], {}, {})


def test_completion_requires_independent_full_inventory_audit():
    with pytest.raises(ValueError, match="Independent completion audit"):
        render(
            {"complete": True, "recorded_actual_calls": 990},
            [],
            {"complete": False, "observed_conditions": 989},
            {},
        )


def test_a_completed_flag_cannot_hide_a_missing_evidence_arm():
    with pytest.raises(ValueError, match="five-arm inventory"):
        render(
            {
                "complete": True,
                "recorded_actual_calls": 990,
                "patient_count": 33,
                "methods": [{"recorded_calls": 99, "accepted": 99}] * 9,
                "accepted": 891,
            },
            [],
            {"complete": True, "observed_conditions": 990},
            {},
        )
