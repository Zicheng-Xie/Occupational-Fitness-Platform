# Case-level evidence allocation and paired fitness judgments

This isolated experiment consumes the frozen 88-original retrieval comparison.
It preserves production extraction, semantic review, rule outcomes and retrieval
defaults. Previous experiments and completed reports are not rewritten.

## Allocation policy

The established allocator gives documented modules round-robin slots, with at
most five originals per patient. With five active modules, this can supply only
the first-ranked original from each module even when a later Top5 original
covers more relevant criteria.

The experimental `case_criterion_floor_exact_v1` policy:

1. Uses the union of the same active modules' actual Top5 originals. It performs
   no additional retrieval or label-based source supplementation.
2. Preserves the typed criteria covered by the baseline's actually supplied
   packet. Containment requires same-page literal original-text proof.
3. Enumerates subsets of at most five originals within the same 9,000-byte
   UTF-8 JSON budget. It maximizes represented modules, minimum module criterion
   coverage fraction, and total criterion coverage fraction, in that order.
4. Breaks ties by original retrieval rank and evidence bytes. It retains complete
   original passages and the existing module/rank presentation order.

False and zero remain documented values. Modules without documented facts stay
unresolved; when no module has a documented fact, the established fallback to
all requested modules remains. Corpus criterion coverage does not establish
patient-specific applicability or clinical entailment.

Across the same 45 source-labeled scopes in 33 observed development cases:

| Evidence arm | Actual case-packet original coverage |
|---|---:|
| Original Hybrid RRF / round robin | 80.74% |
| Seventh method / round robin | 82.22% |
| Seventh method / new case allocation | 86.67% |
| Ninth method / round robin | 84.44% |
| Ninth method / new case allocation | 84.44% |

These are evidence measurements, not fitness classification results. New
allocation changes model-visible packets in 22 seventh-route cases and 19
ninth-route cases. It does not improve every case or resolve every missing
criterion. No weights or source exceptions are tuned after observing labels.

## Fixed judgment protocol

The five evidence arms separate retrieval changes from allocation changes.
Patient facts, nurse-note context, system prompt, temperature 0, seed 0, original
source budget and response contract stay fixed. Llama 3 8B and Qwen3.5 4B run
serially, with three actual calls for each case/model/arm. Repeated calls are
not independent patients. Reference labels and rule outcomes never enter model
requests.

The full preparation contains 165 patient/arm packets and 990 planned calls.
A separate five-case mechanism pilot has 150 planned calls. Its previously
observed fixtures test normal mixed screening, empty-fact Blackout, Diabetes,
mixed uncertainty and the known module-to-packet bottleneck. They do not form
a held-out performance test. The two packet-coverage gains occur in
`VAL-MIX-02/blackout` and `VAL-MIX-06/blackout`, which are in the full comparison
and outside the mechanism pilot. Full-run calls are separate actual executions;
pilot responses are not imported or counted as new full-run calls.

Source-ID failures, truncation and other failed calls remain in the all-recorded
agreement denominator. They are not accepted abstentions. The report separately
records appropriate information-insufficient outcomes and abstention against a
different engineering reference. Citation validity does not establish that an
explanation follows from the evidence; all explanations enter an independent
review queue.

Paired comparisons include Hybrid RRF versus seventh/ninth with the same old
allocator, and old versus new allocation for each route. Identical request bodies
with different observed outcomes are flagged as input-identical variation;
their difference is not attributed to allocation.

## Files and commands

- `evaluation/case_evidence_allocation.py`: exact bounded packet selection.
- `tools/prepare_case_allocation_judgments.py`: frozen allocations, requests,
  separate scoring labels, source pins and post-allocation coverage.
- `tools/run_frozen_retrieval_judgments.py`: unchanged actual inference and
  response validation.
- `tools/run_case_allocation_series.py`: serial full execution in resumable
  batches, with source/runtime guards and automatic final reporting.
- `tools/report_case_allocation_judgments.py`: paired outcome changes, confusion
  matrices, case/evidence viewer, raw records and explanation-review queue.
- `configs/experiments/case_allocation_judgments_v1.yaml`: frozen model versions,
  prompt budgets, evidence budget and mechanism-case selection.

```powershell
.venv/Scripts/python.exe -X utf8 -m tools.run_case_allocation_series
# Resume the same interrupted series without rerunning recorded conditions:
.venv/Scripts/python.exe -X utf8 -m tools.run_case_allocation_series --resume
```

Only one series process may own its lock. The runner rejects foreign experiment
locks with live processes and does not remove historical lock files. Exited
owners are checked through native process inspection and recorded with lock
fingerprints. Do not start a second model experiment alongside it.

Preparations are in `outputs/experiments/case_allocation_judgment_preparation_v1`
and `case_allocation_judgment_pilot_inputs_v1`. Pilot observations are in
`case_allocation_judgment_pilot_v1`, full observations in
`case_allocation_judgment_full_v1`. Completed reports have independent immutable
inventories. Current series progress is in `case_allocation_series_v2/status.json`; the earlier
v1 initialization failure is retained as a zero-call diagnostic. The in-progress
full `results.jsonl` is append-only and the standard HTML report
refreshes after each batch.

## Remaining evidence

The full 990-condition comparison is complete: 957 accepted responses and
33 missing-citation failures. The [completed findings](case_allocation_judgment_findings.md)
show no overall judgment gain: Llama's allocation gains are citation-contract
recovery, while Qwen regresses on SYN-M2-009. Both Blackout focus cases remain
information-insufficient in all 60 conditions despite added evidence coverage.

Independent explanation and applicability review remains pending; the blank
focus worksheet contains all 60 occurrences without prefilled review decisions.
The [twelve-note prospective packet](prospective_case_review.md) is annotation-ready,
with source verification and inference-runner/native-index integration still
pending. It has not been evaluated. The retained
88-original corpus still has layout/applicability limitations, including partial
Blackout Figure 6 fragments. Freeze any subsequent strategy change and evaluate
on genuinely unseen, independently labeled cases before proposing a production
replacement.
