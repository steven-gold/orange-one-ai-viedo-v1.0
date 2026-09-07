import { spawn } from "node:child_process";
import { chromium } from "playwright";

const port = process.env.ACPOS_TEMP_FULL_ACCEPTANCE_PORT ?? "3525";
const base = `http://127.0.0.1:${port}`;
const origin = new URL(base).origin;
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

function sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }

async function waitForServer() {
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${base}/health`, { cache: "no-store" });
      if (response.ok) return;
    } catch {}
    await sleep(400);
  }
  throw new Error("TEMP_FULL_ACCEPTANCE_SERVER_TIMEOUT");
}

async function navigate(page, route, uid, viewSwitch = null) {
  const response = await page.goto(`${base}${route}`, { waitUntil: "domcontentloaded", timeout: 45_000 });
  if (!response?.ok()) throw new Error(`TEMP_NAV_${uid}_${response?.status()}`);
  const root = page.locator("[data-page-uid]").first();
  await root.waitFor({ state: "attached", timeout: 15_000 });
  const actual = await root.getAttribute("data-page-uid");
  if (actual !== uid) throw new Error(`TEMP_UID_MISMATCH_${uid}_${actual}`);
  await page.waitForFunction(
    () => document.querySelector("[data-page-uid]")?.getAttribute("data-page-state") !== "LOADING",
    { timeout: 15_000 },
  );
  if (viewSwitch) {
    const switcher = page.locator(`button[data-view-switch="${viewSwitch}"]:visible:not(:disabled)`).first();
    if (await switcher.count()) {
      await switcher.click();
      await sleep(35);
    }
  }
  const state = await root.getAttribute("data-page-state");
  if (state === "ERROR") throw new Error(`TEMP_PAGE_STATE_ERROR_${uid}`);
  return root;
}

function controlKey(control) {
  return [
    control.viewSwitch ? `view:${control.viewSwitch}` : "",
    control.controlId ? `control:${control.controlId}` : "",
    control.operationId ? `operation:${control.operationId}` : "",
    control.actionUid ? `action:${control.actionUid}` : "",
    control.tag,
    control.accessible,
    String(control.occurrence),
  ].filter(Boolean).join("|");
}

async function snapshot(page) {
  return page.locator('button, a[href], input, select, textarea, [role="button"]').evaluateAll((nodes) => {
    const seen = new Map();
    return nodes.map((node) => {
      const element = /** @type {HTMLElement} */ (node);
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      const visible = style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
      const disabled = "disabled" in element && Boolean(element.disabled);
      const text = (element.textContent ?? "").trim().replace(/\s+/g, " ");
      const associatedLabel = "labels" in element && element.labels
        ? [...element.labels].map((label) => (label.textContent ?? "").trim().replace(/\s+/g, " ")).filter(Boolean).join(" ")
        : "";
      const accessible = [
        element.getAttribute("aria-label"), element.getAttribute("title"), element.getAttribute("placeholder"),
        associatedLabel, "value" in element && typeof element.value === "string" ? element.value : null, text,
      ].map((value) => typeof value === "string" ? value.trim() : "").find(Boolean) ?? "";
      const controlId = element.getAttribute("data-control-id");
      const operationId = element.getAttribute("data-operation-id");
      const actionUid = element.getAttribute("data-action-uid") ?? element.getAttribute("data-action-id");
      const viewSwitch = element.getAttribute("data-view-switch");
      const targetPageUid = element.getAttribute("data-target-page-uid");
      const identity = controlId ?? operationId ?? actionUid ?? viewSwitch ?? `${element.tagName}:${accessible}`;
      const occurrence = seen.get(identity) ?? 0;
      seen.set(identity, occurrence + 1);
      return {
        tag: element.tagName.toLowerCase(),
        type: element.getAttribute("type") ?? "",
        accessible,
        disabled,
        visible,
        controlId,
        operationId,
        actionUid,
        viewSwitch,
        targetPageUid,
        href: element.getAttribute("href"),
        governed: Boolean(controlId || operationId || actionUid || viewSwitch || element.getAttribute("data-gate-uid") || element.getAttribute("data-permission-uid")),
        occurrence,
      };
    }).filter((control) => control.visible);
  });
}

function locatorFor(page, control) {
  if (control.controlId) return page.locator(`[data-control-id="${CSS.escape(control.controlId)}"]`).nth(control.occurrence);
  if (control.operationId) return page.locator(`[data-operation-id="${CSS.escape(control.operationId)}"]`).nth(control.occurrence);
  if (control.actionUid) {
    const a = page.locator(`[data-action-uid="${CSS.escape(control.actionUid)}"]`);
    return a.count().then(async (count) => count ? a.nth(control.occurrence) : page.locator(`[data-action-id="${CSS.escape(control.actionUid)}"]`).nth(control.occurrence));
  }
  return null;
}

async function fillField(locator) {
  const tag = await locator.evaluate((node) => node.tagName.toLowerCase());
  if (tag === "select") {
    const options = await locator.locator("option:not(:disabled)").evaluateAll((nodes) => nodes.map((node) => node.value).filter(Boolean));
    if (!options.length) return false;
    await locator.selectOption(options[0]);
    return true;
  }
  const type = (await locator.getAttribute("type")) ?? "text";
  if (["button","submit","reset","file","hidden"].includes(type)) return false;
  if (type === "checkbox" || type === "radio") {
    await locator.click();
    return true;
  }
  const value =
    type === "number" ? "1" :
    type === "email" ? "test-only@example.invalid" :
    type === "url" ? "https://example.invalid/test-only" :
    type === "date" ? "2026-09-07" :
    "TEST_ONLY_ACCEPTANCE";
  await locator.fill(value);
  return true;
}

async function touchVisibleFormFields(page) {
  const fields = page.locator('section[role="dialog"]:visible input:enabled, section[role="dialog"]:visible select:enabled, section[role="dialog"]:visible textarea:enabled, aside:visible input:enabled, aside:visible select:enabled, aside:visible textarea:enabled');
  let touched = 0;
  const count = await fields.count();
  for (let i = 0; i < count; i += 1) {
    try {
      if (await fillField(fields.nth(i))) touched += 1;
    } catch {}
  }
  return touched;
}

try {
  await waitForServer();
  const browser = await chromium.launch({ headless: true });
  let pages = 0;
  let views = 0;
  let controlsDiscovered = 0;
  let disabledGoverned = 0;
  let inputExercises = 0;
  let actionExercises = 0;
  let formFieldsTouched = 0;
  let dialogsDismissed = 0;
  let navigationCovered = 0;
  let controlledMetadataPages = 0;
  const failures = [];

  try {
    for (const [route, uid] of routes) {
      const discovery = await browser.newPage({ viewport: { width: 1280, height: 1400 } });
      const externalRequests = [];
      discovery.on("request", (request) => {
        const url = new URL(request.url());
        if (!["http:","https:"].includes(url.protocol)) return;
        if (url.origin !== origin) externalRequests.push(request.url());
      });
      try {
        const root = await navigate(discovery, route, uid);
        const productionEligible = await root.getAttribute("data-production-eligible");
        if (productionEligible === "true") throw new Error(`TEMP_CONTROLLED_PRODUCTION_ELIGIBLE_${uid}`);
        if (productionEligible === "false") controlledMetadataPages += 1;

        const initial = await snapshot(discovery);
        const viewIds = [...new Set(initial.map((c) => c.viewSwitch).filter(Boolean))];
        const contexts = [null, ...viewIds];

        for (const viewSwitch of contexts) {
          await navigate(discovery, route, uid, viewSwitch);
          views += 1;
          const controls = await snapshot(discovery);
          controlsDiscovered += controls.length;

          for (const control of controls) {
            if (control.disabled) {
              if (control.governed) disabledGoverned += 1;
              continue;
            }
            if (control.targetPageUid || control.tag === "a") {
              navigationCovered += 1;
              continue;
            }
            if (control.viewSwitch) continue;

            if (["input","select","textarea"].includes(control.tag)) {
              const all = await snapshot(discovery);
              const same = all.filter((item) =>
                item.tag === control.tag &&
                item.controlId === control.controlId &&
                item.operationId === control.operationId &&
                item.actionUid === control.actionUid &&
                item.accessible === control.accessible
              );
              const index = Math.min(control.occurrence, Math.max(0, same.length - 1));
              let loc = null;
              if (control.controlId) loc = discovery.locator(`[data-control-id="${control.controlId}"]`).nth(index);
              else if (control.operationId) loc = discovery.locator(`[data-operation-id="${control.operationId}"]`).nth(index);
              else if (control.accessible) loc = discovery.locator(control.tag).filter({ hasText: control.accessible }).nth(index);
              if (loc && await loc.count() && await loc.isEnabled().catch(() => false)) {
                try {
                  if (await fillField(loc)) inputExercises += 1;
                } catch (error) {
                  failures.push(`INPUT:${uid}:${controlKey(control)}:${error instanceof Error ? error.message : String(error)}`);
                }
              }
              continue;
            }

            if (control.tag === "button" || control.tag === "div") {
              if (!control.governed) continue;
              const actionPage = await browser.newPage({ viewport: { width: 1280, height: 1400 } });
              const actionExternal = [];
              actionPage.on("request", (request) => {
                const url = new URL(request.url());
                if (["http:","https:"].includes(url.protocol) && url.origin !== origin) actionExternal.push(request.url());
              });
              let dialogSeen = false;
              actionPage.on("dialog", async (dialog) => {
                dialogSeen = true;
                dialogsDismissed += 1;
                await dialog.dismiss();
              });
              try {
                const actionRoot = await navigate(actionPage, route, uid, viewSwitch);
                const pageFields = actionPage.locator('input:visible:enabled, select:visible:enabled, textarea:visible:enabled');
                for (let fieldIndex = 0; fieldIndex < await pageFields.count(); fieldIndex += 1) {
                  try {
                    if (await fillField(pageFields.nth(fieldIndex))) inputExercises += 1;
                  } catch {}
                }
                let loc = null;
                if (control.controlId) loc = actionPage.locator(`[data-control-id="${control.controlId}"]:visible:not(:disabled)`).nth(control.occurrence);
                else if (control.operationId) loc = actionPage.locator(`[data-operation-id="${control.operationId}"]:visible:not(:disabled)`).nth(control.occurrence);
                else if (control.actionUid) {
                  const byUid = actionPage.locator(`[data-action-uid="${control.actionUid}"]:visible:not(:disabled)`);
                  loc = await byUid.count()
                    ? byUid.nth(control.occurrence)
                    : actionPage.locator(`[data-action-id="${control.actionUid}"]:visible:not(:disabled)`).nth(control.occurrence);
                }
                if (!loc || !(await loc.count())) continue;
                await loc.click({ timeout: 5_000 });
                actionExercises += 1;
                await sleep(80);
                formFieldsTouched += await touchVisibleFormFields(actionPage);
                const state = await actionRoot.getAttribute("data-page-state");
                if (state === "ERROR") throw new Error("PAGE_STATE_ERROR_AFTER_ACTION");
                if (actionExternal.length) throw new Error(`EXTERNAL_REQUEST_FORBIDDEN:${actionExternal.join(",")}`);
                if (!dialogSeen) await actionPage.keyboard.press("Escape").catch(() => {});
              } catch (error) {
                failures.push(`ACTION:${uid}:${controlKey(control)}:${error instanceof Error ? error.message : String(error)}`);
              } finally {
                await actionPage.close();
              }
            }
          }
        }

        if (externalRequests.length) failures.push(`DISCOVERY_EXTERNAL:${uid}:${externalRequests.join(",")}`);
        pages += 1;
      } catch (error) {
        failures.push(`PAGE:${uid}:${error instanceof Error ? error.message : String(error)}`);
      } finally {
        await discovery.close();
      }
    }
  } finally {
    await browser.close();
  }

  if (pages !== routes.length) failures.push(`PAGE_COUNT:${pages}/${routes.length}`);
  if (actionExercises === 0) failures.push("NO_ACTIONS_EXERCISED");
  if (failures.length) {
    throw new Error(`TEMP_FULL_ACCEPTANCE_FAIL failures=${failures.length} details=${JSON.stringify(failures.slice(0,80))}`);
  }

  process.stdout.write(
    `TEMP_FULL_ACCEPTANCE_PASS pages=${pages} views=${views} controls_scanned=${controlsDiscovered} disabled_governed=${disabledGoverned} input_exercises=${inputExercises} action_exercises=${actionExercises} form_fields_touched=${formFieldsTouched} dialogs_dismissed=${dialogsDismissed} navigation_covered=${navigationCovered} controlled_metadata_pages=${controlledMetadataPages} external_requests=0 cleanup=PROCESS_TEARDOWN_TEST_ONLY\n`
  );
} finally {
  server.kill("SIGTERM");
  await sleep(150);
}
