import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

test("Current formal acceptance ledger covers exact 1481 Production CONTROL+ACTION resources without aggregate DOM auto-pass",async()=>{
  const inventory=JSON.parse(await readFile("docs/construction/evidence/PRODUCTION_FORMAL_CONTROL_ACTION_INVENTORY_2026-09-10.json","utf8"));
  const ledger=JSON.parse(await readFile("docs/construction/evidence/PRODUCTION_FORMAL_ACCEPTANCE_DISPOSITION_2026-09-10.json","utf8"));
  assert.equal(inventory.resources.length,1481);
  assert.deepEqual(inventory.denominator,{controls:1155,actions:326,total:1481});
  assert.equal(ledger.entries.length,1481);
  assert.deepEqual(ledger.denominator,{controls:1155,actions:326,total:1481});
  const keys=new Set(ledger.entries.map(x=>x.resource_key));
  assert.equal(keys.size,1481);
  assert.equal(ledger.counts.PASS,5);
  assert.equal(ledger.counts.BLOCKED,48);
  assert.equal(ledger.counts.NOT_EXECUTED,1428);
  assert.equal(ledger.aggregate_dom_evidence.interactive,558);
  assert.equal(ledger.aggregate_dom_evidence.governed,558);
  assert.equal(ledger.aggregate_dom_evidence.per_resource_pass_propagation,false);
  for(const row of ledger.entries){
    assert.ok(["PASS","BLOCKED","NOT_EXECUTED"].includes(row.disposition));
    if(row.disposition==="PASS") assert.ok(Array.isArray(row.evidence_refs)&&row.evidence_refs.length>0);
    if(row.disposition==="BLOCKED"){
      assert.ok(row.reason_code);
      assert.ok(Array.isArray(row.evidence_refs)&&row.evidence_refs.length>0);
    }
    if(row.disposition==="NOT_EXECUTED") assert.ok(row.reason_code);
  }
});
