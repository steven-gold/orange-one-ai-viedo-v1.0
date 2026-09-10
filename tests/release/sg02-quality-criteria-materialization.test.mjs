import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const read=(p)=>readFile(p,"utf8");

test("SG-02 quality criteria approval materializes the canonical criteria owner",async()=>{
  const runtime=await read("src/server/iam/productionIamCommandRuntime.ts");
  const projection=await read("src/server/shared/pageCatalogProjectionRuntime.ts");
  for(const token of [
    'const SG02_PAGE_UID="admin:SG-02"',
    'const SG02_CRITERIA_RESOURCE_TYPE="quality_criteria_version"',
    "function qaCriteriaConfig",
    "SG02_CRITERIA_KEY_REQUIRED",
    "SG02_CRITERIA_VERSION_REQUIRED",
    "SG02_CRITERIA_DEPARTMENT_INVALID",
    "SG02_CRITERIA_DIMENSIONS_REQUIRED",
    "SG02_CRITERIA_REQUIRED_CHECKS_REQUIRED",
    "SG02_CRITERIA_GATE_POLICY_REQUIRED",
    "SG02_CRITERIA_RESOURCE_ID_INVALID",
    "SG02_ACTIVE_RESOURCE_IMMUTABLE",
    "SG02_CRITERIA_VERSION_CONFLICT",
    "SG02_CRITERIA_MATERIALIZATION_FAILED",
  ]) assert.ok(runtime.includes(token),token);

  assert.match(runtime,/INSERT INTO quality_criteria_versions\(/);
  assert.match(runtime,/criteria_version_id,criteria_key,version_no,department,dimensions,required_checks,gate_policy,status,content_hash/);
  assert.match(runtime,/'APPROVED'/);
  assert.match(runtime,/sha256\(stableJson\(canonical\)\)/);
  assert.match(runtime,/entityType:SG02_PAGE_UID/);
  assert.match(runtime,/await sql\.transaction\(\[/);
  assert.doesNotMatch(runtime,/SG02[\s\S]{0,800}max\(version_no\)/i);
  assert.doesNotMatch(runtime,/SG02[\s\S]{0,800}ORDER BY[^;]*(DESC|latest)/i);

  assert.match(projection,/FROM quality_criteria_versions/);
  assert.match(projection,/criteria_version_id::text AS criteria_version_id/);
  assert.match(projection,/CTRL-ADMIN-SG-02-ACT-01-ACT-CONFIGURE/);
  assert.match(projection,/CTRL-ADMIN-SG-02-ACT-02-ACT-APPROVE/);
});

test("SG-02 keeps non quality-criteria resources on the generic governed-resource path",async()=>{
  const runtime=await read("src/server/iam/productionIamCommandRuntime.ts");
  assert.match(runtime,/if\(text\(payload\.resource_type\)!==SG02_CRITERIA_RESOURCE_TYPE\)return null/);
  assert.match(runtime,/const row=await upsertEntity\(sql,\{kind:"GOVERNED_RESOURCE"/);
});
