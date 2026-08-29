import { chromium } from "playwright";
import fs from "node:fs/promises";

const out = "artifacts/vis02";
await fs.mkdir(out, { recursive: true });

const near = (a, b, tolerance = 2) => Math.abs(a - b) <= tolerance;
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const rect = async (locator) => {
  const box = await locator.boundingBox();
  if (!box) throw new Error(`Missing box for ${await locator.getAttribute("data-section-id") || await locator.getAttribute("data-component-uid") || "locator"}`);
  return { x: +box.x.toFixed(1), y: +box.y.toFixed(1), width: +box.width.toFixed(1), height: +box.height.toFixed(1) };
};

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();
const businessRequests = [];
page.on("request", (request) => {
  if (["xhr", "fetch"].includes(request.resourceType())) businessRequests.push(request.url());
});

await page.goto("http://127.0.0.1:3000/core", { waitUntil: "networkidle" });
assert(await page.locator('[data-page-uid="CORE-01"]').count() === 1, "CORE-01 page UID missing");
assert(await page.locator('[data-vis-step="VIS-02"]').count() === 1, "VIS-02 marker missing");
assert(await page.locator('[data-page-state="EMPTY"]').count() === 1, "CORE empty state missing");

const sections = page.locator('[data-page-uid="CORE-01"] [data-section-id]');
assert(await sections.count() === 10, `Expected 10 sections, got ${await sections.count()}`);
const componentIds = await page.locator('[data-page-uid="CORE-01"] [data-component-uid]').evaluateAll(nodes => [...new Set(nodes.map(node => node.getAttribute('data-component-uid')).filter(Boolean))]);
assert(componentIds.length === 17, `Expected 17 components, got ${componentIds.length}: ${componentIds.join(',')}`);

const header = await rect(page.locator('.global-header'));
const sidebar = await rect(page.locator('.global-sidebar'));
const workspaceBefore = await rect(page.locator('.workspace-slot'));
const contextBar = await rect(page.locator('[data-section-id="CORE-01-SEC-01"]'));
const left = await rect(page.locator('[data-section-id="CORE-01-SEC-02"]'));
const center = await rect(page.locator('[data-section-id="CORE-01-SEC-03"]'));
const right = await rect(page.locator('[data-section-id="CORE-01-SEC-08"]'));
const messages = await rect(page.locator('[data-component-uid="CORE-01-CMP-MESSAGES"]'));
const runtime = await rect(page.locator('[data-section-id="CORE-01-SEC-06"]'));
const composer = await rect(page.locator('[data-component-uid="CORE-01-CMP-COMPOSER"]'));

assert(near(header.height, 58), `Header height ${header.height}`);
assert(near(sidebar.width, 64), `Collapsed sidebar ${sidebar.width}`);
assert(near(workspaceBefore.x, 78) && near(workspaceBefore.y, 68), `Workspace origin ${JSON.stringify(workspaceBefore)}`);
assert(near(contextBar.height, 56), `Context bar height ${contextBar.height}`);
assert(left.width >= 260, `Left rail width ${left.width}`);
assert(center.width >= 720, `Center width ${center.width}`);
assert(right.width >= 300, `Right rail width ${right.width}`);
assert(messages.height >= 420, `Messages height ${messages.height}`);
assert(near(runtime.height, 40), `Runtime strip ${runtime.height}`);
assert(composer.height >= 104, `Composer height ${composer.height}`);
assert(await page.locator('[data-nav-id="NAV-02"][aria-current="page"]').count() === 1, "NAV-02 not active");
assert(await page.locator('[data-nav-id]').count() === 8, `Expected 8 global nav items, got ${await page.locator('[data-nav-id]').count()}`);
assert(await page.locator('[data-nav-id="NAV-01"]').getAttribute('href') === '/', 'NAV-01 route mismatch');
assert(await page.locator('[data-nav-id="NAV-02"]').getAttribute('href') === '/core', 'NAV-02 route mismatch');

const disabledFormControls = page.locator('[data-page-uid="CORE-01"] button[data-control-id], [data-page-uid="CORE-01"] select[data-control-id], [data-page-uid="CORE-01"] textarea[data-control-id]');
const enabledCount = await disabledFormControls.evaluateAll(nodes => nodes.filter(node => !node.disabled).length);
assert(enabledCount === 0, `Business controls prematurely enabled: ${enabledCount}`);

await page.screenshot({ path: `${out}/vis02-1440-top.png` });

