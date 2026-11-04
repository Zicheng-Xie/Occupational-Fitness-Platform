import json
import shutil
from html import escape
from pathlib import Path

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.provenance import digest, write_json
from tools.report_anchored_hybrid import read_rows, verify_bundle

root = Path.cwd()
base = root / "outputs/experiments"
out = base / "semantic_rerank_diagnostic_v1"
if out.exists() or not out.resolve().is_relative_to(base.resolve()):
    raise ValueError("Use a fresh diagnostic directory")
folders = ["guarded_hybrid_v3", "semantic_guarded_hybrid_v5", "semantic_guarded_retrieval_v5", "native_flag_rerank_v1"]
provenance = {}
for name in folders:
    directory = base / name
    manifest = json.loads((directory / "manifest.json").read_bytes())
    if name == "semantic_guarded_retrieval_v5":
        # This reporter's identity includes its explicit production_change=false.
        assert digest({k: v for k, v in manifest.items() if k != "identity"}) == manifest["identity"]
        assert all(file_hash(directory / k) == v for k, v in json.loads((directory / "artifacts.json").read_bytes()).items())
    else:
        verify_bundle(directory)
    provenance[name] = {"identity": manifest["identity"], "artifacts_sha256": file_hash(directory / "artifacts.json")}
corpus = json.loads((base / "semantic_guarded_hybrid_v5/corpus.json").read_bytes())
units = {u["source_id"]: u for u in corpus["units"]}
queries = {q["query_id"]: q for q in json.loads((base / "semantic_guarded_hybrid_v5/queries.json").read_bytes())}
rows = read_rows(base / "semantic_guarded_retrieval_v5/rankings.jsonl")
index = {(r["query_id"], r["method"]): r for r in rows}
scored = json.loads((base / "semantic_guarded_retrieval_v5/retrieval_metrics.json").read_bytes())
metrics = json.loads((base / "semantic_guarded_retrieval_v5/summary.json").read_bytes())
baseline, candidate, native = "planned_hybrid_v3_guarded_30", "planned_hybrid_v5_semantic_025", "flag_embedding_rerank"
regression = next(p for p in metrics["paired_changes"] if p["baseline"] == baseline and p["candidate"] == candidate)
records = []
for comparison in regression["rows"]:
    if comparison["coverage_change"] != "regressed":
        continue
    qid = comparison["query_id"]
    before, after, native_row = [index[(qid, method)] for method in (baseline, candidate, native)]
    required = next(r["reference_sources"] for r in scored if r["query_id"] == qid and r["method"] == candidate)
    trace = {r["source_id"]: r for r in after["diagnostics"]["candidate_score_trace"]}
    quotes = []
    for sid in dict.fromkeys([*before["source_ids"][:5], *after["source_ids"][:5], *[s for s in after["source_ids"] if set(required) & {s, *units[s].get("covers_source_ids", [])}]]):
        unit = units[sid]
        positions = {name: record["source_ids"].index(sid) + 1 if sid in record["source_ids"] else None for name, record in (("v3_rank", before), ("v5_rank", after), ("native_rank", native_row))}
        quotes.append({"source_id": sid, "native_sigmoid": trace[sid]["native_sigmoid"], **positions, "covers_reference_ids": sorted(set(required) & {sid, *unit.get("covers_source_ids", [])}), "covers_source_ids": unit.get("covers_source_ids", []), "section": unit["section"], "pdf_page": unit["pdf_page"], "printed_page": unit["printed_page"], "text_sha256": unit["text_sha256"], "original_text": unit["evidence_text"]})
    records.append({**comparison, "query": queries[qid]["query"], "engineering_reference_sources": required, "v3_top10": before["source_ids"], "v5_top10": after["source_ids"], "native_top10": native_row["source_ids"], "source_quotes_and_scores": quotes})
