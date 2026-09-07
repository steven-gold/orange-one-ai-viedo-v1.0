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
