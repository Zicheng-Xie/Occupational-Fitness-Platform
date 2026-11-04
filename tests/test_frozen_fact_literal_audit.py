"""Source literal evidence is verified without promoting clinical facts."""

import importlib.util
from pathlib import Path


def tool():
    spec = importlib.util.spec_from_file_location(
        "literal_audit", Path(__file__).resolve().parents[1] / "tools/audit_frozen_fact_literals.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_exact_unicode_span_type_and_conflict_detection():
    audit = tool()
    text = "Synthetic é 😀\nvision.flag = false\nhearing.count = 0\n"
    matched = audit.literals(text, "vision.flag")
    assert matched[0]["value"] is False
    span = matched[0]
    assert text[span["char_start"] : span["char_end"]] == span["quote"]
    assert span["line"] == 2
    assert not audit.identical_value(False, 0)
    changed = {"field": "vision.flag", "before": {"value": False}, "frozen": {"value": None}}
    result = audit.inspect_field(text, changed)
    assert result["status"] == "explicit_literal_revalidation_candidate"
    assert result["frozen_value"] is None
    assert (
        audit.inspect_field(text + "vision.flag = true\n", changed)["status"]
        == "conflicting_explicit_literals"
    )


def test_no_natural_language_or_missing_value_inference():
    audit = tool()
    changed = {"field": "vision.flag", "before": {"value": False}, "frozen": {"value": None}}
    for text in [
        "No visual problem was reported.",
        "vision.flag = False",
        "vision.flag = null",
        "vision.flag = NaN",
    ]:
        assert audit.inspect_field(text, changed)["status"] == "no_explicit_literal"
    assert audit.literals('vision.flag = "false"\n', "vision.flag")[0]["value"] == "false"
    assert (
        audit.inspect_field('vision.flag = "false"\n', changed)["status"]
        == "literal_differs_from_prior_extraction"
    )


def test_original_crlf_offsets_and_duplicate_same_values_are_retained():
    audit = tool()
    quote = "vision.flag = false"
    text = "Synthetic\r\n" + quote + "\r\n" + quote + "\r\n"
    start = text.index(quote)
    changed = {
        "field": "vision.flag",
        "before": {
            "value": False,
            "evidence": [{"start": start, "end": start + len(quote), "quote": quote}],
        },
        "frozen": {"value": None, "status": "requires_confirmation"},
    }
    result = audit.inspect_field(text, changed)
    assert result["prior_quoted_spans_verified"] is True
    assert result["status"] == "explicit_literal_revalidation_candidate"
    assert len(result["literal_spans"]) == 2
    assert all(
        text[span["char_start"] : span["char_end"]] == span["quote"]
        for span in result["literal_spans"]
    )
