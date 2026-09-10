import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

test("Gate25 SG-02 NAV-OPEN action is promoted only from exact existing Production evidence",async()=>{
  const evidence=JSON.parse(await readFile("docs/construction/evidence/GATE25_SG02_NAV_ACTION_EXISTING_PRODUCTION_EVIDENCE_2026-09-10.json","utf8"));
  const sync=JSON.parse(await readFile("docs/construction/evidence/GATE25_SG02_NAV_ACTION_LEDGER_SYNC_2026-09-10.json","utf8"));
  const ledger=JSON.parse(await readFile("docs/construction/evidence/PRODUCTION_FORMAL_ACCEPTANCE_DISPOSITION_2026-09-10.json","utf8"));
  assert.equal(evidence.status,"CURRENT_PRODUCTION_EVIDENCE");
  assert.equal(evidence.effectful,false);
  assert.equal(evidence.formal_action_resource,"action:admin:SG-02:ACT-NAV-OPEN");
  assert.equal(sync.changed_count,1);
  assert.deepEqual(sync.changed_resource_keys,["action:admin:SG-02:ACT-NAV-OPEN"]);
  assert.deepEqual(sync.counts_before,{PASS:28,BLOCKED:72,NOT_EXECUTED:1381});
  assert.deepEqual(sync.counts_after,{PASS:29,BLOCKED:72,NOT_EXECUTED:1380});
  assert.deepEqual(ledger.counts,sync.counts_after);
  const row=ledger.entries.find(x=>x.resource_key==="action:admin:SG-02:ACT-NAV-OPEN");
  assert.equal(row?.disposition,"PASS");
  assert.equal(row?.reason_code,"PRODUCTION_READONLY_ACTION_ACCEPTED");
  assert.ok(row?.evidence_refs.includes("docs/construction/evidence/GATE25_SG02_NAV_ACTION_EXISTING_PRODUCTION_EVIDENCE_2026-09-10.json"));
  for(const key of sync.excluded_effectful_resources){const effectful=ledger.entries.find(x=>x.resource_key===key);if(effectful)assert.notEqual(effectful.disposition,"PASS");}
});
