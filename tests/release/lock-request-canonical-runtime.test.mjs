import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
const read=(p)=>readFile(p,"utf8");

test("0042 canonical lock request is explicit, idempotent, audited and evented",async()=>{
  const migration=await read("database/migrations/0042_lock_request_canonical_event_closure.sql");
  const manifest=await read("database/migrations/migration_checksum_manifest.yaml");
  const neon=await read("src/server/database/neonRuntime.ts");
  const sep="\nINSERT INTO public.schema_migration_history";
  const idx=migration.indexOf(sep);
  assert.ok(idx>0);
  const checksum=createHash("sha256").update(migration.slice(0,idx)).digest("hex");
  assert.equal(checksum,"03ac268173889742f876296a825418928c679c965998f00d9e5285405156ad18");
  for(const field of [
    "request_reason","requested_scope_refs","request_correlation_id",
    "request_idempotency_key_hash","request_payload_hash"
  ])assert.ok(migration.includes(field),field);
  assert.match(migration,/REVOKE INSERT ON public\.lock_reviews FROM acpos_app_runtime/);
  assert.match(migration,/CREATE POLICY acpos_quality_criteria_versions_lock_select/);
  assert.match(migration,/count_lock_reviewer_candidates/);
  assert.match(migration,/CREATE OR REPLACE FUNCTION acpos_runtime\.request_lock_review/);
  assert.match(migration,/api:requestMotherLock/);
  assert.match(migration,/api:requestChildLock/);
  assert.match(migration,/api:decideLockReview/);
  assert.match(migration,/LOCK_CRITERIA_VERSION_REQUIRED/);
  assert.match(migration,/LOCK_EVIDENCE_REQUIRED/);
  assert.match(migration,/CORE_LOCK_REVIEWER_PATH_UNRESOLVED/);
  assert.match(migration,/lock\.review_requested/);
  assert.match(migration,/mother_lock\.approved/);
  assert.match(migration,/child_lock\.approved/);
  assert.match(migration,/lock\.rejected/);
  assert.match(migration,/READY_FOR_MOTHER_REVIEW/);
  assert.match(migration,/READY_FOR_CHILD_REVIEW/);
  assert.doesNotMatch(migration,/ORDER BY[^;]*(latest|current|default)/i);
  assert.match(manifest,/0042_lock_request_canonical_event_closure/);
  assert.ok(manifest.includes("03ac268173889742f876296a825418928c679c965998f00d9e5285405156ad18"));
  assert.match(neon,/MAX_SUPPORTED_MIGRATION_COUNT = 42/);
});

test("CORE Mother and Child Lock runtime accept only the single-authority request shape",async()=>{
  const runtime=await read("src/server/core/productionCoreGovernedRuntime.ts");
  for(const key of ["scope","expected_version","correlation_id","idempotency_key","target_ref","request_reason","requested_scope_refs"]){
    assert.ok(runtime.includes(`"${key}"`),key);
  }
  assert.match(runtime,/requestLockReview\(request,"MOTHER"\)/);
  assert.match(runtime,/requestLockReview\(request,"CHILD"\)/);
  assert.match(runtime,/acpos_runtime\.request_lock_review/);
  assert.doesNotMatch(runtime,/async function requestMotherLock[\s\S]{0,1000}project_version_ref/);
  assert.doesNotMatch(runtime,/async function requestChildLock[\s\S]{0,1000}blueprint_version_ref/);
});
