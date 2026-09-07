import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("ERP-01 snapshot refresh is a governed request on the existing ERPConnectorService owner", async () => {
  const authority = await read("authority/pages/admin/ERP-01/ACPOS_ERP-01_ERP_FINANCE_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml");
  const contract = await read("src/domain/erp/erpRuntimeContract.ts");
  const production = await read("src/server/erp/productionErpSnapshotRuntime.ts");
  const identity = await read("src/server/shared/identityPageCommandRuntime.ts");
  const route = await read("src/app/v1/erp/snapshots/refresh/route.ts");

  assert.match(authority, /operation_id: refreshERPSnapshot[\s\S]*path: \/v1\/erp\/snapshots\/refresh[\s\S]*owner: ERPConnectorService/);
  assert.match(authority, /ERP-01-GATE-SNAPSHOT-REFRESH[\s\S]*explicit scope\/version[\s\S]*idempotency[\s\S]*audit/);
  assert.match(contract, /ERP_IMPLEMENTATION_STATUS = "PARTIAL_RUNTIME_BOUND_PENDING_RELEASE"/);
  assert.match(contract, /ERP_SNAPSHOT_REFRESH_IMPLEMENTATION_STATUS = "RUNTIME_BOUND_PENDING_RELEASE"/);

  assert.match(route, /createErpRoute\("refreshERPSnapshot"\)/);
  assert.match(identity, /control:CTRL-ADMIN-ERP-01-ACT-05-ERP-SNAPSHOT-REFRESH/);
  assert.match(identity, /api:refreshERPSnapshot/);
  assert.match(identity, /requestProductionErpSnapshotRefresh/);
  assert.match(identity, /ERP01_OPERATION_PERMISSION_MAPPING_REQUIRED/);

  assert.match(production, /ERP01_REQUIRED_SNAPSHOT_SCOPE_MISSING/);
  assert.match(production, /ERP01_EXPECTED_VERSION_MISSING/);
  assert.match(production, /ERP01_IDEMPOTENCY_KEY_REQUIRED/);
  assert.match(production, /ERP01_SNAPSHOT_NOT_FOUND/);
  assert.match(production, /ERP01_SNAPSHOT_REFRESH_TARGET_AMBIGUOUS/);
  assert.match(production, /ERP01_CONNECTOR_STATE_GUARD_REJECTED/);
  assert.match(production, /ERP01_SNAPSHOT_VERSION_CONFLICT/);
  assert.match(production, /ERP01_SNAPSHOT_STATE_GUARD_REJECTED/);
  assert.match(production, /INSERT INTO public\.erp_sync_jobs/);
  assert.match(production, /status[\s\S]*'QUEUED'/);
  assert.match(production, /erp\.snapshot\.refresh_requested/);
  assert.match(production, /external_request_sent: false/);
  assert.match(production, /snapshot_mutated: false/);
  assert.doesNotMatch(production, /INSERT INTO public\.erp_snapshots/);
  assert.doesNotMatch(production, /UPDATE public\.erp_snapshots/);
  assert.doesNotMatch(production, /fetch\(|external_request_sent:\s*true/);
});

test("ERP-01 Production projection exposes refresh only for a real non-active snapshot target", async () => {
  const projection = await read("src/server/shared/pageCatalogProjectionRuntime.ts");
  const visual = await read("src/components/pages/ErpVisual.tsx");
  const runtime = await read("src/components/pages/ErpControlRuntime.tsx");

  assert.match(projection, /FROM erp_snapshots/);
  assert.match(projection, /FROM erp_sync_jobs/);
  assert.match(projection, /floor\(extract\(epoch FROM created_at\) \* 1000\)::bigint::text AS version/);
  assert.match(projection, /activeRefresh/);
  assert.match(projection, /"ERP-01-GATE-SNAPSHOT-REFRESH": snapshotRefreshReady/);
  assert.match(projection, /"ERP-01-BTN-SNAPSHOT-REFRESH": \[[\s\S]*requested_scope/);
  assert.match(projection, /snapshot_version: asText\(snapshot\?\.version\)/);
  assert.match(visual, /ERP_FORM_SCHEMA_NOT_BOUND/);
  assert.match(runtime, /expected_version: optionalNumber\(selected\.snapshot_version\)/);
});

test("migration 0023 stages only ERP snapshot refresh control/API permissions", async () => {
  const migration = await read("database/migrations/0023_erp_snapshot_refresh_permission_closure.sql");
  const manifest = await read("database/migrations/migration_checksum_manifest.yaml");
  const neonRuntime = await read("src/server/database/neonRuntime.ts");

  assert.match(migration, /control:CTRL-ADMIN-ERP-01-ACT-05-ERP-SNAPSHOT-REFRESH/);
  assert.match(migration, /api:refreshERPSnapshot/);
  assert.match(migration, /ERP01_SNAPSHOT_REFRESH_PERMISSION_RESOURCE_COUNT_MISMATCH/);
  assert.match(migration, /ERP01_SNAPSHOT_REFRESH_APPROVED_ALLOW_COUNT_MISMATCH/);
  assert.match(migration, /ON CONFLICT \(user_id,resource_id,action,version_no\) DO NOTHING/);
  assert.match(migration, /d18b51cb45f1c0ed3519ba3b1d2c7ac2ed11bc270e2bf59e21c98d41694f0cfa/);
  assert.doesNotMatch(migration, /INSERT INTO public\.permission_resources/);
  assert.doesNotMatch(migration, /CREATE ROLE|ALTER ROLE/);

  assert.match(manifest, /contract_id: ACPOS-MIGRATION-CHECKSUM-1\.0\.10/);
  assert.match(manifest, /migration_id: 0023_erp_snapshot_refresh_permission_closure/);
  assert.match(manifest, /payload_sha256: d18b51cb45f1c0ed3519ba3b1d2c7ac2ed11bc270e2bf59e21c98d41694f0cfa/);
  assert.match(manifest, /approval_ref: CR-ERP-0023-PENDING-PRODUCTION-APPLY/);
  assert.match(neonRuntime, /REQUIRED_MIGRATION_COUNT = 20/);
  assert.match(neonRuntime, /MAX_SUPPORTED_MIGRATION_COUNT = 23/);
});