assert len(records) == 4
hypotheses = [
    {"name": "Topical score differs from predicate applicability", "observed": "For under-investigation blackout queries, section 1.2.4 about undetermined mechanism after extensive investigation scores above the source advising no driving until the mechanism is ascertained. Acute metabolic-instability advice also scores below routine diabetes-treatment passages.", "causal_status": "Observational mechanism hypothesis; no controlled prompt, content-format or predicate intervention was run."},
    {"name": "Formatting and surrounding commercial context can affect native scores", "observed": "For SYN-EXT-018, the canonical diplopia source has sigmoid 0.12765262532179067, while the longer commercial-table original containing that same criterion scores 0.8578872059303786. Visual-field originals score up to 0.9184802440252811 despite the query documenting no confirmed field defect.", "causal_status": "The passages differ in length and context as well as headers, so this observation does not isolate the causal contribution of formatting."},
    {"name": "Coverage protection succeeds at Top10 but does not protect Top5 order", "observed": "Both semantic variants retain 100% source coverage at Top10. The primary blend demotes four formerly fully-covered query scopes below rank five, leaving 83.70% average Top5 coverage compared with v3 92.59%.", "causal_status": "Paired retrieval observation with fixed corpus/query/candidate inputs; not a demonstrated clinical judgment effect."},
]
protocol = {
    "kind": "post_freeze_observational_reranker_mechanism_diagnostic", "baseline": baseline, "primary_candidate": candidate, "weights_predefined_before_scoring": [0.25, 0.5],
    "selection": "All four Top5 coverage-regressed labeled scopes for the predefined primary candidate versus v3; no case-specific rank adjustments. Source lists retain unchanged original quotes from both Top5 lists plus returned sources containing the affected reference.",
    "scope": "33 observed development cases; 77 module queries, 45 labeled scopes; no sealed holdout and no clinical accuracy claim.",
    "no_additional_tuning_reason": "One- or two-position adjacent promotions would not generally reach the remaining v3 missing references at ranks7-10. Unconditional native promotion has demonstrated predicate mismatches. Exact literal whole-clause consolidation was already evaluated among v2 variants without improving the retained v3 result. No further source-specific, case-specific or weight-grid tuning is justified on these observed failures.",
    "next_study_not_implemented": ["Independently annotate clause applicability predicates and temporal states, blinded to patient expected source IDs.", "Build held-out query/clause pairs for affirmation, negation, current versus historical states and under-investigation versus resolved mechanism.", "Evaluate predicate entailment separately from topical similarity and citation validity.", "Freeze one globally bounded adjacent-promotion/consolidation policy before the held-out evaluation; retain the full v3 Top10 footprint and whole-original budget.", "Report relevance and applicability errors separately, and only run downstream judgments after that independent validation."],
    "new_model_calls": 0, "production_change": False, "clinical_support_review": "pending", "provenance": provenance,
}
out.mkdir(parents=True)
write_json(out / "diagnostics.json", {"protocol": protocol, "hypotheses": hypotheses, "regressed_query_scopes": records})
text = "SEMANTIC RERANKING: OBSERVATIONAL DIAGNOSTIC\n\nRetain v3 as the preferred seventh method for this batch.\n\nv3: Coverage R@5 92.59%; R@10 100.00%.\nSemantic weight0.25: R@5 83.70%; R@10 100.00%.\nSemantic weight0.50: R@5 81.48%; R@10 100.00%.\nNative Flag baseline: R@5 79.26%; R@10 92.22%.\n\nThese are engineering source-reference recall values on observed development fixtures, not clinical accuracy. Both semantic hypotheses were frozen before scoring. Every failure and regression remains preserved.\n\n"
for h in hypotheses:
    text += h["name"] + "\n" + h["observed"] + "\n" + h["causal_status"] + "\n\n"
