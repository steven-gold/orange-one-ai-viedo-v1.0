import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const contract = await readFile("src/domain/iam/iamRuntimeContract.ts", "utf8");
const projection = await readFile("src/server/iam/iamProjectionRuntime.ts", "utf8");
const uiRuntime = await readFile("src/server/shared/uiProjectionRuntime.ts", "utf8");

test("IAM L1 page mapping is owned by the shared IAM domain contract", () => {
  assert.match(contract, /IAM_FRONT_L1_PAGE_UID/);
  assert.match(contract, /IAM_ADMIN_L1_PAGE_UID/);
  assert.match(contract, /IAM_L1_PAGE_UID/);
  assert.match(projection, /IAM_FRONT_L1_PAGE_UID/);
  assert.match(projection, /IAM_ADMIN_L1_PAGE_UID/);
});

test("production IAM projection reads canonical identity session permission and audit owners", () => {
  for (const owner of [
    "public.app_users",
    "acpos_runtime.accounts",
    "acpos_runtime.sessions",
    "public.account_permission_assignments",
    "public.permission_resources",
    "public.audit_events",
  ]) assert.equal(projection.includes(owner), true, `missing canonical owner ${owner}`);
  assert.match(projection, /active_session_count/);
  assert.match(projection, /front_l1:/);
  assert.match(projection, /admin_l1:/);
  assert.match(projection, /audit_entries:/);
  assert.doesNotMatch(projection, /LOCAL_PASSWORD/);
});

test("IAM-01 non-controlled UI projection is bound to the production materializer", () => {
  assert.match(uiRuntime, /readProductionIamProjection/);
  assert.match(uiRuntime, /request\.page_uid==="admin:IAM-01"/);
  assert.match(uiRuntime, /const productionIam=await readProductionIamProjection\(request\)/);
});
