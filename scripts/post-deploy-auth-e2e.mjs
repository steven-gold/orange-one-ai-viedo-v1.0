const base = (process.env.ACPOS_DEPLOYMENT_URL ?? "https://orange-one-acpos-test.vercel.app").replace(/\/$/, "");
const email = (process.env.ACPOS_PRODUCTION_E2E_EMAIL ?? "").trim();
const password = process.env.ACPOS_PRODUCTION_E2E_PASSWORD ?? "";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function protectionHeaders() {
  const secret = process.env.VERCEL_AUTOMATION_BYPASS_SECRET;
  if (!secret) return {};
  return { "x-vercel-protection-bypass": secret };
}

function cookieHeaders(cookie) {
  return { ...protectionHeaders(), cookie };
}

const projectionUids = [
  "workspace:WB-01",
  "CORE-01",
  "ASSET-01",
  "VIDEO-01",
  "EDIT-01",
  "QA-01",
  "admin:DB-01",
  "workspace:STR-01",
  "workspace:INFO-01",
  "admin:SYS-01",
  "admin:IAM-01",
  "admin:DEV-01",
  "admin:SOC-01",
  "admin:ERP-01",
  "admin:AIAPI-01",
  "admin:SG-02",
  "admin:STR-01",
  "admin:KB-01",
];

if (!email || !password) {
  process.stdout.write("POST_DEPLOY_AUTH_E2E_BLOCKED reason=PRODUCTION_LOGIN_CREDENTIAL_NOT_CONFIGURED\n");
  process.exit(0);
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

const loginText = await login.text();
assert(login.status === 200, `AUTH_LOGIN_HTTP_${login.status}`);
let loginBody;
try {
  loginBody = JSON.parse(loginText);
} catch {
  throw new Error("AUTH_LOGIN_RESPONSE_NOT_JSON");
}
assert(loginBody?.ok === true && loginBody?.logged_in === true, "AUTH_LOGIN_BODY_INVALID");
assert(typeof loginBody?.email === "string" && loginBody.email.toLowerCase() === email.toLowerCase(), "AUTH_LOGIN_ACTOR_MISMATCH");
assert(Boolean(login.headers.get("x-correlation-id")), "AUTH_LOGIN_CORRELATION_ID_MISSING");

const setCookie = login.headers.get("set-cookie") ?? "";
assert(/(?:^|[,; ]+)acpos_session=/.test(setCookie), "AUTH_SESSION_COOKIE_MISSING");
assert(/HttpOnly/i.test(setCookie), "AUTH_SESSION_COOKIE_HTTPONLY_MISSING");
assert(/Secure/i.test(setCookie), "AUTH_SESSION_COOKIE_SECURE_MISSING");
assert(/SameSite=Lax/i.test(setCookie), "AUTH_SESSION_COOKIE_SAMESITE_INVALID");
const cookie = setCookie.split(";")[0].trim();
assert(cookie.startsWith("acpos_session="), "AUTH_SESSION_COOKIE_NAME_INVALID");

const session = await fetch(`${base}/v1/identity/session`, {
  method: "GET",
  cache: "no-store",
  headers: cookieHeaders(cookie),
});
const sessionBody = await session.json().catch(() => null);
assert(session.status === 200, `AUTH_SESSION_HTTP_${session.status}`);
assert(sessionBody?.ok === true && sessionBody?.logged_in === true, "AUTH_SESSION_BODY_INVALID");
assert(typeof sessionBody?.email === "string" && sessionBody.email.toLowerCase() === email.toLowerCase(), "AUTH_SESSION_ACTOR_MISMATCH");
assert(Boolean(session.headers.get("x-correlation-id")), "AUTH_SESSION_CORRELATION_ID_MISSING");

const dashboard = await fetch(`${base}/v1/dashboard/read-model`, {
  method: "GET",
  cache: "no-store",
  headers: cookieHeaders(cookie),
});
const dashboardText = await dashboard.text();
assert(dashboard.status === 200, `AUTH_DASHBOARD_READ_MODEL_HTTP_${dashboard.status}`);
assert(!/TEST_ONLY|TEST-RUN-|"synthetic"\s*:\s*true/.test(dashboardText), "AUTH_DASHBOARD_TEST_DATA_LEAK");

let projectionPass = 0;
for (const uid of projectionUids) {
  const response = await fetch(`${base}/v1/ui-projections/${encodeURIComponent(uid)}`, {
    method: "GET",
    cache: "no-store",
    headers: cookieHeaders(cookie),
  });
  const text = await response.text();
  assert(response.status === 200, `AUTH_PROJECTION_${uid}_HTTP_${response.status}`);
  assert(!/TEST_ONLY|TEST-RUN-|"synthetic"\s*:\s*true/.test(text), `AUTH_PROJECTION_TEST_DATA_LEAK_${uid}`);
  assert(Boolean(response.headers.get("x-correlation-id")), `AUTH_PROJECTION_CORRELATION_ID_MISSING_${uid}`);
  projectionPass += 1;
}

const logout = await fetch(`${base}/v1/identity/session`, {
  method: "DELETE",
  cache: "no-store",
  headers: cookieHeaders(cookie),
});
const logoutBody = await logout.json().catch(() => null);
assert(logout.status === 200, `AUTH_LOGOUT_HTTP_${logout.status}`);
assert(logoutBody?.ok === true && logoutBody?.logged_in === false, "AUTH_LOGOUT_BODY_INVALID");

const afterLogout = await fetch(`${base}/v1/identity/session`, {
  method: "GET",
  cache: "no-store",
  headers: cookieHeaders(cookie),
});
const afterLogoutBody = await afterLogout.json().catch(() => null);
assert(afterLogout.status === 401, `AUTH_LOGOUT_SESSION_STILL_ACTIVE_HTTP_${afterLogout.status}`);
assert(afterLogoutBody?.logged_in === false, "AUTH_LOGOUT_SESSION_BODY_INVALID");

process.stdout.write(`POST_DEPLOY_AUTH_E2E_PASS projections=${projectionPass} dashboard=1 login=1 session=1 logout=1\n`);
