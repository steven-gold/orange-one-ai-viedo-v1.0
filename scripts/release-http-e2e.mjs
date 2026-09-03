import { spawn, spawnSync } from "node:child_process";

const port = process.env.ACPOS_E2E_PORT ?? "3499";
const base = `http://127.0.0.1:${port}`;
const expectReady = process.env.ACPOS_EXPECT_READY === "1";
const expectControlledBlock = process.env.ACPOS_EXPECT_CONTROLLED_BLOCK === "1";
const runtimeMode = process.env.ACPOS_E2E_RUNTIME_MODE ?? "";

const routes = [
  ["/", "workspace:WB-01"], ["/core", "CORE-01"], ["/assets", "ASSET-01"], ["/video", "VIDEO-01"],
  ["/edit", "EDIT-01"], ["/qa", "QA-01"], ["/database", "admin:DB-01"], ["/strategy", "workspace:STR-01"],
  ["/info", "workspace:INFO-01"], ["/admin/system", "admin:SYS-01"], ["/admin/accounts", "admin:IAM-01"],
  ["/admin/dev", "admin:DEV-01"], ["/admin/social", "admin:SOC-01"], ["/admin/erp", "admin:ERP-01"],
  ["/admin/aiapi", "admin:AIAPI-01"], ["/admin/qa-criteria", "admin:SG-02"], ["/admin/strategy", "admin:STR-01"],
  ["/admin/knowledge", "admin:KB-01"],
];

function run(command, args, env = process.env) {
  const result = spawnSync(command, args, { stdio: "inherit", env });
  if (result.status !== 0) process.exit(result.status ?? 1);
}

if (process.env.ACPOS_E2E_SKIP_BUILD !== "1") {
  run("npm", ["run", "build"], { ...process.env, NEXT_PUBLIC_ACPOS_RUNTIME_MODE: runtimeMode });
}

const server = spawn(process.execPath, ["node_modules/next/dist/bin/next", "start", "-p", port], {
  stdio: ["ignore", "inherit", "inherit"],
  env: {
    ...process.env,
    NODE_ENV: "production",
    NEXT_PUBLIC_ACPOS_RUNTIME_MODE: runtimeMode,
    ACPOS_RATE_LIMIT_MAX: "3",
    ACPOS_RATE_LIMIT_WINDOW_MS: "60000",
  },
});

async function waitForServer() {
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${base}/health`, { cache: "no-store" });
      if (response.ok) return;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error("SERVER_START_TIMEOUT");
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

try {
  await waitForServer();

  const health = await fetch(`${base}/health`, { cache: "no-store" });
  assert(health.status === 200, `HEALTH_HTTP_${health.status}`);
  const security = {
    csp: health.headers.get("content-security-policy"),
    hsts: health.headers.get("strict-transport-security"),
    nosniff: health.headers.get("x-content-type-options"),
    referrer: health.headers.get("referrer-policy"),
    permissions: health.headers.get("permissions-policy"),
    frame: health.headers.get("x-frame-options"),
  };
  for (const [name, value] of Object.entries(security)) assert(Boolean(value), `SECURITY_HEADER_MISSING_${name}`);

  const ready = await fetch(`${base}/health/ready`, { cache: "no-store" });
  const readyText = await ready.text();
  if (expectControlledBlock) {
    assert(ready.status === 503, `CONTROLLED_PRODUCTION_READINESS_HTTP_${ready.status}`);
    assert(/CONTROLLED_TEST_NOT_PRODUCTION_READY/.test(readyText), "CONTROLLED_PRODUCTION_READINESS_REASON_MISSING");
  } else if (expectReady) {
    assert(ready.status === 200, `PRODUCTION_NOT_READY_HTTP_${ready.status}`);
  } else {
    assert([200, 503].includes(ready.status), `READINESS_HTTP_${ready.status}`);
  }

  for (const [route, uid] of routes) {
    const page = await fetch(`${base}${route}`, { cache: "no-store" });
    assert(page.status === 200, `PAGE_${route}_HTTP_${page.status}`);
    const projection = await fetch(`${base}/v1/ui-projections/${encodeURIComponent(uid)}`, { cache: "no-store" });
    const text = await projection.text();
    assert(!/TEST_ONLY|TEST-RUN-|"synthetic"\s*:\s*true/.test(text), `PRODUCTION_TEST_DATA_LEAK_${uid}`);
    if (expectControlledBlock) {
      assert(projection.status === 503, `CONTROLLED_PRODUCTION_PROJECTION_${uid}_HTTP_${projection.status}`);
      assert(/UI_PROJECTION_RUNTIME_NOT_BOUND/.test(text), `CONTROLLED_PRODUCTION_PROJECTION_REASON_${uid}`);
    } else {
      assert([200, 503].includes(projection.status), `PROJECTION_${uid}_HTTP_${projection.status}`);
      if (projection.status === 503) assert(/RUNTIME_NOT_BOUND|NOT_BOUND|NOT_CONFIGURED/.test(text), `UNTRUTHFUL_503_${uid}`);
    }
  }

  let limitedResponse = null;
  for (let attempt = 1; attempt <= 4; attempt += 1) {
    const response = await fetch(`${base}/v1/conversations/release-rate-limit/messages`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: "{}",
    });
    if (attempt <= 3) assert(response.status !== 429, `RATE_LIMIT_EARLY_HTTP_${response.status}_ATTEMPT_${attempt}`);
    else limitedResponse = response;
  }
  assert(limitedResponse?.status === 429, `RATE_LIMIT_HTTP_${limitedResponse?.status ?? "missing"}`);
  const limitedBody = await limitedResponse.json();
  assert(limitedBody.reason_code === "RATE_LIMITED", "RATE_LIMIT_REASON_CODE_MISSING");
  assert(Boolean(limitedBody.correlation_id), "RATE_LIMIT_CORRELATION_ID_MISSING");
  assert(Boolean(limitedResponse.headers.get("retry-after")), "RATE_LIMIT_RETRY_AFTER_MISSING");
  assert(limitedResponse.headers.get("x-ratelimit-limit") === "3", "RATE_LIMIT_LIMIT_HEADER_INVALID");
  assert(limitedResponse.headers.get("x-ratelimit-remaining") === "0", "RATE_LIMIT_REMAINING_HEADER_INVALID");

  const missing = await fetch(`${base}/this-route-must-not-exist`, { redirect: "manual" });
  assert(missing.status === 404, `NOT_FOUND_HTTP_${missing.status}`);
  process.stdout.write(`RELEASE_HTTP_E2E_PASS ready=${ready.status} rate_limit=429 controlled_block=${expectControlledBlock ? "1" : "0"}\n`);
} finally {
  server.kill("SIGTERM");
}
