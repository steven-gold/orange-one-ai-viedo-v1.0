import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const registry = await readFile("03_api/operation_registry.yaml", "utf8");
const authority = await readFile("authority/pages/admin/AIAPI-01/ACPOS_AIAPI-01_FINAL_LOCKED_ENCODING.yaml", "utf8");
const providerContract = await readFile("authority/global/ACPOS_PRODUCTION_SCRIPT_CONTENT_AND_PROVIDER_ADAPTER_CONTRACT_FINAL_LOCKED_V1.3.yaml", "utf8");
const runtime = await readFile("src/server/aiApi/productionAiApiCommandRuntime.ts", "utf8");
const commandRuntime = await readFile("src/server/aiApi/aiApiCommandRuntime.ts", "utf8");
const binder = await readFile("src/server/shared/identityPageCommandRuntime.ts", "utf8");
const queueAuthority = await readFile("authority/runtime/ACPOS_PRODUCTION_ASYNC_QUEUE_RUNTIME_CONTRACT_FINAL_LOCKED_V1.0.yaml", "utf8");
const providerAdapter = await readFile("src/server/aiApi/providerHttpAdapterRuntime.ts", "utf8");
const queueRuntime = await readFile("src/server/queue/providerExecutionQueueRuntime.ts", "utf8");
const controlledRuntime = await readFile("src/server/testing/controlledAiApiTestRuntime.ts", "utf8");
const iamRuntime = await readFile("src/server/iam/productionIamCommandRuntime.ts", "utf8");

const routeFiles = [
  ["src/app/v1/aiapi/provider-profiles/route.ts", "listProviderModelProfiles", "createProviderModelProfile"],
  ["src/app/v1/aiapi/provider-profiles/[profileId]/route.ts", "getProviderModelProfile", "updateProviderModelProfile"],
  ["src/app/v1/aiapi/provider-profiles/[profileId]/test/route.ts", "testProviderModelProfile"],
  ["src/app/v1/aiapi/provider-profiles/[profileId]/retire/route.ts", "retireProviderModelProfile"],
  ["src/app/v1/aiapi/provider-profiles/[profileId]/credential/route.ts", "setProviderModelCredential", "deleteProviderModelCredential"],
  ["src/app/v1/aiapi/provider-groups/route.ts", "createProviderCandidateGroup"],
  ["src/app/v1/aiapi/quarantine/route.ts", "getProviderQuarantine"],
  ["src/app/v1/aiapi/quarantine/[quarantineId]/restore/route.ts", "restoreProviderFromQuarantine"],
  ["src/app/v1/aiapi/sandbox-tests/route.ts", "runSandboxTest"],
  ["src/app/v1/aiapi/routes/route.ts", "executeProviderRoute"],
  ["src/app/v1/aiapi/routes/[routeDecisionId]/route.ts", "getProviderRouteDecision"],
  ["src/app/v1/aiapi/kill-switch/route.ts", "setKillSwitch"],
  ["src/app/v1/aiapi/queue/probe/route.ts", "runProviderQueueProbe"],
];

test("AIAPI Current registry materializes only Authority-named provider operations", () => {
  const authorityOperations = [
    "createProviderModelProfile", "updateProviderModelProfile", "getProviderModelProfile",
    "listProviderModelProfiles", "testProviderModelProfile", "retireProviderModelProfile",
    "setProviderModelCredential", "deleteProviderModelCredential", "setKillSwitch",
    "createProviderCandidateGroup", "getProviderQuarantine", "restoreProviderFromQuarantine",
    "runSandboxTest", "executeProviderRoute", "getProviderRouteDecision",
  ];
  for (const operation of authorityOperations) {
    assert.match(authority, new RegExp(`- ${operation}\\b`));
    assert.match(registry, new RegExp(`operation_id: ${operation}\\b`));
  }
  assert.match(registry, /coverage: IDENTITY_SESSION_AIAPI_PROVIDER_AND_IAM_GOVERNED_OPERATIONS/);
  assert.match(registry, /aiapi_effectful_mapping_status: MATERIALIZED_CURRENT/);
});

