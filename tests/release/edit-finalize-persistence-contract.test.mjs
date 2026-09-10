import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
const read=(p)=>readFile(p,"utf8");

test("0050 materializes EDIT Finalize persistence without a parallel lock owner",async()=>{
  const migration=await read("database/migrations/0050_edit_finalize_persistence_permission_rls_closure.sql");
  const manifest=await read("database/migrations/migration_checksum_manifest.yaml");
  const neon=await read("src/server/database/neonRuntime.ts");
  const runtime=await read("src/server/edit/productionEditFinalizeRuntime.ts");
  const lifecycleRuntime=await read("src/server/edit/productionEditVoiceRuntime.ts");
  const sep="\nINSERT INTO public.schema_migration_history";
  const idx=migration.indexOf(sep);
  assert.ok(idx>0);
  const checksum=createHash("sha256").update(migration.slice(0,idx)).digest("hex");
  assert.equal(checksum,"f6be546d52ff486236913c5f8c02971cf7e25c9f801fe3a8c5774f1a548553d5");
  assert.ok(manifest.includes("f6be546d52ff486236913c5f8c02971cf7e25c9f801fe3a8c5774f1a548553d5"));
  for(const column of ["source_timeline_id","source_draft_hash","version_content_hash","source_scorecard_id","saved_by","saved_at"]){
    assert.match(migration,new RegExp(column));
  }
  assert.match(migration,/CREATE TABLE IF NOT EXISTS public\.edit_render_jobs/);
  assert.doesNotMatch(migration,/CREATE TABLE IF NOT EXISTS public\.edit_version_locks/);
  assert.match(migration,/public\.production_output_version_locks/);
  assert.match(migration,/department IN\('ASSET','VIDEO','EDITING'\)/);
  assert.match(runtime,/public\.production_output_version_locks/);
  assert.doesNotMatch(runtime,/public\.edit_version_locks/);
  assert.match(lifecycleRuntime,/public\.production_output_version_locks/);
  assert.doesNotMatch(lifecycleRuntime,/public\.edit_version_locks/);
  assert.ok(Number(neon.match(/MAX_SUPPORTED_MIGRATION_COUNT = (\d+)/)?.[1]??0)>=50);
});

test("0050 seals seven Finalize PAGE_ACTION_CONTROL_API operations and creates no business rows",async()=>{
  const migration=await read("database/migrations/0050_edit_finalize_persistence_permission_rls_closure.sql");
  const registry=await read("03_api/operation_registry.yaml");
  const operations=[
    "saveEditVersion","startEditRender","cancelEditRender","saveEditOutputVersion",
    "lockEditVersion","restoreEditVersionAsDraft","getEditOutputDownload"
  ];
  for(const operation of operations){
    assert.match(registry,new RegExp("operation_id: "+operation+"\\b"));
    assert.match(migration,new RegExp("api:"+operation+"\\b"));
  }
  assert.match(migration,/EDITFINAL0050_APPROVED_ALLOW_COUNT_MISMATCH/);
  assert.match(migration,/IF n<>21/);
  assert.doesNotMatch(migration,/INSERT INTO public\.(editing_timelines|edit_render_jobs|production_output_version_locks|task_outputs|department_tasks|scorecards)\b/i);
  assert.match(registry,/operation_id: lockEditVersion[\s\S]*persistence_owner: public\.production_output_version_locks/);
});


test("EDIT Finalize resolves Blueprint lineage through canonical ChildLock owner",async()=>{
  const runtime=await read("src/server/edit/productionEditFinalizeRuntime.ts");
  assert.match(runtime,/JOIN public\.child_locks cl ON cl\.child_lock_id=t\.child_lock_id AND cl\.status='LOCKED'/);
  assert.match(runtime,/cl\.blueprint_version_id::text/);
  assert.doesNotMatch(runtime,/t\.blueprint_version_id::text/);
});
