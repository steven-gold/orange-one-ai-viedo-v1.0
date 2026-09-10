import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
const read=(p)=>readFile(p,"utf8");

test("0048 closes the WorkPackage DAG edge RLS/runtime omission without business data",async()=>{
  const migration=await read("database/migrations/0048_dag_edge_rls_runtime_closure.sql");
  const manifest=await read("database/migrations/migration_checksum_manifest.yaml");
  const neon=await read("src/server/database/neonRuntime.ts");
  const sep="\nINSERT INTO public.schema_migration_history";
  const idx=migration.indexOf(sep);
  assert.ok(idx>0);
  const checksum=createHash("sha256").update(migration.slice(0,idx)).digest("hex");
  assert.equal(checksum,"5e218c9a78826c0e56719ef7865957b75e4508a021cac9f858edebc7bd2a2f60");
  assert.ok(manifest.includes("5e218c9a78826c0e56719ef7865957b75e4508a021cac9f858edebc7bd2a2f60"));
  assert.match(migration,/ALTER TABLE public\.dag_edges ENABLE ROW LEVEL SECURITY/);
  assert.match(migration,/acpos_dag_edges_actor_select/);
  assert.match(migration,/acpos_dag_edges_orchestrator_insert/);
  assert.match(migration,/dag\.materialize_locked_blueprint/);
  assert.match(migration,/GRANT SELECT,INSERT ON public\.dag_edges TO acpos_app_runtime/);
  assert.doesNotMatch(migration,/INSERT INTO public\.(projects|topics|child_locks|work_packages|dag_snapshots|dag_nodes|dag_edges|task_templates|topic_production_goals|output_contracts)\b/i);
  const ceiling=Number(neon.match(/MAX_SUPPORTED_MIGRATION_COUNT = (\d+)/)?.[1]??0);
  assert.ok(ceiling>=48,`migration ceiling must include 0048, found ${ceiling}`);
});

test("0048 manifest records 0047 as Production-applied and keeps 0048 staged",async()=>{
  const manifest=await read("database/migrations/migration_checksum_manifest.yaml");
  const block47=manifest.match(/- migration_id: 0047_canonical_script_version_runtime[\s\S]*?(?=\n- migration_id:|$)/)?.[0]??"";
  const block48=manifest.match(/- migration_id: 0048_dag_edge_rls_runtime_closure[\s\S]*?(?=\n- migration_id:|$)/)?.[0]??"";
  assert.match(block47,/production_apply: APPLIED_VERIFIED_PRODUCTION_2026-09-10/);
  assert.match(block48,/production_apply: STAGED_PENDING_PRODUCTION_APPLY/);
});
