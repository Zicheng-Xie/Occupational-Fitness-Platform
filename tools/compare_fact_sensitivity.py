"""Compare completed fact versions with exactly held original evidence and judge code."""

import argparse
import csv
import json
from collections import Counter, defaultdict
from html import escape
from pathlib import Path

from occupational_fitness_rag.evaluation import applicability_comparison as experiment
from occupational_fitness_rag.evaluation import passage_comparison as previous
from occupational_fitness_rag.provenance import digest, sha256_bytes, write_json


def completed(directory):
    directory = Path(directory)
    if (directory / ".run.lock").exists():
        raise ValueError("Stop the experiment writer before comparing fact versions")
    raw = (directory / "results.jsonl").read_bytes()
    if not raw.endswith(b"\n"):
        raise ValueError("Incomplete JSONL tail")
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    manifest = json.loads((directory / "manifest.json").read_bytes())
    audit = json.loads((directory / "execution_audit.json").read_bytes())
    snapshot = json.loads((directory / "source_snapshot.json").read_bytes())
    identity_fields = (
        "config",
        "config_sha256",
        "sources_sha256",
        "upstream_fingerprints",
        "environment",
        "planned_keys",
    )
    keys = [previous.condition_key(row) for row in rows]
    if (
        len(keys) != len(set(keys))
        or set(keys) != {tuple(key) for key in manifest["planned_keys"]}
        or sha256_bytes(raw) != audit["results_sha256"]
        or sha256_bytes((directory / "manifest.json").read_bytes()) != audit["manifest_sha256"]
        or digest(snapshot) != manifest["sources_sha256"]
        or digest({key: manifest[key] for key in identity_fields}) != manifest["identity"]
        or sha256_bytes(snapshot["config_text"].encode("utf-8")) != manifest["config_sha256"]
    ):
        raise ValueError("Completed experiment identity or planned keys differ")
    # Revalidate selected inputs, accepted answers and complete attempt costs.
    frozen = experiment.load_retrieval(manifest["config"])
    if frozen["fingerprints"] != manifest["upstream_fingerprints"]:
        raise ValueError("Upstream freeze changed since inference")
    experiment.validate_saved_rows(rows, manifest, frozen)
    return {
        "rows": rows,
        "manifest": manifest,
        "source": snapshot,
        "raw_sha256": sha256_bytes(raw),
        "frozen": frozen,
    }


def compare_pair(before, after, case):
    if previous.condition_key(before) != previous.condition_key(after):
        raise ValueError("Fact versions must share the exact model/case/policy/protocol/repeat")
    if (
        before["model_digest"] != after["model_digest"]
        or before["reference_outcome"] != after["reference_outcome"]
    ):
        raise ValueError("Judge revision or engineering reference changed")
    left, right = before["input_snapshot"], after["input_snapshot"]
    if (
        digest(left) != before["input_sha256"]
        or digest(right) != after["input_sha256"]
        or previous.patient_identity(left) != case["original_patient_identity"]
        or previous.patient_identity(right) != case["sensitivity_patient_identity"]
        or left["verified_patient_facts"] != case["original_verified_patient_facts"]
        or right["verified_patient_facts"] != case["sensitivity_verified_patient_facts"]
        or {k: v for k, v in left.items() if k != "verified_patient_facts"}
        != {k: v for k, v in right.items() if k != "verified_patient_facts"}
    ):
        raise ValueError("Paired inputs changed beyond the pinned source-literal facts")
    a, b = before["status"] == "completed", after["status"] == "completed"
    if a and b:
        status = {
            (False, True): "accepted_wrong_to_correct",
            (True, False): "accepted_correct_to_wrong",
            (True, True): "accepted_both_correct",
            (False, False): "accepted_both_wrong",
        }[(before["reference_agreement"], after["reference_agreement"])]
    else:
        status = {
            (False, True): "failed_to_valid",
            (True, False): "valid_to_failed",
            (False, False): "both_failed",
        }[a, b]
    return {
        **{key: before[key] for key in previous.KEY_FIELDS},
        "transition": status,
        "engineering_reference": before["reference_outcome"],
        "before_status": before["status"],
        "after_status": after["status"],
        "before_outcome": before.get("answer", {}).get("assessment_outcome"),
        "after_outcome": after.get("answer", {}).get("assessment_outcome"),
        "before_agreement": before["reference_agreement"],
        "after_agreement": after["reference_agreement"],
        "before_input_sha256": before["input_sha256"],
        "after_input_sha256": after["input_sha256"],
        "evidence_sha256": digest(left["guideline_evidence"]),
        "changed_fields": [item["field"] for item in case["changes"]],
    }


def metrics(rows):
    return {
        "conditions": len(rows),
        "distinct_cases": len({row["case_id"] for row in rows}),
        "completed": sum(row["status"] == "completed" for row in rows),
        "correct": sum(row["reference_agreement"] for row in rows),
        "engineering_reference_agreement": sum(row["reference_agreement"] for row in rows)
        / len(rows),
        **experiment.classification_metrics(rows, "answer", "status"),
    }


