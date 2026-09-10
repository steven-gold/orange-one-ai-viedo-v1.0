import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
const read=(p)=>readFile(p,"utf8");

test("0049 registers VOICE as its own department without coercing EDITING or business data",async()=>{
  const migration=await read("database/migrations/0049_voice_department_schema_contract.sql");
  const manifest=await read("database/migrations/migration_checksum_manifest.yaml");
  const neon=await read("src/server/database/neonRuntime.ts");
  const sep="\nINSERT INTO public.schema_migration_history";
  const idx=migration.indexOf(sep);
  assert.ok(idx>0);
  const checksum=createHash("sha256").update(migration.slice(0,idx)).digest("hex");
  assert.equal(checksum,"efaca6966229c2cd10c6e0ea4e509d2df8f3c6621cfb460e66635010dacbf947");
  assert.ok(manifest.includes("efaca6966229c2cd10c6e0ea4e509d2df8f3c6621cfb460e66635010dacbf947"));
  assert.match(migration,/ALTER TYPE public\.department_code ADD VALUE IF NOT EXISTS 'VOICE'/);
  assert.match(migration,/e\.enumlabel='VOICE'/);
  assert.doesNotMatch(migration,/UPDATE\s+public\.[a-z_]+[\s\S]*department[^;]*EDITING/i);
  assert.doesNotMatch(migration,/INSERT INTO public\.(department_tasks|task_templates|dag_nodes|work_packages|topic_production_goals)\b/i);
  const ceiling=Number(neon.match(/MAX_SUPPORTED_MIGRATION_COUNT = (\d+)/)?.[1]??0);
  assert.ok(ceiling>=49,`migration ceiling must include 0049, found ${ceiling}`);
});

test("0049 manifest seals 0048 Production evidence and keeps 0049 staged",async()=>{
  const manifest=await read("database/migrations/migration_checksum_manifest.yaml");
  const block48=manifest.match(/- migration_id: 0048_dag_edge_rls_runtime_closure[\s\S]*?(?=\n- migration_id:|$)/)?.[0]??"";
  const block49=manifest.match(/- migration_id: 0049_voice_department_schema_contract[\s\S]*?(?=\n- migration_id:|$)/)?.[0]??"";
  assert.match(block48,/production_apply: APPLIED_VERIFIED_PRODUCTION_2026-09-10/);
  assert.match(block49,/production_apply: STAGED_PENDING_PRODUCTION_APPLY/);
});
