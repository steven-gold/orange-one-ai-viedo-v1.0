# ACPOS Runtime Binding Gap Report

Revision: 2026-09-05 LIVE-WILD-WAVE-DB-CONTRACT
Status: BLOCKED_BEFORE_PRODUCTION_BINDING

## Scope

This document records runtime binding blockers after verified database migration and release validation. It is a gap record only. It does not authorize new schema, new API semantics, invented permissions, or controlled-test runtime promotion to production.

## Verified Completed

- Migration chain 0001-0015: COMPLETE_APPLIED_VERIFIED
- Release Gate baseline: SUCCESS
- Production build validation baseline: PASS
- Current `new` branch runtime audit continued through HEAD `9471dda5727a90822432227d35f28a4bf831ad5c`
- Historical Neon staging schema was inspected read-only on `br-bitter-poetry-b3p6t5ub` / `acpos_staging` / `tiny-dust-89825424`
- Live authority target from 2026-09-05 is `wild-wave-25661146` / `neondb` / PG 18; 0001-0015 COMPLETE is not inherited onto this target
- Production DB driver/env contract materialized in `authority/runtime/ACPOS_PRODUCTION_DATABASE_RUNTIME_CONTRACT_FINAL_LOCKED_V1.0.yaml`
- Formal application API routes for Dashboard and UI Projection are materialized and call the existing runtime ports rather than returning fabricated success
- AIAPI-01 production operation materialization audited against Current AIAPI-01 Authority, Production Script V1.3, frontend/domain ports, controlled runtime, and current repository route tree

## Current Runtime Binding State

The following items remain not executed:

- Database production binding
- Production server runtime adapter binding
- AIAPI-01 effectful operation runtime binding
- Runtime E2E against real database adapters
- External production E2E

The API HTTP surface itself is materially present for audited Dashboard/UI Projection routes. This does not mean production runtime binding is complete because the underlying production runtime adapters remain unbound.

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

### C/D — AIAPI registered operation names exist, application command port/handler is not materialized

Current AIAPI-01 Authority explicitly references operations including `createProviderModelProfile`, `updateProviderModelProfile`, `testProviderModelProfile`, `setProviderModelCredential`, `runSandboxTest`, `executeProviderRoute`, and `getProviderRouteDecision`. It also requires reuse of the current registered operation registry and forbids inferring unregistered API methods/paths/permissions.

Repository audit confirms:

- `src/components/pages/AiApiVisual.tsx` renders these operation IDs but keeps all effectful controls disabled with `REMAP_REQUIRED_NOT_EXECUTED`.
- `src/domain/aiApi/aiApiRuntimePort.ts` materializes only the read-only AIAPI projection client through `/v1/ui-projections/admin%3AAIAPI-01`; it contains no effectful AIAPI command port.
- `src/server/testing/controlledAiApiTestRuntime.ts` is TEST_ONLY synthetic projection state and cannot satisfy production runtime binding.
- `src/server/shared/uiProjectionRuntime.ts` only exposes AIAPI through the generic projection path; without production projection bindings it fails closed.
- Current repository tree contains no dedicated AIAPI effectful `/v1` route family and no dedicated production AIAPI server runtime/gateway implementation path.

Production Script V1.3 states that provider execution belongs to the existing Provider Prompt Adapter / AI API Router / ProviderGateway and creates no new runtime service. Because the current application does not materialize that existing effectful operation port/handler path and AIAPI-01 forbids route inference, a new API route or gateway architecture may not be invented from operation names alone.

Required disposition:

`BLOCK + REPORT_AUTHORITY_GAP`

The missing materialization must be resolved from the current registered operation registry / governed System Lifecycle authority before ProviderGateway implementation or AIAPI effectful remap may proceed.

### D — Driver/env contract named 2026-09-05; bootstrap still empty

The live Neon target and application connection contract are now named. Bootstrap and adapter binding remain not executed.

