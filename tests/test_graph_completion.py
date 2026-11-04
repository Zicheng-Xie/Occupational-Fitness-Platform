"""Reject length-stopped or empty HTTP-200 model outputs before indexing."""

import json

import pytest

from occupational_fitness_rag.evaluation.graph_completion import require_complete_chat


def test_native_complete_output_is_accepted():
    require_complete_chat(json.dumps({"done": True, "done_reason": "stop", "message": {"content": "Complete extraction."}}))


def test_native_length_stop_is_rejected_even_when_content_exists():
    with pytest.raises(ValueError, match="partial extraction"):
        require_complete_chat(json.dumps({"done": True, "done_reason": "length", "message": {"content": "Partial extraction"}}))


def test_openai_compatible_empty_stop_is_rejected():
    with pytest.raises(ValueError, match="empty"):
        require_complete_chat(json.dumps({"choices": [{"finish_reason": "stop", "message": {"content": ""}}]}))
