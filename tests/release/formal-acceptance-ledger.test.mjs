import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

test("Current formal acceptance ledger covers exact 1481 Production CONTROL+ACTION resources without aggregate DOM auto-pass",async()=>{
  const inventory=JSON.parse(await readFile("docs/construction/evidence/PRODUCTION_FORMAL_CONTROL_ACTION_INVENTORY_2026-09-10.json","utf8"));
  const ledger=JSON.parse(await readFile("docs/construction/evidence/PRODUCTION_FORMAL_ACCEPTANCE_DISPOSITION_2026-09-10.json","utf8"));
  const directSync=JSON.parse(await readFile("docs/construction/evidence/GATE25_DIRECT_BLOCKER_LEDGER_SYNC_2026-09-10.json","utf8"));
  const productionDomEvidence=JSON.parse(await readFile("docs/construction/evidence/GATE25_PRODUCTION_DOM_FORMAL_RESOURCE_EVIDENCE_2026-09-10.json","utf8"));
  const productionDomSync=JSON.parse(await readFile("docs/construction/evidence/GATE25_PRODUCTION_DOM_BLOCKER_LEDGER_SYNC_2026-09-10.json","utf8"));
  assert.equal(inventory.resources.length,1481);
  assert.deepEqual(inventory.denominator,{controls:1155,actions:326,total:1481});
  assert.equal(ledger.entries.length,1481);
  assert.deepEqual(ledger.denominator,{controls:1155,actions:326,total:1481});
  const keys=new Set(ledger.entries.map(x=>x.resource_key));
  assert.equal(keys.size,1481);
  assert.deepEqual(ledger.counts,{PASS:29,BLOCKED:108,NOT_EXECUTED:1344});
  assert.equal(ledger.aggregate_dom_evidence.interactive,558);
  assert.equal(ledger.aggregate_dom_evidence.governed,558);
  assert.equal(ledger.aggregate_dom_evidence.per_resource_pass_propagation,false);

  assert.equal(directSync.status,"PHYSICAL_LEDGER_SYNCED");
  assert.equal(directSync.direct_mapping_count,25);
  assert.equal(directSync.pass_readonly,5);
  assert.equal(directSync.blocker_resources,20);
  assert.equal(directSync.newly_blocked,20);
  assert.equal(directSync.already_blocked,0);
  assert.deepEqual(directSync.counts_before,{PASS:5,BLOCKED:48,NOT_EXECUTED:1428});
  assert.deepEqual(directSync.counts_after,{PASS:5,BLOCKED:68,NOT_EXECUTED:1408});
  assert.equal(directSync.synced_resource_keys.length,20);

  assert.equal(productionDomEvidence.status,"CURRENT_PRODUCTION_EVIDENCE");
  assert.equal(productionDomEvidence.production_release_sha,"608e9c46ef6f85ba4d127d3015b73ff1b5aa8e36");
  assert.equal(productionDomEvidence.post_deploy.run_number,1443);
  assert.equal(productionDomEvidence.post_deploy.status,"SUCCESS");
  assert.deepEqual(productionDomEvidence.dom,{pages:18,interactive:559,enabled:343,disabled:216,governed:559,formal_resource_exact_matches:31});
  assert.equal(productionDomEvidence.observations.length,31);

  assert.equal(productionDomSync.status,"PHYSICAL_LEDGER_SYNCED");
  assert.equal(productionDomSync.structural_blocker_candidates,4);
  assert.equal(productionDomSync.changed_count,4);
  assert.deepEqual(productionDomSync.counts_before,{PASS:5,BLOCKED:68,NOT_EXECUTED:1408});
  assert.deepEqual(productionDomSync.counts_after,{PASS:5,BLOCKED:72,NOT_EXECUTED:1404});
  assert.equal(productionDomSync.untouched_prerequisite_resources.length,2);
  assert.equal(productionDomSync.untouched_enabled_resources.length,25);

  const directSynced=new Set(directSync.synced_resource_keys);
  const productionDomBlocked=new Set(productionDomSync.changed_resource_keys);
  assert.equal(directSynced.size,20);
  assert.equal(productionDomBlocked.size,4);
  for(const row of ledger.entries){
    assert.ok(["PASS","BLOCKED","NOT_EXECUTED"].includes(row.disposition));
    if(row.disposition==="PASS") assert.ok(Array.isArray(row.evidence_refs)&&row.evidence_refs.length>0);
    if(row.disposition==="BLOCKED"){
      assert.ok(row.reason_code);
      assert.ok(Array.isArray(row.evidence_refs)&&row.evidence_refs.length>0);
    }
    if(row.disposition==="NOT_EXECUTED") assert.ok(row.reason_code);
    if(directSynced.has(row.resource_key)){
      assert.equal(row.disposition,"BLOCKED");
      assert.ok(row.evidence_refs.includes("docs/construction/evidence/PRODUCTION_FORMAL_ACCEPTANCE_DIRECT_ADAPTERS_2026-09-10.json"));
      assert.ok(row.blocker_detail);
      assert.ok(Array.isArray(row.operation_ids)&&row.operation_ids.length>0);
    }
    if(productionDomBlocked.has(row.resource_key)){
      assert.equal(row.disposition,"BLOCKED");
      assert.ok(row.evidence_refs.includes("docs/construction/evidence/GATE25_PRODUCTION_DOM_FORMAL_RESOURCE_EVIDENCE_2026-09-10.json"));
      assert.ok(["AUTHORITY_BINDING_UNRESOLVED","IMPLEMENTATION_REQUIRED_NOT_EXECUTED","DISABLED_IN_VISUAL_PHASE"].includes(row.reason_code));
    }
  }
});
