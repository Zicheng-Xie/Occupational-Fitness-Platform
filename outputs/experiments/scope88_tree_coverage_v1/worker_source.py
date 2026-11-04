"""Native PageIndex replay and RRF-seeded tree coverage on the reviewed corpus.

The pure-tree control retains the prior strict available-count policy. Two
explicit hybrid ablations broaden actual native branches with real RRF seeds.
They are first-party navigators over a native index, not native PageIndex chat.
No reference labels, rule outcomes or expected source IDs are read here.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.metadata
import json
from copy import deepcopy
from pathlib import Path
from time import perf_counter

from tools import pageindex_extension_worker as native
from tools.run_pageindex_strict_cardinality import parse_strict

METHODS = (
    "pageindex_tree_adapter",
    "pageindex_rrf_branch_coverage",
    "pageindex_rrf_predicate_navigation",
)
PREDICATE_INSTRUCTION = (
    " Match the query's documented predicates, negations and temporal state. "
    "Do not treat an unknown finding as present. Distinguish investigation still "
    "pending from an undetermined cause after completed investigation; current "
    "acute instability from routine long-term management; and commercial "
    "conditions from general background. Rank applicable original criteria "
    "together with their qualifications and exceptions."
)


def read(path):
    return json.loads(Path(path).read_bytes())


def verify_files(folder):
    folder = Path(folder).resolve()
    pins = read(folder / "artifacts.json")
    if not pins:
        raise ValueError("Missing frozen artifact inventory")
    for name, expected in pins.items():
        path = (folder / name).resolve()
        if not path.is_relative_to(folder) or native.file_hash(path) != expected:
            raise ValueError("Frozen source changed: " + str(path))
    return pins


def normalized_branch(raw, body, field, allowed, config):
    value = json.loads(raw["message"]["content"])
    if not isinstance(value, dict) or set(value) != {field}:
        raise ValueError("Branch output contract differs")
    ids = value[field]
    if not isinstance(ids, list) or any(not isinstance(n, str) or n not in allowed for n in ids):
        raise ValueError("Unknown native branch ID")
    unique = list(dict.fromkeys(ids))
    copy = deepcopy(raw)
    copy["message"]["content"] = json.dumps({field: unique})
    native.parse_selection(copy, body, field, allowed, config)
    return unique, {
        "raw_ids": ids,
        "normalized_ids": unique,
        "duplicates_removed": len(ids) - len(unique),
    }


def ranking_body(query, mapping, units, config, selected, seeds=None, predicate=False):
    if seeds is None:
        body, field, allowed, excluded = native.request_body(
            query, mapping, units, config, "originals", selected
        )
        source_order = [
            s["source_id"] for s in json.loads(body["messages"][1]["content"])["originals"]
        ]
        branches = list(selected)
    else:
        leaves = mapping["leaves"]
        by_source = {leaf["source_id"]: nid for nid, leaf in leaves.items()}
        if not seeds or len(seeds) != len(set(seeds)) or any(s not in by_source for s in seeds):
            raise ValueError("Hybrid tree seeds must be actual same-module RRF sources")
        seed_nodes = {by_source[s] for s in seeds}
        branches = list(
            dict.fromkeys(
                [
                    *selected,
                    *[
                        b["node_id"]
                        for b in mapping["branches"]
                        if seed_nodes.intersection(b["leaf_node_ids"])
                    ],
                ]
            )
        )
        branch_map = {b["node_id"]: b for b in mapping["branches"]}
        ids = list(
            dict.fromkeys(
                [
                    *[by_source[s] for s in seeds],
                    *[nid for bid in branches for nid in branch_map[bid]["leaf_node_ids"]],
                ]
            )
        )
        sources, excluded = [], []
        for nid in ids:
            leaf = leaves[nid]
            source = {**leaf, "original_text": units[leaf["source_id"]]["evidence_text"]}
            if (
                len(json.dumps([*sources, source], ensure_ascii=False).encode())
                > config["candidate_max_bytes"]
            ):
                excluded.append(nid)
            else:
                sources.append(source)
        if not sources:
            raise ValueError("No whole original survives the hybrid navigation budget")
        body, field, _, _ = native.request_body(
            query, mapping, units, config, "originals", selected
        )
        data = {
            "module": query["module"],
            "licence_context": "commercial",
            "query": query["query"],
            "originals": sources,
        }
        body["messages"][1]["content"] = json.dumps(data, ensure_ascii=False, allow_nan=False)
        allowed = {s["node_id"] for s in sources}
        body["format"]["properties"][field]["items"]["enum"] = sorted(allowed)
        source_order = [s["source_id"] for s in sources]
    target = min(config["top_k"], len(allowed))
    body["format"]["properties"][field].update(minItems=target, maxItems=target)
    if predicate:
        body["messages"][0]["content"] += PREDICATE_INSTRUCTION
    return body, field, allowed, excluded, source_order, branches


def call(output, query, body, field, allowed, config, phase):
    prior = [
        c
        for c in native.read_records(output / "model_calls.jsonl")
        if c["query_id"] == query["query_id"] and c["phase"] == phase
    ]
    if prior:
        if len(prior) != 1 or prior[0]["request"] != body:
            raise ValueError("A resumed native condition has repeated or changed requests")
        record = prior[0]
        if record["status"] != "completed":
            raise ValueError("Retained prior call failure: " + record.get("error", "unknown"))
        selected, _ = (
            normalized_branch(record["raw_response"], body, field, allowed, config)
            if phase == "branches"
            else parse_strict(record["raw_response"], body, field, allowed, config)
        )
        return selected, record
    started = perf_counter()
    record = {
        **{k: query[k] for k in ("query_id", "case_id", "module")},
        "phase": phase,
        "request": body,
        "request_sha256": native.digest(body),
        "provider_called": True,
    }
    try:
        raw = native.local_json(config, "/api/chat", body)
        record["raw_response"] = raw
        selected, normalization = (
            normalized_branch(raw, body, field, allowed, config)
            if phase == "branches"
            else parse_strict(raw, body, field, allowed, config)
        )
        record.update(
            status="completed", selected_native_node_ids=selected, normalization=normalization
        )
        return selected, record
    except Exception as exc:
        record.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        record["seconds"] = perf_counter() - started
        with (output / "model_calls.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")


def imported_control(query, old_qid, mapping, units, config, parent_rows, parent_calls):
    """Reuse an unchanged module's actual v4 policy; never reinterpret changed context."""
    row = parent_rows[old_qid]
    body, field, allowed, _ = native.request_body(query, mapping, units, config, "branches")
    matches = [c for c in parent_calls if c["query_id"] == old_qid and c["phase"] == "branches"]
    if len(matches) != 1 or matches[0]["request"] != body:
        raise ValueError("Unchanged-module branch request is not byte-equivalent")
    branches, _ = normalized_branch(matches[0]["raw_response"], body, field, allowed, config)
    if branches != row["selected_branch_node_ids"]:
        raise ValueError("Imported actual branch choice differs")
    expected, field, allowed, _, _, _ = ranking_body(query, mapping, units, config, branches)
    matches_rank = []
    for c in parent_calls:
        if c["query_id"] != old_qid or c["phase"] == "branches" or c.get("status") != "completed":
            continue
        actual = c["request"]
        comparable = deepcopy(actual)
        comparable["format"]["properties"][field]["minItems"] = expected["format"]["properties"][
            field
        ]["minItems"]
        comparable["format"]["properties"][field]["maxItems"] = expected["format"]["properties"][
            field
        ]["maxItems"]
        if comparable != expected:
            continue
        try:
            ids, _ = parse_strict(c["raw_response"], expected, field, allowed, config)
        except ValueError:
            continue  # Historical underfilled attempts remain in their parent run.
        if ids == row["selected_leaf_node_ids"]:
            matches_rank.append(c)
    if not matches_rank:
        raise ValueError("Imported control lacks its full actual native ranking response")
    ranked_call = matches_rank[-1]
    ids = [mapping["leaves"][n]["source_id"] for n in row["selected_leaf_node_ids"]]
    if ids != row["source_ids"] or row["status"] != "completed":
        raise ValueError("Imported control source identities differ")
    return row, [matches[0], ranked_call]


