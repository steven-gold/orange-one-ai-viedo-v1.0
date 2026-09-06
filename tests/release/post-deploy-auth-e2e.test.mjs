import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("production authenticated post-deploy E2E is secret-gated and exercises login/session/read/queue/logout", async () => {
  const script = await read("scripts/post-deploy-auth-e2e.mjs");
  const workflow = await read(".github/workflows/post-deploy-smoke.yml");
  const releaseGate = await read(".github/workflows/release-gate.yml");

  assert.match(script, /ACPOS_PRODUCTION_E2E_EMAIL/);
  assert.match(script, /ACPOS_PRODUCTION_E2E_PASSWORD/);
  assert.match(script, /PRODUCTION_LOGIN_CREDENTIAL_NOT_CONFIGURED/);
  assert.match(script, /\/v1\/identity\/session/);
  assert.match(script, /method: "POST"/);
  assert.match(script, /method: "GET"/);
  assert.match(script, /method: "DELETE"/);
  assert.match(script, /acpos_session=/);
  assert.match(script, /AUTH_SESSION_COOKIE_HTTPONLY_MISSING/);
  assert.match(script, /AUTH_SESSION_COOKIE_SECURE_MISSING/);
  assert.match(script, /AUTH_SESSION_COOKIE_SAMESITE_INVALID/);
  assert.match(script, /\/v1\/dashboard\/read-model/);
  assert.match(script, /projectionUids/);
  assert.match(script, /workspace:WB-01/);
  assert.match(script, /admin:KB-01/);
  assert.match(script, /projectionPass \+= 1/);
  assert.match(script, /\/v1\/aiapi\/queue\/probe/);
  assert.match(script, /AUTH_QUEUE_PROBE_HTTP_/);
  assert.match(script, /AUTH_QUEUE_PROBE_RESIDUAL_ROWS/);
  assert.match(script, /queue_probe=1/);
  assert.match(script, /AUTH_LOGOUT_SESSION_STILL_ACTIVE/);
  assert.match(script, /POST_DEPLOY_AUTH_E2E_PASS/);
  assert.doesNotMatch(script, /console\.(?:log|debug)\s*\(/);
  assert.doesNotMatch(script, /AUTH_LOGIN_HTTP_\$\{login\.status\}_\$\{loginText\}/);
  assert.doesNotMatch(script, /AUTH_DASHBOARD_READ_MODEL_HTTP_\$\{dashboard\.status\}_\$\{dashboardText\}/);
  assert.doesNotMatch(script, /AUTH_PROJECTION_\$\{uid\}_HTTP_\$\{response\.status\}_\$\{text\}/);

  assert.match(workflow, /environment: Production/);
  assert.match(workflow, /ACPOS_PRODUCTION_E2E_EMAIL: admin/);
  assert.match(workflow, /ACPOS_PRODUCTION_E2E_PASSWORD: \${{ secrets\.ADMIN }}/);
  assert.match(workflow, /node --check scripts\/post-deploy-auth-e2e\.mjs/);
  assert.match(workflow, /Run deployed ACPOS authenticated E2E/);
  assert.match(workflow, /env\.ACPOS_PRODUCTION_E2E_EMAIL != ''/);
  assert.match(workflow, /env\.ACPOS_PRODUCTION_E2E_PASSWORD != ''/);
  assert.match(workflow, /POST_DEPLOY_AUTH_E2E_BLOCKED reason=PRODUCTION_LOGIN_CREDENTIAL_NOT_CONFIGURED/);
  assert.match(workflow, /id: auth_http/);
  assert.match(workflow, /id: auth_browser/);
  assert.match(workflow, /continue-on-error: true/);
  assert.match(workflow, /Enforce authenticated acceptance/);
  assert.match(workflow, /AUTH_HTTP_OUTCOME/);
  assert.match(workflow, /AUTH_BROWSER_OUTCOME/);
  assert.match(workflow, /if: \${{ always\(\) }}/);

  assert.match(releaseGate, /Validate deployment smoke syntax/);
  assert.match(releaseGate, /node --check scripts\/post-deploy-smoke\.mjs/);
  assert.match(releaseGate, /node --check scripts\/post-deploy-browser-smoke\.mjs/);
  assert.match(releaseGate, /node --check scripts\/post-deploy-auth-e2e\.mjs/);
});
