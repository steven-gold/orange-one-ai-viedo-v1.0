import { chromium } from "playwright";
import fs from "node:fs/promises";

const outDir = "artifacts/vis00";
await fs.mkdir(outDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
await page.goto("http://127.0.0.1:3000", { waitUntil: "networkidle" });

const round = (n) => Math.round(n * 10) / 10;
const near = (actual, expected, tolerance = 0.6) => Math.abs(actual - expected) <= tolerance;
const assert = (condition, message) => { if (!condition) throw new Error(message); };

async function rect(selector) {
  const r = await page.locator(selector).boundingBox();
  if (!r) throw new Error(`Missing rect: ${selector}`);
  return Object.fromEntries(Object.entries(r).map(([k,v]) => [k, round(v)]));
}

const header = await rect(".global-header");
const sidebarCollapsed = await rect(".global-sidebar");
const workspaceCollapsed = await rect(".workspace-slot");
const navCount = await page.locator(".nav-item").count();
const surfaceOpacityCollapsed = Number(await page.locator(".sidebar-surface").evaluate(el => getComputedStyle(el).opacity));
const labelOpacitiesCollapsed = await page.locator(".nav-label").evaluateAll(els => els.map(el => Number(getComputedStyle(el).opacity)));
const bodyOverflow = await page.evaluate(() => ({ w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight }));

assert(near(header.height, 58), `Header height ${header.height} != 58`);
assert(near(header.x, 0) && near(header.y, 0), `Header origin invalid ${JSON.stringify(header)}`);
assert(near(sidebarCollapsed.x, 0) && near(sidebarCollapsed.y, 58), `Collapsed sidebar origin invalid ${JSON.stringify(sidebarCollapsed)}`);
assert(near(sidebarCollapsed.width, 64), `Collapsed sidebar width ${sidebarCollapsed.width} != 64`);
assert(near(workspaceCollapsed.x, 78) && near(workspaceCollapsed.y, 68), `Workspace origin invalid ${JSON.stringify(workspaceCollapsed)}`);
assert(near(workspaceCollapsed.x + workspaceCollapsed.width, 1424), `Workspace right inset invalid ${JSON.stringify(workspaceCollapsed)}`);
assert(near(workspaceCollapsed.y + workspaceCollapsed.height, 884), `Workspace bottom inset invalid ${JSON.stringify(workspaceCollapsed)}`);
assert(navCount === 8, `Nav count ${navCount} != 8`);
assert(surfaceOpacityCollapsed === 0, `Collapsed sidebar surface opacity ${surfaceOpacityCollapsed} != 0`);
assert(labelOpacitiesCollapsed.every(v => v === 0), `Collapsed labels visible: ${labelOpacitiesCollapsed.join(",")}`);
assert(bodyOverflow.w === 1440 && bodyOverflow.h === 900, `Unexpected document overflow ${JSON.stringify(bodyOverflow)}`);

const navBoxes = await page.locator(".nav-item").evaluateAll(els => els.map(el => {
  const r = el.getBoundingClientRect();
  return { x:r.x, y:r.y, width:r.width, height:r.height, bottom:r.bottom };
}));
assert(navBoxes.every(r => near(r.width,44) && near(r.height,44)), `Collapsed nav hit target mismatch: ${JSON.stringify(navBoxes)}`);
assert(Math.max(...navBoxes.map(r => r.bottom)) < 900, "Navigation clips viewport bottom");

await page.screenshot({ path: `${outDir}/vis00-collapsed-1440x900.png`, fullPage: true });

await page.locator(".global-sidebar").hover();
await page.waitForTimeout(180);
const sidebarExpanded = await rect(".global-sidebar");
const workspaceExpanded = await rect(".workspace-slot");
const surfaceOpacityExpanded = Number(await page.locator(".sidebar-surface").evaluate(el => getComputedStyle(el).opacity));
const labelOpacitiesExpanded = await page.locator(".nav-label").evaluateAll(els => els.map(el => Number(getComputedStyle(el).opacity)));
assert(near(sidebarExpanded.width, 221), `Expanded sidebar width ${sidebarExpanded.width} != 221`);
assert(near(workspaceExpanded.x, 78) && near(workspaceExpanded.width, workspaceCollapsed.width), `Workspace reflow detected: ${JSON.stringify({workspaceCollapsed,workspaceExpanded})}`);
assert(surfaceOpacityExpanded > 0.99, `Expanded sidebar surface opacity ${surfaceOpacityExpanded} not visible`);
assert(labelOpacitiesExpanded.every(v => v > 0.99), `Expanded labels not visible: ${labelOpacitiesExpanded.join(",")}`);
await page.screenshot({ path: `${outDir}/vis00-expanded-1440x900.png`, fullPage: true });

await page.mouse.move(900, 500);
await page.waitForTimeout(250);
const sidebarAfterLeave = await rect(".global-sidebar");
assert(near(sidebarAfterLeave.width, 64), `Pointerleave did not collapse: ${sidebarAfterLeave.width}`);

await page.locator(".nav-item").first().focus();
await page.waitForTimeout(30);
const sidebarFocusExpanded = await rect(".global-sidebar");
assert(near(sidebarFocusExpanded.width, 221), `Focusin did not expand: ${sidebarFocusExpanded.width}`);

const result = {
  result: "PASS",
  viewport: "1440x900",
  header,
  sidebarCollapsed,
  sidebarExpanded,
  workspaceCollapsed,
  workspaceExpanded,
  navCount,
  navBoxes,
  surfaceOpacityCollapsed,
  surfaceOpacityExpanded,
  bodyOverflow,
};
await fs.writeFile(`${outDir}/vis00-geometry.json`, JSON.stringify(result, null, 2));
console.log(JSON.stringify(result, null, 2));
await browser.close();
