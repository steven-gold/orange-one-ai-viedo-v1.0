import { chromium } from "playwright";
import fs from "node:fs/promises";

const out = "artifacts/vis03";
await fs.mkdir(out, { recursive: true });
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const near = (a,b,t=2) => Math.abs(a-b) <= t;
const rect = async locator => {
  const box = await locator.boundingBox();
  if (!box) throw new Error("Missing geometry target");
  return { x:+box.x.toFixed(1), y:+box.y.toFixed(1), width:+box.width.toFixed(1), height:+box.height.toFixed(1) };
};

const browser = await chromium.launch({ headless:true });
const context = await browser.newContext({ viewport:{ width:1440, height:900 } });
const page = await context.newPage();
const businessRequests = [];
page.on("request", request => { if (["xhr","fetch"].includes(request.resourceType())) businessRequests.push(request.url()); });
await page.goto("http://127.0.0.1:3000/assets", { waitUntil:"networkidle" });

const root = page.locator('[data-page-uid="ASSET-01"]');
assert(await root.count() === 1, "ASSET-01 root missing");
assert(await root.getAttribute("data-vis-step") === "VIS-03", "VIS-03 marker missing");
assert(await root.getAttribute("data-page-state") === "EMPTY", "ASSET empty state missing");
assert(await root.getAttribute("data-registry-valid") === "true", "85-control registry invalid");
assert(await root.getAttribute("data-authority-controls") === "85", "Authority control count marker mismatch");

const sections = root.locator('[data-section-id]');
const components = await root.locator('[data-component-uid]').evaluateAll(nodes => [...new Set(nodes.map(n=>n.getAttribute('data-component-uid')).filter(Boolean))]);
const visibleControls = root.locator('[data-control-id]');
assert(await sections.count() === 10, `Expected 10 sections, got ${await sections.count()}`);
assert(components.length === 16, `Expected 16 components, got ${components.length}: ${components.join(',')}`);
assert(await visibleControls.count() === 67, `Expected 67 empty-state visible controls, got ${await visibleControls.count()}`);
assert(await root.locator('[data-section-id="ASSET-01-SEC-06"] [data-control-id]').count() === 0, "Correction controls rendered before Modify");
assert(await root.locator('[data-section-id="ASSET-01-SEC-07"] [data-control-id]').count() === 0, "Layer/Patch controls rendered without image-compatible context");
const conditionalDeclared = await root.locator('[data-conditional-controls]').evaluateAll(nodes => nodes.reduce((sum,n)=>sum + Number(n.getAttribute('data-conditional-controls') || 0),0));
assert(conditionalDeclared === 18, `Expected 18 conditional controls, got ${conditionalDeclared}`);
assert(67 + conditionalDeclared === 85, "Visible + conditional controls do not close to 85");

const disabledInteractive = root.locator('button[data-control-id], select[data-control-id], input[data-control-id], textarea[data-control-id]');
const enabledCount = await disabledInteractive.evaluateAll(nodes => nodes.filter(n => !n.disabled).length);
assert(enabledCount === 0, `Business controls prematurely enabled: ${enabledCount}`);

const header = await rect(page.locator('.global-header'));
const sidebar = await rect(page.locator('.global-sidebar'));
const workspace = await rect(page.locator('.workspace-slot'));
const contextBar = await rect(root.locator('[data-section-id="ASSET-01-SEC-01"]'));
const left = await rect(root.locator('[data-section-id="ASSET-01-SEC-02"]'));
const center = await rect(root.locator('[data-section-id="ASSET-01-SEC-03"]'));
const right = await rect(root.locator('[data-section-id="ASSET-01-SEC-09"]'));
const preview = await rect(root.locator('[data-section-id="ASSET-01-SEC-04"]'));
assert(near(header.height,58), `Header height ${header.height}`);
assert(near(sidebar.width,64), `Sidebar width ${sidebar.width}`);
assert(near(workspace.x,78) && near(workspace.y,68), `Workspace origin ${JSON.stringify(workspace)}`);
assert(contextBar.height >= 56, `Context height ${contextBar.height}`);
assert(left.width >= 260, `Left width ${left.width}`);
assert(center.width >= 720, `Center width ${center.width}`);
assert(right.width >= 280, `Right width ${right.width}`);
assert(preview.height >= 500, `Preview height ${preview.height}`);
assert(await page.locator('[data-nav-id="NAV-03"][aria-current="page"]').count() === 1, "NAV-03 not active");
assert(await page.locator('[data-nav-id]').count() === 8, "Global nav count changed");
assert(await page.locator('[data-nav-id="NAV-03"]').getAttribute('href') === '/assets', "NAV-03 route mismatch");

