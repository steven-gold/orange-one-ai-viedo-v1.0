import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

test("Gate25 blocks exact five API-06/07 Production permission resources that lack a Current page owner",async()=>{
  const evidence=JSON.parse(await readFile("docs/construction/evidence/GATE25_API_06_07_NON_CURRENT_PERMISSION_RESOURCE_EVIDENCE_2026-09-10.json","utf8"));
  const sync=JSON.parse(await readFile("docs/construction/evidence/GATE25_API_06_07_NON_CURRENT_PERMISSION_RESOURCE_LEDGER_SYNC_2026-09-10.json","utf8"));
  const ledger=JSON.parse(await readFile("docs/construction/evidence/PRODUCTION_FORMAL_ACCEPTANCE_DISPOSITION_2026-09-10.json","utf8"));
  assert.equal(evidence.status,"CURRENT_AUTHORITY_BLOCKER_EVIDENCE");
  assert.equal(evidence.target_count,5);
  assert.equal(sync.changed_count,5);
  assert.deepEqual(sync.counts_before,{PASS:29,BLOCKED:103,NOT_EXECUTED:1349});
  assert.deepEqual(sync.counts_after,{PASS:29,BLOCKED:108,NOT_EXECUTED:1344});
  const changed=new Set(sync.changed_resource_keys);
  assert.equal(changed.size,5);
  for(const row of ledger.entries.filter(x=>changed.has(x.resource_key))){
    assert.equal(row.disposition,"BLOCKED");
    assert.equal(row.reason_code,"NON_CURRENT_PAGE_PERMISSION_RESOURCE_ACTIVE_IN_PRODUCTION_INVENTORY");
    assert.ok(row.evidence_refs.includes("docs/construction/evidence/GATE25_API_06_07_NON_CURRENT_PERMISSION_RESOURCE_EVIDENCE_2026-09-10.json"));
  }
});
