import fs from "node:fs";

const args=new Set(process.argv.slice(2));
const requirePass=args.has("--require-pass");
const inventoryPath="docs/construction/evidence/PRODUCTION_FORMAL_CONTROL_ACTION_INVENTORY_2026-09-10.json";
const ledgerPath="docs/construction/evidence/PRODUCTION_FORMAL_ACCEPTANCE_DISPOSITION_2026-09-10.json";
const directAdaptersPath="docs/construction/evidence/PRODUCTION_FORMAL_ACCEPTANCE_DIRECT_ADAPTERS_2026-09-10.json";

const inventory=JSON.parse(fs.readFileSync(inventoryPath,"utf8"));
const ledger=JSON.parse(fs.readFileSync(ledgerPath,"utf8"));
const directAdapters=JSON.parse(fs.readFileSync(directAdaptersPath,"utf8"));
const allowed=new Set(["PASS","BLOCKED","NOT_EXECUTED"]);

function fail(code,detail=""){throw new Error(detail?`${code} ${detail}`:code);}
if(inventory?.denominator?.total!==1481||inventory?.denominator?.controls!==1155||inventory?.denominator?.actions!==326) {
  fail("FORMAL_INVENTORY_DENOMINATOR_MISMATCH",JSON.stringify(inventory?.denominator??{}));
}
if(ledger?.denominator?.total!==1481||ledger?.denominator?.controls!==1155||ledger?.denominator?.actions!==326) {
  fail("FORMAL_LEDGER_DENOMINATOR_MISMATCH",JSON.stringify(ledger?.denominator??{}));
}
if(!Array.isArray(inventory.resources)||inventory.resources.length!==1481) fail("FORMAL_INVENTORY_RESOURCE_COUNT_MISMATCH",String(inventory.resources?.length));
if(!Array.isArray(ledger.entries)||ledger.entries.length!==1481) fail("FORMAL_LEDGER_ENTRY_COUNT_MISMATCH",String(ledger.entries?.length));

const inv=new Map();
for(const r of inventory.resources){
  const key=String(r.resource_key??"");
  if(!key) fail("FORMAL_INVENTORY_EMPTY_RESOURCE_KEY");
  if(inv.has(key)) fail("FORMAL_INVENTORY_DUPLICATE_RESOURCE",key);
  if(r.resource_type!=="CONTROL"&&r.resource_type!=="ACTION") fail("FORMAL_INVENTORY_INVALID_TYPE",`${key}:${r.resource_type}`);
  inv.set(key,r.resource_type);
}
const seen=new Set();
const counts={PASS:0,BLOCKED:0,NOT_EXECUTED:0};
const ledgerByKey=new Map();
for(const e of ledger.entries){
  const key=String(e.resource_key??"");
  if(!inv.has(key)) fail("FORMAL_LEDGER_UNKNOWN_RESOURCE",key);
  if(seen.has(key)) fail("FORMAL_LEDGER_DUPLICATE_RESOURCE",key);
  seen.add(key);
  ledgerByKey.set(key,e);
  if(inv.get(key)!==e.resource_type) fail("FORMAL_LEDGER_TYPE_MISMATCH",key);
  if(!allowed.has(e.disposition)) fail("FORMAL_LEDGER_INVALID_DISPOSITION",`${key}:${e.disposition}`);
  const refs=Array.isArray(e.evidence_refs)?e.evidence_refs.filter(Boolean):[];
  const reason=String(e.reason_code??"").trim();
  if(e.disposition==="PASS"&&refs.length===0) fail("FORMAL_LEDGER_PASS_WITHOUT_PER_RESOURCE_EVIDENCE",key);
  if(e.disposition==="BLOCKED"&&(!reason||refs.length===0)) fail("FORMAL_LEDGER_BLOCKED_WITHOUT_REASON_OR_EVIDENCE",key);
  if(e.disposition==="NOT_EXECUTED"&&!reason) fail("FORMAL_LEDGER_NOT_EXECUTED_WITHOUT_REASON",key);
  counts[e.disposition]++;
}
if(seen.size!==inv.size) {
  const missing=[...inv.keys()].filter(k=>!seen.has(k));
  fail("FORMAL_LEDGER_COVERAGE_GAP",missing.slice(0,20).join(","));
}
if((ledger.aggregate_dom_evidence?.per_resource_pass_propagation)!==false) fail("FORMAL_LEDGER_AGGREGATE_DOM_MUST_NOT_PROMOTE_PASS");
if(ledger.counts?.PASS!==counts.PASS||ledger.counts?.BLOCKED!==counts.BLOCKED||ledger.counts?.NOT_EXECUTED!==counts.NOT_EXECUTED) {
  fail("FORMAL_LEDGER_RECORDED_COUNTS_MISMATCH",JSON.stringify({recorded:ledger.counts,actual:counts}));
}

