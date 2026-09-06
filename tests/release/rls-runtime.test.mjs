import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("migration 0016 materializes a non-BYPASSRLS role and session-bound policies", async () => {
  const migration = await read("database/migrations/0016_postgresql_rls_runtime_foundation.sql");
  const manifest = await read("database/migrations/migration_checksum_manifest.yaml");

  assert.match(migration, /CREATE ROLE acpos_app_runtime NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS/);
  assert.match(migration, /RAISE EXCEPTION 'ACPOS_RUNTIME_ROLE_SECURITY_MISMATCH'/);
  assert.doesNotMatch(migration, /ALTER ROLE acpos_app_runtime/);
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
  assert.match(migration, /8c8ca99cbbc171e45940869da014dcbdde7130d2e0dd73d1b2c1cac39e7e3cd4/);
  assert.match(manifest, /contract_id: ACPOS-MIGRATION-CHECKSUM-1\.0\.5/);
  assert.match(manifest, /migration_id: 0016_postgresql_rls_runtime_foundation/);
  assert.match(manifest, /payload_sha256: 8c8ca99cbbc171e45940869da014dcbdde7130d2e0dd73d1b2c1cac39e7e3cd4/);
});

test("migration 0017 extends project-scope RLS to Core story tables", async () => {
  const migration = await read("database/migrations/0017_core_story_rls_closure.sql");
  const manifest = await read("database/migrations/migration_checksum_manifest.yaml");

  assert.match(migration, /ALTER TABLE public\.mother_locks ENABLE ROW LEVEL SECURITY/);
  assert.match(migration, /ALTER TABLE public\.story_candidates ENABLE ROW LEVEL SECURITY/);
  assert.match(migration, /GRANT SELECT ON public\.department_tasks, public\.child_locks TO acpos_app_runtime/);
  assert.match(migration, /acpos_runtime\.can_access_project\(project_id\)/);
  assert.match(migration, /acpos_runtime\.can_manage_project\(project_id\)/);
  assert.match(migration, /0017_core_story_rls_closure/);
  assert.match(migration, /6b2cc216f5f49a40e6d310217c6ddc284361960c063b7b0ad60d8be9eaac7551/);
  assert.match(manifest, /migration_id: 0017_core_story_rls_closure/);
  assert.match(manifest, /payload_sha256: 6b2cc216f5f49a40e6d310217c6ddc284361960c063b7b0ad60d8be9eaac7551/);
});

test("production query runtime sets local non-owner role before protected queries", async () => {
  const neonRuntime = await read("src/server/database/neonRuntime.ts");
  const rlsRuntime = await read("src/server/database/rlsRuntime.ts");
  const identityRuntime = await read("src/server/shared/identityPageCommandRuntime.ts");
  const coreClient = await read("src/domain/core/coreClientPort.ts");

  assert.match(neonRuntime, /REQUIRED_MIGRATION_COUNT = 17/);
  assert.match(rlsRuntime, /RLS_RUNTIME_ROLE = "acpos_app_runtime"/);
  assert.match(rlsRuntime, /set_config\('acpos\.session_token_hash'/);
  assert.match(rlsRuntime, /SET LOCAL ROLE acpos_app_runtime/);
  assert.match(identityRuntime, /hashSessionToken/);
  assert.match(identityRuntime, /runRlsActorQuery/);

  const scopedCalls = (identityRuntime.match(/runRlsActorQuery\(/g) ?? []).length;
  assert.ok(scopedCalls >= 17, `expected at least 17 actor-scoped protected queries, got ${scopedCalls}`);

  assert.match(coreClient, /CORE-01-ACT-STORY-CANDIDATE/);
  assert.match(coreClient, /STORY_CANDIDATE_REGISTERED_SCHEMA_PAYLOAD_REQUIRED/);
  assert.match(identityRuntime, /STORY_CANDIDATE_FIELD_REQUIRED/);
  assert.match(identityRuntime, /strengths/);
  assert.match(identityRuntime, /weaknesses/);
  assert.match(identityRuntime, /market_positioning/);
  assert.match(identityRuntime, /production_cost/);
  assert.match(identityRuntime, /recommendation/);
  assert.match(identityRuntime, /generated_by_subject_type/);
  assert.match(identityRuntime, /'USER'/);
});

test("projection owners do not bypass protected rows", async () => {
  const wb01 = await read("src/server/dashboard/wb01ProjectionRuntime.ts");
  const catalog = await read("src/server/shared/pageCatalogProjectionRuntime.ts");

  assert.match(wb01, /runRlsActorQuery/);
  assert.match(wb01, /hashSessionToken/);
  assert.match(wb01, /JOIN topics tp ON tp\.topic_id = cl\.topic_id/);
  assert.match(wb01, /migrationCount === 17/);

  assert.match(catalog, /runRlsActorQuery/);
  assert.match(catalog, /hashSessionToken/);
  assert.match(catalog, /session_token_hash/);
  assert.match(catalog, /readProjectRefs\(sql, sessionTokenHash\)/);
  assert.match(catalog, /readTopicRefs\(sql, sessionTokenHash\)/);
  assert.match(catalog, /readDepartmentTasks\(sql, sessionTokenHash/);
  assert.match(catalog, /readCoreProjection\(sql, sessionTokenHash\)/);
  assert.match(catalog, /readStrategyFromDb\(sql, sessionTokenHash\)/);
});
