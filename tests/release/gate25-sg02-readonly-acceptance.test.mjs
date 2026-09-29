import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

test("Gate25 SG-02 Production acceptance is exact and bounded to nine readonly drawer controls",async()=>{
  const source=await readFile("scripts/gate25-production-sg02-readonly-acceptance.mjs","utf8");
  const ids=[...source.matchAll(/CTRL-ADMIN-SG-02-[A-Z0-9-]+/g)].map(m=>m[0]);
  const unique=[...new Set(ids)];
  assert.equal(unique.length,9);
  assert.equal(ids.length,9);
  assert.match(source,/\/v1\/ui-projections\/admin:SG-02/);
  assert.match(source,/request\(\)\.method\(\)===\"GET\"/);
  assert.match(source,/data-operation-id/);
  assert.match(source,/getUiProjection/);
  assert.match(source,/data-detail-drawer=\"SG-02\"/);
  assert.match(source,/context\.request\.post\(`\$\{base\}\/v1\/identity\/session`/);
  assert.match(source,/context\.request\.delete\(`\$\{base\}\/v1\/identity\/session`/);
  assert.doesNotMatch(source,/configureGovernedResource|approveGovernedResource|PATCH \/v1\/governance|\/approve/);
  assert.match(source,/GATE25_SG02_READONLY_PRODUCTION_PASS/);
  assert.match(source,/GATE25_SG02_READONLY_PRODUCTION_EVIDENCE/);
});