await page.screenshot({ path:`${out}/vis03-1440-top.png` });
const workspaceNode = page.locator('.workspace-slot');
await workspaceNode.evaluate(el => { el.scrollTop = 650; });
await page.waitForTimeout(100);
await page.screenshot({ path:`${out}/vis03-1440-middle.png` });
await workspaceNode.evaluate(el => { el.scrollTop = el.scrollHeight; });
await page.waitForTimeout(100);
await page.screenshot({ path:`${out}/vis03-1440-bottom.png` });
await workspaceNode.evaluate(el => { el.scrollTop = 0; });

const languageButton = page.locator('button[aria-haspopup="listbox"]');
await languageButton.click();
await page.getByRole('option',{name:/简体中文/}).click();
assert((await root.locator('[data-control-id="ASSET-01-BTN-EXECUTE"]').textContent())?.trim() === '执行', "zh-CN execute mismatch");
await languageButton.click();
await page.getByRole('option',{name:/English/}).click();
assert((await root.locator('[data-control-id="ASSET-01-BTN-EXECUTE"]').textContent())?.trim() === 'Execute', "English execute mismatch");
assert((await root.locator('[data-section-id="ASSET-01-SEC-04"] h2').textContent())?.includes('Preview / Compare'), "English preview heading mismatch");
assert((await root.locator('[data-control-id="ASSET-01-FLD-PROVIDER"] span').textContent())?.includes('Provider / Model'), "Provider/Model fixed term mismatch");
assert(await page.locator('img[alt="ORANGE ONE"]').count() === 1, "ORANGE ONE logo missing");
await page.screenshot({ path:`${out}/vis03-language-en.png` });
await languageButton.click();
await page.getByRole('option',{name:/繁體中文/}).click();

const workspaceBefore = await rect(page.locator('.workspace-slot'));
await page.locator('.global-sidebar').hover();
await page.waitForTimeout(220);
const sidebarExpanded = await rect(page.locator('.global-sidebar'));
const workspaceAfter = await rect(page.locator('.workspace-slot'));
assert(near(sidebarExpanded.width,221), `Expanded sidebar ${sidebarExpanded.width}`);
assert(near(workspaceBefore.x,workspaceAfter.x) && near(workspaceBefore.width,workspaceAfter.width), "Workspace reflowed on sidebar expand");
assert(businessRequests.length === 0, `Business requests occurred: ${businessRequests.join(',')}`);

const validation = {
  result:"PASS", implementation:"VIS-03", route:"/assets", pageUid:"ASSET-01",
  authorityCounts:{ sections:10, components:16, controls:85, visibleEmptyStateControls:67, conditionalControls:18 },
  geometry:{ header, sidebarCollapsed:sidebar, sidebarExpanded, workspace, contextBar, left, center, right, preview },
  state:{ fakeBusinessData:false, enabledBusinessControls:enabledCount, correctionControlsRendered:false, layerPatchControlsRendered:false },
  localeSwitching:{ locales:["zh-TW","zh-CN","en"], businessRequests:businessRequests.length },
  navigation:{ count:8, active:"NAV-03", route:"/assets" },
  workspaceReflowOnSidebarExpand:false
};
await fs.writeFile(`${out}/vis03-validation.json`, JSON.stringify(validation,null,2));
await context.close();

const context1200 = await browser.newContext({ viewport:{ width:1200,height:900 } });
const page1200 = await context1200.newPage();
await page1200.goto('http://127.0.0.1:3000/assets',{waitUntil:'networkidle'});
const width1200 = await page1200.locator('[data-page-uid="ASSET-01"]').evaluate(el=>el.getBoundingClientRect().width);
assert(width1200 >= 1280, `1200 viewport must preserve 1280 min width; got ${width1200}`);
await page1200.screenshot({path:`${out}/vis03-1200-minwidth.png`});
await context1200.close();
await browser.close();
console.log(JSON.stringify(validation));
