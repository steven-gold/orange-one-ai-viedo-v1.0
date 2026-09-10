import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const readJson=async(path)=>JSON.parse(await readFile(path,"utf8"));

test("Gate 17 CORE blocker is backed by exact zero Production lineage owners",async()=>{
  const e=await readJson("docs/construction/evidence/GATE17_CORE_PRODUCTION_LINEAGE_BLOCKER_2026-09-10.json");
  assert.equal(e.status,"PRODUCTION_DATA_BLOCKED_NO_FABRICATION");
  assert.equal(e.gate.gate_number,17);
  assert.equal(e.gate.positive_effectful_acceptance,false);
  assert.equal(e.gate.reason_code,"REAL_CANONICAL_PRODUCTION_LINEAGE_ABSENT");
  const expected=["quality_criteria_versions","topics","topic_versions","topic_production_contracts","topic_blueprints","blueprint_versions","canonical_script_versions","child_locks"];
  assert.deepEqual(Object.keys(e.production_counts).sort(),expected.sort());
  for(const key of expected) assert.equal(e.production_counts[key],0,`${key} must remain evidence-recorded as zero`);
  assert.match(e.rule,/Do not fabricate/);
});

test("Gate 20 EDIT+VOICE blocker preserves real lineage and Provider authority gaps",async()=>{
  const e=await readJson("docs/construction/evidence/GATE20_EDIT_VOICE_PRODUCTION_BLOCKER_2026-09-10.json");
  assert.equal(e.status,"PRODUCTION_BLOCKED_REAL_LINEAGE_AND_PROVIDER_AUTHORITY_ABSENT");
  assert.equal(e.gate.gate_number,20);
  assert.equal(e.gate.positive_effectful_acceptance,false);
  for(const key of ["department_tasks_editing","department_tasks_qa","task_outputs","editing_timelines","edit_render_jobs","production_output_version_locks","editing_runtime_runs","voice_runtime_profiles","approved_route_policies"]){
    assert.equal(e.production_counts[key],0,`${key} must remain evidence-recorded as zero`);
  }
  assert.equal(e.production_counts.approved_provider_capabilities,4);
  assert.deepEqual(e.provider_capability_schema_observation.input_properties,["canonical_instruction"]);
  assert.deepEqual(e.provider_capability_schema_observation.output_properties,["text"]);
  assert.equal(e.provider_capability_schema_observation.edit_render_contract_observed,false);
  assert.equal(e.provider_capability_schema_observation.voice_contract_observed,false);
  for(const code of ["REAL_EDIT_QA_PRODUCTION_LINEAGE_ABSENT","APPROVED_ROUTE_POLICY_ABSENT","EDIT_RENDER_PROVIDER_CONTRACT_ABSENT","VOICE_PROVIDER_CONTRACT_ABSENT"]){
    assert.ok(e.gate.reason_codes.includes(code),code);
  }
  assert.match(e.rule,/Do not substitute/);
  assert.match(e.rule,/Do not fabricate/);
});
