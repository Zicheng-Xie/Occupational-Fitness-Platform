"""Completion integrity gate for the next isolated graph construction revision."""

import json


def require_complete_chat(raw):
    """HTTP success alone cannot authorize a partial entity extraction."""
    response = json.loads(raw)
    if response.get("choices"):
        choice = response["choices"][0]
        complete = choice.get("finish_reason") == "stop"
        content = choice.get("message", {}).get("content")
    else:
        complete = response.get("done") is True and response.get("done_reason") == "stop"
        content = response.get("message", {}).get("content")
    if not complete or not isinstance(content, str) or not content.strip():
        raise ValueError("Incomplete or empty graph-model completion; partial extraction is rejected")
