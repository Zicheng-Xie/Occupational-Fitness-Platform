# Prospective independent nurse-note review

The current packet is `outputs/experiments/prospective_case_review_v2`. The earlier
`prospective_case_review_v1` is preserved unchanged as a superseded preparation
artifact; it must not be used for new annotation or execution. Version 2 contains
12 newly authored synthetic notes, each 212–224 words, covering the five assessment
modules through mixed clinical narratives, repeated measurements, temporal
differences, family history, negation, aiding/correction and missing information.
They contain no real patient data. No extraction, retrieval or judgment model has
been run on these cases, and no reference labels have been generated.

Only existing holdout directory names, filenames and file sizes were inspected.
Their notes and labels were not opened, reused or relabeled. These new notes are
stored outside normal case discovery and are not added to the current 990-condition
experiment. The frozen packet records the current development implementation
identity and the chosen execution plan before the prospective evaluation stage.
The twelve narrative contents are the same as version 1; no model has been run
on either version. Version 2 uses explicit UTF-8/LF note files, so file byte hashes
differ from the older Windows line-ending files while their narrative text agrees.

## What is ready

- `index.html`: English coordinator view of all 12 original notes.
- `reviewer_a.zip`, `reviewer_b.zip`: self-contained blinded reviewer packets.
  Each contains notes, the original 264-page guideline, one blank `annotations.json`,
  review instructions, the real field dictionary and review schema. Neither ZIP contains strategy
  metadata, system predictions, another reviewer's answers or suggested labels.
- `reviewer_a.template.json`, `reviewer_b.template.json`: immutable blank forms.
- `adjudication.template.json`: initially empty; use only for disputed cases.
- `review.schema.json`, `adjudication.schema.json`: strict form contracts.
- `readiness.json`: explicitly false; evaluation is not ready.
- `source_verification.template.json`, `source_verification.schema.json`: separate
  manual verification of exact cited PDF region, section, commercial/shared column
  and footnotes; initially blank, not an automatic clinical-support certificate.
- `execution_plan.json`: selected five existing comparison arms, two model weight
  digests plus the embedding-model weight digest, runtime version, options, corpus,
  frozen vector/native-source assets and source dependency inventory.
  It stays out of the blinded reviewer ZIPs.
- `native_index_contract.json`: original-source, embedding and native-engine
  configuration contract for the future live index preflight; coordinator-only.
- `manifest.json`, `artifacts.json`: source-note and guideline fingerprints.
  `implementation_snapshot.json` is coordinator provenance and stays out of both
  blinded ZIPs.

The notes are AI-assisted synthetic fixtures. Case authorship is not independent
annotation. These cases are unseen by the evaluated retrieval/judgment models at
packet creation, rather than hidden from their author or guaranteed to represent
unseen clinical practice. The packet is not an external clinical benchmark.

## Required human action

1. Give `reviewer_a.zip` to one reviewer and `reviewer_b.zip` to a different reviewer.
   Ask them to work independently. Clinicians or independent domain reviewers may
   supply engineering reference labels; record the actual role truthfully.
2. Each reviewer copies the enclosed `annotations.json` to their own working
   location. They preserve packet/case identities and note hashes, document facts
   using exact field keys and value types from `field_dictionary.json` and original
   note quotations, and label all five modules plus the overall
   outcome with a rationale. Substantive fitness labels require cited original
   guideline page, section and quotation. Missing measurements remain unknown.
3. Each reviewer supplies an identifier, role, timezone-aware completion time and
   the independence/blinding attestations, then changes `status` to `submitted`.
   Blinding refers to outputs and other review answers for these prospective
   cases, not previously published results on different cases. A reviewer involved
   in retrieval development or these case definitions must not attest independence.
4. If labels agree, no adjudication is required. If any module or overall label
   disagrees, a third, distinct adjudicator completes only those disputed cases in
   a copy of `adjudication.template.json`, using original notes and the guideline
   without model outputs. Agreed module labels must remain agreed.
5. A separate source verifier, distinct from the two annotators and any adjudicator,
   checks every submitted citation against the original PDF. After annotation and
   any adjudication, generate a fresh worksheet using `source-check-template`.
   Complete its verifier identity, role, timestamp and independence declarations.
   For every citation, inspect and record the actual page-region `bbox` in PDF
   points; verify its section, commercial/shared column, footnotes and qualifications.
   Set the specific check flags only when true, then submit the form. A page-wide
   quotation match cannot prove applicability: the software also requires this
   separate human verification. Private-only evidence cannot be relabeled as
   commercial merely because the text occurs on the same PDF page.
6. The coordinator verifies reviewer identities, qualifications and process
   records. JSON declarations alone do not authenticate a human or a credential.
   If a synthetic note is implausible or needs correction, return it for a newly
   versioned packet before evaluation; do not force a fitness label or edit a
   frozen note silently.

