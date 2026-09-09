import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
const read=(p)=>readFile(p,"utf8");

test("0044 removes only the historical TEST-CMD command/conversation fixture",async()=>{
  const migration=await read("database/migrations/0044_command_acceptance_fixture_cleanup.sql");
  const manifest=await read("database/migrations/migration_checksum_manifest.yaml");
  const neon=await read("src/server/database/neonRuntime.ts");
  const sep="\nINSERT INTO public.schema_migration_history";
  const idx=migration.indexOf(sep);
  assert.ok(idx>0);
  const checksum=createHash("sha256").update(migration.slice(0,idx)).digest("hex");
  assert.equal(checksum,"4115f0e111e13dcbb044432871ba7116276ace5ef50083c8c402ba6cb5a60579");
  assert.ok(manifest.includes("4115f0e111e13dcbb044432871ba7116276ace5ef50083c8c402ba6cb5a60579"));
  assert.match(neon,/MAX_SUPPORTED_MIGRATION_COUNT = 44/);

  for(const marker of [
    "TEST-CMD-001",
    "TEST-CMD-CREATE-001",
    "TEST-STR-SEND-001",
    "CLEANUP0044_TEST_PROJECT_MARKER_INVALID",
    "CLEANUP0044_TEST_PROJECT_VERSION_MARKER_INVALID",
    "CLEANUP0044_TEST_CONVERSATION_MARKER_INVALID",
    "CLEANUP0044_TEST_MESSAGE_MARKER_INVALID",
    "CLEANUP0044_SHARED_WORKSPACE_MUST_REMAIN",
  ]) assert.ok(migration.includes(marker),marker);

  assert.match(migration,/DELETE FROM public\.conversation_messages/);
  assert.match(migration,/DELETE FROM public\.conversations/);
  assert.match(migration,/UPDATE public\.projects\s+SET active_version_id=NULL/);
  assert.match(migration,/DELETE FROM public\.project_versions/);
  assert.match(migration,/DELETE FROM public\.projects/);
  assert.doesNotMatch(migration,/DELETE FROM public\.workspaces/);
  const businessInsert=migration.slice(0,idx).match(/INSERT INTO public\.(?!schema_migration_history)/g)??[];
  assert.equal(businessInsert.length,0);
});
