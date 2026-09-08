import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("INFO-01 registries materialize exact Current workspace operations without inventing payload fields", async () => {
  const payloads = await read("03_api/business_payload_registry.yaml");
  const operations = await read("03_api/operation_registry.yaml");

  assert.match(payloads, /contract_id: ACPOS-CURRENT-BUSINESS-PAYLOAD-REGISTRY-1\.1\.0/);
  assert.match(payloads, /source_page_uids: \[admin:STR-01, admin:STR-04, workspace:INFO-01\]/);
  assert.match(payloads, /operation_id: adoptContextCandidate[\s\S]*request_schema_id: AdoptContextCandidateRequest[\s\S]*context_candidate_id[\s\S]*decision_reason/);
  assert.match(payloads, /operation_id: decideCandidate[\s\S]*request_schema_id: DecideCandidateRequest[\s\S]*candidate_id[\s\S]*values: \[ACCEPTED, REJECTED\]/);

  assert.match(operations, /coverage: IDENTITY_SESSION_AIAPI_PROVIDER_IAM_AND_INFO_GOVERNED_OPERATIONS/);
  assert.match(operations, /operation_id: searchProjection[\s\S]*authorization_by_page:[\s\S]*admin:IAM-01:[\s\S]*workspace:INFO-01:/);
  assert.match(operations, /operation_id: refreshProjection[\s\S]*authorization_resource_key: api:refreshProjection/);
  assert.match(operations, /operation_id: adoptContextCandidate[\s\S]*persistence_owner: public\.context_candidates/);
  assert.match(operations, /operation_id: decideCandidate[\s\S]*runtime_owner: CANDIDATE_DECISION_RUNTIME/);
  assert.match(operations, /operation_id: exportProjection[\s\S]*materialization_status: BLOCKED_NO_CANONICAL_EXPORT_PERSISTENCE_OWNER/);
});

test("INFO-01 Production projection and client fail closed on unresolved evidence/export/human decision inputs", async () => {
  const projection = await read("src/server/shared/pageCatalogProjectionRuntime.ts");
  const port = await read("src/domain/info/infoProjectionPort.ts");
  const client = await read("src/domain/catalog/identityClientCommandAdapters.ts");

  assert.match(projection, /readInfoFromDb[\s\S]*runRlsActorQuery\([\s\S]*FROM fact_packs f/);
  assert.match(projection, /FROM context_candidates c[\s\S]*JOIN fact_packs f/);
  assert.match(projection, /"INFO-01-GATE-EVIDENCE": false/);
  assert.match(projection, /"INFO-01-GATE-EXPORT": false/);
  assert.match(projection, /"INFO-01-GATE-ADOPT": false/);
  assert.match(projection, /"INFO-01-GATE-DECIDE": false/);
  assert.match(port, /export function isInfoProjectionResolverBound\(\)\{return true;\}/);
  assert.match(port, /function normalizeInfoProjection/);

  assert.match(client, /projection_type: "INFO_WORKSPACE"/);
  assert.match(client, /scope_ref/);
  assert.match(client, /INFO_EXPORT_OWNER_NOT_MATERIALIZED/);
  assert.match(client, /INFO_HUMAN_ADOPTION_INPUT_NOT_MATERIALIZED/);
  assert.match(client, /INFO_HUMAN_DECISION_INPUT_NOT_MATERIALIZED/);
  assert.doesNotMatch(client, /decision:\s*"ACCEPTED"/);
});

test("INFO-01 Production runtime separates adoption from candidate decision and audits exact owner context", async () => {
  const runtime = await read("src/server/info/productionInfoRuntime.ts");
  const identity = await read("src/server/shared/identityPageCommandRuntime.ts");

  assert.match(runtime, /f\.classification <= 'INTERNAL'::classification_level/);
  assert.match(runtime, /SET decision_status='APPROVED'/);
  assert.match(runtime, /'ADOPTED'::text AS state/);
  assert.match(runtime, /decision!=="ACCEPTED"&&decision!=="REJECTED"/);
  assert.match(runtime, /SET decision_status=\$\{decision\}::decision_status/);
  assert.match(runtime, /'context\.adoption_requested'/);
  assert.match(runtime, /'candidate\.decided'/);
  assert.match(runtime, /INFO01_EXPORT_OWNER_NOT_MATERIALIZED/);
  assert.match(runtime, /false AS direct_owner_mutation/);

  assert.match(identity, /refreshProjection:\{resource_key:"api:refreshProjection",action:"EXECUTE"\}/);
  assert.match(identity, /searchProjection:\{resource_key:"api:searchProjection",action:"EXECUTE"\}/);
  assert.match(identity, /adoptContextCandidate:\{resource_key:"api:adoptContextCandidate",action:"EXECUTE"\}/);
  assert.match(identity, /if\(pageUid==="workspace:INFO-01"\)return decideProductionInfoCandidate\(request\)/);
  assert.match(identity, /if \(pageUid === "workspace:INFO-01"\) \{[\s\S]*return executeProductionInfoCommand\(request\);/);
});

test("migration 0029 stages INFO-specific API authority and session-bound INTERNAL-or-lower RLS only", async () => {
  const migration = await read("database/migrations/0029_info_context_candidate_permission_rls_closure.sql");
  const manifest = await read("database/migrations/migration_checksum_manifest.yaml");
  const neonRuntime = await read("src/server/database/neonRuntime.ts");

  for (const resource of [
    "api:refreshProjection",
    "api:searchProjection",
    "api:adoptContextCandidate",
    "api:decideCandidate",
  ]) assert.ok(migration.includes(resource), resource);

  assert.match(migration, /resource_count <> 4/);
  assert.match(migration, /approved_allow_count <> 4/);
  assert.match(migration, /CASE WHEN r\.resource_key='api:decideCandidate' THEN 2 ELSE 1 END/);
  assert.match(migration, /a\.gate_profile->>'page_uid'='workspace:INFO-01'/);
  assert.match(migration, /classification <= 'INTERNAL'::classification_level/);
  assert.match(migration, /ALTER TABLE public\.fact_packs ENABLE ROW LEVEL SECURITY/);
  assert.match(migration, /ALTER TABLE public\.context_candidates ENABLE ROW LEVEL SECURITY/);
  assert.match(migration, /acpos_audit_events_info_insert/);
  assert.match(migration, /policy_count <> 5/);
  assert.match(migration, /a1494503e3dde66d9bcfcf9bdc0c18277bd942a5a415d827058df851dc8ba7b2/);
  assert.doesNotMatch(migration, /CREATE TABLE/);
  assert.doesNotMatch(migration, /INSERT INTO public\.permission_resources/);
  assert.doesNotMatch(migration, /INSERT INTO public\.fact_packs/);
  assert.doesNotMatch(migration, /INSERT INTO public\.context_candidates/);

  const contractVersion = Number(manifest.match(/contract_id: ACPOS-MIGRATION-CHECKSUM-1\.0\.(\d+)/)?.[1] ?? 0);
  assert.ok(contractVersion >= 16);
  assert.match(manifest, /migration_id: 0029_info_context_candidate_permission_rls_closure/);
  assert.match(manifest, /payload_sha256: a1494503e3dde66d9bcfcf9bdc0c18277bd942a5a415d827058df851dc8ba7b2/);
  assert.match(manifest, /approval_ref: CR-INFO-0029-PENDING-PRODUCTION-APPLY/);
  assert.ok(Number(neonRuntime.match(/MAX_SUPPORTED_MIGRATION_COUNT = (\d+)/)?.[1] ?? 0) >= 29);
});
