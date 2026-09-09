"""Build a fingerprinted, column-aware evidence catalogue from configured PDF regions."""

from __future__ import annotations

import json
from pathlib import Path

import pymupdf
import yaml

from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json
from occupational_fitness_rag.schemas.workflow import Citation


def extract_region(page, bbox) -> str:
    """Retain PDF reading order inside a single verified column/row rectangle."""
    return page.get_text("text", clip=pymupdf.Rect(bbox), sort=False).strip()


def build_catalogue(root: Path, anchors_path: Path, output: Path) -> dict:
    config = json.loads(anchors_path.read_text(encoding="utf-8"))
    pdf = root / config["source_path"]
    source_hash = sha256_bytes(pdf.read_bytes())
    if source_hash != config["document_sha256"]:
        raise ValueError("Guideline fingerprint changed; review anchors before rebuilding")
    units, seen = [], set()
    rules = yaml.safe_load(
        (root / "configs/rules/austroads_commercial_v1.yaml").read_text(encoding="utf-8")
    )["rules"]
    with pymupdf.open(pdf) as doc:
        for anchor in config["anchors"]:
            sid = anchor["source_id"]
            if sid in seen:
                raise ValueError("Duplicate source ID")
            seen.add(sid)
            page = doc[anchor["pdf_page"] - 1]
            rect = pymupdf.Rect(anchor["bbox"])
            if not page.rect.contains(rect) or rect.is_empty:
                raise ValueError(f"Invalid source region: {sid}")
            footer = page.get_text(clip=pymupdf.Rect(0, 790, page.rect.width, page.rect.height))
            if str(anchor["printed_page"]) not in footer.split():
                raise ValueError(f"Printed page could not be confirmed: {sid}")
            text = extract_region(page, anchor["bbox"])
            if len(text) < 30:
                raise ValueError(f"Empty/truncated source anchor: {sid}")
            unit = dict(
                anchor,
                document_id=config["document_id"],
                guideline_version=config["document_id"],
                document_sha256=source_hash,
                source_path=config["source_path"],
                licence_context="commercial",
                evidence_text=text,
                text_sha256=sha256_bytes(text.encode("utf-8")),
            )
            linked = [rule for rule in rules if sid in rule["source_ids"]]
            if not linked:
                raise ValueError(f"Knowledge unit is not owned by any rule: {sid}")
            kinds = {
                "unconditional"
                if "UNCONDITIONAL" in r["rule_id"]
                else "conditional"
                if "CONDITIONAL" in r["rule_id"]
                else "general"
                for r in linked
            }
            condition = sorted({r.get("module", r["subcondition"]) for r in linked})
            row_label = anchor["table_row"].lower()
            criterion = (
                "unconditional"
                if "unconditional" in row_label
                else "conditional"
                if "conditional" in row_label
                else next(iter(kinds))
                if len(kinds) == 1
                else "mixed"
            )
            unit.update(
                condition=condition[0] if len(condition) == 1 else "/".join(condition),
                standard="commercial",
                criterion_type=criterion,
                source_text=text,
                bounding_box=anchor["bbox"],
                cross_references=sorted(
                    {other for r in linked for other in r["source_ids"] if other != sid}
                ),
            )
            unit["chunk_id"] = "AFTD-" + digest(unit)[:20]
            # Also validates that no unsupported citation fields escape the builder.
            Citation(**unit, retrieval_score=1.0, score_type="exact_source_id_match")
            units.append(unit)
    data = {
        "schema_version": "1.2.0",
        "document_sha256": source_hash,
        "anchors_sha256": digest(config),
        "ruleset_sha256": digest(
            yaml.safe_load(
                (root / "configs/rules/austroads_commercial_v1.yaml").read_text(encoding="utf-8")
            )
        ),
        "units": units,
    }
    data["index_sha256"] = digest(data)
    write_json(output, data)
    return data


class SourceCatalogue:
    def __init__(self, root: Path, path: Path):
        self.root = root
        data = json.loads(path.read_text(encoding="utf-8"))
        self.index_sha256 = data.pop("index_sha256")
        if digest(data) != self.index_sha256:
            raise ValueError("Evidence index fingerprint mismatch")
        self.anchors_sha256 = data["anchors_sha256"]
        self.ruleset_sha256 = data["ruleset_sha256"]
        self.units = {unit["source_id"]: unit for unit in data["units"]}
        if len(self.units) != len(data["units"]):
            raise ValueError("Duplicate source IDs in catalogue")
        self.verify()

    def verify(self):
        documents = {}
        try:
            for unit in self.units.values():
                if any(sid not in self.units for sid in unit["cross_references"]):
                    raise ValueError("Knowledge unit has unresolved cross references")
                path = (self.root / unit["source_path"]).resolve()
                if not path.is_relative_to(self.root.resolve()):
                    raise ValueError("Source path leaves project root")
                if path not in documents:
                    if sha256_bytes(path.read_bytes()) != unit["document_sha256"]:
                        raise ValueError("Guideline PDF fingerprint mismatch")
                    documents[path] = pymupdf.open(path)
                actual = extract_region(documents[path][unit["pdf_page"] - 1], unit["bbox"])
                if (
                    actual != unit["evidence_text"]
                    or sha256_bytes(actual.encode("utf-8")) != unit["text_sha256"]
                ):
                    raise ValueError(f"Citation does not match PDF: {unit['source_id']}")
                Citation(**unit, retrieval_score=1.0, score_type="exact_source_id_match")
        finally:
            for doc in documents.values():
                doc.close()

    def citation(
        self, source_id: str, score=1.0, score_type="exact_source_id_match"
    ) -> Citation | None:
        unit = self.units.get(source_id)
        return Citation(**unit, retrieval_score=score, score_type=score_type) if unit else None
