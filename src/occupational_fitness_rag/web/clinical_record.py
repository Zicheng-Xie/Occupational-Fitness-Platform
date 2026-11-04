"""Read completed fields from the supplied AFTD Clinical Assessment Record."""

from pathlib import Path

import pymupdf

BASIC_FIELDS = {
    "Surname": "surname",
    "Given names": "given_names",
    "Address": "address",
    "Date of birth": "date_of_birth",
    "Phone": "phone",
    "Driver licence number": "licence_number",
    "State of issue": "licence_state",
    "Employer": "employer",
    "Address_2": "employer_address",
    "Contact name": "employer_contact",
    "Phone_2": "employer_phone",
    "Contact email": "employer_email",
    "Nature of driving duties type of vehicle hours and distances of driving purpose of driving": (
        "driving_duties"
    ),
    "Name of doctor": "practitioner_surname",
    "Date": "assessment_date",
}


def extract_clinical_record(path: Path) -> dict:
    basic = {target: "" for target in BASIC_FIELDS.values()}
    observations = []
    with pymupdf.open(path) as document:
        if len(document) != 5:
            raise ValueError("Expected the five-page AFTD Clinical Assessment Record.")
        for page_number, page in enumerate(document, 1):
            for widget in page.widgets() or ():
                value = str(widget.field_value or "").strip()
                if value in {"", "Off"}:
                    continue
                if widget.field_name in BASIC_FIELDS:
                    basic[BASIC_FIELDS[widget.field_name]] = value
                elif widget.field_type_string != "Signature":
                    observations.append(f"Page {page_number} - {widget.field_name}: {value}")
    return {
        "basic": basic,
        "clinical_text": "Completed AFTD Clinical Assessment Record:\n" + "\n".join(observations),
        "completed_fields": len(observations) + sum(bool(value) for value in basic.values()),
        "missing_basic_fields": [name for name, value in basic.items() if not value],
        "suspect_basic_fields": [
            name
            for name, value in basic.items()
            if value.strip().lower() in {"0", "1", "yes", "no"}
        ],
        "modules": ["hypertension", "vision", "hearing", "blackout", "diabetes"],
    }


def extract_note(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        with pymupdf.open(path) as document:
            parts = [page.get_text("text").strip() for page in document]
        if not all(parts):
            raise ValueError("The nurse note PDF requires OCR before upload.")
        return "\n".join(parts)
    return path.read_text(encoding="utf-8-sig").strip()
