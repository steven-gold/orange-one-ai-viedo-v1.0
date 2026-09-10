import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
const read=(p)=>readFile(p,"utf8");

test("0051 seals EDIT+VOICE audit RLS without opening generic audit writes",async()=>{
  const migration=await read("database/migrations/0051_edit_voice_audit_rls_closure.sql");
  const manifest=await read("database/migrations/migration_checksum_manifest.yaml");
  const neon=await read("src/server/database/neonRuntime.ts");
  const sep="\nINSERT INTO public.schema_migration_history";
  const idx=migration.indexOf(sep);
  assert.ok(idx>0);
  const checksum=createHash("sha256").update(migration.slice(0,idx)).digest("hex");
  assert.equal(checksum,"ddce6a15daa6f3f5e1407163fa2e10717fead8b82c264cbd08ac77ed0c4ab74e");
  assert.ok(manifest.includes("ddce6a15daa6f3f5e1407163fa2e10717fead8b82c264cbd08ac77ed0c4ab74e"));
  assert.match(migration,/acpos_audit_events_edit_insert/);
  assert.match(migration,/acpos_audit_events_edit_select/);
  assert.match(migration,/entity_type='workspace:EDIT-01'/);
  assert.match(migration,/actor_id=acpos_runtime\.current_actor_user_id\(\)/);
  assert.match(migration,/workspace_id IS NULL[\s\S]*reason LIKE 'DENIED:%'[\\s\\S]*reason LIKE 'ERROR:%'/);
  assert.doesNotMatch(migration,/CREATE TABLE/i);
  assert.doesNotMatch(migration,/INSERT INTO public\.(projects|department_tasks|audit_events)\b/i);
  assert.ok(Number(neon.match(/MAX_SUPPORTED_MIGRATION_COUNT = (\d+)/)?.[1]??0)>=51);
});

test("EDIT+VOICE Production audit resolves exact task workspace and is no longer empty",async()=>{
  const runtime=await read("src/server/edit/productionEditVoiceRuntime.ts");
  assert.doesNotMatch(runtime,/auditProductionEditVoiceOperation\(\):Promise<void>\{return;\}/);
  assert.match(runtime,/INSERT INTO public\.audit_events/);
  assert.match(runtime,/JOIN public\.projects p ON p\.project_id=t\.project_id/);
  assert.match(runtime,/EDIT_AUDIT_WORKSPACE_REQUIRED/);
  assert.match(runtime,/entity_type,entity_id,actor_id,actor_type,workspace_id,reason,correlation_id,payload_hash/);
});


test("ALLOWED audit persistence is fail-closed before EDIT effectful execution",async()=>{
  const runtime=await read("src/server/edit/editVoiceRuntime.ts");
  assert.match(runtime,/const allowedAuditPersisted=await audit\(r,\{\.\.\.request,outcome:"ALLOWED"\}\)/);
  assert.match(runtime,/if\(!allowedAuditPersisted\)return\{ok:false as const,status:503[\s\S]*EDIT_AUDIT_PERSISTENCE_REQUIRED/);
  const gate=runtime.indexOf("EDIT_AUDIT_PERSISTENCE_REQUIRED");
  const execute=runtime.indexOf("r.execute(request)");
  assert.ok(gate>=0&&execute>gate,"effectful execute must occur only after durable ALLOWED audit gate");
});
