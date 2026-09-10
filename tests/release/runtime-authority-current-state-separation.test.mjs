import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const identity=await readFile("authority/runtime/ACPOS_PRODUCTION_IDENTITY_RUNTIME_CONTRACT_FINAL_LOCKED_V1.0.yaml","utf8");
const queue=await readFile("authority/runtime/ACPOS_PRODUCTION_ASYNC_QUEUE_RUNTIME_CONTRACT_FINAL_LOCKED_V1.0.yaml","utf8");
test("Identity Current Authority keeps fail-closed semantics but not mutable readiness progression",()=>{
  assert.match(identity,/reason_code: IDENTITY_RUNTIME_NOT_BOUND/);
  assert.match(identity,/adapter_bind_allowed: true/);
  assert.match(identity,/production_ready_claim_allowed_from_this_contract_alone: false/);
  assert.match(identity,/current_state_owner: CURRENT_EXECUTION_STATE\.json/);
  assert.doesNotMatch(identity,/remaining_blockers:/);
  assert.doesNotMatch(identity,/next_action:/);
});
test("Queue Current Authority does not embed old release, SHA, provider counts, or execution outcomes",()=>{
  assert.match(queue,/deployment_state_policy:/);
  assert.match(queue,/mutable_environment_state_embedded: false/);
  assert.match(queue,/current_state_owner: CURRENT_EXECUTION_STATE\.json/);
  assert.doesNotMatch(queue,/provider_execution_implementation_evidence:/);
  assert.doesNotMatch(queue,/release_gate:\s*\n\s*run_number:/);
  assert.doesNotMatch(queue,/external_configuration_current_counts:/);
  assert.doesNotMatch(queue,/production_external_execution_proof:/);
});
