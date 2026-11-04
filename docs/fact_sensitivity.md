# Source-literal fact availability sensitivity

This experiment separates an upstream fact-availability problem from retrieval and
judgment problems. It is an engineering sensitivity analysis on previously inspected
synthetic cases. It does not promote a value into production, change a reference
label, certify a clinical interpretation or rerun retrieval.

## Fixed and changed dimensions

The original condition imports the 33-case, 94-unit preparation in
`outputs/experiments/passage_comparison_full_clean`. Its frozen patient inputs include
fields withheld by the earlier semantic review. The separate source-literal condition
uses exactly the same notes, requested modules, licence context, original evidence,
historical queries, rankings and evidence length limits. Only
`verified_patient_facts` changes.

The eligibility rule is applied to every changed field, before inspecting a new
judgment. A field is eligible only when its original addendum contains a non-null
finite JSON scalar, every explicit assignment agrees with the same exact value and
Python type, the prior extraction agrees with that literal, its previous source spans
match, and the original frozen state matches the change ledger. Boolean `false` is
different from numeric zero and from the string `"false"`. Unicode offsets refer to
UTF-8 decoded text after BOM removal, preserving original CRLF/LF newlines.

The uniform rule admits **41 case-field values in 13 cases**. The remaining **three
changed fields** have no explicit addendum literal and stay withheld. All 33 original
patient records are retained in the snapshot; only the 13 changed cases require new
model calls for this paired sensitivity. Original quarantine reasons and complete
semantic-review records remain attached to the snapshot. Clinical review is pending.

Several original fixtures explicitly state that screening was complete, conditional
criteria were satisfied or a particular chronic-insulin pathway should not apply.
Both arms retain this wording. These are not blinded natural patient records, and
the resulting agreement cannot establish independent clinical generalization.

## Artifact boundaries

`tools/build_source_literal_facts.py` builds and deterministically revalidates the
snapshot. It does not choose fields by engineering outcome. The snapshot records
original and sensitivity patient identities, values, exact quotations, source file
hashes, line/character spans, the eligibility decision and pending review status.

`tools/build_fact_sensitivity_retrieval.py` creates a **separate read-only preparation**.
Its 99 prepared payloads retain the original three evidence policies. Exactly 39
payloads change, corresponding to 13 eligible cases across three policies; 60 remain
unchanged. Each changed payload differs only in its facts. All original source
passages remain complete and exact. The historical 154 retrieval records and
embedding vectors are retained with explicit historical identities and zero new
calls. Their original timing is historical data, not newly executed retrieval cost.

The derived freeze has its own identity binding the fact snapshot, builder source,
original artifact hashes and complete transformed inputs. It must not be described
as evidence retrieved using the restored facts. A later end-to-end comparison must
rebuild queries and retrieval as a distinct intervention and supply the same fact
version to every retrieval method.

## Locked judgment matrices

| Condition | Cases | Models | Evidence policies | Judgment protocols | Repeats | Planned conditions |
|---|---:|---:|---:|---:|---:|---:|
| Original frozen facts | 33 | 2 | 2 | 2 | 3 | 792 |
| Source-literal sensitivity | 13 changed | 2 | 2 | 2 | 3 | 312 |

The initial broader replay was stopped after **100/792 recorded conditions** when
a deterministic materialization defect appeared. Its 97 accepted outputs and three
failures, 149 recorded provider calls and interruption audit remain unchanged in
`applicability_comparison_full33_original`. Work in the interrupted in-flight
condition was not fully journaled and its additional cost is unknown. This partial
run must not be counted as a completed comparison.

The defect capped the program-derived union of direct and prerequisite references
at eight, even though the model's individual lists legally allowed eight each. The
fixed derived bound is 48 (eight direct plus five prerequisites with eight each).
The model-written component limits, prompts, fact provenance checks and original
text remain unchanged. All three saved failing first responses now parse with ten
distinct references and identical first-request hashes; their old failed final
conditions are not retroactively accepted. Fresh `*_v2.yaml` configurations and
fresh result directories bind the fixed package under revision
`program_bound_slots_union_v3`.

The v2 live regression then exposed the same limit in the subsequent provenance
bridge: `review_locations` converted an internal ledger into a model-written final
proposal. The v2 prefix stopped at **81/792 conditions** (78 accepted, three failed,
117 recorded calls). Its interruption and unknown in-flight costs remain separate.
The complete fix resolves internal references directly against the immutable source
catalogue, retaining source/module/field checks, exact original text, Unicode spans
and copied mutable fields. It no longer fabricates an overall outcome merely to
materialize source locations. Final model-written checks still have an eight-field
limit.

