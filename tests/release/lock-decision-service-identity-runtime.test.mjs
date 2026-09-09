import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
const read=(p)=>readFile(p,"utf8");

test("0041 materializes only Current service identities/capabilities and governed lock decision foundation",async()=>{
  const migration=await read("database/migrations/0041_governed_lock_decision_service_identity_foundation.sql");
  const manifest=await read("database/migrations/migration_checksum_manifest.yaml");
  const neon=await read("src/server/database/neonRuntime.ts");
  const separator="\nINSERT INTO public.schema_migration_history";
  const idx=migration.indexOf(separator);
  assert.ok(idx>0);
  const checksum=createHash("sha256").update(migration.slice(0,idx)).digest("hex");
  assert.equal(checksum,"58a7d78fed454b5f1a49a18b2978f44fec248a4dd184ed4f6ea60e998c22f0c5");
  for(const key of ["task_orchestrator","instruction_compiler","dag.materialize_locked_blueprint","task.dispatch_approved_flow","service.script_view.compile","service.instruction_package.compile"]){
    assert.ok(migration.includes(key),key);
  }
  assert.match(migration,/human-permission impersonation by service identities/);
  assert.match(migration,/SEPARATION_OF_DUTIES_VIOLATION/);
  assert.match(migration,/acpos_runtime\.has_account_resource_action\('api:decideLockReview','EXECUTE'\)/);
  assert.match(migration,/decision_idempotency_key_hash/);
  assert.match(migration,/CREATE POLICY acpos_core_lock_review_decide_update/);
  assert.match(migration,/ALTER TABLE public\.service_identities ENABLE ROW LEVEL SECURITY/);
  assert.match(migration,/ALTER TABLE public\.service_identity_capability_assignments ENABLE ROW LEVEL SECURITY/);
  assert.match(migration,/ALTER TABLE public\.mother_locks ENABLE ROW LEVEL SECURITY/);
  assert.match(migration,/ALTER TABLE public\.child_locks ENABLE ROW LEVEL SECURITY/);
  assert.doesNotMatch(migration,/GRANT SELECT,INSERT ON public\.child_locks/);
  assert.match(manifest,/0041_governed_lock_decision_service_identity_foundation/);
  assert.match(manifest,/58a7d78fed454b5f1a49a18b2978f44fec248a4dd184ed4f6ea60e998c22f0c5/);
  assert.match(neon,/MAX_SUPPORTED_MIGRATION_COUNT = 41/);
});

test("Current lock decision API uses existing CORE runtime chain and exact request contract",async()=>{
  const contract=await read("src/domain/core/coreRuntimeContract.ts");
  const route=await read("src/app/v1/lock-reviews/[id]/decision/route.ts");
  const identity=await read("src/server/shared/identityPageCommandRuntime.ts");
  const runtime=await read("src/server/core/productionCoreGovernedRuntime.ts");
  const rls=await read("src/server/database/rlsRuntime.ts");
  assert.match(contract,/CORE-01-PORT-LOCK-DECIDE/);
  assert.match(contract,/\/v1\/lock-reviews\/\{id\}\/decision/);
  assert.match(route,/createCorePostRoute\("CORE-01-PORT-LOCK-DECIDE"\)/);
  assert.match(identity,/CORE-01-PORT-LOCK-DECIDE":"api:decideLockReview"/);
  assert.match(identity,/evaluateResourceAction\("api:decideLockReview","EXECUTE"\)/);
  for(const field of ["scope","expected_version","correlation_id","idempotency_key","lock_review_id","decision","reason"]){
    assert.ok(runtime.includes(`"${field}"`),field);
  }
  assert.match(runtime,/PATH_BODY_ID_MISMATCH/);
  assert.match(runtime,/acpos_runtime\.decide_lock_review/);
  assert.match(runtime,/SEPARATION_OF_DUTIES_VIOLATION/);
  assert.match(rls,/runRlsServiceQuery/);
  assert.match(rls,/acpos\.service_identity_key/);
});