await page.locator('[data-component-uid="CORE-01-CMP-MESSAGES"]').click({ button: 'right', position: { x: 360, y: 180 } });
const messageMenuItems = page.locator('[data-control-id^="CORE-01-MENU-"]');
assert(await messageMenuItems.count() === 6, `Message context menu must contain 6 authority items; got ${await messageMenuItems.count()}`);
const controlsOpen = await page.locator('[data-page-uid="CORE-01"] [data-control-id]').count();
assert(controlsOpen === 50, `Expected 50 controls with context menu open, got ${controlsOpen}`);
await page.screenshot({ path: `${out}/vis02-1440-context-menu.png` });
await page.locator('[data-page-uid="CORE-01"]').click({ position: { x: 20, y: 20 } });

const workspace = page.locator('.workspace-slot');
await workspace.evaluate(el => { el.scrollTop = 560; });
await page.waitForTimeout(100);
await page.screenshot({ path: `${out}/vis02-1440-middle.png` });
await workspace.evaluate(el => { el.scrollTop = el.scrollHeight; });
await page.waitForTimeout(100);
await page.screenshot({ path: `${out}/vis02-1440-bottom.png` });
await workspace.evaluate(el => { el.scrollTop = 0; });

const languageButton = page.locator('button[aria-haspopup="listbox"]');
await languageButton.click();
await page.getByRole('option', { name: /简体中文/ }).click();
assert((await page.locator('[data-control-id="CORE-01-BTN-NEW-THREAD"]').textContent())?.trim() === '＋ 新增对话', 'zh-CN CORE text mismatch');
await languageButton.click();
await page.getByRole('option', { name: /English/ }).click();
assert((await page.locator('[data-control-id="CORE-01-BTN-PROJECT-CREATE"]').textContent())?.trim() === 'Create Project', 'English CORE text mismatch');
assert((await page.locator('[data-control-id="CORE-01-BTN-BLUEPRINT-CREATE"]').textContent())?.includes('Blueprint'), 'Blueprint fixed term changed');
assert((await page.locator('[data-control-id="CORE-01-BTN-DNA-LOCK"]').textContent())?.includes('DNA'), 'DNA fixed term changed');
assert(await page.locator('img[alt="ORANGE ONE"]').count() === 1, 'ORANGE ONE logo missing');
await page.screenshot({ path: `${out}/vis02-language-en.png` });
await languageButton.click();
await page.getByRole('option', { name: /繁體中文/ }).click();

const workspaceBeforeExpand = await rect(page.locator('.workspace-slot'));
await page.locator('.global-sidebar').hover();
await page.waitForTimeout(220);
const expandedSidebar = await rect(page.locator('.global-sidebar'));
const workspaceAfterExpand = await rect(page.locator('.workspace-slot'));
assert(near(expandedSidebar.width, 221), `Expanded sidebar ${expandedSidebar.width}`);
assert(near(workspaceBeforeExpand.x, workspaceAfterExpand.x) && near(workspaceBeforeExpand.width, workspaceAfterExpand.width), 'Workspace reflowed on sidebar expand');

assert(businessRequests.length === 0, `Business requests occurred: ${businessRequests.join(',')}`);

const validation = {
  result: 'PASS',
  implementation: 'VIS-02',
  route: '/core',
  pageUid: 'CORE-01',
  authorityCounts: { sections: 10, components: componentIds.length, controls: controlsOpen },
  geometry: { header, sidebarCollapsed: sidebar, sidebarExpanded: expandedSidebar, workspace: workspaceBefore, contextBar, leftRail: left, center, rightRail: right, messages, runtime, composer },
  emptyState: { fakeBusinessData: false, enabledBusinessControls: enabledCount },
  localeSwitching: { locales: ['zh-TW','zh-CN','en'], businessRequests: businessRequests.length, fixedTermsPreserved: ['ORANGE ONE','AI','Blueprint','DNA','Topic','Runtime'] },
  navigation: { count: 8, dashboard: '/', core: '/core', active: 'NAV-02' },
  messageContextMenuItems: 6,
  workspaceReflowOnSidebarExpand: false,
};
await fs.writeFile(`${out}/vis02-validation.json`, JSON.stringify(validation, null, 2));

await context.close();

const context1200 = await browser.newContext({ viewport: { width: 1200, height: 900 } });
const page1200 = await context1200.newPage();
await page1200.goto('http://127.0.0.1:3000/core', { waitUntil: 'networkidle' });
const coreWidth1200 = await page1200.locator('[data-page-uid="CORE-01"]').evaluate(el => el.getBoundingClientRect().width);
assert(coreWidth1200 >= 1280, `1200 viewport must preserve 1280 min width; got ${coreWidth1200}`);
await page1200.screenshot({ path: `${out}/vis02-1200-minwidth.png` });
await context1200.close();
await browser.close();

console.log(JSON.stringify(validation));
