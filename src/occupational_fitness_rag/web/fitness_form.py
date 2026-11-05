"""Populate the supplied Austroads commercial-driver report."""

import json
from pathlib import Path

import pymupdf

from occupational_fitness_rag.provenance import sha256_bytes, write_json

OUTCOME_FIELDS = {
    "meets_unconditional_standard": "Check Box8",
    "may_meet_conditional_standard": "Check Box9",
    "temporarily_unfit": "Check Box10",
    "does_not_meet_standard": "Check Box14",
}

OPINION_OUTCOMES = {
    "unconditional": "meets_unconditional_standard",
    "conditional": "may_meet_conditional_standard",
    "temporary": "temporarily_unfit",
    "permanent": "does_not_meet_standard",
}

TEXT_FIELDS = {
    "surname": "Surname",
    "given_names": "Given names",
    "address": "Address",
    "date_of_birth": "Date of birth",
    "phone": "Phone",
    "licence_number": "Driver licence number",
    "licence_state": "State of issue",
    "employer": "Employer",
    "employer_contact": "Contact name",
    "employer_address": "Address_2",
    "employer_phone": "Phone_2",
    "employer_email": "Contact email",
    "driving_duties": (
        "Nature of driving duties type of vehicle hours and distances of driving purpose of driving"
    ),
    "practitioner_surname": "Surname_2",
    "practitioner_given_names": "Given names_2",
    "practice_address": "Practice address",
    "practitioner_phone": "Phone_3",
    "facsimile": "Facsimile",
    "assessment_date": "Date of assessment",
    "other_comments": "Text4",
    "management_details": (
        "I recommend andor have actioned the following Local doctor referral Specialist referral "
        "Drug test Practical driver test Other please describe"
    ),
}


def create_completed_form(
    template: Path, output: Path, data: dict, outcome: str, judgment: dict | None = None
) -> None:
    """Write an editable completed copy and include it in the verified run bundle."""
    selected_outcome = OPINION_OUTCOMES.get(data.get("assessment_opinion"))
    if data.get("assessment_opinion") == "system":
        selected_outcome = judgment.get("assessment_outcome") if judgment else outcome
    values = dict(data)
    if judgment:
        model_comment = (
            "AI proposal - clinician review required: " + judgment["explanation"].strip()
        )
        values["other_comments"] = "\n\n".join(
            part for part in (data.get("other_comments", "").strip(), model_comment) if part
        )
    checkbox_values = {
        "Check Box11": data.get("corrective_lenses", False),
        "Check Box12": data.get("hearing_aid", False),
        "Check Box13": data.get("other_aid", False),
        "Check Box15": data.get("local_doctor_referral", False),
        "Check Box16": data.get("specialist_referral", False),
        "Check Box17": data.get("drug_test", False),
        "Check Box18": data.get("practical_driver_test", False),
        "Check Box19": data.get("other_management", False),
        "Check Box20": data.get("review_plan") == "schedule",
        "Check Box21": data.get("review_plan") == "frequent",
    }
    interval_field = "Text2" if data.get("review_plan") == "frequent" else "Text3"
    with pymupdf.open(template) as document:
        for page in document:
            for widget in page.widgets() or ():
                source = next(
                    (key for key, field in TEXT_FIELDS.items() if field == widget.field_name), None
                )
                if source and values.get(source):
                    widget.field_value = str(values[source])
                    if widget.field_name == "Text4":
                        widget.text_fontsize = 8
                elif widget.field_name == "Check Box70":
                    widget.field_value = bool(data.get("history_known"))
                elif widget.field_name == "Check Box71":
                    widget.field_value = not bool(data.get("history_known"))
                elif widget.field_name == "Check Box72":
                    widget.field_value = bool(data.get("licence_sighted"))
                elif widget.field_name == "Check Box73":
                    widget.field_value = not bool(data.get("licence_sighted"))
                elif widget.field_name == "An interim report pending further investigation":
                    widget.field_value = data.get("report_type") == "interim"
                elif widget.field_name == "A final report of the drivers fitness to drive status":
                    widget.field_value = data.get("report_type") == "final"
                elif widget.field_name == OUTCOME_FIELDS.get(selected_outcome):
                    widget.field_value = True
                elif widget.field_name in checkbox_values:
                    widget.field_value = bool(checkbox_values[widget.field_name])
                elif widget.field_name == interval_field and data.get("review_interval"):
                    widget.field_value = data["review_interval"].split()[0]
                widget.update()
        document.save(output, garbage=4, deflate=True)


def add_completed_form_to_run(
    root: Path,
    run: Path,
    data: dict,
    outcome: str,
    filename="completed_fitness_to_drive_report.pdf",
) -> str:
    judgment_path = run / "llm_judgment.json"
    judgment = (
        json.loads(judgment_path.read_text(encoding="utf-8")) if judgment_path.is_file() else None
    )
    data_name = "fitness_to_drive_form.json"
    write_json(run / data_name, {**data, "local_model_judgment": judgment})
    create_completed_form(
        root / "AFTD2022_Fitness_to_Drive_Report-December-2022.pdf",
        run / filename,
        data,
        outcome,
        judgment,
    )
    manifest_path = run / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][data_name] = sha256_bytes((run / data_name).read_bytes())
    manifest["files"][filename] = sha256_bytes((run / filename).read_bytes())
    write_json(manifest_path, manifest)
    return filename
