import { spawn } from "node:child_process";
import { chromium } from "playwright";

const port = process.env.ACPOS_BROWSER_E2E_PORT ?? "3500";
const base = `http://127.0.0.1:${port}`;
const baseOrigin = new URL(base).origin;

function isExpectedUnauthenticatedResponse(response) {
  const url = new URL(response.url());
  if (url.origin !== baseOrigin) return false;
  if (url.pathname === "/v1/identity/session") return response.status() === 401;
  if (url.pathname === "/v1/dashboard/read-model") return response.status() === 403;
  if (url.pathname.startsWith("/v1/ui-projections/")) return [403, 503].includes(response.status());
  return false;
}

const routes = [
  ["/", "workspace:WB-01"], ["/core", "CORE-01"], ["/assets", "ASSET-01"], ["/video", "VIDEO-01"],
  ["/edit", "EDIT-01"], ["/qa", "QA-01"], ["/database", "admin:DB-01"], ["/strategy", "workspace:STR-01"],
  ["/info", "workspace:INFO-01"], ["/admin/system", "admin:SYS-01"], ["/admin/accounts", "admin:IAM-01"],
  ["/admin/dev", "admin:DEV-01"], ["/admin/social", "admin:SOC-01"], ["/admin/erp", "admin:ERP-01"],
  ["/admin/aiapi", "admin:AIAPI-01"], ["/admin/qa-criteria", "admin:SG-02"], ["/admin/strategy", "admin:STR-01"],
  ["/admin/knowledge", "admin:KB-01"],
];

const THREE_COLUMN_TOPOLOGY_UIDS = new Set(["CORE-01","ASSET-01","VIDEO-01","EDIT-01","QA-01"]);


const server = spawn(process.execPath, ["node_modules/next/dist/bin/next", "start", "-p", port], {
  stdio: ["ignore", "inherit", "inherit"],
  env: { ...process.env, NODE_ENV: "production", NEXT_PUBLIC_ACPOS_RUNTIME_MODE: "CONTROLLED_TEST" },
});

