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
async function parseJson(response, stage) {
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
async function post(path, cookie, payload, stage) {
  const response = await fetch(`${base}${path}`, {
    method: "POST",
    cache: "no-store",
    headers: {
      ...cookieHeaders(cookie),
      "content-type": "application/json",
      "x-correlation-id": crypto.randomUUID(),
    },
    body: JSON.stringify(payload),
  });
  const body = await parseJson(response, stage);
  assert(response.status === 200 && body?.ok === true, `${stage}_HTTP_${response.status}_${body?.reason_code ?? "UNKNOWN"}`);
  return body.value ?? {};
}

assert(email && password, "PRODUCTION_LOGIN_CREDENTIAL_NOT_CONFIGURED");

let cookie = "";
try {
  const health = await fetch(`${base}/health`, { cache: "no-store", headers: protectionHeaders() });
  const healthBody = await parseJson(health, "HEALTH");
  assert(health.status === 200, `HEALTH_HTTP_${health.status}_${healthBody?.reason_code ?? "UNKNOWN"}`);
  assert(healthBody?.environment === "production", "HEALTH_ENVIRONMENT_NOT_PRODUCTION");
  if (expectedReleaseSha) {
    assert(healthBody?.release_sha === expectedReleaseSha, `HEALTH_RELEASE_SHA_MISMATCH_${healthBody?.release_sha ?? "UNRESOLVED"}`);
  }

  const readiness = await fetch(`${base}/health/ready`, { cache: "no-store", headers: protectionHeaders() });
  const readinessText = await readiness.text();
  let readinessBody = null;
  try { readinessBody = JSON.parse(readinessText); } catch { /* preserve raw text below */ }
  assert(
    readiness.status === 200,
    `READINESS_HTTP_${readiness.status}_${readinessBody?.reason_code ?? readinessBody?.reason ?? readinessText.slice(0, 200) || "UNKNOWN"}`,
  );

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
  const loginBody = await parseJson(login, "LOGIN");
  assert(
    login.status === 200 && loginBody?.ok === true && loginBody?.logged_in === true,
    `LOGIN_HTTP_${login.status}_${loginBody?.reason_code ?? loginBody?.reason ?? "UNKNOWN"}`,
  );
  cookie = (login.headers.get("set-cookie") ?? "").split(";")[0].trim();
  assert(cookie.startsWith("acpos_session="), "LOGIN_SESSION_COOKIE_MISSING");

  const acceptanceRef = `DEV01-PRODUCTION-ACCEPTANCE-${Date.now()}`;
  const started = await post("/v1/outreach/discovery-jobs", cookie, {
    job_name: "ACPOS Gate 24 DEV Production Acceptance",
    mode: "SINGLE_RUN",
    search_scope: { acceptance_scope: "GATE_24_DEV" },
    allowed_sources: [],
    interval_seconds: 3600,
    result_limit: 1,
    acceptance_ref: acceptanceRef,
  }, "START");
  assert(typeof started.discovery_job_id === "string" && started.discovery_job_id.length > 0, "START_JOB_ID_MISSING");
  assert(started.status === "RUNNING", `START_STATUS_${started.status ?? "UNRESOLVED"}`);
  assert(started.external_request_sent === false, "START_EXTERNAL_REQUEST_FORBIDDEN");
  assert(started.deployment_triggered === false, "START_DEPLOYMENT_TRIGGER_FORBIDDEN");

  const id = encodeURIComponent(started.discovery_job_id);
  const paused = await post(`/v1/outreach/discovery-jobs/${id}/pause`, cookie, {}, "PAUSE");
  assert(paused.status === "PAUSED", `PAUSE_STATUS_${paused.status ?? "UNRESOLVED"}`);
  assert(paused.external_request_sent === false && paused.deployment_triggered === false, "PAUSE_EXTERNAL_EFFECT_FORBIDDEN");

  const resumed = await post(`/v1/outreach/discovery-jobs/${id}/resume`, cookie, {}, "RESUME");
  assert(resumed.status === "RUNNING", `RESUME_STATUS_${resumed.status ?? "UNRESOLVED"}`);
  assert(resumed.external_request_sent === false && resumed.deployment_triggered === false, "RESUME_EXTERNAL_EFFECT_FORBIDDEN");

  const stopped = await post(`/v1/outreach/discovery-jobs/${id}/stop`, cookie, {}, "STOP");
  assert(stopped.status === "STOPPED", `STOP_STATUS_${stopped.status ?? "UNRESOLVED"}`);
  assert(stopped.external_request_sent === false && stopped.deployment_triggered === false, "STOP_EXTERNAL_EFFECT_FORBIDDEN");

  process.stdout.write(
    `PRODUCTION_DEV_LIFECYCLE_E2E_PASS release_sha=${healthBody.release_sha} discovery_job_id=${started.discovery_job_id} start=RUNNING pause=PAUSED resume=RUNNING stop=STOPPED external_request_sent=false deployment_triggered=false\n`,
  );
} finally {
  await logout(cookie);
}
