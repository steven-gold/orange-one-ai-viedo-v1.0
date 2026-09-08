import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const read=(p)=>readFile(p,"utf8");

test("shared correction version authority and routes are materialized",async()=>{
  const authority=await read("authority/runtime/ACPOS_SHARED_RUNTIME_OPERATION_AUTHORITY_V1.0.yaml");
  const operationRegistry=await read("03_api/operation_registry.yaml");
  const payloadRegistry=await read("03_api/business_payload_registry.yaml");
  for(const operation of ["generateCorrectionScriptCandidate","approveCorrectionScriptCandidate","restoreAssetVersionAsNewDraft","lockAssetVersion","lockVideoVersion"]){
    assert.ok(authority.includes(operation),operation);
    assert.ok(operationRegistry.includes(`operation_id: ${operation}`),operation);
    assert.ok(payloadRegistry.includes(`operation_id: ${operation}`),operation);
  }
  assert.match(authority,/Human correction candidate canonical owner is public\.correction_script_versions/);
  assert.match(authority,/Restore as New Draft creates lineage-only draft state/);
  assert.match(authority,/Locked source outputs are never overwritten/);
  for(const path of [
    "src/app/v1/state-commands/correctionscript/generate/route.ts",
    "src/app/v1/state-commands/correctionscript/approve/route.ts",
    "src/app/v1/state-commands/assetversion/restoreasnewdraft/route.ts",
    "src/app/v1/state-commands/assetversion/lock/route.ts",
    "src/app/v1/state-commands/videoversion/lock/route.ts",
  ]) assert.match(await read(path),/sharedProductionPost/);
});

test("shared production runtime requires PAGE ACTION CONTROL API authorization",async()=>{
  const identity=await read("src/server/shared/identityPageCommandRuntime.ts");
  const runtime=await read("src/server/shared/productionSharedOperationRuntime.ts");
  assert.match(identity,/configureSharedProductionOperationRuntime/);
  assert.match(identity,/authorizeSharedProductionOperation/);
  assert.match(identity,/evaluatePageView/);
  for(const key of [
    "action:workspace:ASSET-01:ACT-CORRECTION-GENERATE",
    "control:workspace:ASSET-01:ASSET-01-BTN-CORRECTION-GENERATE",
    "api:generateCorrectionScriptCandidate",
    "action:workspace:VIDEO-01:ACT-CORRECTION-APPROVE",
    "control:workspace:VIDEO-01:VIDEO-01-BTN-APPROVE-CORRECTION",
    "api:approveCorrectionScriptCandidate",
    "api:restoreAssetVersionAsNewDraft","api:lockAssetVersion","api:lockVideoVersion",
  ]) assert.ok(identity.includes(key),key);
  assert.match(runtime,/public\.correction_script_versions/);
  assert.match(runtime,/CORRECTION_PROVIDER_ROUTE_NOT_SUCCESS/);
  assert.match(runtime,/production_output_version_locks/);
  assert.match(runtime,/asset_version_restore_drafts/);
  assert.match(runtime,/VIDEO_SCORE_BELOW_LOCK_THRESHOLD/);
  assert.match(runtime,/USER_REQUESTED_RESTORE_AS_NEW_DRAFT/);
});

test("client shared operations use formal state-command routes and correction execution carries exact approval",async()=>{
  const adapters=await read("src/domain/catalog/identityClientCommandAdapters.ts");
  assert.doesNotMatch(adapters,/SHARED_OPERATION_AUTHORITY_NOT_MATERIALIZED/);
  for(const path of [
    "/v1/state-commands/correctionscript/generate",
    "/v1/state-commands/correctionscript/approve",
    "/v1/state-commands/assetversion/restoreasnewdraft",
    "/v1/state-commands/assetversion/lock",
    "/v1/state-commands/videoversion/lock",
  ]) assert.ok(adapters.includes(path),path);
  assert.match(adapters,/approved_candidate_ref:approved/);
  assert.match(adapters,/mode:"CORRECTION"/);
});

test("department correction execution consumes exact APPROVED candidate and never overwrites locked source",async()=>{
  const runtime=await read("src/server/shared/productionDepartmentPortRuntime.ts");
  for(const token of [
    "APPROVED_CORRECTION_CANDIDATE_REQUIRED","HUMAN_APPROVED_CORRECTION_REQUIRED",
    "CORRECTION_INPUT_FINGERPRINT_STALE","CORRECTION_INSTRUCTION_LINEAGE_STALE",
    "CORRECTION_BLUEPRINT_LINEAGE_STALE","LOCKED_SOURCE_OUTPUT_CORRECTION_FORBIDDEN",
  ]) assert.ok(runtime.includes(token),token);
  assert.match(runtime,/canonical_instruction:canonicalInstruction/);
  assert.match(runtime,/approved_correction_candidate_ref/);
  assert.match(runtime,/correction_source_output_version_id/);
  assert.match(runtime,/INSERT INTO acpos_runtime\.correction_runs/);
  assert.match(runtime,/SET status='RECHECK'/);
  assert.match(runtime,/INSERT INTO public\.task_outputs/);
});

test("ASSET VIDEO projections expose exact correction and version lineage",async()=>{
  const projection=await read("src/server/shared/pageCatalogProjectionRuntime.ts");
  for(const owner of [
    "correction_script_versions","production_output_version_locks","asset_version_restore_drafts",
    "correction_candidate_id","approved_correction_candidate_id","locked_version_ref",
  ]) assert.ok(projection.includes(owner),owner);
  assert.match(projection,/CANDIDATE_OUTPUT/);
  assert.match(projection,/WAIT_CONFIRMATION/);
  assert.match(projection,/CONFIRMED/);
  assert.match(projection,/LOCKED/);
  assert.match(projection,/HANDOFF/);
});

test("migration 0034 seals minimum shared permission RLS and migration ceiling",async()=>{
  const migration=await read("database/migrations/0034_shared_correction_version_runtime_closure.sql");
  const manifest=await read("database/migrations/migration_checksum_manifest.yaml");
  const neon=await read("src/server/database/neonRuntime.ts");
  assert.match(migration,/SHARED0034_PERMISSION_RESOURCE_COUNT_MISMATCH/);
  assert.match(migration,/n<>19/);
  assert.match(migration,/a<>19/);
  assert.match(migration,/SHARED0034_RLS_POLICY_COUNT_MISMATCH/);
  assert.match(migration,/p<>8/);
  assert.match(migration,/SHARED0034_RUNTIME_TABLE_GRANT_COUNT_MISMATCH/);
  assert.match(migration,/g<>6/);
  assert.match(migration,/SHARED0034_RUNTIME_COLUMN_GRANT_COUNT_MISMATCH/);
  assert.match(migration,/cg<>6/);
  assert.match(migration,/production_output_version_locks/);
  assert.match(migration,/asset_version_restore_drafts/);
  assert.match(migration,/861adc15e7bb255290fca7d253bed197cc757baf601f5da5887b0ef62fbee83c/);
  assert.match(manifest,/0034_shared_correction_version_runtime_closure/);
  assert.match(manifest,/861adc15e7bb255290fca7d253bed197cc757baf601f5da5887b0ef62fbee83c/);
  assert.match(neon,/MAX_SUPPORTED_MIGRATION_COUNT = 34/);
});
