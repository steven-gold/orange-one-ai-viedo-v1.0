import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const registry=await readFile("03_api/operation_registry.yaml","utf8");
const client=await readFile("src/domain/iam/productionIamClientRuntime.ts","utf8");
const control=await readFile("src/components/pages/IamControlRuntime.tsx","utf8");
const server=await readFile("src/server/iam/productionIamCommandRuntime.ts","utf8");
const binder=await readFile("src/server/shared/identityPageCommandRuntime.ts","utf8");
const projection=await readFile("src/server/shared/pageCatalogProjectionRuntime.ts","utf8");
const authority=await readFile("authority/pages/admin/IAM-01/ACPOS_IAM-01_ACCOUNT_PERMISSION_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml","utf8");

test("IAM production client and server runtimes are materialized without controlled-only binding",()=>{
  assert.match(client,/ensureProductionIamClientRuntime/);
  assert.match(control,/ensureProductionIamClientRuntime\(\)/);
  assert.match(server,/executeProductionIamCommand/);
  assert.match(binder,/executeProductionIamCommand/);
  assert.doesNotMatch(binder,/IAM01_WRITE_RUNTIME_NOT_MATERIALIZED/);
});

test("IAM Current operations use exact reused ACTION permission resources",()=>{
  const expected=[
    ["saveDraft","action:admin:IAM-02:ACT-DRAFT-SAVE"],
    ["validateDraft","action:admin:IAM-02:ACT-DRAFT-VALIDATE"],
    ["previewAuthorizationImpact","action:admin:IAM-02:ACT-ACCOUNT-PERMISSION-PREVIEW"],
    ["assignAccountPermission","action:admin:IAM-05:ACT-CONFIGURE"],
    ["revokeAccountPermission","action:admin:IAM-05:ACT-CONFIGURE"],
  ];
  for(const [operation,resource] of expected){
    assert.match(registry,new RegExp(`operation_id: ${operation}\\b[\\s\\S]*?authorization_resource_key: ${resource.replace(/[.*+?^$()|[\\]\\\\]/g,"\\\\$&")}`));
    assert.equal(binder.includes(resource),true,`server authorization missing ${resource}`);
  }
  assert.match(binder,/evaluateResourceAction/);
  assert.match(binder,/a\.action=\$\{action\}/);
  assert.match(binder,/PERMISSION_OR_SCOPE_DENIED/);
});

test("generic governance commands require explicit page permission context",()=>{
  for(const page of ["admin:IAM-01","admin:AIAPI-01","admin:SG-02"])assert.equal(registry.includes(page),true);
  assert.match(registry,/page_context_required: true/);
  assert.match(binder,/IAM_OPERATION_PERMISSION_CONTEXT_REQUIRED/);
  assert.match(binder,/IAM_OPERATION_PERMISSION_CONTEXT_UNREGISTERED/);
});

test("IAM L1 permission expansion is explicit and runtime inheritance remains forbidden",()=>{
  assert.match(authority,/runtime_inheritance:\s*FORBIDDEN/);
  assert.match(server,/WITH RECURSIVE resource_tree AS/);
  assert.match(server,/jsonb_array_elements_text/);
  assert.match(server,/permission_resources/);
  assert.doesNotMatch(server,/wildcard/i);
});

test("IAM HIGH-risk apply obtains a real approval reference before assignments",()=>{
  const approvalAt=client.indexOf("/approve");
  const assignmentAt=client.indexOf("/permissions");
  assert.ok(approvalAt>=0 && assignmentAt>=0 && approvalAt<assignmentAt);
  assert.match(client,/IAM_APPROVAL_REF_NOT_RETURNED/);
  assert.match(client,/approval_ref:approvalRef/);
  assert.match(server,/ACCOUNT_PERMISSION_HIGH_RISK_APPROVAL_REQUIRED/);
  assert.match(server,/approval_ref/);
});

test("unresolved identity candidate fields remain fail-closed instead of invented",()=>{
  assert.match(authority,/do not invent username\/email\/department\/position\/identity-source fields/i);
  assert.match(projection,/identity_schema:\s*\[\]/);
  assert.match(projection,/department_presets:\s*\[\]/);
  assert.doesNotMatch(client,/username.*required|password.*required/i);
});
