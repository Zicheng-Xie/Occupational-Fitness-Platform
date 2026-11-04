"""Join completed paired judgments to the exact evidence and ordering supplied.

Read-only postprocessing: no new model calls, relabeling or source substitution.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from html import escape
from pathlib import Path

from occupational_fitness_rag.evaluation.graph_contract import file_hash
from occupational_fitness_rag.evaluation.passage_comparison import read_records
from occupational_fitness_rag.provenance import digest, write_json
from tools.run_frozen_retrieval_judgments import key, verify_files


def compare_evidence(before, after):
    """Separate unchanged patient data from changed original passages/order."""
    first = {k: v for k, v in before.items() if k != "guideline_evidence"}
    second = {k: v for k, v in after.items() if k != "guideline_evidence"}
    if digest(first) != digest(second):
        raise ValueError("Evidence comparison changed the frozen patient")
    pools = [
        {u["source_id"]: u for u in payload["guideline_evidence"]} for payload in (before, after)
    ]
    if any(
        len(pool) != len(payload["guideline_evidence"])
        for pool, payload in zip(pools, (before, after))
    ):
        raise ValueError("Repeated source in the supplied evidence")
    common = pools[0].keys() & pools[1].keys()
    if any(pools[0][sid] != pools[1][sid] for sid in common):
        raise ValueError("A common source ID changed its original text or locator")
    ids = [list(pool) for pool in pools]
    return {
        "patient_identity": digest(first),
        "baseline_source_ids": ids[0],
        "candidate_source_ids": ids[1],
        "added_source_ids": [s for s in ids[1] if s not in pools[0]],
        "removed_source_ids": [s for s in ids[0] if s not in pools[1]],
        "common_source_rank_changes": [
            {
                "source_id": s,
                "baseline_rank": ids[0].index(s) + 1,
                "candidate_rank": ids[1].index(s) + 1,
            }
            for s in ids[0]
            if s in common
        ],
        "baseline_evidence_bytes": len(
            json.dumps(before["guideline_evidence"], ensure_ascii=False).encode()
        ),
        "candidate_evidence_bytes": len(
            json.dumps(after["guideline_evidence"], ensure_ascii=False).encode()
        ),
    }


def build(root, run, retrieval, labels_path, output):
    root, run, retrieval, output = [Path(p).resolve() for p in (root, run, retrieval, output)]
    if output.exists() or not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Use a new evidence-analysis directory")
    run_pins, retrieval_pins = verify_files(run), verify_files(retrieval)
    summary = json.loads((run / "summary.json").read_bytes())
    plan = json.loads((run / "plan.json").read_bytes())
    if not summary["complete"] or (run / ".run.lock").exists():
        raise ValueError("Use a completed, frozen judgment run")
    if file_hash(labels_path) != plan["preparation_artifacts"]["scoring_labels.json"]:
        raise ValueError("Engineering labels differ from the original judgment plan")
    labels = json.loads(Path(labels_path).read_bytes())
    corpus = json.loads((retrieval / "corpus.json").read_bytes())
    units = {u["source_id"]: u for u in corpus["units"]}
    payloads = {
        (r["case_id"], r["method"]): r["payload"]
        for r in json.loads((run / "payloads.json").read_bytes())
    }
    for payload in payloads.values():
        for source in payload["guideline_evidence"]:
            unit = units[source["source_id"]]
            if source["source_text"] != unit["evidence_text"] or any(
                source[k] != unit[k] for k in ("module", "section", "pdf_page", "printed_page")
            ):
                raise ValueError("Judgment evidence is not the exact frozen original source")
    rows = read_records(run / "results.jsonl")
    index = {key(r): r for r in rows}
    requests = json.loads((run / "requests.json").read_bytes())
    changes = json.loads((run / "paired_changes.json").read_bytes())
    pairs = []
    for change in changes:
        if change["reference_outcome"] != labels[change["case_id"]]["reference_outcome"]:
            raise ValueError("Paired outcome differs from the frozen engineering label")
        candidate = index[key(change)]
        baseline = index[(change["case_id"], "hybrid", change["model"], change["repeat"])]
        first, second = [requests[r["request_identity"]] for r in (baseline, candidate)]
        if (
            first["messages"][0] != second["messages"][0]
            or first["options"] != second["options"]
            or first["model"] != second["model"]
        ):
            raise ValueError(
                "Judge model, options or system prompt changed across an evidence pair"
            )
        before, after = [payloads[(r["case_id"], r["method"])] for r in (baseline, candidate)]
        pairs.append(
            {
                **change,
                **compare_evidence(before, after),
                "baseline_request_identity": baseline["request_identity"],
                "candidate_request_identity": candidate["request_identity"],
                "baseline_answer": baseline.get("answer"),
                "candidate_answer": candidate.get("answer"),
                "baseline_status": baseline["status"],
                "candidate_status": candidate["status"],
                "candidate_failure": candidate.get("error"),
                "unaccepted_candidate_content": candidate.get("raw_response", {})
                .get("message", {})
                .get("content")
                if candidate["status"] != "completed"
                else None,
                "independent_support_review": "pending",
            }
        )
    data = {
        "run_identity": plan["identity"],
        "run_artifacts": run_pins,
        "retrieval_artifacts": retrieval_pins,
        "labels_sha256": file_hash(labels_path),
        "reporter_sha256": file_hash(__file__),
        "model_calls": 0,
    }
    output.mkdir(parents=True)
    write_json(output / "manifest.json", {**data, "identity": digest(data)})
    write_json(output / "pairs.json", pairs)
    write_json(
        output / "summary.json",
        {
            "pairs": len(pairs),
            "cases": len({r["case_id"] for r in pairs}),
            "changes": dict(Counter(r["change"] for r in pairs)),
            "new_model_calls": 0,
            "clinical_review": "pending",
        },
    )
    guide = root / corpus["source_path"]
    if file_hash(guide) != corpus["document_sha256"]:
        raise ValueError("Original PDF identity changed")
    shutil.copyfile(guide, output / "evidence_guide.pdf")
    render(output, pairs, payloads)
    write_json(
        output / "artifacts.json", {p.name: file_hash(p) for p in output.iterdir() if p.is_file()}
    )
    return {"pairs": len(pairs), "model_calls": 0}


def render(output, pairs, payloads):
    cards = []
    for row in pairs:
        panels = []
        for side, method in (("baseline", "hybrid"), ("candidate", row["method"])):
            sources = payloads[(row["case_id"], method)]["guideline_evidence"]
            evidence = "".join(
                f"<details><summary>{rank}. {escape(u['source_id'])}</summary><p>Section {escape(str(u['section']))} · "
                f"PDF {u['pdf_page']} · Printed page {u['printed_page']} · "
                f'<a href="evidence_guide.pdf#page={u["pdf_page"]}">Original PDF</a></p><pre>{escape(u["source_text"])}</pre></details>'
                for rank, u in enumerate(sources, 1)
            )
            answer = json.dumps(row[side + "_answer"], indent=2)
            panels.append(
                f"<div><h3>{method}</h3><p>{row[side + '_status']}</p><pre>{escape(answer)}</pre>{evidence}</div>"
            )
        facts = {
            k: v
            for k, v in payloads[(row["case_id"], "hybrid")].items()
            if k != "guideline_evidence"
        }
        audit = {
            k: row[k]
            for k in (
                "added_source_ids",
                "removed_source_ids",
                "common_source_rank_changes",
                "baseline_request_identity",
                "candidate_request_identity",
            )
        }
        cards.append(
            f'<article data-case="{escape(row["case_id"])}" data-model="{row["model"]}" data-method="{row["method"]}" data-repeat="{row["repeat"] + 1}" data-change="{row["change"]}">'
            f"<h2>{escape(row['case_id'])} / {row['model']} / {row['method']} / repeat {row['repeat'] + 1}</h2>"
            f"<p><strong>{row['change']}</strong> · Engineering reference: {row['reference_outcome']}</p>"
            f"<details><summary>Identical patient facts and original note</summary><pre>{escape(json.dumps(facts, ensure_ascii=False, indent=2))}</pre></details>"
            f'<div class="pair">{"".join(panels)}</div><details><summary>Evidence additions, removals and order changes</summary><pre>{escape(json.dumps(audit, indent=2))}</pre></details>'
            f"<p>{escape(row.get('candidate_failure') or '')}</p><pre>{escape(row.get('unaccepted_candidate_content') or '')}</pre></article>"
        )
    filters = "".join(
        f'<label>{name.title()} <select id="{name}"><option value="">All</option>'
        + "".join(
            f"<option>{escape(str(value))}</option>"
            for value in sorted(
                {
                    r["case_id"]
                    if name == "case"
                    else r["repeat"] + 1
                    if name == "repeat"
                    else r[name]
                    for r in pairs
                }
            )
        )
        + "</select></label>"
        for name in ("case", "model", "method", "repeat", "change")
    )
    html = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Evidence changes and judgments | Occupational Fitness Platform</title>
<style>body{font:14px/1.65 Arial,sans-serif;background:#f4f6f8;color:#243748;margin:0}main{max-width:1260px;margin:36px auto;padding:0 24px}header,article,section{background:white;padding:24px;border:1px solid #dce3ea;border-radius:8px;margin:20px 0}.pair{display:grid;grid-template-columns:1fr 1fr;gap:24px}.pair>div{min-width:0}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f6f8fb;padding:14px;font:12px/1.6 Consolas,monospace}summary{cursor:pointer;padding:8px 0}label{display:inline-block;margin:8px 16px 8px 0}select{padding:8px}a{color:#225b83}h2{font-size:19px}h3{font-size:17px}[hidden]{display:none}@media(max-width:800px){.pair{grid-template-columns:1fr}}</style><main><header><p>OCCUPATIONAL FITNESS PLATFORM · EVIDENCE TO JUDGMENT</p><h1>What changed in the evidence and the judgment?</h1>
<p>Identical patient facts, model, options and system prompt. The evidence bundle and its order differ. This does not isolate the causal contribution of one passage or position. Engineering reference agreement is not clinical accuracy; independent support review is pending.</p><p>Completed frozen comparison; three independent calls per model/method. Pilot and full-run completion remain separate. No new model calls were made by this analysis. <a href="pairs.json">Exact paired records</a> · <a href="manifest.json">Input versions</a></p></header><section>"""
    html += filters + '<p id="count"></p></section>' + "".join(cards)
    html += """</main><script>const keys=['case','model','method','repeat','change'];function filter(){let n=0;document.querySelectorAll('article').forEach(a=>{a.hidden=keys.some(k=>document.getElementById(k).value&&a.dataset[k]!==document.getElementById(k).value);if(!a.hidden)n++});document.getElementById('count').textContent=n+' paired records shown'}document.getElementById('method').value='planned_hybrid';document.getElementById('repeat').value='1';const model=document.getElementById('model');for(const o of model.options){if(o.value.startsWith('qwen'))model.value=o.value}keys.forEach(k=>document.getElementById(k).addEventListener('change',filter));filter();</script></html>"""
    (output / "index.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", default="outputs/experiments/seven_method_judgment_pilot_v1")
    parser.add_argument("--retrieval", default="outputs/experiments/seven_method_retrieval_v1")
    parser.add_argument(
        "--labels",
        default="outputs/experiments/retrieval_judgment_preparation_v2/scoring_labels.json",
    )
    parser.add_argument("--output", default="outputs/experiments/seven_method_judgment_evidence_v1")
    args = parser.parse_args()
    print(json.dumps(build(Path.cwd(), args.run, args.retrieval, args.labels, args.output)))
