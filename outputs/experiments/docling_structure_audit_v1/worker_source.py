"""Run a native CPU Docling structure audit without replacing the RAG corpus."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from time import perf_counter


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def save(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def normalized(text):
    return " ".join(text.split())


def tokens(text):
    return Counter(re.findall(r"[a-z0-9]+", text.casefold()))


def token_coverage(expected, observed):
    left, right = tokens(expected), tokens(observed)
    return sum((left & right).values()) / sum(left.values()) if left else None


def top_left_bbox(bbox, height):
    if not bbox or not {"l", "t", "r", "b"} <= set(bbox):
        return None
    left, top, right, bottom = [float(bbox[k]) for k in ("l", "t", "r", "b")]
    if str(bbox.get("coord_origin", "TOPLEFT")).upper() == "BOTTOMLEFT":
        top, bottom = height - top, height - bottom
    return [min(left, right), min(top, bottom), max(left, right), max(top, bottom)]


def intersects(left, right):
    return bool(
        left
        and right
        and min(left[2], right[2]) > max(left[0], right[0])
        and min(left[3], right[3]) > max(left[1], right[1])
    )


def collect_pages(native, page_map):
    """Retain all native text/table metadata; never infer clinical column ownership."""
    output = {}
    for page in page_map:
        number = page["audit_pdf_page"]
        meta = native.get("pages", {}).get(str(number), {})
        height = page["height"]
        regions, tables = [], []
        for item in native.get("texts", []):
            for prov in item.get("prov", []):
                if prov.get("page_no") == number:
                    regions.append(
                        {
                            "kind": "text",
                            "native_ref": item.get("self_ref"),
                            "text": item.get("text", ""),
                            "bbox_top_left": top_left_bbox(prov.get("bbox"), height),
                            "native_provenance": prov,
                        }
                    )
        for item in native.get("tables", []):
            relevant = [p for p in item.get("prov", []) if p.get("page_no") == number]
            if not relevant:
                continue
            tables.append(item)
            for index, cell in enumerate(item.get("data", {}).get("table_cells", [])):
                regions.append(
                    {
                        "kind": "table_cell",
                        "native_ref": item.get("self_ref"),
                        "cell_index": index,
                        "text": cell.get("text", ""),
                        "bbox_top_left": top_left_bbox(cell.get("bbox"), height),
                        "native_cell": cell,
                    }
                )
        output[page["original_pdf_page"]] = {
            **page,
            "native_page_metadata": meta,
            "regions": regions,
            "native_tables": tables,
            "native_page_present": bool(meta),
        }
    return output


def align_sources(units, pages):
    records = []
    for unit in units:
        page = pages[unit["pdf_page"]]
        all_text = "\n".join(r["text"] for r in page["regions"])
        regions = [r for r in page["regions"] if intersects(unit.get("bbox"), r["bbox_top_left"])]
        region_text = "\n".join(r["text"] for r in regions)
        literal = normalized(unit["evidence_text"]) in normalized(all_text)
        local_coverage = token_coverage(unit["evidence_text"], region_text)
        records.append(
            {
                "source_id": unit["source_id"],
                "module": unit["module"],
                "original_pdf_page": unit["pdf_page"],
                "audit_pdf_page": page["audit_pdf_page"],
                "section": unit["section"],
                "printed_page": unit["printed_page"],
                "original_bbox_top_left": unit.get("bbox"),
                "original_text_sha256": unit["text_sha256"],
                "native_page_present": page["native_page_present"],
                "literal_whitespace_normalized_page_match": literal,
                "page_token_coverage": token_coverage(unit["evidence_text"], all_text),
                "region_token_coverage": local_coverage,
                "overlapping_native_region_count": len(regions),
                "overlapping_native_table_cell_count": sum(
                    r["kind"] == "table_cell" for r in regions
                ),
                "overlapping_native_regions": regions,
                "engineering_alignment_status": "literal_page_match_requires_column_review"
                if literal
                else "high_region_token_overlap_requires_review"
                if local_coverage is not None and local_coverage >= 0.9
                else "partial_or_missing_requires_review",
                "clinical_review": "pending",
                "commercial_column_and_footnote_review": "pending",
            }
        )
    return records


def run(corpus_path, pdf_path, models_path, output):
    root = Path(__file__).resolve().parents[1]
    corpus_path, pdf_path, models_path, output = [
        Path(p).resolve() for p in (corpus_path, pdf_path, models_path, output)
    ]
    if output.exists() or not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Use a fresh separate audit directory; preserve earlier results")
    corpus = json.loads(corpus_path.read_bytes())
    units = corpus["units"]
    document_sha = file_hash(pdf_path)
    if len({u["source_id"] for u in units}) != len(units) or any(
        u["document_sha256"] != document_sha for u in units
    ):
        raise ValueError("Audit sources differ from the frozen original PDF")
    if any(
        hashlib.sha256(u["evidence_text"].encode()).hexdigest() != u["text_sha256"] for u in units
    ):
        raise ValueError("Original source text differs")
    pages = sorted({u["pdf_page"] for u in units})
    expected_models = [
        "docling-project--docling-layout-heron/config.json",
        "docling-project--docling-layout-heron/model.safetensors",
        "docling-project--docling-layout-heron/preprocessor_config.json",
        "docling-project--docling-models/model_artifacts/tableformer/accurate/tm_config.json",
        "docling-project--docling-models/model_artifacts/tableformer/accurate/tableformer_accurate.safetensors",
    ]
    models = {
        name: {
            "bytes": (models_path / name).stat().st_size,
            "sha256": file_hash(models_path / name),
        }
        for name in expected_models
    }
    versions = {
        name: importlib.metadata.version(name)
        for name in [
            "docling",
            "docling-core",
            "docling-ibm-models",
            "torch",
            "transformers",
            "PyPDF2",
        ]
    }
    if versions["docling"] != "2.142.0":
        raise ValueError("Unexpected native Docling version")
    data = {
        "kind": "native_docling_original_page_structure_audit",
        "corpus_sha256": file_hash(corpus_path),
        "original_pdf_sha256": document_sha,
        "original_units": len(units),
        "original_pdf_pages": pages,
        "model_artifacts": models,
        "packages": versions,
        "worker_sha256": file_hash(__file__),
        "python": sys.version,
        "configuration": {
            "device": "cpu",
            "num_threads": 4,
            "do_ocr": False,
            "do_table_structure": True,
            "table_mode": "accurate",
            "do_cell_matching": True,
            "document_timeout": 900,
        },
        "original_corpus_changed": False,
        "patient_reference_labels_read": False,
        "clinical_review": "pending",
    }
    manifest = {**data, "identity": digest(data), "production_change": False}
    output.mkdir(parents=True)
    save(output / "manifest.json", manifest)
    (output / "worker_source.py").write_bytes(Path(__file__).read_bytes())
    started = perf_counter()
    summary = {
        "identity": manifest["identity"],
        "status": "failed",
        "ollama_calls": 0,
        "device": "cpu",
        "native_docling_version": versions["docling"],
        "original_corpus_changed": False,
        "production_change": False,
    }
    try:
        # Page copying is only a transport optimization. Layout, tables and text
        # below are produced by native Docling, not by this PDF utility.
        from PyPDF2 import PdfReader, PdfWriter

        reader, writer, page_map = PdfReader(str(pdf_path)), PdfWriter(), []
        for number in pages:
            page = reader.pages[number - 1]
            writer.add_page(page)
            page_map.append(
                {
                    "audit_pdf_page": len(page_map) + 1,
                    "original_pdf_page": number,
                    "width": float(page.mediabox.width),
                    "height": float(page.mediabox.height),
                }
            )
        with (output / "audit_input.pdf").open("wb") as stream:
            writer.write(stream)
        save(output / "page_map.json", page_map)
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["DO_NOT_TRACK"] = "1"
        from docling.datamodel.accelerator_options import AcceleratorOptions
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        options = PdfPipelineOptions(
            artifacts_path=models_path,
            do_ocr=False,
            do_table_structure=True,
            document_timeout=900,
            accelerator_options=AcceleratorOptions(num_threads=4, device="cpu"),
        )
        options.table_structure_options.do_cell_matching = True
        converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
        )
        result = converter.convert(output / "audit_input.pdf", raises_on_error=False)
        native = result.document.export_to_dict()
        save(output / "docling_document.json", native)
        (output / "native_markdown.md").write_text(
            result.document.export_to_markdown(), encoding="utf-8"
        )
        parsed = collect_pages(native, page_map)
        (output / "pages").mkdir()
        for number, page in parsed.items():
            save(output / "pages" / f"page_{number:05}.json", page)
        alignment = align_sources(units, parsed)
        save(output / "source_alignment.json", alignment)
        status = str(result.status.value)
        parsed_count = sum(p["native_page_present"] for p in parsed.values())
        summary.update(
            status="completed"
            if status == "success" and parsed_count == len(page_map)
            else "partial_or_failed",
            native_conversion_status=status,
            native_errors=[str(e) for e in result.errors],
            original_pages=len(page_map),
            parsed_pages=parsed_count,
            original_units=len(units),
            native_tables=sum(len(p["native_tables"]) for p in parsed.values()),
            native_text_regions=sum(
                r["kind"] == "text" for p in parsed.values() for r in p["regions"]
            ),
            native_table_cells=sum(
                r["kind"] == "table_cell" for p in parsed.values() for r in p["regions"]
            ),
            literal_page_matches=sum(
                a["literal_whitespace_normalized_page_match"] for a in alignment
            ),
            mean_page_token_coverage=sum(a["page_token_coverage"] for a in alignment)
            / len(alignment),
            mean_region_token_coverage=sum(a["region_token_coverage"] for a in alignment)
            / len(alignment),
            source_column_and_footnote_review="pending",
            interpretation="Native structure and lexical alignment audit only; no changed ranking or clinical accuracy is claimed",
            audit_pdf_sha256=file_hash(output / "audit_input.pdf"),
        )
    except Exception as exc:
        summary.update(error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        summary["seconds"] = perf_counter() - started
        summary["source_and_inputs_unchanged"] = (
            file_hash(__file__) == data["worker_sha256"]
            and file_hash(corpus_path) == data["corpus_sha256"]
            and file_hash(pdf_path) == document_sha
        )
        save(output / "summary.json", summary)
        save(
            output / "artifacts.json",
            {
                str(p.relative_to(output)).replace("\\", "/"): file_hash(p)
                for p in output.rglob("*")
                if p.is_file() and p.name != "artifacts.json"
            },
        )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corpus", default="outputs/experiments/six_method_query_preparation_v2/corpus.json"
    )
    parser.add_argument("--pdf", default="data/knowledge/raw/ap_g56_22.pdf")
    parser.add_argument("--models", default=".runtime/cache/docling_models")
    parser.add_argument("--output", default="outputs/experiments/docling_structure_audit_v1")
    args = parser.parse_args()
    print(json.dumps(run(args.corpus, args.pdf, args.models, args.output), indent=2))
