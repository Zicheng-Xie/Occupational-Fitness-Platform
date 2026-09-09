from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .models import CaseIntakeResult, CategoryFacts


def _search_int(pattern: str, text: str) -> int | None:
    m = re.search(pattern, text, flags=re.I)
    return int(m.group(1)) if m else None


def _search_float(pattern: str, text: str) -> float | None:
    m = re.search(pattern, text, flags=re.I)
    return float(m.group(1)) if m else None


def _bool_from_patterns(text: str, positive: list[str], negative: list[str]) -> bool | None:
    # Explicit negation wins when both a symptom term and a denial appear in one sentence.
    for p in negative:
        if re.search(p, text, flags=re.I):
            return False
    for p in positive:
        if re.search(p, text, flags=re.I):
            return True
    return None


def _extract_demographics(text: str) -> dict[str, Any]:
    m = re.search(r"(\d{2})-year-old\s+(male|female)\s+([^\.]+)", text, flags=re.I)
    return {
        "age": int(m.group(1)) if m else None,
        "sex": m.group(2).lower() if m else None,
        "occupation": m.group(3).strip() if m else None,
    }


def _extract_vitals(text: str) -> dict[str, Any]:
    bp = re.search(r"BP\s*(\d{2,3})/(\d{2,3})\s*mmHg", text, flags=re.I)
    pulse = re.search(r"(?:pulse|HR)\s*(\d{2,3})\s*bpm", text, flags=re.I)
    return {
        "height_cm": _search_int(r"Height\s*(\d{2,3})\s*cm", text),
        "weight_kg": _search_float(r"weight\s*(\d+(?:\.\d+)?)\s*kg", text),
        "bmi": _search_float(r"BMI\s*(\d+(?:\.\d+)?)", text),
        "bp_systolic": int(bp.group(1)) if bp else None,
        "bp_diastolic": int(bp.group(2)) if bp else None,
        "pulse_bpm": int(pulse.group(1)) if pulse else None,
        "repeat_bp_available": False
        if re.search(r"No repeat BP is available", text, flags=re.I)
        else None,
    }


def _extract_cardiovascular(text: str) -> dict[str, Any]:
    chest_pain = _bool_from_patterns(
        text,
        [r"reports?\s+intermittent exertional chest pain", r"reports?[^\.]*chest pain"],
        [
            r"denies?[^\.]*chest pain",
            r"No current chest pain",
            r"No cardiac symptoms",
            r"Nil cardiac symptoms",
            r"Denies cardiac symptoms",
        ],
    )
    palpitations = _bool_from_patterns(
        text,
        [r"reports?[^\.]*palpitations"],
        [
            r"denies?[^\.]*palpitations",
            r"No current[^\.]*palpitations",
            r"No cardiac symptoms",
            r"Nil cardiac symptoms",
            r"Denies cardiac symptoms",
        ],
    )
    shortness = _bool_from_patterns(
        text,
        [r"reports?[^\.]*shortness of breath", r"reports?[^\.]*breathlessness"],
        [
            r"denies?[^\.]*(?:shortness of breath|breathlessness)",
            r"No current[^\.]*(?:shortness of breath|breathlessness)",
            r"No cardiac symptoms",
            r"Nil cardiac symptoms",
            r"Denies cardiac symptoms",
        ],
    )
    mi_history = _bool_from_patterns(
        text,
        [r"History of myocardial infarction", r"Previous myocardial infarction"],
        [r"No known myocardial infarction"],
    )
    cardiac_surgery = _bool_from_patterns(
        text,
        [r"cardiac surgery"],
        [
            r"No heart disease or cardiac surgery",
            r"No known myocardial infarction or cardiac surgery",
        ],
    )
    if cardiac_surgery is True and re.search(
        r"No (?:heart disease or |known myocardial infarction or )cardiac surgery", text, flags=re.I
    ):
        cardiac_surgery = False

    cardiac_history_present = None
    if re.search(r"No known cardiac history", text, flags=re.I):
        cardiac_history_present = False
    elif re.search(r"No heart disease", text, flags=re.I):
        cardiac_history_present = False
    elif mi_history is True:
        cardiac_history_present = True

    report_available = None
    report_type = None
    if re.search(r"recent cardiology report is available", text, flags=re.I):
        report_available = True
        report_type = "cardiology"
    elif re.search(r"No specialist report is available", text, flags=re.I):
        report_available = False
        report_type = "specialist"

    return {
        "chest_pain": chest_pain,
        "palpitations": palpitations,
        "shortness_of_breath": shortness,
        "cardiac_history_present": cardiac_history_present,
        "myocardial_infarction_history": mi_history,
        "myocardial_infarction_year": _search_int(r"myocardial infarction in\s+(\d{4})", text),
        "pci_or_coronary_stent": True
        if re.search(r"(?:PCI|angioplasty)[^\.]*stent|coronary stent", text, flags=re.I)
        else None,
        "cardiac_surgery_history": cardiac_surgery,
        "specialist_report_available": report_available,
        "specialist_report_type": report_type,
    }


def _acuity_pair(text: str, prefix: str = "") -> dict[str, str] | None:
    if prefix:
        pattern = rf"{prefix}[^\.]*?right eye\s*(6/\d+)[^\.]*?left eye\s*(6/\d+)"
    else:
        pattern = r"right eye\s*(6/\d+)[^\.]*left eye\s*(6/\d+)"
    m = re.search(pattern, text, flags=re.I)
    return {"right": m.group(1), "left": m.group(2)} if m else None


