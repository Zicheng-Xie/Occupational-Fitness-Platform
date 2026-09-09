# Validation scope and case data

| Dataset | Count | Purpose |
|---|---:|---|
| Supplied synthetic inputs | 10 | Original wording and extraction compatibility |
| Authored extension inputs | 20 | Five modules, missing data, conflicts and threshold boundaries |
| Rule regression expectations | 23 | Independently authored engineering expectations; clinical review pending |

The original inputs do not cover blackout and diabetes sufficiently. Separate synthetic inputs provide that coverage without adding invented histories to original cases. Structured additions in extension cases test rule behaviour and cannot establish free-text extraction accuracy.

Tests cover fact types and negation, grounded model proposals, three-valued rules, source binding, tamper detection, API behaviour and report links. Actual Llama runs record model fingerprints, accepted/withheld fields, latency and fallback status. Offline and Chroma checks use the same engineering expectations; exact-source coverage is not semantic Recall@K.

Institutional acceptance still requires clinician review of rules and sources, independent real-world cases, OCR evaluation, free-text model evaluation, access controls and sign-off integration. Passing engineering tests is not clinical approval. The guideline is fixed to the supplied AP-G56-22; a new version requires source review and revalidation.
