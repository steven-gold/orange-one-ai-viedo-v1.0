import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

test("Current formal acceptance ledger covers exact 1481 Production CONTROL+ACTION resources without aggregate DOM auto-pass",async()=>{
  const inventory=JSON.parse(await readFile("docs/construction/evidence/PRODUCTION_FORMAL_CONTROL_ACTION_INVENTORY_2026-09-10.json","utf8"));
  const ledger=JSON.parse(await readFile("docs/construction/evidence/PRODUCTION_FORMAL_ACCEPTANCE_DISPOSITION_2026-09-10.json","utf8"));
  const sync=JSON.parse(await readFile("docs/construction/evidence/GATE25_DIRECT_BLOCKER_LEDGER_SYNC_2026-09-10.json","utf8"));
  assert.equal(inventory.resources.length,1481);
  assert.deepEqual(inventory.denominator,{controls:1155,actions:326,total:1481});
  assert.equal(ledger.entries.length,1481);
  assert.deepEqual(ledger.denominator,{controls:1155,actions:326,total:1481});
  const keys=new Set(ledger.entries.map(x=>x.resource_key));
  assert.equal(keys.size,1481);
  assert.deepEqual(ledger.counts,{PASS:5,BLOCKED:68,NOT_EXECUTED:1408});
  assert.equal(ledger.aggregate_dom_evidence.interactive,558);
  assert.equal(ledger.aggregate_dom_evidence.governed,558);
  assert.equal(ledger.aggregate_dom_evidence.per_resource_pass_propagation,false);
  assert.equal(sync.status,"PHYSICAL_LEDGER_SYNCED");
  assert.equal(sync.direct_mapping_count,25);
  assert.equal(sync.pass_readonly,5);
  assert.equal(sync.blocker_resources,20);
  assert.equal(sync.newly_blocked,20);
  assert.equal(sync.already_blocked,0);
  assert.deepEqual(sync.counts_before,{PASS:5,BLOCKED:48,NOT_EXECUTED:1428});
  assert.deepEqual(sync.counts_after,ledger.counts);
  assert.equal(sync.synced_resource_keys.length,20);
  const synced=new Set(sync.synced_resource_keys);
  assert.equal(synced.size,20);
  for(const row of ledger.entries){
    assert.ok(["PASS","BLOCKED","NOT_EXECUTED"].includes(row.disposition));
    if(row.disposition==="PASS") assert.ok(Array.isArray(row.evidence_refs)&&row.evidence_refs.length>0);
    if(row.disposition==="BLOCKED"){
      assert.ok(row.reason_code);
      assert.ok(Array.isArray(row.evidence_refs)&&row.evidence_refs.length>0);
    }
    if(row.disposition==="NOT_EXECUTED") assert.ok(row.reason_code);
    if(synced.has(row.resource_key)){
      assert.equal(row.disposition,"BLOCKED");
      assert.ok(row.evidence_refs.includes("docs/construction/evidence/PRODUCTION_FORMAL_ACCEPTANCE_DIRECT_ADAPTERS_2026-09-10.json"));
      assert.ok(row.blocker_detail);
      assert.ok(Array.isArray(row.operation_ids)&&row.operation_ids.length>0);
    }
  }
});
