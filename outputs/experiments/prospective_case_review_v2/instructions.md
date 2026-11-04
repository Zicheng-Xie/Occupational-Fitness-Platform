# Independent prospective annotation

This packet contains newly authored synthetic notes, not real patient data.
It has no model predictions, retrieval outputs or expected answers. No system
evaluation has been run on these notes. The entire original guideline is supplied
as guideline.pdf; use its commercial-driver or explicitly shared provisions.

Work independently. Do not inspect another reviewer's answers or any model output.
Do not use a language model to supply the labels. Keep relative dates, family
history, historical tests, negation, aiding/correction and missing measurements
separate. Missing or uncertain information is not a normal finding.

1. Copy annotations.json to a separate working location. Keep the case IDs,
   packet_identity and source-note fingerprints unchanged.
2. Enter your stable reviewer ID, role and timezone-aware completion time.
   Clinicians and independent domain reviewers can provide engineering reference
   labels. Declare authorship/development independence and blinded review truthfully.
   A coordinator must verify identity and qualifications separately; a JSON
   declaration is not professional credential verification.
3. Review every note and all five requested modules. Record documented facts with
   exact note quotations, preserving whose history and which time are described.
   Use exact keys/types from field_dictionary.json; cardiovascular keys belong to
   hypertension, and the other field prefixes identify their assessment module.
4. Supply each module outcome and the overall outcome with a substantive rationale.
   For a substantive fitness label, cite original guideline page, section and an
   exact source quotation and provide a documented fact for that module.
   Information-insufficient labels must explain the actual unresolved information.
   Source quotations and note quotations are checked against their original text;
   those checks do not establish clinical entailment.
5. After completing all cases, set status to submitted and return the form to
   the coordinator. Do not replace the original immutable template.

Allowed outcomes: meets_unconditional_standard, may_meet_conditional_standard,
temporarily_unfit, does_not_meet_standard, insufficient_information.

Two different reviewers submit independently. Only case/module disagreements
require a distinct adjudicator, who checks the notes and guideline without model
outputs. The final labels must be frozen before prospective system execution or
scoring. These are engineering reference labels; clinical accuracy remains
unestablished until the required qualified review and validation are completed.
After annotation, a separate coordinator verifies each cited original PDF region,
section, commercial/shared column, footnotes and qualifications. Literal page text
matching alone cannot establish section membership or commercial applicability.
