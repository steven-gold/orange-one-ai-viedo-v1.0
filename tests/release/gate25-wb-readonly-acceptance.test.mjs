import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

test("Gate25 WB-01 Production acceptance is exact, readonly, and bounded to 14 OPEN controls",async()=>{
  const source=await readFile("scripts/gate25-production-wb-readonly-acceptance.mjs","utf8");
  const ids=[...source.matchAll(/CTRL-WORKSPACE-WB-01-[A-Z0-9-]+-OPEN/g)].map(m=>m[0]);
  const unique=[...new Set(ids)];
  assert.equal(unique.length,14);
  assert.equal(ids.length,14);
  assert.match(source,/production/);
  assert.match(source,/release_sha/);
  assert.match(source,/\/v1\/dashboard\/read-model/);
  assert.match(source,/r\.request\(\)\.method\(\)===\"GET\"/);
  assert.match(source,/data-drawer-section-key/);
  assert.match(source,/data-drawer-state/);
  assert.match(source,/document\.activeElement/);
  assert.match(source,/context\.request\.post\(`\$\{base\}\/v1\/identity\/session`/);
  assert.match(source,/context\.request\.delete\(`\$\{base\}\/v1\/identity\/session`/);
  assert.doesNotMatch(source,/queue\/probe|configureGovernedResource|approveGovernedResource|assignAccountPermission|revokeAccountPermission|createCanonicalScriptVersion|compileWorkPackage/);
  assert.doesNotMatch(source,/method\(\)===\"POST\".*dashboard\/read-model/);
  assert.match(source,/GATE25_WB_READONLY_PRODUCTION_PASS/);
  assert.match(source,/GATE25_WB_READONLY_PRODUCTION_EVIDENCE/);
});
