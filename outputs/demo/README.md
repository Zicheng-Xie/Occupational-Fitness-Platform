# Fixed synthetic demonstration reports

This directory contains 30 verified synthetic assessment bundles selected for distribution with the project. Open [the report directory](../index.html) after downloading or cloning the complete repository. No model service is needed to view these saved reports. GitHub displays HTML source rather than running the local report interface.

`manifest.json` pins the exact demonstration runs. Each bundle includes HTML and Markdown reports, its original synthetic input, structured facts, rule results, guideline evidence, model audit records and a fingerprinted run manifest. These are assessment drafts, not signed clinical decisions.

The bundles are byte-identical copies of the selected local runs. Their historical configuration and provenance remain unchanged. Relative links retain access to the original guideline PDF and report directory.

Ordinary future assessment runs remain excluded by `outputs/runs/` in `.gitignore`. Generating new local runs does not replace this pinned collection. Updating the fixed collection is an explicit maintenance action.

Run `python scripts/verify_demo.py` to verify saved artifacts, replay rules and check citations without invoking a model. Run `python scripts/validate_delivery.py` to check report links. `.gitattributes` disables line-ending conversion for this directory so recorded fingerprints survive checkout on different operating systems.
