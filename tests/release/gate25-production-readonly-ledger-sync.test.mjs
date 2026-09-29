import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

test("Gate25 Production readonly ledger sync promotes exact 23 and excludes effectful resources",async()=>{
  const evidence=JSON.parse(await readFile("docs/construction/evidence/GATE25_PRODUCTION_READONLY_INTERACTION_EVIDENCE_2026-09-10.json","utf8"));
  const sync=JSON.parse(await readFile("docs/construction/evidence/GATE25_PRODUCTION_READONLY_INTERACTION_LEDGER_SYNC_2026-09-10.json","utf8"));
  const ledger=JSON.parse(await readFile("docs/construction/evidence/PRODUCTION_FORMAL_ACCEPTANCE_DISPOSITION_2026-09-10.json","utf8"));
  assert.equal(evidence.status,"PRODUCTION_ACCEPTED");
  assert.deepEqual(evidence.totals,{wb01:14,sg02:9,total:23,effectful_calls:0});
  assert.equal(sync.changed_count,23);
  assert.equal(new Set(sync.changed_resource_keys).size,23);
  assert.deepEqual(sync.counts_before,{PASS:5,BLOCKED:72,NOT_EXECUTED:1404});
  assert.deepEqual(sync.counts_after,{PASS:28,BLOCKED:72,NOT_EXECUTED:1381});
  assert.equal(ledger.entries.length,1481);
  assert.deepEqual(sync.counts_after,{PASS:28,BLOCKED:72,NOT_EXECUTED:1381});
  const changed=new Set(sync.changed_resource_keys);
  for(const key of evidence.forbidden_effectful_resources) assert.ok(!changed.has(key));
  for(const row of ledger.entries.filter(x=>changed.has(x.resource_key))){
    assert.equal(row.disposition,"PASS");
    assert.equal(row.reason_code,"PRODUCTION_READONLY_INTERACTION_ACCEPTED");
    assert.ok(row.evidence_refs.includes("docs/construction/evidence/GATE25_PRODUCTION_READONLY_INTERACTION_EVIDENCE_2026-09-10.json"));
  }
});
