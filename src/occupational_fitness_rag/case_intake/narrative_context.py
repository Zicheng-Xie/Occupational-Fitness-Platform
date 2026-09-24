"""Select bounded verbatim symptom passages for retrieval, never for rule facts.

This conservative vocabulary extends the field dictionary with common nurse-note
phrasing. Matching selects review context; it does not diagnose a condition,
resolve negation or confirm a measurement. Mixed passages may match two modules.
"""

import re

from occupational_fitness_rag.schemas.workflow import TextSpan

MODULE_TERMS = {
    "hypertension": r"blood[- ]pressure|\bbp\b|hypertens|antihypertensive|pressure tablets",
    "vision": r"vis(?:ion|ual)|\beye\b|optometr|diplopia|double|two overlapping|headlights|blur|scotoma|monocular",
    "hearing": r"hear|audiom|audiolog|\bear\b|\bdb\b|dispatch|doorbell|spoken|radio instructions",
    "blackout": r"blackout|syncope|faint|collapse|unresponsive|consciousness|(?:loss of|lost|altered|impaired) awareness|blank spell|seizure",
    "diabetes": r"diabet|insulin|glucose|glycaem|glycem|endocrin|metabolic|thirst|pass urine",
}


CONTEXT_VERSION = 2
LEGACY_BLACKOUT_TERMS = (
    r"blackout|syncope|faint|collapse|unresponsive|consciousness|awareness|blank spell|seizure"
)


def select_narrative_context(case, requests, rules, *, version=CONTEXT_VERSION):
    """Return module-scoped source spans, excluding structured addendum lines.

    Selection is deterministic and bounded to 2,000 characters per module. Entire
    sentences retain uncertainty, negation, subject and timing. Oversized single
    sentences are omitted rather than cut into misleading partial quotations.
    """
    if version not in {1, CONTEXT_VERSION}:
        raise ValueError("Unsupported narrative context version")
    selected = {}
    for module in case.modules_requested:
        spans, budget = [], 2000
        pattern = (
            LEGACY_BLACKOUT_TERMS if module == "blackout" and version == 1 else MODULE_TERMS[module]
        )
        for match in re.finditer(r"[^\n]+", case.source_text):
            if re.match(r"[a-z][a-z0-9_.]+\s*=", match[0]):
                continue
            for sentence in re.finditer(r".+?(?:[.!?](?=\s|$)|$)", match[0]):
                quote = sentence[0]
                leading = len(quote) - len(quote.lstrip())
                quote = quote.strip()
                if not quote or not re.search(pattern, quote, re.I) or len(quote) > budget:
                    continue
                start = match.start() + sentence.start() + leading
                end = start + len(quote)
                spans.append(
                    TextSpan(
                        start=start,
                        end=end,
                        quote=quote,
                        line_start=case.source_text.count("\n", 0, start) + 1,
                        line_end=case.source_text.count("\n", 0, end - 1) + 1,
                    ).model_dump(mode="json")
                )
                budget -= len(quote)
        selected[module] = spans
    return {
        request.request_id: selected[rules[request.rule_id]["module"]]
        for request in requests
        if selected[rules[request.rule_id]["module"]]
    }
