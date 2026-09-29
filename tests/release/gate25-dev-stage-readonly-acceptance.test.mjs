import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const ids=["DEV-01-BTN-STAGE-1","DEV-01-BTN-STAGE-2","DEV-01-BTN-STAGE-3","DEV-01-BTN-STAGE-4","DEV-01-BTN-STAGE-5"];

test("DEV-01 stage selectors remain UI-only and outside the formal permission denominator",async()=>{
  const bindings=await readFile("src/domain/dev/devControlBindings.ts","utf8");
  const visual=await readFile("src/components/pages/DevVisual.tsx","utf8");
  const runner=await readFile("scripts/gate25-production-dev-stage-readonly-acceptance.mjs","utf8");
  const inventory=JSON.parse(await readFile("docs/construction/evidence/PRODUCTION_FORMAL_CONTROL_ACTION_INVENTORY_2026-09-10.json","utf8"));
  const ledger=JSON.parse(await readFile("docs/construction/evidence/PRODUCTION_FORMAL_ACCEPTANCE_DISPOSITION_2026-09-10.json","utf8"));
  assert.equal(ledger.entries.length,1481);
  assert.equal(ledger.counts.PASS+ledger.counts.BLOCKED+ledger.counts.NOT_EXECUTED,1481);
  const inventoryKeys=new Set(inventory.resources.map(row=>row.resource_key));
  const ledgerKeys=new Set(ledger.entries.map(row=>row.resource_key));
  for(const id of ids){
    const line=bindings.split("\n").find(value=>value.includes(`"${id}"`));
    assert.ok(line,`MISSING_BINDING_${id}`);
    assert.match(line,/effect_type: "UI_CONTEXT_STATE"/);
    assert.match(line,/runtime_binding: "CLIENT_STATE_OR_VIEW_NO_API_REQUIRED"/);
    assert.doesNotMatch(line,/method_path:/);
    assert.equal(inventoryKeys.has(`control:${id}`),false,`DEV_STAGE_UNEXPECTED_FORMAL_INVENTORY_${id}`);
    assert.equal(ledgerKeys.has(`control:${id}`),false,`DEV_STAGE_UNEXPECTED_FORMAL_LEDGER_${id}`);
    assert.match(runner,new RegExp(id));
  }
  assert.match(visual,/onUiClick=\{\(\) => setActiveStage\(item\.key\)\}/);
  assert.match(runner,/effectfulRequests/);
  assert.match(runner,/effect_type:"UI_CONTEXT_STATE"/);
  assert.doesNotMatch(runner,/\/v1\/outreach\//);
  assert.doesNotMatch(runner,/invokeDevCommand/);
  assert.equal(ids.length,5);
});
