import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("DEV-01 production discovery lifecycle is authority-bound and uses the canonical outreach table", async () => {
  const contract = await read("src/domain/dev/devRuntimeContract.ts");
  const bindings = await read("src/domain/dev/devControlBindings.ts");
  const runtime = await read("src/server/dev/devCommandRuntime.ts");
  const production = await read("src/server/dev/productionDevCommandRuntime.ts");
  const identity = await read("src/server/shared/identityPageCommandRuntime.ts");
  const projection = await read("src/server/shared/pageCatalogProjectionRuntime.ts");
  const adapters = await read("src/domain/catalog/identityClientCommandAdapters.ts");

  assert.match(contract, /DEV_SYSTEM_IMPLEMENTATION_STATUS = "RUNTIME_BOUND_PENDING_RELEASE"/);
  for (const operation of ["startCompanyDiscovery", "pauseCompanyDiscovery", "resumeCompanyDiscovery", "stopCompanyDiscovery"]) {
    assert.match(bindings, new RegExp(`operation: "${operation}"`));
    assert.match(runtime, new RegExp(`"${operation}"`));
    assert.match(identity, new RegExp(`${operation}:\\{resource_key:"action:admin:DEV-01:`));
    assert.match(adapters, new RegExp(`binding\\.operation === "${operation}"`));
  }

  assert.match(production, /INSERT INTO public\.outreach_discovery_jobs/);
  assert.match(production, /UPDATE public\.outreach_discovery_jobs/);
  assert.match(production, /external_request_sent: false/);
  assert.match(production, /deployment_triggered: false/);
  assert.match(production, /DEV_DISCOVERY_ACTIVE_JOB_STATE_CONFLICT/);
  assert.match(identity, /configureDevCommandRuntime/);
  assert.match(identity, /executeProductionDevCommand/);

  assert.match(projection, /"DEV-01-FLD-JOB-REF"/);
  assert.match(projection, /"DEV-01-GATE-DISCOVERY-START": run_status === null \|\| run_status === "STOPPED"/);
  assert.match(projection, /"DEV-01-GATE-DISCOVERY-RUNNING": run_status === "RUNNING"/);
  assert.match(projection, /"DEV-01-GATE-DISCOVERY-PAUSED": run_status === "PAUSED"/);
  assert.match(projection, /acceptance_scope',''\) <> 'GATE_24_DEV'/);
});

test("DEV-01 production discovery routes stay on the registered Authority paths", async () => {
  const routes = [
    ["src/app/v1/outreach/discovery-jobs/route.ts", "startCompanyDiscovery"],
    ["src/app/v1/outreach/discovery-jobs/[jobId]/pause/route.ts", "pauseCompanyDiscovery"],
    ["src/app/v1/outreach/discovery-jobs/[jobId]/resume/route.ts", "resumeCompanyDiscovery"],
    ["src/app/v1/outreach/discovery-jobs/[jobId]/stop/route.ts", "stopCompanyDiscovery"],
  ];
  for (const [path, operation] of routes) {
    const source = await read(path);
    assert.match(source, /export const POST = createDevRoute/);
    assert.match(source, new RegExp(`createDevRoute\\("${operation}"\\)`));
  }
});


test("DEV-01 production acceptance stays manual, exact-SHA-pinned, and non-deploying", async () => {
  const script = await read("scripts/production-dev-lifecycle-e2e.mjs");
  const workflow = await read(".github/workflows/dev-lifecycle-acceptance.yml");

  assert.match(script, /ACPOS_EXPECT_RELEASE_SHA/);
  assert.match(script, /HEALTH_RELEASE_SHA_MISMATCH/);
  assert.match(script, /\/v1\/outreach\/discovery-jobs/);
  assert.match(script, /\/pause/);
  assert.match(script, /\/resume/);
  assert.match(script, /\/stop/);
  assert.match(script, /external_request_sent === false/);
  assert.match(script, /deployment_triggered === false/);
  assert.match(script, /PRODUCTION_DEV_LIFECYCLE_E2E_PASS/);

  assert.match(workflow, /workflow_dispatch:/);
  assert.doesNotMatch(workflow, /push:/);
  assert.doesNotMatch(workflow, /deployment_status:/);
  assert.match(workflow, /expected_release_sha:/);
  assert.match(workflow, /environment: Production/);
  assert.match(workflow, /node --check scripts\/production-dev-lifecycle-e2e\.mjs/);
  assert.match(workflow, /node scripts\/production-dev-lifecycle-e2e\.mjs/);
});
