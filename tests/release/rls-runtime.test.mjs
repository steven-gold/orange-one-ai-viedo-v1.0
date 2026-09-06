import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("migration 0016 materializes a non-BYPASSRLS role and session-bound policies", async () => {
  const migration = await read("database/migrations/0016_postgresql_rls_runtime_foundation.sql");
  const manifest = await read("database/migrations/migration_checksum_manifest.yaml");

  assert.match(migration, /CREATE ROLE acpos_app_runtime NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS/);
  assert.match(migration, /ALTER ROLE acpos_app_runtime NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS/);
  assert.match(migration, /GRANT acpos_app_runtime TO neondb_owner/);
  assert.match(migration, /current_setting\('acpos\.session_token_hash', true\)/);
  assert.match(migration, /current_actor_user_id/);
  assert.match(migration, /current_actor_is_bootstrap_admin/);
  assert.match(migration, /can_access_project/);
  assert.match(migration, /can_manage_project/);
  assert.match(migration, /can_access_conversation/);

  const protectedTables = [...migration.matchAll(/ALTER TABLE public\.([a-z_]+) ENABLE ROW LEVEL SECURITY/g)].map((match) => match[1]);
  assert.deepEqual(
    protectedTables,
    [
      "account_permission_assignments",
      "user_ui_preferences",
      "project_memberships",
      "projects",
      "project_versions",
      "topics",
      "conversations",
      "conversation_messages",
    ],
  );

  assert.match(migration, /0016_postgresql_rls_runtime_foundation/);
  assert.match(migration, /9695cf577be5ea4aab5cd1a309112bab4e96da8a9743453b1a9bbb67b82b347d/);
  assert.match(manifest, /contract_id: ACPOS-MIGRATION-CHECKSUM-1\.0\.3/);
  assert.match(manifest, /migration_id: 0016_postgresql_rls_runtime_foundation/);
  assert.match(manifest, /payload_sha256: 9695cf577be5ea4aab5cd1a309112bab4e96da8a9743453b1a9bbb67b82b347d/);
});

test("production query runtime sets local non-owner role before protected queries", async () => {
  const neonRuntime = await read("src/server/database/neonRuntime.ts");
  const rlsRuntime = await read("src/server/database/rlsRuntime.ts");
  const identityRuntime = await read("src/server/shared/identityPageCommandRuntime.ts");

  assert.match(neonRuntime, /REQUIRED_MIGRATION_COUNT = 16/);
  assert.match(rlsRuntime, /RLS_RUNTIME_ROLE = "acpos_app_runtime"/);
  assert.match(rlsRuntime, /set_config\('acpos\.session_token_hash'/);
  assert.match(rlsRuntime, /SET LOCAL ROLE acpos_app_runtime/);
  assert.match(identityRuntime, /hashSessionToken/);
  assert.match(identityRuntime, /runRlsActorQuery/);

  const scopedCalls = (identityRuntime.match(/runRlsActorQuery\(/g) ?? []).length;
  assert.ok(scopedCalls >= 15, `expected at least 15 actor-scoped protected queries, got ${scopedCalls}`);
});
