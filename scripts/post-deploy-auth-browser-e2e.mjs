import { chromium } from "playwright";

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

const frontNavIds = ["NAV-01","NAV-02","NAV-03","NAV-04","NAV-05","NAV-06","NAV-07","NAV-08","NAV-09"];
const adminNavIds = ["ADMIN-NAV-01","ADMIN-NAV-02","ADMIN-NAV-03","ADMIN-NAV-04","ADMIN-NAV-05","ADMIN-NAV-06","ADMIN-NAV-07","ADMIN-NAV-08","ADMIN-NAV-09"];

if (!email || !password) {
  process.stdout.write("POST_DEPLOY_AUTH_BROWSER_E2E_BLOCKED reason=PRODUCTION_LOGIN_CREDENTIAL_NOT_CONFIGURED\n");
  process.exit(0);
}

const browser = await chromium.launch({ headless: true });
try {
  const context = await browser.newContext({ extraHTTPHeaders: protectionHeaders() });
  const login = await context.request.post(`${base}/v1/identity/session`, {
    headers: { "content-type": "application/json", "x-correlation-id": crypto.randomUUID() },
    data: { email, password },
  });
  assert(login.status() === 200, `AUTH_BROWSER_LOGIN_HTTP_${login.status()}`);
  const loginBody = await login.json().catch(() => null);
  assert(loginBody?.ok === true && loginBody?.logged_in === true, "AUTH_BROWSER_LOGIN_BODY_INVALID");
  assert(loginBody?.navigation_visibility === "READY", "AUTH_BROWSER_NAVIGATION_VISIBILITY_NOT_READY");
  assert(Array.isArray(loginBody?.visible_page_uids) && loginBody.visible_page_uids.length === 18, "AUTH_BROWSER_VISIBLE_PAGE_COUNT_INVALID");

  const page = await context.newPage();
  await page.goto(`${base}/`, { waitUntil: "networkidle", timeout: 45_000 });
  await page.waitForFunction((expected) => document.querySelectorAll("[data-nav-id]").length === expected, frontNavIds.length, { timeout: 15_000 });
  const actualFront = await page.locator("[data-nav-id]").evaluateAll((nodes) => nodes.map((node) => node.getAttribute("data-nav-id")).filter(Boolean));
  assert(JSON.stringify(actualFront) === JSON.stringify(frontNavIds), `AUTH_BROWSER_FRONT_NAV_MISMATCH_${actualFront.join(",")}`);

  const frontTargets = await page.locator("[data-nav-id]").evaluateAll((nodes) => nodes.map((node) => node.getAttribute("data-target-page-uid")).filter(Boolean));
  assert(frontTargets.length === 9, `AUTH_BROWSER_FRONT_TARGET_COUNT_${frontTargets.length}`);
  const frontSurfaceTargets = await page.locator(".sidebar-footer button[data-target-page-uid]").evaluateAll((nodes) => nodes.map((node) => node.getAttribute("data-target-page-uid")).filter(Boolean));
  assert(frontSurfaceTargets.length === 1, `AUTH_BROWSER_FRONT_SURFACE_TARGET_COUNT_${frontSurfaceTargets.length}`);
  assert(frontSurfaceTargets[0] === "admin:SYS-01", `AUTH_BROWSER_FRONT_SURFACE_TARGET_INVALID_${frontSurfaceTargets[0] ?? "UNRESOLVED"}`);

  await page.goto(`${base}/admin/system`, { waitUntil: "domcontentloaded", timeout: 45_000 });
  await page.waitForFunction((expected) => document.querySelectorAll("[data-nav-id]").length === expected, adminNavIds.length, { timeout: 15_000 });
  const actualAdmin = await page.locator("[data-nav-id]").evaluateAll((nodes) => nodes.map((node) => node.getAttribute("data-nav-id")).filter(Boolean));
  assert(JSON.stringify(actualAdmin) === JSON.stringify(adminNavIds), `AUTH_BROWSER_ADMIN_NAV_MISMATCH_${actualAdmin.join(",")}`);

  const adminTargets = await page.locator("[data-nav-id]").evaluateAll((nodes) => nodes.map((node) => node.getAttribute("data-target-page-uid")).filter(Boolean));
  assert(adminTargets.length === 9, `AUTH_BROWSER_ADMIN_TARGET_COUNT_${adminTargets.length}`);

  const adminSurfaceTargets = await page.locator(".sidebar-footer button[data-target-page-uid]").evaluateAll((nodes) => nodes.map((node) => node.getAttribute("data-target-page-uid")).filter(Boolean));
  assert(adminSurfaceTargets.length === 1, `AUTH_BROWSER_ADMIN_SURFACE_TARGET_COUNT_${adminSurfaceTargets.length}`);
  assert(adminSurfaceTargets[0] === "workspace:WB-01", `AUTH_BROWSER_ADMIN_SURFACE_TARGET_INVALID_${adminSurfaceTargets[0] ?? "UNRESOLVED"}`);

  process.stdout.write("POST_DEPLOY_AUTH_BROWSER_E2E_PASS front_nav=9 admin_nav=9 visible_pages=18\n");
  await context.close();
} finally {
  await browser.close();
}
