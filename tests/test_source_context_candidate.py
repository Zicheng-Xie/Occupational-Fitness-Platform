"""Enclosing context comes from exact original PDF blocks with preserved geometry."""

import hashlib

import pytest

from tools.build_source_context_candidate import ROW_TITLE, layout_text, original_block


class Page:
    def __init__(self, blocks):
        self.blocks = blocks

    def get_text(self, mode):
        assert mode == "blocks"
        return self.blocks


def test_original_row_heading_keeps_exact_text_and_extracted_geometry():
    raw = "Insulin-\ntreated \ndiabetes \n(except \ngestational \ndiabetes)\n"
    geometry = (68.03150177001953, 178.60400390625, 114.8134994506836, 251.510009765625)
    original = (*geometry, raw, 5, 0)
    segment = original_block(Page([original]), ROW_TITLE)
    assert segment["bbox"] == list(geometry)
    assert segment["raw_pdf_text"] == raw
    assert segment["layout_normalized_text"] == ROW_TITLE
    assert segment["raw_pdf_text_sha256"] == hashlib.sha256(raw.encode()).hexdigest()
    assert segment["pdf_text_block_number"] == 5
    assert layout_text("Insulin-treated diabetes") == "Insulin-treated diabetes"


@pytest.mark.parametrize("blocks", [[], [(1, 2, 3, 4, "Different title", 0, 0)]])
def test_missing_or_different_title_is_rejected(blocks):
    with pytest.raises(ValueError, match="one exact text block"):
        original_block(Page(blocks), ROW_TITLE)


def test_ambiguous_original_heading_cannot_be_bound_arbitrarily():
    block = (1, 2, 3, 4, ROW_TITLE, 0, 0)
    with pytest.raises(ValueError, match="one exact text block"):
        original_block(Page([block, block]), ROW_TITLE)
