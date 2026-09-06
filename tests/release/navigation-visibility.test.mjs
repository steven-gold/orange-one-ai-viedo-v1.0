import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(path, "utf8");

test("session navigation visibility is derived from PAGE permission assignments and fails closed", async () => {
  const runtime = await read("src/server/identity/navigationVisibilityRuntime.ts");
  const session = await read("src/app/v1/identity/session/route.ts");
  const shell = await read("src/components/shell/AppShell.tsx");

  assert.match(runtime, /CURRENT_PAGE_RESOURCE_KEYS/);
  assert.match(runtime, /"workspace:WB-01": "page:workspace:WB-01"/);
  assert.match(runtime, /runRlsActorQuery/);
  assert.match(runtime, /r\.resource_type = 'PAGE'/);
  assert.match(runtime, /a\.action = 'VIEW'/);
  assert.match(runtime, /a\.status = 'APPROVED'/);
  assert.match(runtime, /effects\?\.has\("ALLOW"\) && !effects\.has\("DENY"\)/);
  assert.match(runtime, /NAVIGATION_PERMISSION_EVALUATION_FAILED/);

  assert.match(session, /readVisiblePageUidsForActor/);
  assert.match(session, /navigation_visibility: visibility\.ok \? "READY" : "UNAVAILABLE"/);
  assert.match(session, /visible_page_uids: visibility\.visible_page_uids/);

  assert.match(shell, /pageUid: "workspace:WB-01"/);
  assert.match(shell, /pageUid: "admin:KB-01"/);
  assert.match(shell, /visiblePageSet\.has\(item\.pageUid\)/);
  assert.match(shell, /frontSurfaceTarget/);
  assert.match(shell, /adminSurfaceTarget/);
  assert.match(shell, /data-target-page-uid=\{item\.pageUid\}/);
  assert.doesNotMatch(shell, /const navItems = surface === "admin" \? ADMIN_NAV_ITEMS : NAV_ITEMS;/);
});

test("production authenticated acceptance requires exact 18-page API and browser visibility", async () => {
  const api = await read("scripts/post-deploy-auth-e2e.mjs");
  const browser = await read("scripts/post-deploy-auth-browser-e2e.mjs");
  const workflow = await read(".github/workflows/post-deploy-smoke.yml");
  const release = await read(".github/workflows/release-gate.yml");

  assert.match(api, /assertExactVisiblePages/);
  assert.match(api, /visible\.length === projectionUids\.length/);
  assert.match(api, /projectionPass === 18/);
  assert.match(api, /visible_pages=18/);

  assert.match(browser, /frontNavIds/);
  assert.match(browser, /adminNavIds/);
  assert.match(browser, /AUTH_BROWSER_FRONT_NAV_MISMATCH/);
  assert.match(browser, /AUTH_BROWSER_ADMIN_NAV_MISMATCH/);
  assert.match(browser, /POST_DEPLOY_AUTH_BROWSER_E2E_PASS front_nav=9 admin_nav=9 visible_pages=18/);

  assert.match(workflow, /Run deployed ACPOS authenticated browser visibility E2E/);
  assert.match(workflow, /node scripts\/post-deploy-auth-browser-e2e\.mjs/);
  assert.match(release, /node --check scripts\/post-deploy-auth-browser-e2e\.mjs/);
});
