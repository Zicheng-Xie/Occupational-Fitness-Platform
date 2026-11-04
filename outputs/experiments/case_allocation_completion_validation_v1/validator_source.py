"""Freeze completed990-condition results, software checks and actual UI proof."""
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path('E:/code/Occupational-Fitness-Platform')
OUT = ROOT / 'outputs/experiments/case_allocation_completion_validation_v1'
NAMES = [
    'case_allocation_judgment_preparation_v1', 'case_allocation_judgment_pilot_v1',
    'case_allocation_judgment_pilot_report_v1', 'case_allocation_audit_v1',
    'case_allocation_judgment_full_v1', 'case_allocation_series_v2',
    'case_allocation_judgment_comparison_v1', 'case_allocation_effect_analysis_v1',
    'case_allocation_full_integrity_v1', 'case_allocation_completion_v1',
    'case_allocation_focus_support_review_v1',
    'case_allocation_prose_reference_audit_v1',
    'vision_source_visual_review_v1',
    'blackout_source_visual_review_v1', 'prospective_case_review_v1',
    'prospective_case_review_v2', 'scope88_optimization_comparison_v2',
]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_bytes())


def save(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


class HTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.scripts, self.active = [], [], False
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('a', 'img', 'script'):
            self.links.extend(attrs[k] for k in ('href', 'src') if attrs.get(k))
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
        raise ValueError('Preserve completed validation')
    pins, files, links, scripts = {}, 0, 0, 0
    exp = ROOT / 'outputs/experiments'
    for name in NAMES:
        directory = exp / name
        inventory = read(directory / 'artifacts.json')
        if not inventory:
            raise ValueError('Empty frozen input inventory')
        for rel, expected in inventory.items():
            target = (directory / rel).resolve()
            if not target.is_relative_to(directory.resolve()) or sha(target) != expected:
                raise ValueError('Frozen artifact changed: ' + name + '/' + rel)
            files += 1
        pins[name] = sha(directory / 'artifacts.json')
        page = directory / 'index.html'
        if page.exists():
            parser = HTML(); parser.feed(page.read_text(encoding='utf-8'))
            for href in set(parser.links):
                url = urlsplit(href)
                if not url.scheme and url.path:
                    if not (page.parent / unquote(url.path)).resolve().is_file():
                        raise ValueError('Broken local report target: ' + str(page) + '/' + href)
                    links += 1
            for code in parser.scripts:
                result = subprocess.run(['E:/Node.js/node.exe', '--check', '-'], input=code,
                                        text=True, encoding='utf-8', capture_output=True)
                if result.returncode:
                    raise ValueError(result.stderr)
                scripts += 1
    suites = list(ET.parse(OUT/'pytest_final.xml').getroot().iter('testsuite'))
    tests = {k:sum(int(s.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
    if tests['tests'] < 929 or any(tests[k] for k in ('failures','errors','skipped')):
        raise ValueError('The complete current software suite did not pass')
    if (OUT/'ruff.txt').read_text(encoding='utf-8-sig').strip() != 'All checks passed!':
        raise ValueError('The complete source lint check did not pass')
    full = read(exp/'case_allocation_judgment_full_v1/summary.json')
    audit = read(exp/'case_allocation_full_integrity_v1/checks.json')
    analysis = read(exp/'case_allocation_effect_analysis_v1/summary.json')
    if not (full['complete'] and audit['complete'] and analysis['complete']):
        raise ValueError('Incomplete full experiment, independent audit or analysis')
    if (full['recorded'],audit['observed_conditions'],analysis['recorded_actual_calls']) != (990,990,990):
        raise ValueError('Full inventory differs')
    if full['accepted'] != analysis['accepted'] or full['failed'] != sum(audit['failures_by_contract'].values()):
        raise ValueError('Accepted/failed totals differ across independent analyses')
    prep = read(exp/'case_allocation_judgment_preparation_v1/manifest.json')
    for rel, expected in prep['sources'].items():
        if sha(ROOT/rel) != expected:
            raise ValueError('Frozen allocator/preparation source drifted')
    series = read(exp/'case_allocation_series_v2/plan.json')
    for rel, expected in series['sources'].items():
        if sha(ROOT/rel) != expected:
            raise ValueError('Executing series source drifted')
    if any((exp/name/'.run.lock').exists() for name in ('case_allocation_series_v2','case_allocation_judgment_full_v1')):
        raise ValueError('Completed process has not released its locks')
    readiness = read(exp/'prospective_case_review_v2/readiness.json')
    if readiness['ready_for_prospective_evaluation'] or readiness['system_calls']:
        raise ValueError('Unlabeled prospective notes were evaluated')
    prospective_sources = read(exp/'prospective_case_review_v2/implementation_snapshot.json')
    if any(sha(ROOT/name) != expected for name,expected in prospective_sources.items()):
        raise ValueError('Prospective source snapshot drifted after freezing')
    for name in ('overview.png','focus_pair.png','source_context.png','prospective_review.png'):
        if not (OUT/name).is_file():
            raise ValueError('Missing actual browser screenshot: ' + name)
    browser = read(OUT/'browser_checks.json')
    if browser['console_errors'] or not browser['own_tab_and_http_server_closed']:
        raise ValueError('Browser verification did not complete cleanly')
    checks = {'updated_utc':datetime.now(timezone.utc).isoformat(),'pytest':tests,'ruff':'passed',
              'artifact_files_verified':files,'input_inventory_sha256':pins,
              'local_links_verified':links,'inline_javascript_checks':scripts,
              'actual_full_calls':990,'accepted':full['accepted'],'failed':full['failed'],
              'full_run_complete':True,'patient_count':33,'pilot_calls_imported':0,
              'independent_audit':audit,'browser':browser,'prospective_ready':False,
              'prospective_live_source_pins_verified':len(prospective_sources),
              'independent_human_labels':'pending','clinical_review':'pending','production_change':False}
    save(OUT/'checks.json',checks)
    (OUT/'validator_source.py').write_bytes(Path(__file__).read_bytes())
    save(OUT/'artifacts.json',{p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='artifacts.json'})
    print(json.dumps({k:checks[k] for k in ('pytest','actual_full_calls','accepted','failed','artifact_files_verified','local_links_verified','inline_javascript_checks')},indent=2))


if __name__ == '__main__':
    run()
