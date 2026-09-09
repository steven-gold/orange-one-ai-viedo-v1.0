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

const frontNavIds = ["NAV-01","NAV-02","NAV-03","NAV-04","NAV-05","NAV-06","NAV-07","NAV-08"];
const adminNavIds = ["ADMIN-NAV-01","ADMIN-NAV-02","ADMIN-NAV-03","ADMIN-NAV-04","ADMIN-NAV-05","ADMIN-NAV-06","ADMIN-NAV-07","ADMIN-NAV-08"];

if (!email || !password) {
  process.stdout.write("POST_DEPLOY_AUTH_BROWSER_E2E_BLOCKED reason=PRODUCTION_LOGIN_CREDENTIAL_NOT_CONFIGURED\n");
  process.exit(0);
}

const browser = await chromium.launch({ headless: true });
try {
  const context = await browser.newContext({
    extraHTTPHeaders: protectionHeaders(),
    viewport: { width: 1440, height: 1000 },
  });

  const signInPage = await context.newPage();
  const signInResponse = await signInPage.goto(`${base}/login`, { waitUntil: "networkidle", timeout: 45_000 });
  assert(signInResponse?.status() === 200, `AUTH_BROWSER_LOGIN_PAGE_HTTP_${signInResponse?.status()}`);
  const signInRoot = signInPage.locator('[data-login-visual="ACPOS_LOGIN_CURRENT_V2"]');
  await signInRoot.waitFor({ state: "visible", timeout: 15_000 });
  assert(await signInRoot.count() === 1, "AUTH_BROWSER_LOGIN_VISUAL_MARKER_MISSING");
  assert(await signInPage.locator(".login-hero").isVisible(), "AUTH_BROWSER_LOGIN_HERO_NOT_VISIBLE");
  assert(await signInPage.locator(".login-access").isVisible(), "AUTH_BROWSER_LOGIN_ACCESS_NOT_VISIBLE");
  assert(await signInPage.locator('[data-login-contract="CURRENT_VISUAL_AUTHORITY"]').count() === 1, "AUTH_BROWSER_LOGIN_CONTRACT_MISSING");
  assert(await signInPage.locator(".login-language-switch button").count() === 3, "AUTH_BROWSER_LOGIN_LOCALE_COUNT_INVALID");
  assert(await signInPage.locator('form[action="/identity/login"]').count() === 1, "AUTH_BROWSER_LOGIN_FORM_ACTION_INVALID");
  await signInPage.close();

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
  assert(frontTargets.length === 8, `AUTH_BROWSER_FRONT_TARGET_COUNT_${frontTargets.length}`);
  const frontSurfaceTargets = await page.locator(".surface-switch-group [data-target-page-uid]").evaluateAll((nodes) => nodes.map((node) => node.getAttribute("data-target-page-uid")).filter(Boolean));
  assert(JSON.stringify(frontSurfaceTargets) === JSON.stringify(["workspace:WB-01","admin:SYS-01"]), `AUTH_BROWSER_FRONT_SURFACE_TARGET_INVALID_${frontSurfaceTargets.join(",")}`);

  await page.goto(`${base}/admin/system`, { waitUntil: "domcontentloaded", timeout: 45_000 });
  await page.waitForFunction((expected) => document.querySelectorAll("[data-nav-id]").length === expected, adminNavIds.length, { timeout: 15_000 });
  const actualAdmin = await page.locator("[data-nav-id]").evaluateAll((nodes) => nodes.map((node) => node.getAttribute("data-nav-id")).filter(Boolean));
  assert(JSON.stringify(actualAdmin) === JSON.stringify(adminNavIds), `AUTH_BROWSER_ADMIN_NAV_MISMATCH_${actualAdmin.join(",")}`);

  const adminTargets = await page.locator("[data-nav-id]").evaluateAll((nodes) => nodes.map((node) => node.getAttribute("data-target-page-uid")).filter(Boolean));
  assert(adminTargets.length === 8, `AUTH_BROWSER_ADMIN_TARGET_COUNT_${adminTargets.length}`);

  const adminSurfaceTargets = await page.locator(".surface-switch-group [data-target-page-uid]").evaluateAll((nodes) => nodes.map((node) => node.getAttribute("data-target-page-uid")).filter(Boolean));
  assert(JSON.stringify(adminSurfaceTargets) === JSON.stringify(["workspace:WB-01","admin:SYS-01"]), `AUTH_BROWSER_ADMIN_SURFACE_TARGET_INVALID_${adminSurfaceTargets.join(",")}`);

  process.stdout.write("POST_DEPLOY_AUTH_BROWSER_E2E_PASS login_visual=ACPOS_LOGIN_CURRENT_V2 login_locales=3 front_nav=8 admin_nav=8 visible_pages=18\n");
  await context.close();
} finally {
  await browser.close();
}