- Live target: `wild-wave-25661146` / `ORANGEONEACPOSStaging` / `neondb` / PG 18 / production branch `br-shy-cherry-auiol4oy`
- Driver package: `@neondatabase/serverless`
- Env keys in `.env.example`: `DATABASE_URL`, `DATABASE_URL_UNPOOLED`, `NEON_PROJECT_ID`
- `package.json` still has no driver dependency
- `src/instrumentation.ts` `register()` remains empty
- 0001-0015 COMPLETE remains historical evidence on `tiny-dust-89825424` and must not be treated as applied on wild-wave
- System Authority defines ACPOS runtime/business/governance boundaries but does not select or specify the application database client implementation.
- DB-01 Authority defines a read-only inspection business boundary and explicitly forbids raw/direct production mutation; it does not define the application DB driver, pool, connection env contract, or runtime bootstrap implementation.
- Page Integration Matrix defines cross-page data/decision ownership and handoff boundaries, not application database transport/bootstrap technology.
- Production Script V1.3 is scoped to provider-neutral instruction/provider adapters and explicitly creates no new runtime service; it does not define database runtime binding technology.
- Database Migration Authority is scoped to migration/bootstrap/checksum/execution governance and cannot be extended into an application-runtime driver decision.

Selecting a different driver (`pg`, `postgres`, `@vercel/postgres`, Prisma, Drizzle) still requires a new Authority revision.

### E — Leave real external execution to External/Production E2E Gate

- ERP provider synchronization / connector execution
- Social platform binding / discovery / publishing
- Shared crawler / external acquisition
- AI provider real external request execution

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
- `.env.example` now names `DATABASE_URL`, `DATABASE_URL_UNPOOLED`, and `NEON_PROJECT_ID` with empty secret values
- `src/instrumentation.ts` exports an empty `register()` and therefore performs no production server runtime adapter injection

These facts are implementation evidence of the current block; they are not permission to invent the missing contract.

## Blocking Conditions

The following production contracts are still absent from the application runtime and must be materialized before a production binding can be truthfully claimed:

1. Authority-defined production PostgreSQL/Neon driver and connection contract — named `@neondatabase/serverless` / wild-wave
2. Authority-defined production database connection environment contract — named in `.env.example`
3. Production runtime bootstrap call path (`src/instrumentation.ts` register is currently empty) — still open
4. Production server adapter implementations for the existing `configure*Runtime` ports
5. AIAPI effectful command port/handler mapping from the current registered operation registry
6. Domain-specific command/read-model mappings where Authority does not already define exact behavior
7. Real runtime E2E evidence after binding

## Authority Gap Rule

Where Current Authority does not define an exact adapter/database mapping, operation behavior, permission mapping, technical driver/bootstrap contract, API route/handler mapping, or external-provider boundary, the required disposition is:

`BLOCK + REPORT_AUTHORITY_GAP`

No implementation may guess missing schema, fields, permissions, API behavior, driver choice, connection contract, route mapping, or production external behavior.

## Next Allowed Construction Gate

Driver and env keys are named. Production database binding may not proceed until `register()` injects `@neondatabase/serverless` against wild-wave and 0001-0015 are re-verified on `neondb`.

AIAPI effectful production binding may not proceed until the current registered operation registry / governed System Lifecycle materializes the existing operation-to-command-port/handler mapping without route inference.

Until then, allowed work is limited to:

- auditing non-DB production adapters that can be completely derived from Current Authority without inventing transport/bootstrap behavior;
- preserving and testing existing fail-closed API/runtime behavior;
- preparing exact Authority-gap evidence for System Lifecycle governance;
- continuing external-gate classification without executing real external providers.

The read-only DB/Projection paths remain the preferred first database binding candidates once the missing technical contract becomes Authority-defined.

## Rules

- Do not treat controlled runtime as production runtime.
- Do not introduce schema changes from this report.
- Do not infer missing Authority definitions from table names or registered operation names alone.
- Do not select a database driver other than `@neondatabase/serverless` without a new Authority revision.
- Do not invent AIAPI effectful API paths or ProviderGateway architecture where Current Authority requires reuse of an existing registered operation registry.
- Do not claim runtime complete or production ready until implementation, commit, build/test, runtime validation, and E2E evidence all exist.
