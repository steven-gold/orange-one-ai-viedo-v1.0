import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const read=(p)=>readFile(p,"utf8");

test("ASSET VIDEO Production runtime is explicitly bound",async()=>{
  const identity=await read("src/server/shared/identityPageCommandRuntime.ts");
  const runtime=await read("src/server/shared/productionDepartmentPortRuntime.ts");
  assert.match(identity,/configureAssetRuntime\(\{/);
  assert.match(identity,/configureVideoRuntime\(\{/);
  assert.match(identity,/executeProductionDepartmentPort\("ASSET"/);
  assert.match(identity,/executeProductionDepartmentPort\("VIDEO"/);
  assert.match(identity,/DEPARTMENT_PERMISSION/);
  for(const key of ["api:requestTaskExecution","api:retryTaskExecution","api:decideOutputCandidate","api:submitScorecard","api:createFinding","api:createCorrectionRequest","api:createDepartmentHandoff"]) assert.ok(identity.includes(key),key);
  assert.match(runtime,/INSTRUCTION_PACKAGE_NOT_READY/);
  assert.match(runtime,/ROUTE_POLICY_NOT_READY/);
  assert.match(runtime,/executeProductionAiApiCommand/);
  assert.match(runtime,/CANDIDATE_OUTPUT/);
  assert.match(runtime,/HANDOFF_READY/);
});

test("ASSET Production RequestBuilder covers formal current ports",async()=>{
  const adapters=await read("src/domain/catalog/identityClientCommandAdapters.ts");
  assert.match(adapters,/configureAssetRequestBuilder\(\{/);
  for(const action of ["ASSET-01-ACT-FLOW-START","ASSET-01-ACT-EVALUATE","ASSET-01-ACT-CANDIDATE-CONFIRM","ASSET-01-ACT-CORRECTION-EXECUTE","ASSET-01-ACT-TASK-RETRY","ASSET-01-ACT-HANDOFF","ASSET-01-ACT-LAYER-DOC-CREATE","ASSET-01-ACT-PATCH-CREATE"]) assert.ok(adapters.includes(action),action);
  assert.match(adapters,/configureAssetSharedRuntime\(\{/);
  assert.match(adapters,/configureVideoSharedRuntime\(\{/);
  assert.doesNotMatch(adapters,/ASSET_REQUEST_ADAPTER_NOT_BOUND/);
});

test("migration 0033 remains immutable while later migration ceiling advances",async()=>{
  const migration=await read("database/migrations/0033_asset_video_department_runtime_permission_rls_closure.sql");
  const manifest=await read("database/migrations/migration_checksum_manifest.yaml");
  const neon=await read("src/server/database/neonRuntime.ts");
  assert.match(migration,/resource_count<>35/);
  assert.match(migration,/approved_allow_count<>35/);
  assert.match(migration,/DEPT0033_ASSIGNMENT_COUNT_MISMATCH/);
  assert.match(migration,/acpos_task_input_manifests_department_select/);
  assert.match(migration,/acpos_provider_jobs_department_insert/);
  assert.match(migration,/7bb4797ce24c1bba93572b0ec55f5ea6baf7297fc2f0687e95564a556f925c71/);
  assert.doesNotMatch(migration,/INSERT INTO public\.permission_resources/);
  assert.match(manifest,/0033_asset_video_department_runtime_permission_rls_closure/);
  assert.match(manifest,/7bb4797ce24c1bba93572b0ec55f5ea6baf7297fc2f0687e95564a556f925c71/);
  assert.ok(Number(neon.match(/MAX_SUPPORTED_MIGRATION_COUNT = (\\d+)/)?.[1] ?? 0) >= 33);
});
