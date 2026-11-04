"""Verify a frozen Blackout passage against its original PDF page and region."""

from __future__ import annotations

import json
from pathlib import Path

import pymupdf

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.provenance import digest, write_json

SOURCE_ID = "AFTD2022-EXP-05643c50d6cf5973"


def verify(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if (
        not output.is_relative_to(root / "outputs/experiments")
        or (output / "artifacts.json").exists()
    ):
        raise ValueError("Preserve any completed visual-source audit")
    corpus_path = root / "outputs/experiments/scope88_shared_retrieval_v2/corpus.json"
    corpus = json.loads(corpus_path.read_bytes())
    unit = next(u for u in corpus["units"] if u["source_id"] == SOURCE_ID)
    document = root / unit["source_path"]
    if file_hash(document) != unit["document_sha256"]:
        raise ValueError("Original guideline PDF differs from the frozen source")
    output.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(document)
    page = doc[unit["pdf_page"] - 1]
    region = page.get_text(clip=pymupdf.Rect(unit["bbox"]))

    def normalize(text):
        return " ".join(text.split())

    if normalize(unit["evidence_text"]) != normalize(region):
        raise ValueError("The frozen original text differs from its PDF region")
    restriction = "People should be advised not to drive until the mechanism is ascertained and the corresponding standard met."
    if restriction not in normalize(region):
        raise ValueError("The asserted literal restriction is absent")
    for number in (67, 68):
        doc[number - 1].get_pixmap(matrix=pymupdf.Matrix(1.4, 1.4)).save(
            str(output / f"pdf_page_{number}.png")
        )
    page.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=pymupdf.Rect(unit["bbox"])).save(
        str(output / "source_region.png")
    )
    data = {
        "kind": "original_pdf_region_verification",
        "source_id": SOURCE_ID,
        "corpus_file_sha256": file_hash(corpus_path),
        "document_sha256": file_hash(document),
        "pdf_page": unit["pdf_page"],
        "printed_page": unit["printed_page"],
        "section": unit["section"],
        "bbox": unit["bbox"],
        "licence_context": unit["licence_context"],
        "original_source_text": unit["evidence_text"],
        "pdf_region_text": region,
        "normalized_exact_region_match": True,
        "literal_restriction": restriction,
        "adjacent_section": "1.2.2 Vasovagal syncope: qualified exception; not an established diagnosis in the two frozen focus notes",
        "review_scope": "Engineering original-text/region consistency only; clinical applicability review pending",
        "clinical_review_status": "pending",
        "source_text_modified": False,
        "model_calls": 0,
        "production_change": False,
        "verifier_sha256": file_hash(__file__),
    }
    write_json(output / "checks.json", data)
    write_json(output / "manifest.json", {**data, "identity": digest(data)})
    (output / "verifier_source.py").write_bytes(Path(__file__).read_bytes())
    write_json(
        output / "artifacts.json", {p.name: file_hash(p) for p in output.iterdir() if p.is_file()}
    )
    return data


if __name__ == "__main__":
    result = verify(Path.cwd(), Path("outputs/experiments/blackout_source_visual_review_v1"))
    print(
        json.dumps(
            {k: result[k] for k in ("source_id", "pdf_page", "normalized_exact_region_match")}
        )
    )
