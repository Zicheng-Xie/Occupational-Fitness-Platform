# Fitness judgment refinement with frozen evidence

This development experiment follows the completed 990-condition case-allocation
comparison. It targets the distinction between finding the right original text
and applying that text correctly. Production extraction, semantic review, rules,
retrieval defaults and reports are not replaced.

## First intervention: judgment only

`tools/compare_fitness_judgments.py` consumes the immutable packets in
`outputs/experiments/case_allocation_judgment_preparation_v1`. It does not extract
new facts, rerun retrieval or supplement sources with reference answers.

| Protocol | Change | Unchanged components |
|---|---|---|
| `original` | None; exact historical request body | Patient facts, original sources, judge and generation settings |
| `outcome_semantics_v1` | Explicit outcome definitions, prerequisites, exceptions, measurement conditions and known restriction versus missing information | Response schema and patient/evidence message |
| `criterion_ledger_v1` | Same definitions plus compact source/fact/applicability/effect records before the proposed outcome | Patient/evidence message and model generation settings |

The third arm is a single actual call, unlike the previous two-stage
applicability diagnostic. It uses source positions rather than model-copied
identifiers. The application binds each position to the original source and
records its location. This can improve identifier reliability independently of
classification; these effects are reported separately. The source-text digest
uses the project's canonical JSON hashing convention, not a raw PDF byte hash.

Consistency checks compare the model's own established findings with its
proposed outcome. They never rewrite an outcome, infer missing patient data or
establish clinical correctness. A flagged response remains an observed proposal
and stays in the scoring denominator. Explanation support requires independent
review even when identifiers and internal checks are valid.

## Frozen mechanism comparison

Configuration: `configs/experiments/fitness_judgment_mechanism.yaml`.

- Six previously observed development cases: the two mixed Blackout failures,
  the hearing allocation regression, two prior retrieval sensitivity cases and
  an unconditional-standard control.
- Three unchanged evidence arms: Hybrid RRF, seventh method with case allocation,
  and ninth method with case allocation.
- Three judgment protocols, two pinned local models and three actual calls per
  condition: **324 planned calls**. This is six patients, not 324 patients.
- Llama 3 8B followed by Qwen3.5 4B; temperature 0, seed 0, context 8,192 tokens,
  generation reservation 2,048 tokens. At most five whole originals within the
  inherited evidence and request byte budgets.
- Facts and source text are identical across judgment protocols. Reference
  outcomes and rule-engine results never enter a request.

All requests, source-code hashes, runtime/model identities and selected packets
are frozen before inference. Each raw attempt is appended immediately, including
failures. A resumed run does not retry recorded failures or import old predictions.
Checkpoint verification permits appended attempts after a report refresh while
rejecting changes to its previously recorded prefix.

```powershell
.venv/Scripts/python.exe -m tools.compare_fitness_judgments --config configs/experiments/fitness_judgment_mechanism.yaml --prepare-only
.venv/Scripts/python.exe -m tools.compare_fitness_judgments --config configs/experiments/fitness_judgment_mechanism.yaml --resume
```

Open `outputs/experiments/fitness_judgment_mechanism_v1/index.html` after its first
checkpoint. Filter by case, judge, evidence method and repeat to compare the
three protocols side by side. Expand original evidence to inspect complete
passages and open the corresponding PDF page. `summary.json` explicitly records
whether the full run is complete. Results are provisional until it is complete.

Primary endpoints are engineering reference agreement over all recorded
conditions and patient-level majority agreement. Paired valid wrong-to-correct
and correct-to-wrong changes are separate from contract/run-status changes.
Excess information-insufficient predictions, confusion matrices, raw token
counts and measured attempt times are retained. A repeated call is not an
independent patient or an independent annotation. Shared-machine timings must
not be presented as an isolated hardware benchmark.

## Subsequent gates

1. Finish the frozen mechanism comparison and inspect whether improvements
   preserve the hearing and normal controls. Do not choose a protocol by total
   agreement alone while hiding a clinically meaningful new error.
2. Freeze a candidate and run the 33 observed development cases with matched
   fresh controls. Report the six mechanism cases separately from the remaining
   development cases. This is regression testing, not unseen-case validation.
3. Hold the chosen judge fixed before testing companion-evidence preservation.
   The allocator currently prefers fewer/shorter sources when its corpus-level
   criterion coverage is unchanged; test that preference directly. Keep complete
   originals and the same Top5/byte budgets, and preserve the coverage floor.
4. Hold judge and allocator fixed before testing patient-condition-aware seventh
   and ninth retrieval. Preserve original Hybrid RRF and all old/failed variants;
   do not promote a source using an expected answer or reference source ID.
5. Independently annotate and verify the twelve untouched prospective notes.
   Freeze a separate execution protocol before any new strategy sees those
   notes. Existing prospective v2 source pins intentionally do not describe these
   new interventions and must not be silently rewritten.

Engineering reference agreement is not clinical accuracy. No prospective
judgment, independent clinical annotation or production replacement is claimed
by implementing this comparison.
