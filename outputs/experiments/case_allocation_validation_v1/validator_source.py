"""Freeze allocation, pilot and browser checks without freezing a live full run."""
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path('E:/code/Occupational-Fitness-Platform')
OUT = ROOT / 'outputs/experiments/case_allocation_validation_v1'
NAMES = ['case_allocation_judgment_preparation_v1',
         'case_allocation_judgment_pilot_inputs_v1', 'case_allocation_audit_v1',
         'case_allocation_judgment_pilot_v1', 'case_allocation_judgment_pilot_report_v1',
         'case_allocation_series_v1', 'scope88_optimization_comparison_v2']


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_bytes())


def save(p, v):
    p.write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


class HTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.scripts, self.active = [], [], False
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])
        if tag == 'script' and attrs.get('type') != 'application/json' and not attrs.get('src'):
            self.active = True
    def handle_endtag(self, tag):
        if tag == 'script':
            self.active = False
    def handle_data(self, data):
        if self.active:
            self.scripts.append(data)


def run():
    if (OUT / 'artifacts.json').exists():
        raise ValueError('Preserve frozen validation')
    pins, files, links, scripts = {}, 0, 0, 0
    for name in NAMES:
        folder = ROOT / 'outputs/experiments' / name
        inventory = read(folder / 'artifacts.json')
        for rel, expected in inventory.items():
            target = (folder / rel).resolve()
            if not target.is_relative_to(folder.resolve()) or sha(target) != expected:
                raise ValueError('Frozen evidence changed: ' + name + '/' + rel)
            files += 1
        pins[name] = sha(folder / 'artifacts.json')
        page = folder / 'index.html'
        if page.exists():
            parser = HTML()
            parser.feed(page.read_text(encoding='utf-8'))
            for href in set(parser.links):
                url = urlsplit(href)
                if not url.scheme and url.path:
                    if not (page.parent / unquote(url.path)).resolve().exists():
                        raise ValueError('Broken report link: ' + href)
                    links += 1
            for code in parser.scripts:
                p = subprocess.run(['E:/Node.js/node.exe', '--check', '-'], input=code,
                                   text=True, encoding='utf-8', capture_output=True)
                if p.returncode:
                    raise ValueError(p.stderr)
                scripts += 1
    suites = list(ET.parse(OUT / 'pytest_final.xml').getroot().iter('testsuite'))
    tests = {k:sum(int(s.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
    if tests != {'tests':895,'failures':0,'errors':0,'skipped':0}:
        raise ValueError('Full software test suite differs')
    if (OUT / 'ruff.txt').read_text(encoding='utf-8-sig').strip() != 'All checks passed!':
        raise ValueError('Ruff did not pass')
    pilot = read(ROOT / 'outputs/experiments/case_allocation_judgment_pilot_v1/summary.json')
    if (pilot['recorded'],pilot['accepted'],pilot['failed'],pilot['complete']) != (150,134,16,True):
        raise ValueError('Unexpected actual pilot inventory')
    prep = read(ROOT / 'outputs/experiments/case_allocation_judgment_preparation_v1/manifest.json')
    for rel, expected in prep['sources'].items():
        if sha(ROOT / rel) != expected:
            raise ValueError('Allocator/preparation implementation drifted after freezing')
    series = read(ROOT / 'outputs/experiments/case_allocation_series_v2/plan.json')
    for rel, expected in series['sources'].items():
        if sha(ROOT / rel) != expected:
            raise ValueError('Active serial implementation drifted')
    for name in ['overview.png','judgment_pair.png','original_evidence.png']:
        if not (OUT / name).is_file():
            raise ValueError('Missing actual browser proof')
    checks = {'updated_utc':datetime.now(timezone.utc).isoformat(),'pytest':tests,
              'ruff':'passed','artifact_files_verified':files,'input_inventory_sha256':pins,
              'local_links_verified':links,'inline_javascript_checks':scripts,
              'actual_pilot_calls':150,'pilot_accepted':134,'pilot_citation_failures':16,
              'full_conditions_planned':990,'full_run_complete':False,
              'active_series_identity':series['identity'],
              'browser':{'report':'case_allocation_judgment_pilot_report_v1',
                         'case':'SYN-EXT-012','model':'qwen3.5:4b-q4_K_M',
                         'pair':'retrieval_seventh','visible_change':'wrong_to_different_wrong',
                         'expanded_original':'AFTD2022-EXP-e3ca8efaf3d71461',
                         'pdf_page':113,'section':'3.3','console_errors':[],
                         'citation_failure_case':'VAL-MIX-10',
                         'own_tab_and_http_server_closed':True},
              'production_change':False}
    save(OUT / 'checks.json',checks)
    (OUT / 'validator_source.py').write_bytes(Path(__file__).read_bytes())
    save(OUT / 'artifacts.json',{p.name:sha(p) for p in OUT.iterdir()
                               if p.is_file() and p.name!='artifacts.json'})
    print(json.dumps({k:checks[k] for k in ('pytest','artifact_files_verified','local_links_verified','inline_javascript_checks')},indent=2))


if __name__ == '__main__':
    run()
