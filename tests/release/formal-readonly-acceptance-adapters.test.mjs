import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

test("Production formal read-only adapters are exact Current formal resources and never mutate Provider state",async()=>{
  const adapters=JSON.parse(await readFile("docs/construction/evidence/PRODUCTION_FORMAL_ACCEPTANCE_DIRECT_ADAPTERS_2026-09-10.json","utf8"));
  const inventory=JSON.parse(await readFile("docs/construction/evidence/PRODUCTION_FORMAL_CONTROL_ACTION_INVENTORY_2026-09-10.json","utf8"));
  const script=await readFile("scripts/production-formal-readonly-acceptance.mjs","utf8");
  const keys=new Set(inventory.resources.map(x=>x.resource_key));
  assert.equal(adapters.executable_readonly_now.length,4);
  for(const a of adapters.executable_readonly_now){
    assert.ok(keys.has(a.resource_key));
    assert.equal(a.method,"GET");
    assert.equal(a.mutation,false);
    assert.equal(a.external_provider_call,false);
    assert.ok(script.includes(a.operation_id));
    assert.ok(script.includes(a.resource_key));
  }
  assert.ok(!script.includes('method:"PATCH"'));
  assert.ok(!script.includes('method:"PUT"'));
  assert.ok(!script.includes('method:"POST",cache:"no-store",headers:cookieHeaders(cookie)'));
  assert.ok(script.includes("PRODUCTION_FORMAL_READONLY_ACCEPTANCE_PASS resources=4 mutations=0 external_provider_calls=0"));
});
