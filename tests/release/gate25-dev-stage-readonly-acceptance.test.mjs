import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const ids=["DEV-01-BTN-STAGE-1","DEV-01-BTN-STAGE-2","DEV-01-BTN-STAGE-3","DEV-01-BTN-STAGE-4","DEV-01-BTN-STAGE-5"];

test("DEV-01 stage selectors are exact NOT_EXECUTED UI-only Gate25 candidates",async()=>{
  const bindings=await readFile("src/domain/dev/devControlBindings.ts","utf8");
  const visual=await readFile("src/components/pages/DevVisual.tsx","utf8");
  const runner=await readFile("scripts/gate25-production-dev-stage-readonly-acceptance.mjs","utf8");
  const ledger=JSON.parse(await readFile("docs/construction/evidence/PRODUCTION_FORMAL_ACCEPTANCE_DISPOSITION_2026-09-10.json","utf8"));
  assert.deepEqual(ledger.counts,{PASS:28,BLOCKED:72,NOT_EXECUTED:1381});
  const rows=new Map(ledger.entries.map(row=>[row.resource_key,row]));
  for(const id of ids){
    const line=bindings.split("\n").find(value=>value.includes(`"${id}"`));
    assert.ok(line,`MISSING_BINDING_${id}`);
    assert.match(line,/effect_type: "UI_CONTEXT_STATE"/);
    assert.match(line,/runtime_binding: "CLIENT_STATE_OR_VIEW_NO_API_REQUIRED"/);
    assert.doesNotMatch(line,/method_path:/);
    const row=rows.get(`control:${id}`);
    assert.ok(row,`MISSING_LEDGER_RESOURCE_${id}`);
    assert.equal(row.disposition,"NOT_EXECUTED",`DEV_STAGE_LEDGER_NOT_NOT_EXECUTED_${id}`);
    assert.match(runner,new RegExp(id));
  }
  assert.match(visual,/onUiClick=\{\(\) => setActiveStage\(item\.key\)\}/);
  assert.match(runner,/effectfulRequests/);
  assert.match(runner,/effect_type:"UI_CONTEXT_STATE"/);
  assert.doesNotMatch(runner,/\/v1\/outreach\//);
  assert.doesNotMatch(runner,/invokeDevCommand/);
  assert.equal(ids.length,5);
});
