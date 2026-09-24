# Complex nurse-note validation — 24 September 2026

Open [the live report](validated_live/index.html) for individual case reports,
original input text, model audit files and ranked retrieval results. The
[offline report](validated_offline/index.html) provides repeatable regression
results without model services.

## Verified behavior

- 12 complex synthetic notes covered all five modules, including two mixed cases.
- All 12 entered ranked retrieval. Both explicit negative controls used the fast path.
- All 89 live workflow ranking requests included bounded original symptom passages.
- All 19 targeted fact checks passed in both final profiles. These primarily check
  abstention on unsupported data, not extraction completeness or clinical accuracy.
- Before the fixes, the same offline fact checks passed 16/19: historical pressure,
  negated chest pain and a disputed hearing average exposed incorrect assertions.
- The complete test suite passed 197 tests, including 21 new complex-note tests.
  Two existing dependency deprecation warnings remain.
- A previous saved hearing-case report was verified without rewriting its files.
- Browser checks confirmed 14 case links, 54 expanded query/method detail panels,
  no JavaScript errors and no document overflow at mobile width.

## Real local retrieval comparison

Backend: Chroma with `nomic-embed-text`. Model intake and source review: `llama3:8b`.
18 exact original paragraphs were independently searched within their labelled
module. Three retrieval methods and three cutoffs produced 162 scoring rows.

| Method | Mean source Recall@3 | Mean source Recall@5 | MRR@5 |
|---|---:|---:|---:|
| Vector | 50.00% | 80.56% | 0.589 |
| BM25 | 63.89% | 91.67% | 0.576 |
| Hybrid RRF | 47.22% | 94.44% | 0.601 |

Hybrid had the highest mean source Recall@5 on this small development set, but
BM25 performed better at Top 3. This does not establish a universally superior
retriever. The current hybrid production default and RRF algorithm were retained;
this change improves source-context delivery and fact handling, not the ranking
algorithm. The standalone comparison uses a wider module filter than rule-bound
production retrieval and cannot measure its clinical decision accuracy.

Hybrid Top 5 still missed one of two expected sources for `CX-DM-01-Q1` and
`CX-MIX-01-Q1`. Gold labels were written from the existing source catalogue and
require independent review. Related-reference expansion and exact rule-bound
citations were excluded from these scores. Offline vector results use a lexical
surrogate and must not be presented as real dense-vector results.

## Model limitations remain visible

Nine of 14 source reviews produced valid responses: six reported no issue and
three required confirmation. Five failed after the bounded retry and explicitly
required human review: `CX-HTN-01`, `CX-HTN-02`, `CX-BLK-01`, `CX-BLK-02` and
`CX-MIX-02`. Failures included duplicate fields, non-verbatim quotations and
inconsistent uncertain/value pairs. They are not counted as successful reviews.

Seven cases accepted at least one grounded model proposal; seven completed
extraction without accepted proposals. Successful routing or an abstention check
does not mean the model understood every symptom. Clinical adjudication, larger
independent testing, improved paraphrase coverage and better local-model structured
output reliability remain necessary before making broader accuracy claims.

## Provenance

`validated_live/results.json` stores the configuration, fixture hash, rulebook and
knowledge-index hashes, individual fact checks and all retrieval rankings.
Each saved assessment has a source copy, source spans, model calls and weight digest,
an immutable artifact manifest and replay verification. `pytest.xml` records the
engineering test run. Earlier exploratory live runs are not part of this delivery.
