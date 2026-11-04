"""Freeze final automated and interactive validation of native route reports."""

import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path('E:/code/Occupational-Fitness-Platform')
OUT = ROOT / 'outputs/experiments/retrieval_extensions_validation_v1'
EXPERIMENTS = [
    'guarded_hybrid_v3', 'guarded_hybrid_retrieval_v3',
    'guarded_hybrid_v4', 'guarded_hybrid_retrieval_v4',
    'semantic_guarded_hybrid_v5', 'semantic_guarded_retrieval_v5',
    'semantic_rerank_diagnostic_v1',
    'retrieval_extensions_inputs_v1', 'retrieval_extension_protocols_v2',
    'native_flag_rerank_v1', 'native_neo4j_retrieval_v1',
    'native_pageindex_retrieval_v1', 'native_pageindex_retrieval_v2',
    'native_pageindex_retrieval_v3', 'native_pageindex_retrieval_v4',
    'docling_structure_audit_v1', 'ten_method_retrieval_v1',
    'ten_method_retrieval_v2', 'ten_method_retrieval_v3',
    'commercial_scope_audit_v1', 'scope_reviewed_corpus_v2',
    'seven_method_judgment_full_v1',
    'judgment_completion_audit_v1', 'anchored_hybrid_judgment_full_v3',
    'anchored_revision_judgment_audit_v1',
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.inline_scripts = []
        self.script = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])
        if tag == 'script' and attrs.get('type') != 'application/json' and not attrs.get('src'):
            self.script = True

    def handle_endtag(self, tag):
        if tag == 'script':
            self.script = False

    def handle_data(self, data):
        if self.script:
            self.inline_scripts.append(data)


def run():
    if (OUT / 'artifacts.json').exists():
        raise ValueError('Preserve the frozen validation bundle')
    checks, pins, count, links, scripts = {}, {}, 0, 0, 0
    for name in EXPERIMENTS:
        folder = ROOT / 'outputs/experiments' / name
        inventory = read(folder / 'artifacts.json')
        if not inventory or not all(isinstance(x, str) for x in inventory.values()):
            raise ValueError('Unexpected inventory: ' + name)
        for relative, expected in inventory.items():
            target = (folder / relative).resolve()
            if not target.is_relative_to(folder.resolve()) or sha(target) != expected:
                raise ValueError('Immutable output changed: ' + name + '/' + relative)
            count += 1
        pins[name] = sha(folder / 'artifacts.json')
        pages = [folder / 'index.html', folder / 'scope_audit/qualified_index.html']
        for page in [p for p in pages if p.is_file()]:
            parser = Links()
            parser.feed(page.read_text(encoding='utf-8'))
            for href in set(parser.links):
                parsed = urlsplit(href)
                if parsed.scheme or not parsed.path:
                    continue
                if not (page.parent / unquote(parsed.path)).resolve().exists():
                    raise ValueError('Broken local report link: ' + name + '/' + href)
                links += 1
            for script in parser.inline_scripts:
                result = subprocess.run(
                    ['E:/Node.js/node.exe', '--check', '-'], input=script,
                    capture_output=True, text=True, encoding='utf-8', check=False)
                if result.returncode:
                    raise ValueError('Invalid inline JavaScript: ' + name + result.stderr)
                scripts += 1
    for report in ('pytest.xml', 'pytest_final.xml'):
        suites = ET.parse(OUT / report).getroot()
        elements = list(suites.iter('testsuite'))
        item = {key: sum(int(s.get(key, 0)) for s in elements)
                for key in ('tests', 'failures', 'errors', 'skipped')}
        if item['failures'] or item['errors'] or not item['tests']:
            raise ValueError('Failed or empty validation suite')
        checks[report] = item
    ruff = subprocess.run(
        [str(ROOT / '.venv/Scripts/python.exe'), '-m', 'ruff', 'check', 'src', 'tests', 'tools'],
        cwd=ROOT, capture_output=True, text=True, encoding='utf-8', check=False)
    (OUT / 'ruff.txt').write_text(ruff.stdout + ruff.stderr, encoding='utf-8')
    if ruff.returncode:
        raise ValueError('Ruff failed; see saved log')
    main = read(ROOT / 'outputs/experiments/ten_method_retrieval_v3/summary.json')
    if main['main_ranking_records'] != 770 or main['method_count'] != 10:
        raise ValueError('Wrong final retrieval inventory')
    for image in ('ten_method_v1_case.png', 'ten_method_v3_qualified.png', 'ten_method_v3_metrics.png'):
        if not (OUT / image).is_file():
            raise ValueError('Missing actual browser verification image: ' + image)
    checks.update({
        'updated_utc': datetime.now(timezone.utc).isoformat(),
        'artifact_files_verified': count, 'artifact_inventory_sha256': pins,
        'local_report_links_verified': links, 'inline_javascript_syntax_checks': scripts,
        'ruff_exit_code': ruff.returncode, 'main_method_metrics': main['main_metrics'],
        'browser': {
            'local_http_only': True,
            'case_filter': 'SYN-EXT-009', 'disease_filter': 'blackout',
            'selected_method': 'planned_hybrid_v3_guarded_30',
            'visible_top5_change': '33.33% to 66.67%',
            'original_evidence_opened': 'AFTD2022-EXP-bbf242d555576d02',
            'visible_original_pdf_page': 70,
            'final_overview': 'ten_method_retrieval_v3',
            'scope_notice_verified': '94 measured; 88 separately reviewed; not reranked',
            'screenshots': ['ten_method_v1_case.png', 'ten_method_v3_qualified.png', 'ten_method_v3_metrics.png'],
        },
        'production_change': False,
        'interpretation': 'Software checks and engineering source-coverage verification, not clinical certification.',
    })
    save(OUT / 'checks.json', checks)
    (OUT / 'validator_source.py').write_bytes(Path(__file__).read_bytes())
    save(OUT / 'artifacts.json', {p.name: sha(p) for p in OUT.iterdir() if p.is_file()})
    print(json.dumps({k: checks[k] for k in (
        'pytest.xml', 'pytest_final.xml', 'artifact_files_verified',
        'local_report_links_verified', 'inline_javascript_syntax_checks', 'ruff_exit_code')}))


if __name__ == '__main__':
    run()
