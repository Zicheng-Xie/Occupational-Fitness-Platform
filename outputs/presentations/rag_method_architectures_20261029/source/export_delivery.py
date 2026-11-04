"""Export final diagrams and their authoring sources without copying references."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from html import escape
from pathlib import Path

TASK = Path(__file__).resolve().parents[1]


def checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(destination):
    source = TASK / "output"
    manifest = json.loads((source / "source_manifest.json").read_text(encoding="utf-8"))
    body = []
    for method in ("3", "4", "7", "9", "10"):
        diagrams = [s for s in manifest["slides"] if s["method"] == method]
        body.append(f'<section><h2>{escape(diagrams[0]["title"])}</h2><div class="pair">')
        for item in diagrams:
            name = item["name"]
            body.append(
                f'<article><h3>{escape(item["kind"])}</h3>'
                f'<a href="figures/{name}.png"><img src="figures/{name}.png" alt="{escape(item["title"] + ": " + item["kind"])}"></a>'
                f'<p><a href="figures/{name}.png">PNG, 1920 × 1080</a> · '
                f'<a href="figures/{name}.svg">Vector SVG</a></p></article>'
            )
        body.append("</div></section>")
    html = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAG architecture diagrams · Occupational Fitness Platform</title><style>
    body{font:17px/1.6 Calibri,Arial,sans-serif;margin:0;background:#fff;color:#10253f}main{max-width:1500px;margin:auto;padding:38px}header{border-bottom:2px solid #d8e1ea;padding-bottom:22px}h1{font-size:34px}h2{font-size:26px;margin-top:36px}h3{font-size:20px}a{color:#104862}img{width:100%;height:auto;border:1px solid #d8e1ea}.brand{color:#13a6a6;font-weight:bold}.pair{display:grid;grid-template-columns:1fr 1fr;gap:28px}article{min-width:0}nav a{display:inline-block;margin-right:25px}footer{border-top:1px solid #d8e1ea;margin-top:40px;padding-top:15px;color:#546a7c}@media(max-width:850px){.pair{grid-template-columns:1fr}main{padding:20px}}
    </style></head><body><main><header><div class="brand">Occupational Fitness Platform</div><h1>RAG architecture and logic diagrams</h1><p>Methods 3, 4, 7, 9 and 10. Each method has an architecture diagram and a logic-flow diagram. The preserved core and latest experimental refinement are identified separately.</p><nav><a href="rag_methods_architecture_and_logic.pptx">Editable PowerPoint · 12 slides</a><a href="rag_methods_architecture_and_logic.pdf">Vector PDF · 12 pages</a><a href="README.md">Figure guide</a><a href="source_manifest.json">Code provenance</a></nav></header>__FIGURES__<footer>English labels · Code-grounded content · Page 4 of the supplied PDF used for visual style only · Methods 9 and 10 explicitly distinguish native execution from frozen-candidate replay.</footer></main></body></html>'''
    (source / "index.html").write_text(html.replace("__FIGURES__", "".join(body)), encoding="utf-8")
    destination = destination.resolve()
    if destination == TASK or destination.is_relative_to(TASK):
        raise ValueError("Delivery must be separate from authoring files")
    files = [(source / n, n) for n in ("rag_methods_architecture_and_logic.pptx", "rag_methods_architecture_and_logic.pdf", "README.md", "source_manifest.json", "index.html")]
    for item in manifest["slides"][:10]:
        for suffix in ("png", "svg"):
            relative = "figures/" + item["name"] + "." + suffix
            files.append((source / relative, relative))
    for name in ("build_deck.mjs", "export_pdf.ps1", "export_delivery.py"):
        files.append((TASK / "source" / name, "source/" + name))
    exported = {}
    for original, relative in files:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and checksum(target) != checksum(original):
            raise ValueError("Do not overwrite an unrelated delivery: " + relative)
        if not target.exists():
            shutil.copyfile(original, target)
        assert checksum(original) == checksum(target)
        exported[relative] = checksum(target)
    (destination / "delivery_manifest.json").write_text(json.dumps({"files": exported, "file_count": len(exported), "main_figures": 10, "slides": 12, "entry": "index.html", "checked": True}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"destination": str(destination), "files": len(exported), "verified": True}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    main(parser.parse_args().destination)
