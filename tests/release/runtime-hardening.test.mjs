import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("global v1 mutation guard is fail-explicit and correlated", async () => {
  const proxy = await read("src/proxy.ts");
  assert.match(proxy, /matcher:\s*\["\/v1\/:path\*"\]/);
  assert.match(proxy, /RATE_LIMITED/);
  assert.match(proxy, /status:\s*429/);
  assert.match(proxy, /retry-after/);
  assert.match(proxy, /x-correlation-id/);
  assert.match(proxy, /x-ratelimit-limit/);
  assert.match(proxy, /x-ratelimit-remaining/);
});

test("rate guard has bounded in-process storage and production defaults", async () => {
  const guard = await read("src/server/shared/requestGuard.ts");
  assert.match(guard, /DEFAULT_LIMIT\s*=\s*120/);
  assert.match(guard, /DEFAULT_WINDOW_MS\s*=\s*60_000/);
  assert.match(guard, /MAX_BUCKETS\s*=\s*10_000/);
  assert.match(guard, /ACPOS_RATE_LIMIT_MAX/);
  assert.match(guard, /ACPOS_RATE_LIMIT_WINDOW_MS/);
  assert.match(guard, /buckets\.delete/);
});

test("observability is vendor-neutral and instrumentation-bound", async () => {
  const observability = await read("src/server/shared/observability.ts");
  const instrumentation = await read("src/instrumentation.ts");
  assert.match(observability, /configureObservabilitySink/);
  assert.match(observability, /OBSERVABILITY_SINK_FAILURE/);
  assert.doesNotMatch(observability, /payload|authorization|cookie/i);
  assert.match(instrumentation, /emitObservability/);
  assert.match(instrumentation, /UNCAUGHT_SERVER_REQUEST_ERROR/);
});

test("release gate covers both construction and production branches", async () => {
  const workflow = await read(".github/workflows/release-gate.yml");
  assert.match(workflow, /pull_request:[\s\S]*branches:\s*\[new, main\]/);
  assert.match(workflow, /push:[\s\S]*branches:\s*\[new, main\]/);
});

test("Vercel build disables standalone while Docker keeps standalone output", async () => {
  const nextConfig = await read("next.config.ts");
  const dockerfile = await read("Dockerfile");
  assert.match(nextConfig, /output:\s*process\.env\.VERCEL\s*\?\s*undefined\s*:\s*"standalone"/);
  assert.match(dockerfile, /\.next\/standalone/);
});
