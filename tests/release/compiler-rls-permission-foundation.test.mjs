import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
const read=(p)=>readFile(p,"utf8");

test("0046 closes compiler RLS and existing API assignments without fabricating business rows",async()=>{
  const migration=await read("database/migrations/0046_compiler_rls_permission_foundation.sql");
  const manifest=await read("database/migrations/migration_checksum_manifest.yaml");
  const neon=await read("src/server/database/neonRuntime.ts");
  const sep="\nINSERT INTO public.schema_migration_history";
  const idx=migration.indexOf(sep);
  assert.ok(idx>0);
  const checksum=createHash("sha256").update(migration.slice(0,idx)).digest("hex");
  assert.equal(checksum,"73f8b38070d62a8c12307674d9e6c0fbefd838c2eaa23da3f1ca7b7d38745c92");
  assert.ok(manifest.includes("73f8b38070d62a8c12307674d9e6c0fbefd838c2eaa23da3f1ca7b7d38745c92"));
  assert.match(neon,/MAX_SUPPORTED_MIGRATION_COUNT = 46/);

  for(const table of [
    "work_packages","dag_snapshots","dag_nodes","task_templates",
    "topic_production_goals","output_contracts","script_projection_rules"
  ]){
    assert.match(migration,new RegExp(`ALTER TABLE public\\.${table} ENABLE ROW LEVEL SECURITY`),table);
  }
  for(const resource of ["api:createCanonicalScriptVersion","api:compileWorkPackage"]){
    assert.ok(migration.includes(resource),resource);
  }
  assert.match(migration,/dag\.materialize_locked_blueprint/);
  assert.match(migration,/service\.script_view\.compile/);
  assert.match(migration,/canonical_script_versions_request_idempotency_uq/);
  assert.match(migration,/work_packages_compile_idempotency_uq/);
  assert.doesNotMatch(migration,/INSERT INTO public\.(projects|topics|child_locks|work_packages|dag_snapshots|dag_nodes|task_templates|topic_production_goals|output_contracts|script_projection_rules)\b/i);
  assert.doesNotMatch(migration,/ALTER TYPE[\s\S]*VOICE/i);
});

test("0046 synchronizes applied cleanup manifest state instead of restoring pending production wording",async()=>{
  const manifest=await read("database/migrations/migration_checksum_manifest.yaml");
  for(const id of [
    "0043_production_test_only_lineage_cleanup",
    "0044_command_acceptance_fixture_cleanup",
    "0045_local_test_identity_cleanup"
  ]){
    const block=manifest.match(new RegExp(`- migration_id: ${id}[\\s\\S]*?(?=\\n- migration_id:|$)`))?.[0]??"";
    assert.match(block,/production_apply: APPLIED_VERIFIED_PRODUCTION_2026-09-10/,id);
  }
});