if(directAdapters?.exact_direct_mapping_count!==25) fail("FORMAL_DIRECT_MAPPING_COUNT_MISMATCH",String(directAdapters?.exact_direct_mapping_count));
const directPass=Array.isArray(directAdapters.executable_readonly_now)?directAdapters.executable_readonly_now:[];
const directBlocked=Array.isArray(directAdapters.mapped_not_yet_executable)?directAdapters.mapped_not_yet_executable:[];
if(directPass.length!==5||directBlocked.length!==20) fail("FORMAL_DIRECT_CLASSIFICATION_COUNT_MISMATCH",JSON.stringify({pass:directPass.length,blocked:directBlocked.length}));
if(directAdapters?.classification_summary?.PASS_READONLY!==5||directAdapters?.classification_summary?.BLOCKED_SAFE_ACCEPTANCE_CONTRACT!==20||directAdapters?.classification_summary?.UNCLASSIFIED!==0){
  fail("FORMAL_DIRECT_CLASSIFICATION_SUMMARY_MISMATCH",JSON.stringify(directAdapters?.classification_summary??{}));
}
const directSeen=new Set();
for(const row of directPass){
  const key=String(row.resource_key??"");
  if(!inv.has(key)) fail("FORMAL_DIRECT_UNKNOWN_RESOURCE",key);
  if(directSeen.has(key)) fail("FORMAL_DIRECT_DUPLICATE_RESOURCE",key);
  directSeen.add(key);
  const disposition=ledgerByKey.get(key)?.disposition;
  if(disposition!=="PASS") fail("FORMAL_DIRECT_READONLY_NOT_LEDGER_PASS",`${key}:${disposition??"MISSING"}`);
}
for(const row of directBlocked){
  const key=String(row.resource_key??"");
  const reason=String(row.reason_code??"").trim();
  const detail=String(row.detail??"").trim();
  if(!inv.has(key)) fail("FORMAL_DIRECT_UNKNOWN_RESOURCE",key);
  if(directSeen.has(key)) fail("FORMAL_DIRECT_DUPLICATE_RESOURCE",key);
  directSeen.add(key);
  if(!reason||!detail) fail("FORMAL_DIRECT_BLOCKER_EVIDENCE_INCOMPLETE",key);
  const disposition=ledgerByKey.get(key)?.disposition;
  if(disposition==="PASS") fail("FORMAL_DIRECT_BLOCKED_RESOURCE_MUST_NOT_BE_PASS",key);
}
if(directSeen.size!==25) fail("FORMAL_DIRECT_COVERAGE_GAP",String(directSeen.size));

process.stdout.write(`FORMAL_ACCEPTANCE_LEDGER_COVERAGE_PASS total=${seen.size} pass=${counts.PASS} blocked=${counts.BLOCKED} not_executed=${counts.NOT_EXECUTED} direct_pass=${directPass.length} direct_blocked=${directBlocked.length}\n`);
if(requirePass&&counts.PASS!==seen.size){
  fail("FORMAL_EFFECTFUL_ACCEPTANCE_NOT_COMPLETE",`pass=${counts.PASS} total=${seen.size} blocked=${counts.BLOCKED} not_executed=${counts.NOT_EXECUTED}`);
}
