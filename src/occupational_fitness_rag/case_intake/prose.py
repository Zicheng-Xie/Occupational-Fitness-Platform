"""Bounded clinical paraphrases, with exact source spans and contextual abstention.

These patterns recognize explicit documentation, not diagnoses inferred from
symptoms. Ambiguous descriptions remain available to symptom retrieval.
"""

import re


def extract_supported_prose(collector):
    text = collector.text

    def record(field, pattern, value):
        for match in re.finditer(pattern, text, re.I):
            start, end = match.span()
            # Retain the whole clause so source review sees qualifiers and subject.
            boundaries = [0, *[m.end() for m in re.finditer(r"[.!?;]\s+|\n+", text)]]
            left = max(p for p in boundaries if p <= start)
            right = next((p for p in boundaries if p >= end), len(text))
            context = text[left:right]
            before = text[left:start]
            if re.search(r"\b(?:family history|mother|father|sister|brother)\b", before, re.I):
                continue
            if re.search(
                r"\b(?:no|not|denies|possible|suspected|hypothetical|if)\s+(?:a |any )?$",
                before,
                re.I,
            ):
                continue
            if re.search(
                r"\b(?:unconfirmed|unverified|unsigned|unreliable|undated|recalls|remembers)\b"
                r"|\b(?:old|earlier|previous) (?:letter|list|record|note|form)\b"
                r"|\b(?:last year|not confirmed|not established|cannot confirm)\b",
                context,
                re.I,
            ):
                continue
            if field == "diabetes.treatment_category" and re.search(
                r"not available for verification|awaiting verification|cannot be verified",
                context,
                re.I,
            ):
                continue
            # Reject uncertainty close to the assertion, including long noun phrases.
            if re.search(
                r"\b(?:possible|suspected|hypothetical|if)\b[^,;.!?]{0,65}$", before, re.I
            ):
                continue
            collector.add(
                field, value(match) if callable(value) else value, (left, right), "prose_explicit"
            )

    record(
        "diabetes.present",
        r"\b(?:the driver|the patient|he|she) (?:has|reports|has been diagnosed with) "
        r"(?:a diagnosis of |established |confirmed )?(?:type [12] )?diabetes\b",
        True,
    )
    record("diabetes.present", r"\b(?:confirmed|established) (?:type [12] )?diabetes\b", True)
    record(
        "diabetes.treatment_category",
        r"\bdiabetes (?:is )?(?:managed|treated) with (?:oral (?:medication|tablets)|tablets)\b",
        "glucose_lowering_agent_non_insulin",
    )
    record(
        "diabetes.treatment_category",
        r"\b(?:the driver|the patient|he|she) (?:now |currently )?(?:uses|injects|takes) insulin\b"
        r"|\bdiabetes (?:is )?(?:managed|treated) (?:with|using) insulin\b",
        "insulin",
    )
    record(
        "diabetes.gestational",
        r"\b(?:diabetes is not gestational|non-gestational diabetes)\b",
        False,
    )
    record(
        "diabetes.acutely_unwell",
        r"\b(?:the driver|the patient|he|she) "
        r"(?:[^.;\n]{0,100}\band )?is acutely unwell\b",
        True,
    )
    record(
        "diabetes.metabolically_unstable",
        r"\b(?:metabolically unstable diabetes|diabetes is metabolically unstable)\b",
        True,
    )

    record(
        "blackout.occurred",
        r"\b(?:the driver|the patient|he|she) (?:experienced|had) "
        r"(?:a witnessed |a |an episode of )?(?:blackout|transient loss of consciousness)\b",
        True,
    )
    record(
        "blackout.mechanism_status",
        r"\b(?:the )?(?:cause|mechanism) (?:is|remains) under investigation\b",
        "under_investigation",
    )

    for name, group in (("persistent_systolic", 1), ("persistent_diastolic", 2)):
        record(
            "cardiovascular.blood_pressure." + name,
            r"\b(?:current )?persistent blood pressure (?:is|was|of|remains|measures) "
            r"(\d{2,3})\s*/\s*(\d{2,3})\s*mmHg",
            lambda m, i=group: int(m[i]),
        )

    record(
        "hearing.clinical_assessment",
        r"\b(?:clinical assessment|hearing screening) "
        r"(?:suggests|indicates|documents) (?:possible |bilateral )?hearing (?:loss|impairment)\b",
        "possible_hearing_loss",
    )
    record(
        "hearing.clinical_assessment",
        r"\b(?:he|she|the driver) (?:also )?reports "
        r"difficulty (?:hearing|understanding (?:dispatch|spoken|radio))\b",
        "possible_hearing_loss",
    )
    record(
        "hearing.audiometry.available",
        r"\b(?:no (?:complete |formal )?(?:audiogram|audiometry) "
        r"(?:is available|has been performed)|audiometry has not been performed)\b",
        False,
    )
    record(
        "hearing.audiometry.available",
        r"\b(?:formal |unaided )?audiometry (?:was|has been) completed\b",
        True,
    )
    record(
        "hearing.unaided_better_ear_average_db",
        r"\b(?:mean unaided threshold|unaided hearing loss) "
        r"in the better ear (?:is|was|averages) (\d+(?:\.\d+)?)\s*dB",
        lambda m: float(m[1]),
    )
    record(
        "hearing.average_frequencies_khz",
        r"\b(?:averaged (?:over|at)|frequencies(?: of)?) "
        r"500,?\s*1000,?\s*2000\s*(?:and|,)\s*3000\s*Hz",
        [0.5, 1, 2, 3],
    )

    for eye, group in (("right", 1), ("left", 2)):
        record(
            f"vision.uncorrected.{eye}.snellen",
            r"\buncorrected (?:visual )?acuity "
            r"(?:is|was|measures) (\d+/\d+) (?:in the )?right eye and (\d+/\d+) (?:in the )?left eye",
            lambda m, i=group: m[i],
        )
    record(
        "vision.visual_field.confirmed_defect",
        r"\b(?:the optometrist|the ophthalmologist) "
        r"(?:confirms|confirmed|documents) (?:a |bilateral )?visual field defect\b",
        True,
    )
    record(
        "vision.diplopia.present",
        r"\b(?:the specialist|the ophthalmologist) "
        r"(?:confirms|confirmed|documents) (?:non-physiological )?diplopia\b",
        True,
    )
    record("vision.diplopia.physiological", r"\bnon-physiological diplopia\b", False)
    record(
        "vision.diplopia.within_20_degrees",
        r"\bdiplopia (?:occurs|is present) "
        r"within (?:the central )?20 degrees(?: of central fixation)?\b",
        True,
    )
