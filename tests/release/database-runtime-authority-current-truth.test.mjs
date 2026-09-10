import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const p="authority/runtime/ACPOS_PRODUCTION_DATABASE_RUNTIME_CONTRACT_FINAL_LOCKED_V1.0.yaml";
const s=await readFile(p,"utf8");
test("Current production DB runtime contract delegates mutable migration truth",()=>{
  assert.match(s,/authority_path: authority\/global\/ACPOS_DATABASE_MIGRATION_AUTHORITY_FINAL_LOCKED_V1\.0\.yaml/);
  assert.match(s,/checksum_manifest: database\/migrations\/migration_checksum_manifest\.yaml/);
  assert.match(s,/mutable_migration_count_embedded: false/);
  assert.match(s,/historical_execution_state_embedded: false/);
  assert.doesNotMatch(s,/exact_migrations:\s*15/);
  assert.doesNotMatch(s,/schema_migration_history must contain 15 rows/);
  assert.doesNotMatch(s,/chain:\s*0001-0015/);
  assert.doesNotMatch(s,/tiny_dust_complete_record:/);
  assert.doesNotMatch(s,/NEON_DRIVER_BOUND_UI_PROJECTION_NOT_BOUND/);
});
