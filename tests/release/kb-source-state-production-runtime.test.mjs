import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("KB-01 pause/resume materializes Current KnowledgeSource state/version contract without provider execution", async () => {
  const authority = await read("authority/pages/admin/KB-01/ACPOS_KB-01_FINAL_LOCKED_ENCODING.yaml");
  const runtime = await read("src/server/knowledge/productionKnowledgeSourceStateRuntime.ts");
  const identity = await read("src/server/shared/identityPageCommandRuntime.ts");
  const knowledgeRuntime = await read("src/server/knowledge/knowledgeRuntime.ts");

  assert.match(authority, /SourceStateChangeRequest:[\s\S]*source_id[\s\S]*expected_version[\s\S]*reason[\s\S]*correlation_id[\s\S]*idempotency_key/);
  assert.match(authority, /DRAFT->ACTIVE[\s\S]*ACTIVE->PAUSED[\s\S]*PAUSED->ACTIVE/);
  assert.match(authority, /pauseKnowledgeSource[\s\S]*\/v1\/knowledge\/sources\/\{sourceId\}\/pause/);
  assert.match(authority, /resumeKnowledgeSource[\s\S]*\/v1\/knowledge\/sources\/\{sourceId\}\/resume/);

  assert.match(runtime, /exactKeys\(payload\)/);
  assert.match(runtime, /KB01_SOURCE_ID_MISMATCH/);
  assert.match(runtime, /KB01_EXPECTED_VERSION_MISSING/);
  assert.match(runtime, /KB01_SOURCE_STATE_REASON_REQUIRED/);
  assert.match(runtime, /KB01_CORRELATION_ID_MISMATCH/);
  assert.match(runtime, /KB01_IDEMPOTENCY_CONFLICT/);
  assert.match(runtime, /status=\$\{targetState\}/);
  assert.match(runtime, /source_version=source_version\+1/);
  assert.match(runtime, /INSERT INTO public\.audit_events/);
  assert.match(runtime, /WITH updated AS/);
  assert.match(runtime, /knowledge\.source\.paused/);
  assert.match(runtime, /knowledge\.source\.resumed/);
  assert.match(runtime, /external_request_sent: false/);
  assert.doesNotMatch(runtime, /fetch\(|ProviderGateway|external_request_sent:\s*true/);

  assert.match(identity, /evaluateResourceAction\("permission:knowledge\.source\.configure","EXECUTE"\)/);
  assert.match(identity, /transitionProductionKnowledgeSource/);
  assert.match(identity, /KB01_OPERATION_PERMISSION_MAPPING_REQUIRED/);
  assert.match(knowledgeRuntime, /statusForReason/);
  assert.match(knowledgeRuntime, /VERSION_CONFLICT/);
  assert.match(knowledgeRuntime, /STATE_GUARD/);
});

test("KB-01 Production projection and UI use real source_version and exact state-transition request schema", async () => {
  const projection = await read("src/server/shared/pageCatalogProjectionRuntime.ts");
  const visual = await read("src/components/pages/KnowledgeAdminVisual.tsx");

  assert.match(projection, /source_version::text AS source_version/);
  assert.match(projection, /selected_source/);
  assert.match(projection, /"KB-01-CTL-SOURCE-PAUSE": asText\(first\?\.status\) === "ACTIVE"/);
  assert.match(projection, /"KB-01-CTL-SOURCE-RESUME": asText\(first\?\.status\) === "PAUSED"/);

  assert.match(visual, /window\.prompt/);
  assert.match(visual, /reason: reason\.trim\(\)/);
  assert.match(visual, /correlation_id: correlationId/);
  assert.match(visual, /"x-correlation-id": correlationId/);
  assert.match(visual, /expected_version: sourceVersion/);
  assert.match(visual, /idempotency_key:/);
});

test("migration 0024 stages KnowledgeSource state/version, configure permission, and KB-scoped RLS only", async () => {
  const migration = await read("database/migrations/0024_kb_source_state_permission_rls_closure.sql");
  const manifest = await read("database/migrations/migration_checksum_manifest.yaml");
  const neonRuntime = await read("src/server/database/neonRuntime.ts");

  assert.match(migration, /status TYPE text USING status::text/);
  assert.match(migration, /source_version integer NOT NULL DEFAULT 1/);
  assert.match(migration, /status IN \('DRAFT','ACTIVE','PAUSED','RETIRED'\)/);
  assert.match(migration, /permission:knowledge\.source\.configure/);
  assert.match(migration, /aa55cc3a-bab5-5c45-9625-617de64a8fff/);
  assert.match(migration, /acpos_runtime\.can_configure_knowledge_source/);
  assert.match(migration, /ALTER TABLE public\.knowledge_sources ENABLE ROW LEVEL SECURITY/);
  assert.match(migration, /ALTER TABLE public\.audit_events ENABLE ROW LEVEL SECURITY/);
  assert.match(migration, /acpos_knowledge_sources_configure_update/);
  assert.match(migration, /acpos_audit_events_kb_insert/);
  assert.match(migration, /de41bfa7773dd495056b49e656fa8fd0fb5c032b5d0f680065aa4f90911c9341/);
  assert.doesNotMatch(migration, /INSERT INTO public\.knowledge_sources/);
  assert.doesNotMatch(migration, /CREATE TABLE .*knowledge/i);

  assert.match(manifest, /contract_id: ACPOS-MIGRATION-CHECKSUM-1\.0\.\d+/);
  assert.match(manifest, /migration_id: 0024_kb_source_state_permission_rls_closure/);
  assert.match(manifest, /payload_sha256: de41bfa7773dd495056b49e656fa8fd0fb5c032b5d0f680065aa4f90911c9341/);
  assert.ok(Number(neonRuntime.match(/MAX_SUPPORTED_MIGRATION_COUNT = (\d+)/)?.[1] ?? 0) >= 24);
});
