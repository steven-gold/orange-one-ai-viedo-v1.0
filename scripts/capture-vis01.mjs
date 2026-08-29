import { chromium } from "playwright";
import fs from "node:fs/promises";

const outDir = "artifacts/vis01";
await fs.mkdir(outDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const near = (a, b, tolerance = 1) => Math.abs(a - b) <= tolerance;
const round = (n) => Math.round(n * 10) / 10;

async function rect(locator) {
  const r = await locator.boundingBox();
  if (!r) throw new Error("Missing bounding box");
  return Object.fromEntries(Object.entries(r).map(([k,v]) => [k, round(v)]));
}

async function cardRects() {
  const cards = page.locator('[data-page-uid="workspace:WB-01"] section[data-order]');
  const result = [];
  for (let i = 0; i < await cards.count(); i++) {
    const el = cards.nth(i);
    result.push({
      order: Number(await el.getAttribute("data-order")),
      sectionId: await el.getAttribute("data-section-id"),
      state: await el.getAttribute("data-state"),
      ...(await rect(el)),
    });
  }
  return result;
}

await page.goto("http://127.0.0.1:3000", { waitUntil: "networkidle" });

const shell = {
  header: await rect(page.locator(".global-header")),
  sidebar: await rect(page.locator(".global-sidebar")),
  workspace: await rect(page.locator(".workspace-slot")),
};
assert(near(shell.header.height, 58), `Header height ${shell.header.height}`);
assert(near(shell.sidebar.width, 64), `Collapsed sidebar width ${shell.sidebar.width}`);
assert(near(shell.workspace.x, 78) && near(shell.workspace.y, 68), `Workspace origin ${JSON.stringify(shell.workspace)}`);
assert(await page.locator(".nav-item").count() === 8, "Global nav count must be 8");
assert(await page.locator('[data-nav-id="NAV-01"]').getAttribute("aria-current") === "page", "NAV-01 must be active");
const quickValues = await page.locator(".quick-button span").allTextContents();
assert(quickValues.length === 3 && quickValues.every(v => v.trim() === "—"), `Header missing values must be —: ${quickValues}`);

const brandLogo = page.locator('img[alt="ORANGE ONE"]');
assert(await brandLogo.count() === 1, "Canonical ORANGE ONE logo image must render exactly once");
const logoSource = await brandLogo.getAttribute("src");
assert(logoSource === "/brand/orange-one-logo.png", `Unexpected logo source: ${logoSource}`);
const logoNatural = await brandLogo.evaluate(img => ({ width: img.naturalWidth, height: img.naturalHeight }));
assert(logoNatural.width === 416 && logoNatural.height === 192, `Canonical logo dimensions changed: ${JSON.stringify(logoNatural)}`);
const logoRect = await rect(brandLogo);
assert(near(logoRect.width / logoRect.height, 416 / 192, 0.02), `Logo render ratio changed: ${JSON.stringify(logoRect)}`);

let dataRequests = 0;
page.on("request", req => { if (["fetch","xhr"].includes(req.resourceType())) dataRequests++; });

const languageButton = page.locator('button[aria-haspopup="listbox"]');
assert((await languageButton.textContent())?.trim() === "zh-TW", "Default locale control must display zh-TW");
assert(await page.locator("html").getAttribute("lang") === "zh-Hant-TW", "Default html lang must be zh-Hant-TW");
assert((await page.locator('[data-nav-id="NAV-02"] .nav-label').textContent())?.trim() === "專案 / 專題", "Default nav translation mismatch");
assert((await page.locator('[data-order="1"] h2').textContent())?.trim() === "專案總數", "Default WB-01 translation mismatch");

await languageButton.click();
await page.screenshot({ path: `${outDir}/vis01-language-menu-zh-tw.png`, fullPage: false });
await page.getByRole("option").filter({ hasText: "简体中文" }).click();
assert((await languageButton.textContent())?.trim() === "zh-CN", "Language control must display zh-CN after switch");
assert(await page.locator("html").getAttribute("lang") === "zh-Hans-CN", "Simplified Chinese html lang mismatch");
assert((await page.locator('[data-nav-id="NAV-02"] .nav-label').textContent())?.trim() === "项目 / 专题", "zh-CN nav translation mismatch");
assert((await page.locator('[data-order="1"] h2').textContent())?.trim() === "专案总数", "zh-CN WB-01 translation mismatch");
assert((await page.locator('[data-order="12"] h2').textContent())?.trim() === "AI / 产业新闻", "AI fixed term must remain AI in zh-CN");
assert((await page.locator('[data-nav-id="NAV-06"] .nav-label').textContent())?.trim() === "QA", "QA must remain fixed in zh-CN");
assert(await page.evaluate(() => localStorage.getItem("acpos.locale")) === "zh-CN", "zh-CN locale must persist");
assert(await brandLogo.getAttribute("src") === "/brand/orange-one-logo.png", "Locale switch must not alter brand asset");

await languageButton.click();
await page.getByRole("option").filter({ hasText: "English" }).click();
assert((await languageButton.textContent())?.trim() === "en", "Language control must display en after switch");
assert(await page.locator("html").getAttribute("lang") === "en", "English html lang mismatch");
assert((await page.locator('[data-nav-id="NAV-02"] .nav-label').textContent())?.trim() === "Project / Topic", "English nav translation mismatch");
assert((await page.locator('[data-order="1"] h2').textContent())?.trim() === "Company Project Count", "English WB-01 translation mismatch");
assert((await page.locator('[data-order="12"] h2').textContent())?.trim() === "AI / Industry News", "AI fixed term must remain AI in English");
assert((await page.locator('[data-nav-id="NAV-06"] .nav-label').textContent())?.trim() === "QA", "QA must remain fixed in English");
assert(await page.evaluate(() => localStorage.getItem("acpos.locale")) === "en", "English locale must persist");

await languageButton.click();
await page.getByRole("option").filter({ hasText: "繁體中文" }).click();
assert((await languageButton.textContent())?.trim() === "zh-TW", "Language control must return to zh-TW");
assert(await page.locator("html").getAttribute("lang") === "zh-Hant-TW", "Traditional Chinese html lang mismatch after return");
assert((await page.locator('[data-nav-id="NAV-02"] .nav-label').textContent())?.trim() === "專案 / 專題", "zh-TW nav translation mismatch after return");
assert(dataRequests === 0, `Locale switching must not execute business fetch/xhr; got ${dataRequests}`);

const pageRoot = page.locator('[data-page-uid="workspace:WB-01"]');
assert(await pageRoot.count() === 1, "WB-01 root missing");
assert(await page.locator('[data-page-uid="workspace:WB-01"] section[data-order]').count() === 14, "WB-01 must render exactly 14 cards");
const viewButtons = page.locator('[data-page-uid="workspace:WB-01"] button[data-control-id]');
assert(await viewButtons.count() === 14, "WB-01 must render exactly 14 canonical SECTION_OPEN controls");
const orders = await page.locator('[data-page-uid="workspace:WB-01"] section[data-order]').evaluateAll(els => els.map(el => Number(el.getAttribute("data-order"))));
assert(JSON.stringify(orders) === JSON.stringify(Array.from({length:14},(_,i)=>i+1)), `Canonical order mismatch: ${orders}`);
const buttonText = await viewButtons.allTextContents();
assert(buttonText.every(t => t.trim() === "查看"), `Visible trigger must be 查看 only: ${buttonText}`);
const pageSvgs = await page.locator('[data-page-uid="workspace:WB-01"] svg').count();
assert(pageSvgs === 0, `Decorative page icons/charts forbidden; found ${pageSvgs} SVG`);
const kpiValues = await page.locator('[data-page-uid="workspace:WB-01"] section[data-order]').evaluateAll(els => els.slice(0,6).map(el => {
  const body = el.querySelector('div[class*="cardBody"]');
  return body?.textContent?.trim() ?? "";
}));
assert(kpiValues.every(v => v === "—"), `KPI missing values must be —: ${kpiValues}`);
const cardStates = await page.locator('[data-page-uid="workspace:WB-01"] section[data-order]').evaluateAll(els => els.map(el => el.getAttribute("data-state")));
assert(cardStates.every(v => v === "EMPTY"), `Visual baseline must use EMPTY state only: ${cardStates}`);

const cards1440 = await cardRects();
const heightExpected = {1:136,2:136,3:136,4:136,5:136,6:136,7:320,8:320,9:280,10:280,11:240,12:240,13:240,14:220};
for (const c of cards1440) assert(near(c.height, heightExpected[c.order]), `1440 order ${c.order} height ${c.height}`);
assert(cards1440.slice(0,6).every(c => near(c.y, cards1440[0].y)), "1440 six KPI cards must share one row");
assert(cards1440.slice(0,6).every(c => near(c.width, cards1440[0].width)), "1440 KPI widths must match");
assert(near(cards1440[6].y, cards1440[7].y), "Project and company progress must share row");
assert(near(cards1440[8].y, cards1440[9].y), "Production and notifications must share row");
assert(cards1440.slice(10,13).every(c => near(c.y, cards1440[10].y) && near(c.width, cards1440[10].width)), "Information cards must share row/equal span");
assert(near(cards1440[6].width, cards1440[7].width * 2 + 16, 2), "8/4 project row span mismatch");
assert(near(cards1440[8].width, cards1440[9].width * 2 + 16, 2), "8/4 production row span mismatch");
const workspaceMetrics1440 = await page.locator(".workspace-slot").evaluate(el => ({clientWidth:el.clientWidth,scrollWidth:el.scrollWidth,clientHeight:el.clientHeight,scrollHeight:el.scrollHeight,scrollTop:el.scrollTop}));
assert(workspaceMetrics1440.scrollHeight > workspaceMetrics1440.clientHeight, "Dashboard must scroll vertically at 1440x900");
assert(workspaceMetrics1440.scrollWidth === workspaceMetrics1440.clientWidth, `1440 should not require horizontal scroll: ${JSON.stringify(workspaceMetrics1440)}`);
await page.screenshot({ path: `${outDir}/vis01-1440-top.png`, fullPage: false });
await page.locator(".workspace-slot").evaluate(el => { el.scrollTop = 470; });
await page.waitForTimeout(50);
await page.screenshot({ path: `${outDir}/vis01-1440-middle.png`, fullPage: false });
await page.locator(".workspace-slot").evaluate(el => { el.scrollTop = el.scrollHeight; });
await page.waitForTimeout(50);
await page.screenshot({ path: `${outDir}/vis01-1440-bottom.png`, fullPage: false });
await page.locator(".workspace-slot").evaluate(el => { el.scrollTop = 0; });

const firstTrigger = viewButtons.first();
await firstTrigger.click();
await page.waitForTimeout(50);
assert(dataRequests === 0, `Visual drawer must not execute API requests; got ${dataRequests}`);
const drawer = page.locator('[data-component-uid="WB-01-CMP-DRAWER-PROJECTION"] [role="dialog"]');
const drawerRect = await rect(drawer);
assert(near(drawerRect.width, 520), `Drawer width ${drawerRect.width} != 520`);
assert(near(drawerRect.y, 58), `Drawer y ${drawerRect.y} != 58`);
assert((await page.locator("#wb01-drawer-title").textContent())?.trim() === "專案總數", "Drawer title mismatch");
assert((await page.locator('[data-component-uid="WB-01-CMP-DRAWER-PROJECTION"]').textContent())?.includes("read_model_version: —"), "Drawer read_model_version missing");
assert((await page.locator('[data-component-uid="WB-01-CMP-DRAWER-PROJECTION"]').textContent())?.includes("correlation_id: —"), "Drawer correlation_id missing");
assert(await page.locator('[role="dialog"] button').count() === 1, "Drawer may expose only Close action in visual baseline");
assert(await page.locator('[role="dialog"] button').evaluate(el => el === document.activeElement), "Close button must receive focus");
await page.keyboard.press("Tab");
assert(await page.locator('[role="dialog"] button').evaluate(el => el === document.activeElement), "Drawer focus trap failed");
await page.screenshot({ path: `${outDir}/vis01-1440-drawer.png`, fullPage: false });
await page.keyboard.press("Escape");
assert(await drawer.count() === 0, "Escape must close drawer");
assert(await firstTrigger.evaluate(el => el === document.activeElement), "Focus must return to SECTION_OPEN trigger");

await page.setViewportSize({ width: 1366, height: 900 });
await page.waitForTimeout(80);
const cards1366 = await cardRects();
assert(cards1366.slice(0,3).every(c => near(c.y, cards1366[0].y)), "1366 KPI 1-3 must share first row");
assert(cards1366.slice(3,6).every(c => near(c.y, cards1366[3].y)), "1366 KPI 4-6 must share second row");
assert(cards1366[3].y > cards1366[0].y, "1366 KPI second row missing");
assert(cards1366.slice(0,6).every(c => near(c.width, cards1366[0].width)), "1366 KPI widths must match");
const metrics1366 = await page.locator(".workspace-slot").evaluate(el => ({clientWidth:el.clientWidth,scrollWidth:el.scrollWidth}));
assert(metrics1366.scrollWidth >= 1280, `1366 dashboard min width must be >=1280: ${JSON.stringify(metrics1366)}`);
await page.screenshot({ path: `${outDir}/vis01-1366-top.png`, fullPage: false });

await page.setViewportSize({ width: 1200, height: 800 });
await page.waitForTimeout(80);
const metrics1200 = await page.locator(".workspace-slot").evaluate(el => ({clientWidth:el.clientWidth,scrollWidth:el.scrollWidth}));
assert(metrics1200.scrollWidth >= 1280 && metrics1200.scrollWidth > metrics1200.clientWidth, `1200 must use horizontal scroll/min-width: ${JSON.stringify(metrics1200)}`);
const cards1200 = await cardRects();
assert(cards1200.slice(0,3).every(c => near(c.y, cards1200[0].y)) && cards1200.slice(3,6).every(c => near(c.y, cards1200[3].y)), "Below 1280 must retain 3+3 desktop layout, not mobile stack");
await page.screenshot({ path: `${outDir}/vis01-1200-minwidth.png`, fullPage: false });

const result = {
  result: "PASS",
  implementation: "VIS-01",
  brand: { source: logoSource, natural: logoNatural, rendered: logoRect, recolored: false },
  localeSwitching: {
    locales: ["zh-TW", "zh-CN", "en"],
    brandAssetPreserved: true,
    fixedTermsPreserved: ["AI", "QA"],
    businessRequestsDuringSwitch: 0,
  },
  shell,
  quickValues,
  sections: 14,
  controls: 14,
  cards1440,
  cards1366,
  cards1200,
  workspaceMetrics1440,
  metrics1366,
  metrics1200,
  drawerRect,
  dataRequestsAfterDrawerOpen: dataRequests,
};
await fs.writeFile(`${outDir}/vis01-validation.json`, JSON.stringify(result, null, 2));
console.log(JSON.stringify(result, null, 2));
await browser.close();
