import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const authority=await readFile("authority/global/ACPOS_DATABASE_MIGRATION_AUTHORITY_FINAL_LOCKED_V1.0.yaml","utf8");
test("Migration Current Authority is governance-only and delegates mutable execution truth",()=>{
  assert.match(authority,/registration_source: database\/migrations\/migration_checksum_manifest\.yaml/);
  assert.match(authority,/applied_history_relation: schema_migration_history/);
  assert.match(authority,/checksum_match_required: true/);
  assert.match(authority,/current_state_owner: CURRENT_EXECUTION_STATE\.json/);
  assert.match(authority,/historical_execution_evidence_is_not_runtime_authority: true/);
  assert.doesNotMatch(authority,/materialized_migration_count:/);
  assert.doesNotMatch(authority,/production_applied_migration_count:/);
  assert.doesNotMatch(authority,/current_production_reconciliation:/);
  assert.doesNotMatch(authority,/temporary_0002_validation:/);
  assert.doesNotMatch(authority,/staging_0003_pre_correction_preflight:/);
  assert.doesNotMatch(authority,/CR-R9-/);
  assert.doesNotMatch(authority,/tiny-dust/);
});
