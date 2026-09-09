"""Conservative extraction with exact source spans and three-state fact handling.

Free prose coverage is deliberately bounded. Canonical ``field = JSON`` addenda
allow reviewers to supply every rule field explicitly without inventing facts.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import pymupdf

from occupational_fitness_rag.provenance import sha256_bytes
from occupational_fitness_rag.schemas.workflow import ClinicalCase, Fact, TextSpan


def collect_field_specs(rules: list[dict]) -> dict[str, dict]:
    specs: dict[str, dict] = {}

    def visit(node):
        if not node:
            return
        if "field" in node:
            op, value = node["operator"], node["value"]
            kind = (
                "snellen"
                if "snellen" in op
                else "list"
                if op == "set_equals"
                else "boolean"
                if isinstance(value, bool)
                else "number"
                if isinstance(value, (int, float))
                else "string"
            )
            spec = specs.setdefault(node["field"], {"type": kind})
            if kind != spec["type"]:
                raise ValueError(f"Conflicting types for {node['field']}")
            if "unit" in node:
                spec["unit"] = node["unit"]
            if kind == "string":
                spec.setdefault("allowed_values", [])
                for item in value if op == "in" else [value]:
                    if item not in spec["allowed_values"]:
                        spec["allowed_values"].append(item)
        for key in ("all", "any"):
            for child in node.get(key, []):
                visit(child)

    for rule in rules:
        visit(rule.get("gate"))
        visit(rule["condition"])
    extras = {
        "cardiovascular.blood_pressure.observed_systolic": {"type": "number", "unit": "mmHg"},
        "cardiovascular.blood_pressure.observed_diastolic": {"type": "number", "unit": "mmHg"},
        "cardiovascular.blood_pressure.repeat_available": {"type": "boolean"},
        "cardiovascular.myocardial_infarction_history": {"type": "boolean"},
        "cardiovascular.chest_pain": {"type": "boolean"},
        "cardiovascular.shortness_of_breath": {"type": "boolean"},
        "cardiovascular.specialist_report_available": {"type": "boolean"},
        "vision.normal_statement": {"type": "boolean"},
        "vision.visual_field.reported_defect": {"type": "boolean"},
        "hearing.hearing_aid_used": {"type": "boolean"},
    }
    specs.update(extras)
    # Keep both measured eyes as provenance parents even when a rule only reads
    # the derived better-eye value (corrected acuity in the supplied case 002).
    for correction in ("uncorrected", "corrected"):
        for eye in ("right.snellen", "left.snellen", "better_eye"):
            specs.setdefault(f"vision.{correction}.{eye}", {"type": "snellen"})
    specs["hearing.average_frequencies_khz"]["unit"] = "kHz"
    specs["blackout.diagnosis"]["allowed_values"] += ["undetermined"]
    specs["blackout.mechanism_status"]["allowed_values"] += ["diagnosed"]
    specs["diabetes.treatment_category"]["allowed_values"] += ["none", "other"]
    return specs


def valid_value(name: str, value: Any, specs: dict[str, dict]) -> bool:
    spec = specs.get(name)
    if not spec:
        return False
    kind = spec["type"]
    if kind == "boolean":
        return type(value) is bool
    if kind == "number":
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            return False
        if "systolic" in name:
            return 40 <= value <= 300
        if "diastolic" in name:
            return 20 <= value <= 200
        if "average_db" in name:
            return value <= 140
        if "degrees" in name:
            return value <= 360
        if "count" in name:
            return float(value).is_integer() and value >= 1
        return True
    if kind == "snellen":
        return isinstance(value, str) and bool(
            re.fullmatch(r"[1-9]\d*(?:\.\d+)?/[1-9]\d*(?:\.\d+)?", value)
        )
    if kind == "list":
        return (
            isinstance(value, list)
            and len(value) > 0
            and all(type(x) in (int, float) and math.isfinite(x) and x > 0 for x in value)
            and len(value) == len(set(value))
        )
    return isinstance(value, str) and value in spec.get("allowed_values", [value])


def snellen_ratio(value: str) -> float:
    numerator, denominator = value.split("/")
    return float(numerator) / float(denominator)


class FactCollector:
    def __init__(self, text: str, specs: dict[str, dict], page_ranges=()):
        self.text, self.specs, self.page_ranges = text, specs, page_ranges
        self.facts: dict[str, Fact] = {}
        self.warnings: list[str] = []

    def add(self, name, value, match, method="regex"):
        start, end = match.span() if hasattr(match, "span") else match
        span = TextSpan(
            start=start,
            end=end,
            quote=self.text[start:end],
            line_start=self.text.count("\n", 0, start) + 1,
            line_end=self.text.count("\n", 0, end - 1) + 1,
            pdf_page=next((page for a, b, page in self.page_ranges if a <= start < b), None),
        )
        if not valid_value(name, value, self.specs):
            self.facts[name] = Fact(status="requires_confirmation", evidence=[span], method=method)
            self.warnings.append(f"INVALID_VALUE:{name}")
            return
        previous = self.facts.get(name)
        evidence = [*(previous.evidence if previous else []), span]
        if previous and (
            previous.status != "present"
            or type(previous.value) is not type(value)
            or previous.value != value
        ):
            self.facts[name] = Fact(
                status="conflicting", evidence=evidence, method="conflict_detection"
            )
            self.warnings.append(f"CONFLICTING_FACT:{name}")
            return
        self.facts[name] = Fact(
            value=value,
            status="present",
            unit=self.specs[name].get("unit"),
            evidence=evidence,
            method=method,
        )

    def pattern(self, name, pattern, value):
        for match in re.finditer(pattern, self.text, re.I):
            self.add(name, value(match) if callable(value) else value, match)


def extract_traceable_text(
    text: str,
    case_id: str,
    source_document: str,
    specs: dict,
    *,
    source_bytes: bytes | None = None,
    source_kind="text",
    page_ranges=(),
    modules=None,
) -> ClinicalCase:
    c = FactCollector(text, specs, page_ranges)
    # First preserve every numeric observation; repeated/inconsistent readings are not
    # silently collapsed to one representative or persistent measurement.
    for match in re.finditer(r"\bBP\s*(\d{2,3})/(\d{2,3})\s*mmHg", text, re.I):
        c.add("cardiovascular.blood_pressure.observed_systolic", int(match[1]), match)
        c.add("cardiovascular.blood_pressure.observed_diastolic", int(match[2]), match)
    c.pattern("cardiovascular.blood_pressure.repeat_available", r"No repeat BP is available", False)
    for prefix in ("Persistent BP", "Consistent BP"):
        for match in re.finditer(prefix + r"\s*(\d{2,3})/(\d{2,3})\s*mmHg", text, re.I):
            c.add("cardiovascular.blood_pressure.persistent_systolic", int(match[1]), match)
            c.add("cardiovascular.blood_pressure.persistent_diastolic", int(match[2]), match)
    c.pattern(
        "cardiovascular.myocardial_infarction_history",
        r"(?<!no )(?:History of|Previous) myocardial infarction(?: in \d{4})?",
        True,
    )
    c.pattern(
        "cardiovascular.myocardial_infarction_history", r"No known myocardial infarction", False
    )
    c.pattern("cardiovascular.chest_pain", r"Reports?[^.;\n]*chest pain", True)
    c.pattern(
        "cardiovascular.chest_pain",
        r"(?:Denies|No current)[^.;\n]*chest pain|(?:No|Nil|Denies) cardiac symptoms",
        False,
    )
    c.pattern(
        "cardiovascular.shortness_of_breath",
        r"Reports?[^.;\n]*(?:shortness of breath|breathlessness)",
        True,
    )
    c.pattern(
        "cardiovascular.specialist_report_available",
        r"A recent cardiology report is available",
        True,
    )
    c.pattern(
        "cardiovascular.specialist_report_available", r"No specialist report is available", False
    )

    for label, prefix in [
        ("uncorrected", r"Unaided visual acuity[: ]*"),
        ("corrected", r"corrected with glasses to\s*"),
    ]:
        for match in re.finditer(
            prefix + r"right eye\s*(\d+/\d+)[, ]+(?:and )?left eye\s*(\d+/\d+)", text, re.I
        ):
            c.add(f"vision.{label}.right.snellen", match[1], match)
            c.add(f"vision.{label}.left.snellen", match[2], match)
    c.pattern(
        "vision.normal_statement",
        r"Vision[: ]+(?:WNL|meets commercial driving standards)[^.;\n]*",
        True,
    )
    c.pattern("vision.diplopia.present", r"Reports?[^.;\n]*diplopia", True)
    c.pattern("vision.diplopia.present", r"No diplopia", False)
    c.pattern(
        "vision.visual_field.confirmed_defect",
        r"Visual fields normal|No visual field defect",
        False,
    )
    c.pattern("vision.visual_field.reported_defect", r"Reports?[^.;\n]*visual field defect", True)
    c.pattern(
        "vision.specialist_assessment_available", r"No optometrist report is available", False
    )

    c.pattern(
        "hearing.clinical_assessment",
        r"(?:Hearing|Audio):\s*(?:WNL|normal|Meets commercial driving standards)[^.;\n]*|no hearing loss",
        "no_hearing_loss",
    )
    c.pattern(
        "hearing.clinical_assessment",
        r"Bilateral hearing loss|Reports?[^.;\n]*(?:reduced hearing|hearing loss)",
        "possible_hearing_loss",
    )
    c.pattern("hearing.hearing_aid_used", r"uses hearing aids|with hearing aids", True)
    c.pattern(
        "hearing.hearing_aid_used",
        r"(?:without|No) hearing aids?|no hearing loss or hearing aids",
        False,
    )
    c.pattern("hearing.audiometry.available", r"Audiometry completed", True)
    c.pattern("hearing.audiometry.available", r"No audiometry or audiogram is available", False)
    c.pattern(
        "hearing.unaided_better_ear_average_db",
        r"unaided better ear average\s*(\d+(?:\.\d+)?)\s*dB",
        lambda m: float(m[1]),
    )
    c.pattern(
        "hearing.ent_or_audiologist_information_available",
        r"No audiologist report is available",
        False,
    )
    c.pattern(
        "hearing.average_frequencies_khz",
        r"(?:averaged over|frequencies)\s*0\.5,?\s*1,?\s*2\s*(?:and|,)\s*3\s*kHz",
        [0.5, 1, 2, 3],
    )

    c.pattern(
        "blackout.occurred",
        r"No (?:history of )?blackouts?\b(?!\s+(?:history|information|details|documentation|documented|recorded|available))",
        False,
    )
    c.pattern(
        "blackout.occurred",
        r"Reports? (?:a |an |one |two |recurrent )?blackouts?\b|A blackout occurred",
        True,
    )
    c.pattern(
        "blackout.mechanism_status",
        r"Blackout mechanism (?:is )?under investigation",
        "under_investigation",
    )
    c.pattern(
        "blackout.mechanism_status",
        r"Blackout mechanism (?:is )?undetermined after investigation",
        "undetermined_after_investigation",
    )
    c.pattern(
        "diabetes.present",
        r"No (?:history of )?diabetes\b(?!\s+(?:history|information|details|documentation|documented|recorded|available))",
        False,
    )
    for match in re.finditer(r"(?:History of|Diagnosed with) (?:type [12] )?diabetes", text, re.I):
        prefix = text[max(0, match.start() - 80) : match.start()]
        if not re.search(r"\b(?:no|denies|without|negative for|family)\s+(?:a\s+)?$", prefix, re.I):
            c.add("diabetes.present", True, match)
    c.pattern(
        "diabetes.treatment_category",
        r"Diabetes (?:is )?managed (?:by|with) diet and exercise alone",
        "diet_and_exercise_only",
    )
    c.pattern("diabetes.treatment_category", r"Diabetes (?:is )?treated with insulin", "insulin")

    # Optional structured addendum. Whitelisted fields, JSON types and units are
    # defined by the exported data dictionary; invalid facts abstain explicitly.
    for match in re.finditer(r"(?m)^([a-z][a-z0-9_.]+)\s*=\s*([^\n\r]+)", text):
        name = match[1]
        if name not in specs:
            c.warnings.append(f"UNRECOGNIZED_FIELD:{name}")
            continue
        try:
            value = json.loads(match[2])
        except ValueError:
            c.warnings.append(f"INVALID_JSON_VALUE:{name}")
            c.add(name, None, match, "structured_addendum")
            continue
        if value is not None:
            c.add(name, value, match, "structured_addendum")

    for label in ("uncorrected", "corrected"):
        keys = [f"vision.{label}.{eye}.snellen" for eye in ("right", "left")]
        parents = [c.facts.get(k, Fact()) for k in keys]
        if all(p.status == "present" for p in parents):
            derived = Fact(
                value=max((p.value for p in parents), key=snellen_ratio),
                status="present",
                evidence=[s for p in parents for s in p.evidence],
                method="snellen_better_eye",
                derived_from=keys,
            )
            name = f"vision.{label}.better_eye"
            existing = c.facts.get(name)
            if existing and (existing.status != "present" or existing.value != derived.value):
                c.facts[name] = Fact(
                    status="conflicting",
                    evidence=[*existing.evidence, *derived.evidence],
                    method="derived_conflict",
                )
                c.warnings.append(f"CONFLICTING_FACT:{name}")
            else:
                c.facts[name] = derived
    for name in specs:
        c.facts.setdefault(name, Fact(unit=specs[name].get("unit")))
    options = {"modules_requested": modules} if modules else {}
    return ClinicalCase(
        case_id=case_id,
        source_document=source_document,
        source_kind=source_kind,
        source_sha256=sha256_bytes(
            source_bytes if source_bytes is not None else text.encode("utf-8")
        ),
        text_sha256=sha256_bytes(text.encode("utf-8")),
        source_text=text,
        facts=c.facts,
        warnings=sorted(set(c.warnings)),
        **options,
    )


def extract_traceable_file(path: str | Path, specs: dict, modules=None) -> ClinicalCase:
    path = Path(path)
    source = path.read_bytes()
    page_ranges = []
    if path.suffix.lower() == ".pdf":
        parts, offset = [], 0
        with pymupdf.open(path) as doc:
            for number, page in enumerate(doc, 1):
                text = page.get_text(sort=True)
                if not text.strip():
                    raise ValueError(
                        f"PDF page {number} has no extractable text; OCR and human verification are required"
                    )
                parts.append(text)
                page_ranges.append((offset, offset + len(text), number))
                offset += len(text) + 1
        text, kind = "\n".join(parts), "pdf"
    elif path.suffix.lower() in {".txt", ".md"}:
        text, kind = source.decode("utf-8-sig"), "text"
    else:
        raise ValueError("Supported report files: UTF-8 .txt/.md and text-bearing .pdf")
    return extract_traceable_text(
        text,
        path.stem,
        path.name,
        specs,
        source_bytes=source,
        source_kind=kind,
        page_ranges=page_ranges,
        modules=modules,
    )
