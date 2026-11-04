# Original-note and retrieved-evidence model review

The preserved ten-method and five-family refinement reports now have a local
model review panel. The original ranking observations, metrics, production rules
and patient files are unchanged. Reports are augmented when served; the frozen
HTML and its recorded hashes are not overwritten.

## Run the interactive report

```powershell
Set-Location 'E:\code\Occupational-Fitness-Platform'
.\scripts\start_retrieval_review.ps1
```

- Refinements: <http://127.0.0.1:8781/refinement/index.html>
- All ten original methods: <http://127.0.0.1:8781/ten-methods/index.html>

Select a case/module, method/variant, Top 5 or Top 10 and installed local model.
The panel automatically queues the selected condition. Calls are serialized.
"Assess all methods for this scope" queues the same case/module for all methods
shown in that report. The panel presents saved reviews for an identical request.
The server must remain running for new model calls; opening a file URL alone
cannot execute Python or connect to the same-origin review API.

Static previews served by VS Code or another file server also cannot execute
the review API. The panel shows embedded saved decisions in that mode and offers
**Open live assessment for this exact selection**, preserving the case, method,
model, Top K and evidence policy. **Previously generated model decisions** lists
actual saved conclusions and explanations. A file-server `ENOENT` response is
identified as the wrong service, not misreported as an Ollama failure. Reconnect
can recover a stopped local service without reloading or losing saved results.

## Input and output contract

`evaluation/retrieval_judgment.py` builds model input from the **entire original
nurse note** and exactly the returned Top K originals, including original source
text, source IDs, section and PDF page. It does not use engineering reference
answers, expected source IDs, rule outcomes or retrieval scores. A module-specific
review does not establish clearance for unassessed diseases or the whole patient.

The output includes `fitness` (`yes`, `no`, `undetermined`), a more precise outcome,
one or two explanation paragraphs, decisive missing information and concise
evidence-to-patient checks. Each check selects a supplied source slot and an
original patient paragraph. The application resolves their complete verbatim
text and character offsets; the model does not have to transcribe original text
or long identifiers. Selecting valid originals is **not**
proof that the model applied the standard correctly. Clinical review remains pending.
Unknown facts do not become normal findings. An unconditional exclusion is not
automatically exclusion of conditional eligibility. Conditional permission keeps
its prerequisites. Inconsistent proposals remain visible with review warnings.

For notes with multiple requested modules, select **All requested modules** for a
case-level proposal. This uses a documented module round-robin allocation of the
actual returned originals, then takes exactly five or ten whole sources. It is a
separate condition from each per-module review; it does not supply five or ten
originals per disease. The input panel lists every supplied passage.

## Cross-chapter dependencies

`strict_topk` never adds evidence. Explicit section links missing from the Top K
or frozen corpus are displayed in the dependency audit. `explicit_references`
is a separate experimental condition: follow frozen explicit section links for
at most two hops and at most twenty total whole originals. Targets can cross
disease modules without needing their own high retrieval rank. Related-source
edges alone are not treated as explicit chapter dependencies. Private-only
sources are excluded. Unavailable chapters remain unresolved; the system never
invents their text or silently treats a partial corpus as a complete section.
The initial Top K and retrieval metrics remain unchanged in both conditions.

## Integrity, capacity and persistence

Llama's native context is read from the installed Ollama model metadata. Its byte
BPE vocabulary/merges are reconstructed with `tokenizers`; segmentation follows
Meta's official Llama 3 tokenizer. Prompt/schema budget includes a conservative
template margin and reserved generation space. Qwen uses a conservative byte
upper bound within its native context. Over-budget evidence is rejected whole,
never truncated. Incomplete responses and unavailable source/paragraph selections fail
validation; raw responses remain in the audit. No model fallback is performed.

Conditions are cached by protocol, judge-engine version, exact model digest, evidence, prompt and
condition identity. Model calls run in a single worker; an OS file lock prevents
overlapping controllers in the same output directory. JSON records persist
requests, exact evidence, responses, tokens, timing and failures under
`outputs/experiments/retrieval_judgments_20261103/records`. An interrupted queued
or running condition can resume. Completed and failed observations are preserved.
Presentation-only changes do not hide saved model calls. Exact older requests
can be revalidated using the current parser and imported as derived cache records,
retaining the original observation and its ID for audit.

## Invalid-reference recovery

An `established` criterion must select a real, one-based original patient
paragraph. Paragraph zero means missing information and is only allowed for an
unresolved check. The decoder schema now encodes this relation in separate
applicability branches, while runtime validation continues to reject invalid
references. It never invents a paragraph or changes an established claim into an
unresolved claim to make a response pass.

A complete response with an invalid reference receives at most one validation
repair using the same model, complete original note and exact retrieved evidence.
The repair request is budget-checked independently, including its feedback. Both
requests and actual responses are retained in `attempts`; accepted repair output
is bound to `response_request`. Incomplete or truncated completions are not
accepted or automatically repaired. No other model or evidence is substituted.

The panel shows `repairing` while this second call runs. If validation still
fails, it displays a readable explanation, technical details and **Retry failed
assessment**. This explicit retry creates a separate record with `retry_of`,
retains the failed observation unchanged, and updates a persistent cache pointer.
Reopening the condition returns the retry result rather than a permanently cached
failure. A successful format repair is not proof of clinical correctness; outcome
consistency warnings and clinician-review requirements remain visible.

## Batch and offline export

```powershell
.venv/Scripts/python.exe -m tools.serve_retrieval_judgments --batch `
  --dataset refinement --case VAL-MIX-02 `
  --method scope88_prefix_criterion_v6__literal_facets `
  --model llama3:8b --top-k 5

.venv/Scripts/python.exe -m tools.serve_retrieval_judgments --batch `
  --dataset ten-methods --model qwen3.5:4b-q4_K_M --top-k 10

.venv/Scripts/python.exe -m tools.serve_retrieval_judgments `
  --export outputs/reports/retrieval_model_review
```

Close the interactive service before using a batch controller on the same output.
Batch filters can repeat `--case` and `--method`; absent filters mean all cases and
methods in that dataset. Run Top 5/10 and each model as separate, explicit batches.
Offline exports embed saved review records in the augmented `index.html` and keep
the original reports intact. They can display recorded commentary without Ollama;
new calls require the local service. No accuracy score is inferred from quotation
validation. Aggregate judgment accuracy requires a completed, label-audited
comparison and independent review, not just successful generation.

`examples/retrieval_judgment_client.py` demonstrates submission through the live
service, including a case-level `CASE:VAL-MIX-02` condition. Run
`python -m tools.validate_retrieval_review --submit` while the service is running
to queue the 48-condition integration matrix (five diseases, two models, two K
values, case-level method 7/9 comparison, all ten methods and reference expansion).
Run without `--submit` to refresh progress and failure accounting. These checks
surface model inconsistencies; they are not a labelled fitness-accuracy estimate.

Tokenizer segmentation reference:
<https://github.com/meta-llama/llama3/blob/main/llama/tokenizer.py>.
