"""Verify the actual supplied commercial-vision original against its PDF region."""
import hashlib
import json
from pathlib import Path

import fitz

ROOT = Path('E:/code/Occupational-Fitness-Platform')
OUT = ROOT/'outputs/experiments/vision_source_visual_review_v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def run():
    if OUT.exists():
        raise ValueError('Preserve earlier source reviews')
    corpus_path = ROOT/'outputs/experiments/scope88_optimization_comparison_v2/corpus.json'
    corpus = json.loads(corpus_path.read_bytes())
    unit = next(u for u in corpus['units'] if u['source_id']=='AFTD2022-EXP-a09b64ac70a92828')
    pdf = ROOT/unit['source_path']
    if sha(pdf) != unit['document_sha256']:
        raise ValueError('Original guideline changed')
    payload_path = ROOT/'outputs/experiments/case_allocation_judgment_preparation_v1/payloads.json'
    payloads = json.loads(payload_path.read_bytes())
    supplied = next(s for r in payloads if r['case_id']=='VAL-MIX-02' and r['method']=='seventh_case_coverage' for s in r['payload']['guideline_evidence'] if s['source_id']==unit['source_id'])
    with fitz.open(pdf) as doc:
        page = doc[unit['pdf_page']-1]
        region = page.get_text(clip=fitz.Rect(unit['bbox']))
        if ' '.join(region.split()) != ' '.join(unit['evidence_text'].split()) or supplied['source_text'] != unit['evidence_text']:
            raise ValueError('Actual supplied source differs from the native PDF column')
        OUT.mkdir(parents=True)
        page.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(OUT/'page_220.png')
        page.get_pixmap(matrix=fitz.Matrix(2,2),clip=fitz.Rect(unit['bbox'])).save(OUT/'source_region.png')
    data = {'kind':'native_commercial_vision_region_consistency','source_id':unit['source_id'],
            'section':unit['section'],'pdf_page':unit['pdf_page'],'printed_page':unit['printed_page'],
            'bbox':unit['bbox'],'licence_context':unit['licence_context'],
            'pdf_sha256':sha(pdf),'corpus_sha256':sha(corpus_path),'payloads_sha256':sha(payload_path),
            'native_region_text':region,'actual_supplied_text':supplied['source_text'],
            'normalized_exact_pdf_match':True,'actual_payload_text_exact_match':True,
            'review_scope':'Engineering literal text and column consistency; no independent clinical adjudication.',
            'clinical_review':'pending','model_calls':0,'production_change':False,'verifier_sha256':sha(Path(__file__))}
    save(OUT/'checks.json',data)
    (OUT/'verifier_source.py').write_bytes(Path(__file__).read_bytes())
    save(OUT/'artifacts.json',{p.name:sha(p) for p in OUT.iterdir() if p.is_file()})
    print(json.dumps({k:data[k] for k in ('source_id','pdf_page','normalized_exact_pdf_match','actual_payload_text_exact_match')},indent=2))


if __name__=='__main__':
    run()