test("AIAPI routes bind fixed registry operations through one governed runtime", async () => {
  for (const [path, ...operations] of routeFiles) {
    const source = await readFile(path, "utf8");
    assert.match(source, /createAiApiRoute/);
    for (const operation of operations) assert.match(source, new RegExp(`["']${operation}["']`));
  }
  assert.match(commandRuntime, /AIAPI_COMMAND_RUNTIME_NOT_BOUND/);
  assert.match(binder, /configureAiApiCommandRuntime/);
  assert.match(binder, /CURRENT_PAGE_RESOURCE_KEYS\["admin:AIAPI-01"\]/);
  assert.match(binder, /executeProductionAiApiCommand/);
  assert.match(binder, /auditProductionAiApiCommand/);
});

test("AIAPI production adapter preserves provider and credential safety gates", () => {
  assert.match(providerContract, /OPENAI_COMPATIBLE_CHAT/);
  assert.match(providerContract, /GENERIC_JSON_HTTP/);
  assert.match(providerContract, /SECRET_REFERENCE_ONLY/);
  assert.match(providerContract, /prompt_template_rule: Must contain canonical instruction placeholder/);
  assert.match(runtime, /AIAPI_PROMPT_TEMPLATE_CANONICAL_TOKEN_REQUIRED/);
  assert.match(runtime, /PROVIDER_SECRET_ENV_NOT_BOUND/);
  assert.match(runtime, /PROVIDER_SECRET_REFERENCE_NOT_APPROVED/);
  assert.match(runtime, /FROM secret_references/);
  assert.match(runtime, /s\.status='APPROVED'/);
  assert.match(runtime, /SECRET_REFERENCE_NOT_APPROVED/);
  assert.match(runtime, /secret_reference_approved/);
  assert.match(runtime, /credentialStatus\(row\.secret_env_ref, row\.secret_reference_approved === true\)/);
  assert.match(runtime, /compileProviderRequest/);
  assert.match(runtime, /executeProviderHttpRequest/);
  assert.match(runtime, /enqueueProviderExecutionRequest/);
  assert.match(runtime, /drainProviderExecutionEvent/);
  assert.match(runtime, /external_request_sent:false/);
  assert.match(runtime, /production_secret_used:false/);
  assert.match(runtime, /plaintext_persisted:false/);
  assert.match(providerAdapter, /OPENAI_COMPATIBLE_CHAT/);
  assert.match(providerAdapter, /GENERIC_JSON_HTTP/);
  assert.match(providerAdapter, /PROVIDER_ENDPOINT_PRIVATE_NETWORK_FORBIDDEN/);
  assert.match(providerAdapter, /PROVIDER_REQUEST_TIMEOUT/);
  assert.match(providerAdapter, /PROVIDER_RESPONSE_TEXT_PATH_NOT_FOUND/);
  assert.match(providerAdapter, /headers\.authorization/);
  assert.match(providerAdapter, /Bearer/);
  assert.match(providerAdapter, /X_GOOG_API_KEY/);
  assert.match(providerAdapter, /x-goog-api-key/);
  assert.match(providerAdapter, /PROVIDER_AUTH_MODE_INVALID/);
  assert.match(queueRuntime, /executeQueuedProviderRequest/);
  assert.match(queueRuntime, /recordQueuedProviderFailure/);
  assert.match(providerAdapter, /p\.enabled AS profile_enabled/);
  assert.match(providerAdapter, /secret_reference_approved/);
  assert.match(providerAdapter, /PROVIDER_PROFILE_DISABLED/);
  assert.match(providerAdapter, /PROVIDER_SECRET_REFERENCE_NOT_APPROVED/);
  assert.match(providerAdapter, /PROVIDER_PREFLIGHT_NOT_READY/);
  assert.match(providerAdapter, /PROVIDER_GROUP_DISABLED/);
  assert.match(providerAdapter, /PROVIDER_MEMBER_DISABLED/);
  assert.match(providerAdapter, /PROVIDER_PROFILE_HEALTH_TEST_REQUIRED/);
  assert.match(providerAdapter, /PROVIDER_CAPABILITY_MISMATCH/);
  assert.match(providerAdapter, /PROVIDER_CAPABILITY_NOT_APPROVED_FOR_CLASSIFICATION/);
  assert.match(providerAdapter, /PROVIDER_PROFILE_VERSION_CHANGED_AFTER_COMPILE/);
  assert.match(providerAdapter, /cp\.profile_version AS compiled_profile_version/);
  assert.match(providerAdapter, /pf\.checks_json/);
  assert.match(providerAdapter, /provider_capabilities c/);
  assert.match(providerAdapter, /shouldDegradeProviderHealth/);
  assert.match(providerAdapter, /PROVIDER_REQUEST_/);
  assert.match(providerAdapter, /PROVIDER_HTTP_STATUS_/);
  assert.match(providerAdapter, /PROVIDER_RESPONSE_/);
  assert.match(providerAdapter, /PROVIDER_ENDPOINT_/);
  assert.doesNotMatch(runtime + providerAdapter, /process\.env\[[^\]]+\]\s*=(?!=)|process\.env\.[A-Z0-9_]+\s*=/);
  assert.doesNotMatch(providerAdapter, /console\.(?:log|debug|info|warn|error)\s*\(/);
});