Keep submitted forms outside the immutable packet. The freeze command validates
all required records, exact note/PDF quotations and PDF regions, dictionary types
and modules, case scope, reviewer identities and disagreement handling before
writing a new label bundle. Correct dictionary types and literal quotations do
not prove clinical entailment, patient identity, negation or time interpretation;
the independent humans remain responsible for those judgments:

```powershell
.venv/Scripts/python.exe -X utf8 -m tools.prepare_prospective_review_pack source-check-template `
  --reviewer-a path/to/reviewer_a.submitted.json `
  --reviewer-b path/to/reviewer_b.submitted.json `
  --output path/to/source_verification.working.json
# Include --adjudication when an adjudication was required.
# A separate source verifier completes the worksheet and submits it.

.venv/Scripts/python.exe -X utf8 -m tools.prepare_prospective_review_pack freeze-labels `
  --reviewer-a path/to/reviewer_a.submitted.json `
  --reviewer-b path/to/reviewer_b.submitted.json `
  --source-verification path/to/source_verification.submitted.json `
  --output outputs/experiments/prospective_case_labels_v2
# Add --adjudication path/to/adjudication.submitted.json only when labels disagree.

.venv/Scripts/python.exe -X utf8 -m tools.prepare_prospective_review_pack check-ready `
  --labels outputs/experiments/prospective_case_labels_v2
```

The prospective harness must load cases and separate scoring labels through
`evaluation/prospective_review.py::prospective_inputs`. It revalidates the frozen
reviews, independent source verification, packet self identity, exact note files,
source dependency inventory, frozen corpus and locally installed model digests;
setting a readiness Boolean alone cannot bypass
this gate. Returned model-visible case inputs contain notes and requested modules,
without reference outcomes. This gate controls the new prospective evaluation
path. The existing general upload endpoint is unchanged and cannot prevent a user
from manually uploading a note. Such exploration would contaminate the intended
prospective evaluation and must be disclosed rather than called unseen testing.
Freezing labels records `independent_labels_frozen: true` while execution readiness
remains false. It does not falsely mark an absent runner ready. `check-ready`
blocks until an actual pinned runner and live native-index preflight exist, then
checks local runtime metadata only after human records validate. It does not
generate an answer. No metadata or model call occurred during packet preparation.

## Execution plan and pending harness integration

The active plan preserves the existing hybrid baseline and seventh/ninth methods
under round-robin/case-coverage allocation, the existing two models, three repeats,
budgets, corpus and temperature zero. Python sources (including embedded prompts),
configuration/schema sources and dependency declarations are hashed as a
conservative closure. Required provenance, field validation and gate contracts
must be present. A changed source, corpus, runtime or weight digest blocks entry.

The actual prospective inference runner and native-index live-preflight adapter
are **not implemented or executed** by this preparation tool. The gate fails
closed while they are pending. A future runner must call `prospective_inputs`
before inference, honor its frozen execution plan and keep returned scoring labels
outside prompts. Its pinned `retrieval_probe` must inspect actual native database
source/embedding/configuration contents and return the canonical identity of
`native_index_contract.json`, rather than reuse historical query outputs or merely
assert a Boolean. The callback must reside in the newly pinned runner source.
The function does not automatically intercept existing product upload endpoints.

Adding a new runner need not repeat independent annotation of unchanged notes.
Use an explicit pre-inference execution-plan amendment after labels are frozen:

```powershell
.venv/Scripts/python.exe -X utf8 -m tools.prepare_prospective_review_pack freeze-execution-amendment `
  --labels outputs/experiments/prospective_case_labels_v2 `
  --runner-source tools/run_prospective_comparison.py `
  --coordinator-id actual-coordinator-id `
  --reason "Integrate the new runner without changing frozen components or strategies." `
  --attest-zero-prior-inference `
  --output outputs/experiments/prospective_execution_integration_v1
```

The runner path above is a future implementation, not an existing runnable entry.
The command refuses an absent runner. An amendment may add one pinned runner file;
it rejects changes to existing components, prompts/configurations, methods,
weights, corpus and budgets. The coordinator must inspect the changes and attest
truthfully that no prospective inference has occurred. This declaration is an
auditable record, not proof that off-platform uploads did not happen. Supply the
amendment directory to `prospective_inputs(..., execution_amendment_directory=...)`
or `check-ready --execution-amendment ...`. Existing labels remain unchanged.
Strategy tuning or source changes beyond runner integration require a separately
reviewed protocol; they must not be silently accepted as the preregistered test.

## Remaining work

Independent human annotation, any required adjudication, separate source/section/
scope verification, actual inference-harness integration and native-index live
preflight implementation are still pending.
After labels and execution plan are frozen, run the already chosen
methods with fixed extraction, models, prompts and evidence budgets. Score results
against the frozen labels without tuning on this packet. Investigate explanation
support, restrictive-criterion omissions and citation failures separately from
classification agreement. Engineering agreement must not be reported as clinical
accuracy; qualified clinical review and validation remain a separate requirement.
