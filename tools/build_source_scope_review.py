"""Render source-bound scope cards independently of inference and production rules.

The observations describe original-page layout and textual scope. They are AI
engineering review aids, with all human and clinical review still pending.
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from html import escape
from pathlib import Path

PDF_SHA256 = "5811cfbb29c4db2cec704033ec2ee31506e78445ed8108e72d324cbef780500c"
PRIOR_RESULTS_SHA256 = "3577e23854a46d1f3c9f6ce95942515c990d1f776fc630ec22ca2b81856d90be"
OBSERVATIONS = {
    "AFTD2022-HTN-COM-001": {
        "enclosing_scope": "Hypertension row, Commercial standards column, unconditional exclusion.",
        "preserved_conditions": "Consistently greater than 170 systolic OR greater than 100 diastolic, treated or untreated. The comparisons are strict greater-than comparisons.",
        "not_established_by_this_passage": "A raised pressure does not itself satisfy a conditional-licence pathway. An isolated observed pressure is not the same field as consistently raised pressure.",
        "adjacent_context": "A separate conditional paragraph below has cumulative therapy, four-week control, medication-effect and organ-damage requirements. Its specialist footnote distinguishes initial granting from agreed ongoing GP review.",
        "related_canonical_sources": ["AFTD2022-HTN-COM-002"],
        "review_priority": "Review claims that convert the unconditional exclusion into conditional permission without the separate prerequisites.",
    },
    "AFTD2022-VIS-COM-004": {
        "enclosing_scope": "Visual fields row, Commercial standards column, unconditional exclusion.",
        "preserved_conditions": "The exclusion is explicitly for an unconditional licence when any visual-field defect is present.",
        "not_established_by_this_passage": "This short exclusion does not establish exclusion from both unconditional and conditional pathways, nor permanent ineligibility.",
        "adjacent_context": "The next paragraph in the same commercial cell describes conditional consideration with annual review, specialist information, extent, significant-loss and stability criteria. The private column has different criteria and must remain separate.",
        "related_canonical_sources": ["AFTD2022-VIS-COM-005"],
        "review_priority": "Review the VAL-MIX-06 claim applying this unconditional-only sentence to the conditional pathway.",
    },
    "AFTD2022-DM-COM-003": {
        "enclosing_scope": "Narrative subsection 3.2.2 Acute hyperglycaemia, left page column; no private/commercial table split within this paragraph.",
        "preserved_conditions": "The no-driving advice is tied to being acutely unwell with metabolically unstable diabetes. The source also states a limitation in evidence about regular hyperglycaemia effects on driving.",
        "not_established_by_this_passage": "It does not define an arbitrary numerical glucose threshold, a fixed waiting interval, a conditional permission or a permanent licensing exclusion.",
        "adjacent_context": "The following subsection addresses comorbidities and end-organ complications. Vision, neuropathy, sleep-apnoea and cardiovascular headings in the right column are separate material.",
        "related_canonical_sources": [],
        "review_priority": "Review acute no-driving advice classified as conditional permission or used to establish permanent exclusion; distinguish the current illness advice from a licence pathway label.",
    },
    "AFTD2022-HEAR-COM-001": {
        "enclosing_scope": "Hearing loss row, Commercial standards column, initial clinical assessment and audiometry referral.",
        "preserved_conditions": "Possible hearing loss on initial clinical assessment leads to audiometry referral.",
        "not_established_by_this_passage": "It supplies no measured hearing threshold and does not itself determine a licence outcome. The private-column statement that there is no hearing standard is outside this commercial passage.",
        "adjacent_context": "The commercial quantitative exclusion follows below, then conditional and individualised assessment pathways and three footnotes.",
        "related_canonical_sources": ["AFTD2022-HEAR-COM-002", "AFTD2022-HEAR-COM-003"],
        "review_priority": "Keep qualitative suspected hearing loss separate from a completed, applicable audiometric measurement.",
    },
    "AFTD2022-HEAR-COM-002": {
        "enclosing_scope": "Hearing loss row, Commercial standards column, unconditional exclusion.",
        "preserved_conditions": "Unaided better-ear hearing loss at least 40 dB, averaged at 0.5, 1, 2 and 3 kHz. The threshold includes exactly 40.",
        "not_established_by_this_passage": "39.9 is mathematically below 40, so it does not satisfy this numerical exclusion. That comparison alone is not a complete clinical fitness determination or evidence of conditional permission. Aided hearing and a different frequency average are not interchangeable with this measure.",
        "adjacent_context": "Conditional and individualised assessment paragraphs below use ENT/audiologist information and hearing-aid considerations. The footnotes address stable conditions, assessment guidance and possible hearing-aid distraction.",
        "related_canonical_sources": ["AFTD2022-HEAR-COM-001", "AFTD2022-HEAR-COM-003"],
        "review_priority": "Review the SYN-EXT-020 numerical comparison separately from its typed conditional_permission finding and unconditional pathway.",
    },
    "AFTD2022-DM-COM-008": {
        "enclosing_scope": "Commercial standards column, conditional paragraph of the Insulin-treated diabetes (except gestational diabetes) row.",
        "preserved_conditions": "Conditional consideration depends on at least annual review, driving task and appropriate specialist information. All four listed criteria are joined cumulatively: recent-event assessment, risk-minimising regimen, awareness and end-organ effects. The recent-event wording is generally at least six weeks, as assessed by the specialist.",
        "not_established_by_this_passage": "Six elapsed weeks alone are not unconditional clearance or an automatic conditional permission. The source does not make the specialist assessment optional.",
        "adjacent_context": "Important enclosing-context gap: the row title and its except gestational diabetes qualification are in the separate condition column, outside this stored canonical bounding box and source_text. The full original page makes the qualification visible. The private column includes different review language and additional text that must not be imported into the commercial cell.",
        "related_canonical_sources": ["AFTD2022-DM-COM-009"],
        "review_priority": "Before a future corpus revision, bind the original row-title qualification to the commercial criterion without silently changing the current frozen corpus. Review SYN-EXT-014 boundary interpretation and SYN-EXT-016 gestational scope explicitly.",
    },
    "AFTD2022-DM-COM-009": {
        "enclosing_scope": "Narrative subsection 3.3.2 Recommendation and review of conditional licences for commercial vehicle drivers, left page column.",
        "preserved_conditions": "The title explicitly limits the subsection to commercial drivers. Specialist advice and periodic review are described; at least three months of glucose-monitoring records should be reviewed for commercial drivers receiving insulin treatment.",
        "not_established_by_this_passage": "The presence of records for three months is not itself evidence they have been reviewed, and this paragraph does not replace the clinical criteria in the insulin table.",
        "adjacent_context": "The private-driver subsection 3.3.1 above is separate. Later text in the right column addresses non-insulin treatment and specialist-access arrangements; those paragraphs are outside this canonical crop.",
        "related_canonical_sources": ["AFTD2022-DM-COM-008"],
        "review_priority": "Keep monitoring-record availability, specialist review and satisfaction of all table criteria as distinct documented assertions.",
    },
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def priority_claims(root):
    """Attach exact historical proposals, with reference and overall outcome withheld."""
    path = root / "outputs/experiments/applicability_comparison_bound_v2/results.jsonl"
    raw = path.read_bytes()
    if sha256(raw) != PRIOR_RESULTS_SHA256 or not raw.endswith(b"\n"):
        raise ValueError("Historical proposal snapshot changed")
    wanted = {
        ("VAL-MIX-06", "qwen3.5:4b-q4_K_M", "reference_evidence"),
        ("VAL-MIX-07", "llama3:8b", "reference_evidence"),
        ("SYN-EXT-020", "qwen3.5:4b-q4_K_M", "module_query"),
    }
    claims = []
    for line in raw.decode("utf-8").splitlines():
        row = json.loads(line)
        if (
            (row["case_id"], row["model"], row["evidence_policy"]) not in wanted
            or row["protocol"] != "applicability_first"
            or row["repeat"] != 0
            or row["status"] != "completed"
        ):
            continue
        for check in row["answer"]["criterion_checks"]:
            if check["source_id"] not in OBSERVATIONS:
                continue
            claims.append(
                {
                    **{
                        key: row[key]
                        for key in (
                            "case_id",
                            "model",
                            "evidence_policy",
                            "protocol",
                            "repeat",
                            "input_sha256",
                        )
                    },
                    "original_source_id": check["source_id"],
                    "model_proposal": check,
                    "cited_verified_facts": {
                        field: row["input_snapshot"]["verified_patient_facts"][field]
                        for field in check["fact_fields"]
                    },
                    "support_review": "pending_independent_human_review",
                    "clinical_review": "pending",
                }
            )
    return {
        "results_sha256": sha256(raw),
        "overall_outcomes_and_references_disclosed": False,
        "claims": claims,
    }


def build(root, output, pdftoppm):
    import pymupdf

    root, output = Path(root).resolve(), Path(output).resolve()
    if not output.is_relative_to(root) or output == root:
        raise ValueError("Scope review requires its own project output directory")
    program = shutil.which(pdftoppm) or str(Path(pdftoppm).resolve())
    if not Path(program).is_file():
        raise ValueError("A local pdftoppm executable is required")
    pdf = root / "data/knowledge/raw/ap_g56_22.pdf"
    raw = pdf.read_bytes()
    if sha256(raw) != PDF_SHA256:
        raise ValueError("The reviewed original PDF revision changed")
    corpus_path = root / "outputs/experiments/corpus_quality_v1/corpus.json"
    corpus_raw = corpus_path.read_bytes()
    corpus = json.loads(corpus_raw)
    units = {unit["source_id"]: unit for unit in corpus["units"]}
    document = pymupdf.open(stream=raw, filetype="pdf")
    assets = output / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    pages = sorted({units[source]["pdf_page"] for source in OBSERVATIONS})
    version = (
        subprocess.run([program, "-v"], check=True, capture_output=True)
        .stderr.decode("utf-8")
        .splitlines()[0]
    )
    for page_number in pages:
        subprocess.run(
            [
                program,
                "-f",
                str(page_number),
                "-l",
                str(page_number),
                "-r",
                "110",
                "-singlefile",
                "-png",
                str(pdf),
                str(assets / f"pdf_page_{page_number}"),
            ],
            check=True,
            capture_output=True,
        )
    cards = []
    for source_id, observation in OBSERVATIONS.items():
        unit = units[source_id]
        if (
            unit["document_sha256"] != PDF_SHA256
            or sha256(unit["evidence_text"].encode("utf-8")) != unit["text_sha256"]
        ):
            raise ValueError("A canonical text or document fingerprint changed")
        page = document[unit["pdf_page"] - 1]
        rectangle = pymupdf.Rect(unit["bbox"])
        if not page.rect.contains(rectangle):
            raise ValueError("Canonical crop extends beyond the PDF page")
        extracted = page.get_text("text", clip=rectangle)
        if (
            re.sub(r"\s+", " ", extracted).strip()
            != re.sub(r"\s+", " ", unit["evidence_text"]).strip()
        ):
            raise ValueError("Original PDF region differs from the stored criterion")
        filename = source_id.lower() + ".png"
        page.get_pixmap(matrix=pymupdf.Matrix(2.4, 2.4), clip=rectangle, alpha=False).save(
            assets / filename
        )
        cards.append(
            {
                **{
                    key: unit[key]
                    for key in (
                        "source_id",
                        "section",
                        "pdf_page",
                        "printed_page",
                        "bbox",
                        "table_row",
                        "text_sha256",
                    )
                },
                "coordinate_system": "PDF points from the top-left page origin; one-based PDF and printed page labels are separate",
                "source_text": unit["evidence_text"],
                "raw_pdf_region_text": extracted,
                "region_text_sha256": sha256(extracted.encode("utf-8")),
                "region_text_whitespace_equivalent": True,
                "canonical_crop_image": "assets/" + filename,
                "full_page_context_image": f"assets/pdf_page_{unit['pdf_page']}.png",
                "ai_engineering_scope_observation": observation,
                "human_review_status": "pending",
                "clinical_review_status": "pending",
            }
        )
    report = {
        "schema_version": "1.0.0",
        "source_document": "data/knowledge/raw/ap_g56_22.pdf",
        "source_document_sha256": PDF_SHA256,
        "corpus_file_sha256": sha256(corpus_raw),
        "corpus_sha256": corpus["corpus_sha256"],
        "builder_sha256": sha256(Path(__file__).read_bytes()),
        "rendering": {
            "full_page_engine": version,
            "full_page_dpi": 110,
            "region_engine": "PyMuPDF " + pymupdf.VersionBind,
            "region_scale": 2.4,
        },
        "ai_visual_review_record": {
            "date": "2026-10-15",
            "pdf_sha256": PDF_SHA256,
            "full_pages_inspected": pages,
            "review_kind": "AI engineering inspection of original-page headers, columns, adjacent qualifications and footnotes; not human or clinical adjudication",
        },
        "cards": cards,
        "historical_proposal_review_leads": priority_claims(root),
        "human_review_completed": 0,
        "clinical_review_status": "pending",
        "production_change": False,
        "frozen_corpus_change": False,
        "limitations": [
            "Seven selected original knowledge units, not a certification of the full 94-unit corpus.",
            "Whitespace-equivalent source extraction and valid coordinates do not prove clinical applicability or model reasoning correctness.",
            "Scope observations are AI engineering descriptions of the pinned original document; an independent human and qualified clinician must review them.",
            "The enclosing insulin-row gestational exception lies outside DM-COM-008's existing criterion crop. It is documented here, without patching a frozen experiment.",
            "No patient outcome, rule threshold, production pathway or accepted model judgment is edited. Historical model proposals are review leads, not an adjudicated error set.",
        ],
    }
    report["asset_sha256"] = {
        str(path.relative_to(output)).replace("\\", "/"): sha256(path.read_bytes())
        for path in sorted(assets.glob("*.png"))
    }
    (output / "source_scope_cards.json").write_text(json_text(report), encoding="utf-8")
    html = [
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Original source scope review | Occupational Fitness Platform</title>',
        "<style>body{font:15px/1.65 Segoe UI,Arial;color:#253447;background:#f5f7fa;margin:32px auto;padding:0 22px;max-width:1280px}article{background:white;border:1px solid #d9e2e9;border-radius:10px;margin:24px 0;padding:26px}h1,h2,h3{line-height:1.3}h2{font-size:21px}h3{font-size:15px;margin-bottom:5px}p{margin-top:6px}img{max-width:100%;height:auto;border:1px solid #d9e2e9}blockquote,pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f0f5f8;padding:16px}summary{cursor:pointer;padding:10px 0}a{color:#235f86}.status{background:#fff5dc;padding:12px;border-left:3px solid #aa7a22}.scope{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:24px}@media(max-width:850px){.scope{grid-template-columns:1fr}}</style>",
        "<h1>Original source scope review</h1><p>Seven original criterion regions across six guideline pages. Full-page context preserves headings, private/commercial columns and neighbouring qualifications.</p>",
        '<p class="status">AI engineering review aid. Independent human review: 0 completed. Clinical review pending. Existing rules, corpus and experimental results are unchanged.</p>',
        '<p><a href="source_scope_cards.json">Source identities, coordinates, exact text and review leads</a></p>',
    ]
    html.extend("<p>" + escape(item) + "</p>" for item in report["limitations"])
    for card in cards:
        html.append(
            f'<article id="{escape(card["source_id"], quote=True)}"><h2>{escape(card["source_id"])} · {escape(card["table_row"])}</h2><p>Section {escape(card["section"])} · PDF {card["pdf_page"]} · Printed page {card["printed_page"]} · Region {escape(str(card["bbox"]))}</p><div class="scope"><section>'
        )
        for key, title in [
            ("enclosing_scope", "Original scope"),
            ("preserved_conditions", "Conditions retained"),
            ("not_established_by_this_passage", "Inference boundary"),
            ("adjacent_context", "Enclosing and adjacent context"),
            ("review_priority", "Review priority"),
        ]:
            html.append(
                "<h3>"
                + title
                + "</h3><p>"
                + escape(card["ai_engineering_scope_observation"][key])
                + "</p>"
            )
        html.append(
            f'</section><section><h3>Exact original criterion crop</h3><a href="{card["canonical_crop_image"]}"><img src="{card["canonical_crop_image"]}" alt="Original PDF region for {escape(card["source_id"], quote=True)}"></a><details><summary>Original criterion text and text check</summary><blockquote>{escape(card["source_text"])}</blockquote><p>Original-region extraction matches after whitespace normalization. Source and extracted text have separate fingerprints.</p></details></section></div><details><summary>Full original page: headings, columns and qualifications</summary><a href="{card["full_page_context_image"]}"><img loading="lazy" src="{card["full_page_context_image"]}" alt="Original PDF page {card["pdf_page"]}"></a></details>'
        )
        proposals = [
            claim
            for claim in report["historical_proposal_review_leads"]["claims"]
            if claim["original_source_id"] == card["source_id"]
        ]
        if proposals:
            html.append(
                "<details><summary>Historical model claims requiring independent review</summary><pre>"
                + escape(json.dumps(proposals, ensure_ascii=False, indent=2))
                + "</pre></details>"
            )
        html.append("</article>")
    html.append("</html>")
    (output / "index.html").write_text("".join(html), encoding="utf-8")
    return {
        "cards": len(cards),
        "original_pdf_pages": len(pages),
        "assets": len(report["asset_sha256"]),
        "historical_claim_leads": len(report["historical_proposal_review_leads"]["claims"]),
        "human_review_completed": 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="outputs/experiments/source_scope_review_v1")
    parser.add_argument("--pdftoppm", default="pdftoppm")
    args = parser.parse_args()
    print(json.dumps(build(Path(__file__).resolve().parents[1], args.output, args.pdftoppm)))
