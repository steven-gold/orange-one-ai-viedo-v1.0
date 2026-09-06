import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const visual = await readFile("src/components/pages/AiApiVisual.tsx", "utf8");
const commandPort = await readFile("src/domain/aiApi/aiApiCommandPort.ts", "utf8");
const runtimePort = await readFile("src/domain/aiApi/aiApiRuntimePort.ts", "utf8");
const authority = await readFile("authority/pages/admin/AIAPI-01/ACPOS_AIAPI-01_FINAL_LOCKED_ENCODING.yaml", "utf8");

test("AIAPI UI binds current governed operations instead of hard-disabled remap placeholders", () => {
  assert.match(visual, /data-current-ui-binding-status="MATERIALIZED_CURRENT"/);
  assert.match(visual, /invokeAiApiCommand/);
  assert.match(visual, /data-operation-id/);
  assert.match(visual, /AIAPI_PROFILE_SELECTION_REQUIRED/);
  assert.doesNotMatch(visual, /REMAP_REQUIRED_NOT_EXECUTED/);
});

test("AIAPI provider table uses profile identity and optimistic version state", () => {
  assert.match(runtimePort, /profile_id: string/);
  assert.match(runtimePort, /version: number \\| null/);
  assert.match(visual, /data-profile-id=\\{row\\.profile_id\\}/);
  assert.match(visual, /selectedProfileId === row\\.profile_id/);
  assert.match(visual, /expected_version: selectedRow\\?\\.version/);
});

test("AIAPI credential surface accepts secret references only", () => {
  assert.match(visual, /secret_env_ref/);
  assert.match(visual, /noPlaintextSecret/);
  assert.doesNotMatch(visual, /type="password"/);
  assert.doesNotMatch(visual, /api_key|secret_value|plaintext_key/i);
  assert.match(commandPort, /setProviderModelCredential/);
  assert.match(commandPort, /deleteProviderModelCredential/);
});

test("AIAPI command port reuses registered Current routes", () => {
  const required = [
    "/v1/aiapi/provider-profiles",
    "/v1/aiapi/provider-groups",
    "/v1/aiapi/quarantine",
    "/v1/aiapi/sandbox-tests",
    "/v1/aiapi/routes",
    "/v1/aiapi/kill-switch",
    "/v1/aiapi/queue/probe",
    "/v1/governance/resources/",
  ];
  for (const route of required) assert.equal(commandPort.includes(route), true, `missing ${route}`);
  assert.match(authority, /single_page_workspace: true/);
  assert.match(visual, /admin:AIAPI-01/);
});
