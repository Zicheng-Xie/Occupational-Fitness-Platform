"""Inventory deliverable files, check neutral naming and validate supplied source assets."""

import argparse
import json
import re
from pathlib import Path

from occupational_fitness_rag.provenance import sha256_bytes, write_json

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".venv", ".git", ".pytest_cache", ".ruff_cache", "__pycache__", "useless can delete"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--forbid", action="append", default=[])
    parser.add_argument("--original-disposition", type=Path)
    args = parser.parse_args()
    records, violations = [], []
    tokens = [re.compile(r"\b" + re.escape(word) + r"\b", re.I) for word in args.forbid]
    target = ROOT / "outputs/evaluation/repository_audit.json"
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if (
            not path.is_file()
            or set(relative.parts) & EXCLUDED
            or "indexes" in relative.parts
            or path == target
            or path.suffix == ".pyc"
        ):
            continue
        data = path.read_bytes()
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = ""
        if any(token.search(relative.as_posix()) or token.search(text) for token in tokens):
            violations.append(relative.as_posix())
        records.append({"path": relative.as_posix(), "sha256": sha256_bytes(data)})
    preserved = []
    if args.original_disposition:
        originals = json.loads(args.original_disposition.read_text(encoding="utf-8"))
        for record in originals["files"]:
            name = record.get("current_path") or ""
            if record["status"] != "preserved_original" or not name.startswith(
                (
                    "data/cases/nurse_notes/",
                    "data/cases/gold/",
                    "data/knowledge/raw/",
                )
            ):
                continue
            path = ROOT / name
            if sha256_bytes(path.read_bytes()) != record["original_sha256"]:
                raise ValueError(f"Original asset changed: {name}")
            preserved.append(name)
    write_json(
        target,
        {
            "status": "passed" if not violations else "failed",
            "files": len(records),
            "naming_violations": violations,
            "original_assets_verified": preserved,
            "scope": "UTF-8 engineering contents and paths; runtime dependencies, caches, indexes and external history excluded. Retained source assets are fingerprinted, not rewritten.",
            "inventory": records,
        },
    )
    print(
        f"Inventoried {len(records)} files; {len(violations)} naming violations; "
        f"{len(preserved)} original assets verified"
    )
    if violations:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
