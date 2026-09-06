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
  assert.match(manifest, /contract_id: ACPOS-MIGRATION-CHECKSUM-1\.0\.6/);
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

test("migration 0018 protects department runtime tables by project authority", async () => {
  const migration = await read("database/migrations/0018_department_runtime_rls_closure.sql");
  const manifest = await read("database/migrations/migration_checksum_manifest.yaml");

  assert.match(migration, /project_id_for_task/);
  assert.match(migration, /project_id_for_output/);
  assert.match(migration, /GRANT SELECT, INSERT, UPDATE, DELETE ON/);
  assert.match(migration, /TO acpos_app_runtime/);

  const protectedTables = [...migration.matchAll(/ALTER TABLE public\.([a-z_]+) ENABLE ROW LEVEL SECURITY/g)].map((match) => match[1]);
  assert.deepEqual(
    protectedTables,
    [
      "department_tasks",
      "task_outputs",
      "findings",
      "correction_requests",
      "scorecards",
      "handoffs",
      "release_packages",
    ],
  );

  const policies = [...migration.matchAll(/CREATE POLICY ([a-z_]+)/g)].map((match) => match[1]);
  assert.equal(policies.length, 14);
  assert.match(migration, /acpos_runtime\.can_access_project/);
  assert.match(migration, /acpos_runtime\.can_manage_project/);
  assert.match(migration, /DEPARTMENT_RLS_EXISTING_PROJECT_RESOLUTION_GAP/);
  assert.match(migration, /0018_department_runtime_rls_closure/);
  assert.match(migration, /d898fcc1a2ccd0d3b814e3cd0578b4c0a8a573f84e96a0e68c68b4af1b2212b5/);
  assert.match(manifest, /migration_id: 0018_department_runtime_rls_closure/);
  assert.match(manifest, /payload_sha256: d898fcc1a2ccd0d3b814e3cd0578b4c0a8a573f84e96a0e68c68b4af1b2212b5/);
});

test("production query runtime sets local non-owner role before protected queries", async () => {
  const neonRuntime = await read("src/server/database/neonRuntime.ts");
  const rlsRuntime = await read("src/server/database/rlsRuntime.ts");
  const identityRuntime = await read("src/server/shared/identityPageCommandRuntime.ts");
  const coreClient = await read("src/domain/core/coreClientPort.ts");

  assert.match(neonRuntime, /REQUIRED_MIGRATION_COUNT = 18/);
  assert.match(neonRuntime, /MAX_SUPPORTED_MIGRATION_COUNT = 19/);
  assert.doesNotMatch(neonRuntime, /TARGET_MIGRATION_COUNT/);
  assert.match(neonRuntime, /isSupportedMigrationCount/);
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
  assert.match(wb01, /isSupportedMigrationCount\(migrationCount\)/);
  assert.doesNotMatch(wb01, /TARGET_MIGRATION_COUNT/);

  assert.match(catalog, /runRlsActorQuery/);
  assert.match(catalog, /hashSessionToken/);
  assert.match(catalog, /session_token_hash/);
  assert.match(catalog, /readProjectRefs\(sql, sessionTokenHash\)/);
  assert.match(catalog, /readTopicRefs\(sql, sessionTokenHash\)/);
  assert.match(catalog, /readDepartmentTasks\(sql, sessionTokenHash/);
  assert.match(catalog, /readCoreProjection\(sql, sessionTokenHash\)/);
  assert.match(catalog, /readStrategyFromDb\(sql, sessionTokenHash\)/);
});
