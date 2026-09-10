import { spawn } from "node:child_process";
import { readFile } from "node:fs/promises";
import { chromium } from "playwright";

const port = process.env.ACPOS_CONTROL_ACCEPTANCE_PORT ?? "3600";
const base = `http://127.0.0.1:${port}`;
const routes = [
  ["/", "workspace:WB-01"], ["/core", "CORE-01"], ["/assets", "ASSET-01"], ["/video", "VIDEO-01"],
  ["/edit", "EDIT-01"], ["/qa", "QA-01"], ["/database", "admin:DB-01"], ["/strategy", "workspace:STR-01"],
  ["/info", "workspace:INFO-01"], ["/admin/system", "admin:SYS-01"], ["/admin/accounts", "admin:IAM-01"],
  ["/admin/dev", "admin:DEV-01"], ["/admin/social", "admin:SOC-01"], ["/admin/erp", "admin:ERP-01"],
  ["/admin/aiapi", "admin:AIAPI-01"], ["/admin/qa-criteria", "admin:SG-02"], ["/admin/strategy", "admin:STR-01"],
  ["/admin/knowledge", "admin:KB-01"],
];
const formalInventory=JSON.parse(await readFile("docs/construction/evidence/PRODUCTION_FORMAL_CONTROL_ACTION_INVENTORY_2026-09-10.json","utf8"));
const formalInventoryKeys=new Set(formalInventory.resources.map((row)=>String(row.resource_key??"")));

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
  throw new Error("CONTROL_ACCEPTANCE_SERVER_START_TIMEOUT");
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

