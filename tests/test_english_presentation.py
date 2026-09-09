"""English presentation and generated-commentary regression checks."""

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from occupational_fitness_rag.llm import LocalNarrative
from occupational_fitness_rag.pipeline.workflow import OccupationalFitnessWorkflow
from occupational_fitness_rag.reporting.builder import render_reports
from occupational_fitness_rag.reporting.presentation import render_library

ROOT = Path(__file__).resolve().parents[1]


def test_report_and_library_use_english():
    workflow = OccupationalFitnessWorkflow(ROOT / "configs/workflow.offline.yaml")
    case, result, evidence, note = workflow.from_text("No diabetes.", "LANGUAGE-TEST")
    reports = render_reports(case, result, evidence, note, ROOT, ROOT / "outputs")
    library = render_library(
        [
            {
                "case_id": case.case_id,
                "relative": "example",
                "assessment_outcome": result.assessment_outcome,
                "missing_count": 1,
            }
        ]
    )
    for content in [*reports.values(), library, note.summary]:
        assert not re.search(r"[\u3400-\u9fff]", content)
    assert '<html lang="en">' in reports["draft_report.html"]
    assert '<html lang="en">' in library
    assert "Search case ID or outcome" in library
    assert "Clinical review pending" in reports["draft_report.html"]


def test_commentary_rejects_chinese_output():
    with pytest.raises(ValidationError, match="English"):
        LocalNarrative(commentary="\u9700\u8981\u590d\u6838")
    assert LocalNarrative(commentary="Clinical review is required.").commentary
