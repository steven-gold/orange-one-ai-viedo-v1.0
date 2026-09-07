import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("SOC-01 Draft/Candidate runtime reuses Current Authority owners and exact registered routes", async () => {
  const authority = await read("authority/pages/admin/SOC-01/ACPOS_SOC-01_SOCIAL_PUBLISHING_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml");
  const contract = await read("src/domain/social/socRuntimeContract.ts");
  const sharedDraftRoute = await read("src/app/v1/drafts/route.ts");
  const candidateRoute = await read("src/app/v1/candidates/[id]/decision/route.ts");
  const contentRuntime = await read("src/server/social/productionSocContentRuntime.ts");
  const candidateRuntime = await read("src/server/shared/candidateDecisionRuntime.ts");
  const identity = await read("src/server/shared/identityPageCommandRuntime.ts");

  assert.match(authority, /operation_id: saveDraft[\s\S]*path: \/v1\/drafts[\s\S]*owner: Existing Draft\/Candidate owner/);
  assert.match(authority, /operation_id: decideCandidate[\s\S]*path: \/v1\/candidates\/\{id\}\/decision[\s\S]*owner: Existing Candidate owner/);
  assert.match(contract, /SOC01_IMPLEMENTATION_STATUS="PARTIAL_RUNTIME_BOUND_PENDING_RELEASE"/);
  assert.match(contract, /SOC01_CONTENT_CANDIDATE_IMPLEMENTATION_STATUS="RUNTIME_BOUND_PENDING_RELEASE"/);

  assert.match(sharedDraftRoute, /pageUid === "admin:SOC-01"/);
  assert.match(sharedDraftRoute, /operation_id: "saveDraft"/);
  assert.match(sharedDraftRoute, /runIamOperation/);
  assert.match(candidateRoute, /decideCandidate/);
  assert.match(candidateRuntime, /bindIdentityPageCommandRuntimes/);
  assert.match(candidateRuntime, /namedReason/);

  assert.match(identity, /evaluateResourceAction\("api:saveDraft","EXECUTE"\)/);
  assert.match(identity, /evaluateResourceAction\("api:decideCandidate","EXECUTE"\)/);
  assert.match(identity, /configureCandidateDecisionRuntime/);
  assert.match(identity, /decideProductionSocCandidate/);

  assert.match(contentRuntime, /FROM public\.content_packages/);
  assert.match(contentRuntime, /kind='SOC_CONTENT_DRAFT'/);
  assert.match(contentRuntime, /SOC01_IDEMPOTENCY_KEY_REQUIRED/);
  assert.match(contentRuntime, /SOC01_DRAFT_VERSION_CONFLICT/);
  assert.match(contentRuntime, /SOC01_CANDIDATE_VERSION_CONFLICT/);
  assert.match(contentRuntime, /SOC01_SOURCE_PACKAGE_CHANGED/);
  assert.match(contentRuntime, /external_request_sent: false/);
  assert.match(contentRuntime, /publish_triggered: false/);
  assert.doesNotMatch(contentRuntime, /fetch\(|ProviderGateway|external_request_sent:\s*true/);
});

test("SOC-01 Production UI enables only materialized content actions and derives gates from real owners", async () => {
  const commandPort = await read("src/domain/social/socCommandPort.ts");
  const controlRuntime = await read("src/components/pages/SocControlRuntime.tsx");
  const adapters = await read("src/domain/catalog/identityClientCommandAdapters.ts");
  const projection = await read("src/server/shared/pageCatalogProjectionRuntime.ts");

  assert.match(commandPort, /isSocCommandActionBound/);
  assert.match(controlRuntime, /isSocCommandActionBound/);
  assert.doesNotMatch(controlRuntime, /isSocCommandAdapterBound/);

  assert.match(adapters, /"SOC-01-ACT-CONTENT-SAVE"/);
  assert.match(adapters, /"SOC-01-ACT-CANDIDATE-DECIDE"/);
  assert.match(adapters, /"SOC-01-ACT-REFRESH"/);
  assert.match(adapters, /supports:/);
  assert.doesNotMatch(adapters, /"SOC-01-ACT-PUBLISH-REQUEST"[\s\S]{0,160}supports/);
  assert.match(adapters, /page_uid: "admin:SOC-01"/);
  assert.match(adapters, /\/v1\/drafts/);
  assert.match(adapters, /\/v1\/candidates\/\$\{encodeURIComponent\(candidateRef\)\}\/decision/);

  assert.match(projection, /FROM content_packages/);
  assert.match(projection, /FROM acpos_runtime\.entities/);
  assert.match(projection, /kind='SOC_CONTENT_DRAFT'/);
  assert.match(projection, /"SOC-01-GATE-CONTENT": Boolean\(contentPackage\)/);
  assert.match(projection, /"SOC-01-GATE-CANDIDATE": candidateStatus === "REVIEW"/);
  assert.match(projection, /"SOC-01-GATE-PUBLISH": candidateStatus === "APPROVED" && targets\.length > 0/);
});

test("migration 0022 stages only the two missing SOC API assignments and stays pending Production apply", async () => {
  const migration = await read("database/migrations/0022_soc_draft_candidate_permission_closure.sql");
  const manifest = await read("database/migrations/migration_checksum_manifest.yaml");
  const neonRuntime = await read("src/server/database/neonRuntime.ts");

  assert.match(migration, /api:saveDraft/);
  assert.match(migration, /api:decideCandidate/);
  assert.match(migration, /resource_count <> 2/);
  assert.match(migration, /approved_allow_count <> 2/);
  assert.match(migration, /ON CONFLICT \(user_id,resource_id,action,version_no\) DO NOTHING/);
  assert.match(migration, /CR-SOC-0022-PENDING-PRODUCTION-APPLY/);
  assert.match(migration, /4592e475b078613928117e40a304c3d039a187e234a3ef257844226cb4b50047/);
  assert.doesNotMatch(migration, /INSERT INTO public\.permission_resources/);
  assert.doesNotMatch(migration, /CREATE ROLE|ALTER ROLE/);

  assert.match(manifest, /contract_id: ACPOS-MIGRATION-CHECKSUM-1\.0\.10/);
  assert.match(manifest, /migration_id: 0022_soc_draft_candidate_permission_closure/);
  assert.match(manifest, /payload_sha256: 4592e475b078613928117e40a304c3d039a187e234a3ef257844226cb4b50047/);
  assert.match(manifest, /approval_ref: CR-SOC-0022-PENDING-PRODUCTION-APPLY/);
  assert.match(manifest, /production_apply: PENDING/);
  assert.match(neonRuntime, /REQUIRED_MIGRATION_COUNT = 20/);
  assert.match(neonRuntime, /MAX_SUPPORTED_MIGRATION_COUNT = 23/);
});
