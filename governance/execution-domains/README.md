# Execution Domain Isolation
This directory is the only legal execution-entry surface for governed process selection.
An executor MUST select exactly one domain manifest before reading execution rules. It MUST NOT recursively scan the governance tree to infer applicable rules.
Domains: BASIC_DESIGN, WORD_YAML, STAGE, AUDIT.
Canonical authorities remain at their registered owner paths. Domain manifests reference them; they do not duplicate or supersede them.
Universal rule: WEB-GOV-03-S062A. Cross-domain execution requires terminal PASS and explicit handoff.