def validate_held_origin(before_frozen, after_frozen, snapshot):
    """Bind a fact-only experiment to its exact historical query and vector records."""
    original, updated = before_frozen["upstream_snapshot"], after_frozen["upstream_snapshot"]
    origin = original["manifest.json"]["identity"]
    derivation = updated["manifest.json"].get("derivation", {})
    if (
        origin != snapshot["metadata"]["retrieval_identity"]
        or derivation.get("kind") != "source_literal_fact_sensitivity_with_held_evidence"
        or derivation.get("original_retrieval_identity") != origin
        or derivation.get("fact_snapshot_identity") != snapshot["identity"]
        or derivation.get("retrieval_executed") is not False
        or derivation.get("new_retrieval_calls") != 0
        or derivation.get("new_embedding_calls") != 0
        or original["retrieval.json"]["records"] != updated["retrieval.json"]["records"]
        or original["embeddings.json"]["vectors"] != updated["embeddings.json"]["vectors"]
        or original["corpus.json"] != updated["corpus.json"]
    ):
        raise ValueError("Sensitivity is not bound to the unchanged historical retrieval origin")


def compare(before_dir, after_dir, snapshot_path):
    from tools.build_source_literal_facts import load_snapshot

    before_dir, after_dir = Path(before_dir).resolve(), Path(after_dir).resolve()
    if before_dir == after_dir:
        raise ValueError("Fact versions require different completed experiment directories")
    before, after = completed(before_dir), completed(after_dir)
    snapshot = load_snapshot(snapshot_path, Path(__file__).resolve().parents[1])
    validate_held_origin(before["frozen"], after["frozen"], snapshot)
    if before["raw_sha256"] == after["raw_sha256"]:
        raise ValueError("Raw result clones cannot establish a fact sensitivity")
    if before["source"]["first_party_source"] != after["source"]["first_party_source"]:
        raise ValueError("Judge implementation changed between fact versions")
    if any(
        before["source"][key] != after["source"][key]
        for key in ["python", "platform", "dependencies"]
    ):
        raise ValueError("Python, platform or dependency revisions changed")
    if before["manifest"]["environment"] != after["manifest"]["environment"]:
        raise ValueError("Runtime or installed model revision changed")
    for field in [
        "models",
        "evidence_policies",
        "protocols",
        "repeats",
        "context_length",
        "output_tokens",
        "prompt_max_bytes",
        "request_max_bytes",
        "evidence_max_bytes",
        "top_k",
        "sensitivity_k",
        "max_validation_repairs",
    ]:
        if before["manifest"]["config"][field] != after["manifest"]["config"][field]:
            raise ValueError("Compared judge or evidence budget changed: " + field)
    changed = {key for key, value in snapshot["cases"].items() if value["changes"]}
    if set(after["manifest"]["config"]["case_ids"]) != changed:
        raise ValueError("Sensitivity must include all uniformly eligible changed cases")
    if after["manifest"]["config"].get("fact_snapshot_identity") != snapshot["identity"]:
        raise ValueError("Sensitivity config does not pin this fact version")
    left = {previous.condition_key(row): row for row in before["rows"]}
    pairs, selected, by_key = [], [], {}
    for row in after["rows"]:
        key = previous.condition_key(row)
        if key not in left:
            raise ValueError("Missing matching original-fact condition")
        pair = compare_pair(left[key], row, snapshot["cases"][row["case_id"]])
        pairs.append(pair)
        selected.append(left[key])
        by_key[key] = (left[key], row)
    groups = defaultdict(list)
    for pair in pairs:
        groups[pair["model"], pair["evidence_policy"], pair["protocol"]].append(pair)
    grouped = []
    for (model, policy, protocol), items in sorted(groups.items()):
        indices = [tuple(item[key] for key in previous.KEY_FIELDS) for item in items]
        grouped.append(
            {
                "model": model,
                "evidence_policy": policy,
                "protocol": protocol,
                "transitions": dict(Counter(item["transition"] for item in items)),
                "before": metrics([by_key[key][0] for key in indices]),
                "after": metrics([by_key[key][1] for key in indices]),
            }
        )
    report = {
        "before_results_sha256": before["raw_sha256"],
        "after_results_sha256": after["raw_sha256"],
        "before_identity": before["manifest"]["identity"],
        "after_identity": after["manifest"]["identity"],
        "fact_snapshot_identity": snapshot["identity"],
        "tool_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "pairs": pairs,
        "pair_count": len(pairs),
        "distinct_cases": len(changed),
        "transition_counts": dict(Counter(item["transition"] for item in pairs)),
        "before": metrics(selected),
        "after": metrics(after["rows"]),
        "groups": grouped,
        "clinical_review": "pending",
        "production_change": False,
        "interpretation": (
            "Source-literal fact availability sensitivity on previously seen engineering cases. "
            "Original retrieval queries, rankings and complete evidence texts are held fixed, not "
            "rerun. Labels and judge code are unchanged. Temperature zero does not guarantee identical "
            "outputs; separate runs retain stochastic and order effects. Original notes include "
            "engineered assertions and cannot establish independent clinical validity."
        ),
    }
    write_json(after_dir / "fact_sensitivity_analysis.json", report)
    with (after_dir / "fact_transitions.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        fields = [key for key in pairs[0] if key != "changed_fields"] + ["changed_fields_json"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(
            {
                **{k: v for k, v in pair.items() if k != "changed_fields"},
                "changed_fields_json": json.dumps(pair["changed_fields"]),
            }
            for pair in pairs
        )
    cards = []
    for pair in pairs:
        key = tuple(pair[field] for field in previous.KEY_FIELDS)
        old, new = by_key[key]
        case = snapshot["cases"][pair["case_id"]]
        changes = [
            {
                "field": item["field"],
                "frozen": item["frozen"],
                "restored": item["restored"],
                "literal_spans": item["literal_spans"],
                "review_status": item["review_status"],
            }
            for item in case["changes"]
        ]
        columns = "".join(
            f"<section><h3>{title}</h3><p>{escape(row.get('answer', {}).get('assessment_outcome', 'RUN_FAILURE'))}</p>"
            f"<p>{escape(row.get('answer', {}).get('explanation', row.get('error', '')))}</p>"
            f"<details><summary>Final evidence checks</summary><pre>{escape(json.dumps(row.get('answer', {}).get('criterion_checks', []), indent=2))}</pre></details></section>"
            for title, row in [
                ("Original quarantined facts", old),
                ("Source-literal sensitivity", new),
            ]
        )
        evidence = "".join(
            f"<details><summary>{escape(source['source_id'])} · Section {escape(source['section'])} · PDF {source['pdf_page']}</summary><blockquote>{escape(source['source_text'])}</blockquote></details>"
            for source in old["input_snapshot"]["guideline_evidence"]
        )
        cards.append(
            f'<article data-case="{escape(pair["case_id"])}" data-model="{escape(pair["model"])}" data-transition="{pair["transition"]}">'
            f"<h2>{escape(pair['case_id'])} · {escape(pair['model'])}</h2>"
            f"<p>{escape(pair['evidence_policy'])} / {escape(pair['protocol'])} · Repeat {pair['repeat'] + 1} · {pair['transition']}</p>"
            f'<p>Engineering reference: {escape(pair["engineering_reference"])}</p><div class="pair">{columns}</div>'
            f"<details><summary>Exact fact-version changes (clinical review pending)</summary><pre>{escape(json.dumps(changes, indent=2))}</pre></details>"
            f"<details><summary>Identical original evidence in both conditions</summary>{evidence}</details></article>"
        )
    selectors = "".join(
        f'<label>{name}<select data-field="{name}"><option value="">All</option>'
        + "".join(
            f'<option value="{escape(str(value), quote=True)}">{escape(str(value))}</option>'
            for value in sorted({item[field] for item in pairs})
        )
        + "</select></label>"
        for name, field in [("case", "case_id"), ("model", "model"), ("transition", "transition")]
    )
    html = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fact availability sensitivity | Occupational Fitness Platform</title><style>body{font:14px/1.6 system-ui;color:#203648;background:#f5f7f9;margin:32px auto;max-width:1400px;padding:20px}article{background:white;border:1px solid #dbe3e9;padding:24px;margin:20px 0;border-radius:8px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:24px}pre,blockquote{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f6f9;padding:14px}select{display:block;padding:8px}label{display:inline-block;margin:12px}h2{font-size:18px}summary{cursor:pointer}article[hidden]{display:none}@media(max-width:800px){.pair{grid-template-columns:1fr}}</style><h1>Fact availability sensitivity</h1>'
    html += f"<p>{len(pairs)} paired conditions · {len(changed)} distinct cases · {snapshot['metadata']['restored_field_count']} source-literal fields across the case set</p><p>{escape(report['interpretation'])}</p>"
    html += "<pre>" + escape(json.dumps(report["transition_counts"], indent=2)) + "</pre>"
    html += selectors + "".join(cards)
    html += '<p><a href="fact_sensitivity_analysis.json">Paired data and metrics</a> · <a href="fact_transitions.csv">Transitions CSV</a> · <a href="review.html">Stage-level report</a></p><script>function f(){let s=[...document.querySelectorAll("select")];document.querySelectorAll("article").forEach(a=>a.hidden=s.some(x=>x.value&&a.dataset[x.dataset.field]!==x.value))}document.querySelectorAll("select").forEach(x=>x.addEventListener("change",f));</script></html>'
    (after_dir / "fact_sensitivity.html").write_text(html, encoding="utf-8")
    return {
        key: report[key]
        for key in ["pair_count", "distinct_cases", "transition_counts", "before", "after"]
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--before", default="outputs/experiments/applicability_comparison_full33_original"
    )
    parser.add_argument("--after", default="outputs/experiments/applicability_fact_sensitivity_v1")
    parser.add_argument(
        "--snapshot",
        default="outputs/experiments/source_literal_facts_v1/source_literal_facts.json",
    )
    args = parser.parse_args()
    print(json.dumps(compare(args.before, args.after, args.snapshot), indent=2))
