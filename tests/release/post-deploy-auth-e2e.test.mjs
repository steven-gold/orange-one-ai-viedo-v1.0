import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("production authenticated post-deploy E2E is secret-gated and exercises login/session/read/logout", async () => {
  const script = await read("scripts/post-deploy-auth-e2e.mjs");
  const workflow = await read(".github/workflows/post-deploy-smoke.yml");

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
  assert.match(script, /AUTH_LOGOUT_SESSION_STILL_ACTIVE/);
  assert.match(script, /POST_DEPLOY_AUTH_E2E_PASS/);
  assert.doesNotMatch(script, /console\.(?:log|debug)\s*\(/);

  assert.match(workflow, /secrets\.ACPOS_PRODUCTION_E2E_EMAIL/);
  assert.match(workflow, /secrets\.ACPOS_PRODUCTION_E2E_PASSWORD/);
  assert.match(workflow, /node --check scripts\/post-deploy-auth-e2e\.mjs/);
  assert.match(workflow, /Run deployed ACPOS authenticated E2E/);
  assert.match(workflow, /env\.ACPOS_PRODUCTION_E2E_EMAIL != ''/);
  assert.match(workflow, /env\.ACPOS_PRODUCTION_E2E_PASSWORD != ''/);
  assert.match(workflow, /POST_DEPLOY_AUTH_E2E_BLOCKED reason=PRODUCTION_LOGIN_CREDENTIAL_NOT_CONFIGURED/);
});