text += "NO FURTHER RANK TUNING\n" + protocol["no_additional_tuning_reason"] + "\n\nNEXT STUDY (NOT IMPLEMENTED)\n" + "\n".join(str(i + 1) + ". " + s for i, s in enumerate(protocol["next_study_not_implemented"])) + "\n"
(out / "brief.txt").write_text(text, encoding="utf8")
html = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Semantic reranking diagnostic | Occupational Fitness Platform</title><style>body{font:14px/1.6 Arial,sans-serif;margin:0;background:#f3f6f8;color:#24384a}main{max-width:1200px;margin:30px auto;padding:0 24px}section,header{padding:24px;background:white;border:1px solid #dce4ea;border-radius:8px;margin-bottom:20px}h1{font-size:27px}h2{font-size:19px}table{border-collapse:collapse;width:100%;font-size:12px}td,th{text-align:left;padding:9px;border-bottom:1px solid #dce4ea}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f8fa;padding:14px}a{color:#236082}summary{cursor:pointer;padding:10px 0}</style><main><header><h1>Semantic reranking: observed failure mechanisms</h1><p>Occupational Fitness Platform · Experimental development evidence</p><p>Keep v3 as the preferred seventh method. These observations generate hypotheses; they do not establish clinical accuracy or isolate the effect of any single passage/header.</p><p><a href="diagnostics.json">Exact scores, rankings and source text</a> · <a href="brief.txt">English brief</a> · <a href="manifest.json">Provenance</a></p></header>'
for h in hypotheses:
    html += "<section><h2>" + escape(h["name"]) + "</h2><p>" + escape(h["observed"]) + "</p><p>" + escape(h["causal_status"]) + "</p></section>"
for record in records:
    html += "<section><h2>" + escape(record["case_id"] + " / " + record["module"]) + "</h2><pre>" + escape(record["query"]) + "</pre><p>Engineering reference sources: " + escape(", ".join(record["engineering_reference_sources"])) + "</p><table><tr><th>Original source</th><th>Native sigmoid</th><th>v3 rank</th><th>v5 rank</th><th>Native rank</th></tr>"
    for source in record["source_quotes_and_scores"]:
        html += "<tr>" + "".join("<td>" + escape(str(source[k])) + "</td>" for k in ("source_id", "native_sigmoid", "v3_rank", "v5_rank", "native_rank")) + "</tr>"
    html += "</table>"
    for source in record["source_quotes_and_scores"]:
        html += "<details><summary>" + escape(source["source_id"]) + " · Section " + escape(str(source["section"])) + " · PDF " + str(source["pdf_page"]) + '</summary><p><a href="evidence_guide.pdf#page=' + str(source["pdf_page"]) + '">Open original guideline page</a> · Printed page ' + escape(str(source["printed_page"])) + "</p><pre>" + escape(source["original_text"]) + "</pre></details>"
    html += "</section>"
html += "<section><h2>Stop further tuning on this batch</h2><p>" + escape(protocol["no_additional_tuning_reason"]) + "</p><h2>Next study — not implemented</h2><ol>" + "".join("<li>" + escape(s) + "</li>" for s in protocol["next_study_not_implemented"]) + "</ol><p>" + escape(protocol["scope"]) + "</p></section></main></html>"
(out / "index.html").write_text(html, encoding="utf8")
guide = base / "semantic_guarded_retrieval_v5/evidence_guide.pdf"
assert file_hash(guide) == corpus["document_sha256"]
shutil.copyfile(guide, out / "evidence_guide.pdf")
shutil.copyfile(__file__, out / "builder_source.py")
manifest = {"protocol_sha256": digest(protocol), "input_provenance": provenance, "source_document_sha256": corpus["document_sha256"], "native_configuration": json.loads((base / "native_flag_rerank_v1/manifest.json").read_bytes())["config"], "builder_sha256": file_hash(__file__), "new_model_calls": 0}
write_json(out / "manifest.json", {**manifest, "identity": digest(manifest), "production_change": False})
write_json(out / "artifacts.json", {p.name: file_hash(p) for p in out.iterdir() if p.is_file() and p.name != "artifacts.json"})
print(json.dumps({"identity": digest(manifest), "artifacts_sha256": file_hash(out / "artifacts.json"), "regressed_scopes": len(records)}))
