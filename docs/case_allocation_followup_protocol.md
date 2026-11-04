# Follow-up after the frozen case-allocation comparison

The current 990-condition comparison changes supplied evidence only. Its original
facts, judge prompt, response schema and results must remain immutable. A retrieval
coverage gain does not establish improved interpretation, and recovering a valid
citation is different from correcting a valid but wrong classification.

## Independent review before another judgment intervention

For VAL-MIX-02 and VAL-MIX-06, review the original note, verified facts, every
actually supplied passage and each model explanation. In particular, distinguish:

- whether the Blackout restriction passage entered the model request;
- whether the response cited that exact supplied source;
- whether the explanation acknowledged the documented unresolved mechanism;
- whether the overall outcome applied the original restriction consistently;
- whether an adjacent qualification or exception is actually established;
- whether missing information in another module obscured an established finding.

Record an engineering consistency finding separately from independent clinical
adjudication. An automated literal-match flag cannot establish entailment or a
reviewer's clinical qualifications. Keep every failed raw response in the record.

## Small, separately frozen judgment ablation

If independent review confirms an interpretation or outcome-mapping problem,
prepare a new development experiment with the same frozen patient facts and
evidence. Do not rerank evidence or re-extract facts in this ablation.

| Arm | Changed component | Purpose |
|---|---|---|
| Original judgment contract | None | Reproduce the measured baseline |
| Explicit outcome semantics | Outcome definitions and a requirement to distinguish established restrictions from unrelated unknowns | Test whether the response contract leaves outcome mapping unclear |
| Criterion-first judgment | Explicit patient fact, original clause, applicability, exception and unresolved-information checks before the overall output | Test whether an auditable intermediate decision helps apply supplied evidence |

These are proposed interventions, not implemented or measured improvements. The
definitions must follow independently reviewed guideline meaning, rather than a
case identifier, expected answer or a rule-engine conclusion inserted into the
prompt. An established restriction must not be invented from fatigue, family
history, an unverified finding or a historical event outside the applicable
criterion. Unassessed modules remain unknown.

Freeze the arm definitions and source hashes before calls. Use the same local
model versions, original-text budget, context reservation, temperature, seed and
repeat count. Record all actual requests and responses; run models serially.
Patient-level paired effects, valid classification changes, contract changes,
excess abstentions and original-text support remain separate endpoints. Do not
silently repair citation failures or replace failed runs with another method.

## Prospective evaluation

The twelve new notes in `prospective_case_review_v2` have no system predictions or
reference answers. Give the two blinded ZIPs to independent reviewers. Verify
their process, resolve label disagreements and freeze labels with the readiness
gate described in `prospective_case_review.md` before testing any strategy.

The proposed judgment ablation may use the existing development cases. It must
not use the prospective notes or reviewer labels for prompt design or strategy
selection. Any strategy evaluated on the prospective set must be fixed before
its first prospective call. A strategy adjusted using those outcomes requires a
different, newly annotated test cohort; repeating on the same cases does not
restore independence.

Engineering references do not establish clinical accuracy. Corpus layout,
commercial/private scope, cross-reference completeness and clinical explanation
support still require review before a production replacement is proposed.
