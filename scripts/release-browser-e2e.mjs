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
  } finally {
    await browser.close();
  }
  process.stdout.write(`RELEASE_BROWSER_E2E_PASS cases=${cases} interactive_controls=${interactiveControls} governed_controls=${governedControls} safe_local_clicks=${safeLocalClicks} strategy_form_cases=${strategyFormCases} sg_governance_cases=${sgGovernanceCases}\n`);
} finally {
  server.kill("SIGTERM");
}