try {
  await waitForServer();
  const browser = await chromium.launch({ headless: true });
  const failures = [];
  let interactiveTotal = 0;
  let enabledTotal = 0;
  let disabledTotal = 0;
  let governedTotal = 0;
  const perPage = [];
  const formalEvidence=new Map();

  try {
    for (const [route, expectedUid] of routes) {
      const page = await browser.newPage({ viewport: { width: 1440, height: 1400 } });
      const runtimeErrors = [];
      page.on("pageerror", (error) => runtimeErrors.push(`pageerror:${error.message}`));
      const response = await page.goto(`${base}${route}`, { waitUntil: "domcontentloaded", timeout: 45_000 });
      assert(response?.ok(), `CONTROL_NAV_${route}_${response?.status()}`);
      const root = page.locator("[data-page-uid]").first();
      await root.waitFor({ state: "attached", timeout: 15_000 });
      const actualUid = await root.getAttribute("data-page-uid");
      assert(actualUid === expectedUid, `CONTROL_UID_${route}_${actualUid}`);
      await page.locator("body").waitFor({ state: "visible", timeout: 15_000 });
      try {
        await page.waitForFunction(
          () => document.querySelector("[data-page-uid]")?.getAttribute("data-page-state") !== "LOADING",
          { timeout: 15_000 },
        );
      } catch {
        throw new Error(`CONTROL_STUCK_LOADING_${expectedUid}`);
      }

      try {
        await page.waitForFunction(
          () => {
            const current = document.querySelector("[data-page-uid]");
            if (!current) return false;
            const nodes = Array.from(current.querySelectorAll("button,input,select,textarea,a[href],[role='button']"));
            return nodes.some((node) => {
              const style = getComputedStyle(node);
              const rect = node.getBoundingClientRect();
              return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
            });
          },
          { timeout: 15_000 },
        );
      } catch {}

      const audit = await page.evaluate(() => {
        const root = document.querySelector("[data-page-uid]");
        if (!root) return { rows: [], visible: 0, enabled: 0, disabled: 0, governed: 0, nodesTotal: 0, diagnostic: { rootMissing: true } };
        const pageUid=root.getAttribute("data-page-uid")||"";
        const formalPageUid=pageUid.includes(":")?pageUid:`workspace:${pageUid}`;
        const selector = "button,input,select,textarea,a[href],[role='button']";
        const nodes = Array.from(root.querySelectorAll(selector));
        const visible = nodes.filter((node) => {
          const style = getComputedStyle(node);
          const rect = node.getBoundingClientRect();
          return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
        });
        const governanceNames = [
          "data-control-id", "data-control-uid", "data-action-uid", "data-operation-id", "data-view-switch", "data-view-uid", "data-gate-uid",
          "data-permission-uid", "data-permission", "data-navigation-target", "data-command-id", "data-action-id",
        ];
        const rows = visible.map((node, index) => {
          const element = node;
          const tag = element.tagName.toLowerCase();
          const disabled = "disabled" in element ? Boolean(element.disabled) : element.getAttribute("aria-disabled") === "true";
          const label = (element.getAttribute("aria-label") || element.textContent || element.getAttribute("placeholder") || element.getAttribute("name") || "").trim().replace(/\s+/g, " ").slice(0, 120);
          const owner = element.closest(governanceNames.map((name) => `[${name}]`).join(","));
          const value=(name)=>element.getAttribute(name)||owner?.getAttribute(name)||"";
          const governance = governanceNames.filter((name) => Boolean(value(name)));
          const identities=Object.fromEntries(governanceNames.map((name)=>[name,value(name)]).filter(([,v])=>v));
          const candidateKeys=new Set();
          const addControl=(v)=>{if(!v)return;if(v.startsWith("control:"))candidateKeys.add(v);else if(v.startsWith("CTRL-"))candidateKeys.add(`control:${v}`);};
          const addAction=(v)=>{if(!v)return;if(v.startsWith("action:"))candidateKeys.add(v);else if(v.startsWith("ACT-")&&formalPageUid)candidateKeys.add(`action:${formalPageUid}:${v}`);};
          addControl(value("data-control-id"));addControl(value("data-control-uid"));
          addAction(value("data-action-uid"));addAction(value("data-action-id"));
          const permissionUid=value("data-permission-uid");
          if(permissionUid.startsWith("control:")||permissionUid.startsWith("action:"))candidateKeys.add(permissionUid);
          const gateUid = value("data-gate-uid");
          const allowed = value("data-allowed");
          const runtimeBinding = value("data-runtime-binding");
          const enabledInVisualPhase = value("data-enabled-in-visual-phase");
          const disabledReason =
            element.getAttribute("data-disabled-reason") || element.getAttribute("data-blocked-reason") || element.getAttribute("data-blocked-error-uid") ||
            owner?.getAttribute("data-disabled-reason") || owner?.getAttribute("data-blocked-reason") || owner?.getAttribute("data-blocked-error-uid") ||
            element.getAttribute("title") || (disabled && allowed === "false" && gateUid ? `${gateUid}:NOT_SATISFIED` : "") ||
            (disabled && enabledInVisualPhase === "false" ? "DISABLED_IN_VISUAL_PHASE" : "") ||
            (disabled && /^(NOT_EXECUTED|NOT_BOUND|BLOCKED|UNRESOLVED)/.test(runtimeBinding) ? runtimeBinding : "");
          const searchRegion = element.closest("[role='search']");
          const governedSearchPeer = Boolean(searchRegion?.querySelector("[data-control-id],[data-control-uid],[data-action-uid],[data-action-id],[data-operation-id]"));
          const localSemantic = tag === "a" || element.getAttribute("type") === "submit" || element.getAttribute("type") === "reset" || element.hasAttribute("aria-controls") || element.hasAttribute("aria-expanded") || (tag === "input" && Boolean(searchRegion) && governedSearchPeer);
          return { index, tag, label, disabled, governance, identities, candidateKeys:[...candidateKeys], disabledReason, localSemantic };
        });
        const rootStyle = getComputedStyle(root);
        const rootRect = root.getBoundingClientRect();
        return {
          rows,
          visible: rows.length,
          enabled: rows.filter((row) => !row.disabled).length,
          disabled: rows.filter((row) => row.disabled).length,
          governed: rows.filter((row) => row.governance.length > 0 || row.localSemantic).length,
          nodesTotal: nodes.length,
          diagnostic: { pageState: root.getAttribute("data-page-state") || "", rootDisplay: rootStyle.display, rootVisibility: rootStyle.visibility, rootWidth: Math.round(rootRect.width), rootHeight: Math.round(rootRect.height) },
        };
      });

      interactiveTotal += audit.visible;
      enabledTotal += audit.enabled;
      disabledTotal += audit.disabled;
      governedTotal += audit.governed;
      perPage.push({ route, uid: expectedUid, ...audit, rows: undefined });
      if (audit.visible === 0) failures.push(`${expectedUid}:ZERO_VISIBLE_INTERACTIVE_CONTROLS:nodes=${audit.nodesTotal}:diagnostic=${JSON.stringify(audit.diagnostic)}`);

      for (const row of audit.rows) {
        const ref = `${expectedUid}:${row.tag}:${row.index}:${row.label || "UNLABELED"}`;
        if (!row.label && row.tag !== "input") failures.push(`${ref}:ACCESSIBLE_LABEL_MISSING`);
        if (row.disabled && !row.disabledReason && row.governance.length > 0) failures.push(`${ref}:DISABLED_REASON_MISSING`);
        if (!row.disabled && row.governance.length === 0 && !row.localSemantic) failures.push(`${ref}:INTERACTION_BINDING_IDENTITY_MISSING`);
        for(const key of row.candidateKeys){
          if(!formalInventoryKeys.has(key)) continue;
          const existing=formalEvidence.get(key)??{resource_key:key,observations:0,enabled_observations:0,disabled_observations:0,pages:new Set(),routes:new Set(),labels:new Set(),disabled_reasons:new Set()};
          existing.observations++;
          if(row.disabled)existing.disabled_observations++;else existing.enabled_observations++;
          existing.pages.add(expectedUid);existing.routes.add(route);if(row.label)existing.labels.add(row.label);if(row.disabledReason)existing.disabled_reasons.add(row.disabledReason);
          formalEvidence.set(key,existing);
        }
      }
      for (const error of runtimeErrors) failures.push(`${expectedUid}:${error}`);
      await page.close();
    }
  } finally {
    await browser.close();
  }

  const formalRows=[...formalEvidence.values()].sort((a,b)=>a.resource_key.localeCompare(b.resource_key)).map((row)=>({
    resource_key:row.resource_key,observations:row.observations,enabled_observations:row.enabled_observations,disabled_observations:row.disabled_observations,
    pages:[...row.pages].sort(),routes:[...row.routes].sort(),labels:[...row.labels].sort(),disabled_reasons:[...row.disabled_reasons].sort(),
  }));
  if (failures.length) {
    process.stderr.write(`CONTROL_ACCEPTANCE_FAIL count=${failures.length}\n${failures.slice(0, 200).join("\n")}\n`);
    process.stderr.write(`CONTROL_ACCEPTANCE_PAGE_COUNTS ${JSON.stringify(perPage)}\n`);
    process.stderr.write(`CONTROL_ACCEPTANCE_FORMAL_RESOURCE_EVIDENCE ${JSON.stringify(formalRows)}\n`);
    process.exitCode = 1;
  } else {
    process.stdout.write(`CONTROL_ACCEPTANCE_PASS pages=${routes.length} interactive=${interactiveTotal} enabled=${enabledTotal} disabled=${disabledTotal} governed=${governedTotal}\n`);
    process.stdout.write(`CONTROL_ACCEPTANCE_PAGE_COUNTS ${JSON.stringify(perPage)}\n`);
    process.stdout.write(`CONTROL_ACCEPTANCE_FORMAL_RESOURCE_EVIDENCE matched=${formalRows.length} ${JSON.stringify(formalRows)}\n`);
  }
} finally {
  server.kill("SIGTERM");
}
