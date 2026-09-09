const base = (process.env.ACPOS_DEPLOYMENT_URL ?? "https://orange-one-acpos-test.vercel.app").replace(/\/$/, "");
const email = (process.env.ACPOS_PRODUCTION_E2E_EMAIL ?? "").trim();
const password = process.env.ACPOS_PRODUCTION_E2E_PASSWORD ?? "";
const expectedReleaseSha = (process.env.ACPOS_EXPECT_RELEASE_SHA ?? "").trim();

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
function protectionHeaders() {
  const secret = process.env.VERCEL_AUTOMATION_BYPASS_SECRET;
  return secret ? { "x-vercel-protection-bypass": secret } : {};
}
function cookieHeaders(cookie) {
  return { ...protectionHeaders(), cookie };
}
async function json(response, stage) {
  const text = await response.text();
  try { return JSON.parse(text); } catch { throw new Error(`${stage}_RESPONSE_NOT_JSON`); }
}
async function logout(cookie) {
  if (!cookie) return;
  await fetch(`${base}/v1/identity/session`, {
    method: "DELETE",
    cache: "no-store",
    headers: cookieHeaders(cookie),
  }).catch(() => undefined);
}

assert(email && password, "PRODUCTION_LOGIN_CREDENTIAL_NOT_CONFIGURED");

