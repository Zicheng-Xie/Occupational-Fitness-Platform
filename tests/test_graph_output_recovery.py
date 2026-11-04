"""Recovery diagnostics must preserve prompts and refuse context overflow."""

import json

import pytest

from occupational_fitness_rag.evaluation.graph_contract import fingerprint
from tools.check_graph_output_recovery import expanded_request


def call():
    body = {"model": "qwen", "stream": False, "messages": [{"role": "user", "content": "Exact original."}],
            "options": {"num_predict": 2048, "num_ctx": 8192, "seed": 0, "temperature": 0}}
    return {"request": body, "request_sha256": fingerprint(body),
            "raw_response": json.dumps({"done_reason": "length", "prompt_eval_count": 1200})}


def test_only_output_budget_changes_in_native_replay():
    original = call()
    expanded = expanded_request(original, 4096, 8192)
    assert expanded["messages"] == original["request"]["messages"]
    assert original["request"]["options"]["num_predict"] == 2048
    expanded["options"]["num_predict"] = 2048
    assert expanded == original["request"]


def test_no_silent_input_truncation_to_make_larger_output_fit():
    with pytest.raises(ValueError, match="context capacity"):
        expanded_request(call(), 7500, 8192)
