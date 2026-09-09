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
  assert.doesNotMatch(shell, /id: "NAV-09"/);
  assert.doesNotMatch(shell, /id: "ADMIN-NAV-09"/);
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
  assert.match(browser, /POST_DEPLOY_AUTH_BROWSER_E2E_PASS login_visual=ACPOS_LOGIN_CURRENT_V2 login_locales=3 front_nav=8 admin_nav=8 visible_pages=18/);
  assert.match(browser, /AUTH_BROWSER_LOGIN_VISUAL_MARKER_MISSING/);
  assert.match(browser, /AUTH_BROWSER_LOGIN_LOCALE_COUNT_INVALID/);

  assert.match(workflow, /Run deployed ACPOS authenticated browser visibility E2E/);
  assert.match(workflow, /node scripts\/post-deploy-auth-browser-e2e\.mjs/);
  assert.match(release, /node --check scripts\/post-deploy-auth-browser-e2e\.mjs/);
});


test("AppShell preserves frozen global visual shell classes while retaining permission-aware navigation", async () => {
  const shell = await readFile("src/components/shell/AppShell.tsx", "utf8");
  const css = await readFile("src/app/globals.css", "utf8");

  for (const className of ["acpos-shell", "global-header", "global-sidebar", "workspace-slot", "header-cluster", "sidebar-surface"]) {
    assert.match(shell, new RegExp(`className=.*${className}`), `${className} must remain in the Current visual shell`);
    assert.match(css, new RegExp(`\\.${className}\\b`), `${className} must have a global visual rule`);
  }

  for (const staleClass of ["app-shell", "shell-main", "topbar", "content-area"]) {
    assert.doesNotMatch(shell, new RegExp(`className=["']${staleClass}["']`), `${staleClass} must not replace the frozen shell without matching visual authority`);
  }

  assert.match(shell, /visible_page_uids/);
  assert.match(shell, /data-target-page-uid=\{item\.pageUid\}/);
  assert.match(shell, /surface-switch-group/);
  assert.match(shell, /GHS-CTL-SURFACE-FRONT/);
  assert.match(shell, /GHS-CTL-SURFACE-ADMIN/);
  assert.doesNotMatch(shell, /sidebar-footer/);
  assert.match(shell, /GHS-PORT-IDENTITY/);
});


test("Current Global L1 authority is user-confirmed 8 frontend + 8 admin while INFO/KB remain non-L1 current pages", async () => {
  const nav = await read("authority/global/ACPOS_CURRENT_NAVIGATION_PERMISSION_AUTHORITY_FINAL_LOCKED.yaml");
  const shellAuthority = await read("authority/global/GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY_FINAL_LOCKED_V1.9.yaml");
  const system = await read("authority/global/ACPOS_SYSTEM_AUTHORITY_FINAL_LOCKED_CURRENT.yaml");
  const matrix = await read("authority/global/ACPOS_PAGE_INTEGRATION_MATRIX_FINAL_LOCKED_CURRENT.yaml");
  const iam = await read("src/components/pages/IamVisual.tsx");
  const iamCatalog = await read("src/i18n/iamCatalog.ts");

  assert.match(nav, /front_workspace_navigation:[\s\S]*?count: 8/);
  assert.match(nav, /admin_navigation:[\s\S]*?count: 8/);
  assert.doesNotMatch(nav, /nav_id: NAV-09/);
  assert.doesNotMatch(nav, /nav_id: ADMIN-NAV-09/);
  assert.match(shellAuthority, /navigation:[\s\S]*?count: 8/);
  assert.doesNotMatch(shellAuthority, /nav_id: NAV-09/);
  assert.match(system, /Front workspace navigation has exactly 8 L1 items/);
  assert.match(system, /Admin navigation has exactly 8 L1 items/);
  assert.match(matrix, /page_uid: workspace:INFO-01[\s\S]*?navigation: NON_L1_CURRENT_PAGE/);
  assert.match(matrix, /page_uid: admin:KB-01[\s\S]*?navigation: NON_L1_CURRENT_ADMIN_PAGE/);
  assert.match(iam, /data-frontend-l1-count="8"/);
  assert.match(iam, /data-backend-l1-count="8"/);
  assert.match(iamCatalog, /前台 8 L1/);
  assert.match(iamCatalog, /後台 8 L1/);
});
