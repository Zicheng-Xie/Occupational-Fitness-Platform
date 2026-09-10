"""Check report links and current contract examples without a browser dependency."""

import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from occupational_fitness_rag.provenance import write_json
from occupational_fitness_rag.schemas.red_flag_result import WorkflowRuleResult
from occupational_fitness_rag.schemas.workflow import (
    ClinicalCase,
    ReviewNote,
    WorkflowEvidencePack,
)

ROOT = Path(__file__).resolve().parents[1]


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links = set(), []

    def handle_starttag(self, tag, attributes):
        values = dict(attributes)
        if "id" in values:
            if values["id"] in self.ids:
                raise ValueError("Duplicate HTML ID")
            self.ids.add(values["id"])
        if tag == "a" and "href" in values:
            self.links.append(values["href"])


def main():
    manifest = json.loads((ROOT / "outputs/demo_manifest.json").read_text(encoding="utf-8"))
    pages = [ROOT / "outputs/index.html"] + [
        ROOT / r["output"] / "draft_report.html" for r in manifest
    ]
    count = 0
    for page in pages:
        parser = LinkParser()
        text = page.read_text(encoding="utf-8")
        if "\ufffd" in text or "DRAFT" not in text:
            raise ValueError(f"Broken encoding or missing draft marker: {page}")
        parser.feed(text)
        for href in parser.links:
            url = urlsplit(href)
            if url.scheme or url.netloc:
                raise ValueError(f"Unexpected external report link: {href}")
            if url.path:
                target = (page.parent / unquote(url.path)).resolve()
                if not target.is_relative_to(ROOT) or not target.is_file():
                    raise ValueError(f"Broken/outside report file link: {page}: {href}")
            elif url.fragment not in parser.ids:
                raise ValueError(f"Broken report anchor: {page}: {href}")
            count += 1
    target = ROOT / "examples/contracts/syn_m2_009"
    for name, model in {
        "structured_case": ClinicalCase,
        "rule_result": WorkflowRuleResult,
        "evidence_pack": WorkflowEvidencePack,
        "gp_review_note": ReviewNote,
    }.items():
        model.model_validate_json((target / f"{name}.json").read_text(encoding="utf-8"))
    write_json(
        ROOT / "outputs/evaluation/artifact_checks.json",
        {
            "status": "passed",
            "html_documents": len(pages),
            "links_checked": count,
            "contract_examples": 4,
            "browser_visual_review": "not_performed_no_connected_browser_available",
            "scope": "Static link, internal anchor, draft marker, UTF-8 and contract validation. Does not claim pixel-level browser rendering QA.",
        },
    )
    print(f"Validated {len(pages)} HTML documents, {count} links, and 4 contract examples")


if __name__ == "__main__":
    main()
