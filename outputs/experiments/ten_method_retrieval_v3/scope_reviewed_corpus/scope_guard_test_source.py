"""A clipped commercial token must not admit private or broken chart regions."""

import pytest

from occupational_fitness_rag.evaluation.comparison_corpus import narrative_scope_issue


@pytest.mark.parametrize("title", ["Private", "Private - standards", "Private vehicle drivers"])
def test_private_subject_is_not_overridden_by_commercial_text_elsewhere(title):
    text = "Private threshold 6/12. A clipped Commercial footnote occurs below."
    assert "private-headed" in narrative_scope_issue(title, text)


def test_chart_answers_detect_a_caption_outside_the_extracted_column():
    text = "Commercial\nBetter eye at least 6/9\nNo\nYes\nFit to hold a con\nPrivate"
    assert "decision-chart" in narrative_scope_issue("Commercial", text)


def test_private_word_in_shared_prose_is_not_a_blanket_exclusion():
    text = "A conditional licence can be considered for private and commercial drivers."
    assert narrative_scope_issue("Therapy with shared applicability", text) is None


def test_ordinary_negative_prose_is_not_a_chart_branch():
    text = "No flexibility is provided for commercial drivers. Yes is not a separate node."
    assert narrative_scope_issue("Visual field", text) is None