def run(root, shared, output, index_only=False, resume=False):
    root, shared, output = [Path(p).resolve() for p in (root, shared, output)]
    if not output.is_relative_to(root / "outputs/experiments"):
        raise ValueError("Use experiment storage")
    shared_pins = verify_files(shared)
    corpus, queries = [read(shared / n) for n in ("corpus.json", "queries.json")]
    units = native.validate_inputs(corpus, queries)
    if len(units) != 88 or len(queries) != 77:
        raise ValueError("Expected the shared reviewed 88-source, 77-query inventory")
    if any(
        q["corpus_sha256"] != corpus["corpus_sha256"]
        or q["query_id"] != native.digest({k: v for k, v in q.items() if k != "query_id"})
        for q in queries
    ):
        raise ValueError("Actual query identities must bind the reviewed corpus")
    parent = root / "outputs/experiments/native_pageindex_retrieval_v4"
    parent_pins = verify_files(parent)
    prior = read(parent / "manifest.json")
    config = native.settings(prior["config"])
    if importlib.metadata.version("pageindex") != config["expected_pageindex_version"]:
        raise ValueError("Native PageIndex version differs")
    environment = native.runtime(config)
    anchor = read(shared / "anchor_candidates.json")
    if isinstance(anchor, dict) and "candidates" in anchor:
        anchor = anchor["candidates"]
    data = {
        "kind": "reviewed_corpus_native_tree_coverage",
        "shared_artifacts_sha256": native.file_hash(shared / "artifacts.json"),
        "parent_artifacts_sha256": native.file_hash(parent / "artifacts.json"),
        "corpus_sha256": corpus["corpus_sha256"],
        "config": config,
        "runtime": environment,
        "methods": list(METHODS),
        "candidate_policy": "Actual RRF Top20 first, then originals from model-selected and seed-linked native branches; whole-source 20000-byte cap",
        "promotion_candidate": METHODS[1],
        "predicate_variant_is_ablation": True,
        "source_sha256": native.file_hash(__file__),
        "native_worker_sha256": native.file_hash(native.__file__),
        "strict_parser_sha256": native.file_hash(
            root / "tools/run_pageindex_strict_cardinality.py"
        ),
        "reference_labels_available": False,
        "native_chat_retrieval_used": False,
    }
    identity = native.digest(data)
    manifest = {**data, "identity": identity, "production_change": False}
    if output.exists():
        if not resume or read(output / "manifest.json") != manifest:
            raise ValueError("Resume requires the exact frozen tree protocol")
        if (output / "artifacts.json").exists():
            verify_files(output)
            return read(output / "summary.json")
    else:
        output.mkdir(parents=True)
        native.save(output / "manifest.json", manifest)
        for name, value in (("corpus.json", corpus), ("queries.json", queries)):
            native.save(output / name, value)
        (output / "worker_source.py").write_bytes(Path(__file__).read_bytes())
    mappings = asyncio.run(native.build_index(output, units, config))
    if index_only:
        return {"identity": identity, "indexed_units": len(units), "model_calls": 0}
    parent_rows = {r["query_id"]: r for r in native.read_records(parent / "results.jsonl")}
    parent_calls = sum(
        [
            native.read_records(parent / n)
            for n in (
                "imported_v2_model_calls.jsonl",
                "imported_v3_model_calls.jsonl",
                "model_calls.jsonl",
            )
        ],
        [],
    )
    old_units = {u["source_id"]: u for u in read(parent / "corpus.json")["units"]}
    old_queries = read(parent / "queries.json")

    def query_content(q):
        return {k: v for k, v in q.items() if k not in {"query_id", "corpus_sha256"}}

    old_keys = {native.digest(query_content(q)): q["query_id"] for q in old_queries}
    if len(old_keys) != 77 or any(native.digest(query_content(q)) not in old_keys for q in queries):
        raise ValueError("Historical query lineage changes facts or literal query content")
    rows, imports = [], {}
    for query in queries:
        module, qid = query["module"], query["query_id"]
        mapping = mappings[module]
        unchanged = {s: u for s, u in units.items() if u["module"] == module} == {
            s: u for s, u in old_units.items() if u["module"] == module
        }
        branches, branch_failure = None, None
        if unchanged:
            old_qid = old_keys[native.digest(query_content(query))]
            control, observed = imported_control(
                query, old_qid, mapping, units, config, parent_rows, parent_calls
            )
            branches = control["selected_branch_node_ids"]
            for c in observed:
                imports[native.digest(c)] = c
            control = {
                **control,
                "method": METHODS[0],
                "experiment_identity": identity,
                "query_id": qid,
                "historical_query_id": old_qid,
                "imported_result_sha256": native.digest(control),
                "new_retrieval_seconds": 0.0,
                "actual_prior_calls_sha256": [native.digest(c) for c in observed],
            }
        else:
            control = {k: query[k] for k in ("query_id", "case_id", "module")}
            control.update(
                method=METHODS[0], experiment_identity=identity, source_ids=[], status="failed"
            )
            try:
                body, field, allowed, _ = native.request_body(
                    query, mapping, units, config, "branches"
                )
                branches, _ = call(output, query, body, field, allowed, config, "branches")
                body, field, allowed, excluded, candidates, _ = ranking_body(
                    query, mapping, units, config, branches
                )
                selected, observed = call(output, query, body, field, allowed, config, METHODS[0])
                ids = [mapping["leaves"][n]["source_id"] for n in selected]
                control.update(
                    status="completed",
                    source_ids=ids,
                    selected_branch_node_ids=branches,
                    selected_leaf_node_ids=selected,
                    candidate_source_ids=candidates,
                    original_text_hashes={s: units[s]["text_sha256"] for s in ids},
                    excluded_native_nodes_by_navigation_budget=excluded,
                    new_retrieval_seconds=observed["seconds"],
                )
            except Exception as exc:
                control["error"] = f"{type(exc).__name__}: {exc}"
                if branches is None:
                    branch_failure = control["error"]
        rows.append(control)
        for method in METHODS[1:]:
            row = {k: query[k] for k in ("query_id", "case_id", "module")}
            row.update(method=method, experiment_identity=identity, source_ids=[], status="failed")
            try:
                if branches is None:
                    raise ValueError("Actual branch navigation failed: " + str(branch_failure))
                seeds = anchor[qid][:20]
                body, field, allowed, excluded, candidates, expanded = ranking_body(
                    query, mapping, units, config, branches, seeds, predicate=method == METHODS[2]
                )
                selected, observed = call(output, query, body, field, allowed, config, method)
                ids = [mapping["leaves"][n]["source_id"] for n in selected]
                row.update(
                    status="completed",
                    source_ids=ids,
                    selected_branch_node_ids=branches,
                    expanded_branch_node_ids=expanded,
                    actual_rrf_seed_ids=seeds,
                    selected_leaf_node_ids=selected,
                    candidate_source_ids=candidates,
                    original_text_hashes={s: units[s]["text_sha256"] for s in ids},
                    excluded_native_nodes_by_navigation_budget=excluded,
                    new_retrieval_seconds=observed["seconds"],
                )
            except Exception as exc:
                row["error"] = f"{type(exc).__name__}: {exc}"
            rows.append(row)
        print(
            f"Tree {query['case_id']}/{module}: " + ", ".join(r["status"] for r in rows[-3:]),
            flush=True,
        )
        (output / "results.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
        )
    calls = native.read_records(output / "model_calls.jsonl")
    for row in rows:
        if row["status"] == "completed" and (
            len(row["source_ids"]) != len(set(row["source_ids"]))
            or any(s not in units or units[s]["module"] != row["module"] for s in row["source_ids"])
        ):
            raise ValueError("Invalid returned original inventory")
    if (
        verify_files(shared) != shared_pins
        or verify_files(parent) != parent_pins
        or native.runtime(config) != environment
    ):
        raise ValueError("Frozen input or model identity changed")
    if native.file_hash(__file__) != data["source_sha256"]:
        raise ValueError("Frozen navigator implementation changed")
    (output / "imported_model_calls.jsonl").write_text(
        "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in imports.values()),
        encoding="utf-8",
    )
    summary = {
        "identity": identity,
        "planned": 77 * 3,
        "recorded": len(rows),
        "completed": sum(r["status"] == "completed" for r in rows),
        "failed": sum(r["status"] != "completed" for r in rows),
        "imported_actual_calls_used": len(imports),
        "new_actual_model_calls": len(calls),
        "new_call_seconds": sum(c["seconds"] for c in calls),
        "index_model_calls": 0,
        "scope_review_pending": True,
        "production_change": False,
    }
    native.save(output / "summary.json", summary)
    native.save(
        output / "artifacts.json",
        {
            p.relative_to(output).as_posix(): native.file_hash(p)
            for p in output.rglob("*")
            if p.is_file()
        },
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--shared", type=Path, default=Path("outputs/experiments/scope88_shared_retrieval_v2")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/experiments/scope88_tree_coverage_v1")
    )
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(Path.cwd(), args.shared, args.output, resume=args.resume), indent=2))
