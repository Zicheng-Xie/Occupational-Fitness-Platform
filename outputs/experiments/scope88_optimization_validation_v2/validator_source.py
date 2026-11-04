"""Verify immutable replay outputs and preserve software/browser evidence."""
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path('E:/code/Occupational-Fitness-Platform')
OUT = ROOT / 'outputs/experiments/scope88_optimization_validation_v2'
NAMES = [
    'scope_reviewed_corpus_v2', 'scope88_shared_retrieval_v1',
    'scope88_shared_retrieval_v2', 'scope88_flag_rerank_v1',
    'scope88_flag_rerank_v2', 'scope88_prefix_allocation_v6',
    'scope88_prefix_comparison_v6', 'scope88_prefix_diagnostic_v6',
    'scope88_prefix_validation_v6', 'scope88_neo4j_strategies_v2',
    'scope88_neo4j_criterion_transfer_v3', 'scope88_neo4j_validation_v3',
    'scope88_tree_coverage_v1', 'scope88_external_graph_protocol_v1',
    'scope88_external_graph_v1', 'scope88_optimization_progress_v1',
    'scope88_optimization_progress_v2', 'scope88_optimization_comparison_v1', 'scope88_optimization_comparison_v2', 'scope88_independent_audit_v1',
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


class HTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.scripts, self.in_script = [], [], False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])
        if tag == 'script' and attrs.get('type') != 'application/json' and not attrs.get('src'):
            self.in_script = True

    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_script = False

    def handle_data(self, data):
        if self.in_script:
            self.scripts.append(data)


def run():
    if (OUT / 'artifacts.json').exists():
        raise ValueError('Preserve completed validation')
    pins, count, links, scripts = {}, 0, 0, 0
    for name in NAMES:
        folder = ROOT / 'outputs/experiments' / name
        inventory = read(folder / 'artifacts.json')
        for rel, expected in inventory.items():
            target = (folder / rel).resolve()
            if not target.is_relative_to(folder.resolve()) or sha(target) != expected:
                raise ValueError('Changed frozen output: ' + name + '/' + rel)
            count += 1
        pins[name] = sha(folder / 'artifacts.json')
        page = folder / 'index.html'
        if page.exists():
            parser = HTML()
            parser.feed(page.read_text(encoding='utf-8'))
            for href in set(parser.links):
                url = urlsplit(href)
                if not url.scheme and url.path:
                    if not (page.parent / unquote(url.path)).resolve().exists():
                        raise ValueError('Broken source link: ' + name + '/' + href)
                    links += 1
            for script in parser.scripts:
                result = subprocess.run(['E:/Node.js/node.exe', '--check', '-'], input=script,
                                        text=True, encoding='utf-8', capture_output=True)
                if result.returncode:
                    raise ValueError('Invalid JS: ' + name + result.stderr)
                scripts += 1
    suite = ET.parse(OUT / 'pytest.xml').getroot()
    suites = list(suite.iter('testsuite'))
    tests = {key: sum(int(s.get(key, 0)) for s in suites)
             for key in ('tests', 'failures', 'errors', 'skipped')}
    if tests['tests'] != 881 or tests['failures'] or tests['errors']:
        raise ValueError('Unexpected full-suite result')
    if (OUT / 'ruff.txt').read_text(encoding='utf-8-sig').strip() != 'All checks passed!':
        raise ValueError('Ruff did not pass')
    summary = read(ROOT / 'outputs/experiments/scope88_optimization_comparison_v2/summary.json')
    if summary['completed_method_count'] != 10 or summary['pending_inputs']:
        raise ValueError('The complete comparison must contain all ten routes')
    quality = read(ROOT / 'outputs/experiments/scope88_optimization_comparison_v2/native_index_quality.json')
    if quality['overall_status'] != 'degraded' or quality['unrecovered_exact_index_requests'] != 1:
        raise ValueError('Preserve the actual degraded vision-index qualification')
    screenshots = ['overview.png', 'seventh_case.png', 'original_evidence.png', 'method_metrics.png']
    for name in screenshots:
        if not (OUT / name).is_file():
            raise ValueError('Missing actual browser image: ' + name)
    checks = {
        'updated_utc': datetime.now(timezone.utc).isoformat(), 'pytest': tests,
        'ruff': 'passed', 'artifact_files_verified': count,
        'artifact_inventory_sha256': pins, 'local_report_links_verified': links,
        'inline_javascript_syntax_checks': scripts,
        'browser': {
            'report': 'scope88_optimization_comparison_v2', 'local_http_only': True,
            'case': 'SYN-EXT-009', 'module': 'blackout',
            'left': 'scope88_guarded_v3', 'right': 'scope88_prefix_criterion_v6',
            'visible_module_and_packet_coverage_change': '66.67% to 100.00%',
            'original_source': 'AFTD2022-EXP-05643c50d6cf5973',
            'original_pdf_page': 68, 'section': '1.2.1',
            'second_case': 'VAL-MIX-10', 'second_packet_coverage': '0% unchanged',
            'neo4j_filter_verified': True, 'console_errors': [],
            'screenshots': screenshots, 'temporary_tab_and_server_closed': True,
        },
        'main_metrics': summary['main_metrics'], 'production_change': False,
        'native_index_quality': quality,
        'interpretation': 'Software and engineering source-coverage checks, not clinical validation.',
    }
    save(OUT / 'checks.json', checks)
    (OUT / 'validator_source.py').write_bytes(Path(__file__).read_bytes())
    save(OUT / 'artifacts.json', {p.name: sha(p) for p in OUT.iterdir()
                                if p.is_file() and p.name != 'artifacts.json'})
    print(json.dumps({k: checks[k] for k in ('pytest', 'artifact_files_verified',
                                            'local_report_links_verified',
                                            'inline_javascript_syntax_checks')}, indent=2))


if __name__ == '__main__':
    run()

