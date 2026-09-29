import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
const read=(p)=>readFile(p,"utf8");

test("0045 removes only the historical local:test acceptance identity",async()=>{
  const migration=await read("database/migrations/0045_local_test_identity_cleanup.sql");
  const manifest=await read("database/migrations/migration_checksum_manifest.yaml");
  const neon=await read("src/server/database/neonRuntime.ts");
  const sep="\nINSERT INTO public.schema_migration_history";
  const idx=migration.indexOf(sep);
  assert.ok(idx>0);
  const checksum=createHash("sha256").update(migration.slice(0,idx)).digest("hex");
  assert.equal(checksum,"af1384b6f8c1cdb36a69e4d1e69baabdf8c1fbcce7bc17edc7c5ad39feaf0376");
  assert.ok(manifest.includes("af1384b6f8c1cdb36a69e4d1e69baabdf8c1fbcce7bc17edc7c5ad39feaf0376"));
  const ceiling=Number(neon.match(/MAX_SUPPORTED_MIGRATION_COUNT = (\d+)/)?.[1]??0);
  assert.ok(ceiling>=45);

  for(const marker of [
    "local:test","display_name='TEST'","email::text='test'",
    "BOOTSTRAP-TEST-WB01-VIEW-2026-09-05",
    "CLEANUP0045_TEST_IDENTITY_CARDINALITY_INVALID",
    "CLEANUP0045_TEST_ASSIGNMENT_MARKER_INVALID",
    "CLEANUP0045_TEST_AUDIT_MARKER_INVALID",
    "CLEANUP0045_TEST_IDENTITY_SESSION_STILL_ACTIVE"
  ])assert.ok(migration.includes(marker),marker);

  assert.match(migration,/DELETE FROM public\.audit_events/);
  assert.match(migration,/DELETE FROM public\.account_permission_assignments/);
  assert.match(migration,/DELETE FROM public\.app_users/);
  assert.doesNotMatch(migration,/local:admin/);
});
