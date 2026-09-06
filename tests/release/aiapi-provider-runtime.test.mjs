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
  assert.match(providerAdapter, /authorization:/);
  assert.match(providerAdapter, /Bearer/);
  assert.match(queueRuntime, /executeQueuedProviderRequest/);
  assert.match(queueRuntime, /recordQueuedProviderFailure/);
  assert.doesNotMatch(runtime + providerAdapter, /process\.env\[[^\]]+\]\s*=(?!=)|process\.env\.[A-Z0-9_]+\s*=/);
  assert.doesNotMatch(providerAdapter, /console\.(?:log|debug|info|warn|error)\s*\(/);
});

test("AIAPI queue probe is separately governed by queue runtime authority", () => {
  assert.match(queueAuthority, /operation_id: runProviderQueueProbe/);
  assert.match(queueAuthority, /path: \/v1\/aiapi\/queue\/probe/);
  assert.match(queueAuthority, /external_provider_call: FORBIDDEN/);
  assert.match(registry, /operation_id: runProviderQueueProbe/);
  assert.match(registry, /probe_cleanup_required: true/);
  assert.match(runtime, /runProviderQueueRuntimeProbe/);
});