async function waitForServer() {
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${base}/health`, { cache: "no-store" });
      if (response.ok) return;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error("BROWSER_SERVER_START_TIMEOUT");
}

async function requireActionable(locator, reason, timeout = 5_000) {
  try {
    await locator.click({ trial: true, timeout });
  } catch {
    throw new Error(reason);
  }
}

async function navigateToCurrentPage(page, route, uid) {
  const response = await page.goto(`${base}${route}`, { waitUntil: "domcontentloaded", timeout: 45_000 });
  if (!response?.ok()) throw new Error(`NAV_${route}_${response?.status()}`);
  const root = page.locator("[data-page-uid]").first();
  await root.waitFor({ state: "attached", timeout: 15_000 });
  const actual = await root.getAttribute("data-page-uid");
  if (actual !== uid) throw new Error(`UID_${route}_${actual}`);
  await page.locator("body").waitFor({ state: "visible", timeout: 15_000 });
  try {
    await page.waitForFunction(
      () => {
        const current = document.querySelector("[data-page-uid]");
        return current?.getAttribute("data-page-state") !== "LOADING";
      },
      { timeout: 15_000 },
    );
  } catch {
    throw new Error(`STUCK_LOADING_${uid}`);
  }
  return root;
}

try {
  await waitForServer();
  const browser = await chromium.launch({ headless: true });
  let cases = 0;
  let interactiveControls = 0;
  let governedControls = 0;
  let safeLocalClicks = 0;
  let strategyFormCases = 0;
  let sgGovernanceCases = 0;
  let iamMutationCases = 0;
  let erpMutationCases = 0;
  let devMutationCases = 0;
  let socMutationCases = 0;
  let aiApiMutationCases = 0;
  let kbMutationCases = 0;
  let i18nCases = 0;
  let shellGeometryCases = 0;
  let visualTopologyCases = 0;
  let sidebarReflowCases = 0;
  try {
    for (const width of [1024, 1280, 1440, 1920]) {
      for (const [route, uid] of routes) {
        const page = await browser.newPage({ viewport: { width, height: 1400 } });
        const errors = [];
        page.on("pageerror", (error) => errors.push(`pageerror:${error.message}`));
        page.on("response", (response) => {
          if (response.status() >= 400 && !isExpectedUnauthenticatedResponse(response)) {
            errors.push(`response:${response.status()}:${new URL(response.url()).pathname}`);
          }
        });
        page.on("console", (message) => {
          if (message.type() === "error" && !/Failed to load resource.*(?:401|403|503)/.test(message.text())) errors.push(`console:${message.text()}`);
        });
        const root = await navigateToCurrentPage(page, route, uid);
        const overflowAudit = await page.evaluate(() => {
          const overflow = document.documentElement.scrollWidth - document.documentElement.clientWidth;
          if (overflow <= 0) return { overflow, offenders: [] };
          const viewportRight = document.documentElement.clientWidth;
          const isClippedByAncestor = (element) => {
            let parent = element.parentElement;
            const rect = element.getBoundingClientRect();
            while (parent && parent !== document.body) {
              const parentRect = parent.getBoundingClientRect();
              const overflowX = getComputedStyle(parent).overflowX;
              if (
                ["auto", "scroll", "hidden", "clip"].includes(overflowX) &&
                rect.right > parentRect.right + 0.5
              ) return true;
              parent = parent.parentElement;
            }
            return false;
          };
          const offenders = [...document.querySelectorAll("body *")]
            .map((node) => {
              const element = /** @type {HTMLElement} */ (node);
              const rect = element.getBoundingClientRect();
              const style = getComputedStyle(element);
              return {
                tag: element.tagName.toLowerCase(),
                id: element.id || "",
                className: typeof element.className === "string" ? element.className : "",
                right: Math.round(rect.right * 100) / 100,
                width: Math.round(rect.width * 100) / 100,
                overflowX: style.overflowX,
                delta: Math.round((rect.right - viewportRight) * 100) / 100,
                clipped: isClippedByAncestor(element),
              };
            })
            .filter((entry) => entry.delta > 0.5 && !entry.clipped)
            .sort((a, b) => b.delta - a.delta)
            .slice(0, 12);
          const root = document.querySelector("[data-page-uid]");
          const chain = [];
          let current = root;
          while (current) {
            const element = /** @type {HTMLElement} */ (current);
            const rect = element.getBoundingClientRect();
            chain.push({
              tag: element.tagName.toLowerCase(),
              className: typeof element.className === "string" ? element.className : "",
              left: Math.round(rect.left * 100) / 100,
              right: Math.round(rect.right * 100) / 100,
              width: Math.round(rect.width * 100) / 100,
              clientWidth: element.clientWidth,
              scrollWidth: element.scrollWidth,
              overflowX: getComputedStyle(element).overflowX,
            });
            current = current.parentElement;
          }
          return { overflow, offenders, chain };
        });
        if (overflowAudit.overflow > 0 && overflowAudit.offenders.length > 0) {
          throw new Error(`OVERFLOW_${uid}_${width}_${overflowAudit.overflow}_OFFENDERS_${JSON.stringify(overflowAudit.offenders)}_CHAIN_${JSON.stringify(overflowAudit.chain)}`);
        }
        const body = (await page.locator("body").textContent()) ?? "";
        if (body.includes('"use client"') || body.includes("function KnowledgeAdminVisual") || body.includes("const CONTROLS")) throw new Error(`SOURCE_RENDER_${uid}`);

        if (width === 1280) {
          try {
            await page.waitForFunction(
              () => {
                const header = document.querySelector(".global-header");
                const sidebar = document.querySelector(".global-sidebar");
                const workspace = document.querySelector(".workspace-slot");
                if (!(header instanceof HTMLElement) || !(sidebar instanceof HTMLElement) || !(workspace instanceof HTMLElement)) return false;
                const h = header.getBoundingClientRect();
                const s = sidebar.getBoundingClientRect();
                const w = workspace.getBoundingClientRect();
                return Math.abs(h.height - 58) <= 1
                  && h.width > 0
                  && Math.abs(s.width - 64) <= 1
                  && Math.abs(s.top - 58) <= 1
                  && Math.abs(w.left - 78) <= 1
                  && Math.abs(w.top - 68) <= 1;
              },
              { timeout: 5_000 },
            );
          } catch {
            throw new Error(`SHELL_GEOMETRY_NOT_STABLE_${uid}`);
          }
          const shellGeometry = await page.evaluate(() => {
            const header = document.querySelector(".global-header");
            const sidebar = document.querySelector(".global-sidebar");
            const workspace = document.querySelector(".workspace-slot");
            if (!(header instanceof HTMLElement) || !(sidebar instanceof HTMLElement) || !(workspace instanceof HTMLElement)) {
              return null;
            }
            const rect = (element) => {
              const value = element.getBoundingClientRect();
              const style = getComputedStyle(element);
              return {
                left: value.left,
                top: value.top,
                right: value.right,
                bottom: value.bottom,
                width: value.width,
                height: value.height,
                position: style.position,
              };
            };
            return { header: rect(header), sidebar: rect(sidebar), workspace: rect(workspace) };
          });
          if (!shellGeometry) throw new Error(`SHELL_GEOMETRY_MISSING_${uid}`);
          const near = (actual, expected) => Math.abs(actual - expected) <= 1;
          if (shellGeometry.header.position !== "fixed" || !near(shellGeometry.header.top, 0) || !near(shellGeometry.header.height, 58)) {
            throw new Error(`SHELL_HEADER_GEOMETRY_${uid}_${JSON.stringify(shellGeometry.header)}`);
          }
          if (shellGeometry.sidebar.position !== "fixed" || !near(shellGeometry.sidebar.left, 0) || !near(shellGeometry.sidebar.top, 58) || !near(shellGeometry.sidebar.width, 64)) {
            throw new Error(`SHELL_SIDEBAR_GEOMETRY_${uid}_${JSON.stringify(shellGeometry.sidebar)}`);
          }
          if (shellGeometry.workspace.position !== "fixed" || !near(shellGeometry.workspace.left, 78) || !near(shellGeometry.workspace.top, 68) || !near(shellGeometry.workspace.right, 1264) || !near(shellGeometry.workspace.bottom, 1384)) {
            throw new Error(`SHELL_WORKSPACE_GEOMETRY_${uid}_${JSON.stringify(shellGeometry.workspace)}`);
          }
          shellGeometryCases += 1;

          if (THREE_COLUMN_TOPOLOGY_UIDS.has(uid)) {
            const topology = await page.evaluate(() => {
              const grid = document.querySelector('[data-layout-grid="workspace-three-column"]');
              if (!(grid instanceof HTMLElement)) return null;
              return ["left","center","right"].map((column) => {
                const element = grid.querySelector(`:scope > [data-layout-column="${column}"]`);
                if (!(element instanceof HTMLElement)) return null;
                const rect = element.getBoundingClientRect();
                return { column, left: rect.left, top: rect.top, width: rect.width, right: rect.right };
              });
            });
            if (!topology || topology.some((entry) => !entry)) throw new Error(`VISUAL_TOPOLOGY_COLUMN_MISSING_${uid}_${JSON.stringify(topology)}`);
            const [left, center, right] = topology;
            const sameRow = Math.abs(left.top - center.top) <= 4 && Math.abs(center.top - right.top) <= 4;
            const ordered = left.left < center.left && center.left < right.left && left.right <= center.left + 1 && center.right <= right.left + 1;
            const centerPriority = center.width > left.width && center.width > right.width;
            if (!sameRow || !ordered || !centerPriority) {
              throw new Error(`VISUAL_TOPOLOGY_INVALID_${uid}_${JSON.stringify(topology)}`);
            }
            visualTopologyCases += 1;
          }

          const collapsedStageSections = {
            "ASSET-01": ["ASSET-01-SEC-06","ASSET-01-SEC-07","ASSET-01-SEC-08","ASSET-01-SEC-10"],
            "VIDEO-01": ["VIDEO-01-SEC-05","VIDEO-01-SEC-06","VIDEO-01-SEC-07","VIDEO-01-SEC-08","VIDEO-01-SEC-09","VIDEO-01-SEC-10"],
            "QA-01": ["QA-01-SEC-07","QA-01-SEC-08","QA-01-SEC-09","QA-01-SEC-10"],
          }[uid];
          if (collapsedStageSections) {
            const visibleUnexpected = await page.evaluate((ids) => ids.filter((id) => {
              const element = document.querySelector(`[data-section-id="${id}"]`);
              if (!(element instanceof HTMLElement)) return false;
              const style = getComputedStyle(element);
              const rect = element.getBoundingClientRect();
              return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
            }), collapsedStageSections);
            if (visibleUnexpected.length) throw new Error(`STAGE_FIRST_LAYER_FLATTENED_${uid}_${visibleUnexpected.join(",")}`);
          }

          if (uid === "EDIT-01") {
            const editLayout = await page.evaluate(() => {
              const pageRoot = document.querySelector('[data-page-uid="EDIT-01"]');
              const preview = document.querySelector('[data-component-uid="EDIT-01-CMP-PREVIEW"]');
              const timeline = document.querySelector('[data-component-uid="EDIT-01-CMP-TIMELINE"]');
              const dock = document.querySelector('[data-current-stage-action-dock="true"]');
              if (!(pageRoot instanceof HTMLElement) || !(preview instanceof HTMLElement) || !(timeline instanceof HTMLElement) || !(dock instanceof HTMLElement)) return null;
              const p = pageRoot.getBoundingClientRect(), v = preview.getBoundingClientRect(), t = timeline.getBoundingClientRect(), d = dock.getBoundingClientRect();
              return {pageHeight:p.height,previewTop:v.top,previewBottom:v.bottom,timelineTop:t.top,timelineBottom:t.bottom,dockTop:d.top,dockBottom:d.bottom,timelineOverflow:getComputedStyle(timeline).overflowY};
            });
            if (!editLayout || editLayout.previewBottom > editLayout.dockTop + 1 || editLayout.timelineTop >= editLayout.dockTop || editLayout.dockBottom > innerHeight + 2) {
              throw new Error(`EDIT_VIEWPORT_LOCK_INVALID_${JSON.stringify(editLayout)}`);
            }
          }

          if (route === "/") {
            const sidebar = page.locator(".global-sidebar");
            const workspace = page.locator(".workspace-slot");
            await sidebar.hover();
            await page.waitForFunction(() => {
              const element = document.querySelector(".workspace-slot");
              return element instanceof HTMLElement && element.getBoundingClientRect().left >= 234;
            }, { timeout: 5_000 });
            const expandedLeft = await workspace.evaluate((element) => element.getBoundingClientRect().left);
            await workspace.hover();
            await page.waitForFunction(() => {
              const element = document.querySelector(".workspace-slot");
              return element instanceof HTMLElement && Math.abs(element.getBoundingClientRect().left - 78) <= 1;
            }, { timeout: 5_000 });
            if (expandedLeft < 234) throw new Error(`SIDEBAR_WORKSPACE_REFLOW_MISSING_${expandedLeft}`);
            sidebarReflowCases += 1;
          }

          const controls = await page.locator('button, a[href], input, select, textarea, [role="button"]').evaluateAll((nodes) =>
            nodes.map((node, index) => {
              const element = /** @type {HTMLElement} */ (node);
              const style = getComputedStyle(element);
              const rect = element.getBoundingClientRect();
              const visible = style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
              const disabled = "disabled" in element && Boolean(element.disabled);
              const text = (element.textContent ?? "").trim().replace(/\s+/g, " ");
              const associatedLabel = "labels" in element && element.labels
                ? [...element.labels]
                    .map((label) => (label.textContent ?? "").trim().replace(/\s+/g, " "))
                    .filter(Boolean)
                    .join(" ")
                : "";
              const accessible = [
                element.getAttribute("aria-label"),
                element.getAttribute("title"),
                element.getAttribute("placeholder"),
                associatedLabel,
                "value" in element && typeof element.value === "string" ? element.value : null,
                text,
              ].map((value) => typeof value === "string" ? value.trim() : "").find(Boolean) ?? "";
              const governed = [
                "data-control-id", "data-operation-id", "data-action-uid",
                "data-gate-uid", "data-permission-uid"
              ].some((name) => element.hasAttribute(name));
              return {
                index,
                tag: element.tagName.toLowerCase(),
                type: element.getAttribute("type"),
                href: element.getAttribute("href"),
                role: element.getAttribute("role"),
                accessible,
                disabled,
                visible,
                governed,
                controlId: element.getAttribute("data-control-id"),
                operationId: element.getAttribute("data-operation-id"),
                actionUid: element.getAttribute("data-action-uid"),
                viewSwitch: element.getAttribute("data-view-switch"),
                disabledReason: element.getAttribute("data-disabled-reason"),
                gateUid: element.getAttribute("data-gate-uid"),
                permissionUid: element.getAttribute("data-permission-uid"),
                insideForm: Boolean(element.closest("form")),
              };
            })
          );
          const visibleControls = controls.filter((control) => control.visible);
          interactiveControls += visibleControls.length;
          governedControls += visibleControls.filter((control) => control.governed).length;

          for (const control of visibleControls) {
            if (!control.accessible) throw new Error(`CONTROL_ACCESSIBLE_NAME_MISSING_${uid}_${control.tag}_${control.index}`);
            if (control.tag === "a" && (!control.href || control.href === "#" || /^javascript:/i.test(control.href))) {
              throw new Error(`CONTROL_LINK_TARGET_INVALID_${uid}_${control.index}`);
            }
            if (control.tag === "button" && control.insideForm && !control.type) {
              throw new Error(`CONTROL_FORM_BUTTON_TYPE_MISSING_${uid}_${control.index}`);
            }
            if (control.governed && !control.disabled && !(control.controlId || control.operationId || control.actionUid || control.viewSwitch)) {
              throw new Error(`CONTROL_GOVERNED_ACTION_IDENTITY_MISSING_${uid}_${control.index}`);
            }
            if (control.governed && control.disabled && !(control.disabledReason || control.gateUid || control.permissionUid)) {
              throw new Error(`CONTROL_DISABLED_REASON_MISSING_${uid}_${control.index}`);
            }
          }

          const viewSwitches = page.locator("button[data-view-switch]:visible:not(:disabled)");
          for (let index = 0; index < await viewSwitches.count(); index += 1) {
            const button = viewSwitches.nth(index);
            await button.click();
            await page.waitForTimeout(25);
            const currentUid = await page.locator("[data-page-uid]").first().getAttribute("data-page-uid");
            if (currentUid !== uid) throw new Error(`CONTROL_VIEW_SWITCH_NAVIGATION_ESCAPE_${uid}_${index}`);
            safeLocalClicks += 1;
          }
        }

        if (errors.length) throw new Error(`${uid}_${width}_${errors.join("|")}`);
        cases += 1;
        await page.close();
      }
    }
    const localeHtmlLang = {
      "zh-TW": "zh-Hant-TW",
      "zh-CN": "zh-Hans-CN",
      en: "en",
    };
    for (const [route, uid] of routes) {
      const page = await browser.newPage({ viewport: { width: 1280, height: 1400 } });
      try {
        await page.goto(base, { waitUntil: "domcontentloaded", timeout: 45_000 });
        const snapshots = {};
        for (const locale of ["zh-TW", "zh-CN", "en"]) {
          await page.evaluate((nextLocale) => window.localStorage.setItem("acpos.locale", nextLocale), locale);
          const root = await navigateToCurrentPage(page, route, uid);
          await page.waitForFunction(
            (expected) => document.documentElement.lang === expected,
            localeHtmlLang[locale],
            { timeout: 5_000 },
          );
          const heading = root.locator("h1, h2").first();
          if (await heading.count() === 0) throw new Error(`I18N_PAGE_HEADING_MISSING_${uid}_${locale}`);
          const title = ((await heading.textContent({ timeout: 5_000 })) ?? "").trim();
          if (!title) throw new Error(`I18N_PAGE_HEADING_EMPTY_${uid}_${locale}`);
          const visibleText = ((await root.innerText()) ?? "").replace(/\s+/g, " ").trim();
          if (!visibleText) throw new Error(`I18N_VISIBLE_TEXT_MISSING_${uid}_${locale}`);
          snapshots[locale] = { title, visibleText };
          i18nCases += 1;
        }
        if (snapshots["zh-TW"].visibleText === snapshots.en.visibleText) throw new Error(`I18N_ZHTW_NOT_RERENDERED_${uid}`);
        if (snapshots["zh-CN"].visibleText === snapshots.en.visibleText) throw new Error(`I18N_ZHCN_NOT_RERENDERED_${uid}`);
      } finally {
        await page.close();
      }
    }

    const strategyPage = await browser.newPage({ viewport: { width: 1280, height: 1400 } });
    try {
      await navigateToCurrentPage(strategyPage, "/admin/strategy", "admin:STR-01");

      const searchButton = strategyPage.locator('button[data-action-id="ACT-SEARCH"][data-source-page-uid="admin:STR-01"]').first();
      if (!(await searchButton.isEnabled())) throw new Error("STRATEGY_SEARCH_CONTROL_NOT_ENABLED_IN_CONTROLLED_TEST");
      if ((await searchButton.getAttribute("data-operation-id")) !== "searchProjection") throw new Error("STRATEGY_SEARCH_OPERATION_TRACE_INVALID");
      await searchButton.click();
      const searchModal = strategyPage.locator('[data-form-schema="SearchProjectionRequest"]');
      await searchModal.waitFor({ state: "visible", timeout: 5_000 });
      await searchModal.locator('input').nth(0).fill("TEST-STR");
      const searchSubmit = searchModal.locator("footer button").last();
      await searchSubmit.click();
      await searchModal.waitFor({ state: "detached", timeout: 5_000 });
      strategyFormCases += 1;

      const refreshButton = strategyPage.locator('button[data-action-id="ACT-REFRESH"][data-source-page-uid="admin:STR-01"]').first();
      if (!(await refreshButton.isEnabled())) throw new Error("STRATEGY_REFRESH_CONTROL_NOT_ENABLED_IN_CONTROLLED_TEST");
      if ((await refreshButton.getAttribute("data-operation-id")) !== "refreshProjection") throw new Error("STRATEGY_REFRESH_OPERATION_TRACE_INVALID");
      await refreshButton.click();
      const refreshModal = strategyPage.locator('[data-form-schema="RefreshProjectionRequest"]');
      await refreshModal.waitFor({ state: "visible", timeout: 5_000 });
      const refreshSubmit = refreshModal.locator("footer button").last();
      await refreshSubmit.click();
      await refreshModal.waitFor({ state: "detached", timeout: 5_000 });
      strategyFormCases += 1;

      await strategyPage.locator('button[data-view-uid="STR-CURRENT-VIEW-INTELLIGENCE-FACT"]').click();

      const configureButton = strategyPage.locator('button[data-action-id="ACT-CONFIGURE"][data-source-page-uid="admin:STR-02"]').first();
      if (!(await configureButton.isEnabled())) throw new Error("STRATEGY_CONFIGURE_CONTROL_NOT_ENABLED_IN_CONTROLLED_TEST");
      if ((await configureButton.getAttribute("data-operation-id")) !== "configureGovernedResource") throw new Error("STRATEGY_CONFIGURE_OPERATION_TRACE_INVALID");
      await configureButton.click();
      const configureModal = strategyPage.locator('[data-form-schema="ConfigureGovernedResourceRequest"]');
      await configureModal.waitFor({ state: "visible", timeout: 5_000 });
      await configureModal.locator("input").nth(0).fill("STRATEGY_FACT");
      await configureModal.locator("input").nth(1).fill("TEST-STR-FACT-001");
      await configureModal.locator("textarea").nth(0).fill('{"mode":"controlled-test"}');
      await configureModal.locator("input").nth(2).fill("Controlled Strategy governance configuration");
      await configureModal.locator("footer button").last().click();
      await configureModal.waitFor({ state: "detached", timeout: 5_000 });
      strategyFormCases += 1;

      const approveButton = strategyPage.locator('button[data-action-id="ACT-APPROVE"][data-source-page-uid="admin:STR-02"]').first();
      if (!(await approveButton.isEnabled())) throw new Error("STRATEGY_APPROVE_CONTROL_NOT_ENABLED_IN_CONTROLLED_TEST");
      if ((await approveButton.getAttribute("data-operation-id")) !== "approveGovernedResource") throw new Error("STRATEGY_APPROVE_OPERATION_TRACE_INVALID");
      await approveButton.click();
      const approveModal = strategyPage.locator('[data-form-schema="ApproveGovernedResourceRequest"]');
      await approveModal.waitFor({ state: "visible", timeout: 5_000 });
      await approveModal.locator("input").nth(0).fill("STRATEGY_FACT");
      await approveModal.locator("input").nth(1).fill("TEST-STR-FACT-001");
      await approveModal.locator("input").nth(2).fill("Controlled Strategy governance approval");
      await approveModal.locator("footer button").last().click();
      await approveModal.waitFor({ state: "detached", timeout: 5_000 });
      strategyFormCases += 1;

      const unresolvedDecision = strategyPage.locator('button[data-action-id="ACT-CANDIDATE-DECIDE"]');
      await strategyPage.locator('button[data-view-uid="STR-CURRENT-VIEW-DECISION"]').click();
      if ((await unresolvedDecision.getAttribute("data-operation-id")) !== "rejectStrategyCandidate") throw new Error("STRATEGY_REJECT_OPERATION_TRACE_INVALID");
      if (await unresolvedDecision.isEnabled()) throw new Error("STRATEGY_REJECT_SHOULD_REMAIN_DISABLED");
    } finally {
      await strategyPage.close();
    }

    const sgPage = await browser.newPage({ viewport: { width: 1280, height: 1400 } });
    try {
      await navigateToCurrentPage(sgPage, "/admin/qa-criteria", "admin:SG-02");

      const configureButton = sgPage.locator('button[data-control-id="CTRL-ADMIN-SG-02-ACT-01-ACT-CONFIGURE"][data-operation-id="configureGovernedResource"]').first();
      if (!(await configureButton.isEnabled())) throw new Error("SG02_CONFIGURE_CONTROL_NOT_ENABLED_IN_CONTROLLED_TEST");
      await configureButton.click();
      const sgDrawer = sgPage.locator('aside[data-detail-drawer="SG-02"]');
      await sgDrawer.waitFor({ state: "visible", timeout: 5_000 });
      await sgDrawer.locator("input").nth(0).fill("quality_criteria_version");
      await sgDrawer.locator("input").nth(1).fill("TEST-CRITERIA-DRAFT-001");
      await sgDrawer.locator("textarea").nth(0).fill('{"mode":"controlled-test","threshold":0.95}');
      await sgDrawer.locator("textarea").nth(1).fill("Controlled SG-02 governance configuration");
      const configureSubmit = sgDrawer.locator('button[data-control-id="CTRL-ADMIN-SG-02-ACT-01-ACT-CONFIGURE"][data-operation-id="configureGovernedResource"]').last();
      await configureSubmit.click();
      await sgDrawer.locator("input").first().waitFor({ state: "detached", timeout: 5_000 });
      if ((await sgPage.locator('[data-page-uid="admin:SG-02"]').getAttribute("data-page-state")) === "ERROR") {
        throw new Error("SG02_CONFIGURE_RUNTIME_ERROR");
      }
      sgGovernanceCases += 1;
      await sgDrawer.locator("button").first().click();
      await sgDrawer.waitFor({ state: "detached", timeout: 5_000 });

      const approveButton = sgPage.locator('button[data-control-id="CTRL-ADMIN-SG-02-ACT-02-ACT-APPROVE"][data-operation-id="approveGovernedResource"]').first();
      if (!(await approveButton.isEnabled())) throw new Error("SG02_APPROVE_CONTROL_NOT_ENABLED_IN_CONTROLLED_TEST");
      await approveButton.click();
      await sgDrawer.waitFor({ state: "visible", timeout: 5_000 });
      await sgDrawer.locator("input").nth(0).fill("quality_criteria_version");
      await sgDrawer.locator("input").nth(1).fill("TEST-CRITERIA-REVIEW-001");
      await sgDrawer.locator("textarea").nth(0).fill("Controlled SG-02 governance approval");
      await sgDrawer.locator("input").nth(2).fill("3");
      const approveSubmit = sgDrawer.locator('button[data-control-id="CTRL-ADMIN-SG-02-ACT-02-ACT-APPROVE"][data-operation-id="approveGovernedResource"]').last();
      await approveSubmit.click();
      await sgDrawer.locator("input").first().waitFor({ state: "detached", timeout: 5_000 });
      if ((await sgPage.locator('[data-page-uid="admin:SG-02"]').getAttribute("data-page-state")) === "ERROR") {
        throw new Error("SG02_APPROVE_RUNTIME_ERROR");
      }
      sgGovernanceCases += 1;
    } finally {
      await sgPage.close();
    }

    const iamPage = await browser.newPage({ viewport: { width: 1280, height: 1400 } });
    try {
      await navigateToCurrentPage(iamPage, "/admin/accounts", "admin:IAM-01");
      const iamRoot = iamPage.locator('[data-page-uid="admin:IAM-01"]');
      if ((await iamRoot.getAttribute("data-effectful-runtime-ready")) !== "true") {
        throw new Error("IAM_EFFECTFUL_RUNTIME_NOT_READY_IN_CONTROLLED_TEST");
      }

      const addButton = iamPage.locator('button[data-control-id="IAM-01-BTN-ADD"]');
      await iamPage.waitForFunction(
        () => {
          const button = document.querySelector('button[data-control-id="IAM-01-BTN-ADD"]');
          return button instanceof HTMLButtonElement && !button.disabled;
        },
        { timeout: 5_000 },
      );
      await addButton.click();
      await iamPage.waitForFunction(
        () => document.querySelector('[data-page-uid="admin:IAM-01"]')?.getAttribute("data-page-state") === "CREATE_BASIC",
        { timeout: 5_000 },
      );

      const identityField = iamPage.locator('input[data-field-uid="TEST-IAM-FIELD-IDENTITY-CANDIDATE"]');
      const scopeField = iamPage.locator('input[data-field-uid="TEST-IAM-FIELD-ORG-SCOPE"]');
      await identityField.fill("TEST-IDENTITY-CANDIDATE-NEW-001");
      await scopeField.fill("TEST-ORG-SCOPE-NEW");
      await iamPage.locator('select[data-control-id="IAM-01-SEL-DEPT-PRESET"]').selectOption("TEST-IAM-PRESET-EDITING");

      const saveButton = iamPage.locator('button[data-control-id="IAM-01-BTN-SAVE-DRAFT"]');
      if (!(await saveButton.isEnabled())) throw new Error("IAM_SAVE_DRAFT_NOT_ENABLED");
      await saveButton.click();
      const validateButton = iamPage.locator('button[data-control-id="IAM-01-BTN-VALIDATE"]');
      await validateButton.waitFor({ state: "visible", timeout: 5_000 });
      await iamPage.waitForFunction(
        () => {
          const button = document.querySelector('button[data-control-id="IAM-01-BTN-VALIDATE"]');
          return button instanceof HTMLButtonElement && !button.disabled;
        },
        { timeout: 5_000 },
      );
      iamMutationCases += 1;

      await validateButton.click();
      await iamPage.waitForFunction(
        () => document.querySelector('[data-page-uid="admin:IAM-01"]')?.getAttribute("data-page-state") === "CREATE_PERMISSION",
        { timeout: 5_000 },
      );
      iamMutationCases += 1;

      const previewButton = iamPage.locator('button[data-control-id="IAM-01-BTN-PREVIEW"]');
      await iamPage.waitForFunction(
        () => {
          const button = document.querySelector('button[data-control-id="IAM-01-BTN-PREVIEW"]');
          return button instanceof HTMLButtonElement && !button.disabled;
        },
        { timeout: 5_000 },
      );
      await previewButton.click();
      await iamPage.waitForFunction(
        () => document.querySelector('[data-page-uid="admin:IAM-01"]')?.getAttribute("data-page-state") === "CREATE_PREVIEW",
        { timeout: 5_000 },
      );
      iamMutationCases += 1;

      const completeButton = iamPage.locator('button[data-control-id="IAM-01-BTN-COMPLETE"]');
      await iamPage.waitForFunction(
        () => {
          const button = document.querySelector('button[data-control-id="IAM-01-BTN-COMPLETE"]');
          return button instanceof HTMLButtonElement && !button.disabled;
        },
        { timeout: 5_000 },
      );
      if (!(await completeButton.getAttribute("data-operations"))?.includes("assignAccountPermission")) {
        throw new Error("IAM_COMPLETE_ORCHESTRATION_TRACE_INVALID");
      }
      iamPage.once("dialog", async (dialog) => {
        await dialog.accept();
      });
      await completeButton.click();
      await iamPage.waitForFunction(
        () => document.querySelector('[data-page-uid="admin:IAM-01"]')?.getAttribute("data-page-state") === "COMPLETE",
        { timeout: 10_000 },
      );
      await iamPage.locator('button[data-account-id="TEST-IAM-ACCOUNT-NEW-001"]').waitFor({ state: "visible", timeout: 5_000 });
      if ((await iamRoot.getAttribute("data-runtime-error-uid")) !== null) throw new Error("IAM_COMPLETE_RUNTIME_ERROR");
      iamMutationCases += 1;
    } finally {
      await iamPage.close();
    }

    const erpPage = await browser.newPage({ viewport: { width: 1280, height: 1400 } });
    try {
      await navigateToCurrentPage(erpPage, "/admin/erp", "admin:ERP-01");
      const syncTab = erpPage.locator('button[data-control-id="ERP-01-BTN-TAB-SYNC"]');
      await requireActionable(syncTab, "ERP_SYNC_TAB_NOT_ENABLED_IN_CONTROLLED_TEST");
      await syncTab.click();

      const refreshButton = erpPage.locator('button[data-control-id="ERP-01-BTN-SNAPSHOT-REFRESH"]');
      await requireActionable(refreshButton, "ERP_SNAPSHOT_REFRESH_NOT_ENABLED_IN_CONTROLLED_TEST");
      if ((await refreshButton.getAttribute("data-form-schema-ready")) !== "true") throw new Error("ERP_SNAPSHOT_REFRESH_FORM_NOT_BOUND");
      await refreshButton.click();

      const refreshForm = erpPage.locator('[data-drawer-form="ERP-01-BTN-SNAPSHOT-REFRESH"]');
      await refreshForm.waitFor({ state: "visible", timeout: 5_000 });
      await refreshForm.locator('[data-form-field-key="requested_scope"] input').fill("finance-ledger");
      const submit = refreshForm.locator('button[data-form-submit="true"]');
      if (!(await submit.isEnabled())) throw new Error("ERP_SNAPSHOT_REFRESH_SUBMIT_NOT_ENABLED");
      await submit.click();
      await refreshForm.waitFor({ state: "detached", timeout: 5_000 });
      if ((await erpPage.locator('[data-page-uid="admin:ERP-01"]').getAttribute("data-page-state")) === "ERROR") {
        throw new Error("ERP_SNAPSHOT_REFRESH_RUNTIME_ERROR");
      }
      erpMutationCases += 1;
    } finally {
      await erpPage.close();
    }

    const devPage = await browser.newPage({ viewport: { width: 1280, height: 1400 } });
    try {
      const devRoot = await navigateToCurrentPage(devPage, "/admin/dev", "admin:DEV-01");
      const startButton = devPage.locator('button[data-control-id="DEV-01-BTN-DISCOVERY-START"]');
      if (!(await startButton.isEnabled())) throw new Error("DEV_DISCOVERY_START_NOT_ENABLED_IN_CONTROLLED_TEST");
      if ((await startButton.getAttribute("data-operation")) !== "startCompanyDiscovery") throw new Error("DEV_DISCOVERY_START_OPERATION_TRACE_INVALID");
      await startButton.click();

      const pauseButton = devPage.locator('button[data-control-id="DEV-01-BTN-DISCOVERY-PAUSE"]');
      await pauseButton.waitFor({ state: "visible", timeout: 5_000 });
      if (!(await pauseButton.isEnabled())) throw new Error("DEV_DISCOVERY_PAUSE_NOT_ENABLED_AFTER_START");
      if ((await pauseButton.getAttribute("data-operation")) !== "pauseCompanyDiscovery") throw new Error("DEV_DISCOVERY_PAUSE_OPERATION_TRACE_INVALID");
      if ((await devRoot.getAttribute("data-page-state")) === "ERROR") throw new Error("DEV_DISCOVERY_START_RUNTIME_ERROR");
      devMutationCases += 1;

      await pauseButton.click();
      const resumeButton = devPage.locator('button[data-control-id="DEV-01-BTN-DISCOVERY-RESUME"]');
      await resumeButton.waitFor({ state: "visible", timeout: 5_000 });
      if (!(await resumeButton.isEnabled())) throw new Error("DEV_DISCOVERY_RESUME_NOT_ENABLED_AFTER_PAUSE");
      if ((await resumeButton.getAttribute("data-operation")) !== "resumeCompanyDiscovery") throw new Error("DEV_DISCOVERY_RESUME_OPERATION_TRACE_INVALID");
      devMutationCases += 1;

      await resumeButton.click();
      await pauseButton.waitFor({ state: "visible", timeout: 5_000 });
      const stopButton = devPage.locator('button[data-control-id="DEV-01-BTN-DISCOVERY-STOP"]');
      await stopButton.waitFor({ state: "visible", timeout: 5_000 });
      if (!(await stopButton.isEnabled())) throw new Error("DEV_DISCOVERY_STOP_NOT_ENABLED_AFTER_RESUME");
      if ((await stopButton.getAttribute("data-operation")) !== "stopCompanyDiscovery") throw new Error("DEV_DISCOVERY_STOP_OPERATION_TRACE_INVALID");
      devMutationCases += 1;

      await stopButton.click();
      await startButton.waitFor({ state: "visible", timeout: 5_000 });
      if (!(await startButton.isEnabled())) throw new Error("DEV_DISCOVERY_START_NOT_RESTORED_AFTER_STOP");
      if ((await devRoot.getAttribute("data-runtime-error-uid")) !== null) throw new Error("DEV_DISCOVERY_STOP_RUNTIME_ERROR");
      devMutationCases += 1;
    } finally {
      await devPage.close();
    }

    const socPage = await browser.newPage({ viewport: { width: 1280, height: 1400 } });
    try {
      const socRoot = await navigateToCurrentPage(socPage, "/admin/social", "admin:SOC-01");
      const contentTab = socPage.locator('button[data-control-id="SOC-01-TAB-STAGE-3"]');
      if (!(await contentTab.isEnabled())) throw new Error("SOC_CONTENT_TAB_NOT_ENABLED_IN_CONTROLLED_TEST");
      await contentTab.click();

      const saveButton = socPage.locator('button[data-control-id="SOC-01-BTN-CONTENT-SAVE"]');
      await saveButton.waitFor({ state: "visible", timeout: 5_000 });
      if (!(await saveButton.isEnabled())) throw new Error("SOC_CONTENT_SAVE_NOT_ENABLED_IN_CONTROLLED_TEST");
      if ((await saveButton.getAttribute("data-action-uid")) !== "SOC-01-ACT-CONTENT-SAVE") throw new Error("SOC_CONTENT_SAVE_ACTION_TRACE_INVALID");
      await saveButton.click();
      await socPage.waitForFunction(
        () => (document.querySelector('[data-control-id="SOC-01-FLD-APPROVAL"]')?.textContent ?? "").includes("REVIEW"),
        { timeout: 5_000 },
      );
      if ((await socRoot.getAttribute("data-page-state")) === "ERROR") throw new Error("SOC_CONTENT_SAVE_RUNTIME_ERROR");
      socMutationCases += 1;

      const decideButton = socPage.locator('button[data-control-id="SOC-01-BTN-CANDIDATE-DECIDE"]');
      await decideButton.waitFor({ state: "visible", timeout: 5_000 });
      if (!(await decideButton.isEnabled())) throw new Error("SOC_CANDIDATE_DECIDE_NOT_ENABLED_IN_CONTROLLED_TEST");
      if ((await decideButton.getAttribute("data-action-uid")) !== "SOC-01-ACT-CANDIDATE-DECIDE") throw new Error("SOC_CANDIDATE_DECIDE_ACTION_TRACE_INVALID");
      await decideButton.click();
      await socPage.waitForFunction(
        () => (document.querySelector('[data-control-id="SOC-01-FLD-APPROVAL"]')?.textContent ?? "").includes("APPROVED"),
        { timeout: 5_000 },
      );
      if (await decideButton.isVisible()) throw new Error("SOC_CANDIDATE_DECIDE_SHOULD_CLOSE_AFTER_APPROVAL");
      if ((await socRoot.getAttribute("data-page-state")) === "ERROR") throw new Error("SOC_CANDIDATE_DECIDE_RUNTIME_ERROR");
      socMutationCases += 1;
    } finally {
      await socPage.close();
    }

    const aiApiPage = await browser.newPage({ viewport: { width: 1280, height: 1400 } });
    try {
      const aiApiRoot = await navigateToCurrentPage(aiApiPage, "/admin/aiapi", "admin:AIAPI-01");
      await aiApiPage.locator('button[data-view-switch="AIAPI-01-VIEW-OPERATIONS"]').click();

      const killButton = aiApiPage.locator('button[data-operation-id="setKillSwitch"]');
      await aiApiPage.waitForFunction(
        () => {
          const button = document.querySelector('button[data-operation-id="setKillSwitch"]');
          return button instanceof HTMLButtonElement && !button.disabled;
        },
        { timeout: 5_000 },
      );

      const executeKillSwitch = async (enabled, reason) => {
        await killButton.click();
        const dialog = aiApiPage.locator('section[role="dialog"]');
        await dialog.waitFor({ state: "visible", timeout: 5_000 });

        const targetType = dialog.locator('[data-field-key="target_type"] select');
        const targetRef = dialog.locator('[data-field-key="target_ref"] input');
        const enabledField = dialog.locator('[data-field-key="enabled"] select');
        const reasonField = dialog.locator('[data-field-key="reason"] textarea');
        const confirmation = dialog.locator('[data-field-key="confirmation"] select');

        await targetType.selectOption("PROFILE");
        await targetRef.fill("TEST-AIAPI-PROVIDER-001");
        await enabledField.selectOption(enabled ? "true" : "false");
        await reasonField.fill(reason);
        await confirmation.selectOption("CONFIRM");
        await dialog.locator("button").last().click();
        await dialog.waitFor({ state: "detached", timeout: 5_000 });

        const result = aiApiPage.locator('aside[data-aiapi-command-result="true"]');
        await result.waitFor({ state: "visible", timeout: 5_000 });
        const resultText = (await result.textContent()) ?? "";
        if (!resultText.includes('"external_request_sent": false')) throw new Error("AIAPI_KILL_SWITCH_EXTERNAL_REQUEST_GUARD_MISSING");
        if (!resultText.includes(`"enabled": ${enabled ? "true" : "false"}`)) throw new Error("AIAPI_KILL_SWITCH_RESULT_STATE_INVALID");
        if ((await aiApiRoot.getAttribute("data-page-state")) === "ERROR") throw new Error("AIAPI_KILL_SWITCH_RUNTIME_ERROR");
        aiApiMutationCases += 1;
      };

      await executeKillSwitch(false, "Controlled Gate 24 disable verification");
      await executeKillSwitch(true, "Controlled Gate 24 restore verification");
    } finally {
      await aiApiPage.close();
    }


    const kbPage = await browser.newPage({ viewport: { width: 1280, height: 1400 } });
    try {
      const kbRoot = await navigateToCurrentPage(kbPage, "/admin/knowledge", "admin:KB-01");
      await kbPage.locator('button[data-view-uid="KB-01-VIEW-SOURCE"]').click();

      const pauseButton = kbPage.locator('button[data-control-id="KB-01-CTL-SOURCE-PAUSE"]');
      await pauseButton.waitFor({ state: "visible", timeout: 5_000 });
      await kbPage.waitForFunction(
        () => {
          const button = document.querySelector('button[data-control-id="KB-01-CTL-SOURCE-PAUSE"]');
          return button instanceof HTMLButtonElement && !button.disabled;
        },
        { timeout: 5_000 },
      );
      if ((await pauseButton.getAttribute("data-action-operation")) !== "pauseKnowledgeSource") throw new Error("KB_SOURCE_PAUSE_OPERATION_TRACE_INVALID");
      await pauseButton.click();

      const resumeButton = kbPage.locator('button[data-control-id="KB-01-CTL-SOURCE-RESUME"]');
      await resumeButton.waitFor({ state: "visible", timeout: 5_000 });
      await kbPage.waitForFunction(
        () => {
          const button = document.querySelector('button[data-control-id="KB-01-CTL-SOURCE-RESUME"]');
          return button instanceof HTMLButtonElement && !button.disabled;
        },
        { timeout: 5_000 },
      );
      if ((await resumeButton.getAttribute("data-action-operation")) !== "resumeKnowledgeSource") throw new Error("KB_SOURCE_RESUME_OPERATION_TRACE_INVALID");
      if ((await kbRoot.getAttribute("data-page-state")) === "ERROR") throw new Error("KB_SOURCE_PAUSE_RUNTIME_ERROR");
      kbMutationCases += 1;

      await resumeButton.click();
      await pauseButton.waitFor({ state: "visible", timeout: 5_000 });
      await kbPage.waitForFunction(
        () => {
          const button = document.querySelector('button[data-control-id="KB-01-CTL-SOURCE-PAUSE"]');
          return button instanceof HTMLButtonElement && !button.disabled;
        },
        { timeout: 5_000 },
      );
      if ((await kbRoot.getAttribute("data-page-state")) === "ERROR") throw new Error("KB_SOURCE_RESUME_RUNTIME_ERROR");
      kbMutationCases += 1;
    } finally {
      await kbPage.close();
    }
  } finally {
    await browser.close();
  }
  process.stdout.write(`RELEASE_BROWSER_E2E_PASS cases=${cases} i18n_cases=${i18nCases} shell_geometry_cases=${shellGeometryCases} visual_topology_cases=${visualTopologyCases} sidebar_reflow_cases=${sidebarReflowCases} interactive_controls=${interactiveControls} governed_controls=${governedControls} safe_local_clicks=${safeLocalClicks} strategy_form_cases=${strategyFormCases} sg_governance_cases=${sgGovernanceCases} iam_mutation_cases=${iamMutationCases} erp_mutation_cases=${erpMutationCases} dev_mutation_cases=${devMutationCases} soc_mutation_cases=${socMutationCases} aiapi_mutation_cases=${aiApiMutationCases} kb_mutation_cases=${kbMutationCases}\n`);
} finally {
  server.kill("SIGTERM");
}
