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

test("register() injects the authority Neon driver and WB-01 projection binding", async () => {
  const instrumentation = await read("src/instrumentation.ts");
  const neonRuntime = await read("src/server/database/neonRuntime.ts");
  const packageJson = await read("package.json");
  const ready = await read("src/app/health/ready/route.ts");
  const uiProjection = await read("src/server/shared/uiProjectionRuntime.ts");
  const wb01 = await read("src/server/dashboard/wb01ProjectionRuntime.ts");
  assert.match(packageJson, /"@neondatabase\/serverless"/);
  assert.match(instrumentation, /bindProductionNeonRuntime/);
  assert.match(instrumentation, /bindWb01ProjectionRuntime/);
  assert.match(instrumentation, /NEXT_RUNTIME === "edge"/);
  assert.match(neonRuntime, /@neondatabase\/serverless/);
  assert.match(neonRuntime, /wild-wave-25661146/);
  assert.match(neonRuntime, /NEON_PROJECT_ID_IDENTITY_MISMATCH/);
  assert.match(neonRuntime, /DATABASE_URL_UNPOOLED/);
  assert.match(neonRuntime, /schema_migration_history/);
  assert.doesNotMatch(neonRuntime, /configureUiProjectionRuntime/);
  assert.match(neonRuntime, /ensureProductionNeonRuntime/);
  const identity = await read("src/server/identity/identityRuntime.ts");
  const dashboard = await read("src/server/dashboard/readModelRuntime.ts");
  assert.match(identity, /ensureProductionNeonRuntime/);
  assert.match(dashboard, /bindWb01ProjectionRuntime/);
  assert.match(uiProjection, /bindWb01ProjectionRuntime/);
  assert.match(wb01, /configureUiProjectionRuntime/);
  assert.match(wb01, /configureDashboardRuntime/);
  assert.match(ready, /status:\s*503/);
  assert.match(ready, /getUiProjection/);
  assert.match(uiProjection, /UI_PROJECTION_RUNTIME_NOT_BOUND/);
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

test("current EDIT integration ports remain reachable through their authority-bound routes", async () => {
  const contract = await read("src/domain/edit/editRuntimeContract.ts");
  assert.match(contract, /EDIT_INTEGRATION_PORT_COUNT\s*=\s*EDIT_INTEGRATION_PORT_UIDS\.length/);
  assert.match(contract, /EDIT-01-PORT-VOICE-QA-HANDOFF/);

  const routeBindings = [
    ["src/app/v1/handoffs/route.ts", "POST", "createDepartmentHandoff"],
    ["src/app/v1/editing-runtime-runs/route.ts", "POST", "createEditingRuntimeRun"],
    ["src/app/v1/editing-runtime-runs/[runId]/route.ts", "GET", "getEditingRuntimeRun"],
    ["src/app/v1/editing-runtime-runs/[runId]/assembly/route.ts", "POST", "completeAssembly"],
    ["src/app/v1/tasks/[taskId]/outputs/[outputVersionId]/decision/route.ts", "POST", "decideOutputCandidate"],
    ["src/app/v1/scorecards/route.ts", "POST", "submitScorecard"],
    ["src/app/v1/editing-runtime-runs/[runId]/voice-handoff/route.ts", "POST", "transitionEditingToVoiceStage"],
    ["src/app/v1/voice-runtime-runs/[runId]/start/route.ts", "POST", "startVoiceRuntime"],
    ["src/app/v1/voice-runtime-runs/[runId]/route.ts", "GET", "getVoiceRuntimeRun"],
    ["src/app/v1/voice-runtime-runs/[runId]/audio-mix/route.ts", "POST", "completeAudioMix"],
    ["src/app/v1/voice-runtime-runs/[runId]/lip-sync/route.ts", "POST", "completeLipSync"],
    ["src/app/v1/voice-runtime-runs/[runId]/subtitle/route.ts", "POST", "completeSubtitle"],
    ["src/app/v1/voice-runtime-runs/[runId]/qa-handoff/route.ts", "POST", "handoffVoiceToQA"],
  ];

  for (const [path, method, operation] of routeBindings) {
    const source = await read(path);
    assert.match(source, new RegExp(`export\\s+const\\s+${method}\\s*=`), `${path} must expose ${method}`);
    assert.match(source, new RegExp(`["']${operation}["']`), `${path} must remain bound to ${operation}`);
  }

  const contractPorts = [...contract.matchAll(/"EDIT-01-PORT-[A-Z0-9-]+":\{operation:"([^"]+)",method:"(GET|POST)",path:"([^"]+)"\}/g)];
  assert.equal(contractPorts.length, 15, `expected 15 current EDIT integration ports, found ${contractPorts.length}`);
});

test("current QA integration ports remain reachable through their authority-bound routes", async () => {
  const contract = await read("src/domain/qa/qaRuntimeContract.ts");
  assert.match(contract, /QA_INTEGRATION_PORT_COUNT\s*=\s*QA_INTEGRATION_PORT_UIDS\.length/);
  assert.match(contract, /QA-01-PORT-AUTO-TOPIC/);
  assert.doesNotMatch(contract, /"QA-01-PORT-AUTO-TOPIC":\{operation:/);

  const routeBindings = [
    ["src/app/v1/ui-projections/[pageUid]/route.ts", "GET", "getUiProjection"],
    ["src/app/v1/qa/reviews/route.ts", "POST", "startQaReview"],
    ["src/app/v1/scorecards/route.ts", "POST", "submitScorecard"],
    ["src/app/v1/findings/route.ts", "POST", "createFinding"],
    ["src/app/v1/correction-requests/route.ts", "POST", "createCorrectionRequest"],
    ["src/app/v1/state-commands/qareview/startrecheck/route.ts", "POST", "startRecheck"],
    ["src/app/v1/state-commands/qareview/decidepass/route.ts", "POST", "decidePass"],
    ["src/app/v1/state-commands/qareview/decidefail/route.ts", "POST", "decideFail"],
    ["src/app/v1/release-packages/route.ts", "POST", "createReleasePackage"],
  ];

  for (const [path, method, operation] of routeBindings) {
    const source = await read(path);
    assert.match(
      source,
      new RegExp(`export\\s+(?:const\\s+${method}\\s*=|async\\s+function\\s+${method}\\s*\\()`),
      `${path} must expose ${method}`,
    );
    const operationPattern = operation === "getUiProjection"
      ? /\bgetUiProjection\b/
      : new RegExp(`["']${operation}["']`);
    assert.match(source, operationPattern, `${path} must remain bound to ${operation}`);
  }

  const contractPorts = [...contract.matchAll(/"QA-01-PORT-[A-Z0-9-]+":\{operation:"([^"]+)",method:"(GET|POST)",path:"([^"]+)"\}/g)];
  assert.equal(contractPorts.length, 9, `expected 9 HTTP QA integration ports, found ${contractPorts.length}`);
});

test("SYS-01 keeps undefined lifecycle operations fail-closed while shared conversation routes remain reachable", async () => {
  const authority = await read("authority/pages/admin/SYS-01/ACPOS_SYS-01_SYSTEM_LIFECYCLE_AI_FINAL_DESIGN_ENCODING.yaml");
  const contract = await read("src/domain/system/systemRuntimeContract.ts");
  const lifecycleRuntime = await read("src/server/system/systemLifecycleRuntime.ts");
  const projectionPort = await read("src/domain/system/systemProjectionPort.ts");
  const conversationBindings = await read("src/server/system/systemConversationBindings.ts");
  const conversationRuntime = await read("src/server/shared/conversationRuntime.ts");
  const messageRoute = await read("src/app/v1/conversations/[conversationId]/messages/route.ts");
  const stopRoute = await read("src/app/v1/conversations/[conversationId]/generation/stop/route.ts");
  const visual = await read("src/components/pages/SystemVisual.tsx");

  assert.match(authority, /implementation_status:\s*NOT_EXECUTED/);
  assert.doesNotMatch(authority, /\/v1\//);
  assert.match(contract, /SYS_IMPLEMENTATION_STATUS\s*=\s*["']NOT_EXECUTED["']/);
  assert.match(contract, /SYS_SERVICE_OPERATIONS\s*=\s*\[["']createCandidate["'],\s*["']createChangeRequest["'],\s*["']runSandboxTest["']\]/);
  assert.doesNotMatch(contract, /PORT_METHOD_PATH|api_path/i);
  assert.match(lifecycleRuntime, /SYS01_RUNTIME_NOT_BOUND/);
  assert.match(lifecycleRuntime, /SYSTEM_CONTINUITY_CONTEXT_UNRESOLVED/);
  assert.match(lifecycleRuntime, /AUTHORIZATION_EVALUATION_FAILED/);
  assert.match(projectionPort, /\/v1\/ui-projections\/admin%3ASYS-01/);

  assert.match(conversationBindings, /\/v1\/conversations\/\$\{encodeURIComponent\(input\.conversation_id\)\}\/messages/);
  assert.match(conversationBindings, /\/v1\/conversations\/\$\{encodeURIComponent\(input\.conversation_id\)\}\/generation\/stop/);
  assert.match(messageRoute, /conversationPost\(["']sendConversationMessage["']\)/);
  assert.match(stopRoute, /conversationPost\(["']stopConversationGeneration["']\)/);
  assert.match(conversationRuntime, /CONVERSATION_RUNTIME_NOT_BOUND/);
  assert.match(conversationRuntime, /status:503/);

  assert.match(visual, /data-effectful-runtime-ready=["']false["']/);
  for (const controlId of [
    "SYS-01-BTN-ATTACH",
    "SYS-01-BTN-SEND",
    "SYS-01-BTN-STOP",
    "SYS-01-BTN-CANDIDATE-CREATE",
    "SYS-01-BTN-CR-CREATE",
    "SYS-01-BTN-SANDBOX-TEST",
  ]) {
    assert.match(visual, new RegExp(`id=["']${controlId}["'][\\s\\S]{0,300}?\\bdisabled\\b`), `${controlId} must remain disabled until its exact runtime binding is authority-resolved`);
  }
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
