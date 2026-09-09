"""Check active product files for non-English content and HTML language metadata."""

import argparse
import json
import re
from pathlib import Path

import pymupdf

from occupational_fitness_rag.provenance import write_json

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".venv", ".git", ".pytest_cache", ".ruff_cache", "__pycache__", "indexes", "tmp"}
CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff\U00020000-\U0002fa1f]")


def inspect(root):
    issues, checked, pdfs, html_documents = [], 0, 0, 0
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if not path.is_file() or set(relative.parts) & EXCLUDED:
            continue
        if relative.as_posix() == "outputs/evaluation/english_language_check.json":
            continue
        if CJK.search(relative.as_posix()):
            issues.append({"path": relative.as_posix(), "reason": "non_english_filename"})
        if path.suffix.lower() == ".pdf":
            with pymupdf.open(path) as document:
                text = "\n".join(page.get_text() for page in document)
            pdfs += 1
        else:
            try:
                text = path.read_text(encoding="utf-8-sig")
            except (UnicodeError, OSError):
                continue
        checked += 1
        # Decode JSON escapes as well as visible text.
        if path.suffix.lower() == ".json":
            try:
                text = json.dumps(json.loads(text), ensure_ascii=False)
            except ValueError:
                issues.append({"path": relative.as_posix(), "reason": "invalid_json"})
        if CJK.search(text):
            issues.append({"path": relative.as_posix(), "reason": "non_english_text"})
        if path.suffix.lower() == ".html":
            html_documents += 1
            if not re.search(r'<html\b[^>]*\blang=["\x27]en(?:-[A-Za-z]+)?["\x27]', text):
                issues.append(
                    {"path": relative.as_posix(), "reason": "missing_english_html_language"}
                )
    return {
        "status": "passed" if not issues else "failed",
        "text_files_checked": checked,
        "pdf_documents_checked": pdfs,
        "html_documents_checked": html_documents,
        "violations": issues,
        "scope": "Active UTF-8 product files, decoded JSON, filenames and PDF text. Runtime dependencies and caches are excluded.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    report = inspect(args.root.resolve())
    write_json(args.root / "outputs/evaluation/english_language_check.json", report)
    print(json.dumps(report, indent=2))
    if report["violations"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
