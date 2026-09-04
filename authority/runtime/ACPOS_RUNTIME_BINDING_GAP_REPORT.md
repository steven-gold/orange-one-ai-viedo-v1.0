# ACPOS Runtime Binding Gap Report

Revision: 2026-09-04 POST-MIGRATION-RUNTIME-READINESS-AUDIT
Status: BLOCKED_BEFORE_PRODUCTION_BINDING

## Scope

This document records runtime binding blockers after verified database migration and release validation. It is a gap record only. It does not authorize new schema, new API semantics, invented permissions, or controlled-test runtime promotion to production.

## Verified Completed

- Migration chain 0001-0015: COMPLETE_APPLIED_VERIFIED
- Release Gate baseline: SUCCESS
- Production build validation baseline: PASS
- Current `new` branch runtime audit continued through HEAD `447a577ab52fb8bb9bff953679ed3aa99f6fcdcc`
- Current Neon staging schema inspected read-only on `br-bitter-poetry-b3p6t5ub` / `acpos_staging`
- Formal application API routes for Dashboard and UI Projection are materialized and call the existing runtime ports rather than returning fabricated success

## Current Runtime Binding State

The following items remain not executed:

- Database production binding
- Production server runtime adapter binding
- Runtime E2E against real database adapters
- External production E2E

The API HTTP surface itself is materially present for audited routes. This does not mean production runtime binding is complete because the underlying production runtime adapters remain unbound.

## Existing API / Runtime Path Verified

Audited examples:

- `src/app/v1/dashboard/read-model/route.ts` -> `getDashboardReadModel()`
- `src/app/v1/ui-projections/[pageUid]/route.ts` -> `getUiProjection()`

These routes preserve `correlation_id`, `cache-control: no-store`, explicit HTTP failure status, and existing fail-closed runtime behavior. Therefore API route absence is not the primary blocker for these paths.

## Existing Runtime Ports Verified

The application already contains formal fail-closed runtime ports with `configure*Runtime` binding entry points. These are not production adapters by themselves.

- UiProjection: `configureUiProjectionRuntime`
- Dashboard: `configureDashboardRuntime`
- Knowledge: `configureKnowledgeRuntime`
- ERP: `configureErpCommandRuntime`
- Social: `configureSocCommandRuntime`
- IAM: `configureIamRuntime`
- QA: `configureQaRuntime`
- DB Read Model: `configureDbReadModelRuntime`

The audited ports preserve authorization, audit/error handling, correlation IDs, and explicit NOT_BOUND behavior. Controlled test fallbacks remain test-only and must not satisfy production binding.

## Runtime Readiness Classification

### B — DB schema exists, production adapter/bootstrap missing

- UiProjection
- Dashboard
- DB Read Model
- Knowledge
- IAM
- QA

For these domains, API/runtime ports exist and relevant database structures are present, but there is no production PostgreSQL/Neon driver bootstrap and no server startup adapter injection.

### C — API/runtime exists, database mapping or external execution boundary is not fully materialized

- ERP
- Social

ERP has canonical tables including `erp_connectors`, `erp_mappings`, `erp_snapshots`, `erp_sync_jobs`, and related audit/failure structures. Social has canonical tables including `social_account_bindings`, `social_market_targets`, `social_target_discovery_jobs`, and related publishing/manual-action structures. Their runtime command ports exist, but the production command-to-database/external-adapter implementation is not materialized.

### D — Authority technical contract gap

The Current Database Migration Authority governs database migration/bootstrap/checksum/execution. It does not define the application runtime database client technology, production connection environment key contract, pooling/lifecycle implementation, or server adapter injection implementation.

Accordingly, selecting `pg`, `postgres`, `@neondatabase/serverless`, `@vercel/postgres`, Prisma, Drizzle, or another runtime driver without a Current Authority definition would be an invented technical contract and is blocked.

### E — Leave real external execution to External/Production E2E Gate

- ERP provider synchronization / connector execution
- Social platform binding / discovery / publishing
- Shared crawler / external acquisition

These may not be treated as complete from local or controlled-test adapters.

## Database Structures Confirmed for Binding Work

Read-only staging inspection confirms materialized canonical tables needed by the next binding stages, including:

- Core/read projection: `projects`, `project_versions`, `topics`, `topic_versions`, `department_tasks`, `provider_jobs`, `qa_review_runs`
- Dashboard: `dashboard_todos`
- Authorization: `permission_resources`, `account_permission_assignments`, `project_memberships`
- Audit/correlation: `audit_events`
- Knowledge: `knowledge_sources`, `fact_packs`, `evidence_records`
- ERP: `erp_connectors`, `erp_mappings`, `erp_snapshots`, `erp_sync_jobs`, `erp_failures`, `erp_audit_references`
- Social: `social_account_bindings`, `social_market_targets`, `social_target_discovery_jobs`, `social_manual_actions`, `publish_requests`

This inspection does not modify schema and does not reopen migration work.

## Production Runtime Bootstrap Evidence

Current repository evidence remains:

- `package.json` contains Next/React dependencies only and no production PostgreSQL/Neon runtime driver
- `.env.example` contains no database connection/runtime binding environment contract
- `src/instrumentation.ts` exports an empty `register()` and therefore performs no production server runtime adapter injection

These facts are implementation evidence of the current block; they are not permission to invent the missing contract.

## Blocking Conditions

The following production contracts are still absent from the application runtime and must be materialized before a production binding can be truthfully claimed:

1. Authority-defined production PostgreSQL/Neon driver and connection contract
2. Authority-defined production database connection environment contract
3. Production runtime bootstrap call path (`src/instrumentation.ts` register is currently empty)
4. Production server adapter implementations for the existing `configure*Runtime` ports
5. Domain-specific command/read-model mappings where Authority does not already define exact behavior
6. Real runtime E2E evidence after binding

## Authority Gap Rule

Where Current Authority does not define an exact adapter/database mapping, operation behavior, permission mapping, technical driver/bootstrap contract, or external-provider boundary, the required disposition is:

`BLOCK + REPORT_AUTHORITY_GAP`

No implementation may guess missing schema, fields, permissions, API behavior, driver choice, connection contract, or production external behavior.

## Next Allowed Construction Gate

The next implementation batch may begin only after the production database runtime technical contract is present in Current Authority, or when another production adapter can be fully derived from existing Current Authority without inventing that contract.

The read-only DB/Projection paths remain the preferred first binding candidates because their API routes, fail-closed runtime ports, canonical schema, and read-only DB-01 business boundary are already materialized. They are nevertheless blocked from real Neon binding until the technical database runtime contract is authority-defined.

## Rules

- Do not treat controlled runtime as production runtime.
- Do not introduce schema changes from this report.
- Do not infer missing Authority definitions from table names alone.
- Do not select a database driver or connection contract by preference.
- Do not claim runtime complete or production ready until implementation, commit, build/test, runtime validation, and E2E evidence all exist.