def _extract_vision(text: str) -> dict[str, Any]:
    unaided = _acuity_pair(text, "Unaided visual acuity")
    corrected = _acuity_pair(text, "corrected with glasses to")
    if corrected is None:
        m = re.search(
            r"corrected with glasses to right eye\s*(6/\d+)\s+and left eye\s*(6/\d+)",
            text,
            flags=re.I,
        )
        corrected = {"right": m.group(1), "left": m.group(2)} if m else None

    meets_standard = None
    if re.search(r"Vision:\s*Meets commercial driving standards", text, flags=re.I) or re.search(
        r"Vision meets commercial driving standards", text, flags=re.I
    ):
        meets_standard = True
    elif re.search(r"Vision:\s*WNL", text, flags=re.I):
        meets_standard = True

    correction = None
    if re.search(r"without correction|without corrective lenses", text, flags=re.I):
        correction = False
    if re.search(r"Vision:\s*WNL with glasses", text, flags=re.I) or re.search(
        r"corrected with glasses", text, flags=re.I
    ):
        correction = True

    diplopia = _bool_from_patterns(text, [r"Reports intermittent diplopia"], [r"No diplopia"])
    field_defect = True if re.search(r"visual field defect", text, flags=re.I) else None
    fields_normal = True if re.search(r"Visual fields normal", text, flags=re.I) else None
    optometrist_report_available = (
        False if re.search(r"No optometrist report is available", text, flags=re.I) else None
    )

    return {
        "meets_standard_statement": meets_standard,
        "correction_used": correction,
        "unaided_visual_acuity": unaided,
        "corrected_visual_acuity": corrected,
        "diplopia": diplopia,
        "visual_field_defect": field_defect,
        "visual_fields_normal": fields_normal,
        "optometrist_report_available": optometrist_report_available,
    }


def _extract_hearing(text: str) -> dict[str, Any]:
    normal_statement = None
    if re.search(
        r"Hearing:\s*(?:WNL|normal|Meets commercial driving standards)", text, flags=re.I
    ) or re.search(r"Audio:\s*WNL", text, flags=re.I):
        normal_statement = True

    hearing_loss = _bool_from_patterns(
        text,
        [r"Bilateral hearing loss", r"hearing loss in the left ear", r"Reports reduced hearing"],
        [r"no hearing loss"],
    )
    aids = _bool_from_patterns(
        text,
        [r"uses hearing aids", r"with hearing aids"],
        [
            r"without hearing aids",
            r"without aids",
            r"No hearing aids?\b",
            r"no hearing loss or hearing aids",
        ],
    )
    audiometry = _bool_from_patterns(
        text,
        [r"Audiometry completed"],
        [r"No audiometry or audiogram is available"],
    )
    audiologist_report_available = (
        False if re.search(r"No audiologist report is available", text, flags=re.I) else None
    )
    better_ear = _search_float(r"better ear average\s*(\d+(?:\.\d+)?)\s*dB", text)

    return {
        "normal_statement": normal_statement,
        "hearing_loss": hearing_loss,
        "hearing_aids_used": aids,
        "audiometry_completed": audiometry,
        "unaided_better_ear_average_db": better_ear,
        "audiologist_report_available": audiologist_report_available,
    }


def _extract_explicit_missing(text: str) -> list[str]:
    pairs = [
        (r"No repeat BP is available", "repeat_blood_pressure"),
        (r"No specialist report is available", "specialist_report"),
        (r"No optometrist report is available", "optometrist_report"),
        (r"No audiologist report is available", "audiologist_report"),
        (r"No audiometry or audiogram is available", "audiometry_or_audiogram"),
    ]
    return [name for pattern, name in pairs if re.search(pattern, text, flags=re.I)]


def _category_map(facts: dict[str, Any], missing: list[str]) -> list[CategoryFacts]:
    # Mapping is based only on which fact domains are present in the note.
    # It does not decide whether any standard is met.
    cv = {"vitals": facts["vitals"], "cardiovascular": facts["cardiovascular"]}
    vision = facts["vision"]
    hearing = facts["hearing"]
    return [
        CategoryFacts(
            category="cardiovascular",
            facts=cv,
            explicit_missing=[
                x for x in missing if x in {"repeat_blood_pressure", "specialist_report"}
            ],
        ),
        CategoryFacts(
            category="vision",
            facts=vision,
            explicit_missing=[x for x in missing if x == "optometrist_report"],
        ),
        CategoryFacts(
            category="hearing",
            facts=hearing,
            explicit_missing=[
                x for x in missing if x in {"audiologist_report", "audiometry_or_audiogram"}
            ],
        ),
    ]


def extract_case_text(text: str, case_id: str, source_document: str) -> CaseIntakeResult:
    clean = " ".join(text.strip().split())
    facts = {
        "demographics": _extract_demographics(clean),
        "vitals": _extract_vitals(clean),
        "cardiovascular": _extract_cardiovascular(clean),
        "vision": _extract_vision(clean),
        "hearing": _extract_hearing(clean),
    }
    missing = _extract_explicit_missing(clean)
    return CaseIntakeResult(
        case_id=case_id,
        source_document=source_document,
        structured_facts=facts,
        explicit_missing=missing,
        category_map=_category_map(facts, missing),
        notes=[
            "Fixture parser for the supplied SYN-M2 notes; production extraction remains an upstream component.",
            "Category mapping is non-diagnostic and does not determine fitness or RAG routing.",
        ],
    )


def extract_case_file(path: str | Path) -> CaseIntakeResult:
    path = Path(path)
    m = re.search(r"SYN-M2-(\d{3})", path.name, flags=re.I)
    case_id = f"SYN-M2-{m.group(1)}" if m else path.stem
    return extract_case_text(
        path.read_text(encoding="utf-8"), case_id=case_id, source_document=path.name
    )