`tools/replay_applicability_materialization.py` replays all 88 historical first
responses through parsing, source materialization and aggregation request building,
including six failed conditions from the two prefixes. Existing accepted locations
and initial requests remain identical. This is offline regression evidence, not
six newly accepted judgments. The next gate is the 12-condition, two-model SYN006
pilot in `applicability_provenance_pilot_v3.yaml`. Fresh full/sensitivity `*_v3.yaml`
configurations use `program_bound_slots_provenance_v4` only after that gate passes.

That actual pilot completed **12/12 conditions and 18/18 provider calls**, with all
accepted raw stage outputs reparsed and source/runtime pins verified. Llama's three
two-stage responses retained ten resolved references each; Qwen selected five, all
resolved without clipping. This passes the **execution gate only**. On this one
previously inspected case, Llama agreed with the reference in 0/3 calls under each
protocol, while Qwen moved from 3/3 single-call agreements to 0/3 two-stage agreements.
Those three accepted regressions remain recorded. They are not removed, reclassified
as provider failure or used to retune the prompt before the broader locked replay.
The pilot does not establish a semantic benefit or justify a production switch.

The evidence policies are actual hybrid RRF with the already frozen module query,
and separately selected reference evidence. Reference evidence is an upper-context
diagnostic control rather than an ordinary retrieval method. Judgment protocols are
single-call `passage_selection` and two-stage `applicability_first`. These conditions
do not constitute a new six-retriever comparison. Both stages, failed attempts and
bounded structural repairs count toward costs.

Model revisions, Ollama version, context/output limits, temperature and seed are
explicitly pinned by configuration. Models run serially. Temperature zero does not
guarantee identical repeated outputs. The original and sensitivity matrices execute
at different times, so order and residual nondeterminism remain possible.

```powershell
.venv/Scripts/python.exe -m tools.build_source_literal_facts
.venv/Scripts/python.exe -m tools.build_fact_sensitivity_retrieval
.venv/Scripts/python.exe -m occupational_fitness_rag.evaluation.applicability_comparison --config configs/experiments/applicability_provenance_pilot_v3.yaml
.venv/Scripts/python.exe -m occupational_fitness_rag.evaluation.applicability_comparison --config configs/experiments/applicability_comparison_full33_original_v3.yaml
.venv/Scripts/python.exe -m occupational_fitness_rag.evaluation.applicability_comparison --config configs/experiments/applicability_fact_sensitivity_v3.yaml
```

Run the matrices serially. Existing outputs require unchanged-source `--resume`;
changed configurations or package contents require a new experiment directory.
Frozen historical preparations are imported through explicit verified identities;
their old manifests are never rebound to current source code.

## Analysis and remaining validation

`tools/audit_applicability_execution.py` reparses accepted raw model responses and
checks complete planned keys, provenance, source/config/runtime identities and costs.
`tools/compare_fact_sensitivity.py` then pairs each of the 312 sensitivity conditions
with its corresponding original condition and rejects changes to evidence, notes,
reference, judge implementation, model, repeat or budgets. It reports accepted
wrong-to-correct and correct-to-wrong transitions separately from recovered failures.

`tools/analyze_applicability_cohorts.py` separates engineering/complex cohorts, the
eight protocol-development cases, remaining cases and upstream-discrepancy strata.
Multi-module fixtures have overall references; module slices are not independently
labelled disease-specific accuracy. Five-class confusion matrices retain failures as
missed references. Report class counts, per-class recall, Macro-F1 and the
always-insufficient baseline alongside aggregate engineering reference agreement.

`tools/audit_applicability_disagreements.py` prioritizes final conditional-permission
claims whose same passage was marked uncertain/inapplicable or had unmet/unknown
prerequisites in stage one. Both stages can be wrong. These flags are review leads,
not an automatic truth test or a correction policy. The review worksheet hides
reference outcomes, preserves original text and retains human annotations.

Independent source-support review, clinician-approved labels, newly held-out cases,
and a refreshed six-method retrieval/judgment comparison remain separate requirements.
Engineering reference agreement and source-identifier validity must not be labelled
clinical accuracy or demonstrated explanation support.
