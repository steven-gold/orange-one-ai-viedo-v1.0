import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const adapter = fs.readFileSync("src/domain/catalog/identityClientCommandAdapters.ts", "utf8");
const server = fs.readFileSync("src/server/shared/identityPageCommandRuntime.ts", "utf8");
const port = fs.readFileSync("src/domain/strategyAdmin/strategyAdminRuntimePort.ts", "utf8");
const visual = fs.readFileSync("src/components/pages/StrategyAdminVisual.tsx", "utf8");

test("Strategy Admin search and refresh use registered routes with source identity", () => {
  assert.match(adapter, /input\.operation === "searchProjection" \|\| input\.operation === "refreshProjection"/);
  assert.match(adapter, /"\/v1\/search"/);
  assert.match(adapter, /"\/v1\/projections\/refresh"/);
  assert.match(adapter, /current_page_uid: "admin:STR-01"/);
  assert.match(adapter, /source_page_uid: input\.source_page_uid/);
});

test("Strategy Admin server authorization checks current page plus exact source action", () => {
  assert.match(server, /CURRENT_PAGE_RESOURCE_KEYS\["admin:STR-01"\]/);
  assert.match(server, /action:admin:STR-01:ACT-SEARCH/);
  assert.match(server, /action:admin:STR-01:ACT-REFRESH/);
  assert.match(server, /action:admin:STR-04:ACT-SEARCH/);
  assert.match(server, /evaluateResourceAction\(resourceKey, "INVOKE"\)/);
});

test("Strategy Admin only marks Search and Refresh runtime-ready", () => {
  assert.match(port, /STRATEGY_ADMIN_MATERIALIZED_OPERATIONS[\s\S]*"searchProjection"[\s\S]*"refreshProjection"/);
  assert.doesNotMatch(port, /STRATEGY_ADMIN_MATERIALIZED_OPERATIONS[\s\S]*"exportProjection"[\s\S]*\]\);/);
});

test("Strategy Admin materializes registered Search and Refresh forms", () => {
  assert.match(visual, /SearchProjectionRequest/);
  assert.match(visual, /RefreshProjectionRequest/);
  assert.match(visual, /data-runtime-binding-validation="PARTIAL_SEARCH_REFRESH_MATERIALIZED"/);
  assert.match(visual, /data-runtime-materialized-operations="searchProjection,refreshProjection"/);
});
