import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("SYS-01 SystemChangeService is materialized without enabling locked visual mutations", async () => {
  const [authority, lifecycle, runtime, identity, projection, migration, manifest] = await Promise.all([
    read("authority/pages/admin/SYS-01/ACPOS_SYS-01_SYSTEM_LIFECYCLE_AI_FINAL_DESIGN_ENCODING.yaml"),
    read("src/server/system/systemLifecycleRuntime.ts"),
    read("src/server/system/productionSystemLifecycleRuntime.ts"),
    read("src/server/shared/identityPageCommandRuntime.ts"),
    read("src/server/shared/pageCatalogProjectionRuntime.ts"),
    read("database/migrations/0020_system_lifecycle_runtime.sql"),
    read("database/migrations/migration_checksum_manifest.yaml"),
  ]);

  assert.match(authority, /status: FINAL_LOCKED/);
  assert.match(authority, /createCandidate[\s\S]*enabled_in_visual_phase: false/);
  assert.match(authority, /createChangeRequest[\s\S]*enabled_in_visual_phase: false/);
  assert.match(authority, /runSandboxTest[\s\S]*enabled_in_visual_phase: false/);
  assert.match(authority, /independent_change: CREATE_NEW_SYSTEM_CHANGE_ID_BUT_REUSE_CURRENT_SYSTEM_TRUTH/);

  assert.match(lifecycle, /generated_system_change_id: boolean/);
  assert.match(lifecycle, /input\.operation_id !== "createCandidate"/);
  assert.match(runtime, /public\.system_changes/);
  assert.match(runtime, /public\.system_change_candidates/);
  assert.match(runtime, /public\.system_change_requests/);
  assert.match(runtime, /executeProductionAiApiCommand/);
  assert.match(runtime, /operation_id: "runSandboxTest"/);
  assert.match(runtime, /production_mutation: false/);
  assert.match(runtime, /deployment_triggered: false/);

  assert.match(identity, /action:admin:SYS-01:ACT-CANDIDATE-CREATE/);
  assert.match(identity, /api:createCandidate/);
  assert.match(identity, /action:admin:SYS-01:ACT-CR-CREATE/);
  assert.match(identity, /api:createChangeRequest/);
  assert.match(identity, /api:runSandboxTest/);
  assert.match(identity, /authorizeSystemLifecycle/);
  assert.doesNotMatch(identity, /configureSystemLifecycleRuntime\([\s\S]{0,1400}PROVIDER_GATEWAY_NOT_MATERIALIZED/);

  assert.match(projection, /FROM public\.system_changes/);
  assert.match(projection, /FROM public\.system_change_candidates/);
  assert.match(migration, /CREATE TABLE IF NOT EXISTS public\.system_changes/);
  assert.match(migration, /ENABLE ROW LEVEL SECURITY/);
  assert.match(migration, /acpos_runtime\.can_access_system_change/);
  assert.match(migration, /PENDING-CR-SYS-0020/);
  assert.match(manifest, /0020_system_lifecycle_runtime/);
  assert.match(manifest, /22fb185cc50fa0d19d1431bd5e2fb6233ca28878dbafa7b65da9d44caba02b9f/);
  assert.match(manifest, /production_apply: BLOCKED_PENDING_HUMAN_APPROVAL_AND_PREVIEW_VALIDATION/);
});

test("SYS-01 0020 does not invent a second provider, audit, sandbox, or deployment system", async () => {
  const [runtime, migration] = await Promise.all([
    read("src/server/system/productionSystemLifecycleRuntime.ts"),
    read("database/migrations/0020_system_lifecycle_runtime.sql"),
  ]);
  assert.doesNotMatch(migration, /CREATE TABLE[^\n]+sandbox/i);
  assert.doesNotMatch(migration, /CREATE TABLE[^\n]+audit/i);
  assert.doesNotMatch(migration, /CREATE TABLE[^\n]+provider/i);
  assert.doesNotMatch(runtime, /executeSystemRelease/i);
  assert.match(runtime, /audit_events/);
  assert.match(runtime, /executeProductionAiApiCommand/);
});
