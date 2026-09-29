import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read=(path)=>readFile(path,"utf8");

test("IAM-01 Current Authority operations remain mapped to existing Production IAM owner",async()=>{
  const authority=await read("authority/pages/admin/IAM-01/ACPOS_IAM-01_ACCOUNT_PERMISSION_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml");
  const identity=await read("src/server/shared/identityPageCommandRuntime.ts");
  const runtime=await read("src/server/iam/productionIamCommandRuntime.ts");

  for(const operation of [
    "searchProjection",
    "saveDraft",
    "validateDraft",
    "configureGovernedResource",
    "previewAuthorizationImpact",
    "assignAccountPermission",
    "revokeAccountPermission",
    "approveGovernedResource",
  ]) assert.match(authority,new RegExp("operation: "+operation));

  assert.match(identity,/searchProjection:\{resource_key:"action:admin:IAM-01:ACT-SEARCH"/);
  assert.match(identity,/saveDraft:\{resource_key:"action:admin:IAM-02:ACT-DRAFT-SAVE"/);
  assert.match(identity,/validateDraft:\{resource_key:"action:admin:IAM-02:ACT-DRAFT-VALIDATE"/);
  assert.match(identity,/previewAuthorizationImpact:\{resource_key:"action:admin:IAM-02:ACT-ACCOUNT-PERMISSION-PREVIEW"/);
  assert.match(identity,/assignAccountPermission:\{resource_key:"action:admin:IAM-05:ACT-CONFIGURE"/);
  assert.match(identity,/revokeAccountPermission:\{resource_key:"action:admin:IAM-05:ACT-CONFIGURE"/);
  assert.match(identity,/"admin:IAM-01":[\s\S]*action:admin:IAM-05:ACT-CONFIGURE[\s\S]*action:admin:IAM-05:ACT-APPROVE/);

  assert.match(runtime,/case"searchProjection"/);
  assert.match(runtime,/case"saveDraft"/);
  assert.match(runtime,/case"validateDraft"/);
  assert.match(runtime,/case"previewAuthorizationImpact"/);
  assert.match(runtime,/case"configureGovernedResource"/);
  assert.match(runtime,/case"approveGovernedResource"/);
  assert.match(runtime,/case"assignAccountPermission"/);
  assert.match(runtime,/case"revokeAccountPermission"/);
});

test("migration 0026 stages six existing IAM ACTION assignments and no new authority objects",async()=>{
  const migration=await read("database/migrations/0026_iam_operation_permission_closure.sql");
  const manifest=await read("database/migrations/migration_checksum_manifest.yaml");
  const neonRuntime=await read("src/server/database/neonRuntime.ts");

  for(const resource of [
    "action:admin:IAM-01:ACT-SEARCH",
    "action:admin:IAM-02:ACT-DRAFT-SAVE",
    "action:admin:IAM-02:ACT-DRAFT-VALIDATE",
    "action:admin:IAM-02:ACT-ACCOUNT-PERMISSION-PREVIEW",
    "action:admin:IAM-05:ACT-CONFIGURE",
    "action:admin:IAM-05:ACT-APPROVE",
  ]) assert.match(migration,new RegExp(resource.replaceAll(":","\\:")));

  assert.match(migration,/resource_count <> 6/);
  assert.match(migration,/approved_allow_count <> 6/);
  assert.match(migration,/ON CONFLICT \(user_id,resource_id,action,version_no\) DO NOTHING/);
  assert.match(migration,/642d77e5f54bc5d922e6325d7a22d28ec7e2e3d2eb8b8005e493a8c0aea52cfe/);
  assert.doesNotMatch(migration,/INSERT INTO public\.permission_resources/);
  assert.doesNotMatch(migration,/CREATE TABLE|ALTER TABLE|CREATE ROLE|ALTER ROLE/);

  assert.match(manifest,/migration_id: 0026_iam_operation_permission_closure/);
  assert.match(manifest,/payload_sha256: 642d77e5f54bc5d922e6325d7a22d28ec7e2e3d2eb8b8005e493a8c0aea52cfe/);
  assert.match(manifest,/approval_ref: CR-IAM-0026-PENDING-PRODUCTION-APPLY/);
  assert.ok(Number(neonRuntime.match(/MAX_SUPPORTED_MIGRATION_COUNT = (\d+)/)?.[1]??0)>=26);
});