let cookie = "";
try {
  const health = await fetch(`${base}/health`, { cache: "no-store", headers: protectionHeaders() });
  const healthBody = await json(health, "HEALTH");
  assert(health.status === 200, `HEALTH_HTTP_${health.status}`);
  assert(healthBody?.environment === "production", "HEALTH_ENVIRONMENT_NOT_PRODUCTION");
  if (expectedReleaseSha) {
    assert(
      healthBody?.release_sha === expectedReleaseSha,
      `HEALTH_RELEASE_SHA_MISMATCH_${healthBody?.release_sha ?? "UNRESOLVED"}`,
    );
  }

  const login = await fetch(`${base}/v1/identity/session`, {
    method: "POST",
    cache: "no-store",
    redirect: "manual",
    headers: {
      ...protectionHeaders(),
      "content-type": "application/json",
      "x-correlation-id": crypto.randomUUID(),
    },
    body: JSON.stringify({ email, password }),
  });
  const loginBody = await json(login, "LOGIN");
  assert(login.status === 200, `LOGIN_HTTP_${login.status}`);
  assert(loginBody?.ok === true && loginBody?.logged_in === true, "LOGIN_BODY_INVALID");
  cookie = (login.headers.get("set-cookie") ?? "").split(";")[0].trim();
  assert(cookie.startsWith("acpos_session="), "LOGIN_SESSION_COOKIE_MISSING");

  const acceptanceRef = `SYS01-PRODUCTION-ACCEPTANCE-${Date.now()}`;
  const candidate = await fetch(`${base}/v1/system/changes/candidates`, {
    method: "POST",
    cache: "no-store",
    headers: {
      ...cookieHeaders(cookie),
      "content-type": "application/json",
      "x-correlation-id": crypto.randomUUID(),
    },
    body: JSON.stringify({
      current_goal: "Validate the governed ACPOS SYS-01 Production lifecycle without triggering a Production deployment.",
      scope: {
        acceptance_scope: "GATE_24_SYS01",
        acceptance_ref: acceptanceRef,
        expected_release_sha: expectedReleaseSha || healthBody.release_sha,
      },
      candidate_document: {
        title: "SYS-01 Production Lifecycle Acceptance",
        requirement: "Candidate, change request, and sandbox test must be governed, auditable, and non-deploying.",
      },
    }),
  });
  const candidateBody = await json(candidate, "CANDIDATE");
  assert(candidate.status === 200 && candidateBody?.ok === true, `CANDIDATE_HTTP_${candidate.status}_${candidateBody?.reason_code ?? "UNKNOWN"}`);
  const candidateValue = candidateBody?.value ?? {};
  assert(typeof candidateValue.system_change_id === "string" && candidateValue.system_change_id.length > 0, "SYSTEM_CHANGE_ID_MISSING");
  assert(typeof candidateValue.candidate_ref === "string" && candidateValue.candidate_ref.length > 0, "CANDIDATE_REF_MISSING");
  assert(candidateValue.status === "DRAFT", `CANDIDATE_STATUS_${candidateValue.status ?? "UNRESOLVED"}`);
  assert(candidateValue.production_mutation === false, "CANDIDATE_PRODUCTION_MUTATION_FORBIDDEN");
  assert(candidateValue.deployment_triggered === false, "CANDIDATE_DEPLOYMENT_TRIGGER_FORBIDDEN");

  const systemChangeId = candidateValue.system_change_id;
  const candidateRef = candidateValue.candidate_ref;
  const request = await fetch(
    `${base}/v1/system/changes/${encodeURIComponent(systemChangeId)}/requests`,
    {
      method: "POST",
      cache: "no-store",
      headers: {
        ...cookieHeaders(cookie),
        "content-type": "application/json",
        "x-correlation-id": crypto.randomUUID(),
      },
      body: JSON.stringify({
        candidate_ref: candidateRef,
        reason: "Production acceptance evidence for the user-approved SYS-01 lifecycle runtime.",
        impact_scope: {
          acceptance_scope: "GATE_24_SYS01",
          acceptance_ref: acceptanceRef,
          production_deploy_allowed: false,
        },
      }),
    },
  );
  const requestBody = await json(request, "CHANGE_REQUEST");
  assert(request.status === 200 && requestBody?.ok === true, `CHANGE_REQUEST_HTTP_${request.status}_${requestBody?.reason_code ?? "UNKNOWN"}`);
  const requestValue = requestBody?.value ?? {};
  assert(requestValue.system_change_id === systemChangeId, "CHANGE_REQUEST_SYSTEM_CHANGE_MISMATCH");
  assert(requestValue.candidate_ref === candidateRef, "CHANGE_REQUEST_CANDIDATE_MISMATCH");
  assert(typeof requestValue.change_request_ref === "string" && requestValue.change_request_ref.length > 0, "CHANGE_REQUEST_REF_MISSING");
  assert(requestValue.status === "SUBMITTED", `CHANGE_REQUEST_STATUS_${requestValue.status ?? "UNRESOLVED"}`);
  assert(requestValue.production_mutation === false, "CHANGE_REQUEST_PRODUCTION_MUTATION_FORBIDDEN");
  assert(requestValue.deployment_triggered === false, "CHANGE_REQUEST_DEPLOYMENT_TRIGGER_FORBIDDEN");

  const sandbox = await fetch(
    `${base}/v1/system/changes/${encodeURIComponent(systemChangeId)}/sandbox-tests`,
    {
      method: "POST",
      cache: "no-store",
      headers: {
        ...cookieHeaders(cookie),
        "content-type": "application/json",
        "x-correlation-id": crypto.randomUUID(),
      },
      body: JSON.stringify({
        canonical_instruction: "ACPOS SYS-01 Production acceptance sandbox compile. Preserve canonical meaning and do not send an external Provider request.",
      }),
    },
  );
  const sandboxBody = await json(sandbox, "SANDBOX");
  assert(sandbox.status === 200 && sandboxBody?.ok === true, `SANDBOX_HTTP_${sandbox.status}_${sandboxBody?.reason_code ?? "UNKNOWN"}`);
  const sandboxValue = sandboxBody?.value ?? {};
  assert(sandboxValue.system_change_id === systemChangeId, "SANDBOX_SYSTEM_CHANGE_MISMATCH");
  assert(sandboxValue.candidate_ref === candidateRef, "SANDBOX_CANDIDATE_MISMATCH");
  assert(typeof sandboxValue.provider_profile_id === "string" && sandboxValue.provider_profile_id.length > 0, "SANDBOX_PROVIDER_PROFILE_MISSING");
  assert(sandboxValue.production_mutation === false, "SANDBOX_PRODUCTION_MUTATION_FORBIDDEN");
  assert(sandboxValue.deployment_triggered === false, "SANDBOX_DEPLOYMENT_TRIGGER_FORBIDDEN");
  assert(sandboxValue.sandbox?.status === "PASS", `SANDBOX_STATUS_${sandboxValue.sandbox?.status ?? "UNRESOLVED"}`);
  assert(sandboxValue.sandbox?.dry_run === true, "SANDBOX_MUST_BE_DRY_RUN");
  assert(sandboxValue.sandbox?.external_request_sent === false, "SANDBOX_EXTERNAL_REQUEST_FORBIDDEN");
  assert(typeof sandboxValue.sandbox?.test_id === "string" && sandboxValue.sandbox.test_id.length > 0, "SANDBOX_TEST_ID_MISSING");

  process.stdout.write(
    `PRODUCTION_SYS_LIFECYCLE_E2E_PASS release_sha=${healthBody.release_sha} system_change_id=${systemChangeId} candidate_ref=${candidateRef} change_request_ref=${requestValue.change_request_ref} sandbox_test_id=${sandboxValue.sandbox.test_id} provider_profile_id=${sandboxValue.provider_profile_id} dry_run=true external_request_sent=false production_mutation=false deployment_triggered=false\n`,
  );
} finally {
  await logout(cookie);
}
