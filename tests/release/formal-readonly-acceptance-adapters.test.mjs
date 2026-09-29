import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

test("Production formal read-only adapters are exact Current formal resources and never mutate Provider state",async()=>{
  const adapters=JSON.parse(await readFile("docs/construction/evidence/PRODUCTION_FORMAL_ACCEPTANCE_DIRECT_ADAPTERS_2026-09-10.json","utf8"));
  const inventory=JSON.parse(await readFile("docs/construction/evidence/PRODUCTION_FORMAL_CONTROL_ACTION_INVENTORY_2026-09-10.json","utf8"));
  const script=await readFile("scripts/production-formal-readonly-acceptance.mjs","utf8");
  const keys=new Set(inventory.resources.map(x=>x.resource_key));
  assert.equal(adapters.exact_direct_mapping_count,25);
  assert.equal(adapters.executable_readonly_now.length,5);
  assert.equal(adapters.mapped_not_yet_executable_count,20);
  assert.equal(adapters.mapped_not_yet_executable.length,20);
  assert.deepEqual(adapters.classification_summary,{PASS_READONLY:5,BLOCKED_SAFE_ACCEPTANCE_CONTRACT:20,UNCLASSIFIED:0});
  const directKeys=new Set();
  for(const a of adapters.executable_readonly_now){
    assert.ok(keys.has(a.resource_key));
    assert.ok(!directKeys.has(a.resource_key),`duplicate direct resource ${a.resource_key}`);
    directKeys.add(a.resource_key);
    assert.ok(a.method==="GET"||(a.resource_key==="action:admin:IAM-01:ACT-SEARCH"&&a.method==="POST"&&a.effect==="READ"));
    assert.equal(a.mutation,false);
    assert.equal(a.external_provider_call,false);
    assert.ok(script.includes(a.operation_id));
    assert.ok(script.includes(a.resource_key));
  }
  for(const a of adapters.mapped_not_yet_executable){
    assert.ok(keys.has(a.resource_key),`blocked direct resource missing from inventory ${a.resource_key}`);
    assert.ok(!directKeys.has(a.resource_key),`duplicate direct resource ${a.resource_key}`);
    directKeys.add(a.resource_key);
    assert.ok(Array.isArray(a.operation_ids)&&a.operation_ids.length>0,`operation_ids missing ${a.resource_key}`);
    assert.ok(typeof a.path==="string"&&a.path.length>0,`path missing ${a.resource_key}`);
    assert.ok(typeof a.effect==="string"&&a.effect.length>0,`effect missing ${a.resource_key}`);
    assert.ok(typeof a.reason_code==="string"&&a.reason_code.length>0,`reason_code missing ${a.resource_key}`);
    assert.ok(typeof a.detail==="string"&&a.detail.length>0,`detail missing ${a.resource_key}`);
  }
  assert.equal(directKeys.size,25);
  assert.ok(!script.includes('method:"PATCH"'));
  assert.ok(!script.includes('method:"PUT"'));
  assert.ok(script.includes('response.headers.get("x-correlation-id")'));
  assert.ok(script.includes("PRODUCTION_FORMAL_READONLY_ACCEPTANCE_PASS resources=5 mutations=0 external_provider_calls=0"));
});

test("IAM Search adapter honors raw infoPost success body and correlation header contract",async()=>{
  const script=await readFile("scripts/production-formal-readonly-acceptance.mjs","utf8");
  const start=script.indexOf("async function callReadPost");
  const end=script.indexOf("assert(email&&password",start);
  const block=script.slice(start,end);
  assert.ok(start>=0&&end>start);
  assert.match(block,/response\.headers\.get\("x-correlation-id"\)/);
  assert.match(block,/validate\(body\)/);
  assert.doesNotMatch(block,/body\?\.ok===true/);
  assert.doesNotMatch(block,/validate\(body\.value\)/);
});
