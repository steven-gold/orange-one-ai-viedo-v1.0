import test from "node:test";
import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";

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

test("production instrumentation does not import controlled test runtimes", async () => {
  const instrumentation = await read("src/instrumentation.ts");
  assert.doesNotMatch(instrumentation, /from\s+["']@\/server\/testing\//);
  assert.doesNotMatch(instrumentation, /import\s*\(["']@\/server\/testing\//);
});

test("controlled test mode is hard-disabled for production deployment", async () => {
  const controlledTestData = await read("src/domain/testing/controlledTestData.ts");
  assert.match(controlledTestData, /ACPOS_DEPLOYMENT_ENV/);
  assert.match(controlledTestData, /PRODUCTION_ENVIRONMENT_VALUE\s*=\s*["']production["']/);
  assert.match(controlledTestData, /trim\(\)\.toLowerCase\(\)/);
  assert.match(controlledTestData, /deploymentEnvironment\s*!==\s*PRODUCTION_ENVIRONMENT_VALUE/);
});

test("core controlled runtime is gated by the shared production-safe guard", async () => {
  const coreRuntime = await read("src/server/core/coreRuntime.ts");
  assert.match(coreRuntime, /from\s+["']@\/domain\/testing\/controlledTestData["']/);
  assert.match(coreRuntime, /isControlledTestMode\(\)\s*\?\s*getControlledCoreTestRuntimeBindings\(\)\s*:\s*null/);
  assert.doesNotMatch(coreRuntime, /NEXT_PUBLIC_ACPOS_RUNTIME_MODE\s*===\s*["']CONTROLLED_TEST["']/);
});

test("core controlled server helper cannot bypass the shared production-safe guard", async () => {
  const coreTestRuntime = await read("src/server/testing/controlledCoreTestRuntime.ts");
  assert.match(coreTestRuntime, /from\s+["']@\/domain\/testing\/controlledTestData["']/);
  assert.match(coreTestRuntime, /isControlledCoreServerTestMode\(\):\s*boolean\s*\{\s*return\s+isControlledTestMode\(\);\s*\}/s);
  assert.doesNotMatch(coreTestRuntime, /process\.env\.ACPOS_RUNTIME_MODE/);
});

test("all controlled server test helpers use the shared production-safe runtime-mode guard", async () => {
  const files = (await readdir("src/server/testing"))
    .filter((name) => /^controlled.*TestRuntime\.ts$/.test(name));
  assert.ok(files.length >= 18, `expected controlled runtime inventory, found ${files.length}`);

  for (const name of files) {
    const source = await read(`src/server/testing/${name}`);
    assert.doesNotMatch(
      source,
      /process\.env\.(?:NEXT_PUBLIC_ACPOS_RUNTIME_MODE|ACPOS_RUNTIME_MODE)/,
      `${name} must not bypass the shared runtime-mode guard`,
    );

    const helpers = [...source.matchAll(/export\s+function\s+(isControlled\w+ServerTestMode)\([^)]*\)(?::\s*boolean)?\s*\{([^}]*)\}/g)];
    for (const [, helperName, body] of helpers) {
      assert.match(source, /@\/domain\/testing\/controlledTestData/, `${name} must import the shared guard`);
      assert.match(body, /return\s+isControlledTestMode\(\)\s*;/, `${helperName} in ${name} must delegate to the shared guard`);
    }
  }
});

test("production projection HTTP boundary blocks controlled-mode misconfiguration", async () => {
  const route = await read("src/app/v1/ui-projections/[pageUid]/route.ts");
  assert.match(route, /ACPOS_DEPLOYMENT_ENV/);
  assert.match(route, /NEXT_PUBLIC_ACPOS_RUNTIME_MODE\s*===\s*["']CONTROLLED_TEST["']/);
  assert.match(route, /UI_PROJECTION_RUNTIME_NOT_BOUND/);
  assert.match(route, /status:\s*503/);
});

test("production readiness remains fail-closed for controlled mode and unbound UI runtime", async () => {
  const readiness = await read("src/app/health/ready/route.ts");
  const uiRuntime = await read("src/server/shared/uiProjectionRuntime.ts");

  assert.match(readiness, /NEXT_PUBLIC_ACPOS_RUNTIME_MODE\s*===\s*["']CONTROLLED_TEST["']/);
  assert.match(readiness, /CONTROLLED_TEST_NOT_PRODUCTION_READY/);
  assert.match(readiness, /status:\s*503/);
  assert.match(readiness, /getUiProjection/);
  assert.match(readiness, /if\s*\(!probe\.ok\)/);

  assert.match(uiRuntime, /if\s*\(!runtime\)/);
  assert.match(uiRuntime, /UI_PROJECTION_RUNTIME_NOT_BOUND/);
  assert.match(uiRuntime, /status:\s*503/);
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
