const base = (process.env.ACPOS_DEPLOYMENT_URL ?? "https://orange-one-acpos-test.vercel.app").replace(/\/$/, "");
const expectReady = process.env.ACPOS_EXPECT_READY === "1";

const routes = [
  ["/", "workspace:WB-01"], ["/core", "CORE-01"], ["/assets", "ASSET-01"], ["/video", "VIDEO-01"],
  ["/edit", "EDIT-01"], ["/qa", "QA-01"], ["/database", "admin:DB-01"], ["/strategy", "workspace:STR-01"],
  ["/info", "workspace:INFO-01"], ["/admin/system", "admin:SYS-01"], ["/admin/accounts", "admin:IAM-01"],
  ["/admin/dev", "admin:DEV-01"], ["/admin/social", "admin:SOC-01"], ["/admin/erp", "admin:ERP-01"],
  ["/admin/aiapi", "admin:AIAPI-01"], ["/admin/qa-criteria", "admin:SG-02"], ["/admin/strategy", "admin:STR-01"],
  ["/admin/knowledge", "admin:KB-01"],
];

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function fetchWithRetry(path, init = {}) {
  const deadline = Date.now() + 120_000;
  let lastError;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${base}${path}`, { ...init, cache: "no-store" });
      if (response.status !== 502 && response.status !== 503 && response.status !== 504) return response;
      if (path === "/health/ready" || path.startsWith("/v1/ui-projections/")) return response;
      lastError = new Error(`HTTP_${response.status}`);
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 3000));
  }
  throw lastError ?? new Error(`REMOTE_FETCH_TIMEOUT_${path}`);
}

const health = await fetchWithRetry("/health");
assert(health.status === 200, `HEALTH_HTTP_${health.status}`);
const healthBody = await health.json();
assert(healthBody?.status === "ok", "HEALTH_STATUS_NOT_OK");
assert(healthBody?.service === "ORANGE ONE ACPOS", "HEALTH_SERVICE_INVALID");
assert(typeof healthBody?.environment === "string" && healthBody.environment !== "unspecified", "HEALTH_ENVIRONMENT_UNRESOLVED");
assert(typeof healthBody?.release_sha === "string" && /^[0-9a-f]{40}$/i.test(healthBody.release_sha), "HEALTH_RELEASE_SHA_UNRESOLVED");

for (const header of ["content-security-policy", "strict-transport-security", "x-content-type-options", "referrer-policy", "permissions-policy", "x-frame-options"]) {
  assert(Boolean(health.headers.get(header)), `SECURITY_HEADER_MISSING_${header}`);
}

const ready = await fetchWithRetry("/health/ready");
const readyText = await ready.text();
if (expectReady) assert(ready.status === 200, `PRODUCTION_NOT_READY_HTTP_${ready.status}_${readyText}`);
else assert([200, 503].includes(ready.status), `READINESS_HTTP_${ready.status}`);
if (ready.status === 503) assert(/NOT_BOUND|NOT_CONFIGURED|NOT_READY/.test(readyText), `UNTRUTHFUL_READINESS_503_${readyText}`);

for (const [route, uid] of routes) {
  const page = await fetchWithRetry(route);
  assert(page.status === 200, `PAGE_${route}_HTTP_${page.status}`);

  const projection = await fetchWithRetry(`/v1/ui-projections/${encodeURIComponent(uid)}`);
  const projectionText = await projection.text();
  assert(!/TEST_ONLY|TEST-RUN-|"synthetic"\s*:\s*true/.test(projectionText), `PRODUCTION_TEST_DATA_LEAK_${uid}`);
  assert([200, 503].includes(projection.status), `PROJECTION_${uid}_HTTP_${projection.status}`);
  if (projection.status === 503) {
    assert(/RUNTIME_NOT_BOUND|NOT_BOUND|NOT_CONFIGURED/.test(projectionText), `UNTRUTHFUL_503_${uid}_${projectionText}`);
    assert(Boolean(projection.headers.get("x-correlation-id")), `PROJECTION_CORRELATION_ID_MISSING_${uid}`);
  }
}

process.stdout.write(`POST_DEPLOY_SMOKE_PASS base=${base} ready=${ready.status} environment=${healthBody.environment} release_sha=${healthBody.release_sha} projections=${routes.length}\n`);