test("AIAPI capability governance approval materializes the canonical provider capability registry", () => {
  assert.match(iamRuntime, /AIAPI_PAGE_UID="admin:AIAPI-01"/);
  assert.match(iamRuntime, /AIAPI_CAPABILITY_RESOURCE_VERSION_CONFLICT/);
  assert.match(iamRuntime, /provider_key,model_key,capability_version,accepted_classifications,input_schema,output_schema,limits,status,capability_hash/);
  assert.match(iamRuntime, /ON CONFLICT\(provider_key,model_key,capability_version\) DO UPDATE/);
  assert.match(iamRuntime, /classification_level\[\]/);
  assert.match(iamRuntime, /capability_hash=EXCLUDED\.capability_hash/);
  assert.match(iamRuntime, /sql\.transaction\(\[/);
  assert.match(iamRuntime, /AIAPI_CAPABILITY_MATERIALIZATION_FAILED/);
  assert.doesNotMatch(iamRuntime, /PROVIDER_CAPABILITY["']|resource_type\s*===\s*["']PROVIDER_CAPABILITY/);
});

test("Gate 22 has an independent real Production External Provider acceptance harness", async () => {
  const workflow = await readFile(".github/workflows/external-provider-acceptance.yml", "utf8");
  const script = await readFile("scripts/production-external-provider-e2e.mjs", "utf8");
  assert.match(workflow, /workflow_dispatch:/);
  assert.match(workflow, /push:[\s\S]*branches:[\s\S]*- new[\s\S]*paths:[\s\S]*- \.github\/external-provider-acceptance-trigger\.txt/);
  assert.doesNotMatch(workflow, /pull_request:|schedule:/);
  assert.match(workflow, /environment:\s*Production/);
  assert.match(workflow, /ACPOS_EXTERNAL_E2E_PROFILE_IDS=profile-groq-text-v1,profile-google-text-v1,profile-deepseek-text-v1,profile-openrouter-text-v1/);
  assert.match(workflow, /ACPOS_EXPECT_RELEASE_SHA=.*external-provider-acceptance-trigger\.txt/);
  assert.match(script, /REAL_PROVIDER_PROFILE_ID_NOT_CONFIGURED/);
  assert.match(script, /REAL_PROVIDER_GROUP_ID_NOT_CONFIGURED/);
  assert.match(script, /REAL_PROVIDER_CAPABILITY_NOT_CONFIGURED/);
  assert.match(script, /PROFILE_CONNECTION_TEST_MUST_BE_REAL/);
  assert.match(script, /external_request_sent === true/);
  assert.match(script, /PRODUCTION_EXTERNAL_PROVIDER_E2E_PASS/);
  assert.doesNotMatch(script, /TEST_ONLY|CONTROLLED_TEST/);
  assert.match(runtime, /external_request_sent:true/);
});

test("AIAPI queue probe is separately governed by queue runtime authority", () => {
  assert.match(queueAuthority, /operation_id: runProviderQueueProbe/);
  assert.match(queueAuthority, /path: \/v1\/aiapi\/queue\/probe/);
  assert.match(queueAuthority, /external_provider_call: FORBIDDEN/);
  assert.match(registry, /operation_id: runProviderQueueProbe/);
  assert.match(registry, /probe_cleanup_required: true/);
  assert.match(runtime, /runProviderQueueRuntimeProbe/);
});



test("provider capability governance query matches canonical schema", async () => {
  const migration = await readFile("database/migrations/0001_canonical_schema.sql", "utf8");
  assert.match(migration, /CREATE TABLE provider_capabilities/);
  const providerCapabilityTable = migration.match(/CREATE TABLE provider_capabilities \(([\s\S]*?)\n\);/)?.[1] ?? "";
  assert.match(providerCapabilityTable, /capability_version text NOT NULL/);
  assert.doesNotMatch(providerCapabilityTable, /capability_key text/);

  assert.match(runtime, /p\.capability_type/);
  assert.match(runtime, /asText\(m\.capability_type\)!==requiredCapability/);
  assert.match(runtime, /FROM provider_capabilities c/);
  assert.match(runtime, /c\.provider_key=m\.provider_id/);
  assert.match(runtime, /c\.model_key=m\.model_id/);
  assert.match(runtime, /c\.status='APPROVED'/);
  assert.match(runtime, /accepted_classifications::text\[\]/);
  assert.doesNotMatch(runtime, /c\.capability_key/);
});


test("AIAPI controlled fixture matches Current provider projection and safe read contracts", () => {
  assert.match(controlledRuntime, /profile_id:/);
  assert.match(controlledRuntime, /adapter:/);
  assert.match(controlledRuntime, /base_url:/);
  assert.match(controlledRuntime, /health_status:/);
  assert.match(controlledRuntime, /capability_status:/);
  assert.match(controlledRuntime, /capability_version:/);
  assert.match(controlledRuntime, /request\.operation_id === "getProviderModelProfile"/);
  assert.match(controlledRuntime, /request\.operation_id === "testProviderModelProfile"/);
  assert.match(controlledRuntime, /request\.operation_id === "getProviderQuarantine"/);
  assert.match(controlledRuntime, /external_request_sent: false/);
  assert.match(controlledRuntime, /TEST_ONLY_PASS/);
});


test("queued provider dispatch revalidates the full preflight authority before any external request", () => {
  const dispatchIndex = providerAdapter.indexOf("export async function executeQueuedProviderRequest");
  const httpIndex = providerAdapter.indexOf("await executeProviderHttpRequest(profile", dispatchIndex);
  for (const marker of [
    "PROVIDER_PREFLIGHT_NOT_READY",
    "PROVIDER_GROUP_DISABLED",
    "PROVIDER_MEMBER_DISABLED",
    "PROVIDER_PROFILE_DISABLED",
    "PROVIDER_PROFILE_HEALTH_TEST_REQUIRED",
    "PROVIDER_CAPABILITY_MISMATCH",
    "PROVIDER_CAPABILITY_NOT_APPROVED_FOR_CLASSIFICATION",
    "PROVIDER_SECRET_REFERENCE_NOT_APPROVED",
    "PROVIDER_PROFILE_VERSION_CHANGED_AFTER_COMPILE",
    "PROVIDER_SECRET_ENV_NOT_BOUND",
  ]) {
    const markerIndex = providerAdapter.indexOf(marker, dispatchIndex);
    assert.ok(markerIndex > dispatchIndex && markerIndex < httpIndex, `${marker} must fail closed before external HTTP dispatch`);
  }
  assert.match(providerAdapter, /m\.provider_id=p\.provider_id AND m\.model_id=p\.model_id/);
  assert.match(providerAdapter, /pf\.checks_json->>'data_classification'/);
});

test("governance-only queued failures do not falsify provider health", () => {
  assert.match(providerAdapter, /function shouldDegradeProviderHealth/);
  assert.match(providerAdapter, /if \(shouldDegradeProviderHealth\(reasonCode\)\)/);
  assert.doesNotMatch(
    providerAdapter.match(/function shouldDegradeProviderHealth[\s\S]*?\n\}/)?.[0] ?? "",
    /GROUP_DISABLED|MEMBER_DISABLED|CAPABILITY|VERSION_CHANGED|SECRET_REFERENCE/
  );
});
