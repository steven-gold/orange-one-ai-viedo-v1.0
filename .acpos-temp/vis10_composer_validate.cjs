const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch({headless:true});
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  let businessXHR = 0;
  page.on('request', req => {
    if (['xhr','fetch'].includes(req.resourceType())) businessXHR += 1;
  });
  await page.goto('http://127.0.0.1:3000/admin/system', {waitUntil:'networkidle'});

  const base = await page.evaluate(() => {
    const root = document.querySelector('[data-page-uid="admin:SYS-01"]');
    const workspace = document.querySelector('.workspace-slot');
    const sidebar = document.querySelector('.global-sidebar');
    const controls = [...document.querySelectorAll('[data-control-id]')].map(el => el.getAttribute('data-control-id'));
    const sections = [...document.querySelectorAll('[data-section-id]')].map(el => el.getAttribute('data-section-id'));
    const textarea = document.getElementById('SYS-01-INP-MESSAGE');
    const attach = document.getElementById('SYS-01-BTN-ATTACH');
    const send = document.getElementById('SYS-01-BTN-SEND');
    const stop = document.getElementById('SYS-01-BTN-STOP');
    const cs = textarea ? getComputedStyle(textarea) : null;
    return {
      pageUid: root?.getAttribute('data-page-uid'),
      controls,
      sections,
      workspaceX: workspace?.getBoundingClientRect().x,
      workspaceClient: workspace?.clientWidth,
      workspaceScroll: workspace?.scrollWidth,
      pageWidth: root?.scrollWidth,
      sidebarWidth: sidebar?.getBoundingClientRect().width,
      textareaExists: !!textarea,
      textareaDisabled: textarea?.disabled ?? null,
      textareaResize: cs?.resize,
      textareaMinHeight: cs?.minHeight,
      attachDisabled: attach?.disabled ?? null,
      sendDisabled: send?.disabled ?? null,
      stopDisabled: stop?.disabled ?? null,
      adminNavCount: document.querySelectorAll('.global-sidebar [data-nav-id^="ADMIN-NAV-"]').length,
      activeNav: document.querySelector('.global-sidebar [aria-current="page"]')?.getAttribute('data-nav-id')
    };
  });

  const expectedControls = [
    'SYS-01-BTN-SINGLE-AI','SYS-01-BTN-MULTI-AI','SYS-01-BTN-COUNCIL-DISCUSSION','SYS-01-BTN-COUNCIL-PARALLEL',
    'SYS-01-INP-MESSAGE','SYS-01-BTN-ATTACH','SYS-01-BTN-SEND','SYS-01-BTN-STOP',
    'SYS-01-BTN-CANDIDATE-CREATE','SYS-01-BTN-CR-CREATE','SYS-01-BTN-NAV-OPEN','SYS-01-BTN-SANDBOX-TEST'
  ];
  if (base.pageUid !== 'admin:SYS-01') throw new Error('SYS page uid mismatch');
  if (base.sections.length !== 8 || new Set(base.sections).size !== 8) throw new Error(`sections mismatch ${base.sections.length}`);
  if (base.controls.length !== 12 || new Set(base.controls).size !== 12) throw new Error(`controls mismatch ${base.controls.length}`);
  for (const id of expectedControls) if (!base.controls.includes(id)) throw new Error(`missing control ${id}`);
  if (!base.textareaExists || base.textareaDisabled) throw new Error('message textarea must exist and be editable in visual phase');
  if (base.textareaResize !== 'vertical') throw new Error(`textarea resize expected vertical got ${base.textareaResize}`);
  if (!base.attachDisabled || !base.sendDisabled || !base.stopDisabled) throw new Error('business composer buttons must remain disabled in visual phase');
  if (base.adminNavCount !== 9 || base.activeNav !== 'ADMIN-NAV-01') throw new Error('admin navigation regression');
  if (base.workspaceX !== 78 || base.workspaceClient !== base.workspaceScroll) throw new Error(`1440 geometry overflow ${JSON.stringify(base)}`);

  await page.locator('#SYS-01-INP-MESSAGE').fill('local visual draft');
  if ((await page.locator('#SYS-01-INP-MESSAGE').inputValue()) !== 'local visual draft') throw new Error('local draft typing failed');
  await page.screenshot({path:'docs/construction/evidence/VIS-10/vis10-composer-1440-top.png', fullPage:false});

  await page.hover('.global-sidebar');
  await page.waitForTimeout(80);
  const expanded = await page.evaluate(() => ({
    x: document.querySelector('.workspace-slot')?.getBoundingClientRect().x,
    side: document.querySelector('.global-sidebar')?.getBoundingClientRect().width
  }));
  if (expanded.x !== 78 || expanded.side !== 221) throw new Error(`sidebar overlay regression ${JSON.stringify(expanded)}`);
  await page.screenshot({path:'docs/construction/evidence/VIS-10/vis10-composer-1440-expanded.png', fullPage:false});
  await page.mouse.move(700, 400);
  await page.waitForTimeout(260);

  await page.evaluate(() => { const w=document.querySelector('.workspace-slot'); if (w) w.scrollTop = w.scrollHeight; });
  await page.waitForTimeout(80);
  await page.screenshot({path:'docs/construction/evidence/VIS-10/vis10-composer-1440-bottom.png', fullPage:false});

  await page.setViewportSize({width:1600,height:900});
  await page.goto('http://127.0.0.1:3000/admin/system', {waitUntil:'networkidle'});
  const g1600 = await page.evaluate(() => { const w=document.querySelector('.workspace-slot'); const p=document.querySelector('[data-page-uid="admin:SYS-01"]'); return {client:w?.clientWidth,scroll:w?.scrollWidth,page:p?.scrollWidth,x:w?.getBoundingClientRect().x}; });
  if (g1600.client !== g1600.scroll || g1600.x !== 78) throw new Error(`1600 overflow ${JSON.stringify(g1600)}`);

  await page.setViewportSize({width:1200,height:900});
  await page.goto('http://127.0.0.1:3000/admin/system', {waitUntil:'networkidle'});
  const g1200 = await page.evaluate(() => { const w=document.querySelector('.workspace-slot'); const p=document.querySelector('[data-page-uid="admin:SYS-01"]'); return {client:w?.clientWidth,scroll:w?.scrollWidth,page:p?.scrollWidth,x:w?.getBoundingClientRect().x}; });
  if (!(g1200.scroll > g1200.client && g1200.page >= 1280) || g1200.x !== 78) throw new Error(`1200 min width behavior ${JSON.stringify(g1200)}`);

  // Shared shell regression across all completed front routes and IAM.
  const routes = ['/', '/core', '/assets', '/video', '/edit', '/qa', '/database', '/strategy', '/info', '/admin/accounts'];
  for (const route of routes) {
    await page.setViewportSize({width:1440,height:900});
    await page.goto(`http://127.0.0.1:3000${route}`, {waitUntil:'networkidle'});
    const shell = await page.evaluate(() => {
      const w=document.querySelector('.workspace-slot');
      const navs=[...document.querySelectorAll('.global-sidebar [data-nav-id]')];
      return {x:w?.getBoundingClientRect().x,count:navs.length,active:navs.filter(x=>x.getAttribute('aria-current')==='page').length};
    });
    if (shell.x !== 78 || shell.count !== 9 || shell.active !== 1) throw new Error(`shell regression ${route} ${JSON.stringify(shell)}`);
  }

  fs.writeFileSync('docs/construction/evidence/VIS-10/vis10-composer-validation.json', JSON.stringify({
    route:'/admin/system', sections:8, controls:12, composerControls:4,
    textareaResizable:true, textareaVisualPhaseEditable:true,
    attachSendStopVisualPhaseDisabled:true,
    geometry1440:base, expanded, viewport1600:g1600, viewport1200:g1200,
    sharedShellRoutesValidated:routes.length, businessXHR
  }, null, 2));
  if (businessXHR !== 0) throw new Error(`business XHR/fetch expected 0 got ${businessXHR}`);
  await browser.close();
  console.log('VIS-10 composer remediation Chromium PASS');
})().catch(err => { console.error(err); process.exit(1); });
