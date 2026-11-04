"""Post-hoc prose-ID audit; never repair or reclassify measured responses."""
import argparse
import hashlib
import json
import re
from collections import Counter
from html import escape
from pathlib import Path

ROOT = Path('E:/code/Occupational-Fitness-Platform')
PATTERN = re.compile(r'\bAFTD2022-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*\b')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def inventory(folder):
    pins = read(folder/'artifacts.json')
    for name, expected in pins.items():
        target = (folder/name).resolve()
        if not target.is_relative_to(folder.resolve()) or sha(target) != expected:
            raise ValueError('Frozen input changed')
    return sha(folder/'artifacts.json')


def run(output):
    exp = ROOT/'outputs/experiments'
    directory = exp/'case_allocation_judgment_full_v1'
    preparation = exp/'case_allocation_judgment_preparation_v1'
    analysis = exp/'case_allocation_effect_analysis_v1'
    pins = {name:inventory(exp/name) for name in (directory.name,preparation.name,analysis.name)}
    if (directory/'.run.lock').exists() or not read(directory/'summary.json')['complete']:
        raise ValueError('Wait for the complete stopped experiment')
    rows = [json.loads(line) for line in (directory/'results.jsonl').read_text(encoding='utf-8').splitlines()]
    if len(rows) != 990:
        raise ValueError('Require every actual full condition')
    payloads = {(r['case_id'],r['method']):r['payload'] for r in read(preparation/'payloads.json')}
    all_ids = {s['source_id'] for p in payloads.values() for s in p['guideline_evidence']}
    records, bad = [], []
    for row in rows:
        if row['status'] != 'completed':
            continue
        answer = row['answer']
        supplied = {s['source_id'] for s in payloads[(row['case_id'],row['method'])]['guideline_evidence']}
        if not set(answer['source_ids']) <= supplied:
            raise ValueError('Previously accepted structured citations are not supplied')
        mentions = []
        for token in sorted(set(PATTERN.findall(answer['explanation']))):
            status = 'supplied' if token in supplied else ('known_in_frozen_packets_but_not_supplied' if token in all_ids else 'unknown_in_frozen_packets')
            mentions.append({'literal_id':token,'status':status})
        datum = {k:row[k] for k in ('case_id','model','method','repeat')}
        datum.update(structured_source_ids=answer['source_ids'],prose_mentions=mentions,
                     explanation=answer['explanation'],actual_supplied_source_ids=sorted(supplied))
        records.append(datum)
        if any(m['status'] != 'supplied' for m in mentions):
            bad.append(datum)
    if output.exists():
        raise ValueError('Preserve prior post-hoc audits')
    summary = {'kind':'posthoc_literal_prose_identifier_audit','full_conditions':990,
               'accepted_conditions':len(records),'structured_contract_failures':990-len(records),
               'accepted_conditions_with_prose_ids':sum(bool(r['prose_mentions']) for r in records),
               'accepted_conditions_with_unsupplied_prose_id':len(bad),
               'prose_token_statuses':dict(Counter(m['status'] for r in records for m in r['prose_mentions'])),
               'regex':PATTERN.pattern,'new_model_calls':0,'raw_statuses_modified':False,
               'matching_scope':'Case-sensitive AFTD2022 prefix and ASCII hyphens; unique literal tokens per response, not every textual occurrence.',
               'parser_limits':'Lowercase prefixes and Unicode dashes are not detected. Hyphenated prose suffixes or spaced malformed IDs may create partial or extended tokens. Flagged literals require manual review, not a hallucination verdict.',
               'engineering_reference_labels_used':False,'clinical_review':'pending',
               'interpretation':'Literal identifier audit only. Unknown means absent from all actual frozen packets, not a clinician determination or a definitive hallucination count. Correct identifiers do not establish entailment. Prose anomalies remain separate from the measured structured-contract failure count.',
               'input_inventory_sha256':pins,'auditor_sha256':sha(Path(__file__))}
    output.mkdir(parents=True)
    save(output/'summary.json',summary)
    save(output/'accepted_prose_audit.json',records)
    save(output/'flagged_prose_references.json',bad)
    html = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Prose citation audit | Occupational Fitness Platform</title><style>body{font:15px/1.65 Arial;max-width:1180px;margin:32px auto;padding:24px;color:#26394a;background:#f5f7f9}section{padding:24px;background:white;border:1px solid #dce4eb;margin:16px 0;border-radius:8px}pre{white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer;padding:10px 0}a{color:#235f88}</style><section><small>OCCUPATIONAL FITNESS PLATFORM · POST-HOC ENGINEERING AUDIT</small><h1>Structured citations versus literal IDs in prose</h1>'
    html += f"<p>{len(records)} accepted responses; {990-len(records)} separately retained structured-contract failures. {len(bad)} accepted conditions contain a flagged literal token absent from their actual supplied packet.</p><p>{escape(summary['interpretation'])}</p><p>{escape(summary['matching_scope'])} {escape(summary['parser_limits'])}</p><p><a href='summary.json'>Summary</a> · <a href='flagged_prose_references.json'>All flagged literals and original explanations</a> · <a href='accepted_prose_audit.json'>Every accepted explanation audit</a></p></section>"
    for r in bad:
        html += '<section><details><summary>'+escape(' | '.join(str(r[k]) for k in ('case_id','model','method','repeat')))+'</summary><pre>'+escape(json.dumps(r,indent=2,ensure_ascii=False))+'</pre></details></section>'
    (output/'index.html').write_text(html,encoding='utf-8')
    (output/'auditor_source.py').write_bytes(Path(__file__).read_bytes())
    save(output/'artifacts.json',{p.name:sha(p) for p in output.iterdir() if p.is_file()})
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/experiments/case_allocation_prose_reference_audit_v1')
    run(parser.parse_args().output)
