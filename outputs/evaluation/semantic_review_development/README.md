# Semantic review development trials

These synthetic development records are retained to document observed failures while building
the second-pass reviewer. They are not the active runtime policy or independent validation.

- `semantic_review_initial.json`: direct critique, first prompt; two valid reviews out of eight.
- `semantic_review_prompt_v2.json`: clearer critique instructions; five valid reviews out of eight.
- `semantic_review_prompt_v3.json`: explicit boolean meanings and one bounded format retry;
  six valid reviews out of eight, with additional unsupported flags.

The active implementation independently re-reads the original note without seeing previously
extracted values. The program then compares the two readings. Its final development result is
`../semantic_review.json`. The same fixtures informed implementation changes, so this is not a
held-out evaluation. No clinical accuracy claim can be made from these results.
