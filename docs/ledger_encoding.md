# Aggregation encoding diagnostic

This experiment measures a concrete context-budget failure without changing production rules, uploads, patient extraction or the clinical review workflow. It compares a per-passage copy of patient values with references to the same shared patient table. It does not compare retrieval algorithms.

## Implementation

`evaluation/applicability_judgment.py` accepts an explicit `aggregation_ledger_mode`:

| Mode | Aggregation input |
| --- | --- |
| `full_values` | Historical default: every ledger entry repeats its referenced patient values and quotations. |
| `field_references` | Each ledger entry retains its interpretation, field identifiers, prerequisites and source identifiers. Patient values and quotations resolve against the complete, unchanged `verified_patient_facts` table. |

Both modes retain the entire nurse note, patient table and original guideline passages. They use identical output schemas, model options, temperatures, seeds and structural repair limits. No source passage, exception or patient quotation is truncated. An unverified ledger remains an unverified model proposal. The program does not turn a warning or a reference label into the model's outcome.

Unknown mode names fail validation before inference. The historical default is unchanged. Selecting a mode changes the frozen configuration and request identity; it cannot be silently introduced into an older experiment.

## Read-only request audit

```powershell
.venv/Scripts/python.exe -m tools.audit_ledger_materialization --source outputs/experiments/applicability_comparison_full33_original_v3 --output NEW_EMPTY_AUDIT_DIRECTORY
```

`outputs/experiments/ledger_encoding_byte_audit_v2/index.html` inspects 384 accepted first-stage ledgers from the complete 792-condition main replay. Every reconstructed full-value initial aggregation request matches its historical request. Original patient inputs, passage bytes and ledger interpretations are preserved in the reference encoding.

Of the 384 requests, 345 are smaller. Median serialized-byte reduction is 6.03%, with a maximum of 24.20%; 39 small requests grow because the reference contract introduces a fixed explanatory overhead. These are measured request bytes, not estimated token counts, inference success or judgment accuracy. The inspected records contain 23 historical context-budget failures. Real-model testing is required to evaluate recovery.

## Paired real-model diagnostic

The diagnostic reuses the exact accepted repeat-zero first-stage proposal for each selected case and model. It then reruns aggregation only. Each pair receives identical patient facts, original evidence and the same fallible ledger interpretation; only its value materialization changes. Three independent aggregation calls per encoding are retained. Encoding order alternates across repeats, and judges run serially.

The five prespecified engineering fixtures cover all five modules: `SYN-EXT-002`, `SYN-EXT-006`, `SYN-EXT-010`, `SYN-EXT-017` and `SYN-EXT-018`. They are previously observed development cases, not an unseen validation set. Reference evidence and actual module-query evidence have separate experiment identities and reports.

```powershell
.venv/Scripts/python.exe -m tools.compare_ledger_encoding --source outputs/experiments/applicability_comparison_full33_original_v3 --output NEW_EMPTY_DIAGNOSTIC_DIRECTORY --cases SYN-EXT-002 SYN-EXT-006 SYN-EXT-010 SYN-EXT-017 SYN-EXT-018 --runtime-version 0.40.6 --evidence-policy module_query --repeats 3
```

Add `--resume` only for an identical manifest, source snapshot, runtime, model inventory, upstream bytes and saved inputs. `--max-conditions 0` performs preparation without inference. Every condition stores its complete requests, raw responses, validation failures, call count and original-source locations. Rehashed prompt tampering, altered labels, duplicate conditions and changed call counts are rejected when resuming. Completed outputs receive an execution audit.

The cached first-stage proposals were originally generated on Ollama 0.40.4. Both aggregation encodings in these new diagnostics run on the explicitly pinned Ollama 0.40.6. Historical first-stage calls are not counted as newly executed calls, and historical model outcomes are not pooled with the new runtime. Consequently this diagnostic is not a new end-to-end extraction or two-stage protocol evaluation.

Open the English reports:

- `outputs/experiments/ledger_encoding_pilot_v1/index.html`: reference-evidence diagnostic, 60 completed conditions. All 60 outputs pass the response contract. Thirty accepted pairs retain the same agreement status: 24 wrong-to-wrong and six correct-to-correct. No judgment improvement is demonstrated by this control.
- `outputs/experiments/ledger_encoding_module_pilot_v1/index.html`: completed actual module-query evidence diagnostic, 60 conditions. Full-value encoding accepts 24/30 outputs; field references accept 30/30. Six context failures recover, but three accepted judgments change from reference agreement to disagreement. Each encoding has only three agreements across 30 planned conditions. Among recovered executions, three agree and three disagree with the reference. This is execution recovery without an overall agreement gain.
- `outputs/experiments/applicability_comparison_full33_original_v3/cohort_report.html`: full original 33-case cohort and evidence-policy analysis.
- `outputs/experiments/applicability_comparison_full33_original_v3/review.html`: original evidence, stage outputs and paired judgment inspection.

Failures remain in the denominator. Recovery from an execution failure is counted separately from a valid wrong judgment becoming correct. Engineering reference agreement is not clinical accuracy. Address validity is not evidence entailment; original-support and clinical review remain pending.

The default protocol is retained because the diagnostic does not establish a judgment improvement. Investigate strict inequalities, OR/AND interpretation, conditional prerequisites and output-category mapping before committing to a larger protocol replay. Observed workstation timings include concurrent read-only engineering and testing work; they are not an isolated latency benchmark.

## Remaining gates

The original fact-sensitivity replay remains frozen at 243/312 conditions. Its declared runtime is 0.40.4, while the installed runtime is 0.40.6; no new conditions have been appended across that version boundary. The result prefix, ownership records and complete historical source snapshot are preserved. Resume only after restoring its exact runtime/source/model environment, or declare a separately identified replacement. Never relax the runtime check to merge them.

After the encoding diagnostic, inspect both the recovered execution cases and the remaining semantic errors before selecting the next common judgment protocol. Full-cohort verification, original-table context repair, strict graph-index/source-mapping validation and a unified six-retriever comparison remain necessary. Production retrieval is not automatically switched.

## Shared six-method query preparation

`tools/prepare_six_method_inputs.py` prepares fresh module queries from the uniformly verified source-literal snapshot. `outputs/experiments/six_method_query_preparation_v1` contains 33 patient inputs, 77 module queries and 462 planned case/module/method records. It excludes reference outcomes, rule outcomes and historical source rankings from query construction. False and zero values and original quotations remain explicit.

This preparation runs no retrieval, embedding, graph construction or judgment calls. Its `ready_for_execution` flag is false. Table-context review, graph index identities and a common judgment/no-evidence contract must be settled before execution. A later corpus revision requires a new preparation identity. The historical held-evidence fact sensitivity remains a separate experiment whose old queries were intentionally retained.
