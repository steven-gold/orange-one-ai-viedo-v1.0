import fs from "node:fs";

const catalogPath = "06_permission/account_permission_catalog.yaml";
const text = fs.readFileSync(catalogPath, "utf8");

function readCount(key) {
  const match = text.match(new RegExp(`^\\s*${key}:\\s*(\\d+)\\s*$`, "m"));
  if (!match) throw new Error(`LEGACY_PERMISSION_CATALOG_BASELINE_MISSING_${key}`);
  return Number(match[1]);
}

const canonicalPages = readCount("canonical_pages");
const pageResources = readCount("page_permission_resources");
const controlResources = readCount("control_permission_resources");
const actionResources = readCount("action_permission_resources");
const resourceTotal = readCount("resource_total");
const legacyCatalogControlActionBaseline = controlResources + actionResources;

if (canonicalPages !== 92 || pageResources !== 92) {
  throw new Error(`FORMAL_ACCEPTANCE_PAGE_CATALOG_MISMATCH canonical=${canonicalPages} page_resources=${pageResources}`);
}
if (controlResources !== 1141) {
  throw new Error(`FORMAL_ACCEPTANCE_CONTROL_DENOMINATOR_CHANGED expected=1141 actual=${controlResources}`);
}
if (actionResources !== 312) {
  throw new Error(`FORMAL_ACCEPTANCE_ACTION_DENOMINATOR_CHANGED expected=312 actual=${actionResources}`);
}
if (legacyCatalogControlActionBaseline !== 1453) {
  throw new Error(`LEGACY_PERMISSION_CATALOG_BASELINE_CHANGED expected=1453 actual=${legacyCatalogControlActionBaseline}`);
}
if (resourceTotal !== 3650) {
  throw new Error(`FORMAL_PERMISSION_RESOURCE_TOTAL_CHANGED expected=3650 actual=${resourceTotal}`);
}

process.stdout.write(
  `LEGACY_PERMISSION_CATALOG_BASELINE_PASS canonical_pages=${canonicalPages} controls=${controlResources} actions=${actionResources} control_action_baseline=${legacyCatalogControlActionBaseline} permission_resources=${resourceTotal}\n`,
);

const currentEvidencePath = "docs/construction/evidence/CURRENT_ACCEPTANCE_DENOMINATOR_2026-09-10.json";
const current = JSON.parse(fs.readFileSync(currentEvidencePath, "utf8"));
const currentNeon = current.production_neon ?? {};
const currentDom = current.post_deploy_dom ?? {};
if (current.legacy_permission_catalog?.controls !== controlResources || current.legacy_permission_catalog?.actions !== actionResources || current.legacy_permission_catalog?.control_action_baseline !== legacyCatalogControlActionBaseline || current.legacy_permission_catalog?.permission_resources !== resourceTotal) {
  throw new Error("CURRENT_DENOMINATOR_LEGACY_BASELINE_MISMATCH");
}
if (currentNeon.active_controls !== 1148 || currentNeon.active_actions !== 319 || currentNeon.current_control_action_denominator !== 1467 || currentNeon.control_action_expansion !== 14) {
  throw new Error(`CURRENT_PERMISSION_CONTROL_ACTION_DENOMINATOR_MISMATCH controls=${currentNeon.active_controls} actions=${currentNeon.active_actions} total=${currentNeon.current_control_action_denominator} expansion=${currentNeon.control_action_expansion}`);
}
if (currentNeon.active_permission_resources !== 3672 || currentNeon.permission_resource_expansion !== 22) {
  throw new Error(`CURRENT_PERMISSION_RESOURCE_DENOMINATOR_MISMATCH total=${currentNeon.active_permission_resources} expansion=${currentNeon.permission_resource_expansion}`);
}
if (currentDom.interactive !== 555 || currentDom.governed !== 555 || currentDom.enabled + currentDom.disabled !== currentDom.interactive) {
  throw new Error(`CURRENT_DOM_EVIDENCE_MISMATCH interactive=${currentDom.interactive} governed=${currentDom.governed} enabled=${currentDom.enabled} disabled=${currentDom.disabled}`);
}
process.stdout.write(`CURRENT_ACCEPTANCE_DENOMINATOR_PASS legacy=${legacyCatalogControlActionBaseline} current_permission=${currentNeon.current_control_action_denominator} expansion=${currentNeon.control_action_expansion} current_dom=${currentDom.interactive} governed=${currentDom.governed}\n`);
