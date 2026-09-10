import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

test("Gate25 blocks exact thirteen retired AIAPI-04..09 Production permission resources without recreating legacy pages",async()=>{
  const evidence=JSON.parse(await readFile("docs/construction/evidence/GATE25_AIAPI_04_09_RETIRED_PERMISSION_RESOURCE_EVIDENCE_2026-09-10.json","utf8"));
  const sync=JSON.parse(await readFile("docs/construction/evidence/GATE25_AIAPI_04_09_RETIRED_PERMISSION_RESOURCE_LEDGER_SYNC_2026-09-10.json","utf8"));
  const ledger=JSON.parse(await readFile("docs/construction/evidence/PRODUCTION_FORMAL_ACCEPTANCE_DISPOSITION_2026-09-10.json","utf8"));
  assert.equal(evidence.status,"CURRENT_AUTHORITY_BLOCKER_EVIDENCE");
  assert.equal(evidence.target_count,13);
  assert.equal(sync.changed_count,13);
  assert.deepEqual(sync.counts_before,{PASS:29,BLOCKED:77,NOT_EXECUTED:1375});
  assert.deepEqual(sync.counts_after,{PASS:29,BLOCKED:90,NOT_EXECUTED:1362});
  const changed=new Set(sync.changed_resource_keys);
  assert.equal(changed.size,13);
  for(const row of ledger.entries.filter(x=>changed.has(x.resource_key))){
    assert.equal(row.disposition,"BLOCKED");
    assert.equal(row.reason_code,"RETIRED_CURRENT_UI_PERMISSION_RESOURCE_ACTIVE_IN_PRODUCTION_INVENTORY");
    assert.ok(row.evidence_refs.includes("docs/construction/evidence/GATE25_AIAPI_04_09_RETIRED_PERMISSION_RESOURCE_EVIDENCE_2026-09-10.json"));
  }
  for(const key of evidence.preserved_existing_specific_blockers){
    assert.ok(!changed.has(key));
    const row=ledger.entries.find(x=>x.resource_key===key);
    assert.equal(row?.disposition,"BLOCKED");
    assert.notEqual(row?.reason_code,"RETIRED_CURRENT_UI_PERMISSION_RESOURCE_ACTIVE_IN_PRODUCTION_INVENTORY");
  }
});
