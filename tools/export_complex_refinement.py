"""Build the concise review and export an integrity-checked portable report."""

from __future__ import annotations

import argparse
import json
import shutil
from html import escape
from pathlib import Path

from occupational_fitness_rag.evaluation.retrieval_refinement import original_footprints
from tools.complex_ten_contract import ROOT, digest, pin, read, rows, write_json
from tools.refine_complex_retrieval import DEFAULT, PARENT, SOURCES, TARGETS, verify
from tools.report_complex_refinement import NAMES, NUMBERS, pct


def review(output):
    protocol = verify(output, PARENT)
    summary = read(output / "summary.json")
    joint = read(output / "joint_prefix/manifest.json")
    if joint["identity"] != digest({k: v for k, v in joint.items() if k != "identity"}):
        raise ValueError("Joint selection manifest differs")
    if joint["parent_rankings_sha256"] != pin(output / "rankings.jsonl"):
        raise ValueError("Joint selection input differs")
    for name, expected in joint["source_files"].items():
        if pin(ROOT / name) != expected:
            raise ValueError("Joint selection source differs")
    actual = rows(output / "rankings.jsonl")
    previous = {(r["query_id"], r["method"]): r for r in actual}
    units = {u["source_id"]: u for u in read(output / "corpus.json")["units"]}
    extra = rows(output / "joint_prefix/rankings.jsonl")
    if (
        pin(output / "joint_prefix/rankings.jsonl")
        != read(output / "joint_prefix/complete.json")["rankings_sha256"]
    ):
        raise ValueError("Joint selection output differs")
    changed = 0
    for r in extra:
        old = previous[r["query_id"], r["baseline_method"] + "__literal_facets"]
        if r["record_sha256"] != digest({k: v for k, v in r.items() if k != "record_sha256"}) or r[
            "parent_record_sha256"
        ] != digest(old):
            raise ValueError("Joint selection lineage differs")
        if r["status"] != "completed":
            raise ValueError("The joint-selection review requires completed conditions")
        atoms = original_footprints(units, r["module"])
        for k in (1, 3, 5, 10):
            before = set().union(*(atoms[s] for s in old["source_ids"][:k]))
            after = set().union(*(atoms[s] for s in r["source_ids"][:k]))
            if not before <= after:
                raise ValueError("Joint selection lost a protected original")
        changed += r["source_ids"] != old["source_ids"]
    if len(extra) != 714:
        raise ValueError("Joint selection cardinality differs")
    # Verify the complete initial implementation trace and its exact source
    # snapshots. Failed rows are not substituted into the repaired comparison.
    initial = protocol["retained_initial_implementation_attempt"]
    for name, key in (("protocol.json", "protocol_sha256"), ("rankings.jsonl", "rankings_sha256")):
        if pin(output / "initial_attempt" / name) != initial[key]:
            raise ValueError("Retained initial observations changed")
    for name, expected in initial["source_snapshots"].items():
        if pin(output / "initial_attempt/implementation" / name) != expected:
            raise ValueError("Retained initial implementation snapshot differs")
    final = {
        "protocol_identity": protocol["identity"],
        "primary_conditions": len(actual),
        "joint_conditions": len(extra),
        "joint_changed_rankings": changed,
        "joint_combinations_checked": sum(
            r["diagnostics"]["five_source_combinations"] for r in extra
        ),
        "successful_conditions": sum(r["status"] == "completed" for r in actual + extra),
        "failed_final_conditions": sum(r["status"] != "completed" for r in actual + extra),
        "retained_initial_conditions": 3570,
        "retained_initial_failed_conditions": 1164,
        "nested_original_checks": 4 * (len(actual) + len(extra)),
        "old_baselines_preserved": True,
        "production_unchanged": True,
    }
    write_json(output / "final_audit.json", final)
    mm = {(m["cohort"], m["module"], m["method"]): m for m in summary["metrics"]}
    pm = {(m["cohort"], m["method"]): m for m in summary["packet_metrics"]}
    content = ""
    for base in TARGETS:
        before, after = mm["all", "all", base], mm["all", "all", base + "__literal_facets"]
        packet0, packet1 = pm["all", base], pm["all", base + "__literal_facets"]
        content += "<tr><td>" + escape(NUMBERS[base] + " · " + NAMES[base]) + "</td>"
        for key in (
            "coverage_recall_5",
            "coverage_recall_10",
            "complete_coverage_5",
            "exact_id_recall_5",
        ):
            content += f"<td>{pct(before[key])}<span>→ {pct(after[key])}</span></td>"
        content += f"<td>{pct(packet0['mean_reference_coverage'])}<span>→ {pct(packet1['mean_reference_coverage'])}</span></td></tr>"
    html = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Retrieval optimization results · Occupational Fitness Platform</title><style>
    *{box-sizing:border-box}body{font:14px/1.7 Segoe UI,Arial,sans-serif;color:#23384c;background:#f5f7fa;margin:0}main{max-width:1430px;margin:auto;padding:38px}header{border-bottom:1px solid #dbe3eb;padding-bottom:22px}h1{font-size:31px;letter-spacing:-.7px;margin:14px 0}h2{font-size:20px}.brand{font-size:11px;font-weight:700;letter-spacing:1.3px}.muted{color:#61778b}section{background:#fff;border:1px solid #dce4ec;border-radius:9px;margin-top:24px;padding:25px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin-top:25px}.cards div{border:1px solid #dce4ec;border-radius:7px;padding:18px;background:white}.cards b{display:block;font-size:26px}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}th,td{padding:17px 12px;border-bottom:1px solid #e0e7ee;text-align:right;white-space:nowrap}td:first-child,th:first-child{text-align:left}th{font-size:11px;color:#61778b}td span{display:block;font-weight:650;color:#224d6d}.note{border-left:3px solid #9baec0;padding-left:17px}a{color:#245b85;text-decoration:none}a:hover{text-decoration:underline}.action{display:inline-block;border:1px solid #bbcbd9;border-radius:5px;padding:9px 15px;margin-right:10px;background:#fff}footer{color:#61778b;margin:30px 0}.cols{display:grid;grid-template-columns:1fr 1fr;gap:25px}@media(max-width:850px){main{padding:20px 14px}.cards{grid-template-columns:1fr 1fr}.cols{grid-template-columns:1fr}}
    </style></head><body><main><header><div class="brand">OCCUPATIONAL FITNESS PLATFORM · ENGINEERING EVALUATION</div><h1>Retrieval optimization results</h1><p class="muted">29 October 2026 · Paired comparison on the same frozen cases, corpus and engineering references.</p><a class="action" href="index.html#comparison">Full interactive comparison ↗</a><a class="action" href="index.html#cases">Inspect original evidence ↗</a><a class="action" href="metrics.csv">Download metrics CSV ↗</a></header>
    <div class="cards"><div><b>234</b>Unchanged complex input notes</div><div><b>4,284</b>Completed new conditions</div><div><b>0</b>Final execution failures</div><div><b>273</b>Source-labelled query scopes</div></div>
    <section><h2>Before → after</h2><p>After = protected allocation plus verbatim sentence views. Every successful variant preserves the earlier complete original-text footprint at ranks 1, 3, 5 and 10. Larger retrieved parent passages are counted at their full text size.</p><div class="scroll"><table><thead><tr><th>Method family</th><th>Coverage R@5</th><th>Coverage R@10</th><th>Complete evidence @5</th><th>Exact source ID @5</th><th>Case packet coverage</th></tr></thead><tbody>__TABLE__</tbody></table></div><p class="muted">273 labelled module queries from 222 labelled cases contribute to source recall. All 234 notes are retrieved. Packet coverage is scored per labelled case under the unchanged five-whole-original / 9,000-byte round-robin evidence budget.</p></section>
    <section><h2>What changed</h2><div class="cols"><div><h3>Candidate retrieval and fusion</h3><p>Method 3 uses wider measured vector/BM25 candidates. Method 4 retains its source/rule/section graph candidate ranking. Method 7 expands its original fact-planned search frontier. All can use up to six complete, verbatim disease-scoped sentences, with a fixed RRF weight shared across the added views.</p><p>Method 9 replays its actual Neo4j response frontier; method 10 replays its actual PageIndex navigated original leaves. Their new facet scores and allocation are first-party post-retrieval refinements, with no new graph/tree navigation or hidden native substitute.</p></div><div><h3>Original evidence allocation</h3><p>Only same-page parents containing complete retrieved originals can consolidate overlapping evidence. New ranking preserves previous whole-original coverage at four prefix depths. The selection objective uses typed criterion coverage and total original coverage, then measured retrieval relevance; no expected answers enter ranking.</p><p>Original methods, all previous results, unchanged notes and production settings remain preserved. New local sentence embeddings were actually computed by Ollama; raw requests and responses are included.</p></div></div></section>
    <section><h2>Gains and limits</h2><p>Method 10 reaches 90.29% coverage R@5 and 87.02% case packet coverage. Method 4 reaches 95.18% coverage R@10. Method 3 mainly improves R@10. Methods 7 and 9 retain their earlier R@5; their gains are in R@10.</p><p class="note">The metrics do not all improve. Exact-ID recall declines because a complete parent original replaces directly returned child IDs; method 4 also uses more original text. Do not interpret broader original-text coverage as universal retrieval superiority or improved fitness judgment accuracy.</p><p>For methods 7 and 9, an additional joint-selection experiment examined __COMBINATIONS__ five-passage combinations in 714 conditions. It produced no additional change. This result concerns the current candidate pool, nested preservation constraints and typed/all-original coverage objective; it does not establish a limit on patient-aware relevance ranking or other retrieval architectures.</p><p>The paired ablation is retained: allocation alone versus allocation plus sentence views. Sentence views do not increase R@5 for methods 7 or 9 on this cohort. This is a development-set observation, with correlated synthetic families and pending independent clinical annotation.</p></section>
    <section><h2>Validation and evidence trail</h2><p>__CHECKS__ nested whole-original coverage checks passed across the final 4,284 conditions. The first implementation attempt contained a source-swap defect: 1,164 of its 3,570 conditions were rejected. That full attempt and its exact source snapshots remain in <a href="initial_attempt/complete.json">initial_attempt</a>. The defect was fixed, all primary conditions rerun, and no favorable failed-run results were substituted.</p><p>Recorded optimization timing excludes reused native graph/tree navigation, intake and cached embeddings. This experiment does not claim an end-to-end latency improvement. Clinical decision models were not called.</p><p><a href="final_audit.json">Final integrity audit</a> · <a href="protocol.json">Frozen primary protocol</a> · <a href="joint_prefix/manifest.json">Joint-selection protocol</a> · <a href="paired_case_changes.json">Per-case paired changes</a> · <a href="joint_prefix/rankings.jsonl">Joint-selection raw records</a> · <a href="summary.json">Complete primary metrics</a></p></section>
    <section><h2>Next decision</h2><p>Keep the production retriever unchanged. Test whether method 10's higher finite-budget evidence coverage improves fitness decisions under the same frozen facts, decision model and prompt. For methods 7 and 9, investigate which patient-specific conditions and exceptions are missing from the evidence, rather than maximizing corpus criterion counts alone. Independently review retrieval relevance before claiming precision or clinical accuracy.</p></section><footer>Engineering source-reference comparison · Clinical review pending · Original evidence remains inspectable.</footer></main></body></html>"""
    html = (
        html.replace("__TABLE__", content)
        .replace("__COMBINATIONS__", f"{final['joint_combinations_checked']:,}")
        .replace("__CHECKS__", f"{final['nested_original_checks']:,}")
    )
    (output / "review.html").write_text(html, encoding="utf-8")
    return final


def export(output, destination):
    review(output)
    destination = destination.resolve()
    if (
        destination == output
        or destination.is_relative_to(output)
        or output.is_relative_to(destination)
    ):
        raise ValueError("Delivery must be separate from source observations")
    destination.mkdir(parents=True, exist_ok=True)
    exported = {}
    for source in output.rglob("*"):
        if not source.is_file() or source.name in {".owner.lock", "delivery_manifest.json"}:
            continue
        relative = source.relative_to(output)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and pin(target) != pin(source):
            raise ValueError(
                "Do not overwrite a different prior delivered observation: " + str(relative)
            )
        if not target.exists():
            shutil.copyfile(source, target)
        if pin(target) != pin(source):
            raise ValueError("Export hash differs")
        exported[relative.as_posix()] = pin(target)
    sources = [
        *SOURCES,
        *read(output / "joint_prefix/manifest.json")["source_files"],
        "tools/export_complex_refinement.py",
        "tests/test_retrieval_refinement.py",
        "docs/complex_234_retrieval_refinement.md",
    ]
    for name in dict.fromkeys(sources):
        target = destination / "implementation" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and pin(target) != pin(ROOT / name):
            raise ValueError("Delivered implementation differs")
        if not target.exists():
            shutil.copyfile(ROOT / name, target)
        exported[target.relative_to(destination).as_posix()] = pin(target)
    for name, expected in exported.items():
        if pin(destination / name) != expected:
            raise ValueError("Delivered observation changed")
    write_json(
        destination / "delivery_manifest.json",
        {
            "files": exported,
            "file_count": len(exported),
            "total_bytes": sum((destination / n).stat().st_size for n in exported),
            "entry": "review.html",
            "verified": True,
        },
    )
    print(
        json.dumps(
            {"destination": str(destination), "files": len(exported), "entry": "review.html"}
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT)
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    if args.destination:
        export(args.output.resolve(), args.destination)
    else:
        print(json.dumps(review(args.output.resolve()), indent=2))
