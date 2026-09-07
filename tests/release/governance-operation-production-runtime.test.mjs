import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("SG-02 and Strategy governance reuse the existing governed-resource owner with distinct current/source permission context", async () => {
  const identity = await read("src/server/shared/identityPageCommandRuntime.ts");
  const iam = await read("src/server/iam/productionIamCommandRuntime.ts");
  const strategy = await read("src/domain/strategyAdmin/strategyAdminRuntimePort.ts");
  const adapters = await read("src/domain/catalog/identityClientCommandAdapters.ts");
  const qa = await read("src/domain/qaCriteria/qaCriteriaRuntimePort.ts");

  assert.match(identity, /"admin:SG-02":[\s\S]*action:admin:SG-02:ACT-CONFIGURE[\s\S]*action:admin:SG-02:ACT-APPROVE/);
  assert.match(identity, /"admin:STR-02":[\s\S]*action:admin:STR-02:ACT-CONFIGURE[\s\S]*action:admin:STR-02:ACT-APPROVE/);
  assert.match(identity, /currentPageUid=asText\(payload\.current_page_uid\)\?\?asText\(payload\.page_uid\)/);
  assert.match(identity, /sourcePageUid=asText\(payload\.source_page_uid\)\?\?asText\(payload\.page_uid\)/);

  assert.match(iam, /async function configureResource/);
  assert.match(iam, /kind:"GOVERNED_RESOURCE"/);
  assert.match(iam, /async function approveResource/);
  assert.match(iam, /operation:"configureGovernedResource"/);
  assert.match(iam, /operation:"approveGovernedResource"/);

  assert.match(strategy, /intelligence:[\s\S]*"ACT-CONFIGURE": "admin:STR-02"[\s\S]*"ACT-APPROVE": "admin:STR-02"/);
  assert.match(adapters, /current_page_uid: "admin:STR-01"/);
  assert.match(adapters, /source_page_uid: input\.source_page_uid/);
  assert.match(qa, /page_uid: "admin:SG-02"/);
});

test("migration 0025 stages only the four existing governance operation assignments", async () => {
  const migration = await read("database/migrations/0025_governance_operation_permission_closure.sql");
  const manifest = await read("database/migrations/migration_checksum_manifest.yaml");
  const neonRuntime = await read("src/server/database/neonRuntime.ts");

  assert.match(migration, /action:admin:SG-02:ACT-CONFIGURE/);
  assert.match(migration, /action:admin:SG-02:ACT-APPROVE/);
  assert.match(migration, /action:admin:STR-02:ACT-CONFIGURE/);
  assert.match(migration, /action:admin:STR-02:ACT-APPROVE/);
  assert.match(migration, /resource_count <> 4/);
  assert.match(migration, /approved_allow_count <> 4/);
  assert.match(migration, /ON CONFLICT \(user_id,resource_id,action,version_no\) DO NOTHING/);
  assert.match(migration, /current_page_uid/);
  assert.match(migration, /source_page_uid/);
  assert.match(migration, /c95ea4cb98a21749b962abe4f43b28ee3b2552e3505d85704c9c3903be2e3c23/);
  assert.doesNotMatch(migration, /INSERT INTO public\.permission_resources/);
  assert.doesNotMatch(migration, /CREATE TABLE|ALTER TABLE|CREATE ROLE|ALTER ROLE/);

  assert.match(manifest, /migration_id: 0025_governance_operation_permission_closure/);
  assert.match(manifest, /payload_sha256: c95ea4cb98a21749b962abe4f43b28ee3b2552e3505d85704c9c3903be2e3c23/);
  assert.match(manifest, /approval_ref: CR-GOV-0025-PENDING-PRODUCTION-APPLY/);
  assert.ok(Number(neonRuntime.match(/MAX_SUPPORTED_MIGRATION_COUNT = (\d+)/)?.[1] ?? 0) >= 25);
});
