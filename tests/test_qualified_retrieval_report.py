import hashlib
import json

import pytest

from occupational_fitness_rag.provenance import digest, write_json
from tools import qualify_retrieval_report as qualifier


def freeze(path):
    write_json(
        path / "artifacts.json",
        {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in path.iterdir() if p.is_file()},
    )


def fixtures(tmp_path):
    base = tmp_path / "outputs/experiments"
    parent, audit, reviewed, output = [
        base / name for name in ("parent", "audit", "reviewed", "qualified")
    ]
    for folder in (parent, audit, reviewed):
        folder.mkdir(parents=True)
    units = [
        {
            "source_id": sid,
            "evidence_text": sid,
            "text_sha256": hashlib.sha256(sid.encode()).hexdigest(),
        }
        for sid in ("keep", "exclude")
    ]
    write_json(parent / "corpus.json", {"units": units})
    write_json(parent / "summary.json", {"main_metrics": [{"coverage_recall_5": 0.9}]})
    write_json(
        parent / "manifest.json", {"kind": "fixture", "identity": digest({"kind": "fixture"})}
    )
    (parent / "rankings.jsonl").write_text('{"source_ids":["exclude"]}\n', encoding="utf-8")
    (parent / "index.html").write_text(
        '<html lang="en"><h1>Ten independent retrieval routes</h1><script id="report-data">unchanged</script></html>',
        encoding="utf-8",
    )
    write_json(audit / "summary.json", {"status": "scope_issue_verified"})
    write_json(reviewed / "corpus.json", {"units": units[:1]})
    for folder in (parent, audit, reviewed):
        freeze(folder)
    return parent, audit, reviewed, output


def test_qualification_preserves_rankings_metrics_and_discloses_unrun_reviewed_corpus(tmp_path):
    parent, audit, reviewed, output = fixtures(tmp_path)
    result = qualifier.build(tmp_path, parent, audit, reviewed, output)
    assert result["excluded_source_ids"] == ["exclude"]
    assert result["reviewed_corpus_rerun_complete"] is False
    assert (output / "rankings.jsonl").read_bytes() == (parent / "rankings.jsonl").read_bytes()
    assert json.loads((output / "summary.json").read_bytes())["main_metrics"] == [
        {"coverage_recall_5": 0.9}
    ]
    html = (output / "index.html").read_text(encoding="utf-8")
    assert "commercial-only textual purity" in html
    assert 'id="report-data">unchanged</script>' in html


def test_qualification_rejects_silent_rewrites_of_retained_originals(tmp_path):
    parent, audit, reviewed, output = fixtures(tmp_path)
    changed = json.loads((reviewed / "corpus.json").read_bytes())
    changed["units"][0]["evidence_text"] = "rewritten"
    write_json(reviewed / "corpus.json", changed)
    (reviewed / "artifacts.json").unlink()
    freeze(reviewed)
    with pytest.raises(ValueError, match="silently rewrite"):
        qualifier.build(tmp_path, parent, audit, reviewed, output)


def test_portable_audit_view_rebases_external_links_without_mutating_original(tmp_path):
    parent, audit, _, _ = fixtures(tmp_path)
    pdf = tmp_path / "data/knowledge/raw/guide.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"same-guideline")
    (parent / "evidence_guide.pdf").write_bytes(pdf.read_bytes())
    html = '<a href="../../../data/knowledge/raw/guide.pdf#page=214">PDF</a><a href="../parent/index.html">Report</a><a href="findings.json">Findings</a>'
    copied = qualifier.portable_audit_view(audit.resolve(), parent.resolve(), html)
    assert 'href="../evidence_guide.pdf#page=214"' in copied
    assert 'href="../index.html"' in copied
    assert 'href="findings.json"' in copied
    assert "../../../data/knowledge/raw/guide.pdf" in html
