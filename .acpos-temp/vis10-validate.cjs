const { chromium } = require('playwright');
const fs = require('fs');
const assert = (v, m) => { if (!v) throw new Error(m); };
const exact = (a,b,m) => assert(JSON.stringify(a) === JSON.stringify(b), `${m}: ${JSON.stringify(a)} != ${JSON.stringify(b)}`);
const sameSet = (a,b,m) => {
  assert(a.length === b.length, `${m} count: ${a.length} != ${b.length}`);
  assert(new Set(a).size === a.length, `${m} duplicate UID: ${JSON.stringify(a)}`);
  exact([...a].sort(), [...b].sort(), m);
};
const FRONT = ['NAV-01','NAV-02','NAV-03','NAV-04','NAV-05','NAV-06','NAV-07','NAV-08','NAV-09'];
const ADMIN = ['ADMIN-NAV-01','ADMIN-NAV-02','ADMIN-NAV-03','ADMIN-NAV-04','ADMIN-NAV-05','ADMIN-NAV-06','ADMIN-NAV-07','ADMIN-NAV-08','ADMIN-NAV-09'];
const SECTIONS = ['SEC-ADMIN-SYS-01-SYSTEM-CONTEXT','SEC-ADMIN-SYS-01-CONVERSATION','SEC-ADMIN-SYS-01-CANDIDATE-CHANGE','SEC-ADMIN-SYS-01-SOURCE-REFS','SEC-ADMIN-SYS-01-IMPACT-PREVIEW','SEC-ADMIN-SYS-01-AUDIT','SEC-ADMIN-SYS-01-ACTION-DOCK','SEC-ADMIN-SYS-01-EXECUTION-PANEL'];
const CONTROLS = ['SYS-01-BTN-SINGLE-AI','SYS-01-BTN-MULTI-AI','SYS-01-BTN-COUNCIL-DISCUSSION','SYS-01-BTN-COUNCIL-PARALLEL','SYS-01-BTN-CANDIDATE-CREATE','SYS-01-BTN-CR-CREATE','SYS-01-BTN-NAV-OPEN','SYS-01-BTN-SANDBOX-TEST'];
(async()=>{
  const browser = await chromium.launch({headless:true});
  const results = { route:'/admin/system', frontNav:[], adminNav:[], sections:SECTIONS, controls:CONTROLS, viewports:{}, xhr:0 };
  for (const width of [1600,1440,1200]) {
    const page = await browser.newPage({viewport:{width,height:900}});
    let requests = 0;
    page.on('request', req => { if (['xhr','fetch'].includes(req.resourceType())) requests++; });
    const res = await page.goto('http://127.0.0.1:3000/admin/system',{waitUntil:'networkidle'});
    assert(res && res.ok(), `route failed ${width}`);
    assert(await page.locator('[data-page-uid="admin:SYS-01"]').count() === 1, 'page uid missing');
    exact(await page.locator('[data-section-id]').evaluateAll(es=>es.map(e=>e.getAttribute('data-section-id'))), SECTIONS, 'section registry');
    sameSet(await page.locator('[data-control-id]').evaluateAll(es=>es.map(e=>e.getAttribute('data-control-id'))), CONTROLS, 'control registry');
    const adminNav = await page.locator('[data-nav-id]').evaluateAll(es=>es.map(e=>e.getAttribute('data-nav-id')));
    exact(adminNav, ADMIN, `admin nav ${width}`);
    assert(await page.locator('[data-nav-id="ADMIN-NAV-01"][aria-current="page"]').count() === 1, 'active admin nav missing');
    const g = await page.evaluate(()=>({
      workspaceX: Math.round(document.querySelector('.workspace-slot').getBoundingClientRect().x),
      sidebar: Math.round(document.querySelector('.global-sidebar').getBoundingClientRect().width),
      workspaceClient: document.querySelector('.workspace-slot').clientWidth,
      workspaceScroll: document.querySelector('.workspace-slot').scrollWidth,
      pageWidth: Math.round(document.querySelector('[data-page-uid="admin:SYS-01"]').getBoundingClientRect().width)
    }));
    if (width >= 1440) assert(g.workspaceScroll === g.workspaceClient, `unexpected workspace horizontal overflow ${width}: ${JSON.stringify(g)}`);
    if (width === 1200) assert(g.workspaceScroll >= 1280 && g.workspaceScroll > g.workspaceClient, `1200 minwidth rule failed: ${JSON.stringify(g)}`);
    assert(g.workspaceX === 78, `workspace x ${width}`);
    await page.locator('.global-sidebar').hover();
    await page.waitForTimeout(160);
    const expanded = await page.evaluate(()=>({sidebar:Math.round(document.querySelector('.global-sidebar').getBoundingClientRect().width),workspaceX:Math.round(document.querySelector('.workspace-slot').getBoundingClientRect().x)}));
    assert(expanded.sidebar === 221 && expanded.workspaceX === 78, `overlay rule ${width}: ${JSON.stringify(expanded)}`);
    results.viewports[width] = {...g, expandedSidebar:expanded.sidebar};
    results.xhr += requests;
    await page.screenshot({path:`docs/construction/evidence/VIS-10/vis10-${width}-top.png`,fullPage:false});
    if (width === 1440) {
      await page.locator('[data-section-id="SEC-ADMIN-SYS-01-EXECUTION-PANEL"]').scrollIntoViewIfNeeded();
      await page.screenshot({path:'docs/construction/evidence/VIS-10/vis10-1440-bottom.png',fullPage:false});
    }
    await page.close();
  }
  const front = await browser.newPage({viewport:{width:1440,height:900}});
  await front.goto('http://127.0.0.1:3000/',{waitUntil:'networkidle'});
  results.frontNav = await front.locator('[data-nav-id]').evaluateAll(es=>es.map(e=>e.getAttribute('data-nav-id')));
  exact(results.frontNav, FRONT, 'front nav preserved');
  await front.locator('.account-button').click();
  assert(await front.locator('.account-popover-link[href="/admin/system"]').count() === 1, 'frontend admin entry missing');
  await front.screenshot({path:'docs/construction/evidence/VIS-10/vis10-front-admin-entry.png',fullPage:false});
  await front.close();
  const admin = await browser.newPage({viewport:{width:1440,height:900}});
  await admin.goto('http://127.0.0.1:3000/admin/system',{waitUntil:'networkidle'});
  results.adminNav = await admin.locator('[data-nav-id]').evaluateAll(es=>es.map(e=>e.getAttribute('data-nav-id')));
  await admin.locator('.account-button').click();
  assert(await admin.locator('.account-popover-link[href="/"]').count() === 1, 'admin front return missing');
  assert(await admin.locator('[data-control-id]:not([disabled])').count() === 0, 'enabled control exists in visual phase');
  assert(await admin.locator('text=Provider / Model').count() === 0, 'provider picker residue');
  assert(await admin.locator('text=Production Deploy').count() === 0, 'production deploy residue');
  await admin.locator('button[aria-label="語言"]').click();
  await admin.getByRole('option',{name:/English/}).click();
  assert(await admin.getByRole('heading',{name:'System Lifecycle AI Workbench'}).count() === 1, 'English locale failed');
  fs.writeFileSync('docs/construction/evidence/VIS-10/vis10-validation.json', JSON.stringify(results,null,2));
  await admin.close();
  await browser.close();
  assert(results.xhr === 0, `business xhr/fetch detected: ${results.xhr}`);
})().catch(e=>{console.error(e);process.exit(1)});
