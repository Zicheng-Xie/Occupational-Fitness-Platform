from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .models import GuidelineChunk


def load_annotation_rules(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rules = data.get("annotations", [])
    if not isinstance(rules, list):
        raise ValueError("annotations must be a list")
    return rules


def _matches(chunk: GuidelineChunk, match: dict[str, str]) -> bool:
    checks = []
    if match.get("section_regex"):
        checks.append(bool(re.search(match["section_regex"], chunk.section, flags=re.I)))
    if match.get("title_regex"):
        checks.append(bool(re.search(match["title_regex"], chunk.title, flags=re.I)))
    if match.get("text_regex"):
        checks.append(bool(re.search(match["text_regex"], chunk.text, flags=re.I)))
    return bool(checks) and all(checks)


def apply_annotations(
    chunks: list[GuidelineChunk],
    rules: list[dict[str, Any]],
    default_licence_context: str,
) -> list[GuidelineChunk]:
    for chunk in chunks:
        chunk.metadata.setdefault("module", "unclassified")
        chunk.metadata.setdefault("category", "unclassified")
        chunk.metadata.setdefault("subcondition", "unclassified")
        chunk.metadata.setdefault("licence_context", default_licence_context)
        for rule in rules:
            match = rule.get("match", {}) or {}
            if _matches(chunk, match):
                for key, value in (rule.get("set", {}) or {}).items():
                    chunk.metadata[key] = value
                break
    return chunks
