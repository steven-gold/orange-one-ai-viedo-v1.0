# Pre-Repair Constraints

- Date: 2026-09-08
- Status: ACTIVE_BEFORE_REPAIR
- Deploy: FORBIDDEN
- Second product system: FORBIDDEN

This file is the processing-before limit. Repair work starts only after the frozen snapshot and this constraint file are accepted.

## Hard stops

1. Do not deploy, republish, or retarget Vercel until program files are complete and the user authorizes one deployment.
2. Do not treat CONTROLLED_TEST, HTML 200, CI Release Gate, or `/health/ready=200` as production usable.
3. Do not invent schema, permissions, API paths, AIAPI effectful routes, or a driver other than `@neondatabase/serverless`.
4. Do not add a 19th product page, a new nav item, or a parallel ACPOS product system.
5. Do not rewrite Current Page Authority to fit missing code.
6. Do not promote `CONTROLLED_TEST` adapters into production bindings.
7. Do not claim COMPLETE unless files, render/test evidence, and validation all exist.
8. Do not change live `/health/ready` semantics in this freeze window.
9. Do not guess DEV-01 `/v1/outreach/*` request semantics from operation names.
10. Do not read or invent Secret values. `VERCEL_AUTOMATION_BYPASS_SECRET` stays user-supplied.

## Allowed work in this window

1. Keep audit records in `.monkeycode/specs/2026-09-08-strict-construction-audit-monitor/`.
2. Keep an independent GitHub Issue as a mirror of the same records.
3. Plan a construction-audit monitor that reuses existing construction evidence.
4. Repair local program files later, still without deploying, until the user authorizes one deployment.

## Monitor page decision

A dedicated product route such as `/audit` or a new `page_uid` is blocked.

Current Authority forbids extra menu, extra route, extra page, and inferred subsystem. Construction progress already states it must not become a second system/page authority. SYS-01 states only one Unified System Lifecycle AI and no parallel system.

Allowed monitor shapes, in preference order:

1. GitHub Issue plus this specs directory as the current strict audit surface.
2. A construction evidence JSON/YAML under `docs/construction/evidence/` consumed by existing SYS-01 audit/raw_logs composition, without a new route.
3. A later SYS-01 section remap only if Current SYS-01 Authority already names the exact section and the remap does not add navigation.

Blocked monitor shapes:

1. New Next.js page under `src/app/audit` or similar.
2. New nav_id in `ACPOS_CURRENT_NAVIGATION_PERMISSION_AUTHORITY`.
3. New dashboard cards, KPIs, or charts invented for audit cosmetics.
4. A second progress YAML that replaces `ACPOS_WEBSITE_CONSTRUCTION_PROGRESS.yaml`.

## Repair order after this freeze

1. Align construction progress YAML and gap report with current bootstrap facts. Keep COMPLETE false.
2. Inventory every registered page, control, action, gate, permission, route, and `configure*` port against Current Authority.
3. Close 待修正 items that are documentation lag.
4. Keep 未完成 runtime adapters fail-closed until Authority mapping is exact.
5. One deployment only after the user authorizes it, against a SHA that exists in git.

## GitHub mirror rule

The GitHub Issue is an independent construction-audit record. It must cite this directory. It must not create a second product, a second authority set, or a second navigation tree.
