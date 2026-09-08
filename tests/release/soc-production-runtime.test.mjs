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
  assert.match(adapters, /"SOC-01-ACT-POLICY-CONFIG"/);
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
  assert.match(projection, /"SOC-01-GATE-POLICY": policyTargetStatus === "JOINED"/);
  assert.match(projection, /"SOC-01-GATE-PUBLISH": publishContextReady/);
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

  assert.match(manifest, /contract_id: ACPOS-MIGRATION-CHECKSUM-1\.0\.\d+/);
  assert.match(manifest, /migration_id: 0022_soc_draft_candidate_permission_closure/);
  assert.match(manifest, /payload_sha256: 4592e475b078613928117e40a304c3d039a187e234a3ef257844226cb4b50047/);
  assert.match(manifest, /approval_ref: CR-SOC-0022-PENDING-PRODUCTION-APPLY/);
  assert.match(manifest, /production_apply: PENDING/);
  assert.match(neonRuntime, /REQUIRED_MIGRATION_COUNT = 20/);
  assert.ok(Number(neonRuntime.match(/MAX_SUPPORTED_MIGRATION_COUNT = (\d+)/)?.[1] ?? 0) >= 22);
});


test("SOC-01 target posting policy runtime reuses exact Authority request, route and local persistence owner", async () => {
  const authority = await read("authority/pages/admin/SOC-01/ACPOS_SOC-01_SOCIAL_PUBLISHING_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml");
  const interactions = await read("07_ui/interaction_registry.yaml");
  const adapters = await read("src/domain/catalog/identityClientCommandAdapters.ts");
  const identity = await read("src/server/shared/identityPageCommandRuntime.ts");
  const runtime = await read("src/server/social/productionSocPolicyRuntime.ts");
  const route = await read("src/app/v1/social/targets/[targetId]/posting-policy/route.ts");
  const projection = await read("src/server/shared/pageCatalogProjectionRuntime.ts");

  assert.match(authority, /ConfigureSocialTargetPolicyRequest:[\s\S]*minimum_interval_hours[\s\S]*daily_limit[\s\S]*weekly_limit/);
  assert.match(authority, /operation_id: configureSocialTargetPolicy[\s\S]*method: PUT[\s\S]*\/v1\/social\/targets\/\{targetId\}\/posting-policy[\s\S]*owner: PublishingService/);
  assert.match(interactions, /soc_policy_interaction_registry:/);
  assert.match(interactions, /SOC-01-BTN-POLICY-CONFIG[\s\S]*ConfigureSocialTargetPolicyRequest/);
  assert.match(route, /createSocRoute\("configureSocialTargetPolicy"\)/);
  assert.match(adapters, /openSocTargetPolicyDialog/);
  assert.match(adapters, /method="PUT"/);
  assert.match(adapters, /expected_version:targetVersion/);
  assert.match(identity, /SOC_TARGET_POLICY_PERMISSIONS/);
  assert.match(identity, /configureProductionSocTargetPolicy/);
  assert.match(runtime, /acpos_runtime\.idempotency/);
  assert.match(runtime, /pg_advisory_xact_lock/);
  assert.match(runtime, /join_status='READY_TO_POST'/);
  assert.match(runtime, /version=t\.version\+1/);
  assert.match(runtime, /external_request_sent',false/);
  assert.match(runtime, /publish_triggered',false/);
  assert.doesNotMatch(runtime, /fetch\(|ProviderGateway/);
  assert.match(projection, /runRlsActorQuery\([\s\S]*FROM public\.social_market_targets/);
  assert.match(projection, /selected:[\s\S]*target_id:[\s\S]*target_version:/);
});

test("migration 0030 stages only existing SOC policy resources, target version and session-bound RLS", async () => {
  const migration = await read("database/migrations/0030_soc_target_policy_permission_rls_closure.sql");
  const manifest = await read("database/migrations/migration_checksum_manifest.yaml");
  const neonRuntime = await read("src/server/database/neonRuntime.ts");

  assert.match(migration, /action:admin:SOC-04:ACT-SOCIAL-TARGET-POLICY/);
  assert.match(migration, /control:CTRL-ADMIN-SOC-04-ACT-01-ACT-SOCIAL-TARGET-POLICY/);
  assert.match(migration, /api:configureSocialTargetPolicy/);
  assert.match(migration, /resource_count <> 3/);
  assert.match(migration, /approved_allow_count <> 3/);
  assert.match(migration, /ADD COLUMN IF NOT EXISTS version bigint NOT NULL DEFAULT 1/);
  assert.match(migration, /ALTER TABLE public\.social_market_targets ENABLE ROW LEVEL SECURITY/);
  assert.match(migration, /ALTER TABLE acpos_runtime\.idempotency ENABLE ROW LEVEL SECURITY/);
  assert.match(migration, /acpos_social_market_targets_soc_policy_update/);
  assert.match(migration, /acpos_idempotency_actor_insert/);
  assert.match(migration, /acpos_audit_events_soc_insert/);
  assert.match(migration, /d43ee379e03c27824e61613f89ffdb75823182ef3397bd9c507d70b943aed518/);
  assert.doesNotMatch(migration, /INSERT INTO public\.permission_resources/);
  assert.doesNotMatch(migration, /CREATE ROLE|ALTER ROLE/);
  assert.match(manifest, /migration_id: 0030_soc_target_policy_permission_rls_closure/);
  assert.match(manifest, /payload_sha256: d43ee379e03c27824e61613f89ffdb75823182ef3397bd9c507d70b943aed518/);
  assert.match(manifest, /production_apply: PENDING/);
  assert.ok(Number(neonRuntime.match(/MAX_SUPPORTED_MIGRATION_COUNT = (\\d+)/)?.[1] ?? 0) >= 30);
});


test("SOC-01 publish request closes canonical target/content relation without metadata identity fallback", async () => {
  const authority = await read("authority/pages/admin/SOC-01/ACPOS_SOC-01_SOCIAL_PUBLISHING_SINGLE_PAGE_FINAL_LOCKED_ENCODING.yaml");
  const migration = await read("database/migrations/0031_soc_publish_request_relation_runtime.sql");
  const manifest = await read("database/migrations/migration_checksum_manifest.yaml");
  const runtime = await read("src/server/social/productionSocPublishRuntime.ts");
  const route = await read("src/app/v1/social/targets/[targetId]/publish/route.ts");
  const identity = await read("src/server/shared/identityPageCommandRuntime.ts");
  const projection = await read("src/server/shared/pageCatalogProjectionRuntime.ts");
  const adapters = await read("src/domain/catalog/identityClientCommandAdapters.ts");
  const interactions = await read("07_ui/interaction_registry.yaml");

  assert.match(authority, /canonical_column: social_target_id[\s\S]*metadata_target_id: FORBIDDEN/);
  assert.match(authority, /canonical_column: content_package_id[\s\S]*foreign_key: public\.content_packages\.content_package_id/);
  assert.match(authority, /canonical_identity_keys_forbidden:[\s\S]*target_id[\s\S]*content_package_id[\s\S]*channel_account_id[\s\S]*release_package_id/);
  assert.match(authority, /target_state_after_request: PENDING_EXTERNAL/);
  assert.match(route, /createSocRoute\("requestSocialTargetPublish"\)/);

  assert.match(migration, /ADD COLUMN IF NOT EXISTS social_target_id uuid/);
  assert.match(migration, /ADD COLUMN IF NOT EXISTS content_package_id uuid/);
  assert.match(migration, /publish_requests_social_target_id_fkey/);
  assert.match(migration, /publish_requests_content_package_id_fkey/);
  assert.match(migration, /publish_requests_metadata_no_canonical_identity/);
  assert.match(migration, /NOT metadata \?\| ARRAY/);
  assert.match(migration, /request_soc_target_publish/);
  assert.match(migration, /SOC01_CONTENT_NOT_APPROVED/);
  assert.match(migration, /join_status='PENDING_EXTERNAL'/);
  assert.match(migration, /external_request_sent',false/);
  assert.match(migration, /81f65e614d720ad44b8d8d4b2594f7128caac5af396d16221f15f46a31fc600e/);
  assert.doesNotMatch(migration, /metadata[^\n]*target_id/);
  assert.doesNotMatch(migration, /INSERT INTO public\.permission_resources/);

  assert.match(manifest, /migration_id: 0031_soc_publish_request_relation_runtime/);
  assert.match(manifest, /payload_sha256: 81f65e614d720ad44b8d8d4b2594f7128caac5af396d16221f15f46a31fc600e/);
  assert.match(identity, /SOC_PUBLISH_REQUEST_PERMISSIONS/);
  assert.match(identity, /requestProductionSocTargetPublish/);
  assert.match(runtime, /request_soc_target_publish/);
  assert.match(runtime, /requestSocialTargetPublish/);
  assert.match(runtime, /createHash\("sha256"\)/);
  assert.doesNotMatch(runtime, /fetch\(|ProviderGateway/);
  assert.match(projection, /FROM public\.publish_requests/);
  assert.match(projection, /content_package_id: packageRef/);
  assert.match(projection, /channel_account_id:/);
  assert.match(adapters, /openSocPublishRequestConfirm/);
  assert.match(adapters, /\/v1\/social\/targets\/\$\{encodeURIComponent\(targetId\)\}\/publish/);
  assert.match(interactions, /soc_publish_request_interaction_registry:/);
  assert.match(interactions, /SOC-01-BTN-PUBLISH[\s\S]*RequestSocialTargetPublishRequest/);
});
