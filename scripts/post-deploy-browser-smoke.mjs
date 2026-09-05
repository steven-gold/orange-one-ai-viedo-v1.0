import { chromium } from "playwright";

const base = (process.env.ACPOS_DEPLOYMENT_URL ?? "https://orange-one-acpos-test.vercel.app").replace(/\/$/, "");

function protectionHeaders() {
  const secret = process.env.VERCEL_AUTOMATION_BYPASS_SECRET;
  if (!secret) return {};
  return {
    "x-vercel-protection-bypass": secret,
  };
}

const routes = [
  ["/", "workspace:WB-01"], ["/core", "CORE-01"], ["/assets", "ASSET-01"], ["/video", "VIDEO-01"],
  ["/edit", "EDIT-01"], ["/qa", "QA-01"], ["/database", "admin:DB-01"], ["/strategy", "workspace:STR-01"],
  ["/info", "workspace:INFO-01"], ["/admin/system", "admin:SYS-01"], ["/admin/accounts", "admin:IAM-01"],
  ["/admin/dev", "admin:DEV-01"], ["/admin/social", "admin:SOC-01"], ["/admin/erp", "admin:ERP-01"],
  ["/admin/aiapi", "admin:AIAPI-01"], ["/admin/qa-criteria", "admin:SG-02"], ["/admin/strategy", "admin:STR-01"],
  ["/admin/knowledge", "admin:KB-01"],
];

const browser = await chromium.launch({ headless: true });
let cases = 0;
try {
  for (const width of [1280, 1440, 1920]) {
    for (const [route, uid] of routes) {
      const page = await browser.newPage({
        viewport: { width, height: 1400 },
        extraHTTPHeaders: protectionHeaders(),
      });
      const errors = [];
      page.on("pageerror", (error) => errors.push(`pageerror:${error.message}`));
      page.on("console", (message) => {
        if (message.type() === "error" && !/Failed to load resource.*503/.test(message.text())) {
          errors.push(`console:${message.text()}`);
        }
      });

      const response = await page.goto(`${base}${route}`, { waitUntil: "networkidle", timeout: 45_000 });
      if (!response?.ok()) throw new Error(`NAV_${route}_${response?.status()}`);

      const root = page.locator("[data-page-uid]").first();
      await root.waitFor({ state: "attached", timeout: 15_000 });
      const actual = await root.getAttribute("data-page-uid");
      if (actual !== uid) throw new Error(`UID_${route}_${actual}`);

      const state = await root.getAttribute("data-page-state");
      if (state === "LOADING") throw new Error(`STUCK_LOADING_${uid}`);

      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      if (overflow > 0) throw new Error(`OVERFLOW_${uid}_${width}_${overflow}`);

      const body = (await page.locator("body").textContent()) ?? "";
      if (body.includes('"use client"') || body.includes("function KnowledgeAdminVisual") || body.includes("const CONTROLS")) {
        throw new Error(`SOURCE_RENDER_${uid}`);
      }
      if (/TEST_ONLY|TEST-RUN-|"synthetic"\s*:\s*true/.test(body)) throw new Error(`TEST_DATA_LEAK_${uid}`);
      if (errors.length) throw new Error(`${uid}_${width}_${errors.join("|")}`);

      cases += 1;
      await page.close();
    }
  }
} finally {
  await browser.close();
}

process.stdout.write(`POST_DEPLOY_BROWSER_SMOKE_PASS base=${base} cases=${cases} widths=1280,1440,1920 pages=${routes.length}\n`);
