"""Exact duplicates reduce review work without hiding source or reference bias."""

import importlib.util
import json
from copy import deepcopy
from pathlib import Path


def review_tool():
    spec = importlib.util.spec_from_file_location(
        "support_packets",
        Path(__file__).resolve().parents[1] / "tools/build_support_review_packets.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_exact_deduplication_keeps_occurrences_and_excludes_reference_labels():
    tool = review_tool()
    row = {
        "case_id": "SYNTHETIC",
        "model": "model-a",
        "protocol": "passage_selection",
        "evidence_policy": "module_query",
        "repeat": 0,
        "reference_outcome": "DO_NOT_DISCLOSE_REFERENCE_SENTINEL",
        "input_snapshot": {"verified_patient_facts": {"indicator": {"value": False}}},
        "stages": {
            "aggregation": {
                "attempts": [
                    {
                        "number": 1,
                        "criterion_locations": [
                            {
                                "source_id": "source-a",
                                "pdf_page": 7,
                                "spans": [{"original_quote": "Synthetic original criterion."}],
                                "check": {
                                    "finding": "information_missing",
                                    "conclusion": "A prerequisite remains unknown.",
                                },
                            }
                        ],
                    }
                ]
            }
        },
    }
    repeated = deepcopy(row)
    repeated["repeat"] = 1
    packets = tool.collect_packets([row, repeated])
    assert len(packets) == 1 and len(packets[0]["occurrences"]) == 2
    assert "DO_NOT_DISCLOSE_REFERENCE_SENTINEL" not in json.dumps(packets)
    assert packets[0]["verified_patient_facts"]["indicator"]["value"] is False
    repeated["stages"]["aggregation"]["attempts"][0]["criterion_locations"][0]["check"][
        "conclusion"
    ] += " Different claim."
    assert len(tool.collect_packets([row, repeated])) == 2
    repeated = deepcopy(row)
    repeated["input_snapshot"]["verified_patient_facts"]["indicator"]["value"] = True
    assert len(tool.collect_packets([row, repeated])) == 2
