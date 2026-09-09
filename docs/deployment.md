# Deployment boundaries

The platform supports enterprise occupational health and commercial-driver assessment workflows. Local operation includes model-assisted intake, rule checks, guideline citations and English review reports.

This delivery is a decision-support application with rules marked `pending_clinical_review` and reports marked `DRAFT`. Demonstration records are explicitly synthetic.

Before live institutional deployment, implement and validate organisation accounts and roles, case access auditing, encryption and backups, retention controls, clinician review and electronic sign-off, rule approval records, independent validation and infrastructure operations.

The development API binds to loopback. Institutional integration is required before exposing it as a business service. Model calls use direct local connections; model weights remain managed by Ollama. The supplied guideline retains its original publication and redistribution terms.
